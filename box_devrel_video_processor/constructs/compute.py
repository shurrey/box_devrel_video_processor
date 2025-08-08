import aws_cdk as cdk
from aws_cdk import (
    Size,
    aws_lambda as _lambda,
    aws_lambda_python_alpha as _lambpy,
    aws_ec2 as ec2,
    aws_ecr_assets
)
from constructs import Construct
from app_config import app_config

class ComputeConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, vpc, storage, security, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Lambda layer
        box_gen_lambda_layer = _lambpy.PythonLayerVersion(
            self, 'BoxLayer',
            entry='box_sdk_gen',
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description='transcription Box Gen layer',
            layer_version_name='devrelTranscriptionGenBoxLayer'
        )

        # Use pre-built public layer for OpenCV/Pillow/numpy
        opencv_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "OpenCVLayer",
            layer_version_arn="arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p312-opencv-python:1"
        )
        
        # Skip ML layers - use container image instead
        
        # Skill Lambda (outside VPC for API Gateway)
        self.skill_lambda = _lambpy.PythonFunction(
            self, "SkillLambda",
            entry="lambdas/skill",
            index="skill.py",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_handler",
            layers=[box_gen_lambda_layer],
            timeout=cdk.Duration.minutes(15),
            role=security.skill_lambda_role,
            environment={
                "LOG_LEVEL": app_config['LOG_LEVEL'],
                "BOX_SKILL_SECRET_ARN": security.box_skill_secret.secret_arn,
                "QUEUE_URL": storage.transcribe_queue.queue_url
            }
        )

        # Transcribe Lambda (inside VPC)
        self.transcribe_lambda = _lambpy.PythonFunction(
            self, "TranscribeLambda",
            entry="lambdas/transcribe",
            index="transcribe.py",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_handler",
            layers=[box_gen_lambda_layer],
            timeout=cdk.Duration.minutes(15),
            role=security.vpc_lambda_role,
            ephemeral_storage_size=Size.gibibytes(10),
            memory_size=10240,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            environment={
                "LOG_LEVEL": app_config['LOG_LEVEL'],
                "BOX_SKILL_SECRET_ARN": security.box_skill_secret.secret_arn,
                "STORAGE_BUCKET": storage.storage_bucket.bucket_name,
                "TRANSCRIBE_BUCKET": storage.transcription_bucket.bucket_name,
                "JOB_TABLE": storage.job_table.table_name,
                "QUEUE_URL": storage.transcribe_queue.queue_url
            }
        )

        # Summarize Lambda (container image for ML dependencies)
        self.summarize_lambda = _lambda.DockerImageFunction(
            self, "SummarizeLambda",
            code=_lambda.DockerImageCode.from_image_asset(
                "lambdas/process",
                file="Dockerfile",
                platform=aws_ecr_assets.Platform.LINUX_AMD64
            ),
            timeout=cdk.Duration.minutes(15),
            role=security.vpc_lambda_role,
            ephemeral_storage_size=Size.gibibytes(10),
            memory_size=10240,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            environment={
                "LOG_LEVEL": app_config['LOG_LEVEL'],
                "STORAGE_BUCKET": storage.storage_bucket.bucket_name,
                "TRANSCRIBE_BUCKET": storage.transcription_bucket.bucket_name,
                "JOB_TABLE": storage.job_table.table_name,
                "BOX_DOCGEN_SECRET_ARN": security.box_docgen_secret.secret_arn,
                "NUMBA_CACHE_DIR": "/tmp",
                "NUMBA_DISABLE_JIT": "1"
            }
        )
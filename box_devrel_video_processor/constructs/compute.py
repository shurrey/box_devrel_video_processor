import aws_cdk as cdk
from aws_cdk import (
    Size,
    aws_lambda as _lambda,
    aws_lambda_python_alpha as _lambpy,
    aws_ec2 as ec2
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

        # Summarize Lambda (inside VPC)
        self.summarize_lambda = _lambpy.PythonFunction(
            self, "SummarizeLambda",
            entry="lambdas/process",
            index="process.py",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_handler",
            layers=[box_gen_lambda_layer],
            timeout=cdk.Duration.minutes(15),
            role=security.vpc_lambda_role,
            ephemeral_storage_size=Size.gibibytes(10),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            environment={
                "LOG_LEVEL": app_config['LOG_LEVEL'],
                "STORAGE_BUCKET": storage.storage_bucket.bucket_name,
                "TRANSCRIBE_BUCKET": storage.transcription_bucket.bucket_name,
                "JOB_TABLE": storage.job_table.table_name,
                "BOX_DOCGEN_SECRET_ARN": security.box_docgen_secret.secret_arn
            }
        )
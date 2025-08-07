import aws_cdk as cdk
from aws_cdk import (
    aws_iam as _iam,
    aws_secretsmanager as secretsmanager
)
from constructs import Construct
from app_config import box_config

class SecurityConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, storage, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create Secrets Manager secrets for Box credentials
        self.box_skill_secret = secretsmanager.Secret(
            self, "BoxSkillSecret",
            secret_name="box-devrel/skill-credentials",
            description="Box Skill API credentials",
            secret_object_value={
                "client_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_CLIENT_ID']),
                "primary_key": cdk.SecretValue.unsafe_plain_text(box_config['BOX_KEY_1']),
                "secondary_key": cdk.SecretValue.unsafe_plain_text(box_config['BOX_KEY_2'])
            }
        )
        
        self.box_docgen_secret = secretsmanager.Secret(
            self, "BoxDocGenSecret",
            secret_name="box-devrel/docgen-credentials",
            description="Box DocGen API credentials",
            secret_object_value={
                "client_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_DOCGEN_CLIENT_ID']),
                "client_secret": cdk.SecretValue.unsafe_plain_text(box_config['BOX_DOCGEN_CLIENT_SECRET']),
                "template_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_DOCGEN_TEMPLATE_ID']),
                "blog_agent_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_BLOG_AGENT_ID']),
                "tweet_agent_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_TWEET_AGENT_ID']),
                "linkedin_agent_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_LINKEDIN_AGENT_ID']),
                "youtube_agent_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_YOUTUBE_AGENT_ID']),
                "ai_file_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_AI_FILE_ID']),
                "metadata_template_key": cdk.SecretValue.unsafe_plain_text(box_config['BOX_METADATA_TEMPLATE_KEY'])
            }
        )

        # Create IAM policy with minimal permissions
        lambda_custom_policy = _iam.PolicyDocument(
            assign_sids=False,
            statements=[
                # S3 permissions for specific buckets only
                _iam.PolicyStatement(
                    effect=_iam.Effect.ALLOW,
                    actions=[
                        's3:GetObject',
                        's3:PutObject',
                        's3:DeleteObject'
                    ],
                    resources=[
                        storage.storage_bucket.bucket_arn + "/*",
                        storage.transcription_bucket.bucket_arn + "/*"
                    ]
                ),
                # Transcribe permissions
                _iam.PolicyStatement(
                    effect=_iam.Effect.ALLOW,
                    actions=[
                        'transcribe:StartTranscriptionJob',
                        'transcribe:GetTranscriptionJob',
                        'transcribe:ListTranscriptionJobs'
                    ],
                    resources=["*"]  # Transcribe jobs don't have specific ARNs
                ),
                # Bedrock permissions for specific models
                _iam.PolicyStatement(
                    effect=_iam.Effect.ALLOW,
                    actions=[
                        'bedrock:InvokeModel',
                        'bedrock:InvokeModelWithResponseStream'
                    ],
                    resources=[
                        f"arn:aws:bedrock:{cdk.Stack.of(self).region}::foundation-model/*"
                    ]
                ),
                # SQS permissions for specific queue
                _iam.PolicyStatement(
                    effect=_iam.Effect.ALLOW,
                    actions=[
                        'sqs:SendMessage',
                        'sqs:ReceiveMessage',
                        'sqs:DeleteMessage',
                        'sqs:GetQueueAttributes'
                    ],
                    resources=[storage.transcribe_queue.queue_arn]
                ),
                # DynamoDB permissions for specific table
                _iam.PolicyStatement(
                    effect=_iam.Effect.ALLOW,
                    actions=[
                        'dynamodb:GetItem',
                        'dynamodb:PutItem',
                        'dynamodb:UpdateItem',
                        'dynamodb:DeleteItem'
                    ],
                    resources=[storage.job_table.table_arn]
                ),
                # Secrets Manager permissions
                _iam.PolicyStatement(
                    effect=_iam.Effect.ALLOW,
                    actions=[
                        'secretsmanager:GetSecretValue'
                    ],
                    resources=[
                        self.box_skill_secret.secret_arn,
                        self.box_docgen_secret.secret_arn
                    ]
                )
        ])

        # Role for skill Lambda (outside VPC)
        self.skill_lambda_role = _iam.Role(
            scope=self, id='SkillLambdaRole',
            assumed_by=_iam.ServicePrincipal('lambda.amazonaws.com'),
            role_name="box-devrel-skill-lambda-role",
            description="box-devrel-skill-lambda-role",
            inline_policies={"lambda_custom_policy": lambda_custom_policy},
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    'service-role/AWSLambdaBasicExecutionRole'
                )
            ]
        )
        
        # Role for VPC Lambdas
        self.vpc_lambda_role = _iam.Role(
            scope=self, id='VpcLambdaRole',
            assumed_by=_iam.ServicePrincipal('lambda.amazonaws.com'),
            role_name="box-devrel-vpc-lambda-role",
            description="box-devrel-vpc-lambda-role",
            inline_policies={"lambda_custom_policy": lambda_custom_policy},
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    'service-role/AWSLambdaBasicExecutionRole'
                ),
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    'service-role/AWSLambdaVPCAccessExecutionRole'
                )
            ]
        )
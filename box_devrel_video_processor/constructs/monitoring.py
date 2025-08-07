import aws_cdk as cdk
from aws_cdk import aws_cloudtrail as cloudtrail
from constructs import Construct

class MonitoringConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, storage, compute, api, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # CloudTrail for audit logging
        cloudtrail.Trail(
            self, 'DevRelTrail',
            bucket=storage.trail_bucket,
            include_global_service_events=True,
            is_multi_region_trail=True,
            enable_file_validation=True
        )

        # CloudWatch Alarms for Lambda errors
        compute.skill_lambda.metric_errors().create_alarm(
            self, "SkillLambdaErrors",
            threshold=5,
            evaluation_periods=2,
            alarm_description="Skill Lambda error rate too high"
        )
        
        compute.transcribe_lambda.metric_errors().create_alarm(
            self, "TranscribeLambdaErrors",
            threshold=3,
            evaluation_periods=2,
            alarm_description="Transcribe Lambda error rate too high"
        )
        
        compute.summarize_lambda.metric_errors().create_alarm(
            self, "SummarizeLambdaErrors",
            threshold=3,
            evaluation_periods=2,
            alarm_description="Summarize Lambda error rate too high"
        )

        # API Gateway error monitoring
        api.api.metric_client_error().create_alarm(
            self, "ApiGateway4xxErrors",
            threshold=10,
            evaluation_periods=2,
            alarm_description="API Gateway 4xx error rate too high"
        )
        
        api.api.metric_server_error().create_alarm(
            self, "ApiGateway5xxErrors",
            threshold=5,
            evaluation_periods=2,
            alarm_description="API Gateway 5xx error rate too high"
        )
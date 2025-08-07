#!/usr/bin/env python3
import aws_cdk as cdk
from aws_cdk import (
    aws_s3 as s3,
    aws_lambda_event_sources as ales
)
from constructs import Construct

from .constructs.networking import NetworkingConstruct
from .constructs.storage import StorageConstruct
from .constructs.security import SecurityConstruct
from .constructs.compute import ComputeConstruct
from .constructs.api import ApiConstruct
from .constructs.monitoring import MonitoringConstruct

class BoxDevRelVideoProcessorStack(cdk.Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
       
        # Create constructs
        networking = NetworkingConstruct(self, "Networking")
        storage = StorageConstruct(self, "Storage")
        security = SecurityConstruct(self, "Security", storage=storage)
        compute = ComputeConstruct(self, "Compute", 
                                 vpc=networking.vpc, 
                                 storage=storage, 
                                 security=security)
        api = ApiConstruct(self, "Api", skill_lambda=compute.skill_lambda)
        monitoring = MonitoringConstruct(self, "Monitoring", 
                                       storage=storage, 
                                       compute=compute, 
                                       api=api)

        # Event sources
        transcribe_source = ales.SqsEventSource(storage.transcribe_queue)
        compute.transcribe_lambda.add_event_source(transcribe_source)

        summarize_source = ales.S3EventSource(
            storage.transcription_bucket, 
            events=[s3.EventType.OBJECT_CREATED_PUT],
            filters=[
                s3.NotificationKeyFilter(
                    prefix="transcriptions/",
                    suffix=".srt"
                )
            ]
        )
        compute.summarize_lambda.add_event_source(summarize_source)

        # Permissions
        storage.job_table.grant_full_access(compute.transcribe_lambda)
        storage.job_table.grant_full_access(compute.summarize_lambda)
        storage.storage_bucket.grant_read_write(compute.transcribe_lambda)
        storage.storage_bucket.grant_read_write(compute.summarize_lambda)
        storage.transcription_bucket.grant_read_write(compute.summarize_lambda)
        storage.transcribe_queue.grant_send_messages(compute.skill_lambda)
        storage.transcribe_queue.grant_consume_messages(compute.transcribe_lambda)
        storage.transcribe_queue.grant_purge(compute.transcribe_lambda)
        
        # Outputs
        cdk.CfnOutput(self, "Deployment Stage", value=str(api.api.deployment_stage.to_string()))
        cdk.CfnOutput(self, "URL", value=api.api.url)
        cdk.CfnOutput(self, "OIDC Login Endpoint: ", value=api.skill_resource.path)


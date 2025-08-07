import aws_cdk as cdk
from aws_cdk import (
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_dynamodb as _dynamo,
    aws_cloudtrail as cloudtrail
)
from constructs import Construct

class StorageConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Dead letter queue for failed messages
        dead_letter_queue = sqs.Queue(
            self, "TranscribeDeadLetterQueue",
            queue_name="DevRelTranscribeDeadLetterQueue",
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        self.transcribe_queue = sqs.Queue(
            self, "TranscribeQueue",
            queue_name="DevRelTranscribeQueue",
            visibility_timeout=cdk.Duration.minutes(15),
            removal_policy=cdk.RemovalPolicy.DESTROY,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=dead_letter_queue
            )
        )
        
        # CloudWatch alarm for DLQ messages
        from aws_cdk import aws_cloudwatch as cloudwatch
        cloudwatch.Alarm(
            self, "TranscribeDLQAlarm",
            metric=cloudwatch.Metric(
                namespace="AWS/SQS",
                metric_name="ApproximateNumberOfVisibleMessages",
                dimensions_map={"QueueName": dead_letter_queue.queue_name}
            ),
            threshold=1,
            evaluation_periods=1,
            alarm_description="Failed transcription jobs in Dead Letter Queue need attention"
        )

        self.storage_bucket = s3.Bucket(
            self, 'StorageBucket',
            bucket_name="box-devrel-video-storage-bucket",
            public_read_access=False,
            auto_delete_objects=True,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True
        )

        self.transcription_bucket = s3.Bucket(
            self, 'TranscriptionBucket',
            bucket_name="box-devrel-video-transcription-bucket",
            public_read_access=False,
            auto_delete_objects=True,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True
        )
        
        self.job_table = _dynamo.Table(
            self, "JobTable",
            table_name="devRelTranscriptionJobTable",
            partition_key=_dynamo.Attribute(name="job_id", type=_dynamo.AttributeType.STRING),
            removal_policy=cdk.RemovalPolicy.DESTROY,
            encryption=_dynamo.TableEncryption.AWS_MANAGED
        )

        # CloudTrail bucket
        self.trail_bucket = s3.Bucket(
            self, 'CloudTrailBucket',
            bucket_name="box-devrel-cloudtrail-logs",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            auto_delete_objects=True,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )
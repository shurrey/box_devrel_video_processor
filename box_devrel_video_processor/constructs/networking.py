import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

class NetworkingConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create VPC for internal processing
        self.vpc = ec2.Vpc(self, "ProcessingVpc", max_azs=2, nat_gateways=1)
        
        # Add VPC endpoints for AWS services
        self.vpc.add_gateway_endpoint("S3Endpoint", service=ec2.GatewayVpcEndpointAwsService.S3)
        self.vpc.add_gateway_endpoint("DynamoEndpoint", service=ec2.GatewayVpcEndpointAwsService.DYNAMODB)
        self.vpc.add_interface_endpoint("SQSEndpoint", service=ec2.InterfaceVpcEndpointAwsService.SQS)
        self.vpc.add_interface_endpoint("TranscribeEndpoint", service=ec2.InterfaceVpcEndpointAwsService.TRANSCRIBE)
        self.vpc.add_interface_endpoint("SecretsManagerEndpoint", service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER)
        
        # Note: Box API calls go through NAT Gateway (internet access already configured)
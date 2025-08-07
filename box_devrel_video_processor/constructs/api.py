import aws_cdk as cdk
from aws_cdk import aws_apigateway as _apigw
from constructs import Construct

class ApiConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, skill_lambda, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Define API Gateway
        self.api = _apigw.RestApi(self, 'SkillGateway')

        skill_resource = self.api.root.add_resource(
            'skill',
            default_cors_preflight_options=_apigw.CorsOptions(
                allow_methods=['POST'],
                allow_origins=[
                    'https://api.box.com',
                    'https://upload.box.com',
                    'https://app.box.com',
                    'https://account.box.com',
                    'https://cloud.app.box.com',
                    'https://boxcloud.box.com'
                ])
        )

        skill_lambda_integration = _apigw.LambdaIntegration(
            skill_lambda,
            proxy=True,
            integration_responses=[
                _apigw.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': "'*'"
                    }
                )
            ]
        )

        skill_resource.add_method(
            'POST', skill_lambda_integration,
            method_responses=[
                _apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ]
        )
        
        self.skill_resource = skill_resource
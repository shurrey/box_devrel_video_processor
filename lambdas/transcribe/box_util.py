import os
import datetime
import json
import boto3

from box_sdk_gen import (
    BoxClient,
    BoxDeveloperTokenAuth,
    ByteStream,
    read_byte_stream
)

def get_box_credentials():
    secret_arn = os.environ['BOX_SKILL_SECRET_ARN']
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_arn)
    return json.loads(response['SecretString'])

class box_util:

    def __init__(self, read_token, write_token, logger):
        self.logger = logger

        credentials = get_box_credentials()
        self.client_id = credentials['client_id']
        self.primary_key = credentials['primary_key']
        self.secondary_key = credentials['secondary_key']

        self.read_client = self.get_basic_client(read_token)
        self.write_client = self.get_basic_client(write_token)

        self.logger.debug(f"client_id: {self.client_id} retrieved from secrets manager")
        
    def get_basic_client(self,token):

        auth = BoxDeveloperTokenAuth(token=token)

        return BoxClient(auth)
    
    def get_file_contents(self,file_id):

        downloaded_file_content: ByteStream = self.read_client.downloads.download_file(
            file_id=file_id
        )

        self.logger.debug(f"downloaded file content = {downloaded_file_content}")

        file_content = read_byte_stream(downloaded_file_content)

        return file_content
import base64
import hashlib
import hmac
import os
import datetime
import json
import boto3

from box_sdk_gen import (
    BoxClient, 
    BoxDeveloperTokenAuth,
    ByteStream
)

def get_box_credentials():
    secret_arn = os.environ['BOX_SKILL_SECRET_ARN']
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_arn)
    return json.loads(response['SecretString'])

class box_util:

    skills_error_enum = {
        "FILE_PROCESSING_ERROR": 'skills_file_processing_error',
        "INVALID_FILE_SIZE": 'skills_invalid_file_size_error',
        "INVALID_FILE_FORMAT": 'skills_invalid_file_format_error',
        "INVALID_EVENT": 'skills_invalid_event_error',
        "NO_INFO_FOUND": 'skills_no_info_found',
        "INVOCATIONS_ERROR": 'skills_invocations_error',
        "EXTERNAL_AUTH_ERROR": 'skills_external_auth_error',
        "BILLING_ERROR": 'skills_billing_error',
        "UNKNOWN": 'skills_unknown_error'
    }

    box_video_formats = set([
        '.3g2',
        '.3gp',
        '.avi',
        '.flv',
        '.m2v',
        '.m2ts',
        '.m4v',
        '.mkv',
        '.mov',
        '.mp4',
        '.mpeg',
        '.mpg',
        '.ogg',
        '.mts',
        '.qt',
        '.ts',
        '.wmv'
    ])

    box_audio_formats = set([
        '.3g2',
        '.aac',
        '.aif',
        '.aifc',
        '.aiff',
        '.amr',
        '.au',
        '.flac',
        '.m4a',
        '.mp3',
        '.ogg',
        '.ra',
        '.wav',
        '.wma'
    ])

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
    
    def _compute_signature(self, body, headers, signature_key):
        if signature_key is None:
            return None
        if headers.get('box-signature-version') != '1':
            return None
        if headers.get('box-signature-algorithm') != 'HmacSHA256':
            return None

        encoded_signature_key = signature_key.encode('utf-8')
        encoded_delivery_time_stamp = headers.get('box-delivery-timestamp').encode('utf-8')
        new_hmac = hmac.new(encoded_signature_key, digestmod=hashlib.sha256)
        new_hmac.update(body + encoded_delivery_time_stamp)
        signature = base64.b64encode(new_hmac.digest()).decode()
        return signature
    
    def is_launch_safe(self, body, headers):
        primary_signature = self._compute_signature(body, headers, self.primary_key)
        if primary_signature is not None and hmac.compare_digest(primary_signature, headers.get('box-signature-primary')):
            return True

        if self.secondary_key:
            secondary_signature = self._compute_signature(body, headers, self.secondary_key)
            if secondary_signature is not None and hmac.compare_digest(secondary_signature, headers.get('box-signature-secondary')):
                return True
            return False

        return False

    def is_video(self, file_type):
        return file_type in box_util.box_video_formats
    
    def is_audio(self, file_type):
        return file_type in box_util.box_audio_formats
    
    def get_file_contents(self,file_id):
        
        file_content_stream: ByteStream = self.read_client.downloads.download_file(file_id=file_id)
        file_content = file_content_stream.read()

        return file_content
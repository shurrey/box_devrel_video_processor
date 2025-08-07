import base64
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
import json
import logging
import os
from pprint import pformat
from urllib.parse import parse_qsl

import box_util


sqs = boto3.client('sqs')
queue_url = os.environ['QUEUE_URL']

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
logger = logging.getLogger()

if LOG_LEVEL == "DEBUG":
    logger.setLevel(logging.DEBUG)
elif LOG_LEVEL == "ERROR":
    logger.setLevel(logging.ERROR)
elif LOG_LEVEL == "WARN":
    logger.setLevel(logging.WARN)
else:
    logger.setLevel(logging.INFO)

def get_file_context(body):
    
    file_context = {}

    file_context['request_id'] = body['id']
    file_context['skill_id'] = body['skill']['id']
    file_context['file_id'] = body['source']['id']
    file_context['file_name'] = body['source']['name']
    file_context['file_size'] = body['source']['size']
    file_context['file_read_token'] = body['token']['read']['access_token']
    file_context['file_write_token'] = body['token']['write']['access_token']
    file_context['user_id'] = body['event']['created_by']['id']
    file_context['folder_id'] = body['source']['parent']['id']
    
    return file_context


def lambda_handler(event, context):
    logger.debug(f"skill->lambda_handler: Event: " + pformat(event))
    logger.debug(f"skill->lambda_handler: Context: " + pformat(context))

    try:
        
        body = json.loads(event['body'])
        body_bytes = bytes(event['body'], 'utf-8')
        headers = event['headers']

        file_context = get_file_context(body)

        boxsdk = box_util.box_util(
            file_context['file_read_token'],
            file_context['file_write_token'],
            logger
        )

        if not boxsdk.is_launch_safe(body_bytes,headers):
            message = "Launch failed signature check"
            
            logger.debug(message)
            
            return {
                "statusCode": 403,
                "body": message,
                "headers": {
                    "Content-Type": "text/plain",
                }
            }
        
        file_name, file_extension = os.path.splitext(file_context['file_name'])

        if not boxsdk.is_video(file_extension) and not boxsdk.is_audio(file_extension):
            message = "File is not audio or video"
            logger.debug(message)

            return {
                "statusCode": 415,
                "body": message,
                "headers": {
                    "Content-Type": "text/plain",
                }
            }
        
        logger.debug("launch valid")

        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(file_context)
        )

        return {
            "statusCode": 200,
            "body": "Video processing started",
            "headers": {
                "Content-Type": "text/plain",
            }
        }
        
    except Exception as e:
        message = f"Error processing skill request: {e}"
        logger.exception(message)

        
        return {
            'statusCode' : 500,
            'body' : message,
            "headers": {
                "Content-Type": "text/plain"
            }
        }
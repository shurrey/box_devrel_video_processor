import base64
import sys
import time
from urllib.parse import parse_qsl
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
import json
import logging
import os
from pprint import pformat
import uuid
from thumbnail import extract_person_thumbnail, get_random_video_frame


import ai_util,box_util

dynamodb = boto3.resource('dynamodb')

JOB_TABLE = os.environ['JOB_TABLE']
job_table= dynamodb.Table(JOB_TABLE)

s3 = boto3.client('s3')
storage_bucket = os.environ['STORAGE_BUCKET']
transcription_bucket = os.environ['TRANSCRIBE_BUCKET']

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

def get_box_docgen_credentials():
    secret_arn = os.environ['BOX_DOCGEN_SECRET_ARN']
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_arn)
    return json.loads(response['SecretString'])


def get_job_data(job_id):
    results = job_table.query(KeyConditionExpression=Key("job_id").eq(job_id))
    
    job_data = {}
    
    try:
        item = results['Items'][0]
        logger.debug("item: " + str(item))

        """
        'job_id': str(job_id),
        'job_uri': str(job_uri),
        'request_id': file_context['request_id'],
        'skill_id': file_context['skill_id'],
        'file_id': file_context['file_id'],
        'file_name': file_context['file_name'],
        'file_size': file_context['file_size'],
        'file_read_token': file_context['file_read_token'],
        'file_write_token': file_context['file_write_token'],
        """
        
        job_data['job_id'] = item['job_id']
        job_data['job_uri'] =  item['job_uri']
        job_data['request_id'] =  item['request_id']
        job_data['skill_id'] =  item['skill_id']
        job_data['file_id'] =  str(item['file_id'])
        job_data['file_name'] =  item['file_name']
        job_data['file_size'] =  str(item['file_size'])
        job_data['folder_id'] =  str(item['folder_id'])
        job_data['file_read_token'] =  item['file_read_token']
        job_data['file_write_token'] =  item['file_write_token']
        job_data['user_id'] =  str(item['user_id'])
        logger.debug("job_data: " + str(job_data))
        
    except Exception as e:
        logger.error(str(e))
        logger.error(job_id + ' is not defined.')
        raise Exception(f"{job_id} is not defined. {e}")

    return job_data


def delete_job_data(job_id):
    job_table.delete_item(
        Key={
            'job_id': job_id
        }
    )


def create_transcript_with_seconds(entries):
    
    transcript = ""
    second = -1

    for entry in entries:
        
        if entry['type'] == "punctuation":
            start = second
        else:
            start=int(float(entry['start_time']))
            
        if second == -1:
            second = start

        if start == second:
            transcript += f"{entry['alternatives'][0]['content']} "
        else:
            time_tuple=divmod(second, 60)
            time_string= f"{time_tuple[0]:02d}:{time_tuple[1]:02d}"
            transcript += f"\n{time_string} {entry['alternatives'][0]['content']} "
            second=start

    return transcript

def process_transcription(transcription_file,job_data,box,ai,video_shared_link, srt_shared_link, credentials):  
    """
    "template_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_DOCGEN_TEMPLATE_ID']),
    "blog_agent_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_BLOG_AGENT_ID']),
    "tweet_agent_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_TWEET_AGENT_ID']),
    "linkedin_agent_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_LINKEDIN_AGENT_ID']),
    "youtube_agent_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_YOUTUBE_AGENT_ID']),
    "ai_file_id": cdk.SecretValue.unsafe_plain_text(box_config['BOX_AI_FILE_ID']),
    "metadata_template_key"
    """
    try:
                            
        meeting_file = transcription_file.replace("transcriptions/","").replace(".json", "")

        transcription, entries = ai.get_transcription(meeting_file)

        transcript = create_transcript_with_seconds(entries)
        
        logger.debug(f"transcription {transcription} transcript with seconds {transcript}")

        metadata = box.box_ai_extract(transcription, credentials['ai_file_id'], credentials['metadata_template_key'])

        blog = box.ask_box_ai(
            transcription,
            "write a blog post highlighting the technology described in the provided transcription.",
            credentials['blog_agent_id'],
            credentials['ai_file_id']
        )

        logger.debug(f"blog {blog}")

        tweet = box.ask_box_ai(
            transcription,
            "write a tweet highlighting the technology described in the provided transcription.",
            credentials['tweet_agent_id'],
            credentials['ai_file_id']
        )

        logger.debug(f"tweet {tweet}")

        linkedin = box.ask_box_ai(
            transcription,
            "write a linkedin post highlighting the technology described in the provided transcription.",
            credentials['linkedin_agent_id'],
            credentials['ai_file_id']
        )

        logger.debug(f"linkedin {linkedin}")

        youtube_description = box.ask_box_ai(
            transcript,
            "write a youtube description highlighting the technology described in the provided transcription.",
            credentials['youtube_agent_id'],
            credentials['ai_file_id']
        )

        logger.debug(f"youtube {youtube_description}")

        doc_contents = box.create_docgen_json(
            topic=metadata.get("topic") or "unknown",
            author=metadata.get("author") or "unknown",
            provider=metadata.get("provider") or "unknown",
            model=metadata.get("model") or "unknown",
            technologogies=metadata.get("technologies") or "unknown",
            youtube_shared_link=video_shared_link or "",
            srt_shared_link=srt_shared_link or "",
            title=metadata.get("title") or "unknown",
            thumbnail_shared_link="thumbnail_shared_link",
            youtube_description=(youtube_description.replace("\"", "'") if youtube_description else ""),
            tags=metadata.get("tags") or "unknown",
            linkedin=(linkedin.replace("\"", "'") if linkedin else ""),
            tweet=(tweet.replace("\"", "'") if tweet else ""),
            blog=(blog.replace("\"", "'") if blog else "")
        )

        logger.debug(f"doc_contents {doc_contents}")

        box.generate_document(doc_contents, job_data['folder_id'], meeting_file, credentials['template_id'])

        thumbnail_folder_id = box.create_folder(job_data['folder_id'])
        video_content = ai.get_video(job_data['file_name'])  # Replace with the path to your video file
        video_file = "/tmp/video.mp4"
        with open(video_file, "wb") as f:
            f.write(video_content)

        frame_count = 10

        for i in range(frame_count):
            file_name = get_random_video_frame(video_file)

            with open(file_name, 'rb') as f: # type: ignore
                image_bytes = f.read()
                result_bytes = extract_person_thumbnail(
                    input_data=image_bytes,
                    target_size=(1920, 1080),  # YouTube thumbnail size
                    preserve_original_lighting=True  # Keep natural lighting
                )
            if result_bytes is not None:
                box.upload_file(f"{meeting_file}_thumbnail_{i}.jpg", result_bytes, thumbnail_folder_id)

            print(f"Thumbnail extraction complete.")

        return {
            'statusCode' : 200
        }

    except Exception as inst:
        logger.exception(f"transcribe: Exception: {inst}")

        return {
            'statusCode' : 500,
            'body' : f"Error summarizing file: {inst} file_id: {job_data['file_id']} skill_id: {job_data['skill_id']} request_id: {job_data['request_id']}", 
            "headers": {
                "Content-Type": "text/plain"
            }
        }

def lambda_handler(event, context):
    logger.debug(f"summarize->lambda_handler: Event: " + pformat(event))
    logger.debug(f"summarize->lambda_handler: Context: " + pformat(context))

    ai = ai_util.ai_util()

    for record in event['Records']:

        s3_key = record['s3']['object']['key']
        
        if not s3_key.endswith(".srt"):
            logger.info(f"Waiting for the SRT file...")
            return {
                'statusCode' : 200
            }

        time.sleep(30)

        credentials = get_box_docgen_credentials()

        job_data=get_job_data(s3_key.replace("transcriptions/","").replace(".srt","").replace(".json",""))

        box = box_util.box_util(
            credentials['client_id'],
            credentials['client_secret'],
            job_data['user_id'],
            logger    
        )

        json_file = ""
        srt_file = ""

        if s3_key.endswith(".json"):
            json_file = s3_key
            srt_file = s3_key.replace(".json", ".srt") 
        elif s3_key.endswith(".srt"):
            json_file = s3_key.replace(".srt", ".json")
            srt_file = s3_key
        else:
            logger.error(f"Unknown file type: {s3_key}")
            return {
                'statusCode' : 400
            }
        
        print(f"Processing transcription file: {json_file} and subtitles file: {srt_file}")

        video_shared_link = box.get_shared_link(job_data['file_id'])

        uploaded_file = box.upload_file(srt_file.replace("transcriptions/",""), ai.get_subtitles(srt_file.replace("transcriptions/","").replace(".srt","")), job_data['folder_id'])
        srt_shared_link = box.get_shared_link(uploaded_file['id'])

        process_transcription(json_file, job_data, box, ai, video_shared_link, srt_shared_link, credentials)

        delete_job_data(job_data['job_id'])

        # Delete transcription files and original video
        video_file_key = f"videos/{job_data['file_name']}"
        ai.delete_files(json_file, srt_file, video_file_key)


    return {
        'statusCode' : 200
    }
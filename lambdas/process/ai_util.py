import boto3
import json
import os
import uuid

class ai_util:

    def __init__(self):
        self.transcribe = boto3.client("transcribe")
        self.bedrock = boto3.client("bedrock-runtime")
        self.s3 = boto3.client("s3")
        self.transcriptions_store = os.environ['TRANSCRIBE_BUCKET']
        self.recordings_store = os.environ['STORAGE_BUCKET']
        
    def get_transcription_status(self, job_name):
        return self.transcribe.get_transcription_job(TranscriptionJobName=job_name)
    
    def get_transcription(self, job_unique_name):
        response = self.s3.get_object(
            Bucket=self.transcriptions_store,
            Key=f"transcriptions/{job_unique_name}.json"
        )
        content = response['Body'].read()

        json_content = json.loads(content)

        transcript = json_content["results"]['transcripts'][0]['transcript']
        items = json_content["results"]['items']

        return transcript, items
    
    def get_subtitles(self, job_unique_name):
        print(f"getting subtitles for {job_unique_name}")
        response = self.s3.get_object(
            Bucket=self.transcriptions_store,
            Key=f"transcriptions/{job_unique_name}.srt"
        )
        content = response['Body'].read()
        
        return content
    
    def delete_files(self, *file_keys):
        for file_key in file_keys:
            try:
                # Determine bucket based on file path
                if file_key.startswith("videos/"):
                    bucket = self.recordings_store
                    file_key = file_key.replace("videos/", "")
                else:
                    bucket = self.transcriptions_store
                    
                self.s3.delete_object(
                    Bucket=bucket,
                    Key=f"{file_key}"
                )
                print(f"Deleted file {file_key} from bucket {bucket}")
            except Exception as e:
                print(f"Error deleting file {file_key}: {e}")
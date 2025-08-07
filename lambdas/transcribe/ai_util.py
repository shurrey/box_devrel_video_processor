import boto3
import json
import os
import uuid

class ai_util:

    def __init__(self):
        self.transcribe = boto3.client("transcribe")
        self.bedrock = boto3.client("bedrock-runtime")
        self.s3 = boto3.client("s3")
        self.transcribe_store = os.environ['TRANSCRIBE_BUCKET']
        self.recordings_store = os.environ['STORAGE_BUCKET']

    def transcribe_file(self,file):
        """
        Trascribe the meeting recording file and stores the output in a S3 bucket
        """
        temp_name_append = uuid.uuid4().hex[:6]

        file_name, file_extension = os.path.splitext(file)

        print(f"file name {file_name} extension {file_extension} media format {file_extension[1:]}")

        job_name = file_name.replace(" ", "_").replace(",","").replace("&","_")
        job_unique_name = f"{job_name}_{temp_name_append}"

        job_uri = f"s3://{self.recordings_store}/{file}"

        self.transcribe.start_transcription_job(
            TranscriptionJobName=job_unique_name,
            Media={'MediaFileUri': job_uri},
            MediaFormat=file_extension[1:],
            LanguageCode='en-US',
            OutputBucketName=self.transcribe_store,
            OutputKey=f"transcriptions/{job_unique_name}.json",
            Subtitles={
                'Formats': ['srt']
            }
        )

        return job_unique_name, job_uri
    
    def get_transcription_status(self, job_name):
        return self.transcribe.get_transcription_job(TranscriptionJobName=job_name)
    
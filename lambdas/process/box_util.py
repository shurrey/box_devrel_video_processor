import io
import os
import datetime
import json
import tempfile
from time import sleep
import boto3

from box_sdk_gen import (
    AiAgentReference,
    AiAgentReferenceTypeField,
    AiItemBase,
    AiItemBaseTypeField,
    AiItemAsk,
    AiItemAskTypeField,
    BoxCCGAuth,
    BoxClient,
    BoxDeveloperTokenAuth,
    CCGConfig,
    CreateAiAskMode,
    CreateAiExtractStructuredMetadataTemplate,
    UploadFileAttributes,
    UploadFileAttributesParentField,
    FileReferenceV2025R0,
    CreateDocgenBatchV2025R0DestinationFolder,
    DocGenDocumentGenerationDataV2025R0,
    DocGenJobV2025R0StatusField,
    AddShareLinkToFileSharedLink,
    AddShareLinkToFileSharedLinkAccessField,
)

from box_sdk_gen.internal.utils import ByteStream

class box_util:

    def __init__(self, client_id, client_secret, user_id, logger):
        self.logger = logger
        self.client_id = client_id
        self.client_secret = client_secret
        
        self.client = self.get_ccg_client(user_id)

        self.box_ai_file_id = os.environ.get('BOX_AI_FILE_ID', None)
        self.box_ai_file_id = os.environ.get('BOX_AI_FILE_ID', None)
        self.box_docgen_template_id = os.environ.get('BOX_DOCGEN_TEMPLATE_ID', None)
        self.box_metadata_template_key = os.environ.get('BOX_METADATA_TEMPLATE_KEY', None)


        
    def get_basic_client(self,token):

        auth = BoxDeveloperTokenAuth(token=token)

        return BoxClient(auth)
    
    def get_ccg_client(self, user_id):
        ccg_config = CCGConfig(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_id=user_id,
        )
        auth = BoxCCGAuth(config=ccg_config)
        return BoxClient(auth=auth)
    
    def upload_file(self, file_name, content, folder_id):
        is_bytes = isinstance(content, (bytes, bytearray))
        mode = "wb" if is_bytes else "w"
        with tempfile.NamedTemporaryFile(mode=mode, delete=False) as temp_file:
            # Write bytes or text
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Upload the file
            with open(temp_file_path, "rb") as file:
                # Use root folder if folder_id is not provided
                parent_id = "0"
                if folder_id is not None:
                    parent_id = str(folder_id)

                uploaded_file = self.client.uploads.upload_file(
                    UploadFileAttributes(
                        name=file_name, parent=UploadFileAttributesParentField(id=parent_id)
                    ),
                    file,
                )

            self.logger.debug(f"File uploaded successfully: {uploaded_file.to_dict()}")
            
            entries = uploaded_file.to_dict()['entries']
            
            return entries[0]
        except Exception as e:
            self.logger.error(f"Error uploading file: {e}")
            return {
                'statusCode' : 500
            }
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)

    def box_ai_extract(self, content, ai_file_id, metadata_template_key):
        
        ai_ask_agent_config = AiAgentReference(id="enhanced_extract_agent", type=AiAgentReferenceTypeField.AI_AGENT_ID)
        try:
            box_ai_response = self.client.ai.create_ai_extract_structured(
                items=[
                    AiItemBase(
                        id=ai_file_id, # type: ignore
                        type=AiItemBaseTypeField.FILE,
                        content=content
                    )
                ],
                metadata_template=CreateAiExtractStructuredMetadataTemplate(
                    template_key=metadata_template_key,
                    scope="enterprise"
                ),
                ai_agent=ai_ask_agent_config
            )
            response_dict = box_ai_response.to_dict()
            self.logger.debug(f"Box AI extract response: {response_dict}")    
            return response_dict["answer"] # type: ignore

        except Exception as e:
            self.logger.error(f"Error asking box ai: {e}")
            return None
        
    def ask_box_ai(self, content, prompt, agent_id, ai_file_id):
        
        ai_ask_agent_config = AiAgentReference(id=agent_id, type=AiAgentReferenceTypeField.AI_AGENT_ID)
        try:
            box_ai_response = self.client.ai.create_ai_ask(
                CreateAiAskMode.SINGLE_ITEM_QA,
                prompt,
                [
                    AiItemAsk(
                        id=ai_file_id, # type: ignore
                        type=AiItemAskTypeField.FILE,
                        content=content,
                    )
                ],
                ai_agent=ai_ask_agent_config,
            )

            return box_ai_response.answer # type: ignore

        except Exception as e:
            self.logger.error(f"Error asking box ai: {e}")
            return None

    def generate_document(self, doc_contents, folder_id, file_name, template_id):
        docgen_jobs = self.client.docgen.create_docgen_batch_v2025_r0(
        FileReferenceV2025R0(id=template_id), # type: ignore
        "api",
        CreateDocgenBatchV2025R0DestinationFolder(id=folder_id),
        "docx",
        [
            DocGenDocumentGenerationDataV2025R0(
                generated_file_name=file_name, user_input=doc_contents
            )
        ],
    )

        self.logger.debug(f"Docgen job created with id: {docgen_jobs.id}")

        # Wait for the docgen job to complete
        while True:
            docgen_batch = self.client.docgen.get_docgen_batch_job_by_id_v2025_r0(docgen_jobs.id)

            self.logger.debug(f"Docgen job status: {docgen_batch.entries[0].status}")
            if docgen_batch.entries[0].status == DocGenJobV2025R0StatusField.COMPLETED:
                self.logger.debug(f"Docgen job completed with status: {docgen_batch.entries[0].status}")
                self.logger.info(f"Docgen job output file id: {docgen_batch.entries[0].output_file.id}")
                return docgen_batch.entries[0].output_file.id
            if docgen_batch.entries[0].status == DocGenJobV2025R0StatusField.FAILED:
                self.logger.error(f"Docgen job failed: {docgen_batch}")
                return None

            sleep(1)
        
        return None
    
    def create_docgen_json(self, 
        topic,
        author,
        provider,
        model,
        technologogies,
        youtube_shared_link,
        srt_shared_link,
        title,
        thumbnail_shared_link,
        youtube_description,
        tags,
        linkedin,
        tweet,
        blog
    ):
        
        docgen_json = {
            "topic": topic,
            "author": author,
            "provider": provider,
            "model": model,
            "technologies": technologogies,
            "youtube": {
                "shared_link": youtube_shared_link,
                "srt": srt_shared_link,
                "title": title,
                "thumbnail": thumbnail_shared_link,
                "description": youtube_description,
                "tags": tags
            },
            "linkedin" : linkedin,
            "x" : tweet,
            "blog" : blog
        }
        return docgen_json
    
    def get_shared_link(self, file_id):

        response = self.client.shared_links_files.add_share_link_to_file(
            file_id,
            "shared_link",
            shared_link=AddShareLinkToFileSharedLink(
                access=AddShareLinkToFileSharedLinkAccessField.COMPANY
            )
        )

        self.logger.debug(f"Shared link response: {response}")
        return response.shared_link.url # type: ignore
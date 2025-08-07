import pytest
import os
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_app_config():
    """Mock app_config module for all tests"""
    mock_config = {
        'box_config': {
            'BOX_CLIENT_ID': 'test-client-id',
            'BOX_KEY_1': 'test-key-1',
            'BOX_KEY_2': 'test-key-2',
            'BOX_DOCGEN_CLIENT_ID': 'test-docgen-client-id',
            'BOX_DOCGEN_CLIENT_SECRET': 'test-docgen-secret',
            'BOX_DOCGEN_TEMPLATE_ID': 'test-template-id',
            'BOX_BLOG_AGENT_ID': 'test-blog-agent',
            'BOX_TWEET_AGENT_ID': 'test-tweet-agent',
            'BOX_LINKEDIN_AGENT_ID': 'test-linkedin-agent',
            'BOX_YOUTUBE_AGENT_ID': 'test-youtube-agent',
            'BOX_AI_FILE_ID': 'test-ai-file-id',
            'BOX_METADATA_TEMPLATE_KEY': 'test-template-key'
        },
        'app_config': {
            'LOG_LEVEL': 'DEBUG'
        },
        'ai_config': {}
    }
    
    with patch.dict('sys.modules', {
        'app_config': type('MockModule', (), mock_config)()
    }):
        yield
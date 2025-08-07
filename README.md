
# Box DevRel Video Processor

An automated video processing pipeline that transforms uploaded videos into comprehensive social media content packages using AWS services and Box AI.

## Overview

This Box Skill automatically processes video/audio files uploaded to configured Box folders by:

1. **Transcription**: Downloads media files, uploads to S3, and uses AWS Transcribe to generate SRT subtitles
2. **AI Analysis**: Leverages Box AI to extract metadata and generate social media content
3. **Content Generation**: Creates YouTube descriptions, LinkedIn posts, X (Twitter) posts, and blog content
4. **Document Creation**: Uses Box Doc Gen to compile everything into a comprehensive document
5. **Cleanup**: Automatically removes temporary files after processing

## Architecture

- **API Gateway**: Receives Box webhook events
- **Lambda Functions**: 
  - Skill Lambda: Validates webhooks and queues jobs
  - Transcribe Lambda: Handles video download and transcription
  - Process Lambda: Generates content using Box AI and DocGen
- **Storage**: S3 buckets for video storage and transcriptions
- **Queue**: SQS for reliable job processing with dead letter queue
- **Database**: DynamoDB for job tracking
- **Security**: VPC isolation, Secrets Manager for credentials, minimal IAM permissions
- **Monitoring**: CloudWatch alarms and CloudTrail audit logging

## Prerequisites

- AWS CLI configured with appropriate permissions
- Node.js 20+ and AWS CDK v2 installed globally
- Python 3.11+
- Box Developer Account with:
  - Box Skills application
  - Box Custom application with client_credentils grant the following scopes:
    - Read files
    - Write files
    - Manage Doc Gen
  - Box AI agents configured
  - Box DocGen template created
  - Box Metadata template created

> ![note]
> Check out the [box_setup](box_setup) folder for examples of agents and information on the metadata template and doc gen template

## Configuration

1. **Create virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate.bat
   pip install -r requirements.txt
   ```

2. **Configure Box credentials:**
   ```bash
   cp app_config_template.py app_config.py
   ```
   
   Edit `app_config.py` with your Box application details:
   - `BOX_CLIENT_ID`: Your Box Skills app client ID
   - `BOX_KEY_1`: Primary webhook signature key
   - `BOX_KEY_2`: Secondary webhook signature key
   - `BOX_DOCGEN_CLIENT_ID`: Box DocGen app client ID
   - `BOX_DOCGEN_CLIENT_SECRET`: Box DocGen app client secret
   - `BOX_DOCGEN_TEMPLATE_ID`: Your DocGen template ID
   - `BOX_BLOG_AGENT_ID`: Box AI Studio Agent ID for writing blogs
   - `BOX_TWEET_AGENT_ID`: Box AI Studio Agent ID for X tweets
   - `BOX_LINKEDIN_AGENT_ID`: Box AI Studio Agent ID for LinkedIn posts
   - `BOX_YOUTUBE_AGENT_ID`: Box AI Studio Agent ID for Youtube descriptions
   - `BOX_AI_FILE_ID`: File ID for Box AI context
   - `BOX_METADATA_TEMPLATE_KEY`: Metadata template key

## Deployment

1. **Synthesize CloudFormation template:**
   ```bash
   cdk synth
   ```

2. **Deploy to AWS:**
   ```bash
   cdk deploy
   ```

3. **Configure Box Skills webhook:**
   - Copy the API Gateway URL from CDK output
   - Add `/skill` to the URL
   - Configure this as your Box Skills webhook endpoint

## Testing

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=lambdas --cov-report=html
```

## Monitoring

- **CloudWatch Logs**: Lambda execution logs
- **CloudWatch Alarms**: Error rate monitoring for all components
- **Dead Letter Queue**: Failed job investigation
- **CloudTrail**: Complete audit trail of all AWS API calls

## Security Features

- VPC isolation for internal processing
- Secrets Manager for credential storage
- Minimal IAM permissions following least privilege
- Encrypted S3 buckets with versioning
- CORS restricted to Box domains only
- Webhook signature validation

## CDK Commands

- `cdk ls` - List all stacks
- `cdk synth` - Synthesize CloudFormation template
- `cdk deploy` - Deploy stack to AWS
- `cdk diff` - Compare deployed stack with current state
- `cdk destroy` - Remove all AWS resources

## Troubleshooting

- Check CloudWatch logs for Lambda errors
- Monitor SQS dead letter queue for failed jobs
- Verify Box webhook signature validation
- Ensure all Box AI agents are properly configured
- Confirm DocGen template exists and is accessible

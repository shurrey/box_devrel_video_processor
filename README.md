
# Box DevRel Video Processor

An automated video processing pipeline that transforms uploaded videos into comprehensive social media content packages using AWS services and Box AI.

## Overview

This Box Skill automatically processes video/audio files uploaded to configured Box folders by:

1. **Transcription**: Downloads media files, uploads to S3, and uses AWS Transcribe to generate SRT subtitles
2. **AI Analysis**: Leverages Box AI to extract metadata and generate social media content
3. **Content Generation**: Creates YouTube descriptions, LinkedIn posts, X (Twitter) posts, and blog content
4. **Thumbnail Generation**: Extracts random video frames and creates professional thumbnails with AI-powered background removal
5. **Document Creation**: Uses Box DocGen to compile everything into a comprehensive document
6. **Cleanup**: Automatically removes temporary files after processing

## Architecture

- **API Gateway**: Receives Box webhook events
- **Lambda Functions**: 
  - Skill Lambda: Validates webhooks and queues jobs
  - Transcribe Lambda: Handles video download and transcription
  - Process Lambda: Container image function with ML libraries for content generation, thumbnail creation, and DocGen
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

## Features

### Thumbnail Generation
- **AI-Powered Background Removal**: Uses rembg with ONNX runtime for professional thumbnail creation
- **Smart Frame Extraction**: Randomly selects frames from first 10 seconds of video
- **Professional Enhancement**: Applies contrast, sharpness, and color adjustments
- **Multiple Thumbnails**: Generates 10 thumbnail variations per video
- **Organized Storage**: Creates dedicated "thumbnails" folder in Box

### Content Generation
- **Multi-Platform Content**: YouTube descriptions, LinkedIn posts, X tweets, and blog posts
- **Metadata Extraction**: Automatically extracts topic, author, technologies, and tags
- **Timestamped Transcripts**: Creates formatted transcripts with timestamps
- **Professional Documents**: Compiles everything into structured DocGen documents

## Security Features

### Network Security
- **VPC Isolation**: Lambda functions run in private VPC subnets
- **NAT Gateway**: Secure outbound internet access for API calls
- **Security Groups**: Restrictive inbound/outbound rules
- **Private Subnets**: No direct internet access for processing functions

### Data Protection
- **Encrypted S3 Buckets**: Server-side encryption with versioning enabled
- **Secrets Manager**: Secure storage of Box API credentials and keys
- **Temporary File Cleanup**: Automatic deletion of processed files
- **In-Transit Encryption**: HTTPS/TLS for all API communications

### Access Control
- **Minimal IAM Permissions**: Least privilege principle for all roles
- **Resource-Based Policies**: Specific permissions per Lambda function
- **Cross-Account Protection**: Prevents unauthorized access
- **Service-Linked Roles**: AWS-managed permissions where applicable

### Authentication & Authorization
- **Webhook Signature Validation**: HMAC-SHA256 verification of Box webhooks
- **Box OAuth**: Secure token-based authentication
- **Client Credentials Grant**: Server-to-server authentication
- **API Key Rotation**: Support for primary/secondary key rotation

### Monitoring & Auditing
- **CloudTrail Logging**: Complete audit trail of all AWS API calls
- **CloudWatch Alarms**: Real-time monitoring and alerting
- **Dead Letter Queue**: Failed job tracking and investigation
- **Structured Logging**: Comprehensive application logs

### Application Security
- **CORS Restrictions**: API Gateway limited to Box domains only
- **Input Validation**: Webhook payload verification
- **Error Handling**: Secure error messages without sensitive data exposure
- **Container Security**: Read-only filesystem with minimal attack surface

## CDK Commands

- `cdk ls` - List all stacks
- `cdk synth` - Synthesize CloudFormation template
- `cdk deploy` - Deploy stack to AWS
- `cdk diff` - Compare deployed stack with current state
- `cdk destroy` - Remove all AWS resources

## Technical Implementation

### Container Image Lambda
- **Process Lambda** uses Docker container for ML dependencies (rembg, onnxruntime, OpenCV)
- **Platform**: Built for linux/amd64 architecture for Lambda compatibility
- **Caching**: Optimized environment variables to handle read-only filesystem
- **Memory**: 10GB memory allocation for ML processing

### ML Libraries
- **rembg**: AI background removal using U²-Net models
- **onnxruntime**: Optimized inference engine for neural networks
- **OpenCV**: Computer vision operations for video frame extraction
- **Pillow**: Image processing and enhancement

### Error Handling
- **Dead Letter Queue**: Failed jobs with 3 retry attempts
- **CloudWatch Alarms**: Monitoring for all Lambda functions
- **Graceful Degradation**: Continues processing even if thumbnail generation fails

## Troubleshooting

- Check CloudWatch logs for Lambda errors
- Monitor SQS dead letter queue for failed jobs
- Verify Box webhook signature validation
- Ensure all Box AI agents are properly configured
- Confirm DocGen template exists and is accessible
- **Container Issues**: Check Docker build logs for ML library compilation errors
- **Thumbnail Failures**: Verify video format compatibility and memory allocation

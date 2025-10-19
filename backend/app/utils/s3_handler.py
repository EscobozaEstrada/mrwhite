import boto3
import os
from botocore.exceptions import ClientError, NoCredentialsError
from flask import current_app
import uuid
from urllib.parse import urlparse
import logging

# Set up logging
logger = logging.getLogger(__name__)

# AWS S3 configuration - USE ENVIRONMENT VARIABLES FOR SECURITY
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')  # Standard AWS env var name
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')  # Standard AWS env var name
AWS_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
AWS_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'master-white-project')

def get_s3_client():
    """Initialize and return an S3 client with proper error handling"""
    if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
        raise ValueError(
            "AWS credentials not found. Please set the following environment variables:\n"
            "- AWS_ACCESS_KEY_ID\n"
            "- AWS_SECRET_ACCESS_KEY\n"
            "- AWS_DEFAULT_REGION (optional, defaults to us-east-1)\n"
            "- S3_BUCKET_NAME (optional, defaults to master-white-project)"
        )
    
    try:
        return boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )
    except Exception as e:
        logger.error(f"Failed to create S3 client: {str(e)}")
        raise

def get_s3_url(object_name):
    """Generate an S3 URL for an object using the correct regional format
    
    Args:
        object_name (str): S3 object name
        
    Returns:
        str: S3 URL
    """
    # Use regional URL format for better performance and compatibility
    return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{object_name}"

def test_s3_connection():
    """Test S3 connection and bucket access
    
    Returns:
        tuple: (success (bool), message (str))
    """
    try:
        s3_client = get_s3_client()
        
        # Test bucket access
        s3_client.head_bucket(Bucket=AWS_BUCKET_NAME)
        
        # Test list objects permission
        response = s3_client.list_objects_v2(Bucket=AWS_BUCKET_NAME, MaxKeys=1)
        
        logger.info(f"✅ S3 connection successful - Bucket: {AWS_BUCKET_NAME}, Region: {AWS_REGION}")
        return True, f"S3 connection successful to bucket {AWS_BUCKET_NAME}"
        
    except NoCredentialsError:
        logger.error("❌ AWS credentials not found")
        return False, "AWS credentials not found or invalid"
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            logger.error(f"❌ Bucket {AWS_BUCKET_NAME} not found")
            return False, f"Bucket {AWS_BUCKET_NAME} not found"
        elif error_code == '403':
            logger.error(f"❌ Access denied to bucket {AWS_BUCKET_NAME}")
            return False, f"Access denied to bucket {AWS_BUCKET_NAME}"
        else:
            logger.error(f"❌ S3 error: {str(e)}")
            return False, f"S3 error: {str(e)}"
    except Exception as e:
        logger.error(f"❌ Unexpected S3 error: {str(e)}")
        return False, f"Unexpected S3 error: {str(e)}"

def upload_file_to_s3(file_path, object_name=None, content_type=None):
    """Upload a file to an S3 bucket
    
    Args:
        file_path (str): Path to the file to upload
        object_name (str): S3 object name. If not specified, file_name from file_path is used
        content_type (str): Content type of the file
        
    Returns:
        tuple: (success (bool), message (str), s3_url (str))
    """
    logger.info(f"🚀 Starting S3 upload: {file_path} -> {object_name}")
    
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_path)
    
    # Ensure object_name doesn't start with '/'
    object_name = object_name.lstrip('/')
    
    try:
        # Get the S3 client
        s3_client = get_s3_client()
        
        # Set content type and other metadata
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        # Set cache control for images
        if content_type and content_type.startswith('image/'):
            extra_args['CacheControl'] = 'max-age=86400'  # 24 hours
        
        # Upload the file
        logger.info(f"📤 Uploading to bucket: {AWS_BUCKET_NAME}, key: {object_name}")
        s3_client.upload_file(
            file_path, 
            AWS_BUCKET_NAME, 
            object_name,
            ExtraArgs=extra_args
        )
        
        # Generate the URL for the uploaded file using regional format
        s3_url = get_s3_url(object_name)
        
        logger.info(f"✅ S3 upload successful: {s3_url}")
        return True, f"File uploaded successfully to S3", s3_url
    
    except NoCredentialsError:
        logger.error("❌ AWS credentials not found")
        return False, "AWS credentials not found or invalid", None
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"❌ S3 ClientError: {error_code} - {error_message}")
        return False, f"S3 upload failed: {error_code} - {error_message}", None
    except FileNotFoundError:
        logger.error(f"❌ File not found: {file_path}")
        return False, f"File not found: {file_path}", None
    except Exception as e:
        logger.error(f"❌ Unexpected error uploading to S3: {str(e)}")
        return False, f"Unexpected error uploading to S3: {str(e)}", None

def check_if_bucket_exists():
    """Check if the configured S3 bucket exists
    
    Returns:
        bool: True if bucket exists, False otherwise
    """
    s3_client = get_s3_client()
    try:
        s3_client.head_bucket(Bucket=AWS_BUCKET_NAME)
        return True
    except ClientError:
        return False

def create_bucket_if_not_exists():
    """Create the S3 bucket if it doesn't exist
    
    Returns:
        tuple: (success (bool), message (str))
    """
    if check_if_bucket_exists():
        return True, f"Bucket {AWS_BUCKET_NAME} already exists"
    
    s3_client = get_s3_client()
    try:
        # Create the bucket
        if AWS_REGION == 'us-east-1':
            # us-east-1 requires special handling
            s3_client.create_bucket(Bucket=AWS_BUCKET_NAME)
        else:
            s3_client.create_bucket(
                Bucket=AWS_BUCKET_NAME,
                CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
            )
        
        # Set bucket policy to allow public read access
        bucket_policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Sid': 'PublicReadGetObject',
                'Effect': 'Allow',
                'Principal': '*',
                'Action': 's3:GetObject',
                'Resource': f'arn:aws:s3:::{AWS_BUCKET_NAME}/*'
            }]
        }
        
        # Convert policy to JSON string
        bucket_policy_string = str(bucket_policy).replace("'", '"')
        
        # Set the policy
        s3_client.put_bucket_policy(
            Bucket=AWS_BUCKET_NAME,
            Policy=bucket_policy_string
        )
        
        return True, f"Bucket {AWS_BUCKET_NAME} created successfully"
    
    except ClientError as e:
        return False, f"Error creating bucket: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error creating bucket: {str(e)}"

def delete_file_from_s3(object_name):
    """Delete a file from the S3 bucket
    
    Args:
        object_name (str): S3 object name
        
    Returns:
        tuple: (success (bool), message (str))
    """
    s3_client = get_s3_client()
    
    try:
        # If the object_name is a full URL, extract just the key
        if object_name.startswith('http'):
            parsed_url = urlparse(object_name)
            path_parts = parsed_url.path.strip('/').split('/')
            object_name = '/'.join(path_parts)
        
        s3_client.delete_object(
            Bucket=AWS_BUCKET_NAME,
            Key=object_name
        )
        
        return True, f"File {object_name} deleted successfully"
    
    except ClientError as e:
        return False, f"Error deleting file from S3: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error deleting file from S3: {str(e)}" 
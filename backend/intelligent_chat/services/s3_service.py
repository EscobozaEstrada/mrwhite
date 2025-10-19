"""
S3 Service for uploading dog images and documents
"""
import logging
import base64
import uuid
from typing import Tuple
import boto3
from botocore.exceptions import ClientError
from config.settings import settings

logger = logging.getLogger(__name__)


class S3Service:
    """Service for uploading files to S3"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket_name = settings.S3_BUCKET_NAME
    
    async def upload_dog_image(
        self,
        image_data: str,
        user_id: int,
        dog_name: str
    ) -> Tuple[str, str]:
        """
        Upload dog image to S3
        
        Args:
            image_data: Base64 encoded image (with or without data:image prefix)
            user_id: User ID for organizing files
            dog_name: Dog name for file naming
        
        Returns:
            Tuple of (s3_url, image_data_without_prefix)
        """
        try:
            # Remove data URL prefix if present and extract content type
            content_type = "image/jpeg"  # default
            if image_data.startswith('data:image'):
                # Extract content type
                prefix, image_data = image_data.split(',', 1)
                if 'png' in prefix:
                    content_type = "image/png"
                elif 'webp' in prefix:
                    content_type = "image/webp"
                elif 'gif' in prefix:
                    content_type = "image/gif"
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            
            # Generate unique filename
            file_extension = content_type.split('/')[-1]
            filename = f"dog-images/{user_id}/{dog_name.replace(' ', '_')}_{uuid.uuid4().hex[:8]}.{file_extension}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=image_bytes,
                ContentType=content_type,
                ACL='private'  # Keep images private
            )
            
            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{filename}"
            
            logger.info(f"✅ Uploaded dog image to S3: {filename}")
            return s3_url, image_data
            
        except ClientError as e:
            logger.error(f"❌ S3 upload failed: {str(e)}")
            raise Exception(f"Failed to upload image to S3: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Image upload error: {str(e)}")
            raise Exception(f"Failed to process image: {str(e)}")
    
    async def upload_file(
        self,
        file_content: bytes,
        file_key: str,
        content_type: str
    ) -> str:
        """
        Upload any file to S3 (generic method for documents)
        
        Args:
            file_content: File bytes
            file_key: S3 key (full path)
            content_type: MIME type
        
        Returns:
            S3 URL
        """
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_content,
                ContentType=content_type,
                ACL='private'
            )
            
            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{file_key}"
            
            logger.info(f"✅ Uploaded file to S3: {file_key}")
            return s3_url
            
        except ClientError as e:
            logger.error(f"❌ S3 upload failed: {str(e)}")
            raise Exception(f"Failed to upload file to S3: {str(e)}")
        except Exception as e:
            logger.error(f"❌ File upload error: {str(e)}")
            raise Exception(f"Failed to process file: {str(e)}")
    
    async def upload_vet_report(
        self,
        file_data: bytes,
        user_id: int,
        dog_name: str,
        filename: str
    ) -> str:
        """
        Upload vet report to S3
        
        Args:
            file_data: File bytes
            user_id: User ID
            dog_name: Dog name
            filename: Original filename
        
        Returns:
            S3 URL
        """
        try:
            # Determine content type
            content_type = "application/pdf"
            if filename.lower().endswith(('.jpg', '.jpeg')):
                content_type = "image/jpeg"
            elif filename.lower().endswith('.png'):
                content_type = "image/png"
            
            # Generate unique filename
            file_extension = filename.split('.')[-1]
            s3_filename = f"vet-reports/{user_id}/{dog_name.replace(' ', '_')}_{uuid.uuid4().hex[:8]}.{file_extension}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_filename,
                Body=file_data,
                ContentType=content_type,
                ACL='private'
            )
            
            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_filename}"
            
            logger.info(f"✅ Uploaded vet report to S3: {s3_filename}")
            return s3_url
            
        except Exception as e:
            logger.error(f"❌ Vet report upload failed: {str(e)}")
            raise Exception(f"Failed to upload vet report: {str(e)}")


# Singleton instance
s3_service = S3Service()

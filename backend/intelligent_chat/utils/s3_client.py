"""
S3 Client for file storage operations
"""
import os
import logging
from typing import BinaryIO, Optional
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

from config.settings import settings

logger = logging.getLogger(__name__)


class S3Client:
    """AWS S3 client for document storage"""
    
    def __init__(self):
        """Initialize S3 client"""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME
        self.prefix = settings.S3_INTELLIGENT_CHAT_PREFIX
    
    def generate_s3_key(self, user_id: int, filename: str, content_type: str = "document") -> str:
        """
        Generate S3 key for file
        
        Args:
            user_id: User ID
            filename: Original filename
            content_type: Type of content (document, vet_report, etc.)
        
        Returns:
            S3 key path
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = filename.replace(" ", "_")
        
        return f"{self.prefix}/{content_type}/user_{user_id}/{timestamp}_{safe_filename}"
    
    async def upload_file(
        self,
        file: BinaryIO,
        s3_key: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload file to S3
        
        Args:
            file: File-like object
            s3_key: S3 key path
            content_type: MIME type
        
        Returns:
            S3 URL
        """
        try:
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            logger.info(f"✅ File uploaded to S3: {s3_key}")
            
            return s3_url
            
        except ClientError as e:
            logger.error(f"❌ S3 upload failed: {str(e)}")
            raise Exception(f"Failed to upload file to S3: {str(e)}")
    
    async def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate presigned URL for temporary access
        
        Args:
            s3_key: S3 key path
            expiration: URL expiration time in seconds (default 1 hour)
        
        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            
            return url
            
        except ClientError as e:
            logger.error(f"❌ Failed to generate presigned URL: {str(e)}")
            raise Exception(f"Failed to generate presigned URL: {str(e)}")
    
    async def delete_file(self, s3_key: str) -> bool:
        """
        Delete file from S3
        
        Args:
            s3_key: S3 key path
        
        Returns:
            True if successful
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"✅ File deleted from S3: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"❌ S3 delete failed: {str(e)}")
            return False
    
    async def download_file(self, s3_key: str) -> bytes:
        """
        Download file from S3
        
        Args:
            s3_key: S3 key path
        
        Returns:
            File content as bytes
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            content = response['Body'].read()
            logger.info(f"✅ File downloaded from S3: {s3_key}")
            
            return content
            
        except ClientError as e:
            logger.error(f"❌ S3 download failed: {str(e)}")
            raise Exception(f"Failed to download file from S3: {str(e)}")
    
    async def file_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3
        
        Args:
            s3_key: S3 key path
        
        Returns:
            True if file exists
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
            
        except ClientError:
            return False







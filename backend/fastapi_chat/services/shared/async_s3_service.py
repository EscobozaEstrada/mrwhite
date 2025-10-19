"""
AWS S3 Document Storage Service
Handles secure document storage and retrieval for knowledge base sources
"""

import os
import logging
import json
import hashlib
import asyncio
from typing import Dict, List, Any, Optional, BinaryIO
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import aioboto3
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class AsyncS3Service:
    """
    Async S3 service for document storage and knowledge base management
    Provides secure, scalable document storage with automated lifecycle management
    """
    
    def __init__(self):
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.documents_bucket = os.getenv("S3_DOCUMENTS_BUCKET", "mr-white-documents")
        self.knowledge_bucket = os.getenv("S3_KNOWLEDGE_BUCKET", "mr-white-knowledge-base")
        self.temp_bucket = os.getenv("S3_TEMP_BUCKET", "mr-white-temp-uploads")
        
        # Session will be created in async context
        self.session = None
        self.s3 = None
        
        # Sync client for non-async operations
        self.s3_client = boto3.client('s3', region_name=self.aws_region)
        
        # Performance tracking
        self.stats = {
            "total_uploads": 0,
            "successful_uploads": 0,
            "failed_uploads": 0,
            "total_downloads": 0,
            "successful_downloads": 0,
            "total_storage_bytes": 0,
            "average_upload_time": 0.0
        }
        
        # Document type mappings
        self.content_types = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.md': 'text/markdown',
            '.json': 'application/json'
        }
        
        logger.info(f"✅ S3 service initialized for region: {self.aws_region}")
    
    async def __aenter__(self):
        """Initialize async S3 session"""
        if not self.session:
            self.session = aioboto3.Session()
        if not self.s3:
            # Create async S3 client context manager
            self.s3_client = self.session.client('s3', region_name=self.aws_region)
            self.s3 = await self.s3_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up S3 session"""
        if hasattr(self, 's3_client') and self.s3_client:
            await self.s3_client.__aexit__(exc_type, exc_val, exc_tb)
            self.s3 = None
            self.s3_client = None
        # aioboto3.Session doesn't need explicit cleanup
    
    # ==================== BUCKET MANAGEMENT ====================
    
    async def ensure_buckets_exist(self) -> bool:
        """Ensure all required S3 buckets exist"""
        try:
            # Ensure we have a valid S3 client
            if not self.s3:
                logger.error("S3 client not initialized. Use 'async with' context manager.")
                return False
                
            buckets_to_create = [
                (self.documents_bucket, "User documents storage"),
                (self.knowledge_bucket, "Knowledge base documents"),
                (self.temp_bucket, "Temporary file uploads")
            ]
            
            for bucket_name, description in buckets_to_create:
                await self._ensure_bucket_exists(bucket_name, description)
            
            logger.info("✅ All S3 buckets verified/created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to ensure buckets exist: {e}")
            return False
    
    async def _ensure_bucket_exists(self, bucket_name: str, description: str):
        """Create bucket if it doesn't exist"""
        try:
            # Ensure we have a valid S3 client
            if not self.s3:
                logger.error("S3 client not initialized. Use 'async with' context manager.")
                return False
                
            await self.s3.head_bucket(Bucket=bucket_name)
            logger.info(f"✅ Bucket {bucket_name} exists")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Create bucket
                create_config = {}
                if self.aws_region != 'us-east-1':
                    create_config['CreateBucketConfiguration'] = {
                        'LocationConstraint': self.aws_region
                    }
                
                await self.s3.create_bucket(
                    Bucket=bucket_name,
                    **create_config
                )
                
                # Set bucket policies and lifecycle
                await self._setup_bucket_policies(bucket_name)
                await self._setup_bucket_lifecycle(bucket_name)
                
                logger.info(f"✅ Created bucket: {bucket_name}")
            else:
                raise
    
    async def _setup_bucket_policies(self, bucket_name: str):
        """Set up bucket policies for security"""
        try:
            # Basic bucket policy for secure access
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "DenyInsecureConnections",
                        "Effect": "Deny",
                        "Principal": "*",
                        "Action": "s3:*",
                        "Resource": [
                            f"arn:aws:s3:::{bucket_name}",
                            f"arn:aws:s3:::{bucket_name}/*"
                        ],
                        "Condition": {
                            "Bool": {
                                "aws:SecureTransport": "false"
                            }
                        }
                    }
                ]
            }
            
            await self.s3.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(policy)
            )
            
            # Enable versioning
            await self.s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # Enable server-side encryption
            await self.s3.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }
                    ]
                }
            )
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to set bucket policies for {bucket_name}: {e}")
    
    async def _setup_bucket_lifecycle(self, bucket_name: str):
        """Set up lifecycle policies for cost optimization"""
        try:
            # Different policies for different bucket types
            if bucket_name == self.temp_bucket:
                # Temp files deleted after 7 days
                lifecycle_config = {
                    'Rules': [
                        {
                            'ID': 'DeleteTempFiles',
                            'Status': 'Enabled',
                            'Expiration': {'Days': 7},
                            'Filter': {'Prefix': 'temp/'}
                        }
                    ]
                }
            else:
                # Standard storage optimization
                lifecycle_config = {
                    'Rules': [
                        {
                            'ID': 'StorageOptimization',
                            'Status': 'Enabled',
                            'Transitions': [
                                {
                                    'Days': 30,
                                    'StorageClass': 'STANDARD_IA'
                                },
                                {
                                    'Days': 90,
                                    'StorageClass': 'GLACIER'
                                }
                            ],
                            'Filter': {}
                        }
                    ]
                }
            
            await self.s3.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration=lifecycle_config
            )
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to set lifecycle policies for {bucket_name}: {e}")
    
    # ==================== DOCUMENT UPLOAD ====================
    
    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        user_id: int,
        document_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload a document to S3"""
        try:
            if not self.s3:
                await self.__aenter__()
            
            # Generate S3 key
            file_hash = hashlib.md5(file_content).hexdigest()
            timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
            s3_key = f"users/{user_id}/{document_type}/{timestamp}/{file_hash}_{filename}"
            
            # Determine content type
            content_type = self._get_content_type(filename)
            
            # Prepare metadata
            upload_metadata = {
                'user_id': str(user_id),
                'original_filename': filename,
                'document_type': document_type,
                'upload_timestamp': datetime.now(timezone.utc).isoformat(),
                'file_hash': file_hash,
                'file_size': str(len(file_content))
            }
            
            if metadata:
                upload_metadata.update({k: str(v) for k, v in metadata.items()})
            
            # Upload to S3
            await self.s3.put_object(
                Bucket=self.documents_bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata=upload_metadata,
                ServerSideEncryption='AES256'
            )
            
            # Generate direct S3 URL (permanent, no expiration)
            download_url = f"https://{self.documents_bucket}.s3.{self.aws_region}.amazonaws.com/{s3_key}"
            
            self.stats["successful_uploads"] += 1
            self.stats["total_storage_bytes"] += len(file_content)
            
            logger.info(f"✅ Uploaded document {filename} for user {user_id}")
            
            return {
                "success": True,
                "s3_bucket": self.documents_bucket,
                "s3_key": s3_key,
                "download_url": download_url,
                "file_size": len(file_content),
                "content_type": content_type,
                "metadata": upload_metadata
            }
            
        except Exception as e:
            self.stats["failed_uploads"] += 1
            logger.error(f"❌ Failed to upload document {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def upload_to_knowledge_base(
        self,
        file_content: bytes,
        filename: str,
        knowledge_category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload document to knowledge base bucket"""
        try:
            if not self.s3:
                await self.__aenter__()
            
            # Generate S3 key for knowledge base
            file_hash = hashlib.md5(file_content).hexdigest()
            s3_key = f"documents/{knowledge_category}/{file_hash}_{filename}"
            
            # Determine content type
            content_type = self._get_content_type(filename)
            
            # Prepare metadata
            upload_metadata = {
                'original_filename': filename,
                'knowledge_category': knowledge_category,
                'upload_timestamp': datetime.now(timezone.utc).isoformat(),
                'file_hash': file_hash,
                'file_size': str(len(file_content)),
                'indexed': 'false'  # Will be updated after Bedrock ingestion
            }
            
            if metadata:
                upload_metadata.update({k: str(v) for k, v in metadata.items()})
            
            # Upload to knowledge base bucket
            await self.s3.put_object(
                Bucket=self.knowledge_bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata=upload_metadata,
                ServerSideEncryption='AES256'
            )
            
            self.stats["successful_uploads"] += 1
            
            logger.info(f"✅ Uploaded {filename} to knowledge base")
            
            return {
                "success": True,
                "s3_bucket": self.knowledge_bucket,
                "s3_key": s3_key,
                "content_type": content_type,
                "metadata": upload_metadata
            }
            
        except Exception as e:
            self.stats["failed_uploads"] += 1
            logger.error(f"❌ Failed to upload to knowledge base {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension"""
        import os
        ext = os.path.splitext(filename)[1].lower()
        return self.content_types.get(ext, 'application/octet-stream')
    
    # ==================== DOCUMENT RETRIEVAL ====================
    
    async def download_document(
        self,
        s3_bucket: str,
        s3_key: str
    ) -> Optional[Dict[str, Any]]:
        """Download a document from S3"""
        try:
            if not self.s3:
                await self.__aenter__()
            
            response = await self.s3.get_object(
                Bucket=s3_bucket,
                Key=s3_key
            )
            
            content = await response['Body'].read()
            
            self.stats["successful_downloads"] += 1
            
            return {
                "success": True,
                "content": content,
                "content_type": response.get('ContentType'),
                "metadata": response.get('Metadata', {}),
                "last_modified": response.get('LastModified')
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to download document {s3_key}: {e}")
            return None
    
    async def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
        method: str = 'get_object'
    ) -> str:
        """Generate presigned URL for secure access"""
        try:
            if not self.s3:
                await self.__aenter__()
            
            url = await self.s3.generate_presigned_url(
                method,
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in
            )
            
            return url
            
        except Exception as e:
            logger.error(f"❌ Failed to generate presigned URL: {e}")
            return ""
    
    async def list_user_documents(
        self,
        user_id: int,
        document_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List documents for a user"""
        try:
            if not self.s3:
                await self.__aenter__()
            
            prefix = f"users/{user_id}/"
            if document_type:
                prefix += f"{document_type}/"
            
            response = await self.s3.list_objects_v2(
                Bucket=self.documents_bucket,
                Prefix=prefix,
                MaxKeys=limit
            )
            
            documents = []
            for obj in response.get('Contents', []):
                # Get metadata
                head_response = await self.s3.head_object(
                    Bucket=self.documents_bucket,
                    Key=obj['Key']
                )
                
                documents.append({
                    "s3_key": obj['Key'],
                    "filename": head_response.get('Metadata', {}).get('original_filename'),
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'],
                    "content_type": head_response.get('ContentType'),
                    "metadata": head_response.get('Metadata', {})
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ Failed to list documents for user {user_id}: {e}")
            return []
    
    # ==================== DOCUMENT MANAGEMENT ====================
    
    async def delete_document(
        self,
        s3_bucket: str,
        s3_key: str
    ) -> bool:
        """Delete a document from S3"""
        try:
            if not self.s3:
                await self.__aenter__()
            
            await self.s3.delete_object(
                Bucket=s3_bucket,
                Key=s3_key
            )
            
            logger.info(f"✅ Deleted document {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete document {s3_key}: {e}")
            return False
    
    async def copy_to_knowledge_base(
        self,
        source_bucket: str,
        source_key: str,
        knowledge_category: str = "user_uploads"
    ) -> bool:
        """Copy document from user storage to knowledge base"""
        try:
            if not self.s3:
                await self.__aenter__()
            
            # Generate new key for knowledge base
            filename = source_key.split('/')[-1]
            dest_key = f"documents/{knowledge_category}/{filename}"
            
            # Copy object
            await self.s3.copy_object(
                CopySource={'Bucket': source_bucket, 'Key': source_key},
                Bucket=self.knowledge_bucket,
                Key=dest_key
            )
            
            logger.info(f"✅ Copied {source_key} to knowledge base")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to copy to knowledge base: {e}")
            return False
    
    # ==================== PERFORMANCE & STATS ====================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get service performance statistics"""
        return {
            **self.stats,
            "buckets": {
                "documents": self.documents_bucket,
                "knowledge": self.knowledge_bucket,
                "temp": self.temp_bucket
            },
            "region": self.aws_region
        }
    
    async def upload_image_to_s3(
        self,
        file_content: bytes,
        filename: str,
        user_id: int,
        content_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        """
        Upload image to S3 with proper path structure for gallery
        
        Args:
            file_content: Raw image bytes
            filename: Unique filename
            user_id: User ID for folder organization
            content_type: MIME type of the image
            
        Returns:
            Dictionary with upload result
        """
        try:
            if not self.s3:
                await self.__aenter__()
            
            # Generate S3 key for images (similar to gallery structure)
            s3_key = f"uploads/{user_id}/images/{filename}"
            
            # Prepare metadata
            upload_metadata = {
                'user_id': str(user_id),
                'upload_type': 'gallery_image',
                'content_type': content_type,
                'upload_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Upload to S3
            await self.s3.put_object(
                Bucket=self.documents_bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata=upload_metadata,
                ServerSideEncryption='AES256'
            )
            
            # Generate direct S3 URL
            download_url = f"https://{self.documents_bucket}.s3.{self.aws_region}.amazonaws.com/{s3_key}"
            
            self.stats["successful_uploads"] += 1
            self.stats["total_storage_bytes"] += len(file_content)
            
            logger.info(f"✅ Uploaded image {filename} for user {user_id}")
            
            return {
                "success": True,
                "s3_bucket": self.documents_bucket,
                "s3_key": s3_key,
                "download_url": download_url,
                "file_size": len(file_content),
                "content_type": content_type,
                "metadata": upload_metadata
            }
            
        except Exception as e:
            self.stats["failed_uploads"] += 1
            logger.error(f"❌ Failed to upload image {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def upload_audio_to_s3(
        self, file_content: bytes, filename: str, user_id: int, content_type: str = "audio/mpeg"
    ) -> Dict[str, Any]:
        """
        Upload audio file to S3 with proper path structure for voice messages
        
        Args:
            file_content: Audio file content as bytes
            filename: Name of the audio file
            user_id: ID of the user uploading
            content_type: MIME type of the audio
            
        Returns:
            Dictionary with upload result
        """
        try:
            if not self.s3:
                await self.__aenter__()
            
            # Generate S3 key for audio files
            s3_key = f"uploads/{user_id}/audio/{filename}"
            
            # Prepare metadata
            upload_metadata = {
                'user_id': str(user_id),
                'upload_type': 'voice_message',
                'content_type': content_type,
                'upload_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Upload to S3
            await self.s3.put_object(
                Bucket=self.documents_bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata=upload_metadata,
                ServerSideEncryption='AES256'
            )
            
            # Generate direct S3 URL
            download_url = f"https://{self.documents_bucket}.s3.{self.aws_region}.amazonaws.com/{s3_key}"
            
            self.stats["successful_uploads"] += 1
            logger.info(f"✅ Audio uploaded to S3: {s3_key}")
            
            return {
                "success": True,
                "s3_bucket": self.documents_bucket,
                "s3_key": s3_key,
                "download_url": download_url,
                "file_size": len(file_content),
                "content_type": content_type,
                "metadata": upload_metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Audio upload to S3 failed: {str(e)}")
            self.stats["failed_uploads"] += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.stats = {
            "total_uploads": 0,
            "successful_uploads": 0,
            "failed_uploads": 0,
            "total_downloads": 0,
            "successful_downloads": 0,
            "total_storage_bytes": 0,
            "average_upload_time": 0.0
        }
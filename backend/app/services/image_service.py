"""
Enhanced Image Service for comprehensive image handling

This service provides:
- Image upload and processing
- OpenAI Vision API integration for image analysis
- S3 storage with fallback
- Database storage with metadata
- Knowledge base integration for RAG
- Gallery management functionality
"""

import logging
import os
import uuid
import base64
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime, timezone
from flask import current_app
from werkzeug.datastructures import FileStorage
from PIL import Image as PILImage
import io

from openai import OpenAI
from app.utils.s3_handler import upload_file_to_s3, get_s3_url, delete_file_from_s3
from app.utils.file_handler import extract_and_store
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app import db

logger = logging.getLogger(__name__)

class ImageService:
    """Comprehensive service for image handling and processing"""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        self.allowed_formats = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
        
    def process_image_upload(self, file: FileStorage, user_id: int, 
                           conversation_id: Optional[int] = None,
                           message_id: Optional[int] = None,
                           user_description: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Comprehensive image processing pipeline
        
        Args:
            file: Uploaded image file
            user_id: User ID who uploaded the image
            conversation_id: Optional conversation ID for chat context
            message_id: Optional message ID for chat context
            user_description: Optional user-provided description for the image
            
        Returns:
            Tuple of (success, message, image_data)
        """
        logger.info(f"🖼️  Starting image processing for user {user_id}, file: {file.filename}")
        logger.info(f"📝 Context: conversation_id={conversation_id}, message_id={message_id}")
        if user_description is not None:
            logger.info(f"👤 User description provided: {user_description[:50]}...")
        
        try:
            # Validate image
            logger.info(f"🔍 Validating image: {file.filename}")
            validation_result = self._validate_image(file)
            if not validation_result[0]:
                logger.error(f"❌ Image validation failed: {validation_result[1]}")
                return validation_result[0], validation_result[1], None
            logger.info(f"✅ Image validation passed")
            
            # Generate unique filename
            file_extension = self._get_file_extension(file.filename)
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            logger.info(f"📁 Generated unique filename: {unique_filename}")
            
            # Upload to S3
            logger.info(f"☁️  Uploading to S3...")
            s3_url, s3_key = self._upload_to_s3(file, unique_filename, user_id)
            if not s3_url:
                logger.error(f"❌ S3 upload failed")
                return False, "Failed to upload image to S3", None
            logger.info(f"✅ S3 upload successful: {s3_url}")
            
            # Use user-provided description if available, otherwise get AI description
            description = ""
            analysis_data = {}
            
            # Handle description based on what was provided
            if user_description is not None:
                # User explicitly provided a description (might be empty string or content)
                if user_description.strip():
                    # Non-empty description provided
                    logger.info(f"👤 Using non-empty user-provided description: {user_description[:100]}...")
                    description = user_description
                else:
                    # Empty string explicitly provided - leave description empty
                    logger.info(f"👤 Empty description explicitly provided, skipping AI analysis")
            else:
                # No user description provided, generate AI description
                logger.info(f"🤖 No user description provided, starting OpenAI Vision analysis...")
                analysis_result = self._analyze_image_with_openai(file, s3_url)
                if not analysis_result[0]:
                    logger.warning(f"⚠️  OpenAI analysis failed: {analysis_result[1]}")
                    # Continue without analysis rather than failing completely
                    description = ""
                    analysis_data = {}
                else:
                    description = analysis_result[1]
                    analysis_data = analysis_result[2]
                    logger.info(f"✅ OpenAI analysis successful: {len(description)} characters")
            
            # Get image metadata
            logger.info(f"📊 Extracting image metadata...")
            metadata = self._extract_image_metadata(file)
            logger.info(f"✅ Metadata extracted: {metadata.get('width', 0)}x{metadata.get('height', 0)}")
            
            # Store in database
            logger.info(f"💾 Storing image in database with description: {description[:50]}...")
            image_record = self._store_image_in_database(
                user_id=user_id,
                filename=unique_filename,
                original_filename=file.filename,
                s3_url=s3_url,
                s3_key=s3_key,
                description=description,
                analysis_data=analysis_data,
                metadata=metadata,
                conversation_id=conversation_id,
                message_id=message_id
            )
            
            if not image_record:
                logger.error(f"❌ Failed to store image in database")
                return False, "Failed to store image in database", None
            logger.info(f"✅ Image stored in database with ID: {image_record.id}")
            
            # Add to knowledge base for RAG
            logger.info(f"🧠 Adding to knowledge base...")
            self._add_to_knowledge_base(
                user_id=user_id,
                image_id=image_record.id,
                filename=file.filename,
                description=description,
                s3_url=s3_url,
                analysis_data=analysis_data
            )
            
            # Prepare response data
            response_data = {
                'id': image_record.id,
                'filename': unique_filename,
                'original_filename': file.filename,
                'url': self._generate_frontend_url(s3_url),
                'description': description,
                'analysis': analysis_data,
                'metadata': metadata,
                'uploaded_at': image_record.created_at.isoformat(),
                'file_size': metadata.get('file_size', 0)
            }
            
            logger.info(f"🎉 Successfully processed image {unique_filename} for user {user_id}")
            return True, "Image processed successfully", response_data
            
        except Exception as e:
            logger.error(f"💥 Error processing image upload: {str(e)}")
            return False, f"Error processing image: {str(e)}", None
    
    def _validate_image(self, file: FileStorage) -> Tuple[bool, str]:
        """Validate uploaded image file"""
        try:
            if not file or not file.filename:
                return False, "No file provided"
            
            # Check file extension
            file_extension = self._get_file_extension(file.filename).lower()
            if file_extension not in self.allowed_formats:
                return False, f"Unsupported file format. Allowed: {', '.join(self.allowed_formats)}"
            
            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size > self.max_image_size:
                return False, f"File too large. Maximum size: {self.max_image_size // (1024*1024)}MB"
            
            # Validate it's actually an image
            try:
                image = PILImage.open(file)
                image.verify()
                file.seek(0)  # Reset file pointer after verification
                return True, "Valid image"
            except Exception as e:
                return False, "Invalid image file"
                
        except Exception as e:
            logger.error(f"Error validating image: {str(e)}")
            return False, "Error validating image"
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename (without the dot)"""
        extension = os.path.splitext(filename)[1].lower()
        return extension[1:] if extension.startswith('.') else extension
    
    def _upload_to_s3(self, file: FileStorage, filename: str, user_id: int) -> Tuple[Optional[str], Optional[str]]:
        """Upload image to S3 bucket with local fallback"""
        try:
            # Create S3 key with user folder structure
            s3_key = f"users/{user_id}/images/{filename}"
            
            # Save file temporarily
            temp_path = f"/tmp/{filename}"
            file.save(temp_path)
            
            # Try to upload to S3 first
            try:
                success, message, s3_url = upload_file_to_s3(temp_path, s3_key, file.content_type)
                
                if success:
                    # Clean up temp file
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                    logger.info(f"✅ S3 upload successful: {s3_url}")
                    return s3_url, s3_key
                else:
                    logger.warning(f"⚠️  S3 upload failed: {message}")
                    # Check if it's a permission issue
                    if "AccessDenied" in message or "Forbidden" in message:
                        logger.error("❌ S3 Access Denied - Check IAM permissions for bucket access")
                        logger.error("💡 Solution: Grant s3:PutObject permission to your IAM user")
                    # Fall back to local storage
                    return self._store_image_locally(temp_path, filename, user_id)
                    
            except Exception as s3_error:
                logger.warning(f"⚠️  S3 upload exception: {str(s3_error)}")
                if "AccessDenied" in str(s3_error):
                    logger.error("❌ S3 Access Denied - IAM user lacks bucket permissions")
                # Fall back to local storage
                return self._store_image_locally(temp_path, filename, user_id)
                
        except Exception as e:
            logger.error(f"Error in upload process: {str(e)}")
            return None, None
    
    def _store_image_locally(self, temp_path: str, filename: str, user_id: int) -> Tuple[Optional[str], Optional[str]]:
        """Store image locally as fallback when S3 fails"""
        try:
            # Create local storage directory
            local_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads', 'images', str(user_id))
            os.makedirs(local_dir, exist_ok=True)
            
            # Move file to local storage
            local_path = os.path.join(local_dir, filename)
            
            # Copy file instead of moving to preserve temp file for cleanup
            import shutil
            shutil.copy2(temp_path, local_path)
            
            # Clean up temp file
            try:
                os.remove(temp_path)
            except:
                pass
            
            # Generate local URL
            local_url = f"/uploads/images/{user_id}/{filename}"
            local_key = f"local/users/{user_id}/images/{filename}"
            
            logger.info(f"✅ Local storage successful: {local_url}")
            return local_url, local_key
            
        except Exception as e:
            logger.error(f"Error storing image locally: {str(e)}")
            # Clean up temp file
            try:
                os.remove(temp_path)
            except:
                pass
            return None, None
    
    def _analyze_image_with_openai(self, file: FileStorage, s3_url: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Analyze image using OpenAI Vision API"""
        try:
            # Read and encode image
            file.seek(0)
            image_data = file.read()
            file.seek(0)
            
            # Convert to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare the prompt for comprehensive analysis
            prompt = """Analyze this image in detail and provide a comprehensive description that includes:

1. Main subject/subjects in the image
2. Setting/environment/background
3. Colors, lighting, and mood
4. Any text visible in the image
5. Objects, animals, or people present
6. Activities or actions taking place
7. Style or type of image (photo, artwork, screenshot, etc.)
8. Any notable details or interesting features

Provide a natural, detailed description that would help someone understand what's in the image without seeing it. If this appears to be related to pets, dogs, or animals, please include specific details about breed, size, color, behavior, or health-related observations."""

            # Call OpenAI Vision API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            description = response.choices[0].message.content.strip()
            
            # Extract additional analysis data
            analysis_data = {
                'model_used': 'gpt-4o',
                'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                'total_tokens': response.usage.total_tokens if response.usage else 0,
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                'confidence': 'high'  # Could be enhanced with additional logic
            }
            
            logger.info(f"OpenAI image analysis successful: {len(description)} characters")
            return True, description, analysis_data
            
        except Exception as e:
            logger.error(f"Error analyzing image with OpenAI: {str(e)}")
            return False, f"Analysis failed: {str(e)}", {}
    
    def _extract_image_metadata(self, file: FileStorage) -> Dict[str, Any]:
        """Extract metadata from image file"""
        try:
            file.seek(0)
            
            # Get file size
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
            
            # Get image dimensions and format
            image = PILImage.open(file)
            file.seek(0)
            
            metadata = {
                'file_size': file_size,
                'width': image.width,
                'height': image.height,
                'format': image.format,
                'mode': image.mode,
                'content_type': file.content_type
            }
            
            # Try to get EXIF data
            try:
                exif = image._getexif()
                if exif:
                    metadata['has_exif'] = True
                    # Add specific EXIF data you want to preserve
                else:
                    metadata['has_exif'] = False
            except:
                metadata['has_exif'] = False
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting image metadata: {str(e)}")
            return {'file_size': 0, 'error': str(e)}
    
    def _store_image_in_database(self, user_id: int, filename: str, original_filename: str,
                               s3_url: str, s3_key: str, description: str, analysis_data: Dict,
                               metadata: Dict, conversation_id: Optional[int] = None,
                               message_id: Optional[int] = None):
        """Store image record in database"""
        try:
            from app.models.image import UserImage
            
            image_record = UserImage(
                user_id=user_id,
                filename=filename,
                original_filename=original_filename,
                s3_url=s3_url,
                s3_key=s3_key,
                description=description,
                analysis_data=analysis_data,
                image_metadata=metadata,
                conversation_id=conversation_id,
                message_id=message_id
            )
            
            db.session.add(image_record)
            db.session.commit()
            
            logger.info(f"Stored image record in database: {image_record.id}")
            return image_record
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing image in database: {str(e)}")
            return None
    
    def _add_to_knowledge_base(self, user_id: int, image_id: int, filename: str,
                             description: str, s3_url: str, analysis_data: Dict):
        """Add image and description to user's knowledge base for RAG"""
        try:
            # Create a comprehensive text representation for the knowledge base
            knowledge_text = f"""
Image: {filename}
Description: {description}
URL: {s3_url}
Image ID: {image_id}
Analysis: {analysis_data.get('model_used', 'AI')} provided detailed visual analysis
Uploaded: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

This is a user-uploaded image that can be referenced in future conversations. The AI can describe this image and provide the image URL when relevant to user queries.
"""
            
            # Use existing file handler to add to knowledge base
            # Create a temporary file-like object with the text content
            from io import StringIO
            text_file = StringIO(knowledge_text)
            
            # Add to vector database using existing infrastructure
            success, message = extract_and_store(
                file_content=knowledge_text,
                user_id=user_id,
                filename=f"image_{image_id}_{filename}.txt",
                file_type="image_description"
            )
            
            if success:
                logger.info(f"Added image {image_id} to knowledge base for user {user_id}")
            else:
                logger.warning(f"Failed to add image to knowledge base: {message}")
                
        except Exception as e:
            logger.error(f"Error adding image to knowledge base: {str(e)}")
    
    def get_user_images(self, user_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's uploaded images for gallery (includes both user_images and IC images)"""
        try:
            from app.models.image import UserImage
            from sqlalchemy import text
            
            # Get images from user_images table
            user_images = UserImage.query.filter_by(
                user_id=user_id,
                is_deleted=False
            ).order_by(
                UserImage.display_order.asc(),  # Primary sort by display_order
                UserImage.created_at.desc()     # Secondary sort by creation date
            ).limit(limit).offset(offset).all()
            
            image_list = []
            for image in user_images:
                # Generate proper URL for frontend access
                image_url = self._generate_frontend_url(image.s3_url)
                
                image_data = {
                    'id': image.id,
                    'filename': image.filename,
                    'original_filename': image.original_filename,
                    'url': image_url,
                    'description': image.description,
                    'metadata': image.image_metadata,
                    'uploaded_at': image.created_at.isoformat(),
                    'file_size': image.image_metadata.get('file_size', 0) if image.image_metadata else 0,
                    'width': image.image_metadata.get('width', 0) if image.image_metadata else 0,
                    'height': image.image_metadata.get('height', 0) if image.image_metadata else 0,
                    'display_order': image.display_order,  # Include display_order in the response
                    'source': 'gallery'  # Mark as gallery source
                }
                image_list.append(image_data)
            
            # If we have fewer images than requested, try to get IC images
            if len(image_list) < limit:
                remaining_limit = limit - len(image_list)
                
                # Get IC images that haven't been synced yet
                ic_images_query = text("""
                    SELECT id, filename, file_type, file_size, mime_type,
                           s3_key, s3_url, extracted_text, image_analysis,
                           conversation_id, message_id, created_at, uploaded_at
                    FROM ic_documents
                    WHERE user_id = :user_id
                      AND file_type IN ('jpg', 'jpeg', 'png', 'gif', 'webp', 'image')
                      AND is_deleted = false
                      AND s3_url IS NOT NULL
                      AND s3_url != ''
                      AND NOT EXISTS (
                          SELECT 1 FROM user_images 
                          WHERE user_images.user_id = :user_id 
                            AND user_images.s3_url = ic_documents.s3_url
                            AND user_images.is_deleted = false
                      )
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                
                ic_result = db.session.execute(ic_images_query, {
                    'user_id': user_id,
                    'limit': remaining_limit
                })
                
                for row in ic_result:
                    ic_image_data = {
                        'id': f"ic_{row[0]}",  # Prefix with ic_ to avoid ID conflicts
                        'filename': row[1],
                        'original_filename': row[1],
                        'url': row[6],  # s3_url
                        'description': row[7] or '',  # extracted_text
                        'metadata': {
                            'file_size': row[3] or 0,
                            'format': row[2] or '',
                            'content_type': row[4] or '',
                            'source': 'intelligent_chat',
                            'ic_document_id': row[0],
                            'width': row[8].get('width', 0) if row[8] else 0,
                            'height': row[8].get('height', 0) if row[8] else 0
                        },
                        'uploaded_at': row[11].isoformat() if row[11] else '',
                        'file_size': row[3] or 0,
                        'width': row[8].get('width', 0) if row[8] else 0,
                        'height': row[8].get('height', 0) if row[8] else 0,
                        'display_order': 999,  # IC images at the end
                        'source': 'intelligent_chat'  # Mark as IC source
                    }
                    image_list.append(ic_image_data)
            
            return image_list
            
        except Exception as e:
            logger.error(f"Error getting user images: {str(e)}")
            return []
    
    def _generate_frontend_url(self, stored_url: str) -> str:
        """Generate proper URL for frontend access"""
        try:
            # If it's already a full URL (S3), return as-is
            if stored_url.startswith('http://') or stored_url.startswith('https://'):
                return stored_url
            
            # If it's a local path, generate full backend URL
            if stored_url.startswith('/uploads/images/'):
                # Get the backend base URL from Flask config or environment
                backend_url = os.getenv('BACKEND_BASE_URL')
                return f"{backend_url}{stored_url}"
            
            # Fallback - return as-is
            return stored_url
            
        except Exception as e:
            logger.error(f"Error generating frontend URL: {str(e)}")
            return stored_url
    
    def delete_image(self, user_id: int, image_id: int) -> Tuple[bool, str]:
        """Delete user's image"""
        try:
            from app.models.image import UserImage
            
            image = UserImage.query.filter_by(
                id=image_id,
                user_id=user_id,
                is_deleted=False
            ).first()
            
            if not image:
                return False, "Image not found"
            
            # Mark as deleted in database
            image.is_deleted = True
            image.deleted_at = datetime.now(timezone.utc)
            
            # Optionally delete from S3 (or keep for backup)
            if image.s3_key:
                try:
                    delete_file_from_s3(image.s3_key)
                except Exception as e:
                    logger.warning(f"Failed to delete from S3: {str(e)}")
            
            db.session.commit()
            
            logger.info(f"Deleted image {image_id} for user {user_id}")
            return True, "Image deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting image: {str(e)}")
            return False, f"Error deleting image: {str(e)}"
    
    def get_image_by_id(self, user_id: int, image_id: int) -> Optional[Dict[str, Any]]:
        """Get specific image by ID"""
        try:
            from app.models.image import UserImage
            
            image = UserImage.query.filter_by(
                id=image_id,
                user_id=user_id,
                is_deleted=False
            ).first()
            
            if not image:
                return None
            
            # Generate proper URL for frontend access
            image_url = self._generate_frontend_url(image.s3_url)
            
            return {
                'id': image.id,
                'filename': image.filename,
                'original_filename': image.original_filename,
                'url': image_url,
                'description': image.description,
                'analysis_data': image.analysis_data,
                'metadata': image.image_metadata,
                'uploaded_at': image.created_at.isoformat(),
                'conversation_id': image.conversation_id,
                'message_id': image.message_id
            }
            
        except Exception as e:
            logger.error(f"Error getting image by ID: {str(e)}")
            return None

    def update_image_order(self, user_id: int, image_ids: List[int]) -> Tuple[bool, str]:
        """
        Update the display order of user's images
        
        Args:
            user_id: User ID
            image_ids: List of image IDs in the desired order
            
        Returns:
            Tuple of (success, message)
        """
        try:
            from app.models.image import UserImage
            
            # Verify all images belong to the user
            user_image_ids = set([img.id for img in UserImage.query.filter_by(
                user_id=user_id,
                is_deleted=False
            ).all()])
            
            # Check if all provided IDs belong to the user
            if not all(img_id in user_image_ids for img_id in image_ids):
                return False, "One or more images do not belong to the user"
            
            # Update display_order for each image
            for index, image_id in enumerate(image_ids):
                image = UserImage.query.filter_by(id=image_id, user_id=user_id).first()
                if image:
                    image.display_order = index
            
            db.session.commit()
            logger.info(f"Updated display order for {len(image_ids)} images for user {user_id}")
            
            return True, f"Successfully updated image order"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating image order: {str(e)}")
            return False, f"Failed to update image order: {str(e)}"

    def update_image_description(self, user_id: int, image_id: int, description: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Update an image's description
        
        Args:
            user_id: User ID who owns the image
            image_id: Image ID to update
            description: New description for the image
            
        Returns:
            Tuple of (success, message, image_data)
        """
        try:
            from app.models.image import UserImage
            
            # Get the image
            image = UserImage.query.filter_by(
                id=image_id,
                user_id=user_id,
                is_deleted=False
            ).first()
            
            if not image:
                return False, "Image not found", None
            
            # Update the description
            image.description = description
            image.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Update the knowledge base entry
            self._update_knowledge_base_description(
                user_id=user_id,
                image_id=image_id,
                filename=image.original_filename,
                description=description,
                s3_url=image.s3_url,
                analysis_data=image.analysis_data or {}
            )
            
            # Return updated image data
            image_data = {
                'id': image.id,
                'filename': image.filename,
                'original_filename': image.original_filename,
                'url': self._generate_frontend_url(image.s3_url),
                'description': description,
                'analysis': image.analysis_data,
                'metadata': image.image_metadata,
                'uploaded_at': image.created_at.isoformat(),
                'updated_at': image.updated_at.isoformat(),
                'file_size': image.image_metadata.get('file_size', 0) if image.image_metadata else 0
            }
            
            logger.info(f"✅ Updated description for image {image_id} for user {user_id}")
            return True, "Image description updated successfully", image_data
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating image description: {str(e)}")
            return False, f"Failed to update image description: {str(e)}", None
    
    def _update_knowledge_base_description(self, user_id: int, image_id: int, filename: str,
                                        description: str, s3_url: str, analysis_data: Dict):
        """Update image description in knowledge base for RAG"""
        try:
            # Create a comprehensive text representation for the knowledge base
            knowledge_text = f"""
Image: {filename}
Description: {description}
URL: {s3_url}
Image ID: {image_id}
Analysis: {analysis_data.get('model_used', 'User provided')} description
Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

This is a user-uploaded image that can be referenced in future conversations. The AI can describe this image and provide the image URL when relevant to user queries.
"""
            
            # Use existing file handler to update knowledge base
            from io import StringIO
            text_file = StringIO(knowledge_text)
            
            # Add to vector database using existing infrastructure
            # Note: This will replace the existing entry if it exists
            success, message = extract_and_store(
                file_content=knowledge_text,
                user_id=user_id,
                filename=f"image_{image_id}_{filename}.txt",
                file_type="image_description"
            )
            
            if success:
                logger.info(f"Updated image {image_id} in knowledge base for user {user_id}")
            else:
                logger.warning(f"Failed to update image in knowledge base: {message}")
                
        except Exception as e:
            logger.error(f"Error updating image in knowledge base: {str(e)}")

    def update_image_title(self, user_id: int, image_id: int, title: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Update an image's title
        
        Args:
            user_id: User ID who owns the image
            image_id: Image ID to update
            title: New title for the image
            
        Returns:
            Tuple of (success, message, image_data)
        """
        try:
            from app.models.image import UserImage
            
            # Get the image
            image = UserImage.query.filter_by(
                id=image_id,
                user_id=user_id,
                is_deleted=False
            ).first()
            
            if not image:
                return False, "Image not found", None
            
            # Update the title
            image.title = title
            image.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Return updated image data
            image_data = {
                'id': image.id,
                'filename': image.filename,
                'original_filename': image.original_filename,
                'url': self._generate_frontend_url(image.s3_url),
                'title': title,
                'description': image.description,
                'analysis': image.analysis_data,
                'metadata': image.image_metadata,
                'uploaded_at': image.created_at.isoformat(),
                'updated_at': image.updated_at.isoformat(),
                'file_size': image.image_metadata.get('file_size', 0) if image.image_metadata else 0
            }
            
            logger.info(f"✅ Updated title for image {image_id} for user {user_id}")
            return True, "Image title updated successfully", image_data
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating image title: {str(e)}")
            return False, f"Failed to update image title: {str(e)}", None

# Global instance
image_service = ImageService()
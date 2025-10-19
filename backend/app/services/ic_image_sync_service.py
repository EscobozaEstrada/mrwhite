"""
IC Image Sync Service
Handles synchronization of images from intelligent_chat ic_documents table to user_images table
so that the gallery can display all user images regardless of upload source.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app import db
from app.models.image import UserImage
from intelligent_chat.models.document import Document as ICDocument
from intelligent_chat.models.base import AsyncSessionLocal

logger = logging.getLogger(__name__)


class ICImageSyncService:
    """Service for syncing IC images to user_images table"""
    
    def __init__(self):
        self.logger = logger
    
    def sync_ic_images_to_gallery(self, user_id: int, limit: int = 100) -> Dict[str, Any]:
        """
        Sync images from ic_documents to user_images table for gallery display
        
        Args:
            user_id: User ID to sync images for
            limit: Maximum number of images to process in one batch
            
        Returns:
            Dict with sync results
        """
        try:
            # Get IC images that haven't been synced yet
            ic_images = self._get_unsynced_ic_images(user_id, limit)
            
            if not ic_images:
                return {
                    'success': True,
                    'message': 'No new IC images to sync',
                    'synced_count': 0,
                    'skipped_count': 0
                }
            
            synced_count = 0
            skipped_count = 0
            
            for ic_image in ic_images:
                try:
                    # Check if already synced (by s3_url)
                    existing = UserImage.query.filter_by(
                        user_id=user_id,
                        s3_url=ic_image['s3_url'],
                        is_deleted=False
                    ).first()
                    
                    if existing:
                        self.logger.info(f"Image already synced: {ic_image['filename']}")
                        skipped_count += 1
                        continue
                    
                    # Create new UserImage record
                    user_image = UserImage(
                        user_id=user_id,
                        filename=ic_image['filename'],
                        original_filename=ic_image['filename'],
                        s3_url=ic_image['s3_url'],
                        s3_key=ic_image['s3_key'],
                        description=ic_image.get('extracted_text', ''),
                        analysis_data=ic_image.get('image_analysis', {}),
                        image_metadata=self._extract_image_metadata(ic_image),
                        display_order=0,  # Default order
                        conversation_id=ic_image.get('conversation_id'),
                        message_id=ic_image.get('message_id'),
                        is_deleted=False,
                        created_at=ic_image['created_at'],
                        updated_at=datetime.now(timezone.utc)
                    )
                    
                    db.session.add(user_image)
                    synced_count += 1
                    
                    self.logger.info(f"Synced IC image: {ic_image['filename']} -> user_images table")
                    
                except Exception as e:
                    self.logger.error(f"Failed to sync IC image {ic_image['filename']}: {str(e)}")
                    skipped_count += 1
                    continue
            
            # Commit all changes
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Successfully synced {synced_count} IC images to gallery',
                'synced_count': synced_count,
                'skipped_count': skipped_count,
                'total_processed': len(ic_images)
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"IC image sync failed: {str(e)}")
            return {
                'success': False,
                'message': f'Sync failed: {str(e)}',
                'synced_count': 0,
                'skipped_count': 0
            }
    
    def _get_unsynced_ic_images(self, user_id: int, limit: int) -> List[Dict[str, Any]]:
        """Get IC images that haven't been synced to user_images yet"""
        try:
            # Use raw SQL to query ic_documents table
            query = text("""
                SELECT id, filename, file_type, file_size, mime_type,
                       s3_key, s3_url, extracted_text, image_analysis,
                       conversation_id, message_id, created_at, uploaded_at
                FROM ic_documents
                WHERE user_id = :user_id
                  AND file_type IN ('jpg', 'jpeg', 'png', 'gif', 'webp', 'image')
                  AND is_deleted = false
                  AND s3_url IS NOT NULL
                  AND s3_url != ''
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            result = db.session.execute(query, {
                'user_id': user_id,
                'limit': limit
            })
            
            images = []
            for row in result:
                images.append({
                    'id': row[0],
                    'filename': row[1],
                    'file_type': row[2],
                    'file_size': row[3],
                    'mime_type': row[4],
                    's3_key': row[5],
                    's3_url': row[6],
                    'extracted_text': row[7],
                    'image_analysis': row[8] if row[8] else {},
                    'conversation_id': row[9],
                    'message_id': row[10],
                    'created_at': row[11],
                    'uploaded_at': row[12]
                })
            
            return images
            
        except Exception as e:
            self.logger.error(f"Failed to get unsynced IC images: {str(e)}")
            return []
    
    def _extract_image_metadata(self, ic_image: Dict[str, Any]) -> Dict[str, Any]:
        """Extract image metadata from IC image data"""
        metadata = {
            'file_size': ic_image.get('file_size', 0),
            'format': ic_image.get('file_type', ''),
            'content_type': ic_image.get('mime_type', ''),
            'source': 'intelligent_chat',
            'ic_document_id': ic_image.get('id')
        }
        
        # Add image analysis data if available
        image_analysis = ic_image.get('image_analysis', {})
        if image_analysis:
            if 'width' in image_analysis:
                metadata['width'] = image_analysis['width']
            if 'height' in image_analysis:
                metadata['height'] = image_analysis['height']
            if 'format' in image_analysis:
                metadata['format'] = image_analysis['format']
        
        return metadata
    
    def get_sync_status(self, user_id: int) -> Dict[str, Any]:
        """Get sync status for a user"""
        try:
            # Count IC images
            ic_count_query = text("""
                SELECT COUNT(*) FROM ic_documents
                WHERE user_id = :user_id
                  AND file_type IN ('jpg', 'jpeg', 'png', 'gif', 'webp', 'image')
                  AND is_deleted = false
            """)
            
            ic_count_result = db.session.execute(ic_count_query, {'user_id': user_id})
            ic_count = ic_count_result.scalar()
            
            # Count synced images (user_images with IC source)
            synced_count_query = text("""
                SELECT COUNT(*) FROM user_images
                WHERE user_id = :user_id
                  AND is_deleted = false
                  AND image_metadata->>'source' = 'intelligent_chat'
            """)
            
            synced_count_result = db.session.execute(synced_count_query, {'user_id': user_id})
            synced_count = synced_count_result.scalar()
            
            return {
                'success': True,
                'ic_images_total': ic_count,
                'synced_to_gallery': synced_count,
                'unsynced': ic_count - synced_count,
                'sync_percentage': round((synced_count / ic_count * 100) if ic_count > 0 else 0, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get sync status: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def sync_all_users_ic_images(self, batch_size: int = 50) -> Dict[str, Any]:
        """Sync IC images for all users (admin function)"""
        try:
            # Get all users who have IC images
            users_query = text("""
                SELECT DISTINCT user_id FROM ic_documents
                WHERE file_type IN ('jpg', 'jpeg', 'png', 'gif', 'webp', 'image')
                  AND is_deleted = false
            """)
            
            users_result = db.session.execute(users_query)
            user_ids = [row[0] for row in users_result]
            
            total_synced = 0
            total_skipped = 0
            processed_users = 0
            
            for user_id in user_ids:
                try:
                    result = self.sync_ic_images_to_gallery(user_id, batch_size)
                    if result['success']:
                        total_synced += result['synced_count']
                        total_skipped += result['skipped_count']
                        processed_users += 1
                        
                        self.logger.info(f"Synced user {user_id}: {result['synced_count']} images")
                    
                except Exception as e:
                    self.logger.error(f"Failed to sync user {user_id}: {str(e)}")
                    continue
            
            return {
                'success': True,
                'message': f'Processed {processed_users} users',
                'total_synced': total_synced,
                'total_skipped': total_skipped,
                'processed_users': processed_users
            }
            
        except Exception as e:
            self.logger.error(f"Bulk sync failed: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }

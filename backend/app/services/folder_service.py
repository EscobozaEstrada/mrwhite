"""
Folder Service for managing gallery folders

This service provides:
- Folder creation and management
- Moving images between folders
- Folder metadata operations
"""

import logging
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime, timezone

from app import db
from app.models.folder import Folder
from app.models.image import UserImage

logger = logging.getLogger(__name__)

class FolderService:
    """Service for managing gallery folders"""
    
    def create_folder(self, user_id: int, name: str, description: str = None, 
                    cover_image_id: int = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create a new folder
        
        Args:
            user_id: User ID who owns the folder
            name: Name of the folder
            description: Optional description
            cover_image_id: Optional ID of an image to use as cover
            
        Returns:
            Tuple of (success, message, folder_data)
        """
        try:
            # Validate cover image if provided
            if cover_image_id:
                cover_image = UserImage.query.filter_by(
                    id=cover_image_id,
                    user_id=user_id,
                    is_deleted=False
                ).first()
                
                if not cover_image:
                    return False, "Cover image not found", None
            
            # Create folder
            folder = Folder(
                user_id=user_id,
                name=name,
                description=description,
                cover_image_id=cover_image_id
            )
            
            db.session.add(folder)
            db.session.commit()
            
            logger.info(f"Created folder {folder.id} for user {user_id}")
            return True, "Folder created successfully", folder.to_dict()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating folder: {str(e)}")
            return False, f"Failed to create folder: {str(e)}", None
    
    def update_folder(self, user_id: int, folder_id: int, name: str = None, 
                    description: str = None, cover_image_id: int = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Update a folder's details
        
        Args:
            user_id: User ID who owns the folder
            folder_id: ID of the folder to update
            name: New name (optional)
            description: New description (optional)
            cover_image_id: New cover image ID (optional)
            
        Returns:
            Tuple of (success, message, folder_data)
        """
        try:
            # Get the folder
            folder = Folder.query.filter_by(
                id=folder_id,
                user_id=user_id,
                is_deleted=False
            ).first()
            
            if not folder:
                return False, "Folder not found", None
            
            # Update fields if provided
            if name is not None:
                folder.name = name
                
            if description is not None:
                folder.description = description
                
            if cover_image_id is not None:
                # Validate cover image if provided
                if cover_image_id > 0:
                    cover_image = UserImage.query.filter_by(
                        id=cover_image_id,
                        user_id=user_id,
                        is_deleted=False
                    ).first()
                    
                    if not cover_image:
                        return False, "Cover image not found", None
                    
                    folder.cover_image_id = cover_image_id
                else:
                    # Remove cover image if 0 or negative
                    folder.cover_image_id = None
            
            folder.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            logger.info(f"Updated folder {folder_id} for user {user_id}")
            return True, "Folder updated successfully", folder.to_dict()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating folder: {str(e)}")
            return False, f"Failed to update folder: {str(e)}", None
    
    def delete_folder(self, user_id: int, folder_id: int, delete_images: bool = False) -> Tuple[bool, str]:
        """
        Delete a folder
        
        Args:
            user_id: User ID who owns the folder
            folder_id: ID of the folder to delete
            delete_images: Whether to delete images in the folder or move them to root
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Get the folder
            folder = Folder.query.filter_by(
                id=folder_id,
                user_id=user_id,
                is_deleted=False
            ).first()
            
            if not folder:
                return False, "Folder not found"
            
            # Handle images in the folder
            images = UserImage.query.filter_by(
                folder_id=folder_id,
                user_id=user_id,
                is_deleted=False
            ).all()
            
            if delete_images:
                # Mark all images as deleted
                for image in images:
                    image.is_deleted = True
                    image.deleted_at = datetime.now(timezone.utc)
            else:
                # Move images to root (no folder)
                for image in images:
                    image.folder_id = None
            
            # Mark folder as deleted
            folder.is_deleted = True
            folder.deleted_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            logger.info(f"Deleted folder {folder_id} for user {user_id}")
            return True, "Folder deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting folder: {str(e)}")
            return False, f"Failed to delete folder: {str(e)}"
    
    def get_user_folders(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all folders for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of folder dictionaries
        """
        try:
            folders = Folder.get_user_folders(user_id)
            return [folder.to_dict() for folder in folders]
            
        except Exception as e:
            logger.error(f"Error getting user folders: {str(e)}")
            return []
    
    def get_folder_by_id(self, user_id: int, folder_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific folder by ID
        
        Args:
            user_id: User ID
            folder_id: Folder ID
            
        Returns:
            Folder dictionary or None
        """
        try:
            folder = Folder.get_folder_by_id(user_id, folder_id)
            return folder.to_dict() if folder else None
            
        except Exception as e:
            logger.error(f"Error getting folder by ID: {str(e)}")
            return None
    
    def move_image_to_folder(self, user_id: int, image_id: int, folder_id: Optional[int]) -> Tuple[bool, str]:
        """
        Move an image to a folder or to root
        
        Args:
            user_id: User ID who owns the image
            image_id: ID of the image to move
            folder_id: ID of the destination folder or None for root
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Get the image
            image = UserImage.query.filter_by(
                id=image_id,
                user_id=user_id,
                is_deleted=False
            ).first()
            
            if not image:
                return False, "Image not found"
            
            # If moving to a folder, validate it exists
            if folder_id is not None:
                folder = Folder.query.filter_by(
                    id=folder_id,
                    user_id=user_id,
                    is_deleted=False
                ).first()
                
                if not folder:
                    return False, "Destination folder not found"
            
            # Move the image
            image.folder_id = folder_id
            image.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            destination = f"folder {folder_id}" if folder_id else "root"
            logger.info(f"Moved image {image_id} to {destination} for user {user_id}")
            
            return True, f"Image moved successfully to {destination}"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error moving image to folder: {str(e)}")
            return False, f"Failed to move image: {str(e)}"
    
    def move_images_to_folder(self, user_id: int, image_ids: List[int], folder_id: Optional[int]) -> Tuple[bool, str]:
        """
        Move multiple images to a folder or to root
        
        Args:
            user_id: User ID who owns the images
            image_ids: List of image IDs to move
            folder_id: ID of the destination folder or None for root
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # If moving to a folder, validate it exists
            if folder_id is not None:
                folder = Folder.query.filter_by(
                    id=folder_id,
                    user_id=user_id,
                    is_deleted=False
                ).first()
                
                if not folder:
                    return False, "Destination folder not found"
            
            # Get all images
            images = UserImage.query.filter(
                UserImage.id.in_(image_ids),
                UserImage.user_id == user_id,
                UserImage.is_deleted == False
            ).all()
            
            if not images:
                return False, "No valid images found"
            
            # Move all images
            for image in images:
                image.folder_id = folder_id
                image.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            destination = f"folder {folder_id}" if folder_id else "root"
            logger.info(f"Moved {len(images)} images to {destination} for user {user_id}")
            
            return True, f"Images moved successfully to {destination}"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error moving images to folder: {str(e)}")
            return False, f"Failed to move images: {str(e)}"

# Global instance
folder_service = FolderService() 
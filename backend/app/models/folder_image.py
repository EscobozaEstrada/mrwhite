"""
FolderImage Model for associating images with folders
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app import db

class FolderImage(db.Model):
    """Model for associating images with folders"""
    
    __tablename__ = 'folder_images'
    
    id = Column(Integer, primary_key=True)
    folder_id = Column(Integer, ForeignKey('image_folders.id'), nullable=False, index=True)
    image_id = Column(Integer, ForeignKey('user_images.id'), nullable=False, index=True)
    
    # Display order within folder
    display_order = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    folder = relationship("ImageFolder", backref="folder_images")
    image = relationship("UserImage", backref="folder_associations")
    
    # Ensure each image can only be in a folder once
    __table_args__ = (
        UniqueConstraint('folder_id', 'image_id', name='uix_folder_image'),
    )
    
    @staticmethod
    def get_folder_images(folder_id: int):
        """Get images in a folder ordered by display_order"""
        return FolderImage.query.filter_by(
            folder_id=folder_id
        ).order_by(
            FolderImage.display_order.asc()
        ).all()
    
    @staticmethod
    def get_folder_image_count(folder_id: int) -> int:
        """Get total count of images in a folder"""
        return FolderImage.query.filter_by(
            folder_id=folder_id
        ).count() 
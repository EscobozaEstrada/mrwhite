"""
Folder Model for organizing images in the gallery
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app import db

class ImageFolder(db.Model):
    """Model for organizing images into folders"""
    
    __tablename__ = 'image_folders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Folder information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Display order for folder list
    display_order = Column(Integer, default=0, nullable=False)
    
    # Status and timestamps
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="folders")
    
    def to_dict(self):
        """Convert folder to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_user_folders(user_id: int):
        """Get user's folders"""
        return ImageFolder.query.filter_by(
            user_id=user_id,
            is_deleted=False
        ).order_by(
            ImageFolder.display_order.asc(),
            ImageFolder.created_at.desc()
        ).all()
    
    @staticmethod
    def get_user_folder_count(user_id: int) -> int:
        """Get total count of user's folders"""
        return ImageFolder.query.filter_by(
            user_id=user_id,
            is_deleted=False
        ).count() 
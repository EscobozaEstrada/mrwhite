"""
User Image Model for storing uploaded images with comprehensive metadata
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app import db
import os

class UserImage(db.Model):
    """Model for storing user uploaded images with comprehensive metadata"""
    
    __tablename__ = 'user_images'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # File information
    filename = Column(String(255), nullable=False)  # Unique filename in S3
    original_filename = Column(String(255), nullable=False)  # Original uploaded filename
    s3_url = Column(Text, nullable=False)  # Full S3 URL
    s3_key = Column(String(500), nullable=False)  # S3 key/path
    
    # AI Analysis
    description = Column(Text)  # OpenAI generated description
    analysis_data = Column(JSON)  # OpenAI analysis metadata (tokens, model, etc.)
    
    # Image metadata
    image_metadata = Column(JSON)  # Width, height, format, file size, EXIF, etc.
    
    # Chat context (optional)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=True, index=True)
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=True, index=True)
    
    # Status and timestamps
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="images")
    conversation = relationship("Conversation", backref="images")
    message = relationship("Message", backref="images")
    
    def __repr__(self):
        return f'<UserImage {self.id}: {self.original_filename} by User {self.user_id}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        # Generate proper URL for frontend access
        stored_url = self.s3_url
        if stored_url.startswith('http://') or stored_url.startswith('https://'):
            # Already a full URL (S3)
            image_url = stored_url
        elif stored_url.startswith('/uploads/images/'):
            # Local path - generate full backend URL
            backend_url = os.getenv('BACKEND_BASE_URL', 'http://localhost:5001')
            image_url = f"{backend_url}{stored_url}"
        else:
            # Fallback
            image_url = stored_url
        
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'url': image_url,
            'description': self.description,
            'analysis_data': self.analysis_data,
            'metadata': self.image_metadata,
            'conversation_id': self.conversation_id,
            'message_id': self.message_id,
            'uploaded_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'file_size': self.image_metadata.get('file_size', 0) if self.image_metadata else 0,
            'width': self.image_metadata.get('width', 0) if self.image_metadata else 0,
            'height': self.image_metadata.get('height', 0) if self.image_metadata else 0,
            'format': self.image_metadata.get('format', '') if self.image_metadata else ''
        }
    
    def to_gallery_dict(self):
        """Convert to simplified dictionary for gallery display"""
        # Generate proper URL for frontend access
        stored_url = self.s3_url
        if stored_url.startswith('http://') or stored_url.startswith('https://'):
            # Already a full URL (S3)
            image_url = stored_url
        elif stored_url.startswith('/uploads/images/'):
            # Local path - generate full backend URL
            backend_url = os.getenv('BACKEND_BASE_URL', 'http://localhost:5001')
            image_url = f"{backend_url}{stored_url}"
        else:
            # Fallback
            image_url = stored_url
        
        return {
            'id': self.id,
            'url': image_url,
            'title': self.original_filename,
            'description': self.description,
            'uploaded_at': self.created_at.isoformat() if self.created_at else None,
            'file_size': self.image_metadata.get('file_size', 0) if self.image_metadata else 0,
            'width': self.image_metadata.get('width', 0) if self.image_metadata else 0,
            'height': self.image_metadata.get('height', 0) if self.image_metadata else 0
        }
    
    @staticmethod
    def get_user_images(user_id: int, limit: int = 50, offset: int = 0):
        """Get user's images for gallery"""
        return UserImage.query.filter_by(
            user_id=user_id,
            is_deleted=False
        ).order_by(
            UserImage.created_at.desc()
        ).limit(limit).offset(offset).all()
    
    @staticmethod
    def get_user_image_count(user_id: int) -> int:
        """Get total count of user's images"""
        return UserImage.query.filter_by(
            user_id=user_id,
            is_deleted=False
        ).count()
    
    @staticmethod
    def search_user_images(user_id: int, search_term: str, limit: int = 20):
        """Search user's images by description or filename"""
        return UserImage.query.filter(
            UserImage.user_id == user_id,
            UserImage.is_deleted == False,
            db.or_(
                UserImage.description.ilike(f'%{search_term}%'),
                UserImage.original_filename.ilike(f'%{search_term}%')
            )
        ).order_by(
            UserImage.created_at.desc()
        ).limit(limit).all() 
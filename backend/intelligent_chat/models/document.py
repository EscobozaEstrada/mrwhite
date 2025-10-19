"""
Document-related models
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, ForeignKey, BigInteger, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Document(Base):
    """Documents uploaded during chat"""
    __tablename__ = "ic_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", use_alter=True, name="fk_ic_docs_user_id"), nullable=False)
    message_id = Column(Integer, ForeignKey("ic_messages.id", ondelete="CASCADE"))
    conversation_id = Column(Integer, ForeignKey("ic_conversations.id", ondelete="CASCADE"))

    # File information
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # 'image', 'pdf', 'docx', 'txt'
    file_size = Column(BigInteger)
    mime_type = Column(String(100))

    # S3 storage
    s3_key = Column(String(500), nullable=False)
    s3_url = Column(Text, nullable=False)

    # Pinecone storage
    pinecone_namespace = Column(String(200))
    pinecone_ids = Column(ARRAY(Text))

    # Extracted content
    extracted_text = Column(Text)
    image_analysis = Column(JSONB)  # For image content analysis

    # Processing status
    processing_status = Column(String(50), default='pending')
    error_message = Column(Text)
    chunk_count = Column(Integer, default=0)
    pinecone_vectors_stored = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Document metadata (renamed to avoid SQLAlchemy reserved attribute conflict)
    doc_metadata = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Soft delete
    is_deleted = Column(Boolean, default=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', type='{self.file_type}')>"

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "s3_url": self.s3_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class VetReport(Base):
    """Vet reports attached to dog profiles for health mode"""
    __tablename__ = "ic_vet_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", use_alter=True, name="fk_ic_vet_reports_user_id"), nullable=False)
    dog_profile_id = Column(Integer, ForeignKey("pet_profiles.id", ondelete="CASCADE", use_alter=True, name="fk_ic_vet_reports_dog_id"), nullable=False)

    # File information
    report_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)

    # S3 storage
    s3_key = Column(String(500), nullable=False)
    s3_url = Column(Text, nullable=False)

    # Pinecone storage
    pinecone_namespace = Column(String(200))
    pinecone_ids = Column(ARRAY(Text))

    # Extracted information
    extracted_text = Column(Text)
    key_findings = Column(JSONB)

    # Report date
    report_date = Column(Date)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<VetReport(id={self.id}, dog_profile_id={self.dog_profile_id}, name='{self.report_name}')>"

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "dog_profile_id": self.dog_profile_id,
            "report_name": self.report_name,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "s3_url": self.s3_url,
            "key_findings": self.key_findings or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


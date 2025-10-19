"""
Conversation-related models
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, ForeignKey, ARRAY, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Conversation(Base):
    """Single conversation per user"""
    __tablename__ = "ic_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", use_alter=True, name="fk_ic_conversations_user_id"), nullable=False, unique=True)
    title = Column(String(255), default="Chat with Mr. White")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_archived = Column(Boolean, default=False)

    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="conversation", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="conversation", cascade="all, delete-orphan")
    context = relationship("ConversationContext", back_populates="conversation", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title='{self.title}')>"


class Message(Base):
    """All chat messages with rich metadata"""
    __tablename__ = "ic_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("ic_conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", use_alter=True, name="fk_ic_messages_user_id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    # Message metadata
    tokens_used = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    model_used = Column(String(100))
    response_time_ms = Column(Integer)

    # Document references
    has_documents = Column(Boolean, default=False)
    document_ids = Column(ARRAY(Integer))

    # Mode context
    active_mode = Column(String(50))  # 'reminders', 'health', 'wayofdog', null
    dog_profile_id = Column(Integer, ForeignKey("pet_profiles.id", ondelete="SET NULL", use_alter=True, name="fk_ic_messages_dog_id"))

    # Timestamps (date_group auto-populated by trigger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    date_group = Column(Date)

    # Search (auto-populated by trigger)
    search_vector = Column(TSVECTOR)

    # Soft delete
    is_deleted = Column(Boolean, default=False)

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ic_messages_role_check"),
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    feedback = relationship("MessageFeedback", back_populates="message", cascade="all, delete-orphan")
    corrections = relationship("UserCorrection", back_populates="message", cascade="all, delete-orphan")
    credit_usage = relationship("CreditUsage", back_populates="message", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="message")

    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', conversation_id={self.conversation_id})>"

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "tokens_used": self.tokens_used,
            "credits_used": float(self.credits_used) if self.credits_used else 0.0,
            "has_documents": self.has_documents,
            "document_ids": self.document_ids or [],
            "active_mode": self.active_mode,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "date_group": self.date_group.isoformat() if self.date_group else None,
        }


class ConversationContext(Base):
    """Current conversation state and active mode"""
    __tablename__ = "ic_conversation_context"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("ic_conversations.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", use_alter=True, name="fk_ic_context_user_id"), nullable=False)

    # Active state
    active_mode = Column(String(50))  # 'reminders', 'health', 'wayofdog', null
    selected_dog_profile_id = Column(Integer, ForeignKey("pet_profiles.id", ondelete="CASCADE", use_alter=True, name="fk_ic_context_dog_id"))

    # Conversation memory
    recent_topics = Column(JSONB, default=[])
    mentioned_dogs = Column(ARRAY(String))

    # Session state
    last_activity = Column(DateTime(timezone=True), server_default=func.now())

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="context")

    def __repr__(self):
        return f"<ConversationContext(id={self.id}, conversation_id={self.conversation_id}, active_mode='{self.active_mode}')>"


"""
User preference model
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, ARRAY, UniqueConstraint, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class UserPreference(Base):
    """User preferences and learned behaviors"""
    __tablename__ = "ic_user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", use_alter=True, name="fk_ic_preferences_user_id"), nullable=False, unique=True)

    # Communication preferences
    response_style = Column(String(50), default='balanced')  # 'concise', 'detailed', 'balanced'
    tone_preference = Column(String(50), default='friendly')  # 'professional', 'friendly', 'casual'

    # Feature preferences
    enable_curiosity = Column(Boolean, default=True)
    enable_followup_questions = Column(Boolean, default=True)
    enable_pawtree_links = Column(Boolean, default=True)

    # Learned patterns
    preferred_topics = Column(JSONB, default=[])
    avoided_topics = Column(JSONB, default=[])

    # Context
    typical_dog_concerns = Column(ARRAY(String))
    common_questions = Column(ARRAY(String))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserPreference(id={self.id}, user_id={self.user_id}, style='{self.response_style}')>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "response_style": self.response_style,
            "tone_preference": self.tone_preference,
            "enable_curiosity": self.enable_curiosity,
            "enable_followup_questions": self.enable_followup_questions,
            "enable_pawtree_links": self.enable_pawtree_links,
            "preferred_topics": self.preferred_topics or [],
            "avoided_topics": self.avoided_topics or [],
        }


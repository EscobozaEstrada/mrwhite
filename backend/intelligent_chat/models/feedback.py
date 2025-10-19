"""
Feedback and correction models
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class UserCorrection(Base):
    """User corrections to learn from mistakes"""
    __tablename__ = "ic_user_corrections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", use_alter=True, name="fk_ic_corrections_user_id"), nullable=False)
    message_id = Column(Integer, ForeignKey("ic_messages.id", ondelete="CASCADE"))

    # Correction details
    incorrect_response = Column(Text)
    correction_text = Column(Text)
    correction_type = Column(String(50))  # 'factual', 'tone', 'format', 'recommendation'

    # Context
    context_summary = Column(Text)

    # Applied
    is_applied = Column(Boolean, default=False)
    applied_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="corrections")

    def __repr__(self):
        return f"<UserCorrection(id={self.id}, type='{self.correction_type}', applied={self.is_applied})>"


class MessageFeedback(Base):
    """Like/dislike feedback on messages"""
    __tablename__ = "ic_message_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("ic_messages.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", use_alter=True, name="fk_ic_feedback_user_id"), nullable=False)

    # Feedback
    feedback_type = Column(String(20), nullable=False)  # 'like', 'dislike'
    feedback_reason = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("feedback_type IN ('like', 'dislike')", name="ic_message_feedback_type_check"),
        UniqueConstraint('message_id', 'user_id', name='unique_message_feedback'),
    )

    # Relationships
    message = relationship("Message", back_populates="feedback")

    def __repr__(self):
        return f"<MessageFeedback(id={self.id}, message_id={self.message_id}, type='{self.feedback_type}')>"



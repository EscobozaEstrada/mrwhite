"""
Credit usage model
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class CreditUsage(Base):
    """Credit consumption tracking per message"""
    __tablename__ = "ic_credit_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", use_alter=True, name="fk_ic_credits_user_id"), nullable=False)
    message_id = Column(Integer, ForeignKey("ic_messages.id", ondelete="CASCADE"))

    # Usage details
    action_type = Column(String(50), nullable=False)  # 'chat', 'document_upload', 'image_analysis', 'voice_transcription'
    credits_used = Column(DECIMAL(10, 4), nullable=False)
    tokens_used = Column(Integer)

    # Model information
    model_used = Column(String(100))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="credit_usage")

    def __repr__(self):
        return f"<CreditUsage(id={self.id}, action='{self.action_type}', credits={self.credits_used})>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "action_type": self.action_type,
            "credits_used": float(self.credits_used),
            "tokens_used": self.tokens_used,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }



"""
Reminder model
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Reminder(Base):
    """Reminders created through reminder mode"""
    __tablename__ = "ic_reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", use_alter=True, name="fk_ic_reminders_user_id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("ic_conversations.id", ondelete="CASCADE"))
    message_id = Column(Integer, ForeignKey("ic_messages.id", ondelete="SET NULL"))
    dog_profile_id = Column(Integer, ForeignKey("pet_profiles.id", ondelete="CASCADE", use_alter=True, name="fk_ic_reminders_dog_id"))

    # Reminder details
    title = Column(String(255), nullable=False)
    description = Column(Text)
    reminder_type = Column(String(50))  # 'vet_appointment', 'medication', 'grooming', 'custom'

    # Timing
    reminder_datetime = Column(DateTime(timezone=True), nullable=False)
    recurrence = Column(String(50))  # 'once', 'daily', 'weekly', 'monthly'

    # Status
    status = Column(String(20), default='pending')  # 'pending', 'sent', 'completed', 'cancelled'
    completed_at = Column(DateTime(timezone=True))

    # Created from chat context
    created_from_message = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'sent', 'completed', 'cancelled')", name="ic_reminders_status_check"),
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="reminders")
    message = relationship("Message", back_populates="reminders")

    def __repr__(self):
        return f"<Reminder(id={self.id}, title='{self.title}', status='{self.status}')>"

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "reminder_type": self.reminder_type,
            "reminder_datetime": self.reminder_datetime.isoformat() if self.reminder_datetime else None,
            "recurrence": self.recurrence,
            "status": self.status,
            "dog_profile_id": self.dog_profile_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }



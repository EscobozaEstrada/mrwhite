"""
Dog Profile Model
"""
from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Date, Numeric, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import Base


class DogProfile(Base):
    """Dog profile model"""
    __tablename__ = "ic_dog_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    breed = Column(String(100))
    age = Column(Integer)
    date_of_birth = Column(Date)
    weight = Column(Numeric)
    gender = Column(String(10))
    color = Column(String(100))
    image_url = Column(String(500))
    image_description = Column(Text)
    comprehensive_profile = Column(JSONB, default=dict)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)






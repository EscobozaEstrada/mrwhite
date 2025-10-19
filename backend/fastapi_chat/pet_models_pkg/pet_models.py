"""
Pet Profile Models for FastAPI Chat Service
SQLAlchemy models for pet_profiles table integration
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Date, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from models import Base

class PetProfile(Base):
    """
    Pet Profile model matching the existing pet_profiles table structure
    """
    __tablename__ = 'pet_profiles'
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Basic information
    name = Column(String(100), nullable=False)
    breed = Column(String(100), nullable=True)
    age = Column(Integer, nullable=True)
    weight = Column(Numeric(5, 2), nullable=True)
    gender = Column(String(10), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    
    # Health information
    microchip_id = Column(String(50), nullable=True)
    spayed_neutered = Column(Boolean, nullable=True)
    known_allergies = Column(Text, nullable=True)
    medical_conditions = Column(Text, nullable=True)
    
    # Emergency contacts
    emergency_vet_name = Column(String(100), nullable=True)
    emergency_vet_phone = Column(String(20), nullable=True)
    
    # 🆕 COMPREHENSIVE PROFILE: Complete JSON storage for all pet details  
    # Starts empty, gets populated as users provide information
    comprehensive_profile = Column(JSONB, nullable=True, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'breed': self.breed,
            'age': self.age,
            'weight': float(self.weight) if self.weight else None,
            'gender': self.gender,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'microchip_id': self.microchip_id,
            'spayed_neutered': self.spayed_neutered,
            'known_allergies': self.known_allergies,
            'medical_conditions': self.medical_conditions,
            'emergency_vet_name': self.emergency_vet_name,
            'emergency_vet_phone': self.emergency_vet_phone,
            'comprehensive_profile': self.comprehensive_profile or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_missing_fields(self) -> list:
        """Get list of fields that are missing (None/empty)"""
        missing = []
        fields_to_check = [
            'breed', 'age', 'weight', 'gender', 'date_of_birth',
            'microchip_id', 'spayed_neutered', 'known_allergies', 
            'medical_conditions', 'emergency_vet_name', 'emergency_vet_phone'
        ]
        
        for field in fields_to_check:
            value = getattr(self, field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)
        
        return missing
    
    def __repr__(self):
        return f"<PetProfile(id={self.id}, name='{self.name}', breed='{self.breed}', user_id={self.user_id})>"


# Pydantic models for API validation
class PetProfileCreate(BaseModel):
    """Schema for creating a new pet profile"""
    name: str = Field(..., min_length=1, max_length=100)
    breed: Optional[str] = Field(None, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=30)
    weight: Optional[float] = Field(None, gt=0, le=200)
    gender: Optional[str] = Field(None, pattern="^(Male|Female|Unknown)$")
    date_of_birth: Optional[str] = None  # ISO format date string
    microchip_id: Optional[str] = Field(None, max_length=50)
    spayed_neutered: Optional[bool] = None
    known_allergies: Optional[str] = None
    medical_conditions: Optional[str] = None
    emergency_vet_name: Optional[str] = Field(None, max_length=100)
    emergency_vet_phone: Optional[str] = Field(None, max_length=20)


class PetProfileUpdate(BaseModel):
    """Schema for updating pet profile (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    breed: Optional[str] = Field(None, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=30)
    weight: Optional[float] = Field(None, gt=0, le=200)
    gender: Optional[str] = Field(None, pattern="^(Male|Female|Unknown)$")
    date_of_birth: Optional[str] = None
    microchip_id: Optional[str] = Field(None, max_length=50)
    spayed_neutered: Optional[bool] = None
    known_allergies: Optional[str] = None
    medical_conditions: Optional[str] = None
    emergency_vet_name: Optional[str] = Field(None, max_length=100)
    emergency_vet_phone: Optional[str] = Field(None, max_length=20)


class PetProfileResponse(BaseModel):
    """Schema for pet profile API responses"""
    id: int
    user_id: int
    name: str
    breed: Optional[str]
    age: Optional[int]
    weight: Optional[float]
    gender: Optional[str]
    date_of_birth: Optional[str]
    microchip_id: Optional[str]
    spayed_neutered: Optional[bool]
    known_allergies: Optional[str]
    medical_conditions: Optional[str]
    emergency_vet_name: Optional[str]
    emergency_vet_phone: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    missing_fields: list = []
    
    class Config:
        from_attributes = True

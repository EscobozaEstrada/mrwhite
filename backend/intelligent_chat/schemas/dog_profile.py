"""
Pydantic schemas for Dog Profile API
Simplified schema for ic_dog_profiles table
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import date, datetime


class DogProfileCreate(BaseModel):
    """Schema for creating a dog profile"""
    name: str = Field(..., min_length=1, max_length=100)
    breed: Optional[str] = Field(None, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=30)
    date_of_birth: Optional[date] = None
    weight: Optional[float] = Field(None, gt=0, le=300)
    gender: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=500)
    image_description: Optional[str] = None
    comprehensive_profile: Optional[Dict[str, Any]] = None


class DogProfileUpdate(BaseModel):
    """Schema for updating a dog profile"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    breed: Optional[str] = Field(None, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=30)
    date_of_birth: Optional[date] = None
    weight: Optional[float] = Field(None, gt=0, le=300)
    gender: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=500)
    image_description: Optional[str] = None
    comprehensive_profile: Optional[Dict[str, Any]] = None


class DogProfileResponse(BaseModel):
    """Schema for dog profile response"""
    id: int
    user_id: int
    name: str
    breed: Optional[str] = None
    age: Optional[int] = None
    date_of_birth: Optional[date] = None
    weight: Optional[float] = None
    gender: Optional[str] = None
    color: Optional[str] = None
    image_url: Optional[str] = None
    image_description: Optional[str] = None
    comprehensive_profile: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat() if v else None
        }
    }


class DogProfileListResponse(BaseModel):
    """Schema for list of dog profiles"""
    dogs: List[DogProfileResponse]


class DogProfileDeleteResponse(BaseModel):
    """Schema for delete response"""
    success: bool
    message: str
    dog_name: Optional[str] = None
    clear_chat_recommended: bool = False
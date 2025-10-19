"""
Chat-related schemas
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChatRequest(BaseModel):
    """Request schema for chat messages"""
    message: str = Field(default="", max_length=10000, description="User message (can be empty if documents are attached)")
    active_mode: Optional[str] = Field(None, description="Active mode: 'reminders', 'health', 'wayofdog', or null")
    dog_profile_id: Optional[int] = Field(None, description="Selected dog profile ID for context")
    document_ids: Optional[List[int]] = Field(default=[], description="IDs of documents attached to this message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Can you help me set a reminder for my dog's vet appointment?",
                "active_mode": "reminders",
                "dog_profile_id": 1,
                "document_ids": []
            }
        }


class DocumentAttachment(BaseModel):
    """Document attachment info"""
    id: int
    filename: str
    file_type: str
    s3_url: str
    created_at: str
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response schema for a single message"""
    id: int
    conversation_id: int
    role: str
    content: str
    tokens_used: int
    credits_used: float
    has_documents: bool
    document_ids: List[int]
    documents: Optional[List[DocumentAttachment]] = []  # Full document info for display
    active_mode: Optional[str]
    created_at: str
    date_group: Optional[str]
    
    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Response schema for chat completion"""
    message: MessageResponse
    streaming: bool = Field(default=False, description="Whether response is streaming")
    conversation_id: int
    credits_remaining: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": {
                    "id": 123,
                    "conversation_id": 45,
                    "role": "assistant",
                    "content": "I'd be happy to help you set a reminder!",
                    "tokens_used": 250,
                    "credits_used": 0.015,
                    "has_documents": False,
                    "document_ids": [],
                    "active_mode": "reminders",
                    "created_at": "2025-10-06T10:30:00Z",
                    "date_group": "2025-10-06"
                },
                "streaming": False,
                "conversation_id": 45,
                "credits_remaining": 9.985
            }
        }


class StreamChunk(BaseModel):
    """Streaming response chunk"""
    type: str = Field(..., description="Chunk type: 'token', 'metadata', 'done', 'error'")
    content: Optional[str] = Field(None, description="Token content for type='token'")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata for type='metadata'")
    error: Optional[str] = Field(None, description="Error message for type='error'")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "token",
                "content": "Hello",
                "metadata": None,
                "error": None
            }
        }


class DogProfileContext(BaseModel):
    """Dog profile context for tailored responses"""
    id: int
    name: str
    breed: Optional[str]
    age: Optional[int]
    weight: Optional[float]
    known_allergies: Optional[str]
    medical_conditions: Optional[str]
    
    class Config:
        from_attributes = True







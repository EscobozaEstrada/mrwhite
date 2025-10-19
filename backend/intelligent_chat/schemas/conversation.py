"""
Conversation-related schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from .chat import MessageResponse


class ConversationResponse(BaseModel):
    """Response schema for conversation"""
    id: int
    user_id: int
    title: str
    created_at: str
    updated_at: str
    message_count: int
    
    class Config:
        from_attributes = True


class ConversationHistoryRequest(BaseModel):
    """Request schema for conversation history"""
    conversation_id: int
    limit: Optional[int] = Field(default=50, le=200, description="Max messages to return")
    offset: Optional[int] = Field(default=0, description="Offset for pagination")
    search_query: Optional[str] = Field(None, description="Search query for keyword search")
    date_filter: Optional[str] = Field(None, description="Date filter (ISO format)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": 45,
                "limit": 50,
                "offset": 0,
                "search_query": "vet appointment",
                "date_filter": "2025-10-06"
            }
        }


class ConversationHistoryResponse(BaseModel):
    """Response schema for conversation history"""
    conversation_id: int
    messages: List[MessageResponse]
    total_count: int
    has_more: bool
    date_groups: List[str]  # List of unique dates
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": 45,
                "messages": [],
                "total_count": 150,
                "has_more": True,
                "date_groups": ["2025-10-06", "2025-10-05", "2025-10-04"]
            }
        }


class ClearChatRequest(BaseModel):
    """Request schema for clearing chat"""
    conversation_id: int
    clear_memory: bool = Field(default=False, description="Also clear Pinecone memories")
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": 45,
                "clear_memory": False
            }
        }


class ClearChatResponse(BaseModel):
    """Response schema for clearing chat"""
    success: bool
    messages_deleted: int
    memory_cleared: bool
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "messages_deleted": 150,
                "memory_cleared": False,
                "message": "Chat cleared successfully"
            }
        }







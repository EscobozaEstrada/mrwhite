"""
State definitions for LangGraph agents.
"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


class AgentState(BaseModel):
    """Base state for all agents."""
    messages: List[BaseMessage] = Field(default_factory=list)
    user_id: int
    conversation_id: int
    mode: str


class ReminderState(AgentState):
    """State for Reminder Agent - tracks reminder creation progress."""
    
    # Extracted information
    title: Optional[str] = None
    description: Optional[str] = None
    reminder_datetime: Optional[datetime] = None
    reminder_type: Optional[str] = None  # medication, vet_appointment, grooming, etc.
    dog_profile_id: Optional[int] = None
    dog_name: Optional[str] = None
    recurrence: Optional[str] = None  # once, daily, weekly, monthly
    
    # Tracking
    missing_fields: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    ready_to_create: bool = False
    reminder_created: bool = False
    reminder_id: Optional[int] = None
    
    # Context from Pinecone
    context_from_memory: Optional[str] = None
    available_dogs: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True






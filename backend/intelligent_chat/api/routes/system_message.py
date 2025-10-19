from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Dict, Any

from models.conversation import Conversation, Message
from models.base import get_db
from middleware.auth import require_auth
from services.chat_service import ChatService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class SystemMessageRequest(BaseModel):
    content: str
    dog_profile_id: Optional[int] = None
    active_mode: Optional[str] = None
    action_type: str  # "dog_added", "dog_edited", "dog_deleted"

class SystemMessageResponse(BaseModel):
    success: bool
    message_id: int
    conversation_id: int
    message: str

@router.post("/system-message", response_model=SystemMessageResponse)
async def create_system_message(
    request: SystemMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Create a system/assistant message in the conversation
    This is used for automated responses like dog addition/editing confirmations
    """
    try:
        user_id = current_user["id"]
        
        # Get or create conversation
        result_conv = await db.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversation = result_conv.scalar_one_or_none()
        
        if not conversation:
            conversation = Conversation(user_id=user_id, title="Chat with Mr. White")
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
        
        # Create chat service instance to use the _store_message method
        chat_service = ChatService()
        
        # Store the system message
        message = await chat_service._store_message(
            db=db,
            conversation_id=conversation.id,
            user_id=user_id,
            role="assistant",
            content=request.content,
            active_mode=request.active_mode,
            dog_profile_id=request.dog_profile_id,
            tokens_used=0,  # No tokens used for system messages
            credits_used=0.0  # No credits used for system messages
        )
        
        logger.info(f"✅ Created system message {message.id} for user {user_id} - Action: {request.action_type}")
        
        return SystemMessageResponse(
            success=True,
            message_id=message.id,
            conversation_id=conversation.id,
            message="System message created successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to create system message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

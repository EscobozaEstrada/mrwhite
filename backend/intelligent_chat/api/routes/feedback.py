"""
Message feedback routes for like/dislike functionality
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from models.base import get_db
from middleware.auth import require_auth
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    """Request schema for message feedback"""
    message_id: int
    feedback_type: str  # 'like' or 'dislike'
    feedback_reason: str | None = None


class FeedbackResponse(BaseModel):
    """Response schema for feedback"""
    success: bool
    message: str
    feedback_id: int | None = None


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit or update feedback for a message
    
    - If feedback already exists, updates it
    - If not, creates new feedback
    """
    try:
        user_id = current_user["id"]
        
        # Validate feedback type
        if request.feedback_type not in ['like', 'dislike']:
            raise HTTPException(status_code=400, detail="Invalid feedback type. Must be 'like' or 'dislike'")
        
        # Check if message exists and belongs to the user's conversation
        message_check = await db.execute(
            text("""
                SELECT m.id, m.user_id, m.conversation_id 
                FROM ic_messages m
                WHERE m.id = :message_id AND m.role = 'assistant'
            """),
            {"message_id": request.message_id}
        )
        message_row = message_check.fetchone()
        
        if not message_row:
            raise HTTPException(status_code=404, detail="Message not found or is not an assistant message")
        
        # Verify user has access to this conversation
        conversation_check = await db.execute(
            text("""
                SELECT id FROM ic_conversations
                WHERE id = :conversation_id AND user_id = :user_id
            """),
            {"conversation_id": message_row.conversation_id, "user_id": user_id}
        )
        
        if not conversation_check.fetchone():
            raise HTTPException(status_code=403, detail="You don't have access to this conversation")
        
        # Check if feedback already exists
        existing_feedback = await db.execute(
            text("""
                SELECT id, feedback_type FROM ic_message_feedback
                WHERE message_id = :message_id AND user_id = :user_id
            """),
            {"message_id": request.message_id, "user_id": user_id}
        )
        existing_row = existing_feedback.fetchone()
        
        if existing_row:
            # Update existing feedback
            await db.execute(
                text("""
                    UPDATE ic_message_feedback
                    SET feedback_type = :feedback_type, feedback_reason = :feedback_reason, created_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """),
                {
                    "feedback_type": request.feedback_type,
                    "feedback_reason": request.feedback_reason,
                    "id": existing_row.id
                }
            )
            await db.commit()
            
            logger.info(f"✅ Updated feedback {existing_row.id} for message {request.message_id}")
            
            return FeedbackResponse(
                success=True,
                message=f"Feedback updated to '{request.feedback_type}'",
                feedback_id=existing_row.id
            )
        else:
            # Insert new feedback
            result = await db.execute(
                text("""
                    INSERT INTO ic_message_feedback (message_id, user_id, feedback_type, feedback_reason)
                    VALUES (:message_id, :user_id, :feedback_type, :feedback_reason)
                    RETURNING id
                """),
                {
                    "message_id": request.message_id,
                    "user_id": user_id,
                    "feedback_type": request.feedback_type,
                    "feedback_reason": request.feedback_reason
                }
            )
            feedback_row = result.fetchone()
            await db.commit()
            
            logger.info(f"✅ Created feedback {feedback_row.id} for message {request.message_id}")
            
            return FeedbackResponse(
                success=True,
                message=f"Feedback '{request.feedback_type}' submitted",
                feedback_id=feedback_row.id
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Feedback submission failed: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")


@router.get("/{message_id}")
async def get_feedback(
    message_id: int,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get feedback for a specific message"""
    try:
        user_id = current_user["id"]
        
        result = await db.execute(
            text("""
                SELECT id, feedback_type, feedback_reason, created_at
                FROM ic_message_feedback
                WHERE message_id = :message_id AND user_id = :user_id
            """),
            {"message_id": message_id, "user_id": user_id}
        )
        feedback = result.fetchone()
        
        if not feedback:
            return {"feedback": None}
        
        return {
            "feedback": {
                "id": feedback.id,
                "type": feedback.feedback_type,
                "reason": feedback.feedback_reason,
                "created_at": feedback.created_at.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Get feedback failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get feedback: {str(e)}")


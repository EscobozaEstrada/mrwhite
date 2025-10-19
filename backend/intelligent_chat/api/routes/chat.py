"""
Chat API Routes
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from schemas.chat import ChatRequest, ChatResponse, MessageResponse
from schemas.conversation import (
    ConversationHistoryRequest,
    ConversationHistoryResponse,
    ClearChatRequest,
    ClearChatResponse
)
from services.chat_service import ChatService
from services.health_chat_service import HealthChatService
from services.wayofdog_chat_service import WayOfDogChatService
from services.credit_service import IntelligentChatCreditService
from models.conversation import Message, Conversation
from middleware.auth import require_auth
from sqlalchemy import select, delete, func

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Intelligent Chat"])

# Initialize services
chat_service = ChatService()
health_service = HealthChatService()
wayofdog_service = WayOfDogChatService()
credit_service = IntelligentChatCreditService()


def get_service_for_mode(active_mode: str):
    """
    Route requests to the appropriate service based on active mode
    """
    if active_mode == "health":
        return health_service
    elif active_mode == "wayofdog":
        return wayofdog_service
    elif active_mode == "reminders":
        return chat_service  # ChatService handles reminders
    else:
        return chat_service  # Default to general chat service




@router.get("/credits")
async def get_credit_status(
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get user's current credit status
    """
    try:
        user_id = current_user["id"]
        credits_remaining = await credit_service.get_user_credits(user_id, cookies=dict(http_request.cookies)) or 0
        
        return {
            "credits_remaining": credits_remaining,
            "user_id": user_id,
            "is_premium": current_user.get("is_premium", False)
        }
        
    except Exception as e:
        logger.error(f"❌ Get credit status failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Send a message to the intelligent chatbot
    
    Non-streaming response
    """
    try:
        user_id = current_user["id"]
        
        # Check if user has documents uploaded
        has_documents = bool(request.document_ids and len(request.document_ids) > 0)
        
        # Check and deduct credits before processing
        success, message, credits_deducted = await credit_service.check_and_deduct_credits(
            user_id=user_id,
            active_mode=request.active_mode,
            has_documents=has_documents,
            metadata={"message_length": len(request.message)},
            cookies=dict(http_request.cookies)
        )
        
        if not success:
            raise HTTPException(status_code=402, detail=message)
        
        logger.info(f"✅ Credits deducted: {credits_deducted} for user {user_id}, mode: {request.active_mode}, docs: {has_documents}")
        
        # Get the appropriate service for the active mode
        service = get_service_for_mode(request.active_mode)
        
        # process_message is an async generator, even when stream=False
        # We need to iterate it and collect the final result
        result = None
        
        # Different services have different method signatures
        if request.active_mode in ["health", "wayofdog"]:
            # Specialized services (HealthChatService, WayOfDogChatService) use BaseChatService signature
            # They need conversation_id and don't take active_mode
            result_conv = await db.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            conversation = result_conv.scalar_one_or_none()
            
            if not conversation:
                conversation = Conversation(user_id=user_id, title="Chat with Mr. White")
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
            
            async for chunk in service.process_message(
                db=db,
                user_id=user_id,
                conversation_id=conversation.id,
                message_content=request.message,
                dog_profile_id=request.dog_profile_id,
                document_ids=request.document_ids,
                stream=False,
                username=current_user.get("username")
            ):
                result = chunk  # Get the final result
        else:
            # ChatService (reminders, general) uses ChatService signature with active_mode
            async for chunk in service.process_message(
                db=db,
                user_id=user_id,
                message_content=request.message,
                active_mode=request.active_mode,
                dog_profile_id=request.dog_profile_id,
                document_ids=request.document_ids,
                stream=False,
                username=current_user.get("username")
            ):
                result = chunk  # Get the final result
        
        if not result:
            raise HTTPException(status_code=500, detail="No response generated")
        
        # Get user's remaining credits
        credits_remaining = await credit_service.get_user_credits(user_id, cookies=dict(http_request.cookies)) or 0
        
        return ChatResponse(
            message=MessageResponse(**result["message"]),
            streaming=False,
            conversation_id=result["message"]["conversation_id"],
            credits_remaining=credits_remaining
        )
        
    except Exception as e:
        logger.error(f"❌ Send message failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_message(
    request: ChatRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Send a message with streaming response (SSE)
    """
    try:
        user_id = current_user["id"]
        logger.info(f"🎯 STREAM REQUEST: user={user_id}, mode={request.active_mode}, message='{request.message[:50]}...', docs={request.document_ids}")
        
        # Check if user has documents uploaded
        has_documents = bool(request.document_ids and len(request.document_ids) > 0)
        
        # Check and deduct credits before processing
        success, message, credits_deducted = await credit_service.check_and_deduct_credits(
            user_id=user_id,
            active_mode=request.active_mode,
            has_documents=has_documents,
            metadata={"message_length": len(request.message)},
            cookies=dict(http_request.cookies)
        )
        
        if not success:
            raise HTTPException(status_code=402, detail=message)
        
        logger.info(f"✅ Credits deducted: {credits_deducted} for user {user_id}, mode: {request.active_mode}, docs: {has_documents}")
        
        # Get the appropriate service for the active mode
        service = get_service_for_mode(request.active_mode)
        
        # Different services have different method signatures
        async def generate():
            if request.active_mode in ["health", "wayofdog"]:
                # Specialized services (HealthChatService, WayOfDogChatService) use BaseChatService signature
                # They need conversation_id and don't take active_mode
                result_conv = await db.execute(
                    select(Conversation).where(Conversation.user_id == user_id)
                )
                conversation = result_conv.scalar_one_or_none()
                
                if not conversation:
                    conversation = Conversation(user_id=user_id, title="Chat with Mr. White")
                    db.add(conversation)
                    await db.commit()
                    await db.refresh(conversation)
                
                async for chunk in service.process_message(
                    db=db,
                    user_id=user_id,
                    conversation_id=conversation.id,
                    message_content=request.message,
                    dog_profile_id=request.dog_profile_id,
                    document_ids=request.document_ids,
                    stream=True,
                    username=current_user.get("username")
                ):
                    yield chunk
            else:
                # ChatService (reminders, general) uses ChatService signature with active_mode
                async for chunk in service.process_message(
                    db=db,
                    user_id=user_id,
                    message_content=request.message,
                    active_mode=request.active_mode,
                    dog_profile_id=request.dog_profile_id,
                    document_ids=request.document_ids,
                    stream=True,
                    username=current_user.get("username")
                ):
                    yield chunk
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Stream message failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    limit: int = 50,
    offset: int = 0,
    search_query: Optional[str] = None,
    date_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get conversation history with optional filters
    """
    try:
        user_id = current_user["id"]
        
        # Get user's conversation
        result = await db.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return ConversationHistoryResponse(
                conversation_id=0,
                messages=[],
                total_count=0,
                has_more=False,
                date_groups=[]
            )
        
        # Build query
        query = select(Message).where(
            Message.conversation_id == conversation.id,
            Message.is_deleted == False
        )
        
        # Apply filters
        if search_query:
            # Full-text search
            query = query.where(
                Message.search_vector.match(search_query)
            )
        
        if date_filter:
            from datetime import datetime
            filter_date = datetime.fromisoformat(date_filter).date()
            query = query.where(Message.date_group == filter_date)
        
        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total_count = count_result.scalar()
        
        # Get messages with pagination
        query = query.order_by(Message.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        messages = result.scalars().all()
        
        # Get unique date groups
        date_result = await db.execute(
            select(Message.date_group)
            .where(Message.conversation_id == conversation.id, Message.is_deleted == False)
            .group_by(Message.date_group)
            .order_by(Message.date_group.desc())
        )
        date_groups = [d[0].isoformat() for d in date_result.all() if d[0]]
        
        # Fetch document details for messages with attachments
        from models.document import Document as DocModel
        from schemas.chat import DocumentAttachment
        
        message_responses = []
        for msg in reversed(messages):
            msg_dict = msg.to_dict()
            
            # If message has documents, fetch their details
            if msg.has_documents and msg.document_ids:
                doc_result = await db.execute(
                    select(DocModel).where(DocModel.id.in_(msg.document_ids))
                )
                docs = doc_result.scalars().all()
                msg_dict["documents"] = [
                    DocumentAttachment(
                        id=doc.id,
                        filename=doc.filename,
                        file_type=doc.file_type,
                        s3_url=doc.s3_url,
                        created_at=doc.created_at.isoformat() if doc.created_at else ""
                    ) for doc in docs
                ]
            else:
                msg_dict["documents"] = []
            
            message_responses.append(MessageResponse(**msg_dict))
        
        return ConversationHistoryResponse(
            conversation_id=conversation.id,
            messages=message_responses,
            total_count=total_count,
            has_more=(offset + limit) < total_count,
            date_groups=date_groups
        )
        
    except Exception as e:
        logger.error(f"❌ Get history failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear", response_model=ClearChatResponse)
async def clear_chat(
    request: ClearChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Clear chat messages and optionally clear Pinecone memories
    
    Two modes:
    - clear_memory=False: Only clear messages (keep AI context)
    - clear_memory=True: Clear messages + Pinecone vectors (complete reset)
    """
    try:
        user_id = current_user["id"]
        
        # Verify conversation belongs to user
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == user_id
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get message IDs for related data cleanup
        message_result = await db.execute(
            select(Message.id).where(
                Message.conversation_id == request.conversation_id
            )
        )
        message_ids = [row[0] for row in message_result.fetchall()]
        messages_count = len(message_ids)
        
        # 1. Delete related data first (foreign key constraints)
        if message_ids:
            # Delete message feedback
            from models.feedback import MessageFeedback
            await db.execute(
                delete(MessageFeedback).where(MessageFeedback.message_id.in_(message_ids))
            )
            logger.info(f"🗑️ Deleted message feedback for conversation {request.conversation_id}")
            
            # Delete message-document associations
            from sqlalchemy import text
            try:
                await db.execute(
                    text("DELETE FROM ic_message_documents WHERE message_id = ANY(:message_ids)"),
                    {"message_ids": message_ids}
                )
                logger.info(f"🗑️ Deleted message-document links for conversation {request.conversation_id}")
            except Exception as e:
                # Table might not exist yet - that's okay
                logger.warning(f"⚠️ Could not delete message-document links: {e}")
        
        # 2. Delete user corrections for this conversation
        from models.feedback import UserCorrection
        await db.execute(
            delete(UserCorrection).where(UserCorrection.message_id.in_(message_ids))
        )
        
        # 3. Delete conversation context
        from models.conversation import ConversationContext
        await db.execute(
            delete(ConversationContext).where(ConversationContext.conversation_id == request.conversation_id)
        )
        
        # 4. Delete messages
        await db.execute(
            delete(Message).where(Message.conversation_id == request.conversation_id)
        )
        
        await db.commit()
        logger.info(f"✅ Deleted {messages_count} messages and related data from conversation {request.conversation_id}")
        
        # 5. Clear Pinecone memories
        from services.memory_service import MemoryService
        memory_service = MemoryService()
        memory_cleared = False
        
        if request.clear_memory:
            # "Clear Chat + Memory" - Delete EVERYTHING (conversations, documents, vet reports, book notes)
            memory_cleared = await memory_service.clear_user_memories_complete(
                user_id=user_id,
                include_s3=False  # Don't delete S3 files (they're in DB, user might want them later)
            )
            logger.info(f"✅ Cleared ALL Pinecone memories for user {user_id}")
        else:
            # "Clear Chat Only" - Delete ONLY conversation memories, keep documents/reports/notes
            memory_cleared = await memory_service.clear_conversation_memories(
                user_id=user_id,
                conversation_id=request.conversation_id
            )
            logger.info(f"✅ Cleared ONLY conversation memories for user {user_id}")
        
        message_text = "Chat cleared successfully (documents and memories preserved)"
        if request.clear_memory:
            message_text = "Chat and ALL memories cleared successfully"
        
        return ClearChatResponse(
            success=True,
            messages_deleted=messages_count,
            memory_cleared=memory_cleared,
            message=message_text
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Clear chat failed: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_chat_status(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get chat status and statistics
    """
    try:
        user_id = current_user["id"]
        # Get conversation
        result = await db.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return {
                "has_conversation": False,
                "message_count": 0,
                "credits_remaining": 10.0
            }
        
        # Count messages
        count_result = await db.execute(
            select(func.count()).select_from(Message).where(
                Message.conversation_id == conversation.id,
                Message.is_deleted == False
            )
        )
        message_count = count_result.scalar()
        
        return {
            "has_conversation": True,
            "conversation_id": conversation.id,
            "message_count": message_count,
            "credits_remaining": 10.0,  # TODO: Get actual credits
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Get status failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


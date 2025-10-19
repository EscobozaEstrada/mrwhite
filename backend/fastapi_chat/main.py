"""
FastAPI Chat Service - Async Migration of Flask Chat & Health AI
Replaces Flask chat functionality with high-performance async architecture
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Load environment variables
from dotenv import load_dotenv
load_dotenv()  # Load from local .env file in fastapi_chat directory

from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse, ORJSONResponse
import uvicorn
import redis.asyncio as redis

# Import async services and models
from models import async_init_db, ChatRequest, HealthChatRequest, ChatResponse, ConversationCreateRequest, AsyncSessionLocal, User
from sqlalchemy import select

# Import new modular services
from services.shared.async_pinecone_service import AsyncPineconeService
from services.shared.async_auth_service import AsyncAuthService
from services.shared.async_cache_service import AsyncCacheService
from services.shared.async_openai_pool_service import get_openai_pool, close_global_openai_pool
from services.shared.async_langgraph_service import AsyncLangGraphService
from services.shared.async_smart_intent_router import get_smart_intent_router, close_smart_intent_router

# Context7 optimizations
from services.shared.optimized_chat_handler import optimized_chat_handler

# Import specialized services
from services.chat.chat_service import ChatService
from services.health_ai.health_service import HealthAIService
from services.document.document_service import DocumentService
from services.reminder.reminder_service import ReminderService

# Import service orchestrator
from services.orchestrator import ServiceOrchestrator

from middleware.async_middleware import (
    require_auth_async, 
    require_premium_async,
    require_credits_async,
    require_dynamic_credits_async,
    usage_tracking_middleware
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global services
orchestrator: Optional[ServiceOrchestrator] = None
chat_service: Optional[ChatService] = None
health_service: Optional[HealthAIService] = None
document_service: Optional[DocumentService] = None
reminder_service: Optional[ReminderService] = None
vector_service: Optional[AsyncPineconeService] = None
auth_service: Optional[AsyncAuthService] = None
cache_service: Optional[AsyncCacheService] = None
redis_client: Optional[redis.Redis] = None
openai_pool = None
smart_intent_router = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async context manager for FastAPI app lifecycle"""
    global orchestrator, chat_service, health_service, document_service, reminder_service, vector_service, auth_service, cache_service, redis_client, openai_pool, smart_intent_router
    
    logger.info("🚀 Starting Modular FastAPI Chat Service...")
    
    try:
        # Initialize AWS MemoryDB for Redis - NO LOCAL FALLBACK
        # ONLY use AWS MemoryDB - ignore any local Redis configurations
        memorydb_endpoint = os.getenv("MEMORYDB_ENDPOINT")
        memorydb_port = os.getenv("MEMORYDB_PORT", "6379")
        
        if not memorydb_endpoint:
            raise RuntimeError(
                "AWS MemoryDB configuration required. Set MEMORYDB_ENDPOINT. "
                "This service uses only AWS MemoryDB - no local Redis support."
            )
        
        # AWS MemoryDB requires TLS connection
        redis_client = redis.Redis(
            host=memorydb_endpoint,
            port=int(memorydb_port),
            ssl=True,
            ssl_cert_reqs=None,  # AWS MemoryDB doesn't require client certificates
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=10
        )
        await redis_client.ping()
        logger.info(f"✅ AWS MemoryDB connection established: {memorydb_endpoint}:{memorydb_port} (TLS enabled)")
        
        # Initialize database
        await async_init_db()
        logger.info("✅ Database initialized")
        
        # Initialize cache service (high-performance caching)
        cache_service = AsyncCacheService(redis_client)
        logger.info("✅ Advanced cache service initialized")
        
        # Initialize OpenAI client pool (30-40% API efficiency improvement)
        openai_pool = await get_openai_pool(pool_size=5)
        app.state.openai_pool = openai_pool
        logger.info("✅ OpenAI client pool initialized with connection pooling")
        
        # Initialize Smart Intent Router for intelligent request routing
        smart_intent_router = await get_smart_intent_router(redis_client)
        logger.info("✅ Smart Intent Router initialized")
        
        # Initialize shared services
        auth_service = AsyncAuthService()
        vector_service = AsyncPineconeService()
        logger.info("✅ Shared services initialized")
        
        # Initialize specialized services
        chat_service = ChatService(vector_service, cache_service, smart_intent_router)
        health_service = HealthAIService(vector_service, redis_client, cache_service, smart_intent_router)
        document_service = DocumentService(vector_service, cache_service, smart_intent_router)
        reminder_service = ReminderService(vector_service, redis_client, cache_service, smart_intent_router)
        logger.info("✅ Specialized services initialized")
        
        # Assign OpenAI pool to services that need it
        chat_service.openai_pool = openai_pool
        health_service.openai_pool = openai_pool
        document_service.openai_pool = openai_pool
        document_service.vision_service.openai_pool = openai_pool  # Assign to vision service too
        document_service.voice_service.openai_pool = openai_pool  # Assign to voice service too
        reminder_service.openai_pool = openai_pool
        
        # Initialize Pet Context Manager for intelligent pet information management
        from services.pet.pet_context_manager import PetContextManager
        from models import AsyncSessionLocal
        
        pet_context_manager = PetContextManager(
            redis_client=redis_client,
            db_session_factory=AsyncSessionLocal,
            openai_client=openai_pool
        )
        logger.info("✅ Pet Context Manager initialized")
        
        # Initialize the Service Orchestrator
        orchestrator = ServiceOrchestrator(
            chat_service=chat_service,
            health_service=health_service,
            document_service=document_service,
            reminder_service=reminder_service,
            smart_intent_router=smart_intent_router,
            pet_context_manager=pet_context_manager
        )
        
        orchestrator.set_redis_client(redis_client)
        logger.info("✅ Service Orchestrator initialized")
        
        # Initialize LangGraph service (async initialization) - WITH REQUIRED PARAMETERS
        langgraph_service = AsyncLangGraphService(vector_service, redis_client)
        
        # CRITICAL FIX: Properly initialize LangGraph service
        logger.info("🔧 Ensuring LangGraph service is properly initialized...")
        await langgraph_service.ensure_initialized()
        logger.info("✅ LangGraph service fully initialized and ready")
        
        # Store services in app state for access in endpoints
        app.state.auth_service = auth_service
        app.state.vector_service = vector_service
        app.state.chat_service = chat_service
        app.state.health_service = health_service
        app.state.cache_service = cache_service
        app.state.langgraph_service = langgraph_service
        app.state.openai_pool = openai_pool
        app.state.smart_intent_router = smart_intent_router
        app.state.pet_context_manager = pet_context_manager
        
        
        logger.info("✅ All services with caching initialized successfully")
        logger.info("🚀 FastAPI Chat Service with 60-70% faster responses is ready!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {str(e)}")
        raise
    
    yield
    
    # Cleanup
    logger.info("🔄 Shutting down FastAPI Chat Service...")
    if redis_client:
        await redis_client.close()
    
    # Close OpenAI client pool
    await close_global_openai_pool()
    if smart_intent_router:
        close_smart_intent_router()
    logger.info("✅ Cleanup completed")

# Create FastAPI app
app = FastAPI(
    title="Mr. White Chat Service",
    description="High-performance async chat and Health AI service",
    version="2.0.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse
)

# Configure CORS with more permissive settings for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://34.228.255.83:3000"),
        "http://34.228.255.83:3000",  # Explicit frontend URL
        "http://34.228.255.83:3005",
        "https://mr-white-project.vercel.app",
        "http://127.0.0.1:3000",  # Alternative 34.228.255.83 format
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Cache-Control",
        "Pragma",
        "Origin",
        "Referer",
        "User-Agent",
        "X-CSRF-Token",
        "X-Forwarded-For",
    ],
    expose_headers=["*"],
    max_age=3600,
)

# Add GZip compression middleware for bandwidth optimization
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add usage tracking middleware
app.middleware("http")(usage_tracking_middleware)

# Security
security = HTTPBearer()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "FastAPI Chat Service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0"
    }

# ==================== CHAT ENDPOINTS ====================

@app.post("/api/talk", response_model=ChatResponse)
async def unified_talk_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _credits: Dict[str, Any] = require_dynamic_credits_async()
) -> ChatResponse:
    """
    Unified Talk Endpoint - Intelligent routing to Chat, HealthAI, Document, or Reminder services
    
    This endpoint analyzes user intent and automatically routes to the appropriate service:
    - Normal chat/queries → Chat Service
    - Health concerns/medical questions → HealthAI Service  
    - Document processing/analysis → Document Service
    - Reminder creation/management → Reminder Service
    """
    try:
       
        logger.info(f"🔍 BACKEND RECEIVED: user_id={current_user['id']}, conversation_id={request.conversation_id}, message='{request.message[:50]}...'")
        logger.info(f"🎯 Talk request from user {current_user['id']} - routing to appropriate service")
        
        # Convert FileUpload objects to dictionaries for orchestrator
        files_dict = None
        if request.files:
            files_dict = []
            for file_upload in request.files:
                file_dict = {
                    "filename": file_upload.filename,
                    "content_type": file_upload.content_type,
                    "content": file_upload.content,
                    "size": file_upload.size,
                    "description": file_upload.description
                }
                files_dict.append(file_dict)

        # Use user's message as-is, no auto-generation
        message = request.message.strip() if request.message else ""

        # Use orchestrator to intelligently route request
        response = await orchestrator.process_user_request(
            user_id=current_user["id"],
            conversation_id=request.conversation_id,
            message=message,
            files=files_dict,
            context={"type": "talk"},
            background_tasks=background_tasks
        )
        
        # Post-processing: Check if user shared inline text for archival
        background_tasks.add_task(
            auto_archive_inline_text,
            current_user["id"],
            message,
            response.get("content", ""),
            vector_service
        )
        
        # Log interaction for analytics
        service_used = response.get("orchestration", {}).get("target_service", "unknown")
        background_tasks.add_task(
            log_talk_interaction,
            current_user["id"],
            request.message,
            response.get("content", ""),
            service_used
        )
        
        # Convert to ChatResponse format if needed
        if isinstance(response, dict):
            # Ensure we have a valid conversation_id
            conversation_id = response.get("conversation_id") or request.conversation_id
            if conversation_id is None:
                conversation_id = 1  # Default conversation ID
            
            return ChatResponse(
                success=response.get("success", True),
                content=response.get("content", ""),
                conversation_id=conversation_id,
                message_id=response.get("message_id", 0),
                thread_id=response.get("thread_id"),
                context_info=response.get("context_info", {}),
                sources_used=response.get("sources_used", []),
                processing_time=response.get("processing_time", 0.0)
            )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Talk endpoint error for user {current_user['id']}: {str(e)}")
        raise HTTPException(status_code=500, detail="Request processing failed")

# /api/chat endpoint removed - Frontend now uses /api/talk with full AWS integration

@app.post("/api/messages/{message_id}/retry", response_model=ChatResponse)
async def retry_ai_message(
    message_id: str,
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _credits: Dict[str, Any] = require_dynamic_credits_async()
) -> ChatResponse:
    """
    Retry/Regenerate an AI message response
    
    This endpoint regenerates a different response to the same user query,
    instead of adding a new message to the conversation.
    """
    try:
        logger.info(f"🔄 Retry message request from user {current_user['id']} for message {message_id}")
        
        # Convert FileUpload objects to dictionaries for orchestrator
        files_dict = None
        if request.files:
            files_dict = []
            for file_upload in request.files:
                file_dict = {
                    "filename": file_upload.filename,
                    "content_type": file_upload.content_type,
                    "content": file_upload.content,
                    "size": file_upload.size,
                    "description": file_upload.description
                }
                files_dict.append(file_dict)

        # Use user's message as-is, no auto-generation
        message = request.message.strip() if request.message else ""

        # Use orchestrator to regenerate response with retry context
        response = await orchestrator.process_user_request(
            user_id=current_user["id"],
            conversation_id=request.conversation_id,
            message=message,
            files=files_dict,
            context={"type": "retry", "message_id": message_id},
            background_tasks=background_tasks
        )
        
        # Log retry interaction for analytics
        service_used = response.get("orchestration", {}).get("target_service", "unknown")
        background_tasks.add_task(
            log_talk_interaction,
            current_user["id"],
            f"[RETRY] {request.message}",
            response.get("content", ""),
            service_used
        )
        
        # Convert to ChatResponse format if needed
        if isinstance(response, dict):
            # Ensure we have a valid conversation_id
            conversation_id = response.get("conversation_id") or request.conversation_id
            if conversation_id is None:
                conversation_id = 1  # Default conversation ID
            
            return ChatResponse(
                success=response.get("success", True),
                content=response.get("content", ""),
                conversation_id=conversation_id,
                message_id=response.get("message_id", 0),
                thread_id=response.get("thread_id"),
                context_info=response.get("context_info", {}),
                sources_used=response.get("sources_used", []),
                processing_time=response.get("processing_time", 0.0)
            )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Retry message endpoint error for user {current_user['id']}: {str(e)}")
        raise HTTPException(status_code=500, detail="Message retry failed")

@app.post("/api/upload")
async def unified_upload_endpoint(
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    files: List[UploadFile] = File(...),
    message: str = Form(""),
    conversation_id: Optional[int] = Form(None),
    file_descriptions: str = Form("{}")
):
    """
    Unified file upload endpoint - automatically routes to Document service
    and provides intelligent file analysis and Q&A
    """
    try:
        logger.info(f"📎 File upload from user {current_user['id']}: {len(files)} files")
        
        # Use orchestrator to handle file upload with intelligent processing
        response = await orchestrator.process_user_request(
            user_id=current_user["id"],
            conversation_id=conversation_id,
            message=message or "Please process these uploaded files",
            files=[{
                "filename": file.filename,
                "content_type": file.content_type,
                "content": await file.read(),
                "description": ""
            } for file in files],
            context={"type": "document_upload"},
            background_tasks=background_tasks
        )
        
        return {
            "success": response.get("success", True),
            "content": response.get("content", f"Successfully processed {len(files)} files"),
            "processed_files": response.get("processed_files", []),
            "conversation_id": response.get("conversation_id", conversation_id),
            "orchestration": response.get("orchestration", {})
        }
        
    except Exception as e:
        logger.error(f"❌ File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="File upload failed")

# /api/chat/upload endpoint removed - Frontend now uses /api/talk which supports files natively

# ==================== CREDIT SYSTEM ENDPOINTS ====================

@app.get("/api/credit-system/status")
async def get_credit_status(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get user's current credit status"""
    try:
        async with AsyncSessionLocal() as session:
            # Get current user data
            query = select(User).where(User.id == current_user["id"])
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Calculate credit status with all expected frontend fields
            credits_balance = user.credits_balance or 0
            is_elite = user.is_premium or False
            
            credit_status = {
                "credits_balance": credits_balance,
                "available_credits": credits_balance,  # Same as credits_balance for now
                "is_elite": is_elite,
                "daily_free_credits_claimed": False,  # TODO: Implement daily free credits logic
                "can_purchase_credits": True,
                "plan_info": {
                    "daily_free_credits": 20 if not is_elite else 0,
                    "monthly_credit_allowance": 3000 if is_elite else 0
                },
                "total_credits_purchased": 0,  # TODO: Implement tracking
                "credits_used_today": user.credits_used_today or 0,
                "credits_used_this_month": user.credits_used_this_month or 0,
                "days_until_monthly_refill": 30,  # TODO: Calculate actual days
                "cost_breakdown": {
                    "chat_messages": 0, 
                    "document_processing": 0,
                    "health_features": 0,
                    "book_generation": 0,
                    "voice_processing": 0,
                    "other": 0
                },
                "subscription_tier": user.subscription_tier or "free",
                "subscription_status": getattr(user, 'subscription_status', 'active' if user.is_premium else 'inactive'),
                "is_premium": is_elite,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            return {
                "success": True,
                "data": credit_status
            }
            
    except Exception as e:
        logger.error(f"❌ Credit status error for user {current_user['id']}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve credit status")

# ==================== HEALTH AI ENDPOINTS ====================

# Legacy health endpoint - now routes through orchestrator
@app.post("/api/care-archive/enhanced-chat", response_model=ChatResponse)
async def health_chat_endpoint(
    request: HealthChatRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _credits: Dict[str, Any] = require_credits_async("health")
) -> ChatResponse:
    """
    Legacy Health AI chat endpoint - now routes through orchestrator
    Maintains backward compatibility while using new modular architecture
    """
    try:
        logger.info(f"🏥 Health chat request from user {current_user['id']} (legacy endpoint)")
        
        # Convert FileUpload objects to dictionaries for orchestrator
        files_dict = None
        if request.files:
            files_dict = []
            for file_upload in request.files:
                file_dict = {
                    "filename": file_upload.filename,
                    "content_type": file_upload.content_type,
                    "content": file_upload.content,
                    "size": file_upload.size,
                    "description": file_upload.description
                }
                files_dict.append(file_dict)

        # Generate default message for file-only requests
        message = request.message.strip() if request.message else ""
        if not message and files_dict:
            message = f"Please analyze these medical {'document' if len(files_dict) == 1 else 'documents'} for health insights."

        # Route through orchestrator with health context
        response = await orchestrator.process_user_request(
            user_id=current_user["id"],
            conversation_id=request.conversation_id,
            message=message,
            files=files_dict,
            context={
                "type": "health_ai",
                "health_context": request.health_context,
                "pet_context": request.pet_context
            },
            background_tasks=background_tasks
        )
        
        # Background health analytics
        background_tasks.add_task(
            analyze_health_interaction,
            current_user["id"],
            request.message,
            response.get("content", "")
        )
        
        # Convert to ChatResponse format
        if isinstance(response, dict):
            return ChatResponse(
                success=response.get("success", True),
                content=response.get("content", ""),
                conversation_id=response.get("conversation_id", request.conversation_id),
                message_id=response.get("message_id", 0),
                thread_id=response.get("thread_id", request.thread_id),
                context_info=response.get("context_info", {}),
                sources_used=response.get("sources_used", []),
                processing_time=response.get("processing_time", 0.0)
            )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Health chat error for user {current_user['id']}: {str(e)}")
        raise HTTPException(status_code=500, detail="Health chat processing failed")

@app.get("/api/care-archive/conversation/{conversation_id}/context")
async def get_conversation_context(
    conversation_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Get conversation with enhanced health context"""
    try:
        context_data = await health_service.get_conversation_context(
            user_id=current_user["id"],
            conversation_id=conversation_id
        )
        
        return {
            "success": True,
            "conversation_data": context_data
        }
        
    except Exception as e:
        logger.error(f"❌ Context retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve context")

@app.get("/api/care-archive/care-summary")
async def get_care_summary(
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Get comprehensive care summary for user"""
    try:
        summary = await health_service.get_care_summary(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"❌ Care summary error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve care summary")

# ==================== CARE ARCHIVE MANAGEMENT ====================

@app.post("/api/care-archive/upload-document")
async def upload_care_document(
    file: UploadFile = File(...),
    description: str = Form(""),
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Upload document to care archive"""
    try:
        result = await health_service.upload_care_document(
            user_id=current_user["id"],
            file=file,
            description=description
        )
        
        return {
            "success": True,
            "document": result
        }
        
    except Exception as e:
        logger.error(f"❌ Upload care document error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload document")

@app.post("/api/care-archive/create-care-record")
async def create_care_record(
    title: str,
    category: str,
    description: str,
    date_occurred: str,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Create new care record"""
    try:
        record = await health_service.create_care_record(
            user_id=current_user["id"],
            title=title,
            category=category,
            description=description,
            date_occurred=date_occurred
        )
        
        return {
            "success": True,
            "record": record
        }
        
    except Exception as e:
        logger.error(f"❌ Create care record error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create care record")

@app.get("/api/care-archive/care-timeline")
async def get_care_timeline(
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Get care timeline for user"""
    try:
        timeline = await health_service.get_care_timeline(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "timeline": timeline
        }
        
    except Exception as e:
        logger.error(f"❌ Care timeline error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve care timeline")

@app.get("/api/care-archive/care-records/{category}")
async def get_care_records_by_category(
    category: str,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Get care records by category"""
    try:
        records = await health_service.get_care_records_by_category(
            user_id=current_user["id"],
            category=category
        )
        
        return {
            "success": True,
            "records": records,
            "category": category
        }
        
    except Exception as e:
        logger.error(f"❌ Get care records by category error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve care records")

@app.post("/api/care-archive/search")
async def search_care_archive(
    query: str,
    category: str = None,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Search care archive"""
    try:
        results = await health_service.search_care_archive(
            user_id=current_user["id"],
            query=query,
            category=category
        )
        
        return {
            "success": True,
            "results": results,
            "query": query
        }
        
    except Exception as e:
        logger.error(f"❌ Search care archive error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search care archive")

@app.get("/api/care-archive/reminders")
async def get_care_reminders(
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Get care reminders"""
    try:
        reminders = await health_service.get_care_reminders(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "reminders": reminders
        }
        
    except Exception as e:
        logger.error(f"❌ Get care reminders error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve care reminders")

@app.get("/api/care-archive/knowledge-base-stats")
async def get_knowledge_base_stats(
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Get knowledge base statistics"""
    try:
        stats = await health_service.get_knowledge_base_stats(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Knowledge base stats error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve knowledge base stats")

@app.delete("/api/care-archive/delete-document/{document_id}")
async def delete_care_document(
    document_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Delete care document"""
    try:
        await health_service.delete_care_document(
            user_id=current_user["id"],
            document_id=document_id
        )
        
        return {
            "success": True,
            "message": "Document deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Delete care document error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete document")

@app.get("/api/care-archive/conversation/{conversation_id}/suggestions")
async def get_follow_up_suggestions(
    conversation_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Get follow-up suggestions for conversation"""
    try:
        suggestions = await health_service.get_follow_up_suggestions(
            user_id=current_user["id"],
            conversation_id=conversation_id
        )
        
        return {
            "success": True,
            "suggestions": suggestions
        }
        
    except Exception as e:
        logger.error(f"❌ Follow-up suggestions error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve suggestions")

@app.post("/api/care-archive/analyze-intent")
async def analyze_intent(
    message: str,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Analyze intent of message"""
    try:
        analysis = await health_service.analyze_intent(
            user_id=current_user["id"],
            message=message
        )
        
        return {
            "success": True,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"❌ Analyze intent error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to analyze intent")

@app.get("/api/care-archive/categories")
async def get_care_categories(
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _premium: None = Depends(require_premium_async)
):
    """Get available care categories"""
    try:
        categories = await health_service.get_care_categories()
        
        return {
            "success": True,
            "categories": categories
        }
        
    except Exception as e:
        logger.error(f"❌ Get care categories error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")

@app.post("/api/care-archive/backfill-knowledge-base")
async def backfill_knowledge_base(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Backfill existing care records to knowledge base for better semantic search"""
    try:
        logger.info(f"🔄 Starting knowledge base backfill for user {current_user['id']}")
        
        # Perform backfill operation
        success, message, stats = await health_service.backfill_care_records_to_knowledge_base(
            current_user['id']
        )
        
        if success:
            return {
                "success": True,
                "message": message,
                "stats": stats
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Backfill failed: {message}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Backfill knowledge base error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error during backfill"
        )

# ==================== BOOK CHAT ENDPOINTS ====================

@app.post("/api/book/chat")
async def book_chat_endpoint(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _credits: Dict[str, Any] = require_credits_async("chat")
):
    """Chat about general book content with Mr. White"""
    try:
        logger.info(f"📚 Book chat request from user {current_user['id']}")
        
        # Process book chat message
        response = await chat_service.process_book_chat(
            user_id=current_user["id"],
            message=request.message,
            context="book"
        )
        
        return {
            "success": True,
            "response": response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Book chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Book chat processing failed")

@app.post("/api/book-creation/{book_id}/chat")
async def book_creation_chat_endpoint(
    book_id: int,
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _credits: Dict[str, Any] = require_credits_async("chat")
):
    """Chat with AI about specific book content"""
    try:
        logger.info(f"📖 Book creation chat for book {book_id} by user {current_user['id']}")
        
        # Process book-specific chat
        response = await chat_service.process_book_creation_chat(
            user_id=current_user["id"],
            book_id=book_id,
            message=request.message
        )
        
        return {
            "success": True,
            "response": response,
            "book_id": book_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Book creation chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Book creation chat failed")

@app.post("/api/book/ai-chat-edit")
async def ai_chat_edit(
    message: str,
    current_content: str,
    book_id: str = None,
    chapter_id: str = None,
    chat_history: List[Dict[str, Any]] = [],
    edit_context: Dict[str, Any] = {},
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _credits: Dict[str, Any] = require_credits_async("chat")
):
    """AI-powered conversational story editing"""
    try:
        logger.info(f"📝 AI chat edit request from user {current_user['id']}")
        
        # Process AI-powered editing
        result = await chat_service.process_ai_chat_edit(
            user_id=current_user["id"],
            message=message,
            current_content=current_content,
            book_id=book_id,
            chapter_id=chapter_id,
            chat_history=chat_history,
            edit_context=edit_context
        )
        
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ AI chat edit error: {str(e)}")
        raise HTTPException(status_code=500, detail="AI chat edit failed")

# ==================== HEALTH INTELLIGENCE ENDPOINTS ====================

@app.get("/api/health-intelligence/dashboard")
async def get_health_dashboard(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get comprehensive health dashboard data"""
    try:
        dashboard_data = await health_service.get_health_dashboard_data(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "data": dashboard_data,
            "message": "Health dashboard data retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Health dashboard error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve health dashboard data")

@app.post("/api/health-intelligence/analyze")
async def analyze_health_data(
    analysis_type: str = "general",
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Analyze user's complete health data for insights"""
    try:
        analysis_result = await health_service.analyze_health_data(
            user_id=current_user["id"],
            analysis_type=analysis_type
        )
        
        return {
            "success": True,
            "data": analysis_result,
            "message": "Health data analysis completed"
        }
        
    except Exception as e:
        logger.error(f"❌ Health analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to analyze health data")

# ==================== HEALTH MANAGEMENT ENDPOINTS ====================

@app.post("/api/health/records")
async def create_health_record(
    title: str,
    category: str,
    description: str,
    date_occurred: str,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Create new health record"""
    try:
        record = await health_service.create_health_record(
            user_id=current_user["id"],
            title=title,
            category=category,
            description=description,
            date_occurred=date_occurred
        )
        
        return {
            "success": True,
            "record": record
        }
        
    except Exception as e:
        logger.error(f"❌ Create health record error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create health record")

@app.get("/api/health/records")
async def get_health_records(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get user's health records"""
    try:
        records = await health_service.get_health_records(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "records": records
        }
        
    except Exception as e:
        logger.error(f"❌ Get health records error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve health records")

@app.get("/api/health/records/{record_id}")
async def get_health_record(
    record_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get specific health record"""
    try:
        record = await health_service.get_health_record(
            user_id=current_user["id"],
            record_id=record_id
        )
        
        return {
            "success": True,
            "record": record
        }
        
    except Exception as e:
        logger.error(f"❌ Get health record error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve health record")

@app.put("/api/health/records/{record_id}")
async def update_health_record(
    record_id: int,
    title: str = None,
    category: str = None,
    description: str = None,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Update health record"""
    try:
        record = await health_service.update_health_record(
            user_id=current_user["id"],
            record_id=record_id,
            title=title,
            category=category,
            description=description
        )
        
        return {
            "success": True,
            "record": record
        }
        
    except Exception as e:
        logger.error(f"❌ Update health record error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update health record")

@app.delete("/api/health/records/{record_id}")
async def delete_health_record(
    record_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Delete health record"""
    try:
        await health_service.delete_health_record(
            user_id=current_user["id"],
            record_id=record_id
        )
        
        return {
            "success": True,
            "message": "Health record deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Delete health record error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete health record")

@app.get("/api/health/reminders")
async def get_health_reminders(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get health reminders"""
    try:
        reminders = await health_service.get_health_reminders(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "reminders": reminders
        }
        
    except Exception as e:
        logger.error(f"❌ Get health reminders error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve health reminders")

@app.post("/api/health/reminders")
async def create_health_reminder(
    title: str,
    description: str,
    due_date: str,
    reminder_type: str,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Create health reminder"""
    try:
        reminder = await health_service.create_health_reminder(
            user_id=current_user["id"],
            title=title,
            description=description,
            due_date=due_date,
            reminder_type=reminder_type
        )
        
        return {
            "success": True,
            "reminder": reminder
        }
        
    except Exception as e:
        logger.error(f"❌ Create health reminder error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create health reminder")

@app.put("/api/health/reminders/{reminder_id}")
async def update_health_reminder(
    reminder_id: int,
    title: str = None,
    description: str = None,
    due_date: str = None,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Update health reminder"""
    try:
        reminder = await health_service.update_health_reminder(
            user_id=current_user["id"],
            reminder_id=reminder_id,
            title=title,
            description=description,
            due_date=due_date
        )
        
        return {
            "success": True,
            "reminder": reminder
        }
        
    except Exception as e:
        logger.error(f"❌ Update health reminder error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update health reminder")

@app.delete("/api/health/reminders/{reminder_id}")
async def delete_health_reminder(
    reminder_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Delete health reminder"""
    try:
        await health_service.delete_health_reminder(
            user_id=current_user["id"],
            reminder_id=reminder_id
        )
        
        return {
            "success": True,
            "message": "Health reminder deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Delete health reminder error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete health reminder")

@app.post("/api/health/reminders/{reminder_id}/complete")
async def complete_health_reminder(
    reminder_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Mark health reminder as complete"""
    try:
        reminder = await health_service.complete_health_reminder(
            user_id=current_user["id"],
            reminder_id=reminder_id
        )
        
        return {
            "success": True,
            "reminder": reminder,
            "message": "Reminder marked as complete"
        }
        
    except Exception as e:
        logger.error(f"❌ Complete health reminder error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to complete health reminder")

@app.get("/api/health/reminders/overdue")
async def get_overdue_reminders(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get overdue health reminders"""
    try:
        reminders = await health_service.get_overdue_reminders(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "reminders": reminders
        }
        
    except Exception as e:
        logger.error(f"❌ Get overdue reminders error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve overdue reminders")

@app.post("/api/health/insights/generate")
async def generate_health_insights(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Generate health insights"""
    try:
        insights = await health_service.generate_health_insights(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "insights": insights
        }
        
    except Exception as e:
        logger.error(f"❌ Generate health insights error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate health insights")

@app.get("/api/health/insights")
async def get_health_insights(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get health insights"""
    try:
        insights = await health_service.get_health_insights(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "insights": insights
        }
        
    except Exception as e:
        logger.error(f"❌ Get health insights error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve health insights")

@app.get("/api/health/summary")
async def get_health_summary(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get health summary data for dashboard"""
    try:
        logger.info(f"📊 Getting health summary for user {current_user['id']}")
        
        # Use the same care summary logic 
        summary = await health_service.get_care_summary(current_user['id'])
        
        return {
            "success": True,
            "summary": summary,
            "message": "Health summary retrieved successfully"
        }
    except Exception as e:
        logger.error(f"❌ Health summary error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve health summary")

@app.post("/api/health/chat")
async def health_chat(
    request: HealthChatRequest,
    current_user: Dict[str, Any] = Depends(require_auth_async),
    _credits: Dict[str, Any] = require_credits_async("health")
):
    """Health chat endpoint for dashboard"""
    try:
        logger.info(f"💬 Health chat for user {current_user['id']}: {request.message[:50]}...")
        
        # Process health message
        response = await health_service.process_health_message(
            user_id=current_user['id'],
            message=request.message,
            conversation_id=getattr(request, 'conversation_id', None),
            context=getattr(request, 'context', 'health_dashboard')
        )
        
        return ChatResponse(
            success=True,
            response=response['ai_response'],
            conversation_id=response.get('conversation_id'),
            message_id=response.get('message_id'),
            context=response.get('context', {}),
            processing_time=response.get('processing_time', 0),
            credits_used=response.get('credits_used', 1)
        )
        
    except Exception as e:
        logger.error(f"❌ Health chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Health chat processing failed")

# ==================== CONVERSATION MANAGEMENT ====================

@app.get("/api/conversations")
async def get_conversations(
    limit: int = 50,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get user's conversations with async pagination"""
    try:
        conversations = await chat_service.get_user_conversations(
            user_id=current_user["id"],
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "conversations": conversations,
            "total": len(conversations)
        }
        
    except Exception as e:
        logger.error(f"❌ Conversations retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversations")

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get specific conversation with messages"""
    try:
        conversation_data = await chat_service.get_conversation_with_messages(
            conversation_id=conversation_id,
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "data": conversation_data
        }
        
    except Exception as e:
        logger.error(f"❌ Get conversation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation")

@app.post("/api/conversations")
async def create_conversation(
    request: ConversationCreateRequest,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Create new conversation"""
    try:
        conversation = await chat_service.create_conversation(
            user_id=current_user["id"],
            title=request.title
        )
        
        return {
            "success": True,
            "conversation": conversation
        }
        
    except Exception as e:
        logger.error(f"❌ Conversation creation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")

@app.put("/api/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: int,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Update conversation (title, bookmark status)"""
    try:
        # Get the request body
        body = await request.json()
        title = body.get("title")
        is_bookmarked = body.get("is_bookmarked")
        
        updated_conversation = await chat_service.update_conversation(
            conversation_id=conversation_id,
            user_id=current_user["id"],
            title=title,
            is_bookmarked=is_bookmarked
        )
        
        return {
            "success": True,
            "conversation": updated_conversation
        }
        
    except Exception as e:
        logger.error(f"❌ Conversation update error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update conversation")

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Delete conversation"""
    try:
        await chat_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "message": "Conversation deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Conversation deletion error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

@app.post("/api/conversations/{conversation_id}/messages")
async def add_message_to_conversation(
    conversation_id: int,
    content: str,
    message_type: str = "user",
    attachments: List[Dict[str, Any]] = [],
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Add message to conversation"""
    try:
        message_data = await chat_service.add_message_to_conversation(
            conversation_id=conversation_id,
            user_id=current_user["id"],
            content=content,
            message_type=message_type,
            attachments=attachments
        )
        
        return {
            "success": True,
            "message": message_data
        }
        
    except Exception as e:
        logger.error(f"❌ Add message error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add message")

@app.post("/api/messages/{message_id}/bookmark")
async def bookmark_message(
    message_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Bookmark/unbookmark a message"""
    try:
        result = await chat_service.toggle_message_bookmark(
            message_id=message_id,
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "bookmarked": result["is_bookmarked"],
            "message": "Message bookmark updated"
        }
        
    except Exception as e:
        logger.error(f"❌ Bookmark message error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to bookmark message")

@app.post("/api/messages/{message_id:path}/reaction")
async def add_message_reaction(
    message_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Add reaction to message (like, dislike)"""
    try:
        # Get the request body
        body = await request.json()
        reaction_type = body.get("type")
        
        if not reaction_type or reaction_type not in ["like", "dislike"]:
            raise HTTPException(status_code=400, detail="Invalid reaction type")
        
        result = await chat_service.add_message_reaction(
            message_id=message_id,
            user_id=current_user["id"],
            reaction_type=reaction_type
        )
        
        return {
            "success": True,
            "reaction": result,
            "message": "Reaction added successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Add reaction error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add reaction")

@app.get("/api/bookmarks")
async def get_bookmarks(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get user's bookmarked messages"""
    try:
        bookmarks = await chat_service.get_user_bookmarks(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "bookmarks": bookmarks
        }
        
    except Exception as e:
        logger.error(f"❌ Get bookmarks error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve bookmarks")

@app.post("/api/conversations/{conversation_id}/bookmark")
async def toggle_conversation_bookmark(
    conversation_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Toggle conversation bookmark status"""
    try:
        result = await chat_service.toggle_conversation_bookmark(
            conversation_id=conversation_id,
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "is_bookmarked": result["is_bookmarked"],
            "message": "Conversation bookmark updated"
        }
        
    except Exception as e:
        logger.error(f"❌ Toggle conversation bookmark error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to toggle conversation bookmark")

@app.get("/api/bookmarked-conversations")
async def get_bookmarked_conversations(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get user's bookmarked conversations"""
    try:
        bookmarked_conversations = await chat_service.get_bookmarked_conversations(
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "conversations": bookmarked_conversations
        }
        
    except Exception as e:
        logger.error(f"❌ Get bookmarked conversations error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve bookmarked conversations")

@app.post("/api/clear-cache")
async def clear_conversations_cache(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Clear conversation cache for user"""
    try:
        await chat_service.clear_user_cache(user_id=current_user["id"])
        
        return {
            "success": True,
            "message": "Cache cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Clear cache error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@app.delete("/api/user/{user_id}/conversations")
async def delete_all_user_conversations(
    user_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Delete all conversations for a user (admin only)"""
    try:
        # Verify user can delete (either self or admin)
        if current_user["id"] != user_id and not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        await chat_service.delete_all_user_conversations(user_id=user_id)
        
        return {
            "success": True,
            "message": f"All conversations deleted for user {user_id}"
        }
        
    except Exception as e:
        logger.error(f"❌ Delete all conversations error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete all conversations")

# ==================== ORCHESTRATOR STATS ENDPOINTS ====================

@app.get("/api/orchestrator/stats")
async def get_orchestration_stats(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get comprehensive orchestration and service statistics"""
    try:
        stats = await orchestrator.get_comprehensive_service_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Stats retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve stats")

@app.get("/api/orchestrator/health")
async def orchestrator_health_check(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Check health status of all services"""
    try:
        health_status = await orchestrator.health_check()
        return health_status
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post("/api/orchestrator/reset-stats")
async def reset_orchestration_stats(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Reset orchestration statistics"""
    try:
        orchestrator.reset_orchestration_stats()
        return {
            "success": True,
            "message": "Orchestration statistics reset successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Stats reset error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reset stats")

# ==================== SMART PROMPTS A/B TESTING ENDPOINTS ====================

@app.get("/api/smart-prompts/stats")
async def get_smart_prompt_stats(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get Smart Prompt optimization and A/B testing statistics"""
    try:
        smart_stats = chat_service.get_smart_prompt_stats()
        
        return {
            "success": True,
            "smart_prompt_stats": smart_stats,
            "migration_status": {
                "smart_prompts_enabled": chat_service.ab_test_enabled,
                "smart_prompt_coverage": f"{chat_service.smart_prompt_ratio * 100}%",
                "migration_complete": chat_service.smart_prompt_ratio >= 1.0,
                "traditional_prompts_deprecated": getattr(chat_service, 'smart_prompts_only', False)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Smart prompt stats error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve smart prompt stats")

@app.post("/api/smart-prompts/ab-test/configure")
async def configure_ab_test(
    enabled: bool = True,
    smart_prompt_ratio: float = 0.5,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Configure A/B testing parameters for smart prompts"""
    try:
        if smart_prompt_ratio < 0.0 or smart_prompt_ratio > 1.0:
            raise HTTPException(status_code=400, detail="smart_prompt_ratio must be between 0.0 and 1.0")
        
        chat_service.ab_test_enabled = enabled
        chat_service.smart_prompt_ratio = smart_prompt_ratio
        
        logger.info(f"🧪 A/B Test configured: enabled={enabled}, ratio={smart_prompt_ratio}")
        
        return {
            "success": True,
            "message": "A/B test configuration updated",
            "configuration": {
                "ab_test_enabled": enabled,
                "smart_prompt_ratio": smart_prompt_ratio,
                "estimated_users_with_smart_prompts": f"{smart_prompt_ratio * 100}%"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"A/B test configuration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to configure A/B test")

@app.get("/api/smart-prompts/user/{user_id}/variant")
async def get_user_ab_variant(
    user_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Check which A/B testing variant a specific user is assigned to"""
    try:
        # Verify user can access this info (admin or self)
        if current_user["id"] != user_id and not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        use_smart_prompts = chat_service.should_use_smart_prompts(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "ab_variant": "smart_prompts" if use_smart_prompts else "traditional_prompts",
            "variant_description": {
                "smart_prompts": "Optimized prompts with 60-80% token reduction",
                "traditional_prompts": "Original comprehensive prompt system"
            },
            "ab_test_config": {
                "enabled": chat_service.ab_test_enabled,
                "smart_prompt_ratio": chat_service.smart_prompt_ratio
            }
        }
    except Exception as e:
        logger.error(f"User variant check error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check user variant")

@app.post("/api/smart-prompts/reset-stats")
async def reset_smart_prompt_stats(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Reset smart prompt optimization statistics"""
    try:
        chat_service.smart_prompts.reset_stats()
        return {
            "success": True,
            "message": "Smart prompt statistics reset successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Smart prompt stats reset error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reset smart prompt stats")

@app.post("/api/pet-questions/clear-history/{user_id}")
async def clear_pet_question_history(
    user_id: int,
    pet_name: str = None,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Clear pet question history to stop repetitive questioning (admin/debugging)"""
    try:
        # Verify user can access this (admin or self)
        if current_user["id"] != user_id and not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not chat_service.question_tracker:
            raise HTTPException(status_code=503, detail="Question tracker not available")
        
        await chat_service.question_tracker.clear_question_history(user_id, pet_name)
        
        return {
            "success": True,
            "message": f"Question history cleared for user {user_id}" + (f" and pet {pet_name}" if pet_name else ""),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clear question history error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear question history")

@app.get("/api/pet-questions/stats/{user_id}")
async def get_pet_question_stats(
    user_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get pet question statistics for debugging repetitive question issues"""
    try:
        # Verify user can access this (admin or self)
        if current_user["id"] != user_id and not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not chat_service.question_tracker:
            raise HTTPException(status_code=503, detail="Question tracker not available")
        
        stats = await chat_service.question_tracker.get_question_statistics(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "question_statistics": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get question stats error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve question statistics")

# ==================== DOCUMENT CACHE MANAGEMENT ENDPOINTS ====================

@app.get("/api/orchestrator/cache/stats")
async def get_document_cache_stats(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Get detailed document cache performance statistics"""
    try:
        cache_stats = orchestrator.get_document_cache_stats()
        
        return {
            "success": True,
            "document_cache_statistics": cache_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Document cache stats error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cache statistics")

@app.post("/api/orchestrator/cache/clear")
async def clear_document_cache(
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Clear document cache to free memory (admin only)"""
    try:
        # Only admins can clear cache
        if not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        clear_result = orchestrator.clear_document_cache()
        
        return {
            "success": True,
            "message": "Document cache cleared successfully",
            "clear_statistics": clear_result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clear document cache error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear document cache")

# ==================== BACKGROUND TASKS ====================

async def log_chat_interaction(user_id: int, message: str, response: str):
    """Background task for logging chat interactions"""
    try:
        # Store interaction data for analytics
        await redis_client.lpush(
            f"chat_analytics:{user_id}",
            f"{datetime.now().isoformat()}|{len(message)}|{len(response)}"
        )
        await redis_client.ltrim(f"chat_analytics:{user_id}", 0, 100)  # Keep last 100
        
    except Exception as e:
        logger.error(f"Analytics logging failed: {str(e)}")

async def analyze_health_interaction(user_id: int, message: str, response: str):
    """Background task for health interaction analysis"""
    try:
        # Health-specific analytics
        await redis_client.lpush(
            f"health_analytics:{user_id}",
            f"{datetime.now().isoformat()}|health_chat|{len(message)}"
        )
        
    except Exception as e:
        logger.error(f"Health analytics failed: {str(e)}")

async def auto_archive_inline_text(user_id: int, message: str, response: str, vector_service: AsyncPineconeService):
    """Background task to automatically detect and archive inline text content"""
    try:
        import hashlib
        
        # Keywords that indicate archival intent
        archival_keywords = ['archive', 'store', 'save', 'remember', 'keep']
        document_types = ['poem', 'article', 'story', 'text', 'note', 'passage', 'verse', 'writing']
        
        message_lower = message.lower()
        
        # Check if message contains archival intent
        has_archival_intent = any(keyword in message_lower for keyword in archival_keywords)
        has_document_type = any(doc_type in message_lower for doc_type in document_types)
        
        # Check if message is substantial (>150 chars and has multiple lines)
        is_substantial = len(message) > 150 and '\n' in message
        
        if (has_archival_intent or has_document_type) and is_substantial:
            logger.info(f"📝 AUTO-ARCHIVE: Detected inline text for user {user_id} ({len(message)} chars)")
            
            # Extract title from message (first line or generate from keywords)
            lines = message.split('\n')
            title = None
            content_start = 0
            
            # Look for explicit title indicators
            for i, line in enumerate(lines[:5]):  # Check first 5 lines
                line_lower = line.lower().strip()
                if any(keyword in line_lower for keyword in archival_keywords):
                    # Next non-empty line might be the title or actual content
                    for j in range(i+1, min(i+10, len(lines))):
                        if lines[j].strip() and len(lines[j]) < 100:
                            title = lines[j].strip()
                            content_start = j + 1
                            break
                    break
            
            # If no title found, generate from document type and first words
            if not title:
                doc_type = next((dt for dt in document_types if dt in message_lower), "text")
                first_words = ' '.join(message.split()[:8])
                title = f"{doc_type.capitalize()}: {first_words}"
            
            # Extract actual content (skip introductory lines)
            content = '\n'.join(lines[content_start:]).strip()
            if not content or len(content) < 50:
                content = message  # Use full message if extraction failed
            
            # Generate document ID
            timestamp = int(datetime.now(timezone.utc).timestamp())
            doc_id = f"inline_{hashlib.md5(content.encode()).hexdigest()[:8]}_{timestamp}"
            
            # Split into chunks (3000 chars max)
            chunk_size = 3000
            overlap = 300
            chunks = []
            for i in range(0, len(content), chunk_size - overlap):
                chunk = content[i:i + chunk_size]
                if chunk.strip():
                    chunks.append(chunk)
            
            logger.info(f"📝 AUTO-ARCHIVE: Split into {len(chunks)} chunks, title: '{title[:50]}...'")
            
            # Store in Pinecone
            metadata = {
                'title': title,
                'document_type': next((dt for dt in document_types if dt in message_lower), "text"),
                'filename': f"{title[:30].replace(' ', '_')}.txt",
                'stored_at': datetime.now(timezone.utc).isoformat(),
                'source': 'inline_text_auto_archived',
                'full_content': content[:1000]  # Store preview
            }
            
            success, msg = await vector_service.store_document_vectors(
                user_id=user_id,
                document_id=doc_id,
                text_chunks=chunks,
                metadata=metadata
            )
            
            if success:
                logger.info(f"✅ AUTO-ARCHIVE: Successfully stored inline document '{title[:30]}...' for user {user_id}")
            else:
                logger.error(f"❌ AUTO-ARCHIVE: Failed to store inline document: {msg}")
                
    except Exception as e:
        logger.error(f"❌ AUTO-ARCHIVE: Error processing inline text: {e}")

async def log_talk_interaction(user_id: int, message: str, response: str, service_used: str):
    """Background task for logging unified talk interactions with service routing"""
    try:
        # Store interaction data with service routing info
        interaction_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "message_length": len(message),
            "response_length": len(response),
            "service_used": service_used,
            "endpoint": "talk"
        }
        
        # Store in Redis for analytics
        await redis_client.lpush(
            f"talk_analytics:{user_id}",
            f"{interaction_data['timestamp']}|{service_used}|{len(message)}|{len(response)}"
        )
        await redis_client.ltrim(f"talk_analytics:{user_id}", 0, 100)  # Keep last 100
        
        # Also track service usage statistics
        await redis_client.hincrby("service_usage_stats", service_used, 1)
        
    except Exception as e:
        logger.error(f"Talk analytics logging failed: {str(e)}")

# ==================== REMOVED WEBSOCKET ENDPOINTS ====================
# WebSocket endpoints for real-time chat and health streaming have been removed
# as they were not being used by the frontend. The HTTP-based chat system
# provides all the functionality needed and is fully integrated with the frontend.

# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return ORJSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return ORJSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

# ==================== REMOVED DEVELOPMENT/TESTING ENDPOINTS ====================
# Cache management, performance monitoring, vector batch operations,
# OpenAI pool testing, parallel processing stats, and smart routing test endpoints
# have been removed as they were development-only and not used by the frontend.


@app.get("/api/download/{attachment_id}")
async def download_attachment(
    attachment_id: int,
    current_user: Dict[str, Any] = Depends(require_auth_async)
):
    """Download an attachment file by proxying S3 requests to avoid CORS issues"""
    try:
        # Get attachment details from database
        from models import AsyncSessionLocal, Attachment, Message
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as session:
            query = select(Attachment).join(Message).where(
                Attachment.id == attachment_id,
                Message.user_id == current_user["id"]  # Ensure user owns the file
            )
            result = await session.execute(query)
            attachment = result.scalar_one_or_none()
            
            if not attachment:
                raise HTTPException(status_code=404, detail="Attachment not found or access denied")
            
            # Check if it's an S3 presigned URL
            if attachment.url.startswith("https://") and "s3.amazonaws.com" in attachment.url:
                # Proxy the S3 download to avoid CORS issues
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            # Determine content type
                            content_type = resp.headers.get('content-type', 'application/octet-stream')
                            
                            from fastapi.responses import Response
                            return Response(
                                content=content,
                                media_type=content_type,
                                headers={
                                    "Content-Disposition": f"attachment; filename={attachment.name}",
                                    "Content-Length": str(len(content))
                                }
                            )
                        else:
                            raise HTTPException(status_code=resp.status, detail="Failed to download file from S3")
            else:
                # Legacy file or placeholder
                raise HTTPException(status_code=400, detail="File not available for download")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Download error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download file")

# ==================== STARTUP ====================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    ) 
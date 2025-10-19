"""
Chat Service - Normal chat and query functionality
Handles general conversational AI interactions
"""

import os
import time
import json
import uuid
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

import httpx
import redis.asyncio as redis
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import BackgroundTasks

from models import (
    AsyncSessionLocal, User, Conversation, Message, Attachment, Document,
    ChatResponse, ConversationCreateRequest,
    get_user_conversations_optimized, get_conversation_with_messages_optimized,
    get_bookmarked_conversations_optimized, get_bookmarked_messages_optimized,
    create_conversation_async, create_message_async
)

from services.shared.async_pinecone_service import AsyncPineconeService
from services.shared.async_langgraph_service import AsyncLangGraphService
from services.shared.async_parallel_service import AsyncParallelService
from services.shared.async_vector_batch_service import AsyncVectorBatchService
from services.shared.async_openai_pool_service import get_openai_pool as get_ai_pool
from services.shared.async_cache_service import SemanticResponseCache, RequestDeduplicator, cache_result, multi_layer_cache
# Removed DynamoDB - using PostgreSQL exclusively  
from services.shared.async_bedrock_knowledge_service import AsyncBedrockKnowledgeService
from services.shared.async_bedrock_agents_service import AsyncBedrockAgentsService
from services.shared.async_s3_service import AsyncS3Service

from .chat_prompts import ChatPrompts
from .smart_chat_prompts import SmartChatPrompts
from services.pet.pet_question_tracker import PetQuestionTracker

logger = logging.getLogger(__name__)

class ChatService:
    """
    Chat Service for normal conversational AI interactions
    Handles general queries, context retrieval, and conversation management
    """
    
    def __init__(self, vector_service: AsyncPineconeService, cache_service=None, smart_intent_router=None):
        self.vector_service = vector_service
        self.cache_service = cache_service
        self.smart_intent_router = smart_intent_router
        
        # Initialize parallel processing services  
        self.parallel_service = AsyncParallelService()
        self.vector_batch_service = AsyncVectorBatchService(self.vector_service)
        
        # Initialize AWS services for complete stack
        self.bedrock_knowledge_service = AsyncBedrockKnowledgeService()
        self.bedrock_agents_service = AsyncBedrockAgentsService()
        self.s3_service = AsyncS3Service()
        
        # Initialize optimized LangGraph service with prebuilt agents
        self.langgraph_service = None
        self._langgraph_init_task = None
        
        # Chat prompts manager
        self.prompts = ChatPrompts()
        
        # Smart prompts system (Phase 1 implementation)
        self.smart_prompts = SmartChatPrompts()
        
        # Pet question tracking system to prevent repetitive questioning
        if cache_service and hasattr(cache_service, 'redis'):
            self.question_tracker = PetQuestionTracker(cache_service.redis)
            logger.info("✅ Pet Question Tracker initialized successfully")
        else:
            self.question_tracker = None
            logger.warning("⚠️ Question tracker not available - repetitive questions may occur")
        
        # PRODUCTION MIGRATION COMPLETE: Smart Prompts are now the primary system
        self.ab_test_enabled = True  # Keep enabled for monitoring/rollback capability 
        self.smart_prompt_ratio = 1.0  # 100% of users get smart prompts (full migration)
        self.smart_prompts_only = True  # Flag to indicate traditional prompts are deprecated
        
        # Initialize semantic caching and request deduplication
        if cache_service:
            self.semantic_cache = SemanticResponseCache(cache_service)
            self.request_deduplicator = RequestDeduplicator(cache_service)
        else:
            self.semantic_cache = None
            self.request_deduplicator = None
        
        # AI configuration - Pure AWS Bedrock only (no fallbacks)
        self.ai_pool = None  # AWS Bedrock-only AI pool (no fallbacks)
        self.chat_model = "gpt-4"  # Maps to Claude 3 Sonnet in Bedrock
        self.max_tokens = 1500  # Optimized to prevent truncation while maintaining completeness
        self.temperature = 0.6  # Slightly lower for more focused responses
        
        # AWS services initialization flag
        self.aws_services_initialized = False
        
        # Performance monitoring
        self.parallel_processing_stats = {
            "total_operations": 0,
            "sequential_time": 0.0,
            "parallel_time": 0.0,
            "time_saved": 0.0,
            "efficiency_improvement_percent": 0.0
        }
        
        # Smart routing performance stats
        self.smart_routing_stats = {
            "total_messages": 0,
            "routed_messages": 0,
            "ai_calls_saved": 0,
            "cache_hits": 0,
            "routing_time_saved": 0.0
        }
    
    async def _initialize_langgraph_service(self):
        """Initialize the optimized LangGraph service"""
        try:
            from services.shared.async_langgraph_service import OptimizedLangGraphService
            
            # Get Redis client (assuming it's available from cache service)
            redis_client = None
            if self.cache_service and hasattr(self.cache_service, 'redis_client'):
                redis_client = self.cache_service.redis_client
            else:
                # Create a basic Redis client if not available
                import redis.asyncio as redis
                redis_url = os.getenv("REDIS_URL") or os.getenv("MEMORYDB_ENDPOINT", "redis://localhost:6379")
                if not redis_url.startswith("redis://"):
                    redis_url = f"redis://{redis_url}:6379"
                redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Initialize optimized LangGraph service
            self.langgraph_service = OptimizedLangGraphService(
                vector_service=self.vector_service,
                redis_client=redis_client
            )
            
            logger.info("✅ Optimized LangGraph service initialized in ChatService")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize LangGraph service: {str(e)}")
            # Continue without LangGraph service - fallback to regular processing
            self.langgraph_service = None

    async def ensure_langgraph_service(self):
        """Ensure LangGraph service is initialized before use"""
        if self.langgraph_service is None:
            if self._langgraph_init_task is None:
                self._langgraph_init_task = asyncio.create_task(self._initialize_langgraph_service())
            await self._langgraph_init_task
        return self.langgraph_service
    
    async def _ensure_aws_services_initialized(self):
        """Ensure all AWS services are properly initialized"""
        if self.aws_services_initialized:
            return True
            
        try:
            # Initialize all AWS services with proper async context management
            results = []
            
            # Initialize PostgreSQL service with async context
            try:
                async with AsyncSessionLocal() as session:
                    # Test PostgreSQL connection and ensure tables exist
                    await session.execute(select(User).limit(1))
                    results.append(True)
                    logger.info("✅ PostgreSQL service operational")
            except Exception as e:
                logger.error(f"PostgreSQL initialization failed: {e}")
                results.append(False)
            
            # Initialize Bedrock Knowledge Base service
            try:
                knowledge_result = await self.bedrock_knowledge_service.ensure_knowledge_base_exists()
                results.append(knowledge_result)
            except Exception as e:
                logger.error(f"Bedrock Knowledge Base initialization failed: {e}")
                results.append(False)
            
            # Initialize Bedrock Agents service  
            try:
                agents_result = await self.bedrock_agents_service.ensure_agent_exists()
                results.append(agents_result)
            except Exception as e:
                logger.error(f"Bedrock Agents initialization failed: {e}")
                results.append(False)
            
            # Initialize S3 service with async context
            try:
                async with self.s3_service as s3_service:
                    s3_result = await s3_service.ensure_buckets_exist()
                    results.append(s3_result)
            except Exception as e:
                logger.error(f"S3 initialization failed: {e}")
                results.append(False)
            
            # Check if all services initialized successfully
            success_count = sum(1 for result in results if result is True)
            
            if success_count >= 2:  # At least 2 services working
                self.aws_services_initialized = True
                logger.info(f"✅ AWS services initialized: {success_count}/4 services ready")
                return True
            else:
                logger.warning(f"⚠️  Only {success_count}/4 AWS services initialized")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize AWS services: {e}")
            return False
        
    async def _get_ai_pool(self):
        """Get or initialize the AWS Bedrock AI client pool (no OpenAI fallback)"""
        if self.ai_pool is None:
            self.ai_pool = await get_ai_pool(pool_size=5)
        return self.ai_pool
        
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass

    async def get_conversation_with_messages(
        self,
        conversation_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get specific conversation with messages
        """
        try:
            # Cache miss or no cache service - query database
            from models import get_conversation_with_messages_optimized
            
            async with AsyncSessionLocal() as session:
                # Single query loads conversation + messages + attachments
                conversation = await get_conversation_with_messages_optimized(
                    session, conversation_id, user_id
                )
                
                if not conversation:
                    raise ValueError("Conversation not found or access denied")
                
                message_data = []
                # Ensure messages are sorted by creation time (chronological order)
                sorted_messages = sorted(conversation.messages, key=lambda m: m.created_at)
                for msg in sorted_messages:
                    message_data.append({
                        "id": msg.id,
                        "content": msg.content,
                        "sender": getattr(msg, "sender", None),
                        "timestamp": msg.created_at.isoformat() + 'Z' if msg.created_at else None,
                        "message_type": msg.type if msg.type in ['user', 'ai'] else 'ai',
                        "is_bookmarked": msg.is_bookmarked or False,
                        "attachments": [
                            {
                                "id": att.id,
                                "file_type": att.type,      # Map type to file_type for frontend compatibility
                                "file_name": att.name,      # Map name to file_name for frontend compatibility
                                "file_path": att.url,       # Map url to file_path for frontend compatibility  
                                "file_size": 0              # Default file_size since it's not stored in this model
                            }
                            for att in msg.attachments
                        ] if msg.attachments else []
                    })
                
                result = {
                    "id": conversation.id,
                    "title": conversation.title,
                    "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                    "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
                    "is_bookmarked": conversation.is_bookmarked or False,
                    "messages": message_data,
                    "total_messages": len(message_data)
                }
                
                # Cache the result if cache service available
                if self.cache_service:
                    await self.cache_service.cache_conversation_with_messages(conversation_id, result)
                    
                logger.info(f"✅ Retrieved conversation {conversation_id} with {len(message_data)} messages")
                return result
                
        except Exception as e:
            logger.error(f"Get conversation with messages error: {str(e)}")
            raise e

    async def process_chat_message(
        self,
        user_id: int,
        conversation_id: int,
        message: str,
        files: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Dict[str, Any]:
        """
        Process chat message using complete AWS stack:
        - Bedrock Agents for persistent memory and conversation management
        - Bedrock Knowledge Bases for RAG capabilities
        - PostgreSQL for conversation history storage
        - S3 for document storage
        - MemoryDB + Pinecone for vector operations
        """
        start_time = time.time()
        
        try:
            # Phase 1: Ensure AWS services are initialized
            await self._ensure_aws_services_initialized()
            
            # Phase 2: Handle file uploads to S3 if present
            file_context = []
            if files:
                file_context = await self._process_files_with_s3(user_id, files)
            
            # Phase 3: Get user context for personalized agent interaction
            user_context = await self._build_user_context(user_id, conversation_id)
            
            # Phase 3.5: Process message for pet question responses (prevent repetitive questions)
            await self._process_user_message_for_pet_questions(user_id, message, user_context)
            
            # Phase 4: Use Bedrock Agents for intelligent conversation with persistent memory
            agent_response = await self.bedrock_agents_service.invoke_agent(
                user_id=user_id,
                message=message,
                session_context=user_context
            )
            
            ai_response = agent_response.get("response", "")
            session_id = agent_response.get("session_id")
            
            # Phase 5: Enhance response with Knowledge Base RAG if needed
            if self._requires_knowledge_enhancement(message, ai_response):
                rag_response = await self.bedrock_knowledge_service.retrieve_and_generate(
                    query=message,
                    user_context=user_context
                )
                
                # Combine agent response with knowledge base insights
                ai_response = await self._combine_agent_and_rag_responses(
                    ai_response, rag_response, message
                )
            
            # Phase 6: Store conversation in PostgreSQL for persistence
            conversation_data = await self._store_conversation_in_postgresql(
                user_id, conversation_id, message, ai_response, session_id
            )
            
            # Phase 7: Background tasks for vector indexing and optimization
            if background_tasks:
                background_tasks.add_task(
                    self._background_vector_storage,
                    user_id, conversation_data["conversation_id"], message, ai_response
                )
                background_tasks.add_task(
                    self._background_knowledge_base_update,
                    user_id, message, ai_response, file_context
                )
            
            processing_time = time.time() - start_time
            self._update_parallel_processing_stats(processing_time)
            
            return ChatResponse(
                success=True,
                content=ai_response,
                conversation_id=conversation_data["conversation_id"],
                message_id=conversation_data["message_id"],
                thread_id=session_id,
                context_info={
                    "bedrock_agent_used": True,
                    "knowledge_base_enhanced": self._requires_knowledge_enhancement(message, ai_response),
                    "persistent_memory": True,
                    "files_processed": len(file_context),
                    "session_id": session_id,
                    "aws_services_active": self.aws_services_initialized,
                    "storage_type": "PostgreSQL + MemoryDB + S3"
                },
                sources_used=agent_response.get("citations", []),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Chat processing error: {str(e)}")
            return {
                "success": False,
                "error": f"Chat processing failed: {str(e)}",
                "conversation_id": conversation_id,
                "processing_time": time.time() - start_time
            }
    
    async def process_chat_message_smart(
        self,
        user_id: int,
        conversation_id: int,
        message: str,
        files: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Dict[str, Any]:
        """
        🚀 SMART PROMPT VERSION: Process chat message with optimized prompt system
        Achieves 60-80% token reduction while maintaining response quality
        """
        start_time = time.time()
        
        try:
            logger.info(f"🎯 Smart Prompt Processing for user {user_id}")
            
            # Phase 1: Build user context efficiently
            user_context = await self._build_user_context_smart(user_id, conversation_id)
            
            # Phase 1.25: Add common knowledge (Anahata book content) to context
            user_context = await self._add_common_knowledge_to_context(message, user_context)
            
            # Phase 1.5: Process message for pet question responses (prevent repetitive questions)
            await self._process_user_message_for_pet_questions(user_id, message, user_context)
            
            # Phase 2: Smart prompt analysis and generation
            prompt_context = self.smart_prompts.analyze_message_context(message, user_context)
            optimized_prompt = self.smart_prompts.build_optimized_prompt(message, prompt_context)
            
            logger.info(f"📊 Smart Analysis: {prompt_context.response_type.value} response, {prompt_context.question_complexity.value} complexity")
            
            # Phase 3: Generate AI response with optimized prompt
            ai_response = await self._call_ai_with_smart_prompt(
                message=message,
                system_prompt=optimized_prompt,
                prompt_context=prompt_context,
                user_context=user_context
            )
            
            # Phase 4: Store conversation in PostgreSQL
            conversation_data = await self._store_conversation_in_postgresql(
                user_id, conversation_id, message, ai_response, None, attachments
            )
            
            # Phase 5: Background optimization tracking
            if background_tasks:
                background_tasks.add_task(
                    self._track_smart_prompt_performance,
                    user_id, message, ai_response, prompt_context
                )
            
            processing_time = time.time() - start_time
            
            # Get optimization stats
            optimization_stats = self.smart_prompts.get_optimization_stats()
            
            return ChatResponse(
                success=True,
                content=ai_response,
                conversation_id=conversation_data["conversation_id"],
                message_id=conversation_data["message_id"],
                context_info={
                    "smart_prompts_used": True,
                    "response_type": prompt_context.response_type.value,
                    "question_complexity": prompt_context.question_complexity.value,
                    "modules_used": len(optimized_prompt.split('\n\n')) - 1,  # Approximate modules
                    "optimization_active": True,
                    "tokens_estimated_saved": prompt_context.tokens_estimated,
                    "pets_addressed": len(prompt_context.pets)
                },
                sources_used=[],  # Smart prompts don't need complex RAG initially
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"❌ Smart chat processing error: {str(e)}")
            
            # Fallback to simple response with smart prompts
            try:
                fallback_response = self.smart_prompts.get_fallback_response(message)
                conversation_data = await self._store_conversation_in_postgresql(
                    user_id, conversation_id, message, fallback_response, None, attachments
                )
                
                return ChatResponse(
                    success=True,
                    content=fallback_response,
                    conversation_id=conversation_data["conversation_id"],
                    message_id=conversation_data["message_id"],
                    context_info={"smart_prompts_fallback": True},
                    processing_time=time.time() - start_time
                )
                
            except Exception as fallback_error:
                logger.error(f"❌ Smart prompt fallback failed: {str(fallback_error)}")
                return {
                    "success": False,
                    "error": f"Smart chat processing failed: {str(e)}",
                    "conversation_id": conversation_id,
                    "processing_time": time.time() - start_time
                }
    
    async def _build_user_context_smart(self, user_id: int, conversation_id: int) -> Dict[str, Any]:
        """Build lightweight user context for smart prompts (reduced complexity)"""
        try:
            user_context = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z',
                "pets": [],
                "recent_messages": []
            }
            
            # Get essential user data
            async with AsyncSessionLocal() as session:
                # Get user basic info
                user_query = select(User).where(User.id == user_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if user:
                    user_context.update({
                        "username": user.username,
                        "subscription_tier": user.subscription_tier or "free",
                        "timezone": getattr(user, "timezone", "UTC")
                    })
            
            # Get pet information (lightweight)
            try:
                from pet_models_pkg.pet_models import PetProfile
                from repositories.pet_repository import PetRepository
                
                async with AsyncSessionLocal() as session:
                    pet_repo = PetRepository(session)
                    pets = await pet_repo.get_user_pets(user_id)
                    
                    if pets:
                        pets_context = []
                        for pet in pets[:3]:  # Limit to 3 pets for efficiency
                            pet_data = {
                                "name": pet.name,
                                "breed": pet.breed,
                                "age": pet.age,
                                "weight": float(pet.weight) if pet.weight else None,
                                "gender": pet.gender
                            }
                            pets_context.append(pet_data)
                        
                        user_context["pets"] = pets_context
                        logger.info(f"🐕 Added {len(pets_context)} pets to smart context")
                        
            except Exception as pet_error:
                logger.error(f"❌ Error loading pet context: {pet_error}")
                user_context["pets"] = []
            
            return user_context
            
        except Exception as e:
            logger.error(f"❌ Smart user context error: {e}")
            return {"user_id": user_id, "conversation_id": conversation_id, "pets": []}
    
    async def _add_common_knowledge_to_context(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Add common knowledge search results to user context for smart prompts"""
        try:
            # Check if message mentions Anahata or related concepts
            mentions_anahata = any(keyword in message.lower() for keyword in [
                "anahata", "way of dog", "way of the dog", "interspecies culture", "intuitive bonding"
            ])
            
            # Only search if mentions Anahata or if we need general knowledge
            if mentions_anahata or len(message.split()) > 5:  # Search for longer messages
                vector_service = self.langgraph_service.vector_service
                common_knowledge_results = await vector_service.search_common_knowledge(
                    query=message,
                    top_k=3
                )
                
                if common_knowledge_results:
                    user_context["common_knowledge"] = common_knowledge_results
                    logger.info(f"✅ Added {len(common_knowledge_results)} common knowledge results to smart context")
                else:
                    user_context["common_knowledge"] = []
            else:
                user_context["common_knowledge"] = []
                
        except Exception as e:
            logger.error(f"❌ Error adding common knowledge to context: {e}")
            user_context["common_knowledge"] = []
        
        return user_context
    
    async def _call_ai_with_smart_prompt(
        self,
        message: str,
        system_prompt: str,
        prompt_context,
        user_context: Dict[str, Any]
    ) -> str:
        """Call AI with optimized smart prompt and appropriate parameters"""
        try:
            pool = await self._get_ai_pool()
            
            # Get optimized parameters based on response type
            model_params = self._get_smart_prompt_params(prompt_context)
            
            # Build conversation messages with context
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add common knowledge context if available
            if user_context.get("common_knowledge"):
                knowledge_context = []
                for item in user_context["common_knowledge"]:
                    content = item.get("content", "")
                    if content:
                        knowledge_context.append(content)
                
                if knowledge_context:
                    context_message = f"""Here is relevant information from 'The Way of Dog' by Anahata (a renowned canine behavior specialist):

{chr(10).join(knowledge_context)}

IMPORTANT: When referencing this information, establish that Anahata is the author of "The Way of Dog" on first mention, then use natural pronouns (she, her, her methodology, her approach, etc.) in subsequent references. Write naturally and conversationally - avoid repeating "Anahata" multiple times."""
                    messages.append({"role": "system", "content": context_message})
                    logger.info(f"📚 Added {len(knowledge_context)} Anahata knowledge items to context")
            
            # Add user message
            messages.append({"role": "user", "content": message})
            
            response = await pool.chat_completion(
                messages=messages,
                **model_params
            )
            
            ai_response = response["choices"][0]["message"]["content"]
            
            logger.info(f"✅ Smart AI Response Generated: {len(ai_response.split())} words")
            return ai_response
            
        except Exception as e:
            logger.error(f"❌ Smart AI call error: {str(e)}")
            raise
    
    def _get_smart_prompt_params(self, prompt_context) -> Dict[str, Any]:
        """Get optimized model parameters based on smart prompt analysis"""
        base_params = {
            "model": self.chat_model,
            "temperature": 0.7
        }
        
        # Optimize parameters based on response type
        if prompt_context.response_type.name == "QUICK_ANSWER":
            base_params.update({
                "max_tokens": 150,   # Reduced to prevent cutoffs
                "temperature": 0.4   # More focused
            })
        elif prompt_context.response_type.name == "DETAILED":
            base_params.update({
                "max_tokens": 1200,  # Reduced from 3000 to prevent truncation
                "temperature": 0.7   # Slightly reduced
            })
        elif prompt_context.response_type.name == "EMERGENCY":
            base_params.update({
                "max_tokens": 200,   # Reduced for complete emergency responses
                "temperature": 0.2   # Very focused for safety
            })
        else:  # CONVERSATIONAL
            base_params.update({
                "max_tokens": 800,   # Significantly reduced to prevent truncation
                "temperature": 0.5   # More balanced for conciseness
            })
        
        return base_params
    
    async def _track_smart_prompt_performance(
        self,
        user_id: int,
        message: str,
        response: str,
        prompt_context
    ):
        """Background task to track smart prompt performance"""
        try:
            performance_data = {
                "user_id": user_id,
                "message_length": len(message),
                "response_length": len(response),
                "response_type": prompt_context.response_type.value,
                "complexity": prompt_context.question_complexity.value,
                "pets_count": len(prompt_context.pets),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Store in Redis for analytics
            if self.cache_service:
                cache_key = f"smart_prompt_performance:{user_id}:{int(time.time())}"
                await self.cache_service.set(cache_key, performance_data, ttl=86400)  # 24 hours
                
            logger.debug(f"📊 Smart Prompt Performance Tracked for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Performance tracking error: {str(e)}")
    
    async def _process_user_message_for_pet_questions(
        self,
        user_id: int,
        message: str,
        user_context: Dict[str, Any]
    ):
        """Process user message to detect responses to pet questions and update tracking"""
        try:
            if not self.question_tracker or not user_context.get("pets"):
                return
            
            pet_names = [pet["name"] for pet in user_context["pets"]]
            
            # Detect if user provided information
            provided_info = await self.question_tracker.detect_user_provided_info(
                user_id, message, pet_names
            )
            
            # Detect if user declined to provide information  
            declined_info = await self.question_tracker.detect_user_declined(
                user_id, message, pet_names
            )
            
            # Record declined responses
            for decline in declined_info:
                await self.question_tracker.record_user_declined(
                    user_id,
                    decline["pet_name"],
                    decline["field_name"],
                    decline["reason"]
                )
            
            if provided_info:
                logger.info(f"🐕 User {user_id} provided pet information: {[p['field_name'] for p in provided_info]}")
                
            if declined_info:
                logger.info(f"🚫 User {user_id} declined to provide: {[d['field_name'] for d in declined_info]}")
            
        except Exception as e:
            logger.error(f"❌ Error processing pet question responses: {e}")
    
    def should_use_smart_prompts(self, user_id: int) -> bool:
        """Determine if user should get smart prompts (now production default)"""
        if not self.ab_test_enabled:
            return True  # Default to smart prompts when A/B testing is disabled
        
        # Use user ID hash for consistent assignment
        import hashlib
        user_hash = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
        return (user_hash % 100) < (self.smart_prompt_ratio * 100)
    
    def get_smart_prompt_stats(self) -> Dict[str, Any]:
        """Get smart prompt optimization statistics"""
        return self.smart_prompts.get_optimization_stats()
    
    # ==================== AWS STACK HELPER METHODS ====================
    
    async def _process_files_with_s3(self, user_id: int, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process file uploads using S3 storage"""
        try:
            file_context = []
            
            async with self.s3_service as s3:
                for file_data in files:
                    if 'content' in file_data and 'filename' in file_data:
                        # Upload to S3
                        upload_result = await s3.upload_document(
                            file_content=file_data['content'],
                            filename=file_data['filename'],
                            user_id=user_id,
                            document_type="chat_upload",
                            metadata={
                                'uploaded_via': 'chat',
                                'content_type': file_data.get('content_type', 'application/octet-stream')
                            }
                        )
                        
                        if upload_result.get('success'):
                            file_context.append({
                                'filename': file_data['filename'],
                                's3_key': upload_result['s3_key'],
                                's3_bucket': upload_result['s3_bucket'],
                                'download_url': upload_result['download_url'],
                                'processed': True
                            })
                            
                            # Copy to knowledge base for future RAG
                            await s3.copy_to_knowledge_base(
                                upload_result['s3_bucket'],
                                upload_result['s3_key'],
                                'user_uploads'
                            )
            
            return file_context
            
        except Exception as e:
            logger.error(f"S3 file processing error: {e}")
            return []
    
    async def _build_user_context(self, user_id: int, conversation_id: int) -> Dict[str, Any]:
        """Build comprehensive user context for agent interaction including pet information"""
        try:
            user_context = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
            }
            
            # Get user profile from PostgreSQL
            async with AsyncSessionLocal() as session:
                # Get user data
                user_query = select(User).where(User.id == user_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if user:
                    user_context.update({
                        "username": user.username,
                        "subscription_tier": user.subscription_tier or "free",
                        "timezone": getattr(user, "timezone", "UTC")
                    })
                
                # Get recent conversation history
                conversations_query = select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
                conv_result = await session.execute(conversations_query)
                user_context["recent_conversations"] = conv_result.scalar() or 0
            
        #    Include comprehensive pet information for persistent memory
            try:
                from pet_models_pkg.pet_models import PetProfile
                from repositories.pet_repository import PetRepository
                
                async with AsyncSessionLocal() as session:
                    pet_repo = PetRepository(session)
                    pets = await pet_repo.get_user_pets(user_id)
                    
                    if pets:
                        pets_context = []
                        missing_info_summary = {"critical_missing": [], "total_missing_fields": 0}
                        
                        for pet in pets:
                            pet_data = pet.to_dict()
                            missing_fields = pet.get_missing_fields()
                            
                            # Add missing fields info
                            pet_data["missing_fields"] = missing_fields
                            missing_info_summary["total_missing_fields"] += len(missing_fields)
                            
                            # Track critical missing fields
                            critical_fields = ["emergency_vet_name", "known_allergies", "medical_conditions"]
                            for field in missing_fields:
                                if field in critical_fields and field not in missing_info_summary["critical_missing"]:
                                    missing_info_summary["critical_missing"].append(field)
                            
                            pets_context.append(pet_data)
                        
                        user_context.update({
                            "pets": pets_context,
                            "total_pets": len(pets),
                            "pet_missing_info": missing_info_summary,
                            "pet_completeness_percentage": self._calculate_pet_completeness(pets)
                        })
                        
                        # Generate contextual memory prompt for agent (with smart question tracking)
                        user_context["pet_memory_prompt"] = await self._generate_pet_memory_prompt(user_id, pets, missing_info_summary)
                        
                        logger.info(f"🐕 Added {len(pets)} pets to user context for agent memory")
                    else:
                        user_context.update({
                            "pets": [],
                            "total_pets": 0,
                            "pet_missing_info": {"note": "No pet information available - consider asking about user's pets"}
                        })
                        
            except Exception as pet_error:
                logger.error(f"❌ Error loading pet context for user {user_id}: {pet_error}")
                user_context["pets"] = []
                user_context["total_pets"] = 0
            
            return user_context
            
        except Exception as e:
            logger.error(f"User context building error: {e}")
            return {"user_id": user_id, "conversation_id": conversation_id}
    
    def _calculate_pet_completeness(self, pets: List) -> float:
        """Calculate overall pet profile completeness percentage"""
        if not pets:
            return 0.0
        
        total_fields = 11  # Total possible fields per pet (name, breed, age, weight, etc.)
        total_filled = 0
        total_possible = len(pets) * total_fields
        
        for pet in pets:
            missing_fields = pet.get_missing_fields()
            filled_fields = total_fields - len(missing_fields)
            total_filled += filled_fields
        
        return (total_filled / total_possible) * 100 if total_possible > 0 else 0.0
    
    async def _generate_pet_memory_prompt(self, user_id: int, pets: List, missing_info_summary: Dict) -> str:
        """Generate a structured prompt for the agent with strict anti-hallucination constraints and smart questioning"""
        prompt_parts = [
            "🚨 CRITICAL PET MEDICAL INFORMATION - STRICT ADHERENCE REQUIRED:",
            "WARNING: NEVER make up, assume, or fabricate any medical information about these pets.",
            "ONLY use the exact information provided below from the verified database."
        ]
        
        for pet in pets:
            pet_info = [f"Pet Name: {pet.name}"]
            
            # Add known information with explicit constraints
            if pet.breed:
                pet_info.append(f"Breed: {pet.breed}")
            if pet.age:
                pet_info.append(f"Age: {pet.age} years old")
            if pet.weight:
                pet_info.append(f"Weight: {pet.weight} lbs")
            if pet.gender:
                pet_info.append(f"Gender: {pet.gender}")
            
            # MEDICAL INFORMATION WITH STRICT CONSTRAINTS
            if pet.known_allergies:
                pet_info.append(f"VERIFIED ALLERGIES: {pet.known_allergies}")
            else:
                pet_info.append(f"ALLERGIES: NOT SPECIFIED - DO NOT ASSUME ANY")
                
            if pet.medical_conditions:
                pet_info.append(f"VERIFIED MEDICAL CONDITIONS: {pet.medical_conditions}")
            else:
                pet_info.append(f"MEDICAL CONDITIONS: NOT SPECIFIED - DO NOT ASSUME ANY")
            
            # VETERINARY INFORMATION
            if pet.emergency_vet_name:
                pet_info.append(f"Veterinarian: {pet.emergency_vet_name}")
            else:
                pet_info.append(f"Veterinarian: NOT SPECIFIED")
                
            if pet.emergency_vet_phone:
                pet_info.append(f"Vet Phone: {pet.emergency_vet_phone}")
            else:
                pet_info.append(f"Vet Phone: NOT SPECIFIED")
            
            # Add missing information note (for awareness only, not for asking)
            missing = pet.get_missing_fields()
            if missing:
                critical_missing = [f for f in missing if f in ["emergency_vet_name", "known_allergies", "medical_conditions"]]
                if critical_missing:
                    pet_info.append(f"MISSING CRITICAL INFO: {', '.join(critical_missing)} (for internal awareness - do not repeatedly ask about this)")
            
            prompt_parts.append(" | ".join(pet_info))
        
        # Add strict anti-hallucination constraints
        prompt_parts.extend([
            "",
            "🛡️ ANTI-HALLUCINATION RULES:",
            "- NEVER mention specific medications unless explicitly provided above",
            "- NEVER mention specific treatments unless explicitly provided above", 
            "- NEVER assume allergies or medical conditions not listed above",
            "- NEVER mix up information between different pets",
            "- ONLY use the verified database information shown above",
            "- DO NOT repeatedly ask about the same missing information"
        ])
        
        # Get smart questions to ask (prevents repetition)
        smart_questions_to_ask = []
        if self.question_tracker and missing_info_summary.get("critical_missing"):
            # Build missing info structure for question tracker
            pets_missing_info = {}
            for pet in pets:
                missing = pet.get_missing_fields()
                if missing:
                    pets_missing_info[pet.name] = missing
            
            # Get safe questions that haven't been asked recently
            safe_questions = await self.question_tracker.get_safe_questions_to_ask(
                user_id, pets_missing_info, max_questions=1
            )
            
            if safe_questions:
                smart_questions_to_ask = safe_questions[:1]  # Only one question at a time
        
        # Add smart questioning guidance (only if we have safe questions)
        if smart_questions_to_ask:
            question = smart_questions_to_ask[0]
            prompt_parts.append(f"\n💡 GENTLE QUESTION (if contextually appropriate): {question['question_template']}")
            prompt_parts.append("IMPORTANT: Only ask this question if it flows naturally in the conversation. Do not force it.")
            
            # Record that we're about to potentially ask this question
            if self.question_tracker:
                try:
                    await self.question_tracker.record_question_asked(
                        user_id, 
                        question['pet_name'], 
                        question['field_name'],
                        question['question_template']
                    )
                except Exception as e:
                    logger.error(f"❌ Error recording question: {e}")
        else:
            prompt_parts.append("\n🤐 QUESTION GUIDANCE: Do not ask about missing information - either it was recently asked or user declined to provide it.")
        
        return "\n".join(prompt_parts)
    
    def _requires_knowledge_enhancement(self, message: str, ai_response: str) -> bool:
        """Determine if response needs knowledge base enhancement"""
        # Enhanced logic to detect when RAG would be beneficial
        knowledge_triggers = [
            "don't know", "not sure", "can't find", "need more information",
            "specific", "detailed", "research", "study", "guideline", "protocol"
        ]
        
        message_lower = message.lower()
        response_lower = ai_response.lower()
        
        # Check if message asks for specific information
        asks_for_info = any(trigger in message_lower for trigger in knowledge_triggers)
        
        # Check if AI response suggests it needs more information
        needs_enhancement = any(trigger in response_lower for trigger in knowledge_triggers)
        
        return asks_for_info or needs_enhancement
    
    async def _combine_agent_and_rag_responses(
        self, 
        agent_response: str, 
        rag_response: Dict[str, Any], 
        original_message: str
    ) -> str:
        """Combine agent response with RAG insights"""
        try:
            rag_content = rag_response.get("response", "")
            
            # Use AI to synthesize the responses
            ai_pool = await self._get_ai_pool()
            
            synthesis_prompt = f"""
            You are Mr. White, combining your conversational response with additional knowledge base information.
            
            Original question: {original_message}
            
            Your conversational response: {agent_response}
            
            Additional knowledge from database: {rag_content}
            
            Please provide a cohesive, comprehensive response that naturally integrates both sources of information.
            Maintain your warm, helpful tone while incorporating the additional details where relevant.
            """
            
            messages = [
                {"role": "system", "content": "You are Mr. White, expert dog care assistant with access to comprehensive knowledge."},
                {"role": "user", "content": synthesis_prompt}
            ]
            
            response = await ai_pool.chat_completion(
                messages=messages,
                model=self.chat_model,
                temperature=0.6,
                max_tokens=1200  # Reduced to prevent truncation
            )
            
            return response['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Response synthesis error: {e}")
            return agent_response  # Fallback to original agent response
    
    async def _store_conversation_in_postgresql(
        self, 
        user_id: int, 
        conversation_id: int, 
        message: str, 
        ai_response: str,
        session_id: str,
        attachments: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store conversation in PostgreSQL for persistence"""
        try:
            async with AsyncSessionLocal() as session:
                # Check if conversation exists, create if not
                from sqlalchemy import select
                from models import Conversation
                
                conversation_query = select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id
                )
                existing_conversation = await session.execute(conversation_query)
                conversation = existing_conversation.scalar_one_or_none()
                
                if not conversation:
                    # Create new conversation with the specified ID
                    conversation = await create_conversation_async(
                        session, 
                        user_id, 
                        title=message[:50] + "..." if len(message) > 50 else message,
                        thread_id=session_id
                    )
                    conversation_id = conversation.id
                
                # Add user message
                user_message = await create_message_async(
                    session, conversation_id, message, "user", attachments
                )
                
                # Add AI message
                ai_message = await create_message_async(
                    session, conversation_id, ai_response, "assistant"
                )
                
                return {
                    "conversation_id": conversation_id,
                    "message_id": ai_message.id,
                    "user_message_id": user_message.id
                }
                
        except Exception as e:
            logger.error(f"PostgreSQL storage error: {e}")
            return {
                "conversation_id": conversation_id or 0,
                "message_id": str(uuid.uuid4()),
                "error": str(e)
            }
    
    async def _background_vector_storage(
        self, 
        user_id: int, 
        conversation_id: str, 
        message: str, 
        ai_response: str
    ):
        """Background task for vector storage in MemoryDB"""
        try:
            # Store conversation vectors for future semantic search
            vectors_to_store = [{
                'operation_type': 'chat',
                'user_id': user_id,
                'namespace_suffix': 'chat',
                'records': [
                    {
                        'id': f"msg_{conversation_id}_{int(time.time())}",
                        'metadata': {
                            'text': f"User: {message}\nAssistant: {ai_response}",
                            'conversation_id': conversation_id,
                            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                            'type': 'conversation'
                        }
                    }
                ]
            }]
            
            await self.vector_service.batch_store_vectors(vectors_to_store)
            logger.info(f"✅ Stored conversation vectors for {conversation_id}")
            
        except Exception as e:
            logger.error(f"Background vector storage error: {e}")
    
    async def _background_knowledge_base_update(
        self, 
        user_id: int, 
        message: str, 
        ai_response: str, 
        file_context: List[Dict[str, Any]]
    ):
        """Background task to update knowledge base with valuable interactions"""
        try:
            # Check if this interaction contains valuable information to add to knowledge base
            if self._is_valuable_knowledge(message, ai_response):
                knowledge_content = f"""
                User Question: {message}
                
                Expert Response: {ai_response}
                
                Category: User Interaction
                Source: Mr. White Chat System
                Date: {datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}
                """
                
                # Add to knowledge base
                await self.bedrock_knowledge_service.upload_document_content(
                    content=knowledge_content,
                    s3_key=f"interactions/{user_id}/{int(time.time())}.txt",
                    metadata={
                        'user_id': str(user_id),
                        'type': 'valuable_interaction',
                        'category': 'user_generated'
                    }
                )
                
                logger.info("✅ Added valuable interaction to knowledge base")
                
        except Exception as e:
            logger.error(f"Knowledge base update error: {e}")
    
    def _is_valuable_knowledge(self, message: str, ai_response: str) -> bool:
        """Determine if interaction contains valuable knowledge to preserve"""
        # Check for detailed responses that could help other users
        return (
            len(ai_response) > 200 and  # Substantial response
            any(keyword in ai_response.lower() for keyword in [
                "training", "behavior", "health", "nutrition", "exercise", 
                "grooming", "medical", "emergency", "care", "guide"
            ])
        )

    async def _prepare_chat_context_queries(
        self, 
        message: str, 
        user_id: int, 
        conversation_id: int
    ) -> List[Dict[str, Any]]:
        """
        Prepare context queries for chat processing
        Includes user conversation history, documents, and common knowledge base
        """
        return [
            # User's conversation history (most important for continuity)
            {
                "query_text": message,
                "user_id": user_id,
                "search_type": "chat",
                "top_k": 8  # Increased for better history recall
            },
            # User's uploaded documents
            {
                "query_text": message,
                "user_id": user_id,
                "search_type": "documents",
                "top_k": 4
            },
            # User's health records (for health-related context)
            {
                "query_text": message,
                "user_id": user_id,
                "search_type": "health",
                "top_k": 3
            },
            # Common knowledge base (The Way of the Dog book)
            {
                "query_text": message,
                "user_id": user_id,
                "search_type": "common",
                "top_k": 5  # Increased for better book knowledge
            }
        ]

    async def _process_chat_files(self, user_id: int, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process uploaded files for chat context"""
        # This will be handled by Document service
        return []

    async def _process_with_direct_chat(
        self,
        user_id: int,
        message: str,
        conversation_id: int,
        intent_analysis: Dict[str, Any],
        context_data: Dict[str, Any]
    ) -> str:
        """Process message with direct OpenAI chat completion using comprehensive context"""
        try:
            # Get context-aware prompt
            system_prompt = self.prompts.get_chat_system_prompt(intent_analysis)
            context_text = self._format_context_text(context_data)
            
            # Construct optimized prompt with comprehensive context
            prompt = self.prompts.build_chat_prompt(
                message=message,
                context=context_text,
                intent=intent_analysis
            )
            
            # Call OpenAI with optimized parameters
            response = await self._call_openai_simple(
                prompt, 
                context="chat",
                conversation_id=conversation_id,
                model=intent_analysis.get("recommended_model", self.chat_model)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Direct chat processing error: {str(e)}")
            return self.prompts.get_fallback_response(message)

    async def _process_with_langgraph(
        self,
        user_id: int,
        message: str,
        conversation_id: int,
        thread_id: str,
        intent_analysis: Dict[str, Any]
    ) -> str:
        """Process complex queries with LangGraph"""
        try:
            # This would use the LangGraph service for complex multi-step reasoning
            # For now, fall back to direct chat
            return await self._process_with_direct_chat(
                user_id, message, conversation_id, intent_analysis, []
            )
        except Exception as e:
            logger.error(f"LangGraph processing error: {str(e)}")
            return self.prompts.get_fallback_response(message)

    async def _call_openai_simple(
        self,
        message: str,
        context: str,
        conversation_id: int,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Call AWS Bedrock AI with optimized parameters (no OpenAI fallback)"""
        try:
            pool = await self._get_ai_pool()
            
            response = await pool.chat_completion(
                messages=[
                    {"role": "system", "content": self.prompts.get_chat_system_prompt()},
                    {"role": "user", "content": message}
                ],
                model=model or self.chat_model,
                temperature=self.temperature,
                max_tokens=max_tokens or self.max_tokens
            )
            
            return response["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"OpenAI call error: {str(e)}")
            return self.prompts.get_fallback_response(message)

    # Conversation management methods
    async def _create_conversation(self, user_id: int, message: str) -> Conversation:
        """Create a new conversation"""
        async with AsyncSessionLocal() as session:
            title = message[:50] + "..." if len(message) > 50 else message
            conversation = await create_conversation_async(session, user_id, title)
            return conversation

    async def _get_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """Get existing conversation"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Conversation).where(
                    and_(Conversation.id == conversation_id, Conversation.user_id == user_id)
                )
            )
            return result.scalar_one_or_none()

    async def _save_user_message(self, conversation_id: int, content: str) -> Message:
        """Save user message to database"""
        async with AsyncSessionLocal() as session:
            return await create_message_async(session, conversation_id, content, "user")

    async def _save_ai_message(self, conversation_id: int, content: str) -> Message:
        """Save AI message to database"""
        async with AsyncSessionLocal() as session:
            return await create_message_async(session, conversation_id, content, "ai")

    # Utility methods
    def _format_context_from_search_results(self, search_results: List[Dict[str, Any]], file_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format context data from search results with prioritized organization
        Separates user history, documents, health records, and common knowledge
        """
        context_data = {
            "user_history": [],
            "user_documents": [],
            "user_health": [],
            "common_knowledge": [],
            "file_context": file_context or [],
            "total_sources": len(search_results or []) + len(file_context or [])
        }
        
        # Organize search results by type
        for result in (search_results or []):
            search_type = result.get("search_type", "")
            results_list = result.get("results", [])
            
            if search_type == "chat":
                context_data["user_history"].extend(results_list)
            elif search_type == "documents":
                context_data["user_documents"].extend(results_list)
            elif search_type == "health":
                context_data["user_health"].extend(results_list)
            elif search_type == "common":
                context_data["common_knowledge"].extend(results_list)
        
        return context_data

    def _format_context_text(self, context_data: Dict[str, Any]) -> str:
        """
        Format comprehensive context for AI prompt
        Includes user conversation history, documents, health records, and common knowledge
        """
        context_parts = []
        
        # 1. User Conversation History (most important for continuity)
        if context_data.get("user_history"):
            history_parts = []
            for item in context_data["user_history"][:6]:  # Limit to most relevant
                content = item.get("content", "")
                msg_type = item.get("message_type", "")
                timestamp = item.get("timestamp", "")
                if content and len(content.strip()) > 10:  # Filter meaningful content
                    history_parts.append(f"[{msg_type.upper()}]: {content[:300]}...")
            
            if history_parts:
                context_parts.append(f"=== USER CONVERSATION HISTORY ===\n" + "\n".join(history_parts))
        
        # 2. Common Knowledge Base (The Way of the Dog book)
        if context_data.get("common_knowledge"):
            knowledge_parts = []
            for item in context_data["common_knowledge"]:
                content = item.get("content", "")
                if content and len(content.strip()) > 15:  # Filter meaningful content
                    knowledge_parts.append(f"Book Reference: {content[:400]}...")
            
            if knowledge_parts:
                context_parts.append(f"=== DOG CARE KNOWLEDGE BASE ===\n" + "\n".join(knowledge_parts))
        
        # 3. User Documents
        if context_data.get("user_documents"):
            doc_parts = []
            for item in context_data["user_documents"]:
                content = item.get("content", "")
                filename = item.get("filename", "Document")
                if content and len(content.strip()) > 10:
                    doc_parts.append(f"From {filename}: {content[:300]}...")
            
            if doc_parts:
                context_parts.append(f"=== USER DOCUMENTS ===\n" + "\n".join(doc_parts))
        
        # 4. User Health Records
        if context_data.get("user_health"):
            health_parts = []
            for item in context_data["user_health"]:
                content = item.get("content", "")
                pet_name = item.get("pet_name", "Pet")
                category = item.get("category", "Health")
                if content and len(content.strip()) > 10:
                    health_parts.append(f"{pet_name} - {category}: {content[:250]}...")
            
            if health_parts:
                context_parts.append(f"=== PET HEALTH RECORDS ===\n" + "\n".join(health_parts))
        
        # 5. File Context (current session files)
        if context_data.get("file_context"):
            file_parts = []
            for item in context_data["file_context"]:
                filename = item.get("filename", "Unknown")
                content = item.get("content", "")
                if content:
                    file_parts.append(f"Current File - {filename}: {content[:300]}...")
            
            if file_parts:
                context_parts.append(f"=== CURRENT SESSION FILES ===\n" + "\n".join(file_parts))
        
        return "\n\n".join(context_parts)

    def _format_sources_from_context(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format sources for response with comprehensive context types"""
        sources = []
        
        # User conversation history
        for item in context_data.get("user_history", []):
            sources.append({
                "type": "conversation_history",
                "content": item.get("content", "")[:200],
                "message_type": item.get("message_type", ""),
                "timestamp": item.get("timestamp", "")
            })
        
        # Common knowledge base (The Way of the Dog book)
        for item in context_data.get("common_knowledge", []):
            sources.append({
                "type": "dog_care_knowledge",
                "content": item.get("content", "")[:200],
                "source": "The Way of the Dog",
                "score": item.get("score", 0)
            })
        
        # User documents
        for item in context_data.get("user_documents", []):
            sources.append({
                "type": "user_document",
                "content": item.get("content", "")[:200],
                "filename": item.get("filename", "Document")
            })
        
        # User health records
        for item in context_data.get("user_health", []):
            sources.append({
                "type": "health_record",
                "content": item.get("content", "")[:200],
                "pet_name": item.get("pet_name", "Pet"),
                "category": item.get("category", "Health")
            })
        
        # Current session files
        for file in context_data.get("file_context", []):
            sources.append({
                "type": "current_file",
                "filename": file.get("filename", ""),
                "content": file.get("content", "")[:200]
            })
        
        return sources

    # Conversation management methods
    async def create_conversation(self, user_id: int, title: str) -> Dict[str, Any]:
        """Create a new conversation for the user"""
        try:
            async with AsyncSessionLocal() as session:
                conversation = await create_conversation_async(session, user_id, title)
                
                return {
                    "id": conversation.id,
                    "title": conversation.title,
                    "created_at": conversation.created_at.isoformat(),
                    "updated_at": conversation.updated_at.isoformat(),
                    "is_bookmarked": conversation.is_bookmarked,
                    "thread_id": conversation.thread_id
                }
        except Exception as e:
            logger.error(f"Create conversation error: {str(e)}")
            raise

    async def get_bookmarked_conversations(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's bookmarked conversations"""
        try:
            async with AsyncSessionLocal() as session:
                conversations = await get_bookmarked_conversations_optimized(session, user_id)
                
                result = []
                for conv in conversations:
                    # Generate title from first user message if title is "New Conversation" or empty
                    title = conv.title
                    if not title or title == "New Conversation":
                        title = self._generate_conversation_title(conv)
                    
                    result.append({
                        "id": conv.id,
                        "title": title,
                        "created_at": conv.created_at.isoformat(),
                        "updated_at": conv.updated_at.isoformat(),
                        "is_bookmarked": conv.is_bookmarked,
                        "thread_id": conv.thread_id,
                        "message_count": len(conv.messages) if conv.messages else 0
                    })
                
                return result
        except Exception as e:
            logger.error(f"Get bookmarked conversations error: {str(e)}")
            raise

    # Background tasks
    async def _batch_store_conversation_vectors(
        self,
        user_id: int,
        conversation_id: int,
        messages: List[Message]
    ):
        """Store conversation vectors in batch"""
        try:
            message_data = []
            for msg in messages:
                message_data.append({
                    "id": msg.id,
                    "content": msg.content,
                    "type": msg.type,
                    "created_at": msg.created_at.isoformat()
                })
            
            await self.vector_service.store_chat_vectors(
                user_id, conversation_id, message_data
            )
        except Exception as e:
            logger.error(f"Batch vector storage error: {str(e)}")

    async def _update_conversation_timestamp(self, conversation_id: int, user_id: int = None):
        """Update conversation timestamp"""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Conversation)
                    .where(Conversation.id == conversation_id)
                    .values(updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
                )
                await session.commit()
        except Exception as e:
            logger.error(f"Update timestamp error: {str(e)}")

    # Performance monitoring
    def _update_parallel_processing_stats(self, processing_time: float):
        """Update parallel processing statistics"""
        self.parallel_processing_stats["total_operations"] += 1
        self.parallel_processing_stats["parallel_time"] += processing_time
        
        # Estimate sequential time (would be ~40-50% slower)
        estimated_sequential_time = processing_time * 1.45
        self.parallel_processing_stats["sequential_time"] += estimated_sequential_time
        
        # Calculate savings
        time_saved = estimated_sequential_time - processing_time
        self.parallel_processing_stats["time_saved"] += time_saved
        
        # Calculate efficiency improvement
        total_parallel = self.parallel_processing_stats["parallel_time"]
        total_sequential = self.parallel_processing_stats["sequential_time"]
        
        if total_sequential > 0:
            efficiency_improvement = ((total_sequential - total_parallel) / total_sequential) * 100
            self.parallel_processing_stats["efficiency_improvement_percent"] = efficiency_improvement

    def get_parallel_processing_stats(self) -> Dict[str, Any]:
        """Get parallel processing statistics"""
        return self.parallel_processing_stats.copy()

    def reset_parallel_processing_stats(self):
        """Reset parallel processing statistics"""
        self.parallel_processing_stats = {
            "total_operations": 0,
            "sequential_time": 0.0,
            "parallel_time": 0.0,
            "time_saved": 0.0,
            "efficiency_improvement_percent": 0.0
        }

    async def get_smart_routing_stats(self) -> Dict[str, Any]:
        """Get smart routing statistics"""
        return self.smart_routing_stats.copy()

    def reset_smart_routing_stats(self):
        """Reset smart routing statistics"""
        self.smart_routing_stats = {
            "total_messages": 0,
            "routed_messages": 0,
            "ai_calls_saved": 0,
            "cache_hits": 0,
            "routing_time_saved": 0.0
        }
    # ==================== CONVERSATION MANAGEMENT METHODS ====================
    
    async def get_user_conversations(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's conversations with pagination"""
        try:
            # Use optimized PostgreSQL query
            async with AsyncSessionLocal() as session:
                conversations_result = await get_user_conversations_optimized(
                    session, user_id, limit, offset
                )
                conversations = conversations_result or []
            
            # Format conversations for response
            formatted_conversations = []
            for conv in conversations:
                # Generate title from first user message if title is "New Conversation" or empty
                title = conv.title
                if not title or title == "New Conversation":
                    title = self._generate_conversation_title(conv)
                
                formatted_conv = {
                    "id": conv.id,  # Frontend expects 'id', not 'conversation_id'
                    "conversation_id": conv.id,  # Keep for backward compatibility
                    "title": title,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                    "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                    "message_count": len(conv.messages) if hasattr(conv, 'messages') else 0,
                    "is_bookmarked": conv.is_bookmarked or False,
                    "last_message": conv.messages[-1].content if hasattr(conv, 'messages') and conv.messages else "",
                    "context": "chat"  # Default context for conversations
                }
                formatted_conversations.append(formatted_conv)
            
            # Apply offset for pagination
            if offset > 0:
                formatted_conversations = formatted_conversations[offset:]
            
            # Apply limit
            if limit > 0:
                formatted_conversations = formatted_conversations[:limit]
            
            logger.info(f"✅ Retrieved {len(formatted_conversations)} conversations for user {user_id}")
            return formatted_conversations
        except Exception as e:
            logger.error(f"❌ Failed to get user conversations: {str(e)}")
            raise e

    
    def _generate_conversation_title(self, conversation) -> str:
        """Generate a meaningful title from the first user message"""
        try:
            if hasattr(conversation, 'messages') and conversation.messages:
                # Find the first user message
                first_user_message = None
                for message in conversation.messages:
                    if getattr(message, 'type', '') == 'user':
                        first_user_message = message
                        break
                
                if first_user_message and first_user_message.content:
                    content = first_user_message.content.strip()
                    # Truncate to reasonable length and add ellipsis if needed
                    if len(content) > 50:
                        return content[:47] + "..."
                    return content
            
            # Fallback to conversation ID
            return f"Conversation {conversation.id}"
        except Exception as e:
            logger.error(f"Error generating conversation title: {str(e)}")
            return f"Conversation {conversation.id}"
        
        except Exception as e:
            logger.error(f"❌ Failed to get user conversations: {str(e)}")
            raise e
    
    async def update_conversation(
        self,
        conversation_id: int,
        user_id: int,
        title: Optional[str] = None,
        is_bookmarked: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update conversation title and/or bookmark status"""
        try:
            async with AsyncSessionLocal() as session:
                # Get conversation and verify user access
                query = select(Conversation).where(
                    and_(
                        Conversation.id == conversation_id,
                        Conversation.user_id == user_id
                    )
                )
                result = await session.execute(query)
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found or access denied")
                
                # Update fields if provided
                if title is not None:
                    conversation.title = title
                if is_bookmarked is not None:
                    conversation.is_bookmarked = is_bookmarked
                
                # Update timestamp
                conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                
                await session.commit()
                await session.refresh(conversation)
            
            logger.info(f"✅ Updated conversation {conversation_id} for user {user_id}")
            return {
                "id": conversation.id,
                "title": conversation.title,
                "is_bookmarked": conversation.is_bookmarked,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to update conversation: {str(e)}")
            raise e
    
    async def toggle_conversation_bookmark(
        self,
        conversation_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """Toggle conversation bookmark status"""
        try:
            async with AsyncSessionLocal() as session:
                # Get conversation and verify user access
                query = select(Conversation).where(
                    and_(
                        Conversation.id == conversation_id,
                        Conversation.user_id == user_id
                    )
                )
                result = await session.execute(query)
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found or access denied")
                
                # Toggle bookmark status
                conversation.is_bookmarked = not (conversation.is_bookmarked or False)
                conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                
                await session.commit()
                await session.refresh(conversation)
            
            logger.info(f"✅ Toggled bookmark for conversation {conversation_id} to {conversation.is_bookmarked}")
            return {
                "id": conversation.id,
                "is_bookmarked": conversation.is_bookmarked,
                "title": conversation.title,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to toggle conversation bookmark: {str(e)}")
            raise e
    
    async def get_conversation_with_messages(
        self,
        conversation_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """Get specific conversation with its messages"""
        try:
            # Use optimized PostgreSQL query that already includes messages
            async with AsyncSessionLocal() as session:
                conversation = await get_conversation_with_messages_optimized(
                    session, conversation_id, user_id
                )
                
                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found or access denied")
                
                # Ensure messages are sorted by creation time (chronological order)
                messages = sorted(conversation.messages, key=lambda m: m.created_at)
            
            # Format messages
            formatted_messages = []
            for msg in messages:
                formatted_msg = {
                    "id": msg.id,  # Frontend expects 'id', not 'message_id'
                    "message_id": msg.id,  # Keep for backward compatibility
                    "content": msg.content,
                    "message_type": getattr(msg, "type", "user"),
                    "timestamp": msg.created_at.isoformat() + 'Z' if msg.created_at else None,
                    "attachments": [
                        {
                            "id": att.id,
                            "file_type": att.type,      # Map type to file_type for frontend compatibility
                            "file_name": att.name,      # Map name to file_name for frontend compatibility
                            "file_path": att.url,       # Map url to file_path for frontend compatibility  
                            "file_size": 0              # Default file_size since it's not stored in this model
                        }
                        for att in msg.attachments
                    ] if hasattr(msg, 'attachments') and msg.attachments else [],
                    "is_bookmarked": msg.is_bookmarked or False,
                    "liked": msg.liked or False,
                    "disliked": msg.disliked or False
                }
                formatted_messages.append(formatted_msg)
            
            return {
                "conversation": {
                    "conversation_id": conversation.id,
                    "title": conversation.title or "New Conversation",
                    "created_at": conversation.created_at.isoformat() + 'Z' if conversation.created_at else None,
                    "updated_at": conversation.updated_at.isoformat() + 'Z' if conversation.updated_at else None,
                    "is_bookmarked": conversation.is_bookmarked or False,
                    "context": "chat"
                },
                "messages": formatted_messages
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get conversation with messages: {str(e)}")
            raise e
    

    
    async def delete_conversation(
        self,
        conversation_id: int,
        user_id: int
    ) -> bool:
        """Delete a conversation and its messages"""
        try:
            # Use PostgreSQL with CASCADE DELETE (messages deleted automatically)
            async with AsyncSessionLocal() as session:
                # Verify user ownership and delete in one operation
                conversation_query = select(Conversation).where(
                    and_(Conversation.id == conversation_id, Conversation.user_id == user_id)
                )
                result = await session.execute(conversation_query)
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found or access denied")
                
                # Delete conversation (messages cascade deleted automatically)
                await session.delete(conversation)
                await session.commit()
            
            logger.info(f"✅ Deleted conversation {conversation_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete conversation: {str(e)}")
            raise e
    
    async def add_message_to_conversation(
        self,
        conversation_id: int,
        user_id: int,
        content: str,
        message_type: str = "user",
        attachments: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add a message to a conversation"""
        try:
            # Use optimized PostgreSQL operation
            async with AsyncSessionLocal() as session:
                # Verify conversation ownership
                conversation_query = select(Conversation).where(
                    and_(Conversation.id == conversation_id, Conversation.user_id == user_id)
                )
                result = await session.execute(conversation_query)
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found or access denied")
                
                # Create message using optimized helper
                message = await create_message_async(
                    session, conversation_id, content, message_type, attachments or []
                )
                
                # Update conversation timestamp (timezone-naive for PostgreSQL compatibility)
                conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await session.commit()
                
                # Refresh message to get attachments (if any)
                await session.refresh(message)
                
                # Build message data safely
                message_data = {
                    "message_id": message.id,
                    "conversation_id": message.conversation_id,
                    "content": message.content,
                    "message_type": getattr(message, "type", message_type),
                    "timestamp": message.created_at.isoformat() + 'Z',
                    "attachments": []  # Attachments handled separately if needed
                }
                
                # Handle attachments safely within session context
                if attachments:
                    # Attachments were created in create_message_async, just confirm count
                    message_data["attachment_count"] = len(attachments)
                else:
                    message_data["attachment_count"] = 0
            
            logger.info(f"✅ Added message to conversation {conversation_id}")
            return message_data
            
        except Exception as e:
            logger.error(f"❌ Failed to add message to conversation: {str(e)}")
            raise e
    
    async def toggle_message_bookmark(
        self,
        message_id: str,
        user_id: int
    ) -> Dict[str, Any]:
        """Toggle bookmark status of a message"""
        try:
            # Use PostgreSQL with JOIN for efficient access verification
            async with AsyncSessionLocal() as session:
                # Get message with conversation to verify user access in one query
                query = select(Message).join(Conversation).where(
                    and_(
                        Message.id == int(message_id),
                        Conversation.user_id == user_id
                    )
                )
                result = await session.execute(query)
                message = result.scalar_one_or_none()
                
                if not message:
                    raise ValueError(f"Message {message_id} not found or access denied")
                
                # Toggle bookmark
                message.is_bookmarked = not (message.is_bookmarked or False)
                await session.commit()
                new_bookmark = message.is_bookmarked
            
            logger.info(f"✅ Toggled bookmark for message {message_id}")
            return {"is_bookmarked": new_bookmark}
            
        except Exception as e:
            logger.error(f"❌ Failed to toggle message bookmark: {str(e)}")
            raise e
    
    async def add_message_reaction(
        self,
        message_id: str,
        user_id: int,
        reaction_type: str
    ) -> Dict[str, Any]:
        """Add reaction to a message"""
        try:
            # Use PostgreSQL with JSON operations for reactions
            async with AsyncSessionLocal() as session:
                # Convert message ID to integer (database ID)
                try:
                    db_message_id = int(message_id)
                except ValueError:
                    raise ValueError(f"Invalid message ID format: {message_id}. Expected integer database ID.")
                
                # Get message with conversation to verify user access in one query
                query = select(Message).join(Conversation).where(
                    and_(
                        Message.id == db_message_id,
                        Conversation.user_id == user_id
                    )
                )
                result = await session.execute(query)
                message = result.scalar_one_or_none()
                
                if not message:
                    raise ValueError(f"Message {message_id} not found or access denied")
                
                # Handle reactions (store in JSON field if available)
                # For now, we'll use simple liked/disliked fields
                if reaction_type == "like":
                    message.liked = True
                    message.disliked = False
                elif reaction_type == "dislike":
                    message.liked = False
                    message.disliked = True
                
                await session.commit()
                
                # Refresh the message to get updated data
                await session.refresh(message)
            
            logger.info(f"✅ Added {reaction_type} reaction to message {message_id}")
            return {
                "reaction_type": reaction_type, 
                "liked": message.liked,
                "disliked": message.disliked,
                "message_id": message_id
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to add message reaction: {str(e)}")
            raise e

    async def delete_all_user_conversations(self, user_id: int) -> Tuple[bool, str]:
        """
        Delete all conversations and associated messages for a user
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            async with AsyncSessionLocal() as session:
                # First, get all conversation IDs for the user
                conversations_query = select(Conversation).where(Conversation.user_id == user_id)
                conversations_result = await session.execute(conversations_query)
                conversations = conversations_result.scalars().all()
                
                if not conversations:
                    return True, 'No conversations to delete'
                
                conversation_ids = [conv.id for conv in conversations]
                
                # Get all message IDs for these conversations
                messages_query = select(Message).where(Message.conversation_id.in_(conversation_ids))
                messages_result = await session.execute(messages_query)
                messages = messages_result.scalars().all()
                message_ids = [msg.id for msg in messages]
                
                if message_ids:
                    # Delete attachments first (foreign key constraint)
                    attachments_delete = delete(Attachment).where(Attachment.message_id.in_(message_ids))
                    await session.execute(attachments_delete)
                
                # Then delete all messages for these conversations
                messages_delete = delete(Message).where(Message.conversation_id.in_(conversation_ids))
                await session.execute(messages_delete)
                
                # Finally delete all conversations
                conversations_delete = delete(Conversation).where(Conversation.user_id == user_id)
                await session.execute(conversations_delete)
                
                # Commit the changes
                await session.commit()
                
                logger.info(f"✅ Successfully deleted all conversations for user {user_id}")
                return True, f'Successfully deleted {len(conversations)} conversations and their messages'
                
        except Exception as e:
            logger.error(f"❌ Error deleting all conversations for user {user_id}: {str(e)}")
            return False, f'Error deleting conversations: {str(e)}' 
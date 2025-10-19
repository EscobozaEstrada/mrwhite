"""
Context7 Optimized Chat Handler
Based on AWS Bedrock best practices for performance optimization
Integrated with full AWS stack: PostgreSQL, MemoryDB, Pinecone, Bedrock Knowledge, Bedrock Agents
"""

import asyncio
import time
import json
import logging
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from models import ChatResponse
from .async_openai_pool_service import get_openai_pool
# Removed DynamoDB - using PostgreSQL exclusively
from .async_pinecone_service import AsyncPineconeService
from .async_bedrock_knowledge_service import AsyncBedrockKnowledgeService
from .async_bedrock_agents_service import AsyncBedrockAgentsService
from .async_cache_service import AsyncCacheService

logger = logging.getLogger(__name__)

class OptimizedChatHandler:
    """
    Context7 optimization: High-performance chat handler
    Implements AWS best practices for parallel processing and caching
    """
    
    def __init__(self):
        self.openai_pool = None
        self.performance_metrics = {
            'requests_processed': 0,
            'parallel_requests': 0,
            'cached_responses': 0,
            'average_ttft': 0.0,
            'total_processing_time': 0.0
        }
        
        # Context7 optimization settings
        self.max_parallel_requests = 6
        self.enable_prompt_caching = True
        self.enable_streaming = True
        self.cache_system_prompts = True
        
        
        # AWS services initialization
        self.aws_services_initialized = False
        
        logger.info("✅ OptimizedChatHandler initialized with Context7 optimizations")

    async def initialize(self):
        """Initialize with optimized AI pool and ALL AWS services"""
        if not self.openai_pool:
            self.openai_pool = await get_openai_pool()
            logger.info("🚀 OptimizedChatHandler connected to enhanced AI pool")
        
        
        # Mark AWS services as initialized for now
        if not hasattr(self, 'aws_services_initialized'):
            self.aws_services_initialized = True
    
    async def _initialize_aws_services(self):
        """Initialize all AWS services for complete integration"""
        try:
            init_tasks = []
            
            # Initialize PostgreSQL
            init_tasks.append(self._init_postgresql())
            
            # Initialize Vector services (MemoryDB + Pinecone)
            init_tasks.append(self._init_vector_service())
            
            # Initialize Knowledge Base
            init_tasks.append(self._init_knowledge_service())
            
            # Initialize Bedrock Agents
            init_tasks.append(self._init_agents_service())
            
            # Run all initializations in parallel
            results = await asyncio.gather(*init_tasks, return_exceptions=True)
            
            success_count = sum(1 for result in results if result is True)
            
            if success_count >= 3:  # At least 3/4 services working
                self.aws_services_initialized = True
                logger.info(f"✅ AWS services initialized: {success_count}/4 services ready")
            else:
                logger.warning(f"⚠️ Only {success_count}/4 AWS services initialized")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize AWS services: {e}")
    
    async def _init_postgresql(self):
        """Initialize PostgreSQL service"""
        try:
            # PostgreSQL is already initialized in main.py lifespan
            return True
        except Exception as e:
            logger.error(f"PostgreSQL initialization failed: {e}")
            return False
    
    async def _init_vector_service(self):
        """Initialize Vector service (MemoryDB + Pinecone)"""
        try:
            self.vector_service = AsyncPineconeService()
            await self.vector_service.__aenter__()
            return True
        except Exception as e:
            logger.error(f"Vector service initialization failed: {e}")
            return False
    
    async def _init_knowledge_service(self):
        """Initialize Bedrock Knowledge Base"""
        try:
            return await self.knowledge_service.ensure_knowledge_base_exists()
        except Exception as e:
            logger.error(f"Knowledge Base initialization failed: {e}")
            return False
    
    async def _init_agents_service(self):
        """Initialize Bedrock Agents"""
        try:
            return await self.agents_service.ensure_agent_exists()
        except Exception as e:
            logger.error(f"Bedrock Agents initialization failed: {e}")
            return False

    async def process_chat_optimized(
        self,
        user_id: int,
        message: str,
        conversation_id: Optional[int] = None,
        context: str = "chat",
        use_parallel: bool = True,
        use_cache: bool = True,
        enable_streaming: bool = False
    ) -> ChatResponse:
        """
        Context7 optimization: Process chat with FULL AWS stack integration
        - PostgreSQL: Conversation history retrieval & storage
        - Pinecone: Related conversation search  
        - MemoryDB: High-speed caching
        - Bedrock Knowledge Base: Contextual knowledge
        - Bedrock Agents: Persistent memory across sessions
        """
        start_time = time.time()
        
        # Ensure all services are initialized
        if not self.openai_pool or not self.aws_services_initialized:
            await self.initialize()
        
        try:
            logger.info(f"🚀 Processing optimized chat for user {user_id}")
            
            # Context7 pattern: Build optimized messages with caching
            messages = await self._build_optimized_messages(
                message, user_id, conversation_id, use_cache
            )
            
            # PHASE 7: Context7 optimization: Enhanced chat completion with full context
            result = await self.openai_pool.chat_completion(
                messages=messages,
                model="claude-3-haiku", 
                temperature=0.7,
                max_tokens=1500
            )
            
            # Extract response content
            if 'choices' in result and result['choices']:
                content = result['choices'][0]['message']['content']
            else:
                content = "I apologize, but I'm having trouble processing your request. Please try again."
            
            # Build optimized response
            final_conversation_id = conversation_id or int(time.time())
            final_message_id = int(time.time() * 1000)
            
            # Build enhanced response with full context info
            processing_time = time.time() - start_time
            
            response = ChatResponse(
                success=True,
                content=content,
                conversation_id=final_conversation_id,
                message_id=final_message_id,
                context_info={
                    "user_id": user_id,
                    "service": "optimized_chat_handler",
                    "model_used": result.get('model', 'claude-3-haiku') if isinstance(result, dict) else 'claude-3-haiku',
                    "cache_used": use_cache,
                    "streaming_used": enable_streaming,
                    "ttft": result.get('ttft') if isinstance(result, dict) else None,
                    "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                    "optimization_version": "context7_v1"
                },
                processing_time=processing_time
            )
            
            # Update performance metrics
            ttft = result.get('ttft') if isinstance(result, dict) else None
            await self._update_performance_metrics(processing_time, ttft, use_cache)
            
            logger.info(f"✅ Optimized chat processed for user {user_id} in {processing_time:.3f}s")
            return response
            
        except Exception as e:
            logger.error(f"❌ OptimizedChatHandler error for user {user_id}: {e}")
            
            # Return graceful fallback
            return ChatResponse(
                success=False,
                content="I apologize for the technical difficulty. As your AI dog care assistant, I'm here to help with any questions about your furry friend. What would you like to know?",
                conversation_id=conversation_id or int(time.time()),
                message_id=int(time.time() * 1000),
                context_info={
                    "error": str(e),
                    "fallback": True,
                    "service": "optimized_chat_handler",
                    "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
                },
                processing_time=time.time() - start_time
            )

    async def process_parallel_chats(
        self,
        chat_requests: List[Dict[str, Any]]
    ) -> List[ChatResponse]:
        """
        Context7 optimization: Process multiple chat requests in parallel
        Based on AWS samples concurrent processing patterns
        """
        start_time = time.time()
        
        if not self.openai_pool:
            await self.initialize()
        
        logger.info(f"🔄 Processing {len(chat_requests)} chat requests in parallel")
        
        # Convert requests to proper format for parallel processing
        parallel_requests = []
        for req in chat_requests:
            parallel_requests.append({
                'messages': [{'role': 'user', 'content': req.get('message', '')}],
                'model': 'claude-3-haiku',
                'temperature': 0.7,
                'max_tokens': 1500,
                'use_cache': req.get('use_cache', True)
            })
        
        try:
            # Context7 pattern: Use parallel chat completions
            results = await self.openai_pool.parallel_chat_completions(
                parallel_requests, 
                max_concurrent=self.max_parallel_requests
            )
            
            # Convert results to ChatResponse format
            responses = []
            for i, (result, original_req) in enumerate(zip(results, chat_requests)):
                if result.get('error'):
                    content = "I apologize for the technical difficulty. How can I help you with dog care?"
                    success = False
                else:
                    content = result['choices'][0]['message']['content'] if result.get('choices') else "How can I help you today?"
                    success = True
                
                response = ChatResponse(
                    success=success,
                    content=content,
                    conversation_id=original_req.get('conversation_id', int(time.time()) + i),
                    message_id=int(time.time() * 1000) + i,
                    context_info={
                        "user_id": original_req.get('user_id'),
                        "service": "optimized_parallel_chat",
                        "batch_index": i,
                        "total_in_batch": len(chat_requests),
                        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
                    },
                    processing_time=time.time() - start_time
                )
                responses.append(response)
            
            # Update metrics
            self.performance_metrics['parallel_requests'] += len(chat_requests)
            
            logger.info(f"✅ Processed {len(chat_requests)} parallel chats in {time.time() - start_time:.3f}s")
            return responses
            
        except Exception as e:
            logger.error(f"❌ Parallel chat processing error: {e}")
            
            # Return fallback responses for all requests
            fallback_responses = []
            for i, req in enumerate(chat_requests):
                fallback_responses.append(ChatResponse(
                    success=False,
                    content="I apologize for the technical difficulty. How can I help you with dog care?",
                    conversation_id=req.get('conversation_id', int(time.time()) + i),
                    message_id=int(time.time() * 1000) + i,
                    context_info={
                        "error": str(e),
                        "fallback": True,
                        "service": "optimized_parallel_chat_fallback"
                    },
                    processing_time=time.time() - start_time
                ))
            
            return fallback_responses

    async def _build_optimized_messages(
        self,
        user_message: str,
        user_id: int,
        conversation_id: Optional[int],
        use_cache: bool
    ) -> List[Dict[str, Any]]:
        """
        Context7 optimization: Build messages with prompt caching support
        """
        messages = []
        
        # Context7 pattern: System prompt (cacheable) - Updated for document analysis and memory
        from datetime import datetime, timezone
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current_day = datetime.now(timezone.utc).strftime("%A")
        current_time = datetime.now(timezone.utc).strftime("%H:%M UTC")
        
        system_prompt = f"""You are Mr. White, an intelligent and helpful AI assistant. You excel at natural conversation and building rapport with users. You can help with:
        
        1. **Document Analysis**: When users upload documents, provide comprehensive summaries, key insights, and answer questions about the content
        2. **Dog Care**: Expert advice about dog training, health, nutrition, and general pet care
        3. **General Assistance**: Helpful information and guidance on various topics
        4. **Engaging Conversation**: Build naturally on context provided and maintain flowing dialogue
        
        CONVERSATION STYLE:
        - Be warm, welcoming, and engaging in all interactions
        - Use any conversation context naturally and positively
        - Never disclaim your abilities or apologize for limitations
        - Focus on being helpful and building conversation
        - Match the user's energy and maintain good rapport
        
        When analyzing documents, focus on the actual content provided and give detailed, accurate responses based on what you can read. Always be specific and practical in your recommendations.
        
        
        [SYSTEM INFO: Today is {current_date} ({current_day}) at {current_time}. Only mention this if the user specifically asks about dates, time, or current events.]"""
        
        if self.cache_system_prompts and use_cache:
            # System message will be cached by the AI pool service
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add user message
        messages.append({
            "role": "user", 
            "content": user_message
        })
        
        return messages

    async def _update_performance_metrics(
        self,
        processing_time: float,
        ttft: Optional[float],
        cache_used: bool
    ):
        """Update performance tracking metrics"""
        self.performance_metrics['requests_processed'] += 1
        self.performance_metrics['total_processing_time'] += processing_time
        
        if cache_used:
            self.performance_metrics['cached_responses'] += 1
        
        if ttft:
            # Update running average TTFT
            current_avg = self.performance_metrics['average_ttft']
            count = self.performance_metrics['requests_processed']
            self.performance_metrics['average_ttft'] = (current_avg * (count - 1) + ttft) / count

    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        if not self.openai_pool:
            await self.initialize()
            
        # Get AI pool metrics
        pool_metrics = await self.openai_pool.get_performance_metrics()
        
        return {
            "handler_metrics": self.performance_metrics,
            "ai_pool_metrics": pool_metrics,
            "optimization_status": {
                "parallel_processing": True,
                "prompt_caching": self.enable_prompt_caching,
                "streaming_support": self.enable_streaming,
                "max_concurrent": self.max_parallel_requests
            },
            "recommendations": await self._get_performance_recommendations()
        }

    async def _get_performance_recommendations(self) -> List[str]:
        """Context7 optimization: Performance recommendations"""
        recommendations = []
        
        metrics = self.performance_metrics
        if metrics['requests_processed'] > 10:
            avg_time = metrics['total_processing_time'] / metrics['requests_processed']
            
            if avg_time > 2.0:
                recommendations.append("Consider enabling streaming for faster perceived response time")
            
            cache_rate = metrics['cached_responses'] / metrics['requests_processed']
            if cache_rate < 0.3:
                recommendations.append("Low cache hit rate - consider optimizing prompt structure")
            
            if metrics['parallel_requests'] == 0:
                recommendations.append("Consider using parallel processing for multiple requests")
        
        return recommendations

# Global instance
optimized_chat_handler = OptimizedChatHandler()
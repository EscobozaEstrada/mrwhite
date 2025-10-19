"""
Health AI Service - Specialized health and medical functionality
Handles health-related queries, care records, and medical assistance
"""

import os
import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import asyncio
import time

import httpx
import redis.asyncio as redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    AsyncSessionLocal, User, CareRecord, Message, HealthChatRequest, ChatResponse,
    get_user_care_records_async
)
from services.shared.async_pinecone_service import AsyncPineconeService
from services.shared.async_parallel_service import AsyncParallelService
from services.shared.async_vector_batch_service import AsyncVectorBatchService
from services.shared.async_cache_service import AsyncCacheService
from services.shared.async_openai_pool_service import get_openai_pool
from utils.async_file_processor import AsyncFileProcessor

from .health_prompts import HealthPrompts

logger = logging.getLogger(__name__)

class HealthAIService:
    """
    Health AI Service for specialized pet health assistance
    Handles health queries, care records, and medical document analysis
    """
    
    def __init__(self, vector_service: AsyncPineconeService, redis_client: redis.Redis, cache_service: AsyncCacheService = None, smart_intent_router=None):
        self.vector_service = vector_service
        self.redis_client = redis_client
        self.cache_service = cache_service
        self.smart_intent_router = smart_intent_router
        
        # Initialize performance optimization services
        self.parallel_service = AsyncParallelService()
        self.vector_batch_service = AsyncVectorBatchService(vector_service)
        
        # Initialize OpenAI client pool (optimized)
        self.openai_pool = None  # Will be initialized on demand
        
        # Health AI configuration
        self.health_model = os.getenv("OPENAI_HEALTH_MODEL", "gpt-4")
        self.max_tokens = int(os.getenv("OPENAI_HEALTH_MAX_TOKENS", "2000"))
        self.temperature = float(os.getenv("OPENAI_HEALTH_TEMPERATURE", "0.3"))  # Lower for health
        
        # Health-specific prompts and knowledge
        self.prompts = HealthPrompts()
        
        # Performance monitoring
        self.parallel_processing_stats = {
            "total_operations": 0,
            "sequential_time": 0.0,
            "parallel_time": 0.0,
            "time_saved": 0.0,
            "efficiency_improvement_percent": 0.0
        }
    
    async def _get_openai_pool(self):
        """Get or initialize the OpenAI client pool"""
        if self.openai_pool is None:
            self.openai_pool = await get_openai_pool(pool_size=5)
        return self.openai_pool
        
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass

    async def process_health_message(
        self,
        user_id: int,
        conversation_id: int,
        message: str,
        files: Optional[List[Dict[str, Any]]] = None,
        health_context: Optional[Dict[str, Any]] = None,
        pet_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process health-related message with medical context and specialized AI
        """
        start_time = time.time()
        
        try:
            # Phase 1: Health intent analysis
            health_analysis = await self._analyze_health_intent(message)
            
            # Phase 2: Parallel context gathering
            tasks = []
            
            # Health context retrieval
            health_context_task = self._gather_health_context(user_id, message, health_context)
            tasks.append(health_context_task)
            
            # Medical file processing (if files provided)
            if files:
                file_task = self._process_health_files(user_id, files)
                tasks.append(file_task)
            
            # Execute context gathering in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            context_data = results[0] if not isinstance(results[0], Exception) else {}
            file_context = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else None
            
            # Phase 3: Enhanced health context preparation
            enhanced_context = await self._prepare_enhanced_health_context(
                message, context_data, file_context, health_analysis, pet_context
            )
            
            # Phase 4: Generate specialized health response
            if health_analysis.get("is_emergency", False):
                ai_response = await self._handle_emergency_response(message, enhanced_context)
            else:
                ai_response = await self._generate_health_response(message, enhanced_context, health_analysis)
            
            # Phase 5: Extract health insights and store interaction
            health_insights = await self._extract_health_insights_async(ai_response)
            
            # Store health interaction for learning
            await self._store_health_interaction(user_id, message, ai_response, health_analysis)
            
            processing_time = time.time() - start_time
            self._update_parallel_processing_stats(processing_time)
            
            return ChatResponse(
                success=True,
                content=ai_response,
                conversation_id=conversation_id,
                message_id=0,  # Will be set by message storage
                context_info={
                    "health_analysis": health_analysis,
                    "health_insights": health_insights,
                    "emergency_detected": health_analysis.get("is_emergency", False),
                    "files_processed": len(files) if files else 0
                },
                sources_used=self._format_health_sources(enhanced_context),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Health message processing error: {str(e)}")
            return {
                "success": False,
                "error": f"Health AI processing failed: {str(e)}",
                "conversation_id": conversation_id,
                "processing_time": time.time() - start_time
            }

    async def _analyze_health_intent(self, message: str) -> Dict[str, Any]:
        """Analyze health-related intent with specialized classification"""
        try:
            # Check cache first
            cache_key = f"health_intent:{hash(message)}"
            cached = await self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Use health-specific intent analysis
            prompt = self.prompts.get_health_intent_prompt(message)
            response = await self._call_health_ai(prompt, max_tokens=300)
            
            try:
                analysis = json.loads(response)
            except json.JSONDecodeError:
                # Fallback analysis
                analysis = self._create_fallback_health_analysis(message)
            
            # Cache for 30 minutes
            await self.redis_client.setex(cache_key, 1800, json.dumps(analysis))
            return analysis
            
        except Exception as e:
            logger.error(f"Health intent analysis error: {str(e)}")
            return self._create_fallback_health_analysis(message)

    def _create_fallback_health_analysis(self, message: str) -> Dict[str, Any]:
        """Create fallback health analysis"""
        emergency_keywords = ["emergency", "urgent", "bleeding", "poison", "collapse", "seizure", "unconscious"]
        symptoms_keywords = ["sick", "vomit", "diarrhea", "cough", "fever", "pain", "limping"]
        behavioral_keywords = ["behavior", "aggressive", "anxious", "scared", "destructive"]
        
        is_emergency = any(keyword in message.lower() for keyword in emergency_keywords)
        has_symptoms = any(keyword in message.lower() for keyword in symptoms_keywords)
        is_behavioral = any(keyword in message.lower() for keyword in behavioral_keywords)
        
        return {
            "intent": "emergency" if is_emergency else ("symptoms" if has_symptoms else ("behavioral" if is_behavioral else "general_health")),
            "is_emergency": is_emergency,
            "severity": "high" if is_emergency else ("medium" if has_symptoms else "low"),
            "confidence": 0.7,
            "keywords": message.split()[:5],
            "requires_vet": is_emergency or has_symptoms,
            "category": "emergency" if is_emergency else "health_query"
        }

    async def _gather_health_context(
        self,
        user_id: int,
        message: str,
        provided_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Gather comprehensive health context"""
        try:
            # Parallel context gathering
            tasks = [
                self._get_user_health_records(user_id),
                self._get_recent_health_interactions(user_id),
                self._search_health_knowledge(message, user_id)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            health_records = results[0] if not isinstance(results[0], Exception) else []
            recent_interactions = results[1] if not isinstance(results[1], Exception) else []
            health_knowledge = results[2] if not isinstance(results[2], Exception) else []
            
            # Extract pet context from health records
            pet_context = self._extract_pet_context(health_records, provided_context)
            
            return {
                "health_records": health_records,
                "recent_interactions": recent_interactions,
                "health_knowledge": health_knowledge,
                "pet_context": pet_context,
                "user_provided_context": provided_context or {}
            }
            
        except Exception as e:
            logger.error(f"Health context gathering error: {str(e)}")
            return {}

    async def _get_user_health_records(self, user_id: int) -> List[CareRecord]:
        """Get user's health records"""
        try:
            async with AsyncSessionLocal() as session:
                return await get_user_care_records_async(session, user_id, limit=20)
        except Exception as e:
            logger.error(f"Health records retrieval error: {str(e)}")
            return []

    async def _get_recent_health_interactions(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent health AI interactions"""
        try:
            cache_key = f"health_interactions:{user_id}"
            cached = await self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)[:limit]
            return []
        except Exception as e:
            logger.error(f"Recent interactions error: {str(e)}")
            return []

    async def _search_health_knowledge(self, message: str, user_id: int) -> List[Dict[str, Any]]:
        """Search health knowledge base"""
        try:
            results = await self.vector_service.search_health_context(
                user_id=user_id,
                query=message,
                top_k=5
            )
            return results
        except Exception as e:
            logger.error(f"Health knowledge search error: {str(e)}")
            return []

    def _extract_pet_context(
        self, 
        health_records: List[CareRecord], 
        provided_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract pet context from health records and provided info"""
        pet_info = {
            "name": "Unknown",
            "breed": "Unknown", 
            "age": "Unknown",
            "weight": "Unknown",
            "medical_history": [],
            "current_medications": [],
            "known_allergies": []
        }
        
        # Extract from provided context
        if provided_context:
            pet_info.update({
                "name": provided_context.get("pet_name", pet_info["name"]),
                "breed": provided_context.get("pet_breed", pet_info["breed"]),
                "age": provided_context.get("pet_age", pet_info["age"]),
                "weight": provided_context.get("pet_weight", pet_info["weight"])
            })
        
        # Extract from health records
        if health_records:
            # Get most recent pet info
            recent_record = health_records[0]
            pet_info.update({
                "name": recent_record.pet_name or pet_info["name"],
                "breed": recent_record.pet_breed or pet_info["breed"],
                "age": recent_record.pet_age or pet_info["age"],
                "weight": recent_record.pet_weight or pet_info["weight"]
            })
            
            # Extract medical history
            for record in health_records[:10]:  # Last 10 records
                if record.category in ["medical", "emergency", "checkup"]:
                    pet_info["medical_history"].append({
                        "date": record.date_occurred.isoformat(),
                        "title": record.title,
                        "category": record.category,
                        "description": record.description
                    })
                
                # Extract medications
                if record.medications:
                    for med in record.medications:
                        if med not in pet_info["current_medications"]:
                            pet_info["current_medications"].append(med)
        
        return pet_info

    async def _prepare_enhanced_health_context(
        self,
        message: str,
        context_data: Dict[str, Any],
        file_context: Optional[str],
        health_analysis: Dict[str, Any],
        pet_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare enhanced context for health AI"""
        return {
            "user_message": message,
            "health_analysis": health_analysis,
            "pet_information": context_data.get("pet_context", {}),
            "medical_history": [record for record in context_data.get("health_records", [])],
            "recent_interactions": context_data.get("recent_interactions", []),
            "relevant_knowledge": context_data.get("health_knowledge", []),
            "medical_documents": file_context,
            "provided_pet_context": pet_context or {}
        }

    async def _generate_health_response(
        self,
        message: str,
        context_data: Dict[str, Any],
        health_analysis: Dict[str, Any]
    ) -> str:
        """Generate specialized health AI response"""
        try:
            # Build health-specific prompt
            health_prompt = self.prompts.build_health_response_prompt(
                message=message,
                context=context_data,
                analysis=health_analysis
            )
            
            # Use health-optimized model parameters
            response = await self._call_health_ai(
                prompt=health_prompt,
                max_tokens=self.max_tokens
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Health response generation error: {str(e)}")
            return self.prompts.get_health_fallback_response(health_analysis)

    async def _handle_emergency_response(
        self, 
        message: str, 
        context_data: Dict[str, Any]
    ) -> str:
        """Handle emergency health situations"""
        emergency_prompt = self.prompts.get_emergency_response_prompt(message, context_data)
        
        response = await self._call_health_ai(
            prompt=emergency_prompt,
            max_tokens=1000
        )
        
        # Add emergency disclaimer
        disclaimer = "\n\n⚠️ EMERGENCY NOTICE: This appears to be an urgent situation. Please contact your veterinarian or emergency animal hospital immediately."
        
        return response + disclaimer

    async def _call_health_ai(self, prompt: str, max_tokens: int = None) -> str:
        """Call OpenAI with health-optimized parameters"""
        try:
            pool = await self._get_openai_pool()
            
            response = await pool.chat_completion(
                messages=[
                    {"role": "system", "content": self.prompts.HEALTH_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                model=self.health_model,
                temperature=self.temperature,
                max_tokens=max_tokens or self.max_tokens
            )
            
            return response["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Health AI call error: {str(e)}")
            return "I apologize, but I'm having trouble processing your health question right now. For any urgent concerns, please contact your veterinarian directly."

    async def _process_health_files(
        self,
        user_id: int,
        files: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Process health-related files with medical context"""
        if not files:
            return None
        
        processed_content = []
        
        for file_info in files:
            try:
                filename = file_info.get('filename', 'unknown')
                description = file_info.get('description', '')
                content = file_info.get('content')  # bytes
                content_type = file_info.get('content_type', 'application/octet-stream')
                
                # Extract text content from health documents
                extracted_text = None
                if content:
                    extracted_text = await AsyncFileProcessor.extract_text_content(content, content_type)
                
                # Build comprehensive health file context
                file_context_parts = [f"Medical Document: {filename}"]
                
                if description:
                    file_context_parts.append(f"Description: {description}")
                
                if extracted_text:
                    # Truncate very long medical documents but preserve important content
                    if len(extracted_text) > 2000:
                        extracted_text = extracted_text[:2000] + f"... [Document continues, total length: {len(extracted_text)} characters]"
                    file_context_parts.append(f"Content: {extracted_text}")
                    logger.info(f"Extracted {len(extracted_text)} characters from medical document '{filename}'")
                else:
                    file_context_parts.append("Content: Unable to extract text from this medical document")
                    logger.warning(f"Could not extract text from medical document '{filename}'")
                
                processed_content.append("\n".join(file_context_parts))
                
            except Exception as e:
                logger.error(f"Error processing medical file {file_info.get('filename', 'unknown')}: {str(e)}")
                processed_content.append(f"Medical Document: {file_info.get('filename', 'unknown')} - Processing Error: {str(e)}")
        
        return "\n\n".join(processed_content) if processed_content else None

    async def _extract_health_insights_async(self, ai_response: str) -> List[str]:
        """Extract health insights from AI response"""
        return self._extract_health_insights(ai_response)

    def _extract_health_insights(self, ai_response: str) -> List[str]:
        """Extract actionable health insights from response"""
        insights = []
        
        # Simple keyword-based extraction (could be enhanced with NLP)
        if "veterinarian" in ai_response.lower() or "vet" in ai_response.lower():
            insights.append("veterinary_consultation_recommended")
        
        if "medication" in ai_response.lower() or "medicine" in ai_response.lower():
            insights.append("medication_mentioned")
        
        if "diet" in ai_response.lower() or "food" in ai_response.lower():
            insights.append("dietary_advice_given")
        
        if "exercise" in ai_response.lower() or "activity" in ai_response.lower():
            insights.append("exercise_recommendation")
        
        if "behavior" in ai_response.lower() or "training" in ai_response.lower():
            insights.append("behavioral_guidance")
        
        return insights

    async def _store_health_interaction(
        self,
        user_id: int,
        message: str,
        response: str,
        health_analysis: Dict[str, Any]
    ):
        """Store health interaction for learning and continuity"""
        try:
            interaction = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "message": message,
                "response": response,
                "analysis": health_analysis,
                "insights": self._extract_health_insights(response)
            }
            
            # Store in Redis for quick access
            cache_key = f"health_interactions:{user_id}"
            cached = await self.redis_client.get(cache_key)
            interactions = json.loads(cached) if cached else []
            
            interactions.insert(0, interaction)  # Add to beginning
            interactions = interactions[:20]  # Keep last 20
            
            await self.redis_client.setex(cache_key, 86400, json.dumps(interactions))  # 24 hours
            
        except Exception as e:
            logger.error(f"Health interaction storage error: {str(e)}")

    def _format_health_sources(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format health context sources for response"""
        sources = []
        
        # Add medical history sources
        for record in context_data.get("medical_history", [])[:3]:
            sources.append({
                "type": "medical_history",
                "title": record.get("title", "Medical Record"),
                "date": record.get("date_occurred", "Unknown"),
                "category": record.get("category", "health")
            })
        
        # Add knowledge base sources
        for knowledge in context_data.get("relevant_knowledge", [])[:2]:
            sources.append({
                "type": "health_knowledge",
                "content": knowledge.get("content", "")[:200],
                "score": knowledge.get("score", 0)
            })
        
        return sources

    # Performance monitoring
    def _update_parallel_processing_stats(self, actual_time: float):
        """Update parallel processing statistics"""
        self.parallel_processing_stats["total_operations"] += 1
        self.parallel_processing_stats["parallel_time"] += actual_time
        
        # Estimate sequential time (health processing would be ~50% slower)
        estimated_sequential_time = actual_time * 1.5
        self.parallel_processing_stats["sequential_time"] += estimated_sequential_time
        
        # Calculate savings
        time_saved = estimated_sequential_time - actual_time
        self.parallel_processing_stats["time_saved"] += time_saved
        
        # Calculate efficiency improvement
        total_parallel = self.parallel_processing_stats["parallel_time"]
        total_sequential = self.parallel_processing_stats["sequential_time"]
        
        if total_sequential > 0:
            efficiency_improvement = ((total_sequential - total_parallel) / total_sequential) * 100
            self.parallel_processing_stats["efficiency_improvement_percent"] = efficiency_improvement

    async def get_parallel_processing_stats(self) -> Dict[str, Any]:
        """Get parallel processing statistics"""
        return {
            "service": "health_ai",
            **self.parallel_processing_stats,
            "health_specific_metrics": {
                "emergency_responses": await self._get_emergency_count(),
                "average_response_time": self.parallel_processing_stats["parallel_time"] / max(1, self.parallel_processing_stats["total_operations"])
            }
        }

    def reset_parallel_processing_stats(self):
        """Reset parallel processing statistics"""
        self.parallel_processing_stats = {
            "total_operations": 0,
            "sequential_time": 0.0,
            "parallel_time": 0.0,
            "time_saved": 0.0,
            "efficiency_improvement_percent": 0.0
        }

    async def _get_emergency_count(self) -> int:
        """Get count of emergency responses handled"""
        try:
            emergency_key = "health_ai:emergency_count"
            count = await self.redis_client.get(emergency_key)
            return int(count) if count else 0
        except:
            return 0
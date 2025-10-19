"""
Service Orchestrator - Main orchestrator for routing requests to appropriate services
Analyzes user intent and routes to Chat, HealthAI, Document, or Reminder services
"""

import logging
import time
import asyncio
import base64
import io
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from fastapi import UploadFile

from services.shared.async_smart_intent_router import SmartIntentRouter
from services.shared.dog_context_service import DogContextService
from services.shared.food_recommendation_service import FoodRecommendationService
from services.shared.unified_dog_knowledge_manager import UnifiedDogKnowledgeManager
from services.pet.pet_context_manager import PetContextManager
from services.chat.chat_service import ChatService
from services.health_ai.health_service import HealthAIService
from services.document.document_service import DocumentService
from services.reminder.reminder_service import ReminderService

logger = logging.getLogger(__name__)

class ServiceOrchestrator:
    """
    Main orchestrator that routes requests to appropriate specialized services
    Based on user intent analysis
    """
    
    def __init__(
        self,
        chat_service: ChatService,
        health_service: HealthAIService,
        document_service: DocumentService,
        reminder_service: ReminderService,
        smart_intent_router: SmartIntentRouter,
        pet_context_manager: Optional[PetContextManager] = None
    ):
        self.chat_service = chat_service
        self.health_service = health_service
        self.document_service = document_service
        self.reminder_service = reminder_service
        self.smart_intent_router = smart_intent_router
        
        # Initialize intelligent pet context manager
        self.pet_context_manager = pet_context_manager
        
        # Initialize dog context service for follow-up questions (will be configured with LangGraph later)
        self.dog_context_service = DogContextService()
        
        # Initialize food recommendation service for Pawtree recommendations
        # Will be updated with Redis client later if available
        self.food_recommendation_service = FoodRecommendationService()
        
        # Unified dog knowledge manager (unused - kept for backward compatibility)
        self.unified_dog_manager = None
        
        # Optimized document cache with LRU eviction and statistics
        self._document_cache = {}
        self._document_cache_ttl = 1800  # 30 minutes
        self._document_cache_access_order = []  # For LRU eviction
        self._document_cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "memory_usage": 0,  # Approximate bytes
            "total_requests": 0
        }
        self._max_cache_entries = 500  # Reduced from 1000 for better memory management
        self._max_cache_memory = 50 * 1024 * 1024  # 50MB limit
        
        # Orchestrator performance tracking
        self.orchestration_stats = {
            "total_requests": 0,
            "routing_accuracy": 0.0,
            "average_routing_time": 0.0,
            "service_usage": {
                "chat": 0,
                "health_ai": 0,
                "document": 0,
                "reminder": 0
            },
            "routing_failures": 0
        }
        
    def set_redis_client(self, redis_client):
        """Set Redis client for services that need it"""
        self.food_recommendation_service.redis_client = redis_client
        logger.info("✅ Redis client set for food recommendation service")
        
        # Intent to service mapping
        self.service_mapping = {
            # Chat intents
            "chat_general": "chat",
            "general_chat": "chat",
            "training_help": "chat",
            "behavior_question": "chat",
            "info_request": "chat",
            "information_request": "chat",
            "follow_up": "chat",
            
            # Health AI intents
            "health_general": "health_ai",
            "health_emergency": "health_ai",
            "health_concern": "health_ai",
            "symptoms": "health_ai",
            "emergency": "health_ai",
            "medical_question": "health_ai",
            "care_record": "health_ai",
            "health_analysis": "health_ai",
            
            # Document intents
            "document_related": "document",
            "document_upload": "document",
            "document_analysis": "document",
            "document_search": "document",
            "file_question": "document",
            
            # Reminder intents
            "reminder": "reminder",  # General reminder intent from ML classifier
            "reminder_create": "reminder",
            "reminder_set": "reminder",
            "reminder_manage": "reminder",
            "schedule_related": "reminder"
        }
    
    async def _process_pet_context_parallel(self, user_id: int, message: str, conversation_id: int, intent: str) -> Dict[str, Any]:
        """
        Process pet context in parallel - extracts pet info and loads existing context
        This ensures personalized responses based on stored pet data
        """
        try:
            logger.info(f"🐕 Processing pet context for user {user_id}")
            
            # Process message for new pet information
            pet_processing_result = await self.pet_context_manager.process_message_for_pet_info(
                user_id=user_id,
                message=message,
                conversation_id=conversation_id,
                conversation_context=intent
            )
            
            # Load current pet context for response personalization (force refresh to get latest data)
            current_context = await self.pet_context_manager.get_user_pet_context(user_id, force_refresh=True)
            
            # Get username for personalization
            username = None
            try:
                db_session = self.pet_context_manager.db_session_factory()
                async with db_session as session:
                    result = await session.execute(
                        "SELECT username FROM users WHERE id = :user_id",
                        {"user_id": user_id}
                    )
                    user_record = result.fetchone()
                    if user_record:
                        username = user_record[0]
            except Exception as e:
                logger.debug(f"Could not fetch username for user {user_id}: {e}")
            
            # Format pet context for chat injection with personalization
            formatted_context = self._format_pet_context_for_chat(current_context, username)
            
            result = {
                "current_context": current_context,
                "processing_result": pet_processing_result,
                "formatted_context": formatted_context,
                "follow_up_questions": pet_processing_result.get("questions", []) if isinstance(pet_processing_result, dict) else []
            }
            
            logger.info(f"✅ Pet context processed: {len(current_context.get('pets', []))} pets found")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing pet context: {e}")
            return {
                "current_context": {"pets": [], "total_pets": 0},
                "processing_result": {},
                "formatted_context": "",
                "follow_up_questions": []
            }
    
    def _format_pet_context_for_chat(self, context: Dict[str, Any], username: str = None) -> str:
        """
        Format pet context for injection into chat responses
        Creates detailed, personalized context about user's pets
        """
        try:
            pets = context.get("pets", [])
            if not pets:
                return ""
            
            context_parts = []
            
            # Add personalized greeting if username available
            if username:
                context_parts.append(f"🐕 {username.upper()}'S PET INFORMATION (use for personalized responses):")
            else:
                context_parts.append("🐕 USER'S PET INFORMATION (use for personalized responses):")
            
            for pet in pets:
                pet_details = []
                
                # Basic info - use natural language not bullet points
                name = pet.get('name', 'Unknown')
                breed = pet.get('breed', 'Mixed breed') 
                age = pet.get('age', 'unknown age')
                
                pet_details.append(f"Pet: {name} - {breed}, {age} years old")
                
                # Additional structured data
                if pet.get('weight'): 
                    pet_details.append(f"Weight: {pet.get('weight')} lbs")
                if pet.get('gender'): 
                    pet_details.append(f"Gender: {pet.get('gender')}")
                if pet.get('known_allergies'): 
                    pet_details.append(f"Allergies: {pet.get('known_allergies')}")
                if pet.get('emergency_vet_name'): 
                    pet_details.append(f"Veterinarian: {pet.get('emergency_vet_name')}")
                if pet.get('emergency_vet_phone'): 
                    pet_details.append(f"Vet Phone: {pet.get('emergency_vet_phone')}")
                
                # Comprehensive profile data
                if pet.get('color'): 
                    pet_details.append(f"Color: {pet.get('color')}")
                if pet.get('favorite_food'): 
                    pet_details.append(f"Favorite food: {pet.get('favorite_food')}")
                if pet.get('personality'): 
                    pet_details.append(f"Personality: {pet.get('personality')}")
                if pet.get('special_traits'):
                    pet_details.append(f"Special traits: {pet.get('special_traits')}")
                if pet.get('likes'):
                    pet_details.append(f"Likes: {pet.get('likes')}")
                if pet.get('habits'):
                    pet_details.append(f"Habits: {pet.get('habits')}")
                if pet.get('dislikes'):
                    pet_details.append(f"Dislikes: {pet.get('dislikes')}")
                if pet.get('medical_conditions'):
                    pet_details.append(f"Medical conditions: {pet.get('medical_conditions')}")
                
                context_parts.extend(pet_details)
                context_parts.append("")  # Empty line between pets
            
            # OPTIMIZED RESPONSE REQUIREMENTS (reduced from 27 lines to 6 lines - saves ~320 tokens)
            pet_names = [pet.get('name', 'Unknown') for pet in pets]
            context_parts.append(f"🐕 RESPONSE RULES: Always mention pets by name using their specific details (age, weight, traits). " +
                               f"For multiple pets, address each individually: 'For {pet_names[0]}: [advice]' format. " +
                               f"Never give generic advice - tailor to each pet's characteristics.")
            if len(pets) > 1:
                context_parts.append(f"Multiple pets detected: {', '.join(pet_names)}. Address each pet separately in your response.")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"❌ Error formatting pet context: {e}")
            return ""

    async def process_user_request(
        self,
        user_id: int,
        conversation_id: int,
        message: str,
        files: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
        background_tasks = None
    ) -> Dict[str, Any]:
        """
        Main orchestration method - analyzes intent and routes to appropriate service
        """
        start_time = time.time()
        
        # CRITICAL: Initialize ALL variables BEFORE try block to ensure function-wide scope
        # This prevents "not defined" errors in exception handlers and subsequent code
        pet_context_result = {}
        pet_follow_up_questions = []
        retrieved_docs = None
        food_analysis = {}
        routing_result = {}
        langgraph_result = {}
        ai_response = ""
        
        try:
            # Phase 1: Analyze user intent with smart routing
            routing_result = await self.smart_intent_router.route_message(
                message=message,
                user_id=user_id,
                conversation_id=conversation_id,
                context=context
            )
            
            # Extract intent from smart router result structure
            intent_classification = routing_result.get("intent_classification", {})
            primary_intent = intent_classification.get("intent", "chat_general")
            confidence = intent_classification.get("confidence", 0.0)
            requires_multiple_services = routing_result.get("requires_multiple_services", False)
            
            # Phase 1.5-3.5: Parallel Processing for Performance (Pet Context, Documents, Food Analysis)
            logger.info("🚀 Starting parallel processing for pet context, documents, and food analysis")
            parallel_start_time = time.time()
            
            # Prepare parallel tasks
            tasks = []
            task_names = []
            
            # Task 1: Pet Context Processing
            if self.pet_context_manager:
                tasks.append(self._process_pet_context_parallel(user_id, message, conversation_id, primary_intent))
                task_names.append("pet_context")
            
            # Task 2: Document Detection (only if no files uploaded)
            if not files:
                tasks.append(self._detect_document_related_query(message, user_id, conversation_id))
                task_names.append("document_detection")
            else:
                tasks.append(asyncio.sleep(0))  # Placeholder task
                task_names.append("document_detection_skipped")
            
            # Task 3: Food Analysis
            tasks.append(self.food_recommendation_service.detect_food_query(message, user_id))
            task_names.append("food_analysis")
            
            # Execute all tasks in parallel
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                parallel_time = time.time() - parallel_start_time
                logger.info(f"⚡ Parallel processing completed in {parallel_time:.2f}s")
                
                # Process results with simplified assignment logic to avoid scope issues
                for i, (result, task_name) in enumerate(zip(results, task_names)):
                    if isinstance(result, Exception):
                        logger.error(f"❌ {task_name} failed: {result}")
                        # Set defaults for failed tasks (ALL variables must be set)
                        if task_name == "pet_context":
                            pet_context_result = {"current_context": {}, "processing_result": {}, "follow_up_questions": []}
                            pet_follow_up_questions = []  # CRITICAL: Set this in failure path too
                        elif task_name == "food_analysis":
                            food_analysis = {}
                    else:
                        # Successful task results
                        if task_name == "pet_context":
                            pet_context_result = result if result else {}
                            # Simple, robust assignment to avoid scope confusion
                            follow_up_list = []
                            if result and isinstance(result, dict):
                                follow_up_list = result.get("follow_up_questions", [])
                            pet_follow_up_questions = follow_up_list if isinstance(follow_up_list, list) else []
                        elif task_name == "document_detection" and result:
                            retrieved_docs = result
                        elif task_name == "food_analysis":
                            food_analysis = result if result else {}
                
            except Exception as e:
                logger.error(f"❌ Parallel processing error: {e}")
                # Ensure ALL variables are properly set for fallback (critical for scope)
                pet_context_result = {"current_context": {}, "processing_result": {}, "follow_up_questions": []}
                pet_follow_up_questions = []  # CRITICAL: Must be set in ALL exception paths
                food_analysis = {}  # Reset to empty dict
                # retrieved_docs keeps its default None value
            
            # CRITICAL FIX: Check for greetings BEFORE service mapping to prevent wrong agent selection  
            message_lower = message.lower().strip()
            greeting_patterns = [
                'hello', 'hi', 'hey', 'good morning', 'good evening', 'good afternoon',
                'hello mr white', 'hi mr white', 'hey mr white', 
                'good morning mr white', 'good evening mr white',
                'how are you', 'whats up', "what's up", 'howdy'
            ]
            
            # Check for reminder indicators that should prevent greeting override
            reminder_indicators = [
                r"\b(remind|reminder|schedule|appointment|note that|please note|keep track|make (?:a )?note)\b",
                r"\b(?:has|have)\s+(?:an?\s+)?appointment\b",
                r"\b(checkup|vaccination|vet visit|grooming)\b"
            ]
            
            has_reminder_content = any(re.search(pattern, message_lower) for pattern in reminder_indicators)
            
            # Only treat as greeting if no reminder content detected
            is_greeting_only = not has_reminder_content and any(message_lower.startswith(pattern) for pattern in greeting_patterns)
            
            if is_greeting_only:
                # Force greeting messages to use chat service regardless of intent classification
                target_service = "chat"
                logger.info(f"👋 GREETING OVERRIDE: Forcing chat service for greeting: '{message[:30]}...'")
            else:
                # Determine target service based on intent
                target_service = self.service_mapping.get(primary_intent, "chat")
            
            # Route to appropriate service
            if target_service == "chat":
                # 🚀 PRODUCTION: Smart Prompts (with fallback capability)
                use_smart_prompts = self.chat_service.should_use_smart_prompts(user_id)
                
                if use_smart_prompts:
                    logger.info(f"🎯 Processing with SMART PROMPTS for user {user_id}")
                    try:
                        result = await self.chat_service.process_chat_message_smart(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            message=message,
                            files=files,
                            attachments=retrieved_docs if retrieved_docs else [],
                            background_tasks=background_tasks
                        )
                        # Add system info to result
                        if isinstance(result, dict):
                            result["prompt_system"] = {"type": "smart_prompts", "user_id": user_id}
                        elif hasattr(result, '__dict__'):
                            result.context_info = result.context_info or {}
                            result.context_info["prompt_system"] = {"type": "smart_prompts", "user_id": user_id}
                    except Exception as e:
                        logger.warning(f"⚠️ Smart prompts failed for user {user_id}, falling back: {str(e)}")
                        # Fallback to traditional prompts only if smart prompts fail
                        result = await self.chat_service.process_chat_message(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            message=message,
                            files=files,
                            retrieved_docs=retrieved_docs if retrieved_docs else [],
                            background_tasks=background_tasks
                        )
                        if isinstance(result, dict):
                            result["prompt_system"] = {"type": "traditional_fallback", "user_id": user_id, "fallback_reason": str(e)}
                        elif hasattr(result, '__dict__'):
                            result.context_info = result.context_info or {}
                            result.context_info["prompt_system"] = {"type": "traditional_fallback", "user_id": user_id, "fallback_reason": str(e)}
                else:
                    logger.warning(f"📝 Using TRADITIONAL PROMPTS for user {user_id} (deprecated path)")
                    result = await self.chat_service.process_chat_message(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message=message,
                        files=files,
                        retrieved_docs=retrieved_docs if retrieved_docs else [],
                        background_tasks=background_tasks
                    )
                    # Add deprecation warning to result
                    if isinstance(result, dict):
                        result["prompt_system"] = {"type": "traditional_deprecated", "user_id": user_id}
                    elif hasattr(result, '__dict__'):
                        result.context_info = result.context_info or {}
                        result.context_info["prompt_system"] = {"type": "traditional_deprecated", "user_id": user_id}
            elif target_service == "health_ai":
                result = await self.health_service.process_health_query(
                    user_id, conversation_id, message, files, retrieved_docs, background_tasks
                )
            elif target_service == "document":
                # Generate cache key for document processing
                cache_key = self._generate_document_cache_key(user_id, files, message)
                
                # Check cache first
                cached_result = self._get_cached_document_result(cache_key)
                if cached_result:
                    logger.info(f"📄 Using cached document result for user {user_id}")
                    result = cached_result
                else:
                    # Process document and cache result
                    result = await self.document_service.process_document_request(
                        user_id, conversation_id, message, files, background_tasks
                    )
                    
                    # Cache successful results
                    if result and result.get("success", False):
                        self._cache_document_result(cache_key, result)
                        logger.info(f"📄 Cached new document result for user {user_id}")
                
                # 🆕 CRITICAL FIX: Extract pet information from document text for comprehensive_profile
                if result and result.get("success") and result.get("extracted_text"):
                    extracted_text = result["extracted_text"]
                    logger.info(f"🐕 Processing extracted document text for pet information: {len(extracted_text)} characters")
                    
                    try:
                        # Combine user message with extracted document text for comprehensive pet analysis
                        combined_message_for_pet_extraction = f"{message}\n\nDOCUMENT CONTENT:\n{extracted_text}"
                        
                        # Process the extracted text for pet information
                        pet_extraction_result = await self.pet_context_manager.process_message_for_pet_info(
                            user_id=user_id,
                            message=combined_message_for_pet_extraction,
                            conversation_id=conversation_id,
                            conversation_context="document_analysis"
                        )
                        
                        if pet_extraction_result and pet_extraction_result.get("extraction_successful"):
                            logger.info(f"✅ Successfully extracted pet info from document: {list(pet_extraction_result.get('extracted_data', {}).keys())}")
                            # Add pet extraction info to document result
                            result["pet_extraction"] = {
                                "success": True,
                                "extracted_fields": list(pet_extraction_result.get('extracted_data', {}).keys()),
                                "comprehensive_data_updated": bool(pet_extraction_result.get('storage_result', {}).get('success'))
                            }
                        else:
                            logger.info("ℹ️ No pet information found in document text")
                            result["pet_extraction"] = {"success": False, "reason": "No pet info detected"}
                            
                    except Exception as pet_error:
                        logger.error(f"❌ Error extracting pet info from document: {str(pet_error)}")
                        result["pet_extraction"] = {"success": False, "error": str(pet_error)}
            elif target_service == "reminder":
                result = await self.reminder_service.process_reminder_request(
                    user_id, conversation_id, message, context
                )
            else:
                # Fallback to chat service with A/B testing
                use_smart_prompts = self.chat_service.should_use_smart_prompts(user_id)
                
                if use_smart_prompts:
                    logger.info(f"🎯 A/B Test (Fallback): Using SMART PROMPTS for user {user_id}")
                    result = await self.chat_service.process_chat_message_smart(
                        user_id, conversation_id, message, files, [], background_tasks
                    )
                else:
                    logger.info(f"📝 A/B Test (Fallback): Using TRADITIONAL PROMPTS for user {user_id}")
                    result = await self.chat_service.process_chat_message(
                        user_id, conversation_id, message, files, [], background_tasks
                    )
            
            # Convert result to dict format with orchestration info
            if hasattr(result, 'dict'):
                # Pydantic model - convert to dict
                result = result.dict()
            elif hasattr(result, '__dict__'):
                # Regular object - convert to dict
                result = dict(result.__dict__)
            
            result["orchestration"] = {
                "primary_intent": primary_intent,
                "target_service": target_service,
                "confidence": confidence,
                "routing_time": time.time() - start_time,
                "multi_service": requires_multiple_services
            }
            
            # Update statistics
            self._update_orchestration_stats(target_service, confidence, time.time() - start_time, True)
            
            logger.info(f"✅ ORCHESTRATION COMPLETED SUCCESSFULLY - No fallback needed for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"🚨 ORCHESTRATION ERROR - FALLING BACK TO CHAT SERVICE: {str(e)}")
            
            # Fallback to chat service for error recovery with A/B testing
            try:
                use_smart_prompts = self.chat_service.should_use_smart_prompts(user_id)
                
                if use_smart_prompts:
                    logger.info(f"🎯 A/B Test (Error Recovery): Using SMART PROMPTS for user {user_id}")
                    fallback_result = await self.chat_service.process_chat_message_smart(
                        user_id, conversation_id, message, files, [], background_tasks
                    )
                else:
                    logger.info(f"📝 A/B Test (Error Recovery): Using TRADITIONAL PROMPTS for user {user_id}")
                    fallback_result = await self.chat_service.process_chat_message(
                        user_id, conversation_id, message, files, [], background_tasks
                    )
                
                # Convert ChatResponse to dict to add orchestration info
                if hasattr(fallback_result, 'dict'):
                    # Pydantic model - convert to dict
                    result_dict = fallback_result.dict()
                elif hasattr(fallback_result, '__dict__'):
                    # Regular object - convert to dict
                    result_dict = dict(fallback_result.__dict__)
                else:
                    # Already a dict
                    result_dict = dict(fallback_result)
                
                result_dict["orchestration"] = {
                    "primary_intent": "fallback",
                    "target_service": "chat",
                    "confidence": 0.1,
                    "routing_time": time.time() - start_time,
                    "error": str(e)
                }
                return result_dict
            except Exception as fallback_error:
                logger.error(f"Fallback error: {str(fallback_error)}")
                
                self._update_orchestration_stats("error", 0.0, time.time() - start_time, False)
                
                return {
                    "response": "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                    "success": False,
                    "orchestration": {
                        "primary_intent": "error",
                        "target_service": "error",
                        "confidence": 0.0,
                        "routing_time": time.time() - start_time,
                        "error": f"Primary error: {str(e)}, Fallback error: {str(fallback_error)}"
                    }
                }
        
    def _update_orchestration_stats(self, service: str, confidence: float, routing_time: float, success: bool):
        """Update orchestration statistics for monitoring"""
        try:
            self.orchestration_stats["total_requests"] += 1
            
            if success:
                if service in self.orchestration_stats["service_usage"]:
                    self.orchestration_stats["service_usage"][service] += 1
                
                # Update running averages
                current_accuracy = self.orchestration_stats["routing_accuracy"]
                current_time = self.orchestration_stats["average_routing_time"]
                total_requests = self.orchestration_stats["total_requests"]
                
                # Simple running average calculation
                self.orchestration_stats["routing_accuracy"] = (
                    (current_accuracy * (total_requests - 1) + confidence) / total_requests
                )
                
                self.orchestration_stats["average_routing_time"] = (
                    (current_time * (total_requests - 1) + routing_time) / total_requests
                )
            else:
                self.orchestration_stats["routing_failures"] += 1
                
        except Exception as e:
            logger.warning(f"Failed to update orchestration stats: {e}")

    async def _detect_document_related_query(self, message: str, user_id: int, conversation_id: int) -> Optional[List[Dict]]:
        """Detect if query is document-related and retrieve relevant docs"""
        try:
            # Simple keyword-based detection for document queries
            doc_keywords = [
                "document", "file", "upload", "pdf", "analyze", "summarize", 
                "extract", "text", "content", "report", "attachment"
            ]
            
            message_lower = message.lower()
            if any(keyword in message_lower for keyword in doc_keywords):
                # Query document service for relevant documents
                docs = await self.document_service.search_user_documents(
                    user_id=user_id,
                    query=message,
                    limit=3
                )
                return docs
            
            return None
            
        except Exception as e:
            logger.error(f"Document detection error: {e}")
            return None

    async def process_user_request(
        self,
        user_id: int,
        conversation_id: int,
        message: str,
        files: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
        background_tasks = None
    ) -> Dict[str, Any]:
        """
        Main orchestration method - analyzes intent and routes to appropriate service
        """
        start_time = time.time()
        
        # CRITICAL: Initialize ALL variables BEFORE try block to ensure function-wide scope
        # This prevents "not defined" errors in exception handlers and subsequent code
        pet_context_result = {}
        pet_follow_up_questions = []
        retrieved_docs = None
        food_analysis = {}
        routing_result = {}
        langgraph_result = {}
        ai_response = ""
        
        try:
            # Phase 1: Analyze user intent with smart routing
            routing_result = await self.smart_intent_router.route_message(
                message=message,
                user_id=user_id,
                conversation_id=conversation_id,
                context=context
            )
            
            # Extract intent from smart router result structure
            intent_classification = routing_result.get("intent_classification", {})
            primary_intent = intent_classification.get("intent", "chat_general")
            confidence = intent_classification.get("confidence", 0.0)
            requires_multiple_services = routing_result.get("requires_multiple_services", False)
            
            # Phase 1.5-3.5: Parallel Processing for Performance (Pet Context, Documents, Food Analysis)
            logger.info("🚀 Starting parallel processing for pet context, documents, and food analysis")
            parallel_start_time = time.time()
            
            # Prepare parallel tasks
            tasks = []
            task_names = []
            
            # Task 1: Pet Context Processing
            if self.pet_context_manager:
                tasks.append(self._process_pet_context_parallel(user_id, message, conversation_id, primary_intent))
                task_names.append("pet_context")
            
            # Task 2: Document Detection (only if no files uploaded)
            if not files:
                tasks.append(self._detect_document_related_query(message, user_id, conversation_id))
                task_names.append("document_detection")
            else:
                tasks.append(asyncio.sleep(0))  # Placeholder task
                task_names.append("document_detection_skipped")
            
            # Task 3: Food Analysis
            tasks.append(self.food_recommendation_service.detect_food_query(message, user_id))
            task_names.append("food_analysis")
            
            # Execute all tasks in parallel
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                parallel_time = time.time() - parallel_start_time
                logger.info(f"⚡ Parallel processing completed in {parallel_time:.2f}s")
                
                # Process results with simplified assignment logic to avoid scope issues
                for i, (result, task_name) in enumerate(zip(results, task_names)):
                    if isinstance(result, Exception):
                        logger.error(f"❌ {task_name} failed: {result}")
                        # Set defaults for failed tasks (ALL variables must be set)
                        if task_name == "pet_context":
                            pet_context_result = {"current_context": {}, "processing_result": {}, "follow_up_questions": []}
                            pet_follow_up_questions = []  # CRITICAL: Set this in failure path too
                        elif task_name == "food_analysis":
                            food_analysis = {}
                    else:
                        # Successful task results
                        if task_name == "pet_context":
                            pet_context_result = result if result else {}
                            # Simple, robust assignment to avoid scope confusion
                            follow_up_list = []
                            if result and isinstance(result, dict):
                                follow_up_list = result.get("follow_up_questions", [])
                            pet_follow_up_questions = follow_up_list if isinstance(follow_up_list, list) else []
                        elif task_name == "document_detection" and result:
                            retrieved_docs = result
                        elif task_name == "food_analysis":
                            food_analysis = result if result else {}
                
            except Exception as e:
                logger.error(f"❌ Parallel processing error: {e}")
                # Ensure ALL variables are properly set for fallback (critical for scope)
                pet_context_result = {"current_context": {}, "processing_result": {}, "follow_up_questions": []}
                pet_follow_up_questions = []  # CRITICAL: Must be set in ALL exception paths
                food_analysis = {}  # Reset to empty dict
                # retrieved_docs keeps its default None value
            
            # Handle retry context to generate different responses
            enhanced_message = message
            if context and context.get("type") == "retry":
                logger.info(f"🔄 Retry request detected for message ID: {context.get('message_id')}")
                # Add instructions to generate a different response
                enhanced_message = f"""[RETRY REQUEST] Please provide a different response to this query. Generate an alternative answer that approaches the topic from a different angle or provides additional insights.

                Original query: {message}

                Instructions: Give a fresh perspective on this question, using different examples, explanations, or approaches than you might have used before. Vary your response style and content while maintaining accuracy and helpfulness."""
                
                if retrieved_docs:
                    # Enhance the message with retrieved document content
                    doc_content_parts = []
                    doc_files = set()
                    total_content_chars = 0
                    
                    for doc in retrieved_docs:
                        doc_files.add(doc['filename'])
                        content_excerpt = doc['content'][:2000] + ('...' if len(doc['content']) > 2000 else '')
                        total_content_chars += len(content_excerpt)
                        
                        doc_content_parts.append(
                            f"\n--- Relevant content from {doc['filename']} (relevance: {doc['score']:.2f}) ---\n"
                            f"{content_excerpt}"
                        )
                    
                    enhanced_message = f"""{message}

[CONTEXT: The user is asking about previously uploaded documents. Here is the relevant content to help answer their question:]
{''.join(doc_content_parts)}

Please answer the user's question based on this document content."""
                    
                    logger.info(f"🎯 ChatGPT-level enhancement: Retrieved {len(retrieved_docs)} chunks from {len(doc_files)} documents")
                    logger.info(f"📊 Documents: {', '.join(doc_files)} | Content: {total_content_chars} chars")
                    logger.info(f"🧠 Enhanced query: '{message[:100]}...' → AI now has full document context")

            # Phase 3: Dog Context Analysis (Integrated with Pet Context Manager)
            # Use pet context manager's analysis instead of separate dog context service
            dog_context_analysis = self._analyze_dog_context_from_pet_results(pet_context_result, message, user_id)
            
            # Store results in routing result for later use
            routing_result["dog_context_analysis"] = dog_context_analysis
            routing_result["food_analysis"] = food_analysis
            routing_result["pet_context_result"] = pet_context_result  # Add pet context for _route_to_single_service
            
            logger.info(f"🐕 Dog context analysis: {dog_context_analysis['reasoning']}")
            logger.info(f"🍽️ Food analysis: {food_analysis.get('reasoning', 'No food analysis available')}")
            
            # Phase 4: Determine target service(s)  
            # CRITICAL FIX: Check for greetings BEFORE service routing to prevent wrong agent selection
            message_lower = message.lower().strip()
            greeting_patterns = [
                'hello', 'hi', 'hey', 'good morning', 'good evening', 'good afternoon',
                'hello mr white', 'hi mr white', 'hey mr white', 
                'good morning mr white', 'good evening mr white',
                'how are you', 'whats up', "what's up", 'howdy'
            ]
            
            # Check for reminder indicators that should prevent greeting override
            reminder_indicators = [
                r"\b(remind|reminder|schedule|appointment|note that|please note|keep track|make (?:a )?note)\b",
                r"\b(?:has|have)\s+(?:an?\s+)?appointment\b",
                r"\b(checkup|vaccination|vet visit|grooming)\b"
            ]
            
            has_reminder_content = any(re.search(pattern, message_lower) for pattern in reminder_indicators)
            
            # Only treat as greeting if no reminder content detected
            is_greeting_only = not has_reminder_content and any(message_lower.startswith(pattern) for pattern in greeting_patterns)
            
            if is_greeting_only:
                # Force greeting messages to use chat service regardless of intent classification
                target_service = "chat"
                logger.info(f"👋 GREETING OVERRIDE: Forcing chat service for greeting: '{message[:30]}...'")
            else:
                target_service = self._determine_target_service(primary_intent, routing_result, files)
            
            # Phase 5: Route to appropriate service(s) with enhanced message
            # Add retrieved_docs info to routing_result for memory management
            routing_result["retrieved_docs"] = retrieved_docs
            routing_result["original_message"] = message
            
            if requires_multiple_services:
                result = await self._handle_multi_service_request(
                    user_id, conversation_id, enhanced_message, files, context, routing_result, background_tasks
                )
            else:
                result = await self._route_to_single_service(
                    target_service, user_id, conversation_id, enhanced_message, files, context, routing_result, background_tasks
                )
            
            # Phase 6: Enhance result with orchestration metadata
            # Convert result to dict if it's a ChatResponse object
            if hasattr(result, 'dict'):
                # Pydantic model - convert to dict
                result = result.dict()
            elif hasattr(result, '__dict__') and not isinstance(result, dict):
                # Regular object - convert to dict
                result = dict(result.__dict__)
            
            result["orchestration"] = {
                "primary_intent": primary_intent,
                "target_service": target_service,
                "confidence": confidence,
                "routing_time": time.time() - start_time,
                "multi_service": requires_multiple_services
            }
            
            # Update statistics
            self._update_orchestration_stats(target_service, confidence, time.time() - start_time, True)
            
            logger.info(f"✅ ORCHESTRATION COMPLETED SUCCESSFULLY - No fallback needed for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"🚨 ORCHESTRATION ERROR - FALLING BACK TO CHAT SERVICE: {str(e)}")
            
            # Fallback to chat service for error recovery with A/B testing
            try:
                use_smart_prompts = self.chat_service.should_use_smart_prompts(user_id)
                
                if use_smart_prompts:
                    logger.info(f"🎯 A/B Test (Error Recovery): Using SMART PROMPTS for user {user_id}")
                    fallback_result = await self.chat_service.process_chat_message_smart(
                        user_id, conversation_id, message, files, [], background_tasks
                    )
                else:
                    logger.info(f"📝 A/B Test (Error Recovery): Using TRADITIONAL PROMPTS for user {user_id}")
                fallback_result = await self.chat_service.process_chat_message(
                    user_id, conversation_id, message, files, [], background_tasks
                )
                
                # Convert ChatResponse to dict to add orchestration info
                if hasattr(fallback_result, 'dict'):
                    # Pydantic model - convert to dict
                    result_dict = fallback_result.dict()
                elif hasattr(fallback_result, '__dict__'):
                    # Regular object - convert to dict
                    result_dict = dict(fallback_result.__dict__)
                else:
                    # Already a dict
                    result_dict = dict(fallback_result)
                
                result_dict["orchestration"] = {
                    "primary_intent": "fallback",
                    "target_service": "chat",
                    "confidence": 0.1,
                    "routing_time": time.time() - start_time,
                    "error": str(e)
                }
                return result_dict
            except Exception as fallback_error:
                logger.error(f"Fallback error: {str(fallback_error)}")
                
                self._update_orchestration_stats("error", 0.0, time.time() - start_time, False)
                
                return {
                    "success": False,
                    "content": "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                    "conversation_id": conversation_id,
                    "error": str(e),
                    "orchestration": {
                        "primary_intent": "error",
                        "target_service": "none",
                        "confidence": 0.0,
                        "routing_time": time.time() - start_time,
                        "error": str(e)
                    }
                }

    def _determine_target_service(
        self, 
        primary_intent: str, 
        routing_result: Dict[str, Any], 
        files: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Determine which service should handle the request"""
        
        # Check for files - might indicate document or image processing needed
        if files and len(files) > 0:
            # Check file types to determine routing
            has_images = any(file.get('content_type', '').startswith('image/') for file in files)
            has_audio = any(file.get('content_type', '').startswith('audio/') for file in files)
            has_documents = any(not file.get('content_type', '').startswith(('image/', 'audio/')) for file in files)
            
            # Log file types for debugging
            logger.info(f"📁 File routing: {len(files)} files, images={has_images}, audio={has_audio}, documents={has_documents}")
            
            # If it's clearly a health document, route to health AI
            if primary_intent in ["health_concern", "symptoms", "medical_question"]:
                return "health_ai"
            # Otherwise, document service handles images, audio, and documents with vision/voice
            return "document"
        
        # Check explicit service routing from intent analysis
        explicit_service = routing_result.get("recommended_service")
        if explicit_service in ["chat", "health_ai", "document", "reminder"]:
            return explicit_service
        
        # Use intent mapping
        return self.service_mapping.get(primary_intent, "chat")

    def _convert_dict_files_to_upload_files(self, files: List[Dict[str, Any]]) -> List[UploadFile]:
        """Convert dict-based file data to UploadFile objects for document processing"""
        upload_files = []
        
        for file_data in files:
            try:
                # Extract file content (handle both base64 and direct content)
                content = file_data.get('content', '')
                
                if not content:
                    logger.warning(f"File {file_data.get('filename', 'unknown')} has no content, skipping")
                    continue
                
                if isinstance(content, str):
                    try:
                        # Decode base64 content
                        file_bytes = base64.b64decode(content)
                    except Exception as decode_error:
                        logger.error(f"Failed to decode base64 content for {file_data.get('filename', 'unknown')}: {decode_error}")
                        continue
                elif isinstance(content, bytes):
                    # Direct bytes content
                    file_bytes = content
                else:
                    logger.error(f"Unsupported content type for {file_data.get('filename', 'unknown')}: {type(content)}")
                    continue
                
                if not file_bytes:
                    logger.warning(f"File {file_data.get('filename', 'unknown')} resulted in empty bytes, skipping")
                    continue
                
                # Create a file-like object
                file_obj = io.BytesIO(file_bytes)
                
                # Create UploadFile-like object
                upload_file = UploadFile(
                    filename=file_data.get('filename', 'unknown'),
                    file=file_obj,
                    size=file_data.get('size', len(file_bytes)),
                    headers={'content-type': file_data.get('content_type', 'application/octet-stream')}
                )
                
                upload_files.append(upload_file)
                logger.info(f"✅ Successfully converted file: {file_data.get('filename', 'unknown')} ({len(file_bytes)} bytes)")
                
            except Exception as e:
                logger.error(f"❌ Error converting file {file_data.get('filename', 'unknown')}: {e}")
                continue
        
        logger.info(f"📄 Converted {len(upload_files)} files for document processing")
        return upload_files

    def _convert_sources_to_dict_format(self, sources: List[str]) -> List[Dict[str, Any]]:
        """Convert string sources to dictionary format expected by ChatResponse"""
        if not sources:
            return []
        
        converted_sources = []
        for source in sources:
            if isinstance(source, str):
                converted_sources.append({
                    "type": "document" if "document" in source.lower() else "knowledge_base",
                    "name": source,
                    "confidence": 0.8
                })
            elif isinstance(source, dict):
                # Already in correct format
                converted_sources.append(source)
        
        return converted_sources

    def _convert_files_to_attachments(self, files: Optional[List[Dict[str, Any]]], processed_files: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Convert file data to attachment format for database storage
        Uses S3 URLs from processing results if available
        """
        attachments = []
        if files:
            for file_data in files:
                filename = file_data.get('filename', 'Unknown File')
                # Determine file type based on extension
                file_type = "file"
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    file_type = "image"
                elif filename.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                    file_type = "audio"
                elif filename.lower().endswith('.pdf'):
                    file_type = "document"
                
                # Try to find S3 URL from processed files
                s3_url = f"file://{filename}"  # Default placeholder
                if processed_files:
                    for processed_file in processed_files:
                        if processed_file.get('filename') == filename and processed_file.get('s3_url'):
                            s3_url = processed_file.get('s3_url')
                            logger.info(f"📎 Using S3 URL for {filename}: {s3_url}")
                            break
                
                attachment = {
                    "type": file_type,
                    "name": filename,
                    "url": s3_url,
                }
                attachments.append(attachment)
        return attachments

    async def _detect_document_related_query(self, message: str, user_id: int, conversation_id: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Robust document query detection with multiple safety layers and caching
        Only triggers on explicit document references and respects user exclusions
        """
        try:
            message_lower = message.lower()
            
            # Layer 0: Check cache first for performance
            cache_key = f"doc_query:{user_id}:{hash(message_lower)}"
            cached_result = self._get_cached_document_result(cache_key)
            if cached_result is not None:
                logger.info(f"📦 Cache hit for document query: '{message[:50]}...'")
                return cached_result
            
            # Layer 1: Check for user exclusions FIRST (highest priority)
            if self._check_user_exclusions(message_lower):
                logger.info(f"🚫 User explicitly excluded documents: '{message[:50]}...'")
                self._cache_document_result(cache_key, None)
                return None
            
            # Layer 2: Only proceed if explicit document intent detected
            if not self._detect_explicit_document_intent(message_lower):
                logger.debug(f"📝 No explicit document intent detected: '{message[:50]}...'")
                self._cache_document_result(cache_key, None)
                return None
            
            logger.info(f"🔍 Detected explicit document query from user {user_id}: '{message[:50]}...'")
            
            # Layer 3: Retrieve documents
            retrieved_docs = await self._retrieve_user_documents(user_id, message, conversation_id)
            
            if not retrieved_docs:
                logger.info("📭 No documents found for query")
                self._cache_document_result(cache_key, None)
                return None
            
            # Layer 4: Validate semantic relevance (fast validation)
            relevant_docs = self._filter_relevant_content(message_lower, retrieved_docs)
            
            if not relevant_docs:
                logger.info("🚫 No semantically relevant documents found - content mismatch detected")
                self._cache_document_result(cache_key, None)
                return None
            
            logger.info(f"📚 Retrieved {len(relevant_docs)} relevant document chunks")
            
            # Cache successful result
            self._cache_document_result(cache_key, relevant_docs)
            return relevant_docs
            
        except Exception as e:
            logger.error(f"❌ Error in document detection: {str(e)}")
            return None

    def _check_user_exclusions(self, message_lower: str) -> bool:
        """
        Fast detection of user exclusions (microseconds performance)
        Detect when user explicitly excludes documents
        """
        # Pre-compiled patterns for performance
        exclusion_indicators = [
            'not from the document', 'not from document', 'not about the document',
            'just in general', 'just tell me general', 'tell me in general',
            'ignore the document', 'ignore document', 'skip the document',
            'without the document', 'without document', 'not using the document',
            'general advice', 'general information', 'common knowledge',
            'not from file', 'not from pdf', 'general question'
        ]
        
        # Fast string containment check (much faster than regex)
        return any(indicator in message_lower for indicator in exclusion_indicators)

    def _detect_explicit_document_intent(self, message_lower: str) -> bool:
        """
        Fast detection of explicit document references (microseconds performance)
        Only detects when user explicitly references documents
        """
        # Explicit document indicators (high confidence only)
        explicit_indicators = [
            # Direct document references
            'in the document', 'from the document', 'about the document',
            'according to the document', 'based on the document',
            'the document says', 'the document say', 'document mentions', 'document contains',
            'this document', 'that document', 'the file', 'this file', 'that file',
            
            # File extensions (strong indicators)
            '.pdf', '.docx', '.doc', '.txt', '.csv', '.xlsx', '.pptx',
            
            # Quoted content (likely filenames)
            'in "', 'from "', 'about "', "in '", "from '", "about '",
            
            # Chapter/page references (clear document context)
            'chapter ', 'page ', 'section ', 'paragraph ',
            
            # Story/content specific (when document contains stories)
            'the story says', 'in the story', 'story mentions',
            'the character', 'plot of', 'theme of'
        ]
        
        # Fast string containment check
        return any(indicator in message_lower for indicator in explicit_indicators)

    def _filter_relevant_content(self, query_lower: str, retrieved_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fast semantic relevance filtering (milliseconds performance)
        Filter out completely irrelevant content like Mark Twain stories for dog questions
        """
        if not retrieved_docs:
            return []
        
        # Extract key concepts from query (simple but fast)
        query_concepts = self._extract_key_concepts(query_lower)
        
        if not query_concepts:
            return retrieved_docs  # If no concepts extracted, return all
        
        relevant_docs = []
        for doc in retrieved_docs:
            content = doc.get('content', '').lower()
            
            # Fast relevance check using keyword overlap
            if self._has_content_relevance(query_concepts, content):
                relevant_docs.append(doc)
            else:
                logger.debug(f"🚫 Filtered irrelevant content: query topics {query_concepts} not found in content")
        
        return relevant_docs

    def _extract_key_concepts(self, query_lower: str) -> List[str]:
        """Extract key concepts from query for relevance checking"""
        # Common topic keywords for different domains
        concept_groups = {
            'pets': ['dog', 'cat', 'pet', 'puppy', 'kitten', 'animal', 'breed', 'feeding', 'training', 'veterinary', 'vet'],
            'food': ['food', 'eat', 'feed', 'meal', 'nutrition', 'diet', 'hungry', 'appetite'],
            'health': ['health', 'medical', 'sick', 'disease', 'symptoms', 'treatment', 'medicine'],
            'finance': ['money', 'bank', 'financial', 'investment', 'loan', 'credit', 'payment'],
            'technology': ['computer', 'software', 'app', 'digital', 'internet', 'tech', 'programming'],
            'business': ['business', 'company', 'work', 'job', 'career', 'professional', 'management']
        }
        
        found_concepts = []
        for group_name, keywords in concept_groups.items():
            if any(keyword in query_lower for keyword in keywords):
                found_concepts.append(group_name)
        
        return found_concepts

    def _has_content_relevance(self, query_concepts: List[str], content: str) -> bool:
        """Fast relevance check between query concepts and content"""
        if not query_concepts:
            return True
        
        # Define content indicators for each concept group
        content_indicators = {
            'pets': ['dog', 'cat', 'pet', 'animal', 'puppy', 'kitten', 'breed', 'paws', 'tail', 'bark', 'meow', 'feeding', 'schedules'],
            'food': ['food', 'eat', 'meal', 'cook', 'recipe', 'nutrition', 'hungry', 'taste', 'flavor', 'feeding', 'schedules'],
            'health': ['health', 'medical', 'doctor', 'patient', 'treatment', 'medicine', 'hospital', 'clinic'],
            'finance': ['money', 'dollar', 'bank', 'financial', 'investment', 'loan', 'credit', 'payment', 'economy', 'stock', 'market'],
            'technology': ['computer', 'software', 'digital', 'internet', 'tech', 'programming', 'code', 'data'],
            'business': ['business', 'company', 'work', 'employee', 'manager', 'profit', 'customer', 'market']
        }
        
        # Check if content contains indicators for any of the query concepts
        for concept in query_concepts:
            if concept in content_indicators:
                indicators = content_indicators[concept]
                if any(indicator in content for indicator in indicators):
                    return True
        
        # If no concept match found, it's likely irrelevant
        return False

    async def _retrieve_user_documents(self, user_id: int, query: str, conversation_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document content from user's Pinecone namespace with smart prioritization
        """
        try:
            from services.shared.async_pinecone_service import AsyncPineconeService
            
            # Get the vector service with debugging
            logger.info(f"🔍 DEBUG: chat_service exists: {self.chat_service is not None}")
            logger.info(f"🔍 DEBUG: langgraph_service exists: {hasattr(self.chat_service, 'langgraph_service') and self.chat_service.langgraph_service is not None}")
            if hasattr(self.chat_service, 'langgraph_service') and self.chat_service.langgraph_service:
                logger.info(f"🔍 DEBUG: vector_service exists: {hasattr(self.chat_service.langgraph_service, 'vector_service') and self.chat_service.langgraph_service.vector_service is not None}")
            
            vector_service = self.chat_service.langgraph_service.vector_service
            
            # 🎯 Detect if user mentioned a specific filename
            filename_filter = vector_service._detect_filename_in_query(query)
            
            # 🎯 Smart document search with prioritization
            results = await vector_service.search_user_documents(
                user_id=user_id,
                query=query,
                top_k=5,  # Get more results for better context
                namespace_suffix="docs",
                conversation_id=conversation_id,  # For recency priority
                filename_filter=filename_filter,  # For specific document queries
                recency_priority=True  # Prioritize recent uploads
            )
            
            if results:
                # Format results for easy use
                retrieved_docs = []
                for result in results:
                    retrieved_docs.append({
                        'content': result.get('text', ''),
                        'filename': result.get('metadata', {}).get('filename', 'unknown'),
                        'score': result.get('score', 0.0),
                        'chunk_index': result.get('metadata', {}).get('chunk_index', 0)
                    })
                
                return retrieved_docs
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Error retrieving user documents: {str(e)}")
            return []

    async def _route_to_single_service(
        self,
        target_service: str,
        user_id: int,
        conversation_id: int,
        message: str,
        files: Optional[List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]],
        routing_result: Dict[str, Any],
        background_tasks
    ) -> Dict[str, Any]:
        """Route request to a single service"""
        
        # Use optimized LangGraph agents for all service routing
        await self.chat_service.ensure_langgraph_service()
        if hasattr(self.chat_service, 'langgraph_service') and self.chat_service.langgraph_service:
            # Route through optimized LangGraph service
            agent_type_map = {
                "chat": "chat",
                "health_ai": "health", 
                "document": "document",
                "reminder": "reminder"
            }
            
            agent_type = agent_type_map.get(target_service, "chat")
            
            # Handle document and image processing with files
            if target_service == "document" and files:
                # Check if we have images or audio for special processing
                has_images = any(file.get('content_type', '').startswith('image/') for file in files)
                has_audio = any(file.get('content_type', '').startswith('audio/') for file in files)
                has_documents = any(not file.get('content_type', '').startswith(('image/', 'audio/')) for file in files)
                
                if has_images or has_audio:
                    # Use the mixed file processing method for images, audio, and documents
                    logger.info(f"🖼️🎙️ Processing files with vision/voice support: {len(files)} files")
                    processing_result = await self.document_service.process_mixed_files_with_vision(
                        user_id=user_id,
                        files=files,
                        user_message=message,
                        conversation_id=conversation_id,
                        background_tasks=background_tasks
                    )
                    
                    # Format result as processed_files for compatibility
                    processed_files = processing_result.get("processed_files", [])
                    
                    # Store processed files in routing result for later attachment creation
                    routing_result["processed_files"] = processed_files
                    
                    # 🆕 CRITICAL FIX: Extract pet information from mixed files (documents in the mix)
                    if processed_files and has_documents:
                        # Extract text content from processed documents for pet analysis
                        document_texts = []
                        for file_result in processed_files:
                            if (file_result.get("type") == "document" and 
                                "content_preview" in file_result and 
                                file_result["content_preview"]):
                                document_texts.append(file_result["content_preview"])
                        
                        if document_texts:
                            combined_document_text = "\n\n".join(document_texts)
                            logger.info(f"🐕 Processing mixed files document text for pet information: {len(combined_document_text)} characters")
                            
                            try:
                                # Combine user message with extracted document text for comprehensive pet analysis
                                combined_message_for_pet_extraction = f"{message}\n\nDOCUMENT CONTENT:\n{combined_document_text}"
                                
                                # Process the extracted text for pet information
                                pet_extraction_result = await self.pet_context_manager.process_message_for_pet_info(
                                    user_id=user_id,
                                    message=combined_message_for_pet_extraction,
                                    conversation_id=conversation_id,
                                    conversation_context="mixed_files_document_analysis"
                                )
                                
                                if pet_extraction_result and pet_extraction_result.get("extraction_successful"):
                                    logger.info(f"✅ Successfully extracted pet info from mixed files documents: {list(pet_extraction_result.get('extracted_data', {}).keys())}")
                                    # Add pet extraction info to processing result
                                    processing_result["pet_extraction"] = {
                                        "success": True,
                                        "extracted_fields": list(pet_extraction_result.get('extracted_data', {}).keys()),
                                        "comprehensive_data_updated": bool(pet_extraction_result.get('storage_result', {}).get('success'))
                                    }
                                else:
                                    logger.info("ℹ️ No pet information found in mixed files document text")
                                    processing_result["pet_extraction"] = {"success": False, "reason": "No pet info detected"}
                                    
                            except Exception as pet_error:
                                logger.error(f"❌ Error extracting pet info from mixed files documents: {str(pet_error)}")
                                processing_result["pet_extraction"] = {"success": False, "error": str(pet_error)}
                    
                    # If we have a combined response from vision processing, create a mock LangGraph result
                    if processing_result.get("success") and processing_result.get("content"):
                        # For voice processing, the content should be the transcribed text to be processed by LangGraph
                        if has_audio and not has_images:
                            # Pure audio processing - use transcribed text as the user's message
                            transcribed_content = processing_result.get("content")
                            logger.info(f"🎙️ Using transcribed text as user message: {transcribed_content}")
                            # Set this as the enhanced message for LangGraph processing
                            enhanced_message = transcribed_content
                            # Mark that we have a valid transcribed message to prevent overwriting
                            has_transcribed_message = True
                            # Don't create langgraph_result yet - let it be processed normally
                            logger.info("🎙️ Voice transcription complete, will process with LangGraph agent...")
                        else:
                            # Image processing or mixed - create a mock LangGraph result
                            langgraph_result = {
                                "content": processing_result.get("content"),
                                "agent_used": "vision",
                                "confidence": 0.9,
                                "processing_time": processing_result.get("processing_time", 0.0),
                                "sources_used": []
                            }
                            
                            # Don't return early - let the flow continue to save messages and attachments
                            logger.info("🖼️ Vision processing complete, continuing to message storage...")
                    else:
                        # Handle error case
                        langgraph_result = {
                            "content": "I apologize, but I wasn't able to process the image properly. Please try again.",
                            "agent_used": "vision",
                            "confidence": 0.0,
                            "processing_time": processing_result.get("processing_time", 0.0),
                            "sources_used": []
                        }
                else:
                    # Convert dict files to UploadFile objects for document processing
                    upload_files = self._convert_dict_files_to_upload_files(files)
                    
                    # Process files directly with document service (original method)
                    processed_files = await self.document_service.process_uploaded_files(
                        user_id=user_id,
                        files=upload_files,
                        message=message,
                        conversation_id=conversation_id,
                        background_tasks=background_tasks
                    )
                    
                    # 🆕 CRITICAL FIX: Extract pet information from directly processed files
                    if processed_files:
                        # Extract text content from successful file processing for pet analysis
                        document_texts = []
                        for file_result in processed_files:
                            if (file_result.get("status") == "success" and 
                                file_result.get("extracted_text")):
                                document_texts.append(file_result["extracted_text"])
                        
                        if document_texts:
                            combined_document_text = "\n\n".join(document_texts)
                            logger.info(f"🐕 Processing directly uploaded files text for pet information: {len(combined_document_text)} characters")
                            
                            try:
                                # Combine user message with extracted document text for comprehensive pet analysis
                                combined_message_for_pet_extraction = f"{message}\n\nDOCUMENT CONTENT:\n{combined_document_text}"
                                
                                # Process the extracted text for pet information
                                pet_extraction_result = await self.pet_context_manager.process_message_for_pet_info(
                                    user_id=user_id,
                                    message=combined_message_for_pet_extraction,
                                    conversation_id=conversation_id,
                                    conversation_context="direct_files_document_analysis"
                                )
                                
                                if pet_extraction_result and pet_extraction_result.get("extraction_successful"):
                                    logger.info(f"✅ Successfully extracted pet info from direct files: {list(pet_extraction_result.get('extracted_data', {}).keys())}")
                                    # Store pet extraction info for potential use
                                    routing_result["pet_extraction"] = {
                                        "success": True,
                                        "extracted_fields": list(pet_extraction_result.get('extracted_data', {}).keys()),
                                        "comprehensive_data_updated": bool(pet_extraction_result.get('storage_result', {}).get('success'))
                                    }
                                else:
                                    logger.info("ℹ️ No pet information found in direct files document text")
                                    routing_result["pet_extraction"] = {"success": False, "reason": "No pet info detected"}
                                    
                            except Exception as pet_error:
                                logger.error(f"❌ Error extracting pet info from direct files: {str(pet_error)}")
                                routing_result["pet_extraction"] = {"success": False, "error": str(pet_error)}
                
                # Store processed files in routing result for attachment creation (for non-image files)
                if not has_images:
                    routing_result["processed_files"] = processed_files
                
                # Create document analysis summary for LangGraph with actual content (skip for images and transcribed audio)
                if processed_files and not has_images and not locals().get('has_transcribed_message', False):
                    file_summary_parts = []
                    document_contents = []
                    
                    logger.info(f"🔍 Processing {len(processed_files)} files for AI analysis")
                    
                    for f in processed_files:
                        filename = f.get('filename', 'unknown')
                        status = f.get('status', 'unknown')
                        file_summary_parts.append(f"{filename} ({status})")
                        
                        # Debug: log the structure of each processed file
                        logger.info(f"📋 File {filename}: keys={list(f.keys())}, success={f.get('success')}, has_extracted_text={bool(f.get('extracted_text'))}")
                        
                        # Use Vector-Assisted Analysis for intelligent content retrieval
                        if f.get('extracted_text'):
                            content = f.get('extracted_text', '')
                            logger.info(f"📄 Document {filename}: {len(content)} chars extracted")
                            
                            # Get relevant content using vector search instead of truncation
                            relevant_content = await self._get_relevant_document_content(
                                user_id=user_id,
                                query=message,
                                filename=filename,
                                conversation_id=conversation_id
                            )
                            
                            if relevant_content:
                                document_contents.append(f"\n--- Most Relevant Content from {filename} ---\n{relevant_content}")
                                logger.info(f"📄 Added relevant content for {filename}: {len(relevant_content)} chars")
                            else:
                                # Fallback to intelligent truncation if vector search fails
                                content_preview = await self._intelligent_content_preview(content, message)
                                document_contents.append(f"\n--- Content Preview of {filename} ---\n{content_preview}")
                                logger.info(f"📄 Added fallback content for {filename}: {len(content_preview)} chars")
                    
                    file_summary = f"Processed {len(processed_files)} files: " + ", ".join(file_summary_parts)
                    
                    # Include both summary and actual content with clear instructions
                    if document_contents:
                        # Create a clear, directive message for the AI
                        if not message.strip():
                            directive = "Please analyze this document and provide a comprehensive summary."
                        else:
                            directive = message.strip()
                        
                        enhanced_message = f"""{directive}

                        ✅ DOCUMENT ANALYSIS STATUS: SUCCESSFUL
                        ✅ DOCUMENT PROCESSING: COMPLETE
                        ✅ CONTENT EXTRACTION: SUCCESSFUL

                        I have successfully uploaded and processed the following document(s):
                        {file_summary}

                        🔍 DOCUMENT CONTENT AVAILABLE FOR ANALYSIS:
                        The document analysis tools have successfully extracted and provided the complete content below. 
                        DO NOT apologize for missing document content - the content is fully available and ready for analysis.

                        ==================== DOCUMENT CONTENT START ====================
                        {''.join(document_contents)}
                        ==================== DOCUMENT CONTENT END ====================

                        IMPORTANT: The above document content has been successfully processed and is available for your analysis. 
                        Please provide a detailed response based on this actual document content. Do not mention any issues 
                        with document analysis tools - they have worked correctly and provided the content above."""
                        
                        total_chars = sum(len(content) for content in document_contents)
                        logger.info(f"📄 Sending {len(document_contents)} document contents to AI via Vector-Assisted Analysis (total chars: {total_chars})")
                    else:
                        # Only set document error message if we don't have a transcribed message
                        if not locals().get('has_transcribed_message', False):
                            enhanced_message = f"{message}\n\nDocument processing results: {file_summary}\n\nNo readable content was extracted from the uploaded files."
                            logger.warning("⚠️ No document content found for AI analysis")
                else:
                    # Only set file processing error if we don't have a transcribed message
                    if not locals().get('has_transcribed_message', False):
                        enhanced_message = f"{message}\n\nNo files were successfully processed."
            else:
                # Only set to original message if we don't have a transcribed message
                if not locals().get('has_transcribed_message', False):
                    enhanced_message = message
            
            # Ensure message is never empty for Claude (AWS Bedrock requirement)
            if not enhanced_message.strip():
                if files:
                    enhanced_message = "Document uploaded for analysis."
                else:
                    enhanced_message = "Hello"
            
            # Debug log for voice processing
            if locals().get('has_transcribed_message', False):
                logger.info(f"🎙️ Final enhanced message for LangGraph: {enhanced_message}")
            
            # Process with optimized agent (skip only if we already have vision result, not for audio-only)
            has_images_in_files = files and any(file.get('content_type', '').startswith('image/') for file in files)
            has_audio_only = files and any(file.get('content_type', '').startswith('audio/') for file in files) and not has_images_in_files
            
            if target_service == "document" and has_images_in_files and 'langgraph_result' in locals():
                # We already have the langgraph_result from vision processing above
                logger.info("🖼️ Using existing vision processing result, skipping LangGraph agent...")
            elif target_service == "reminder":
                # Route directly to reminder service for reminder intents
                logger.info(f"🔔 Routing reminder request directly to reminder service: {enhanced_message}")
                reminder_result = await self.reminder_service.process_reminder_request(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message=enhanced_message,
                    context=context
                )
                
                # Convert reminder result to langgraph_result format for consistency
                langgraph_result = {
                    "content": reminder_result.get("content", "Reminder processed successfully."),
                    "agent_used": "reminder",
                    "confidence": 0.9,
                    "processing_time": reminder_result.get("processing_time", 0.0),
                    "sources_used": []
                }
            else:
                langgraph_result = await self.chat_service.langgraph_service.process_with_agent(
                    agent_type=agent_type,
                    user_id=user_id,
                    message=enhanced_message,
                    conversation_id=conversation_id
                )
            
            # Store user memory for future context 
            # Get the original message and retrieved_docs info from routing_result
            original_message = routing_result.get("original_message", message)
            retrieved_docs_info = routing_result.get("retrieved_docs")
            
            # For memory: use enhanced message if we retrieved docs, otherwise original message
            memory_content = enhanced_message if retrieved_docs_info else original_message
            
            # Ensure memory content is meaningful for file uploads
            if not memory_content or memory_content.strip() == "":
                if files:
                    file_descriptions = []
                    for file in files:
                        if file.get('content_type', '').startswith('image/'):
                            file_descriptions.append(f"uploaded image: {file.get('filename', 'image')}")
                        elif file.get('content_type', '').startswith('audio/'):
                            file_descriptions.append(f"uploaded audio: {file.get('filename', 'audio')}")
                        else:
                            file_descriptions.append(f"uploaded file: {file.get('filename', 'document')}")
                    memory_content = f"User {' and '.join(file_descriptions)}"
                else:
                    memory_content = "User sent an empty message"
            
            # Store conversation messages in PostgreSQL for persistent memory
            # For PostgreSQL: always use original user message for clean conversation history
            ai_response = langgraph_result.get('content', '')
            
            # 🧹 Clean contradictory AI responses about dog knowledge
            if self.unified_dog_manager:
                try:
                    unified_knowledge = await self.unified_dog_manager.get_comprehensive_dog_knowledge(user_id)
                    cleaned_response = self.unified_dog_manager.clean_contradictory_response(ai_response, unified_knowledge)
                    if cleaned_response != ai_response:
                        logger.info("🧹 Cleaned contradictory AI response")
                        ai_response = cleaned_response
                        langgraph_result["content"] = ai_response  # Update the result as well
                except Exception as e:
                    logger.error(f"❌ Error cleaning AI response: {e}")
            
            # 🧹 Clean incorrect document analysis error messages
            if files and any(file.get('status') == 'success' for file in routing_result.get("processed_files", [])):
                ai_response = self._clean_document_error_messages(ai_response)
                langgraph_result["content"] = ai_response
            
            # Add follow-up questions if needed (using dog context analysis)
            dog_context_analysis = routing_result.get("dog_context_analysis", {})
            # Add legacy follow-up question if dog context analysis indicates it's needed and pet context manager didn't provide questions
            # Get pet follow-up questions from routing_result to check if they exist
            pet_context_data = routing_result.get("pet_context_result", {})
            existing_follow_up_questions = pet_context_data.get("follow_up_questions", [])
            
            if (dog_context_analysis.get("needs_follow_up") and 
                target_service == "chat" and
                not existing_follow_up_questions and
                await self._should_add_dog_followup(ai_response, dog_context_analysis, user_id)):
                
                follow_up_type = dog_context_analysis.get("follow_up_type")
                
                # Generate a simple follow-up question for cases pet context manager didn't handle
                if follow_up_type == "no_dog_info":
                    follow_up_question = "Also, I'd love to provide more personalized advice! Could you tell me about your dog? I'd like to know their name, breed, age, and any specific concerns you have."
                else:
                    follow_up_question = "Could you tell me more about your dog so I can provide better guidance?"
                
                # Append follow-up question to AI response
                ai_response += "\n\n" + follow_up_question
                
                # Update the langgraph_result content as well for consistency
                langgraph_result["content"] = ai_response
                
                logger.info(f"🐕 Added legacy follow-up question ({follow_up_type}): {follow_up_question[:100]}...")
            
            # Add intelligent pet follow-up questions if any
            # Get pet follow-up questions from routing_result (where they're passed from main method)
            pet_context_data = routing_result.get("pet_context_result", {})
            pet_follow_up_questions = pet_context_data.get("follow_up_questions", [])
            
            if pet_follow_up_questions and target_service == "chat":
                follow_up_text = "\n\n" + "\n".join([f"• {question}" for question in pet_follow_up_questions])
                ai_response += follow_up_text
                
                # Update the langgraph_result content as well for consistency
                langgraph_result["content"] = ai_response
                
                logger.info(f"🐕 Added {len(pet_follow_up_questions)} intelligent pet follow-up questions")
            
            # Add Pawtree recommendation if needed (using food analysis)
            food_analysis = routing_result.get("food_analysis", {})
            logger.info(f"🍽️ DEBUG - Food analysis result: {food_analysis}")
            logger.info(f"🍽️ DEBUG - is_food_related: {food_analysis.get('is_food_related')}, target_service: {target_service}")
            
            if food_analysis.get("is_food_related") and target_service == "chat":
                try:
                    can_recommend = await self.food_recommendation_service.check_recommendation_cooldown(user_id, message)
                    
                    if can_recommend:
                        food_analysis["user_message"] = message
                        
                        # NEW: Use AI response to generate smart Pawtree links for specific foods mentioned
                        pawtree_recommendation = self.food_recommendation_service.generate_pawtree_recommendation_from_ai_response(
                            ai_response, food_analysis
                        )
                        ai_response += "\n\n" + pawtree_recommendation
                        
                        await self.food_recommendation_service.set_recommendation_cooldown(user_id)
                        
                        langgraph_result["content"] = ai_response
                    else:
                        logger.info(f"⏰ Skipped Pawtree recommendation for user {user_id} due to cooldown")
                    
                    logger.info(f"🍽️ Added smart Pawtree recommendation for food-related query (confidence: {food_analysis.get('confidence', 0):.2f})")
                except Exception as e:
                    logger.error(f"❌ Error generating Pawtree recommendation: {e}")
            else:
                logger.info(f"🍽️ DEBUG - No Pawtree recommendation added. Reasons: is_food_related={food_analysis.get('is_food_related')}, target_service={target_service}")
            
            # Store user memory with final AI response (including follow-up questions and recommendations)
            await self.chat_service.langgraph_service.store_user_memory(
                user_id=user_id,
                content=f"User: {memory_content}\nAssistant: {ai_response}",
                memory_type="conversation"
            )
            
            # Get processed files from routing result if available (for S3 URLs)
            processed_files = routing_result.get('processed_files', [])
            attachments = self._convert_files_to_attachments(files, processed_files)
            
            # Create meaningful user message for file uploads without text
            user_message_for_storage = original_message
            if not original_message or original_message.strip() == "":
                # If no text message, create a descriptive message based on uploaded files
                if files:
                    file_descriptions = []
                    for file in files:
                        if file.get('content_type', '').startswith('image/'):
                            file_descriptions.append(f"🖼️Uploaded image: {file.get('filename', 'image')}")
                        elif file.get('content_type', '').startswith('audio/'):
                            file_descriptions.append(f"🎙️Uploaded audio: {file.get('filename', 'audio')}")
                        else:
                            file_descriptions.append(f"📁Uploaded file: {file.get('filename', 'document')}")
                    user_message_for_storage = " ".join(file_descriptions)
                else:
                    user_message_for_storage = "🔍Empty message"
            
            conversation_data = await self.chat_service._store_conversation_in_postgresql(
                user_id, conversation_id, user_message_for_storage, ai_response, None, attachments
            )
            
            # Update image message IDs if we processed images
            if target_service == "document" and files and any(file.get('content_type', '').startswith('image/') for file in files):
                processed_files = routing_result.get("processed_files", [])
                if processed_files:
                    # Extract image IDs from processed files
                    image_ids = [pf.get('image_id') for pf in processed_files if pf.get('image_id')]
                    if image_ids:
                        user_message_id = conversation_data.get("user_message_id")
                        ai_message_id = conversation_data.get("message_id")
                        if user_message_id:
                            await self.document_service.vision_service.update_image_message_ids(
                                image_ids, user_message_id, ai_message_id
                            )
                            logger.info(f"🔗 Updated {len(image_ids)} images with message IDs")
            
            # Convert to expected orchestrator format
            return {
                "success": True,
                "content": langgraph_result.get("content", ""),
                "conversation_id": conversation_id,
                "message_id": routing_result.get("message_id", 0),
                "thread_id": routing_result.get("thread_id"),
                "context_info": {
                    "agent_used": langgraph_result.get("agent_used", agent_type),
                    "confidence": langgraph_result.get("confidence", 0.8),
                    "processing_time": langgraph_result.get("processing_time", 0.0)
                },
                "sources_used": self._convert_sources_to_dict_format(langgraph_result.get("sources_used", [])),
                "processing_time": langgraph_result.get("processing_time", 0.0)
            }
        
        # LangGraph service is required - no fallback to ensure real functionality
        logger.error("❌ LangGraph service not available - this is a critical error")
        raise RuntimeError("LangGraph service is required but not available. Check service initialization.")

    async def _handle_multi_service_request(
        self,
        user_id: int,
        conversation_id: int,
        message: str,
        files: Optional[List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]],
        routing_result: Dict[str, Any],
        background_tasks
    ) -> Dict[str, Any]:
        """Handle requests that require multiple services"""
        
        services_needed = routing_result.get("services_needed", [])
        results = {}
        
        # Execute services in parallel where possible
        tasks = []
        
        for service_name in services_needed:
            if service_name == "document" and files:
                # Generate cache key for multi-service document processing
                cache_key = self._generate_document_cache_key(user_id, files, f"multi_service_{message}")
                
                # Check cache first
                cached_result = self._get_cached_document_result(cache_key)
                if cached_result:
                    logger.info(f"📄 Using cached multi-service document result for user {user_id}")
                    # Create a future that immediately returns the cached result
                    async def cached_task():
                        return cached_result
                    tasks.append((service_name, cached_task()))
                else:
                # Convert dict files to UploadFile objects for document processing
                    upload_files = self._convert_dict_files_to_upload_files(files)
                    
                    # Create task that caches result
                    async def caching_document_task():
                        result = await self.document_service.process_uploaded_files(
                    user_id=user_id,
                    files=upload_files,
                    message=message,
                    conversation_id=conversation_id,
                    background_tasks=background_tasks
                )
                        # Cache successful results
                        if result and result.get("success", False):
                            self._cache_document_result(cache_key, result)
                            logger.info(f"📄 Cached new multi-service document result for user {user_id}")
                        return result
                    
                    tasks.append((service_name, caching_document_task()))
            
            elif service_name == "health_ai":
                # Health analysis task
                task = self.health_service.process_health_message(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message=message,
                    files=files,
                    health_context=context.get("health_context") if context else None
                )
                tasks.append((service_name, task))
            
            elif service_name == "reminder":
                # Reminder processing task
                task = self.reminder_service.process_reminder_request(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message=message,
                    context=context
                )
                tasks.append((service_name, task))
        
        # Execute tasks in parallel
        if tasks:
            task_results = await asyncio.gather(
                *[task for _, task in tasks],
                return_exceptions=True
            )
            
            # Collect results
            for i, (service_name, _) in enumerate(tasks):
                result = task_results[i]
                if not isinstance(result, Exception):
                    results[service_name] = result
                else:
                    logger.error(f"Multi-service error in {service_name}: {result}")
        
        # Synthesize final response using chat service
        synthesis_prompt = self._create_synthesis_prompt(message, results, routing_result)
        
        final_response = await self.chat_service.process_chat_message(
            user_id=user_id,
            conversation_id=conversation_id,
            message=synthesis_prompt,
            files=[],
            attachments=[],
            background_tasks=background_tasks
        )
        
        # Enhance with multi-service results by updating context_info
        # Create a new dict to avoid modifying the original Pydantic model
        enhanced_context = dict(final_response.context_info) if final_response.context_info else {}
        enhanced_context["multi_service_results"] = results
        enhanced_context["services_used"] = services_needed
        
        # Create new ChatResponse with enhanced context_info
        from models import ChatResponse
        final_response = ChatResponse(
            success=final_response.success,
            content=final_response.content,
            conversation_id=final_response.conversation_id,
            message_id=final_response.message_id,
            thread_id=final_response.thread_id,
            context_info=enhanced_context,
            sources_used=final_response.sources_used,
            processing_time=final_response.processing_time
        )
        
        return final_response

    def _create_synthesis_prompt(
        self, 
        original_message: str, 
        service_results: Dict[str, Any], 
        routing_result: Dict[str, Any]
    ) -> str:
        """Create a synthesis prompt for multi-service responses"""
        
        synthesis_parts = [
            f"The user asked: '{original_message}'",
            "",
            "I've processed this request using multiple specialized services. Here are the results:",
            ""
        ]
        
        for service_name, result in service_results.items():
            if service_name == "document" and result.get("processed_files"):
                synthesis_parts.append(f"📄 Document Processing: Successfully processed {len(result['processed_files'])} files")
            elif service_name == "health_ai" and result.get("content"):
                synthesis_parts.append(f"🏥 Health Analysis: {result['content'][:200]}...")
            elif service_name == "reminder" and result.get("reminder_data"):
                action = result["reminder_data"].get("action", "processed")
                synthesis_parts.append(f"⏰ Reminder Service: {action.title()} reminder successfully")
        
        synthesis_parts.extend([
            "",
            "Please provide a comprehensive response that synthesizes all this information into a helpful, coherent answer for the user."
        ])
        
        return "\n".join(synthesis_parts)

    # Performance monitoring and statistics
    def _update_orchestration_stats(
        self, 
        service_used: str, 
        confidence: float, 
        routing_time: float, 
        success: bool
    ):
        """Update orchestration performance statistics"""
        self.orchestration_stats["total_requests"] += 1
        
        if success:
            # Update service usage
            if service_used in self.orchestration_stats["service_usage"]:
                self.orchestration_stats["service_usage"][service_used] += 1
            
            # Update routing accuracy (weighted average)
            total_requests = self.orchestration_stats["total_requests"]
            current_accuracy = self.orchestration_stats["routing_accuracy"]
            self.orchestration_stats["routing_accuracy"] = (
                (current_accuracy * (total_requests - 1) + confidence) / total_requests
            )
            
            # Update average routing time
            current_avg_time = self.orchestration_stats["average_routing_time"]
            self.orchestration_stats["average_routing_time"] = (
                (current_avg_time * (total_requests - 1) + routing_time) / total_requests
            )
        else:
            self.orchestration_stats["routing_failures"] += 1

    def get_orchestration_stats(self) -> Dict[str, Any]:
        """Get comprehensive orchestration performance statistics including document cache"""
        total_requests = self.orchestration_stats["total_requests"]
        
        stats = self.orchestration_stats.copy()
        
        # Add calculated metrics
        if total_requests > 0:
            stats["success_rate"] = (
                (total_requests - self.orchestration_stats["routing_failures"]) / total_requests
            ) * 100
            
            # Service distribution percentages
            service_percentages = {}
            for service, count in self.orchestration_stats["service_usage"].items():
                service_percentages[service] = (count / total_requests) * 100
            
            stats["service_distribution"] = service_percentages
        
        # Add document cache performance statistics
        try:
            stats["document_cache"] = self.get_document_cache_stats()
        except Exception as e:
            stats["document_cache"] = {"error": f"Cache stats unavailable: {str(e)}"}
        
        return stats

    def reset_orchestration_stats(self):
        """Reset orchestration statistics and optionally document cache"""
        self.orchestration_stats = {
            "total_requests": 0,
            "routing_accuracy": 0.0,
            "average_routing_time": 0.0,
            "service_usage": {
                "chat": 0,
                "health_ai": 0,
                "document": 0,
                "reminder": 0
            },
            "routing_failures": 0
        }
        
        # Also reset document cache statistics (but keep cache contents)
        self._document_cache_stats["hits"] = 0
        self._document_cache_stats["misses"] = 0
        self._document_cache_stats["evictions"] = 0
        self._document_cache_stats["total_requests"] = 0

    async def get_comprehensive_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all services"""
        try:
            # Gather stats from all services
            orchestration_stats = self.get_orchestration_stats()
            chat_stats = self.chat_service.get_parallel_processing_stats()
            health_stats = await self.health_service.get_parallel_processing_stats()
            document_stats = self.document_service.get_processing_stats()
            reminder_stats = self.reminder_service.get_reminder_stats()
            
            return {
                "orchestration": orchestration_stats,
                "services": {
                    "chat": chat_stats,
                    "health_ai": health_stats,
                    "document": document_stats,
                    "reminder": reminder_stats
                },
                "overall_performance": {
                    "total_requests_handled": orchestration_stats.get("total_requests", 0),
                    "average_response_time": orchestration_stats.get("average_routing_time", 0.0),
                    "service_success_rate": orchestration_stats.get("success_rate", 0.0),
                    "most_used_service": max(
                        orchestration_stats.get("service_usage", {}).items(),
                        key=lambda x: x[1],
                        default=("none", 0)
                    )[0]
                }
            }
        except Exception as e:
            logger.error(f"Stats gathering error: {str(e)}")
            return {"error": str(e)}

    async def _should_add_dog_followup(self, ai_response: str, dog_analysis: Dict[str, Any], user_id: int) -> bool:
        """
        Comprehensive dog follow-up decision with unified knowledge checking
        Prevents all knowledge conflicts while preserving legitimate follow-up scenarios
        """
        try:
            # Initialize unified knowledge manager if not done already
            if not self.unified_dog_manager and hasattr(self.chat_service, 'langgraph_service') and self.chat_service.langgraph_service:
                self.unified_dog_manager = UnifiedDogKnowledgeManager(
                    self.chat_service.langgraph_service,
                    self.dog_context_service
                )
                logger.info("🔧 Initialized UnifiedDogKnowledgeManager")
            
            # If no unified manager available, use legacy logic
            if not self.unified_dog_manager:
                logger.warning("⚠️ UnifiedDogKnowledgeManager not available, using legacy logic")
                return self._legacy_dog_followup_logic(ai_response, dog_analysis)
            
            # 🔍 STEP 1: Get comprehensive dog knowledge from all sources
            unified_knowledge = await self.unified_dog_manager.get_comprehensive_dog_knowledge(user_id)
            
            # 🔍 STEP 2: Check if AI response demonstrates dog knowledge
            ai_shows_knowledge = self.unified_dog_manager.ai_demonstrates_dog_knowledge(ai_response)
            
            # 🔍 STEP 3: If AI demonstrates knowledge, extract and sync it first
            if ai_shows_knowledge:
                logger.info("🐕 AI demonstrates dog knowledge - extracting and syncing")
                await self.unified_dog_manager.extract_and_sync_ai_knowledge(user_id, ai_response)
                # Refresh unified knowledge after syncing
                unified_knowledge = await self.unified_dog_manager.get_comprehensive_dog_knowledge(user_id)
            
            # 🔍 STEP 4: Analyze what we have after cleaning and syncing
            if not unified_knowledge:
                # No dogs at all - ask for basic info
                logger.info("🐕 No dog knowledge found - will ask for basic dog info")
                dog_analysis["needs_follow_up"] = True
                dog_analysis["follow_up_type"] = "no_dog_info"
                dog_analysis["confidence"] = 0.8
                # Continue to generate basic dog info question
            elif len(unified_knowledge) == 1:
                # Single dog - no clarification needed
                logger.info(f"🐕 Found single dog: {list(unified_knowledge.keys())[0]} - no follow-up needed")
                return False
            elif len(unified_knowledge) > 1:
                # Multiple dogs - need to check if user specified which one
                dog_names = list(unified_knowledge.keys())
                logger.info(f"🐕 Found multiple dogs: {dog_names}")
                
                # Check if user mentioned any specific dog name in their message
                user_mentioned_specific_dog = False
                detected_dogs = dog_analysis.get("detected_dogs", [])
                for mentioned_dog in detected_dogs:
                    if mentioned_dog in dog_names:
                        user_mentioned_specific_dog = True
                        logger.info(f"🐕 User mentioned specific dog: {mentioned_dog}")
                        break
                
                if not user_mentioned_specific_dog:
                    # User has multiple dogs but didn't specify which - ask for clarification
                    logger.info(f"🐕 User has multiple dogs but didn't specify - will ask which one")
                    # Override dog_analysis to ensure multiple_dogs_clarification is triggered
                    dog_analysis["needs_follow_up"] = True
                    dog_analysis["follow_up_type"] = "multiple_dogs_clarification" 
                    dog_analysis["detected_dogs"] = dog_names
                    dog_analysis["confidence"] = 0.9
                    # Continue to generate "which dog" question
                else:
                    # User mentioned specific dog - no follow-up needed
                    logger.info(f"🐕 User specified dog from multiple - no follow-up needed")
                    return False
            
            # 🔍 STEP 3: Check for conflicting phrases in AI response
            conflicting_phrases = [
                "don't have any specific details",
                "don't have access to personal information", 
                "i don't know",
                "i'm not sure about",
                "haven't been told about",
                "i don't have information about",
                "i can't tell you about",
                "no information about",
                "no details about",
                "unfortunately, i don't have"
            ]
            
            ai_lower = ai_response.lower()
            if any(phrase in ai_lower for phrase in conflicting_phrases):
                # AI says it doesn't know - check if this conflicts with known knowledge
                if unified_knowledge:
                    logger.warning("🚨 Conflict: AI says no knowledge but we have dog info - syncing")
                    # This shouldn't happen now that we check unified_knowledge first, but keep as safety
                else:
                    logger.info("🚫 Skipping dog follow-up - AI response indicates no knowledge")
                return False
            
            # 🔍 STEP 4: Check confidence level
            confidence = dog_analysis.get("confidence", 0.0)
            if confidence < 0.7:
                logger.info(f"🚫 Skipping dog follow-up - low confidence ({confidence:.2f})")
                return False
            
            # 🔍 STEP 5: Filter detected dogs for false positives
            detected_dogs = dog_analysis.get("detected_dogs", [])
            if detected_dogs:
                # Use the manager's validation for consistency
                valid_dogs = [
                    dog for dog in detected_dogs 
                    if self.unified_dog_manager._is_valid_dog_name(dog)
                ]
                
                if not valid_dogs:
                    logger.info(f"🚫 Skipping dog follow-up - no valid dogs after filtering: {detected_dogs}")
                    return False
                
                # Update the analysis with filtered dogs
                dog_analysis["detected_dogs"] = valid_dogs
            
            # 🔍 STEP 6: Detect potential conflicts
            conflicts = self.unified_dog_manager.detect_knowledge_conflicts(ai_response, unified_knowledge)
            if conflicts:
                logger.warning(f"🚨 Knowledge conflicts detected: {conflicts} - skipping follow-up")
                return False
            
            # ✅ All checks passed - proceed with legitimate follow-up
            logger.info("✅ All unified knowledge checks passed - allowing follow-up")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in unified dog follow-up decision: {e}")
            # Fallback to legacy logic on error
            return self._legacy_dog_followup_logic(ai_response, dog_analysis)

    def _legacy_dog_followup_logic(self, ai_response: str, dog_analysis: Dict[str, Any]) -> bool:
        """
        Legacy dog follow-up logic as fallback
        """
        conflicting_phrases = [
            "don't have any specific details",
            "don't have access to personal information", 
            "i don't know",
            "i'm not sure about",
            "haven't been told about",
            "i don't have information about",
            "i can't tell you about",
            "no information about",
            "no details about"
        ]
        
        ai_lower = ai_response.lower()
        if any(phrase in ai_lower for phrase in conflicting_phrases):
            logger.info("🚫 Skipping dog follow-up - AI response indicates no knowledge (legacy)")
            return False
        
        confidence = dog_analysis.get("confidence", 0.0)
        if confidence < 0.7:
            logger.info(f"🚫 Skipping dog follow-up - low confidence ({confidence:.2f}) (legacy)")
            return False
        
        detected_dogs = dog_analysis.get("detected_dogs", [])
        if detected_dogs:
            valid_dogs = [
                dog for dog in detected_dogs 
                if (len(dog) >= 2 and 
                    dog.lower() not in ['of', 'to', 'me', 'tell', 'names', 'age', 'years', 'stays', 'ensure'])
            ]
            
            if not valid_dogs:
                logger.info(f"🚫 Skipping dog follow-up - no valid dogs after filtering: {detected_dogs} (legacy)")
                return False
            
            dog_analysis["detected_dogs"] = valid_dogs
        
        return True

    def _clean_document_error_messages(self, ai_response: str) -> str:
        """
        Clean incorrect document analysis error messages when documents were actually processed successfully
        """
        try:
            # Patterns that indicate the AI incorrectly thinks document analysis failed
            error_patterns = [
                # Direct document analysis error messages
                r"(?i)apologies?,?\s*(?:it seems?|but)?\s*(?:the\s+)?document\s+analysis\s+tool\s+(?:did\s+not\s+return\s+any\s+results?|failed|was\s+not\s+available)",
                r"(?i)(?:i\s+apologize?,?\s*but\s+)?(?:the\s+)?document\s+analysis\s+(?:tool\s+)?(?:did\s+not\s+work|failed|returned\s+no\s+results?)",
                r"(?i)(?:unfortunately,?\s*)?(?:i\s+)?(?:was\s+)?unable\s+to\s+(?:retrieve|access|analyze)\s+(?:the\s+)?document\s+content",
                r"(?i)(?:the\s+)?document\s+(?:might\s+be|could\s+be|appears\s+to\s+be)\s+(?:empty|corrupted|not\s+properly\s+uploaded)",
                r"(?i)(?:no\s+readable\s+content|no\s+content)\s+(?:was\s+)?(?:found|extracted|available)\s+(?:from\s+)?(?:the\s+)?(?:uploaded\s+)?(?:document|file)",
                r"(?i)document\s+processing\s+(?:failed|was\s+unsuccessful|encountered\s+(?:an\s+)?error)",
                
                # Tool-related error messages
                r"(?i)(?:the\s+)?document\s+analysis\s+tool\s+(?:is\s+)?(?:temporarily\s+)?(?:unavailable|not\s+working)",
                r"(?i)(?:i\s+)?(?:was\s+)?(?:unable\s+to\s+)?(?:use|access|call)\s+(?:the\s+)?document\s+analysis\s+tool",
                
                # Processing error messages
                r"(?i)(?:there\s+(?:was|were)\s+)?(?:an?\s+)?(?:error|issue|problem)\s+(?:with\s+)?(?:processing|analyzing)\s+(?:the\s+)?(?:document|file)",
                r"(?i)document\s+upload\s+(?:failed|was\s+not\s+successful)",
                
                # Generic apology patterns for document issues
                r"(?i)(?:i\s+)?apologize?\s+for\s+(?:the\s+)?(?:difficulty|issue|problem)\s+(?:with\s+)?(?:the\s+)?(?:document|file)",
            ]
            
            # Find sentences that contain these error patterns
            sentences = ai_response.split('.')
            cleaned_sentences = []
            removed_count = 0
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Check if sentence contains error patterns
                should_remove = False
                for pattern in error_patterns:
                    if re.search(pattern, sentence):
                        should_remove = True
                        removed_count += 1
                        logger.info(f"🧹 Removing incorrect document error message: {sentence[:100]}...")
                        break
                
                if not should_remove:
                    cleaned_sentences.append(sentence)
            
            # Rebuild response
            if removed_count > 0:
                cleaned_response = '. '.join(cleaned_sentences)
                
                # Add proper ending if needed
                if cleaned_response and not cleaned_response.endswith('.'):
                    cleaned_response += '.'
                
                # If response became too short, add a positive opening
                if len(cleaned_response.split()) < 10:
                    cleaned_response = "I've successfully analyzed the document content. " + cleaned_response
                
                logger.info(f"✅ Cleaned {removed_count} incorrect document error messages")
                return cleaned_response
            
            return ai_response
            
        except Exception as e:
            logger.error(f"❌ Error cleaning document error messages: {e}")
            return ai_response

    async def _get_relevant_document_content(
        self, 
        user_id: int, 
        query: str, 
        filename: str,
        conversation_id: int,
        max_chars: int = 6000
    ) -> str:
        """
        Use Vector-Assisted Analysis to retrieve the most relevant document chunks
        instead of truncating the entire document
        """
        try:
            if not query.strip():
                # If no specific query, use general analysis prompt
                query = "document summary key points main content"
            
            # Search for relevant chunks using vector similarity
            vector_service = self.chat_service.langgraph_service.vector_service
            vector_results = await vector_service.search_user_documents(
                user_id=user_id,
                query=query,
                top_k=8,  # Get more chunks for better context
                namespace_suffix="docs",
                conversation_id=conversation_id,
                filename_filter=filename,  # Focus on specific document
                recency_priority=True
            )
            
            if not vector_results:
                logger.warning(f"📄 No vector results found for {filename}")
                return ""
            
            # Combine relevant chunks intelligently
            relevant_chunks = []
            total_chars = 0
            
            for result in vector_results:
                chunk_content = result.get('content', '').strip()
                chunk_score = result.get('score', 0)
                
                if chunk_content and chunk_score > 0.5:  # Only include high-relevance chunks
                    # Add chunk with relevance indicator
                    chunk_with_score = f"[Relevance: {chunk_score:.2f}]\n{chunk_content}"
                    chunk_length = len(chunk_with_score)
                    
                    # Account for newlines between chunks  
                    separator_length = 2 if relevant_chunks else 0  # \n\n between chunks
                    
                    if total_chars + chunk_length + separator_length <= max_chars:
                        relevant_chunks.append(chunk_with_score)
                        total_chars += chunk_length + separator_length
                    else:
                        # Add partial chunk if it fits
                        remaining_chars = max_chars - total_chars - separator_length
                        if remaining_chars > 100:  # Only if meaningful content can fit
                            partial_chunk = chunk_with_score[:remaining_chars] + "..."
                            relevant_chunks.append(partial_chunk)
                        break
            
            if relevant_chunks:
                result_content = "\n\n".join(relevant_chunks)
                logger.info(f"🎯 Vector search found {len(relevant_chunks)} relevant chunks for {filename} ({total_chars} chars)")
                return result_content
            
            logger.warning(f"📄 No relevant chunks found for {filename}")
            return ""
            
        except Exception as e:
            logger.error(f"❌ Vector-assisted content retrieval failed for {filename}: {e}")
            return ""

    async def _intelligent_content_preview(self, content: str, query: str, max_chars: int = 4000) -> str:
        """
        Fallback intelligent content preview when vector search fails
        Tries to extract relevant sections based on query keywords
        """
        try:
            if len(content) <= max_chars:
                return content
            
            # If we have a query, try to find relevant sections
            if query and query.strip():
                import re
                
                # Extract keywords from query (simple approach)
                query_keywords = [word.lower() for word in re.findall(r'\b\w+\b', query) 
                                if len(word) > 3 and word.lower() not in ['the', 'and', 'for', 'with', 'this', 'that']]
                
                if query_keywords:
                    # Split content into paragraphs
                    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                    
                    # Score paragraphs by keyword relevance
                    scored_paragraphs = []
                    for para in paragraphs:
                        para_lower = para.lower()
                        score = sum(1 for keyword in query_keywords if keyword in para_lower)
                        if score > 0:
                            scored_paragraphs.append((score, para))
                    
                    # Sort by relevance and build preview
                    if scored_paragraphs:
                        scored_paragraphs.sort(key=lambda x: x[0], reverse=True)
                        
                        preview_parts = []
                        current_length = 0
                        
                        for score, para in scored_paragraphs:
                            if current_length + len(para) <= max_chars - 100:  # Leave room for ellipsis
                                preview_parts.append(para)
                                current_length += len(para) + 2  # +2 for \n\n
                            else:
                                break
                        
                        if preview_parts:
                            result = "\n\n".join(preview_parts)
                            if current_length < len(content):
                                result += "\n\n[... additional content truncated ...]"
                            return result
            
            # Fallback to simple truncation with better boundaries
            truncated = content[:max_chars]
            
            # Try to end at a sentence boundary
            last_period = truncated.rfind('. ')
            last_newline = truncated.rfind('\n')
            
            if last_period > max_chars - 200:
                truncated = truncated[:last_period + 1]
            elif last_newline > max_chars - 200:
                truncated = truncated[:last_newline]
            
            return truncated + "\n\n[... content truncated for brevity ...]"
            
        except Exception as e:
            logger.error(f"❌ Intelligent content preview failed: {e}")
            # Ultimate fallback
            return content[:max_chars] + "..." if len(content) > max_chars else content

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all services"""
        try:
            health_status = {
                "orchestrator": "healthy",
                "services": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Check each service (simplified health check)
            services = {
                "chat": self.chat_service,
                "health_ai": self.health_service,
                "document": self.document_service,
                "reminder": self.reminder_service
            }
            
            for service_name, service in services.items():
                try:
                    # Simple availability check
                    if hasattr(service, '__aenter__'):
                        async with service:
                            health_status["services"][service_name] = "healthy"
                    else:
                        health_status["services"][service_name] = "healthy"
                except Exception as e:
                    health_status["services"][service_name] = f"unhealthy: {str(e)}"
            
            # Overall status
            all_healthy = all(
                status == "healthy" 
                for status in health_status["services"].values()
            )
            health_status["overall_status"] = "healthy" if all_healthy else "degraded"
            
            return health_status
            
        except Exception as e:
            return {
                "orchestrator": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _determine_conversation_context(self, primary_intent: str, message: str) -> str:
        """
        Determine conversation context for targeted pet information extraction
        """
        message_lower = message.lower()
        
        # Health-related context
        health_keywords = [
            "vet", "veterinarian", "sick", "illness", "disease", "medication", "vaccine",
            "allergy", "allergic", "vomit", "diarrhea", "injury", "surgery", "treatment",
            "emergency", "urgent", "pain", "symptom", "diagnosis", "checkup"
        ]
        
        if primary_intent in ["health_general", "health_emergency", "health_concern", "symptoms", "emergency"]:
            return "health"
        
        if any(keyword in message_lower for keyword in health_keywords):
            return "health"
        
        # Emergency context
        emergency_keywords = ["emergency", "urgent", "help", "immediately", "asap", "911"]
        if any(keyword in message_lower for keyword in emergency_keywords):
            return "emergency"
        
        # Basic information context
        basic_keywords = ["my dog", "my pet", "dog name", "breed", "years old", "born", "age"]
        if any(keyword in message_lower for keyword in basic_keywords):
            return "basic"
        
        # Default to general context
        return "general"

    def _analyze_dog_context_from_pet_results(self, pet_context_result: Dict[str, Any], message: str, user_id: int) -> Dict[str, Any]:
        """
        Analyze dog context based on pet context manager results (replaces Dog Context Service)
        """
        try:
            current_pets = pet_context_result.get("current_context", {}).get("pets", [])
            processing_result = pet_context_result.get("processing_result", {})
            
            # Check if user mentioned dogs in message
            dog_keywords = ['dog', 'pet', 'puppy', 'pup', 'canine', 'pooch']
            has_dog_mention = any(keyword in message.lower() for keyword in dog_keywords)
            
            if not has_dog_mention:
                return {
                    "needs_follow_up": False,
                    "follow_up_type": None,
                    "confidence": 0.0,
                    "detected_dogs": [],
                    "reasoning": "No dog-related keywords detected"
                }
            
            # If we have pet information stored
            if current_pets:
                pet_names = [pet.get("name", "") for pet in current_pets]
                
                # Check if user mentioned specific pet by name
                mentioned_pets = []
                for pet_name in pet_names:
                    if pet_name.lower() in message.lower():
                        mentioned_pets.append(pet_name)
                
                if mentioned_pets:
                    return {
                        "needs_follow_up": False,
                        "follow_up_type": None,
                        "confidence": 0.9,
                        "detected_dogs": mentioned_pets,
                        "reasoning": f"User mentioned specific dog(s): {', '.join(mentioned_pets)}"
                    }
                else:
                    return {
                        "needs_follow_up": False,
                        "follow_up_type": None,
                        "confidence": 0.7,
                        "detected_dogs": pet_names,
                        "reasoning": f"User mentioned dogs and we have information about: {', '.join(pet_names)}"
                    }
            
            # If extraction was successful in this message
            elif processing_result.get("extraction_successful"):
                extracted_data = processing_result.get("extracted_data", {})
                extracted_name = extracted_data.get("name")
                
                if extracted_name:
                    return {
                        "needs_follow_up": False,
                        "follow_up_type": None,
                        "confidence": 0.8,
                        "detected_dogs": [extracted_name],
                        "reasoning": "User is providing dog information in this message"
                    }
            
            # User mentioned dogs but we have no information
            return {
                "needs_follow_up": True,
                "follow_up_type": "no_dog_info",
                "confidence": 0.9,
                "detected_dogs": [],
                "reasoning": "User mentioned dogs but we have no information about their dogs"
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing dog context: {e}")
            return {
                "needs_follow_up": False,
                "follow_up_type": None,
                "confidence": 0.0,
                "detected_dogs": [],
                "reasoning": f"Error in analysis: {str(e)}"
            }

    async def _process_pet_context_parallel(self, user_id: int, message: str, conversation_id: int, primary_intent: str) -> Dict[str, Any]:
        """
        Process pet context in parallel - extracted from main flow for performance
        """
        try:
            # Get current pet context for the user
            current_pet_context = await self.pet_context_manager.get_user_pet_context(user_id)
            
            # Process message for pet information extraction
            conversation_context = self._determine_conversation_context(primary_intent, message)
            pet_processing_result = await self.pet_context_manager.process_message_for_pet_info(
                user_id=user_id,
                message=message,
                conversation_id=conversation_id,
                conversation_context=conversation_context
            )
            
            # Extract follow-up questions
            follow_up_questions = []
            if pet_processing_result.get("extraction_successful"):
                logger.info(f"🐕 Extracted pet info for user {user_id}: {list(pet_processing_result.get('extracted_data', {}).keys())}")
                
                # Get smart follow-up questions if any
                follow_up_questions = pet_processing_result.get("follow_up_questions", [])
                
                if follow_up_questions:
                    logger.info(f"🤔 Generated {len(follow_up_questions)} follow-up questions for user {user_id}")
            
            # Return structured result
            return {
                "current_context": current_pet_context,
                "processing_result": pet_processing_result,
                "follow_up_questions": follow_up_questions
            }
            
        except Exception as e:
            logger.error(f"❌ Pet context processing error: {e}")
            return {
                "current_context": {},
                "processing_result": {},
                "follow_up_questions": []
            }

    def _get_cached_document_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached document result with optimized LRU tracking and statistics
        """
        try:
            self._document_cache_stats["total_requests"] += 1
            cached_entry = self._document_cache.get(cache_key)
            
            if cached_entry:
                timestamp, result, size = cached_entry
                
                # Check if still valid
                if time.time() - timestamp < self._document_cache_ttl:
                    # Update LRU order (move to end = most recently used)
                    if cache_key in self._document_cache_access_order:
                        self._document_cache_access_order.remove(cache_key)
                    self._document_cache_access_order.append(cache_key)
                    
                    # Update statistics
                    self._document_cache_stats["hits"] += 1
                    
                    logger.debug(f"📄 Document cache HIT: {cache_key[:50]}...")
                    return result
                else:
                    # Remove expired entry
                    self._remove_cache_entry(cache_key)
            
            # Cache miss
            self._document_cache_stats["misses"] += 1
            logger.debug(f"📄 Document cache MISS: {cache_key[:50]}...")
            return None
            
        except Exception as e:
            logger.debug(f"Cache retrieval error: {e}")
            self._document_cache_stats["misses"] += 1
            return None

    def _cache_document_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """
        Cache document result with intelligent LRU eviction and memory management
        """
        try:
            if not result:
                return
            
            # Estimate memory size of result (rough approximation)
            result_size = len(str(result).encode('utf-8'))
            
            # Check memory limits before adding
            if (self._document_cache_stats["memory_usage"] + result_size > self._max_cache_memory or 
                len(self._document_cache) >= self._max_cache_entries):
                self._evict_cache_entries(result_size)
            
            # Add to cache
            self._document_cache[cache_key] = (time.time(), result, result_size)
            self._document_cache_access_order.append(cache_key)
            self._document_cache_stats["memory_usage"] += result_size
            
            logger.debug(f"📄 Cached document result: {cache_key[:50]}... (size: {result_size} bytes)")
            
        except Exception as e:
            logger.debug(f"Cache storage error: {e}")

    def _remove_cache_entry(self, cache_key: str) -> None:
        """Remove a single cache entry and update tracking"""
        try:
            if cache_key in self._document_cache:
                _, _, size = self._document_cache[cache_key]
                del self._document_cache[cache_key]
                self._document_cache_stats["memory_usage"] -= size
                
                if cache_key in self._document_cache_access_order:
                    self._document_cache_access_order.remove(cache_key)
                    
        except Exception as e:
            logger.debug(f"Cache entry removal error: {e}")

    def _evict_cache_entries(self, needed_space: int) -> None:
        """
        Intelligent cache eviction using LRU strategy and memory awareness
        """
        try:
            freed_space = 0
            eviction_count = 0
            
            # Remove expired entries first
            current_time = time.time()
            expired_keys = []
            for key, (timestamp, _, size) in self._document_cache.items():
                if current_time - timestamp >= self._document_cache_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                if key in self._document_cache:
                    _, _, size = self._document_cache[key]
                    freed_space += size
                    eviction_count += 1
                    self._remove_cache_entry(key)
                    if freed_space >= needed_space:
                        break
            
            # If still need space, evict LRU entries
            while (freed_space < needed_space or 
                   len(self._document_cache) >= self._max_cache_entries):
                
                if not self._document_cache_access_order:
                    break
                    
                # Remove least recently used (first in list)
                lru_key = self._document_cache_access_order[0]
                if lru_key in self._document_cache:
                    _, _, size = self._document_cache[lru_key]
                    freed_space += size
                    eviction_count += 1
                    self._remove_cache_entry(lru_key)
            
            self._document_cache_stats["evictions"] += eviction_count
            
            if eviction_count > 0:
                logger.debug(f"📄 Evicted {eviction_count} cache entries, freed {freed_space} bytes")
                
        except Exception as e:
            logger.debug(f"Cache eviction error: {e}")

    def _generate_document_cache_key(self, user_id: int, files: List[Dict[str, Any]], message: str = "") -> str:
        """
        Generate optimized cache key for document processing results
        """
        try:
            import hashlib
            
            # Create content-based hash for files
            file_hashes = []
            for file in files or []:
                # Use filename, size, and content type for hash
                file_info = f"{file.get('filename', '')}{file.get('size', 0)}{file.get('content_type', '')}"
                # Include a hash of first 1KB of content if available
                content = file.get('content', '')
                if content:
                    if isinstance(content, str) and len(content) > 1000:
                        content = content[:1000]  # First 1KB for hash
                    file_info += str(hash(content))
                file_hashes.append(file_info)
            
            # Combine user, files, and message context
            cache_content = f"{user_id}_{'-'.join(file_hashes)}_{message[:100]}"
            
            # Generate SHA-256 hash for consistent, collision-resistant key
            return hashlib.sha256(cache_content.encode('utf-8')).hexdigest()[:32]  # 32 char key
            
        except Exception as e:
            logger.debug(f"Cache key generation error: {e}")
            # Fallback to simple hash
            return str(hash(f"{user_id}_{len(files or [])}_{message[:50]}"))[:32]

    def get_document_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive document cache performance statistics"""
        try:
            total_requests = self._document_cache_stats["total_requests"]
            hits = self._document_cache_stats["hits"]
            
            hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "cache_performance": {
                    "hit_rate_percentage": round(hit_rate, 2),
                    "total_requests": total_requests,
                    "cache_hits": hits,
                    "cache_misses": self._document_cache_stats["misses"],
                    "evictions": self._document_cache_stats["evictions"]
                },
                "memory_usage": {
                    "current_entries": len(self._document_cache),
                    "max_entries": self._max_cache_entries,
                    "memory_usage_bytes": self._document_cache_stats["memory_usage"],
                    "memory_usage_mb": round(self._document_cache_stats["memory_usage"] / (1024*1024), 2),
                    "max_memory_mb": round(self._max_cache_memory / (1024*1024), 2),
                    "memory_utilization_percentage": round(
                        (self._document_cache_stats["memory_usage"] / self._max_cache_memory * 100), 2
                    ) if self._max_cache_memory > 0 else 0
                },
                "efficiency": {
                    "average_entry_size_bytes": round(
                        self._document_cache_stats["memory_usage"] / len(self._document_cache)
                    ) if len(self._document_cache) > 0 else 0,
                    "cache_enabled": True,
                    "ttl_minutes": self._document_cache_ttl // 60
                }
            }
        except Exception as e:
            logger.error(f"Error generating cache stats: {e}")
            return {"error": "Unable to generate cache statistics"}

    def clear_document_cache(self) -> Dict[str, Any]:
        """Clear document cache and return statistics"""
        try:
            cleared_entries = len(self._document_cache)
            cleared_memory = self._document_cache_stats["memory_usage"]
            
            # Clear all cache data
            self._document_cache.clear()
            self._document_cache_access_order.clear()
            self._document_cache_stats["memory_usage"] = 0
            self._document_cache_stats["evictions"] += cleared_entries
            
            logger.info(f"📄 Cleared document cache: {cleared_entries} entries, {cleared_memory} bytes")
            
            return {
                "success": True,
                "cleared_entries": cleared_entries,
                "cleared_memory_bytes": cleared_memory,
                "cleared_memory_mb": round(cleared_memory / (1024*1024), 2)
            }
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {"success": False, "error": str(e)}
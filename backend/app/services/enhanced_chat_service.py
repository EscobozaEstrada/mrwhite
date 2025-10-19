"""
Enhanced Chat Service with Complete Knowledge Base Integration

This service provides comprehensive chat functionality with:
- Unified storage across all endpoints
- Context7 semantic understanding
- Complete knowledge base integration
- Proper health AI integration
- Pet context retrieval for personalized responses
"""

import json
import logging
from flask import current_app
from typing import Tuple, Dict, Any, List, Optional

from app.services.ai_service import AIService
from app.services.unified_chat_storage_service import get_unified_chat_storage
from app.services.context7_semantic_service import get_context7_service
from app.services.common_knowledge_service import CommonKnowledgeService
from app.services.pet_context_service import get_pet_context_service
from app.services.context7_semantic_service import ContentType

# Dynamic imports to avoid circular dependencies
try:
    from app.services.enhanced_document_chat_agents import EnhancedDocumentChatAgents
except ImportError:
    EnhancedDocumentChatAgents = None

try:
    from app.services.langgraph_chat_service import LangGraphChatService  
except ImportError:
    LangGraphChatService = None

try:
    from app.services.health_intelligence_service import HealthIntelligenceService
except ImportError:
    HealthIntelligenceService = None

class EnhancedChatService:
    """Enhanced chat service with complete knowledge base integration and pet context"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.storage_service = get_unified_chat_storage()
        self.context7_service = get_context7_service()
        self.common_knowledge_service = CommonKnowledgeService()
        self.pet_context_service = get_pet_context_service()
        
        # Initialize dependent services lazily
        self._document_chat_agents = None
        self._langgraph_chat_service = None
        self._health_intelligence_service = None
        self._services_initialized = False
    
    def _init_services(self):
        """Initialize dependent services lazily to avoid circular imports"""
        if self._services_initialized:
            return
        
        try:
            if EnhancedDocumentChatAgents:
                self._document_chat_agents = EnhancedDocumentChatAgents()
            
            if LangGraphChatService:
                self._langgraph_chat_service = LangGraphChatService()
                
            if HealthIntelligenceService:
                self._health_intelligence_service = HealthIntelligenceService()
            
            self._services_initialized = True
            current_app.logger.info("✅ Enhanced chat services initialized successfully")
            
        except Exception as e:
            current_app.logger.warning(f"Failed to initialize some services: {str(e)}")
    
    def generate_contextual_response(
        self, 
        user_id: int, 
        message: str, 
        conversation_id: Optional[int] = None,
        thread_id: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Generate contextual response using complete knowledge base integration
        
        This is the main entry point that:
        1. Analyzes message semantics with Context7
        2. Checks for pet context requirements 
        3. Searches all knowledge sources comprehensively
        4. Routes to appropriate specialized service
        5. Enhances response with pet context when needed
        6. Stores everything properly in unified storage
        7. Returns enhanced response
        """
        self._init_services()
        
        try:
            current_app.logger.info(f"🧠 Enhanced chat processing for user {user_id}: {message[:100]}...")
            
            # IMPROVED: Check if this is a document-related query
            is_document_query = False
            document_keywords = ["summarize", "summary", "document", "file", "pdf", "extract from document", 
                                "what's in the document", "what does the document say", "tell me about the document",
                                "analyze document", "document analysis", "extract information", "what's in my document",
                                "read document", "read the document", "read my document", "read this document"]
            
            if any(keyword in message.lower() for keyword in document_keywords):
                is_document_query = True
                current_app.logger.info(f"📄 Document-related query detected: '{message}'")
            
            # Check for recent document uploads
            recent_document_upload = self._check_recent_document_upload(user_id, conversation_id)
            
            # If we have a document query AND a recent upload, use document chat agents
            if (is_document_query or recent_document_upload) and self._document_chat_agents:
                current_app.logger.info(f"📄 Routing to document chat agent: '{message}'")
                
                # Use document chat agents for processing
                document_result = self._document_chat_agents.process_document_chat(
                    user_id=user_id,
                    query=message,
                    conversation_id=conversation_id,
                    thread_id=thread_id
                )
                
                if document_result.get("success"):
                    document_name = "your document"
                    if recent_document_upload and recent_document_upload.get("document_names"):
                        document_name = recent_document_upload.get("document_names")[0]
                    
                    return True, document_result["response"], {
                        "service_used": "document_chat_agent",
                        "intent": "document_summary",
                        "document_referenced": True,
                        "referenced_document": document_name,
                        "confidence_score": document_result.get("confidence_score", 0.9)
                    }
                else:
                    current_app.logger.warning(f"⚠️ Document chat agent failed: {document_result.get('error', 'Unknown error')}")
                    # Fall through to regular processing if document chat fails
            
            # Step 1: Context7 Semantic Analysis
            semantic_analysis = self.context7_service.analyze_content_semantics(
                content=message,
                context_history=self._get_recent_context(user_id, conversation_id)
            )
            
            # If this is a document-related query, update the content type
            if is_document_query:
                semantic_analysis.content_type = ContentType.DOCUMENT_REQUEST
                current_app.logger.info(f"📄 Set content type to DOCUMENT_REQUEST for document query")
            
            # Step 2: Get Pet Context
            pet_context = self.pet_context_service.get_pet_context(user_id, message)
            
            # Step 3: Analyze Pet Query
            pet_query_analysis = self.pet_context_service.analyze_pet_query(message)
            
            # Step 4: Get Knowledge Sources
            knowledge_sources = self.storage_service.get_comprehensive_knowledge_sources(
                user_id=user_id,
                query=message,
                conversation_id=conversation_id
            )
            
            # If we have document content in knowledge sources but semantic analysis didn't detect it,
            # and the query looks like it could be document-related, update the content type
            if knowledge_sources.get("user_documents") and len(knowledge_sources.get("user_documents", [])) > 0:
                if semantic_analysis.content_type != ContentType.DOCUMENT_REQUEST and is_document_query:
                    current_app.logger.info("📄 Updating content type to DOCUMENT_REQUEST based on knowledge sources")
                    semantic_analysis.content_type = ContentType.DOCUMENT_REQUEST
            
            # Step 5: Route to appropriate handler based on semantic analysis and pet context
            return self._route_with_semantic_and_pet_analysis(
                user_id=user_id,
                message=message,
                conversation_id=conversation_id,
                thread_id=thread_id,
                semantic_analysis=semantic_analysis,
                knowledge_sources=knowledge_sources,
                pet_context=pet_context,
                pet_query_analysis=pet_query_analysis
            )
            
        except Exception as e:
            current_app.logger.error(f"❌ Enhanced chat service failed: {str(e)}")
            return False, f"I apologize, but I'm having trouble processing your request. Please try again. Error: {str(e)}", {
                "error": str(e),
                "service": "enhanced_chat"
            }
    
    def _route_with_semantic_and_pet_analysis(
        self,
        user_id: int,
        message: str,
        conversation_id: int,
        thread_id: str,
        semantic_analysis,
        knowledge_sources: Dict[str, List[Any]],
        pet_context: Dict[str, Any],
        pet_query_analysis: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Route the query based on semantic analysis and pet context
        This is the central routing logic for the enhanced chat service
        """
        try:
            current_app.logger.info(f"🔀 Routing query with semantic analysis: {semantic_analysis.content_type.value}")
            
            # IMPROVED: Check for document content in knowledge sources
            has_document_content = False
            if knowledge_sources.get("user_documents") and len(knowledge_sources.get("user_documents", [])) > 0:
                has_document_content = True
                current_app.logger.info(f"📄 Found document content in knowledge sources")
            
            # Check for recent document uploads
            recent_document_upload = self._check_recent_document_upload(user_id, conversation_id)
            if recent_document_upload:
                current_app.logger.info(f"📄 Found recent document upload: {recent_document_upload.get('document_names', [])}")
            
            # IMPROVED: Handle document requests with highest priority
            if semantic_analysis.content_type == ContentType.DOCUMENT_REQUEST or has_document_content or recent_document_upload:
                current_app.logger.info("📄 Routing to document request handler")
                return self._handle_document_request_with_context(
                    user_id, message, conversation_id, thread_id, semantic_analysis, knowledge_sources
                )
            
            # Handle emergency situations with high priority
            if semantic_analysis.content_type == ContentType.EMERGENCY_SITUATION:
                current_app.logger.info("🚨 Routing to emergency handler")
                return self._handle_emergency_with_context(
                    user_id, message, semantic_analysis, knowledge_sources
                )
            
            # Handle reminder requests with high priority
            if semantic_analysis.content_type == ContentType.REMINDER_REQUEST:
                current_app.logger.info("⏰ Routing to reminder handler")
                return self._handle_reminder_request_with_context(
                    user_id, message, conversation_id, thread_id, 
                    semantic_analysis, knowledge_sources, pet_context
                )
            
            # Handle health queries with specialized health intelligence
            if semantic_analysis.content_type == ContentType.HEALTH_QUERY:
                current_app.logger.info("🏥 Routing to health query handler")
                return self._handle_health_query_with_context(
                    user_id, message, conversation_id, thread_id, semantic_analysis, knowledge_sources
                )
            
            # Check if this is a request for pet information that was already provided
            if "dog detail" in message.lower() or "my dog" in message.lower():
                # Check if we already have pet information in the context
                chat_messages = knowledge_sources.get("chat_history", [])
                if chat_messages:
                    current_app.logger.info(f"🔍 Checking {len(chat_messages)} chat messages for existing pet info")
                    
                    # Look for messages that might contain pet information
                    pet_info_messages = []
                    for doc in chat_messages:
                        content = doc.page_content.lower()
                        if any(pattern in content for pattern in ["dog name", "my dog", "breed is", "age is"]):
                            pet_info_messages.append(doc.page_content)
                    
                    if pet_info_messages:
                        current_app.logger.info(f"✅ Found {len(pet_info_messages)} messages with potential pet info")
                        
                        # Extract pet information directly
                        combined_text = "\n".join(pet_info_messages)
                        pets_found = self.pet_context_service._fallback_pet_extraction(combined_text)
                        
                        if pets_found:
                            current_app.logger.info(f"✅ Successfully extracted pet info: {pets_found}")
                            
                            # Create a response that uses the extracted information
                            pet = pets_found[0]  # Use the first pet found
                            response = f"Based on our conversation, I know that "
                            
                            if pet["name"] != "unknown":
                                response += f"your dog's name is {pet['name']}"
                                
                                if pet["breed"] != "unknown":
                                    response += f" and {pet['name']} is a {pet['breed']}"
                                    
                                if pet["age"] != "unknown":
                                    response += f", {pet['age']} old"
                                    
                                if pet["weight"] != "unknown":
                                    response += f", weighing {pet['weight']}"
                                
                                response += "."
                            elif pet["breed"] != "unknown":
                                response += f"you have a {pet['breed']}"
                                
                                if pet["age"] != "unknown":
                                    response += f" that is {pet['age']} old"
                                    
                                if pet["weight"] != "unknown":
                                    response += f", weighing {pet['weight']}"
                                
                                response += "."
                            
                            response += " Is there anything specific about your dog that you'd like to know or discuss?"
                            
                            return True, response, {
                                "service_used": "pet_context_retrieval",
                                "intent": "pet_info_retrieval",
                                "pet_info_found": True
                            }
            
            # Handle missing pet information for pet-specific queries
            if pet_query_analysis.get("needs_pet_context", False) and not pet_context.get("context_available", False):
                current_app.logger.info("🐕 Routing to missing pet info handler")
                return self._handle_missing_pet_info_query(
                    user_id, message, pet_query_analysis, knowledge_sources
                )
            
            # Handle multiple pets scenario
            if pet_context.get("context_available", False) and len(pet_context.get("pets_found", [])) > 1:
                current_app.logger.info("🐾 Routing to multiple pets handler")
                return self._handle_multiple_pets_query(
                    user_id, message, pet_context, pet_query_analysis, knowledge_sources
                )
            
            # Default to general chat with context
            current_app.logger.info("💬 Routing to general chat handler")
            return self._handle_general_chat_with_context(
                user_id, message, conversation_id, thread_id, semantic_analysis, knowledge_sources, pet_context
            )
            
        except Exception as e:
            current_app.logger.error(f"❌ Routing failed: {str(e)}")
            # Fallback to general handling
            return self._handle_fallback_with_context(
                user_id, message, semantic_analysis, knowledge_sources, pet_context
            )
    
    def _handle_missing_pet_info_query(
        self,
        user_id: int,
        message: str,
        pet_query_analysis: Dict[str, Any],
        knowledge_sources: Dict[str, List[Any]]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Handle queries when no pet information is found"""
        
        query_type = pet_query_analysis.get("query_type", "general_pet_care")
        
        # Check if this is a diet-related query for special handling
        is_diet_query = self.pet_context_service.is_diet_related_query(message)
        
        if is_diet_query:
            # For diet queries, ask for pet details to provide personalized advice
            response = f"I'd love to help you with {query_type.replace('_', ' ')}! To provide the most personalized advice, could you please tell me:\n\n"
            response += "• Your dog's name\n"
            response += "• Breed (or mix)\n"
            response += "• Age\n"
            response += "• Weight\n"
            response += "• Any known food allergies or health conditions\n\n"
            response += "This information will help me give you tailored recommendations! 🐕"
            
            # Note: Paw Tree recommendation will be added centrally in main response flow
            
            return True, response, {
                "service_used": "pet_info_collection_diet", 
                "intent": "diet_advice",
                "query_type": query_type,
                "confidence_score": 0.95,
                "pawtree_will_be_added_centrally": True,
                "pet_context_needed": True
            }
        
        # Original logic for non-diet queries
        response = f"I'd love to help you with {query_type.replace('_', ' ')}! To provide the most accurate and personalized advice, could you please tell me:\n\n"
        response += "• Your dog's name\n"
        response += "• Breed (or mix)\n"
        response += "• Age\n"
        response += "• Weight\n"
        
        if query_type == "health_advice":
            response += "• Current health status or concerns\n"
        elif query_type == "exercise_plan":
            response += "• Current activity level\n"
        
        response += "\nOnce I have this information, I can give you much more targeted and helpful advice! 🐕"
        
        return True, response, {
            "service_used": "pet_info_collection",
            "intent": "collect_pet_information",
            "query_type": query_type,
            "confidence_score": 0.9,
            "pet_context_needed": True
        }
    
    def _handle_multiple_pets_query(
        self,
        user_id: int,
        message: str,
        pet_context: Dict[str, Any],
        pet_query_analysis: Dict[str, Any],
        knowledge_sources: Dict[str, List[Any]]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Handle queries when multiple pets are found"""
        
        pets_found = pet_context.get("pets_found", [])
        query_type = pet_query_analysis.get("query_type", "general_pet_care")
        
        response = f"I found information about {len(pets_found)} pets in our previous conversations:\n\n"
        
        for i, pet in enumerate(pets_found, 1):
            name = pet.get("name", f"Pet {i}")
            breed = pet.get("breed", "Unknown breed")
            age = pet.get("age", "Unknown age")
            response += f"{i}. {name} - {breed}, {age}\n"
        
        response += f"\nWhich dog are you asking about for this {query_type.replace('_', ' ')} question? Please mention their name so I can provide personalized advice! 🐕"
        
        # Note: Paw Tree recommendation will be added centrally in main response flow
        
        return True, response, {
            "service_used": "pet_clarification",
            "intent": "clarify_pet_selection",
            "query_type": query_type,
            "pets_found": len(pets_found),
            "confidence_score": 0.9,
            "multiple_pets_found": True,
            "pawtree_will_be_added_centrally": self.pet_context_service.is_diet_related_query(message)
        }
    
    def _handle_emergency_with_context(
        self,
        user_id: int,
        message: str,
        semantic_analysis,
        knowledge_sources: Dict[str, List[Any]]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Handle emergency situations with available context"""
        
        current_app.logger.warning(f"🚨 Emergency situation detected for user {user_id}")
        
        # Build emergency response with available context
        emergency_context = ""
        if knowledge_sources.get("care_records"):
            emergency_context = "\n\nBased on your pet's records, "
        
        emergency_response = f"""
🚨 **EMERGENCY SITUATION DETECTED** 🚨

{emergency_context}here's what you should do immediately:

1. **Stay calm** - Your pet needs you to think clearly
2. **Contact your veterinarian immediately** or visit the nearest emergency animal hospital
3. **If your vet is unavailable**, call a 24-hour emergency animal clinic

⚠️ **Important Signs to Monitor:**
- Breathing difficulties
- Loss of consciousness
- Severe bleeding
- Signs of extreme pain
- Inability to move

📞 **Emergency Actions:**
- Keep your pet calm and warm
- Do not give food or water unless instructed
- Transport safely to emergency care

**This is urgent - please seek professional veterinary care immediately.**
        """
        
        return True, emergency_response.strip(), {
            "service_used": "emergency_handler",
            "intent": "emergency",
            "urgency_level": 5,
            "confidence_score": 0.95,
            "emergency_detected": True,
            "immediate_action_required": True
        }
    
    def _handle_health_query_with_context(
        self,
        user_id: int,
        message: str,
        conversation_id: int,
        thread_id: str,
        semantic_analysis,
        knowledge_sources: Dict[str, List[Any]]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Handle health queries with full context integration"""
        
        try:
            current_app.logger.info("🏥 Processing health query with enhanced context")
            
            # Use health intelligence service if available
            if self._health_intelligence_service:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    health_result = loop.run_until_complete(
                        self._health_intelligence_service.process_health_query(
                            user_id=user_id,
                            query=message,
                            thread_id=thread_id
                        )
                    )
                    
                    if health_result and health_result.get("response"):
                        return True, health_result["response"], {
                            "service_used": "health_intelligence",
                            "intent": "health_query",
                            "urgency": health_result.get("urgency", semantic_analysis.urgency_level),
                            "category": health_result.get("category"),
                            "confidence_score": 0.85,
                            "health_context_used": True
                        }
                finally:
                    loop.close()
            
            # Fallback to document chat if health service unavailable
            if self._document_chat_agents and knowledge_sources.get("care_records"):
                doc_result = self._document_chat_agents.process_document_chat(
                    user_id=user_id,
                    query=f"health information: {message}",
                    conversation_id=conversation_id,
                    thread_id=thread_id
                )
                
                if doc_result.get("success"):
                    response = doc_result["response"]
                    response += "\n\n⚠️ **Important**: This information is based on your records. Always consult your veterinarian for professional medical advice."
                    
                    return True, response, {
                        "service_used": "health_query_with_documents",
                        "intent": "health_query",
                        "confidence_score": doc_result.get("confidence_score", 0.7),
                        "document_referenced": True
                    }
            
            # Final fallback with health-focused context
            return self._generate_health_focused_response(user_id, message, knowledge_sources)
            
        except Exception as e:
            current_app.logger.error(f"❌ Health query handling failed: {str(e)}")
            return False, "I can help with health questions. Please provide more details about your concern.", {
                "error": str(e),
                "service": "health_query"
            }
    
    def _handle_general_chat_with_context(
        self,
        user_id: int,
        message: str,
        conversation_id: int,
        thread_id: str,
        semantic_analysis,
        knowledge_sources: Dict[str, List[Any]],
        pet_context: Dict[str, Any] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Handle general chat with full LangGraph and context integration"""
        
        try:
            current_app.logger.info("💬 Processing general chat with enhanced context")
            
            if self._langgraph_chat_service:
                response, context_info = self._langgraph_chat_service.process_message(
                    user_id=user_id,
                    message=message,
                    thread_id=thread_id
                )
                
                # Add Paw Tree recommendation for diet queries
                response = self._add_pawtree_if_diet_query(response, message, pet_context)
                
                return True, response, {
                    **context_info,
                    "service_used": "langgraph_enhanced",
                    "intent": "general_chat",
                    "context_integration": True,
                    "pawtree_checked": True
                }
            
            # Fallback to AI service with rich context
            return self._handle_fallback_with_context(user_id, message, semantic_analysis, knowledge_sources, pet_context)
            
        except Exception as e:
            current_app.logger.error(f"❌ General chat handling failed: {str(e)}")
            return self._handle_fallback_with_context(user_id, message, semantic_analysis, knowledge_sources, pet_context)
    
    def _add_pawtree_if_diet_query(
        self, 
        response: str, 
        message: str, 
        pet_context: Dict[str, Any] = None
    ) -> str:
        """
        Helper method for adding Paw Tree recommendations - now handled centrally
        
        Args:
            response: Original AI response
            message: User's query
            pet_context: Pet context information (optional)
            
        Returns:
            Original response unchanged (Paw Tree handled centrally now)
        """
        # Paw Tree recommendations are now handled centrally in the main response flow
        # to prevent duplication, so this method just returns the original response
        return response
    
    def _handle_fallback_with_context(
        self,
        user_id: int,
        message: str,
        semantic_analysis,
        knowledge_sources: Dict[str, List[Any]],
        pet_context: Dict[str, Any] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Fallback handler with comprehensive context and Paw Tree integration"""
        
        try:
            current_app.logger.info("🔄 Using fallback AI response with context")
            
            # Get relevant documents for context
            context_docs = []
            for source, docs in knowledge_sources.items():
                context_docs.extend(docs[:3])  # Limit to prevent overwhelming context
            
            # Use personalized response function
            try:
                from app.utils.personalization_helper import get_personalized_mr_white_response
                
                # Get conversation history for context
                conversation_history = None
                if user_id:
                    try:
                        from app.models.conversation import Conversation
                        from app.models.message import Message
                        conversation = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.updated_at.desc()).first()
                        if conversation:
                            messages = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.created_at).limit(10).all()
                            conversation_history = [
                                {
                                    "content": msg.content,
                                    "type": msg.type
                                } for msg in messages
                            ]
                    except Exception as e:
                        current_app.logger.error(f"Error getting conversation history: {str(e)}")
                
                # Generate personalized response
                ai_response = get_personalized_mr_white_response(
                    message=message,
                    context="chat",
                    conversation_history=conversation_history,
                    user_id=user_id
                )
                current_app.logger.info("✅ Generated personalized response with username")
            except Exception as e:
                current_app.logger.error(f"Error using personalized response: {str(e)}")
                # Fallback to regular AI service
                ai_response = self.ai_service.get_smart_response(
                    user_id=user_id,
                    query=message,
                    conversation_history=None
                )
            
            # Add Paw Tree recommendation if it's a diet query
            ai_response = self._add_pawtree_if_diet_query(ai_response, message, pet_context)
            
            return True, ai_response, {
                "service_used": "fallback_with_context",
                "intent": "general_assistance", 
                "confidence_score": 0.6,
                "context_sources": list(knowledge_sources.keys()),
                "documents_used": len(context_docs),
                "pawtree_checked": True
            }
            
        except Exception as e:
            current_app.logger.error(f"Fallback handler failed: {str(e)}")
            
            # Final fallback to basic response
            try:
                from app.utils.personalization_helper import get_personalized_mr_white_response
                basic_response = get_personalized_mr_white_response(message, "chat", None, user_id)
            except Exception:
                basic_response = "I apologize, but I'm having trouble processing your request right now. Please try again in a moment."
            
            return True, basic_response, {
                "service_used": "final_fallback",
                "error": str(e),
                "pawtree_checked": True
            }
    
    def _get_recent_context(self, user_id: int, conversation_id: Optional[int]) -> List[Dict[str, Any]]:
        """Get recent conversation context for semantic analysis"""
        try:
            if not conversation_id:
                return []
            
            from app.models.message import Message
            recent_messages = Message.query.filter_by(conversation_id=conversation_id)\
                .order_by(Message.created_at.desc()).limit(5).all()
            
            return [
                {
                    "content": msg.content,
                    "type": msg.type,
                    "timestamp": msg.created_at.isoformat()
                }
                for msg in reversed(recent_messages)  # Chronological order
            ]
            
        except Exception as e:
            current_app.logger.error(f"Error getting recent context: {str(e)}")
            return []
    
    def _get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user profile information for personalization"""
        try:
            from app.models.user import User
            user = User.query.get(user_id)
            
            if user:
                return {
                    "user_id": user_id,
                    "timezone": getattr(user, "timezone", "UTC"),
                    "subscription_tier": getattr(user, "subscription_tier", "free"),
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
            
            return {"user_id": user_id}
            
        except Exception as e:
            current_app.logger.error(f"Error getting user profile: {str(e)}")
            return {"user_id": user_id}
    
    def _handle_reminder_request_with_context(
        self,
        user_id: int,
        message: str,
        conversation_id: int,
        thread_id: str,
        semantic_analysis,
        knowledge_sources: Dict[str, List[Any]],
        pet_context: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Handle reminder requests by routing to the reminder system
        """
        try:
            current_app.logger.info(f"🔔 Processing reminder request for user {user_id}: {message}")
            
            # Import required modules for reminder handling
            from app.services.ai_time_manager import get_ai_time_manager
            from app.models.user import User
            from app.models.health_models import HealthReminder, ReminderType, ReminderStatus
            from app import db
            from datetime import datetime, time
            import re
            
            # Get user information for timezone handling
            user = User.query.get(user_id)
            if not user:
                return False, "User not found", {"error": "user_not_found"}
            
                         # Initialize AI time manager
            ai_time_manager = get_ai_time_manager()
            
            # Extract reminder details from the message using intelligent parsing
            reminder_details = self._parse_reminder_from_message(message, user.timezone)
            
            # If we have pet context available, enhance the reminder details
            if pet_context and pet_context.get("context_available", False) and pet_context.get("pets_found"):
                primary_pet = pet_context["pets_found"][0]  # Use first pet if multiple
                pet_name = primary_pet.get("name", "your pet")
                if pet_name and pet_name.lower() not in reminder_details["title"].lower():
                    reminder_details["title"] = f"{reminder_details['title']} for {pet_name}"
            
            # If we have enough details, create the reminder directly
            if reminder_details.get("has_sufficient_details", False):
                try:
                    # Get user for timezone information
                    user = User.query.get(user_id)
                    user_timezone = user.timezone if user else 'UTC'
                    
                    # Create timezone metadata for proper scheduling
                    timezone_metadata = {
                        'user_timezone': user_timezone,
                        'timezone_aware_creation': True,
                        'extraction_timestamp': datetime.utcnow().isoformat(),
                        'creation_source': 'chat_service'
                    }
                    
                    # Create the reminder
                    reminder = HealthReminder(
                        user_id=user_id,
                        title=reminder_details.get("title", "Health Reminder"),
                        description=reminder_details.get("description", ""),
                        reminder_type=ReminderType(reminder_details.get("reminder_type", "custom")),
                        due_date=reminder_details.get("due_date"),
                        due_time=reminder_details.get("due_time"),
                        status=ReminderStatus.PENDING,
                        send_push=True,
                        send_email=True,
                        days_before_reminder=reminder_details.get("advance_notice_days", 1),
                        extra_data=json.dumps(timezone_metadata)
                    )
                    
                    db.session.add(reminder)
                    db.session.commit()
                    
                    # 🎯 CRITICAL FIX: Schedule the reminder for precision notifications
                    try:
                        from app.services.precision_reminder_scheduler import get_precision_scheduler
                        precision_scheduler = get_precision_scheduler()
                        
                        if precision_scheduler and precision_scheduler.is_running:
                            scheduled = precision_scheduler.schedule_reminder(reminder)
                            if scheduled:
                                current_app.logger.info(f"⏰ Precision scheduled chat reminder {reminder.id} for notifications")
                            else:
                                current_app.logger.warning(f"⚠️  Failed to precision schedule chat reminder {reminder.id}")
                        else:
                            current_app.logger.warning(f"⚠️  Precision scheduler not available for chat reminder {reminder.id}")
                    except Exception as scheduler_error:
                        current_app.logger.error(f"❌ Error scheduling chat reminder {reminder.id}: {str(scheduler_error)}")
                    
                    # Format the success response
                    due_datetime = datetime.combine(reminder.due_date, reminder.due_time or time(9, 0))
                    formatted_date = due_datetime.strftime("%B %d, %Y at %I:%M %p")
                    
                    success_response = f"""🔔 **Reminder Created Successfully!**

📋 **Title:** {reminder.title}
📅 **Due Date:** {formatted_date}
🔔 **Type:** {reminder.reminder_type.value.replace('_', ' ').title()}
📧 **Notifications:** Email and push notifications enabled

Your reminder is now scheduled and you'll receive notifications before it's due. Visit your [Reminders Dashboard](/reminders) to view and manage all your reminders.

Is there anything else I can help you with?"""

                    current_app.logger.info(f"✅ Reminder created successfully: ID {reminder.id}")
                    
                    return True, success_response, {
                        "intent": "reminder_created",
                        "reminder_id": reminder.id,
                        "service_used": "enhanced_reminder_system",
                        "reminder_details": {
                            "title": reminder.title,
                            "due_date": formatted_date,
                            "type": reminder.reminder_type.value
                        }
                    }
                    
                except Exception as e:
                    current_app.logger.error(f"❌ Failed to create reminder: {str(e)}")
                    # Fall through to interactive mode
            
            # If we don't have sufficient details, provide interactive reminder setup
            interactive_response = self._generate_interactive_reminder_response(
                message, reminder_details, user.timezone
            )
            
            return True, interactive_response, {
                "intent": "reminder_interactive_setup",
                "service_used": "enhanced_reminder_system",
                "requires_followup": True,
                "extracted_details": reminder_details
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Error handling reminder request: {str(e)}")
            
            # Provide a helpful fallback response
            fallback_response = f"""🔔 **I'd be happy to help you set up a reminder!**

I detected that you want to create a reminder, but encountered a technical issue while processing your request.

🎯 **To create your reminder successfully:**

1. **Visit the [Reminders Dashboard](/reminders)** for our full-featured reminder system
2. **Use the AI Smart Reminder** feature for intelligent time suggestions
3. **Or try rephrasing your request** with clear details like:
   - "Remind me to feed my dog at 4:50 AM today"
   - "Set a vaccination reminder for next Tuesday at 2 PM"

The Reminders Dashboard offers AI-powered time optimization, timezone-aware scheduling, email and push notifications, and recurring reminder options.

Would you like me to help you with anything else?"""

            return True, fallback_response, {
                "error": str(e),
                "intent": "reminder_fallback",
                "service_used": "reminder_fallback"
            }
    
    def _parse_reminder_from_message(self, message: str, user_timezone: str = "UTC") -> Dict[str, Any]:
        """
        Parse reminder details from natural language message
        """
        import re
        from datetime import datetime, timedelta, time
        
        details = {
            "has_sufficient_details": False,
            "title": "",
            "description": "",
            "reminder_type": "custom",
            "due_date": None,
            "due_time": None,
            "advance_notice_days": 1
        }
        
        message_lower = message.lower()
        
        # Extract title (simplified - use the original message as title)
        if len(message) > 10:
            details["title"] = message[:100] + "..." if len(message) > 100 else message
        
# First, try to identify pet name
        pet_name = None
        pet_name_patterns = [
            r"(?:for|my)\s+(?:dog|cat|pet)\s+([a-zA-Z]+)",  # "my dog Ruby"
            r"(?:dog|cat|pet)\s+named\s+([a-zA-Z]+)",       # "dog named Ruby"
            r"([a-zA-Z]+)(?:'s|\s+needs)",                  # "Ruby's" or "Ruby needs"
            r"(?:for|my)\s+([a-zA-Z]+)(?:\s+(?:the|my)\s+(?:dog|cat|pet))",  # "for Ruby the dog"
        ]
        
        for pattern in pet_name_patterns:
            pet_match = re.search(pattern, message)
            if pet_match:
                pet_name = pet_match.group(1).strip().capitalize()
                current_app.logger.info(f"🐾 Extracted pet name: {pet_name}")
                break
        
        # Extract activity/purpose
        purpose = None
        purpose_patterns = [
            r"for\s+(grooming|vaccination|checkup|medication|vet appointment|vet visit|shots|bath|nail trim|haircut)",
            r"to\s+(groom|vaccinate|check|medicate|visit vet|get shots|take bath|trim nails|get haircut)",
            r"(grooming|vaccination|checkup|medication|vet appointment|vet visit|shots|bath|nail trim|haircut)\s+(?:appointment|session|reminder)",
            r"(?:schedule|book|plan)\s+(?:a|an)?\s+(grooming|vaccination|checkup|medication|vet appointment|vet visit|shots|bath|nail trim|haircut)"
        ]
        
        for pattern in purpose_patterns:
            purpose_match = re.search(pattern, message.lower())
            if purpose_match:
                purpose = purpose_match.group(1).strip()
                current_app.logger.info(f"🎯 Extracted purpose: {purpose}")
                break
        
        # Extract reminder type based on purpose if found
        if purpose:
            if "groom" in purpose.lower():
                details["reminder_type"] = "grooming"
            elif "vaccin" in purpose.lower():
                details["reminder_type"] = "vaccination"
            elif "check" in purpose.lower() or "vet" in purpose.lower():
                details["reminder_type"] = "vet_appointment"
            elif "medic" in purpose.lower():
                details["reminder_type"] = "medication"
        else:
            # Fallback to keyword-based reminder type extraction
            type_patterns = {
                "vaccination": ["vaccin", "shot", "immuniz"],
                "vet_appointment": ["vet", "veterinarian", "doctor", "appointment"],
                "medication": ["medication", "medicine", "pill", "dose"],
                "grooming": ["groom", "bath", "haircut", "nail", "brush"],
                "checkup": ["checkup", "check up", "exam", "physical"],
                "custom": ["feed", "feeding", "food", "meal", "eat", "nutrition"]
            }
            
            for reminder_type, patterns in type_patterns.items():
                if any(pattern in message_lower for pattern in patterns):
                    details["reminder_type"] = reminder_type
                    current_app.logger.info(f"📋 Extracted reminder type from keywords: {reminder_type}")
                    break
        
        # Construct title
        if purpose and pet_name:
            details["title"] = f"{purpose.capitalize()} for {pet_name}"
        elif purpose:
            details["title"] = f"{purpose.capitalize()}"
        elif pet_name:
            details["title"] = f"Reminder for {pet_name}"
        else:
            # Fallback to using a cleaned version of the message
            # Remove time-related phrases
            time_phrases = ["today", "tomorrow", "next week", "at", "pm", "am", "remind me", "set a reminder"]
            cleaned_message = message
            for phrase in time_phrases:
                cleaned_message = re.sub(r'\b' + phrase + r'\b', '', cleaned_message, flags=re.IGNORECASE)
            
            # Clean up extra spaces and trim
            cleaned_message = re.sub(r'\s+', ' ', cleaned_message).strip()
            
            if cleaned_message:
                details["title"] = cleaned_message[:50] + ("..." if len(cleaned_message) > 50 else "")
            else:
                details["title"] = f"{details['reminder_type'].capitalize()} Reminder"
        
        # Set description to original message
        details["description"] = message
        
        # Log the final title and description
        current_app.logger.info(f"📝 Final reminder details - Title: '{details['title']}', Type: {details['reminder_type']}")
        
        # Extract time references
        time_patterns = {
            "today": 0,
            "tomorrow": 1,
            "next week": 7,
            "in a week": 7,
            "in 2 weeks": 14,
            "in a month": 30
        }
        
        for pattern, days_ahead in time_patterns.items():
            if pattern in message_lower:
                details["due_date"] = (datetime.now() + timedelta(days=days_ahead)).date()
                current_app.logger.info(f"📅 Extracted date: {details['due_date']} (pattern: {pattern}, days ahead: {days_ahead})")
                details["has_sufficient_details"] = True
                break
        
        # Extract specific times - comprehensive pattern matching
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)',  # "4:5z0 am"
            r'at\s*(\d{1,2}):(\d{2})\s*(am|pm)',  # "at 4:50 am"  
            r'(\d{1,2}):(\d{2})',  # "4:50" (24-hour assumed if no am/pm)
            r'(\d{1,2})[\.:](\d{2})\s*(am|pm)',  # "3.10pm" or "3:10pm"
            r'(\d{1,2})[\.:](\d{2})',  # "3.10" or "3:10" (24-hour assumed if no am/pm)
            r'(\d{1,2})\s*(am|pm)',  # "3 pm" or "3pm"
            r'at\s*(\d{1,2})\s*(am|pm)',  # "at 3 pm"
            r'(\d{1,2})\s*o\'?clock\s*(am|pm)?',  # "3 o'clock" or "3 oclock pm"
        ]
        
        for pattern in time_patterns:
            time_match = re.search(pattern, message_lower)
            if time_match:
                hour = int(time_match.group(1))
                
                # Check if this pattern has minutes or just hours
                if time_match.lastindex >= 2 and time_match.group(2) not in ["am", "pm"]:
                    minute = int(time_match.group(2))
                else:
                    minute = 0  # Default to top of the hour
                
                # Get am/pm if available - could be in group 2 or 3 depending on pattern
                ampm = None
                for i in range(2, time_match.lastindex + 1):
                    if time_match.group(i) in ["am", "pm"]:
                        ampm = time_match.group(i)
                        break
                
                # Handle am/pm conversion
                if ampm:
                    if ampm == "pm" and hour != 12:
                        hour += 12
                    elif ampm == "am" and hour == 12:
                        hour = 0
                        
                details["due_time"] = time(hour, minute)
                current_app.logger.info(f"⏰ Extracted time: {hour}:{minute:02d} (pattern: {pattern}, match: {time_match.group(0)})")
                break  # Stop at first match
        
        # If we have both date and time with a clear reminder request, mark as sufficient
        if details["due_date"] and details["due_time"] and any(keyword in message_lower for keyword in ["remind", "reminder", "schedule", "set"]):
            details["has_sufficient_details"] = True
        # Or if we have date and a clear reminder request, also sufficient
        elif details["due_date"] and any(keyword in message_lower for keyword in ["remind", "reminder", "schedule"]):
            details["has_sufficient_details"] = True
        
        # Log the final extraction results
        current_app.logger.info(f"🔍 Reminder parsing results: date={details.get('due_date')}, time={details.get('due_time')}, sufficient={details.get('has_sufficient_details')}")
        
        return details
    
    def _generate_interactive_reminder_response(
        self, 
        message: str, 
        extracted_details: Dict[str, Any], 
        user_timezone: str
    ) -> str:
        """
        Generate an interactive response for reminder setup
        """
        response = f"""🔔 **I'd be happy to help you set up a reminder!**

I understand you want to set up a reminder. Here's what I understood from your request:

📋 **Your Request:** {message}
"""
        
        if extracted_details.get("reminder_type") != "custom":
            response += f"- Type: {extracted_details['reminder_type'].replace('_', ' ').title()}\n"
        
        if extracted_details.get("due_date"):
            response += f"- Date: {extracted_details['due_date'].strftime('%B %d, %Y')}\n"
        
        if extracted_details.get("due_time"):
            response += f"- Time: {extracted_details['due_time'].strftime('%I:%M %p')}\n"
        
        response += f"""
🎯 **To complete your reminder setup, please visit our dedicated [Reminders Dashboard](/reminders) where you can:**

✨ Use our **AI-powered reminder creation** with smart time suggestions
🌍 Set timezone-aware scheduling
📱 Configure email and push notifications
🔄 Set up recurring reminders if needed
📊 View all your reminders in one place

**Or you can tell me more details here, such as:**
- "Remind me about Max's vaccination next Tuesday at 2 PM"
- "Set up a grooming appointment reminder for next week"
- "Schedule a vet checkup reminder for the 15th"

Would you like me to help you with anything else regarding reminders?"""

        return response

    def _handle_document_request_with_context(
        self,
        user_id: int,
        message: str,
        conversation_id: int,
        thread_id: str,
        semantic_analysis,
        knowledge_sources: Dict[str, List[Any]]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Handle document-related requests using enhanced document chat agents"""
        
        try:
            current_app.logger.info(f"📄 Handling document request with enhanced agents: '{message}'")
            
            # Check for recent document uploads first
            document_context = self._check_recent_document_upload(user_id, conversation_id)
            
            # Get any document content from knowledge sources
            document_content = ""
            doc_sources = knowledge_sources.get("user_documents", [])
            
            if doc_sources and len(doc_sources) > 0:
                # Extract content from the first document
                doc = doc_sources[0]
                if hasattr(doc, 'page_content') and doc.page_content:
                    document_content = doc.page_content
                    current_app.logger.info(f"✅ Found document content in knowledge sources: {len(document_content)} characters")
            
            if not document_context and not doc_sources:
                current_app.logger.warning("⚠️ No document context or content found for document request")
                return False, "I don't see any documents that you've uploaded recently. Please upload a document first, and then I'll be able to summarize it or answer questions about it.", {
                    "service_used": "document_chat_agent",
                    "intent": "document_request",
                    "document_referenced": False,
                    "error": "no_document_found"
                }
            else:
                if document_context:
                    current_app.logger.info(f"✅ Found document context: {document_context.get('document_names', [])}")
                if doc_sources:
                    current_app.logger.info(f"✅ Found {len(doc_sources)} documents in knowledge sources")
            
            # Create conversation context with document content if available
            conversation_context = {}
            if document_content:
                conversation_context["document_content"] = document_content
                
            # Process document chat through enhanced agents
            if self._document_chat_agents:
                current_app.logger.info("🔄 Sending request to document chat agents")
                
                # Register document query with context manager
                try:
                    from app.utils.conversation_context_manager import get_context_manager
                    context_manager = get_context_manager()
                    context_manager.register_document_query(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        query=message,
                        query_type="document_request"
                    )
                    current_app.logger.info("✅ Registered document query with context manager")
                except Exception as e:
                    current_app.logger.error(f"❌ Failed to register document query: {str(e)}")
                
                # Process the document request
                document_result = self._document_chat_agents.process_document_chat(
                    user_id=user_id,
                    query=message,
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                    conversation_context=conversation_context
                )
                
                if document_result.get('success'):
                    current_app.logger.info("✅ Document chat processed successfully")
                    
                    # Get document name if available
                    document_name = "your document"
                    if document_context and document_context.get("document_names"):
                        document_name = document_context.get("document_names")[0]
                    elif document_result.get("source_document"):
                        document_name = document_result.get("source_document")
                    
                    response = document_result.get('response', '')
                    
                    # Ensure the response doesn't contain pet care expert framing
                    if "pet care expert" in response.lower() or "mr. white" in response.lower():
                        current_app.logger.warning("⚠️ Response contains pet care framing, removing")
                        response = response.replace("As a pet care expert", "")
                        response = response.replace("As Mr. White", "")
                        response = response.replace("I'm a pet care expert", "")
                        response = response.replace("I'm Mr. White", "")
                    
                    return True, response, {
                        "service_used": "document_chat_agent",
                        "intent": "document_request",
                        "document_referenced": True,
                        "referenced_document": document_name,
                        "confidence_score": document_result.get('confidence_score', 0.8)
                    }
                else:
                    current_app.logger.warning(f"⚠️ Document chat processing failed: {document_result.get('error', 'Unknown error')}")
                    
                    # If we have document content but the document chat failed, generate a direct response
                    if document_content and len(document_content) > 100:
                        current_app.logger.info("⚠️ Document chat failed but we have content, generating direct response")
                        try:
                            # Generate a direct response using the document content
                            document_name = "your document"
                            if document_context and document_context.get("document_names"):
                                document_name = document_context.get("document_names")[0]
                            
                            direct_prompt = f"""
                            You are a document analysis expert.
                            
                            User Query: "{message}"
                            
                            Document Name: {document_name}
                            
                            Document Content: {document_content[:8000]}
                            
                            The user is asking about this document. Please provide:
                            1. A comprehensive response that directly addresses their query
                            2. If they're asking for a summary, provide a detailed summary of the document
                            3. Key points and insights from the document relevant to their query
                            4. Any relevant information that would be useful to the user
                            
                            Format your response as a well-structured answer with sections and bullet points where appropriate.
                            Focus ONLY on the document content. Do NOT include any disclaimers about being an AI assistant.
                            """
                            
                            from langchain.schema import SystemMessage as LCSystemMessage
                            from langchain.schema import HumanMessage as LCHumanMessage
                            
                            response = self.ai_service.get_smart_response(
                                user_id=user_id,
                                query=direct_prompt,
                                conversation_history=None
                            )
                            
                            return True, response.content, {
                                "service_used": "direct_document_analysis",
                                "intent": "document_request",
                                "document_referenced": True,
                                "referenced_document": document_name,
                                "confidence_score": 0.9
                            }
                        except Exception as e:
                            current_app.logger.error(f"❌ Direct response generation failed: {str(e)}")
                    
                    # Fallback to using knowledge sources
                    return self._handle_fallback_with_context(
                        user_id, message, semantic_analysis, knowledge_sources, {}
                    )
            else:
                current_app.logger.warning("⚠️ Document chat agents not available")
                return self._handle_fallback_with_context(
                    user_id, message, semantic_analysis, knowledge_sources, {}
                )
                
        except Exception as e:
            current_app.logger.error(f"❌ Document request handling failed: {str(e)}")
            return False, "I apologize, but I'm having trouble processing your document request. Please try again.", {
                "error": str(e),
                "service": "document_request"
            }

    def _check_recent_document_upload(self, user_id: int, conversation_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """Check if there was a recent document upload in this conversation"""
        if not conversation_id:
            # Even without conversation_id, try to check for recent documents
            try:
                # Import Document model only when needed
                try:
                    from app.models.document import Document
                except ImportError:
                    current_app.logger.warning("Document model not available, skipping document check")
                    return None
                    
                from datetime import datetime, timedelta
                
                # Look for documents uploaded in the last 24 hours
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                recent_documents = Document.query.filter(
                    Document.user_id == user_id,
                    Document.created_at >= cutoff_time
                ).order_by(Document.created_at.desc()).limit(3).all()
                
                if recent_documents:
                    document_names = [doc.filename for doc in recent_documents]
                    current_app.logger.info(f"✅ Found recent documents without conversation: {document_names}")
                    return {
                        "has_documents": True,
                        "document_names": document_names,
                        "last_document_interaction": datetime.utcnow().isoformat()
                    }
            except Exception as e:
                current_app.logger.error(f"❌ Error checking recent documents: {str(e)}")
            
            return None
            
        try:
            from app.utils.conversation_context_manager import get_context_manager
            context_manager = get_context_manager()
            
            # Get document context
            document_context = context_manager.get_document_context(user_id, conversation_id)
            current_app.logger.info(f"🔍 Checking for document context in conversation {conversation_id}: {document_context is not None}")
            
            if document_context and document_context.get("has_documents", False):
                current_app.logger.info(f"✅ Found document context: {document_context.get('document_names', [])}")
                return document_context
            
            # If no document context in this conversation, check other recent conversations
            from app.models.conversation import Conversation
            from app.models.message import Message
            from datetime import datetime, timedelta
            
            # Look for conversations with document uploads in the last 60 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=60)
            
            # Find recent conversations for this user
            recent_conversations = Conversation.query.filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= cutoff_time
            ).order_by(Conversation.created_at.desc()).limit(5).all()
            
            current_app.logger.info(f"🔍 Checking {len(recent_conversations)} recent conversations for document context")
            
            for conv in recent_conversations:
                if conv.id == conversation_id:
                    continue  # Skip current conversation, already checked
                    
                other_document_context = context_manager.get_document_context(user_id, conv.id)
                if other_document_context and other_document_context.get("has_documents", False):
                    current_app.logger.info(f"✅ Found document context in conversation {conv.id}: {other_document_context.get('document_names', [])}")
                    return other_document_context
            
            # Check for document upload messages in current conversation
            messages = Message.query.filter(
                Message.conversation_id == conversation_id,
                Message.created_at >= cutoff_time
            ).order_by(Message.created_at.desc()).all()
            
            for msg in messages:
                if msg.type == "ai" and any(keyword in msg.content.lower() for keyword in 
                                          ["document processing complete", "processed documents", "uploaded document",
                                           "document has been", "documents have been", "document analysis",
                                           "analyzed your document", "analyzed your documents"]):
                    current_app.logger.info(f"✅ Found document upload message in conversation {conversation_id}")
                    
                    # Try to extract document names from the message
                    import re
                    doc_match = re.search(r"Processed Documents:(.+?)[\n\r]", msg.content)
                    if doc_match:
                        doc_names = [name.strip() for name in doc_match.group(1).split(",")]
                        return {
                            "has_documents": True,
                            "document_names": doc_names,
                            "last_document_interaction": datetime.utcnow().isoformat()
                        }
                    
                    # Try alternative pattern
                    doc_match = re.search(r"Document: (.+?)[\n\r]", msg.content)
                    if doc_match:
                        doc_name = doc_match.group(1).strip()
                        return {
                            "has_documents": True,
                            "document_names": [doc_name],
                            "last_document_interaction": datetime.utcnow().isoformat()
                        }
                    
                    # If we can't extract names, just return a generic context
                    return {
                        "has_documents": True,
                        "document_names": ["Recently uploaded document"],
                        "last_document_interaction": datetime.utcnow().isoformat()
                    }
            
            # Check for recent documents in the database as a last resort
            try:
                # Import Document model only when needed
                try:
                    from app.models.document import Document
                except ImportError:
                    current_app.logger.warning("Document model not available, skipping document check")
                    return None
                
                # Look for documents uploaded in the last 24 hours
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                recent_documents = Document.query.filter(
                    Document.user_id == user_id,
                    Document.created_at >= cutoff_time
                ).order_by(Document.created_at.desc()).limit(3).all()
                
                if recent_documents:
                    document_names = [doc.filename for doc in recent_documents]
                    current_app.logger.info(f"✅ Found recent documents in database: {document_names}")
                    return {
                        "has_documents": True,
                        "document_names": document_names,
                        "last_document_interaction": datetime.utcnow().isoformat()
                    }
            except Exception as e:
                current_app.logger.error(f"❌ Error checking recent documents: {str(e)}")
            
            current_app.logger.info("❌ No document context found in any recent conversation")
            return None
            
        except Exception as e:
            current_app.logger.error(f"❌ Error checking document upload: {str(e)}")
            return None
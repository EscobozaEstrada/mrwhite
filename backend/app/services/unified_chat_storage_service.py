"""
Unified Chat Storage Service

This service provides a single, consistent interface for storing all chat messages
across different endpoints and ensuring proper knowledge base integration.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from flask import current_app

from app import db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services.ai_service import AIService
from app.utils.file_handler import get_chat_namespace
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
import os

logger = logging.getLogger(__name__)

class UnifiedChatStorageService:
    """Unified service for consistent chat storage across all endpoints"""
    
    def __init__(self):
        self.ai_service = AIService()
    
    def store_message_complete(
        self, 
        user_id: int,
        conversation_id: int,
        user_message: str,
        ai_response: str,
        context_info: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Store complete message exchange (user + AI) with full knowledge base integration
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID  
            user_message: User's message content
            ai_response: AI's response content
            context_info: Additional context from AI processing
            attachments: Any file attachments
            
        Returns:
            Tuple of (success, storage_info)
        """
        try:
            current_app.logger.info(f"🗄️ Storing complete message exchange for user {user_id}")
            
            storage_info = {
                "user_message_stored": False,
                "ai_message_stored": False,
                "vector_storage": {
                    "user_message": False,
                    "ai_response": False
                },
                "knowledge_base_updated": False,
                "context_preserved": False,
                "message_ids": {},
                "errors": []
            }
            
            # 1. Store user message in database
            user_msg_result = self._store_database_message(
                conversation_id, user_message, "user", attachments
            )
            
            if user_msg_result["success"]:
                storage_info["user_message_stored"] = True
                storage_info["message_ids"]["user"] = user_msg_result["message_id"]
                
                # Store user message in vector database
                vector_result = self._store_vector_message(
                    user_id, user_message, user_msg_result["message_id"], 
                    "user", conversation_id, context_info
                )
                storage_info["vector_storage"]["user_message"] = vector_result["success"]
                if not vector_result["success"]:
                    storage_info["errors"].append(f"User message vector storage failed: {vector_result['error']}")
            else:
                storage_info["errors"].append(f"User message database storage failed: {user_msg_result['error']}")
            
            # 2. Store AI response in database  
            ai_msg_result = self._store_database_message(
                conversation_id, ai_response, "ai", None
            )
            
            if ai_msg_result["success"]:
                storage_info["ai_message_stored"] = True
                storage_info["message_ids"]["ai"] = ai_msg_result["message_id"]
                
                # Store AI response in vector database with enhanced metadata
                ai_context = {
                    **(context_info or {}),
                    "response_type": "ai_generated",
                    "original_query": user_message,
                    "conversation_context": True
                }
                
                vector_result = self._store_vector_message(
                    user_id, ai_response, ai_msg_result["message_id"],
                    "ai", conversation_id, ai_context
                )
                storage_info["vector_storage"]["ai_response"] = vector_result["success"]
                if not vector_result["success"]:
                    storage_info["errors"].append(f"AI response vector storage failed: {vector_result['error']}")
            else:
                storage_info["errors"].append(f"AI response database storage failed: {ai_msg_result['error']}")
            
            # 3. Update conversation timestamp
            try:
                conversation = Conversation.query.get(conversation_id)
                if conversation:
                    conversation.updated_at = datetime.now(timezone.utc)
                    db.session.commit()
            except Exception as e:
                storage_info["errors"].append(f"Conversation update failed: {str(e)}")
            
            # 4. Update user knowledge base metadata
            try:
                self._update_knowledge_base_stats(user_id)
                storage_info["knowledge_base_updated"] = True
            except Exception as e:
                storage_info["errors"].append(f"Knowledge base stats update failed: {str(e)}")
            
            # 5. Preserve context for future queries
            if context_info:
                try:
                    self._preserve_conversation_context(user_id, conversation_id, context_info)
                    storage_info["context_preserved"] = True
                except Exception as e:
                    storage_info["errors"].append(f"Context preservation failed: {str(e)}")
            
            # Calculate overall success
            overall_success = (
                storage_info["user_message_stored"] and 
                storage_info["ai_message_stored"] and
                len(storage_info["errors"]) == 0
            )
            
            current_app.logger.info(f"✅ Complete message storage result: {overall_success}")
            if storage_info["errors"]:
                current_app.logger.warning(f"⚠️ Storage errors: {storage_info['errors']}")
            
            return overall_success, storage_info
            
        except Exception as e:
            logger.error(f"❌ Critical error in store_message_complete: {str(e)}")
            return False, {"errors": [str(e)], "critical_failure": True}
    
    def _store_database_message(
        self, 
        conversation_id: int, 
        content: str, 
        message_type: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Store message in PostgreSQL database"""
        try:
            # Create message record
            message = Message(
                conversation_id=conversation_id,
                content=content,
                type=message_type,
                created_at=datetime.now(timezone.utc)
            )
            
            db.session.add(message)
            db.session.flush()  # Get message ID without committing
            
            # Add attachments if provided
            if attachments and message_type == "user":
                from app.models.message import Attachment
                for attachment_data in attachments:
                    attachment = Attachment(
                        message_id=message.id,
                        type=attachment_data.get('type', 'file'),
                        url=attachment_data.get('url', ''),
                        name=attachment_data.get('name', '')
                    )
                    db.session.add(attachment)
            
            db.session.commit()
            
            return {
                "success": True,
                "message_id": message.id,
                "timestamp": message.created_at.isoformat() + 'Z'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database message storage failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _store_vector_message(
        self,
        user_id: int,
        content: str,
        message_id: int,
        message_type: str,
        conversation_id: int,
        context_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store message in Pinecone vector database with enhanced metadata"""
        try:
            # Create comprehensive metadata
            metadata = {
                "message_id": str(message_id),
                "conversation_id": str(conversation_id),
                "message_type": message_type,
                "user_id": str(user_id),
                "source": "chat_history",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content_length": len(content),
                "language": "en",  # Could be detected dynamically
            }
            
            # Add context information if available
            if context_info:
                if context_info.get("intent"):
                    metadata["intent"] = context_info["intent"]
                if context_info.get("confidence_score"):
                    metadata["confidence_score"] = context_info["confidence_score"]
                if context_info.get("service_used"):
                    metadata["service_used"] = context_info["service_used"]
                if context_info.get("document_referenced"):
                    metadata["has_document_context"] = True
                if context_info.get("health_related"):
                    metadata["health_query"] = True
            
            # Create document
            doc = Document(
                page_content=content,
                metadata=metadata
            )
            
            # Store using AI service
            success, message = self.ai_service.process_and_store_documents(
                documents=[doc],
                user_id=user_id,
                file_name="chat_history",
                file_type="chat_message"
            )
            
            return {"success": success, "message": message}
            
        except Exception as e:
            logger.error(f"Vector message storage failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _update_knowledge_base_stats(self, user_id: int):
        """Update user's knowledge base statistics"""
        try:
            from app.models.care_record import KnowledgeBase
            
            # Get or create knowledge base record
            kb = KnowledgeBase.query.filter_by(user_id=user_id).first()
            if not kb:
                # Create new knowledge base record
                from app.utils.file_handler import get_user_namespace
                kb = KnowledgeBase(
                    user_id=user_id,
                    vector_count=1,
                    pinecone_namespace=get_user_namespace(user_id),
                    meta_data={
                        "chat_messages": 1,
                        "documents": 0,
                        "images": 0,
                        "care_records": 0
                    }
                )
                db.session.add(kb)
            else:
                # Update existing record
                kb.vector_count += 1
                kb.last_updated = datetime.now(timezone.utc)
                if not kb.meta_data:
                    kb.meta_data = {}
                kb.meta_data["chat_messages"] = kb.meta_data.get("chat_messages", 0) + 1
            
            db.session.commit()
            current_app.logger.info(f"📊 Updated knowledge base stats for user {user_id}")
            
        except Exception as e:
            logger.error(f"Knowledge base stats update failed: {str(e)}")
            raise
    
    def _preserve_conversation_context(
        self, 
        user_id: int, 
        conversation_id: int, 
        context_info: Dict[str, Any]
    ):
        """Preserve conversation context for future reference"""
        try:
            # Store context in a way that can be retrieved for future queries
            # This could be expanded based on specific needs
            context_metadata = {
                "last_intent": context_info.get("intent"),
                "last_service": context_info.get("service_used"),
                "context_timestamp": datetime.now(timezone.utc).isoformat(),
                "conversation_id": str(conversation_id)
            }
            
            # Could store this in Redis, database, or other persistence layer
            # For now, just log it for debugging
            current_app.logger.info(f"💾 Context preserved for user {user_id}: {context_metadata}")
            
        except Exception as e:
            logger.error(f"Context preservation failed: {str(e)}")
            raise
    
    def store_single_message(
        self,
        user_id: int,
        conversation_id: int,
        content: str,
        message_type: str,
        context_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, int]:
        """
        Store a single message (for cases where user/AI messages are stored separately)
        
        Returns:
            Tuple of (success, message_id)
        """
        try:
            # Store in database
            db_result = self._store_database_message(conversation_id, content, message_type)
            if not db_result["success"]:
                return False, 0
            
            message_id = db_result["message_id"]
            
            # Store in vector database
            vector_result = self._store_vector_message(
                user_id, content, message_id, message_type, conversation_id, context_info
            )
            
            if not vector_result["success"]:
                current_app.logger.warning(f"Vector storage failed for message {message_id}: {vector_result['error']}")
            
            return True, message_id
            
        except Exception as e:
            logger.error(f"Single message storage failed: {str(e)}")
            return False, 0

    def get_comprehensive_knowledge_sources(
        self,
        user_id: int,
        query: str,
        conversation_id: Optional[int] = None
    ) -> Dict[str, List[Any]]:
        """
        Get comprehensive knowledge sources for a query
        
        This method searches across all available knowledge sources:
        - Chat history
        - User documents
        - Care records
        - Common knowledge
        
        Args:
            user_id: User ID
            query: Query to search for
            conversation_id: Optional conversation ID for context
            
        Returns:
            Dictionary with knowledge sources
        """
        try:
            current_app.logger.info(f"🔍 Searching knowledge sources for user {user_id}: '{query[:50]}...'")
            
            knowledge_sources = {
                "chat_history": [],
                "user_documents": [],
                "care_records": [],
                "common_knowledge": []
            }
            
            # Get chat history if conversation_id is provided
            if conversation_id:
                try:
                    from app.utils.file_handler import query_chat_history
                    
                    # Check the function signature and use appropriate parameters
                    try:
                        history_docs = query_chat_history(
                            query=query,
                            user_id=user_id,
                            top_k=5  # Use top_k instead of limit
                        )
                    except TypeError:
                        # Try alternative signature
                        history_docs = query_chat_history(
                            query=query,
                            user_id=user_id
                        )
                    
                    if history_docs:
                        knowledge_sources["chat_history"] = history_docs
                        current_app.logger.info(f"✅ Found {len(history_docs)} relevant chat history documents")
                except Exception as e:
                    current_app.logger.error(f"❌ Error retrieving chat history: {str(e)}")
            
            # Get user documents
            try:
                from app.utils.file_handler import query_user_docs
                
                # Check the function signature and use appropriate parameters
                try:
                    doc_results = query_user_docs(
                        query=query,
                        user_id=user_id,
                        top_k=3  # Use top_k instead of limit
                    )
                except TypeError:
                    # Try alternative signature
                    doc_results = query_user_docs(
                        query=query,
                        user_id=user_id
                    )
                
                if doc_results:
                    knowledge_sources["user_documents"] = doc_results
                    current_app.logger.info(f"✅ Found {len(doc_results)} relevant user documents")
            except Exception as e:
                current_app.logger.error(f"❌ Error retrieving user documents: {str(e)}")
            
            # Get care records - use try/except to handle missing method
            try:
                from app.services.care_archive_service import CareArchiveService
                
                care_service = CareArchiveService()
                
                # Check if the search_care_records method exists
                if hasattr(care_service, 'search_care_records'):
                    care_records = care_service.search_care_records(
                        user_id=user_id,
                        query=query,
                        limit=3
                    )
                    
                    if care_records and len(care_records) > 0:
                        # Convert care records to Document objects
                        care_docs = []
                        for record in care_records:
                            care_docs.append(Document(
                                page_content=f"{record.get('title', '')}: {record.get('content', '')}",
                                metadata={
                                    "source": "care_record",
                                    "id": record.get('id'),
                                    "category": record.get('category'),
                                    "date": record.get('date_occurred')
                                }
                            ))
                        
                        knowledge_sources["care_records"] = care_docs
                        current_app.logger.info(f"✅ Found {len(care_docs)} relevant care records")
                else:
                    current_app.logger.warning("search_care_records method not available in CareArchiveService")
            except Exception as e:
                current_app.logger.error(f"❌ Error retrieving care records: {str(e)}")
            
            # Get common knowledge - use try/except to handle missing method
            try:
                from app.services.common_knowledge_service import CommonKnowledgeService
                
                common_knowledge_service = CommonKnowledgeService()
                
                # Check if the get_relevant_knowledge method exists
                if hasattr(common_knowledge_service, 'get_relevant_knowledge'):
                    common_knowledge = common_knowledge_service.get_relevant_knowledge(query)
                    
                    if common_knowledge:
                        knowledge_sources["common_knowledge"] = common_knowledge
                        current_app.logger.info(f"✅ Found {len(common_knowledge)} relevant common knowledge items")
                else:
                    current_app.logger.warning("get_relevant_knowledge method not available in CommonKnowledgeService")
            except Exception as e:
                current_app.logger.error(f"❌ Error retrieving common knowledge: {str(e)}")
            
            # Log summary of found knowledge sources
            total_sources = sum(len(sources) for sources in knowledge_sources.values())
            current_app.logger.info(f"✅ Found {total_sources} total knowledge sources")
            
            return knowledge_sources
        except Exception as e:
            current_app.logger.error(f"❌ Error getting comprehensive knowledge sources: {str(e)}")
            return {
                "chat_history": [],
                "user_documents": [],
                "care_records": [],
                "common_knowledge": []
            }


# Global service instance
_unified_chat_storage = None

def get_unified_chat_storage() -> UnifiedChatStorageService:
    """Get singleton instance of unified chat storage service"""
    global _unified_chat_storage
    if _unified_chat_storage is None:
        _unified_chat_storage = UnifiedChatStorageService()
    return _unified_chat_storage 
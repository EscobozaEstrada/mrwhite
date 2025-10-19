#!/usr/bin/env python3
"""
Conversation Context Manager
Tracks and manages conversation context, particularly for document-related queries
"""

import os
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
import json
from flask import current_app

class ConversationContextManager:
    """
    Manages conversation context across interactions
    Particularly focused on tracking document context for follow-up questions
    """
    
    def __init__(self):
        self._conversation_contexts = {}  # Stores context by conversation_id
        self._document_contexts = {}      # Stores document context by conversation_id
        self._intent_history = {}         # Stores detected intents by conversation_id
        
    def register_document_upload(self, 
                               user_id: int, 
                               conversation_id: int, 
                               document_names: List[str],
                               document_metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Register that documents were uploaded in a conversation
        This establishes document context for future queries
        """
        context_key = f"{user_id}_{conversation_id}"
        
        # Create or update document context
        if context_key not in self._document_contexts:
            self._document_contexts[context_key] = {
                "has_documents": True,
                "document_names": document_names,
                "last_document_interaction": datetime.now(timezone.utc),
                "document_metadata": document_metadata or {},
                "document_queries": [],
                "document_topics": set()
            }
        else:
            # Update existing context
            self._document_contexts[context_key]["has_documents"] = True
            self._document_contexts[context_key]["document_names"] = document_names
            self._document_contexts[context_key]["last_document_interaction"] = datetime.now(timezone.utc)
            if document_metadata:
                self._document_contexts[context_key]["document_metadata"].update(document_metadata)
        
        current_app.logger.info(f"Registered document upload for conversation {conversation_id}: {document_names}")
    
    def register_document_query(self, 
                              user_id: int, 
                              conversation_id: int, 
                              query: str,
                              query_type: str = "general") -> None:
        """
        Register that a document-related query was made
        This helps track the conversation's document context
        """
        context_key = f"{user_id}_{conversation_id}"
        
        # Ensure document context exists
        if context_key not in self._document_contexts:
            self._document_contexts[context_key] = {
                "has_documents": True,  # Assume documents exist if a query is made
                "document_names": [],
                "last_document_interaction": datetime.now(timezone.utc),
                "document_metadata": {},
                "document_queries": [],
                "document_topics": set()
            }
        
        # Update document context
        self._document_contexts[context_key]["last_document_interaction"] = datetime.now(timezone.utc)
        self._document_contexts[context_key]["document_queries"].append({
            "query": query,
            "timestamp": datetime.now(timezone.utc),
            "query_type": query_type
        })
        
        # Extract potential topics from the query
        topics = self._extract_topics_from_query(query)
        if topics:
            self._document_contexts[context_key]["document_topics"].update(topics)
        
        current_app.logger.info(f"Registered document query for conversation {conversation_id}: {query}")
    
    def has_document_context(self, user_id: int, conversation_id: int) -> bool:
        """Check if the conversation has document context"""
        context_key = f"{user_id}_{conversation_id}"
        return context_key in self._document_contexts and self._document_contexts[context_key]["has_documents"]
    
    def get_document_context(self, user_id: int, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Get document context for a conversation"""
        context_key = f"{user_id}_{conversation_id}"
        if context_key in self._document_contexts:
            context = self._document_contexts[context_key].copy()
            # Convert set to list for JSON serialization
            if "document_topics" in context and isinstance(context["document_topics"], set):
                context["document_topics"] = list(context["document_topics"])
            return context
        return None
    
    def is_document_query(self, 
                        user_id: int, 
                        conversation_id: int, 
                        query: str, 
                        conversation_history: Optional[List[Dict]] = None) -> bool:
        """
        Determine if a query is related to documents
        Uses a combination of keyword detection, conversation context, and intent recognition
        """
        query_lower = query.lower()
        
        # 1. Direct document keyword detection
        doc_keywords = [
            "document", "file", "pdf", "summarize", "summary", "what's in", "what is in", 
            "tell me about", "extract from", "information in", "content of", "uploaded",
            "what do my files say", "what's in my documents", "analyze my files"
        ]
        if any(keyword in query_lower for keyword in doc_keywords):
            return True
        
        # 2. Check if we have document context for this conversation
        if self.has_document_context(user_id, conversation_id):
            # 3. Check for entity questions that might be follow-ups about documents
            entity_patterns = [
                "who", "what", "when", "where", "why", "how", 
                "is there", "are there", "does it", "do they", 
                "find", "search", "look for", "show me"
            ]
            
            if any(pattern in query_lower for pattern in entity_patterns):
                # This is likely a follow-up question if we have document context
                context = self.get_document_context(user_id, conversation_id)
                
                # If we've had recent document interactions, treat as document query
                if context and "last_document_interaction" in context:
                    last_interaction = context["last_document_interaction"]
                    # If document interaction was within the last 10 messages or 30 minutes
                    if isinstance(last_interaction, datetime):
                        now = datetime.now(timezone.utc)
                        minutes_since_interaction = (now - last_interaction).total_seconds() / 60
                        if minutes_since_interaction < 30:  # Within 30 minutes
                            return True
            
            # 4. Check for topic overlap with previous document queries
            context = self.get_document_context(user_id, conversation_id)
            if context and "document_topics" in context:
                topics = self._extract_topics_from_query(query)
                if topics and context["document_topics"]:
                    # If there's topic overlap with previous document queries
                    if any(topic in context["document_topics"] for topic in topics):
                        return True
        
        # 5. Check conversation history for document context
        if conversation_history:
            # Look for document references in recent messages
            doc_context_keywords = ["document", "file", "pdf", "uploaded"]
            recent_messages = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
            
            for msg in recent_messages:
                if msg['type'] == 'ai' and any(keyword in msg['content'].lower() for keyword in doc_context_keywords):
                    # If previous AI message mentioned documents, this is likely a follow-up
                    return True
        
        return False
    
    def update_thread_session_data(self, 
                                 user_id: int, 
                                 conversation_id: int, 
                                 thread_id: str) -> None:
        """
        Update thread session data with document context
        This allows the thread memory to be aware of document context
        """
        from app.agents.agent_manager import get_agent_manager
        
        try:
            agent_manager = get_agent_manager()
            thread_data = agent_manager.get_thread_memory(thread_id)
            
            if thread_data and "session_data" in thread_data:
                # Get document context
                document_context = self.get_document_context(user_id, conversation_id)
                
                if document_context:
                    # Update session data with document context
                    thread_data["session_data"]["document_context"] = {
                        "has_documents": document_context.get("has_documents", False),
                        "document_names": document_context.get("document_names", []),
                        "last_interaction": datetime.now(timezone.utc).isoformat(),
                        "topics": list(document_context.get("document_topics", [])),
                    }
                    
                    current_app.logger.info(f"Updated thread {thread_id} with document context")
        except Exception as e:
            current_app.logger.error(f"Error updating thread session data: {str(e)}")
    
    def _extract_topics_from_query(self, query: str) -> Set[str]:
        """Extract potential topics from a query"""
        # Simple implementation - extract nouns and important words
        # In a production system, this would use NLP for better extraction
        words = query.lower().split()
        # Remove common stop words
        stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "with", "by", "about", "like", "through", "over", "before", "between", "after", "since", "without", "under", "within", "along", "following", "across", "behind", "beyond", "plus", "except", "but", "up", "down", "off", "on"}
        filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
        return set(filtered_words)


# Global instance
_context_manager = None

def get_context_manager() -> ConversationContextManager:
    """Get or create the global context manager instance"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ConversationContextManager()
    return _context_manager 
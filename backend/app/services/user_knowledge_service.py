"""
User Knowledge Service
Connects user's personal knowledge base (comments and notes) to the chatbot
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from flask import current_app

from app.services.pinecone_integration_service import PineconeBookNotesService

logger = logging.getLogger(__name__)

class UserKnowledgeService:
    """Service for accessing and formatting user's personal knowledge base"""
    
    def __init__(self):
        self.pinecone_service = PineconeBookNotesService()
    
    def search_user_knowledge(self, user_id: int, query: str, top_k: int = 5) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Search user's personal knowledge base for relevant notes and comments
        
        Args:
            user_id: User ID
            query: Search query
            top_k: Number of results to return
            
        Returns:
            Tuple of (success, results)
        """
        try:
            search_result = self.pinecone_service.search_user_knowledge_base(
                user_id=user_id,
                query=query,
                top_k=top_k
            )
            
            if not search_result.get('success', False):
                logger.warning(f"User knowledge search failed: {search_result.get('message', 'Unknown error')}")
                return False, []
            
            # Extract and format results
            matches = search_result.get('results', {}).get('matches', [])
            formatted_results = []
            
            for match in matches:
                # Extract metadata
                metadata = match.get('metadata', {})
                text = metadata.get('text', '')
                
                # Format result
                formatted_result = {
                    'content': text,
                    'score': match.get('score', 0),
                    'page_number': metadata.get('page_number', 0),
                    'note_type': metadata.get('note_type', 'note'),
                    'color': metadata.get('color', 'yellow'),
                    'book_title': metadata.get('book_title', ''),
                    'content_type': metadata.get('content_type', 'book_note')
                }
                
                formatted_results.append(formatted_result)
            
            logger.info(f"Found {len(formatted_results)} user knowledge results for query: '{query}'")
            return True, formatted_results
            
        except Exception as e:
            logger.error(f"Error searching user knowledge: {str(e)}")
            return False, []
    
    def get_user_knowledge_context(self, user_id: int, query: str, top_k: int = 3) -> str:
        """
        Get user knowledge context for a query
        
        Args:
            user_id: User ID
            query: Search query
            top_k: Number of results to include
            
        Returns:
            Formatted string with user knowledge context
        """
        success, results = self.search_user_knowledge(user_id, query, top_k)
        
        if not success or not results:
            return ""
        
        # Format results into a context string
        context_parts = []
        
        for i, result in enumerate(results):
            content_type = result.get('content_type', 'note')
            icon = "🖍️" if content_type == "book_highlight" else "📝"
            
            context_part = f"{icon} **User {content_type}** (Page {result.get('page_number', 0)}):\n"
            context_part += f"{result.get('content', '')}\n\n"
            
            context_parts.append(context_part)
        
        if context_parts:
            return "USER'S PERSONAL NOTES AND COMMENTS:\n\n" + "\n".join(context_parts)
        
        return ""

# Singleton pattern
_user_knowledge_service = None

def get_user_knowledge_service() -> UserKnowledgeService:
    """Get or create user knowledge service instance"""
    global _user_knowledge_service
    if _user_knowledge_service is None:
        _user_knowledge_service = UserKnowledgeService()
    return _user_knowledge_service 
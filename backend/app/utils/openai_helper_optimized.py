from typing import List, Dict, Optional
from flask import current_app
from app.services.ai_service import AIService
from app.utils.cache import cached, performance_monitor
import os

# Global AI service instance
ai_service = AIService()


@cached(ttl=600, key_prefix="mr_white_response")
@performance_monitor
def get_mr_white_response(message: str, context: str = "chat", 
                         conversation_history: Optional[List[Dict]] = None) -> str:
    """
    Optimized Mr. White response generation using AIService
    
    Args:
        message: User message
        context: Context type (chat, file_upload, etc.)
        conversation_history: Previous conversation messages
        
    Returns:
        AI response string
    """
    try:
        current_app.logger.info(f"Generating response for context: {context}")
        
        # Determine response type based on context
        response_type_mapping = {
            "chat": "standard",
            "file_upload": "file_upload", 
            "document_query": "document_analysis",
            "summary": "summary"
        }
        
        response_type = response_type_mapping.get(context, "standard")
        
        # Use AIService for optimized response generation
        response = ai_service.generate_chat_response(
            query=message,
            context_docs=None,  # AIService will handle document retrieval internally
            conversation_history=conversation_history,
            response_type=response_type
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error in get_mr_white_response: {str(e)}")
        return "I apologize, but I'm having trouble processing your request at the moment. Please try again."


@performance_monitor
def get_smart_response_with_context(user_id: int, message: str, 
                                  conversation_history: Optional[List[Dict]] = None) -> str:
    """
    Get smart response with automatic context detection and document retrieval
    
    Args:
        user_id: User ID for document retrieval
        message: User message
        conversation_history: Previous conversation messages
        
    Returns:
        AI response string
    """
    try:
        # Use AIService smart response with automatic document retrieval
        response = ai_service.get_smart_response(
            user_id=user_id,
            query=message,
            conversation_history=conversation_history
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error in get_smart_response_with_context: {str(e)}")
        return "I apologize, but I encountered an error processing your request. Please try again."


@cached(ttl=1800, key_prefix="document_response")  
def get_document_based_response(user_id: int, query: str, 
                               conversation_history: Optional[List[Dict]] = None) -> str:
    """
    Generate response specifically based on user's uploaded documents
    
    Args:
        user_id: User ID for document retrieval
        query: User query
        conversation_history: Previous conversation messages
        
    Returns:
        AI response string based on documents
    """
    try:
        # Search user documents
        success, documents = ai_service.search_user_documents(
            query=query,
            user_id=user_id,
            top_k=5,
            similarity_threshold=0.7
        )
        
        if not success or not documents:
            return "I couldn't find any relevant information in your uploaded documents for this query. Please make sure you have uploaded documents or try rephrasing your question."
        
        # Generate response based on documents
        response = ai_service.generate_chat_response(
            query=query,
            context_docs=documents,
            conversation_history=conversation_history,
            response_type="document_analysis"
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error in get_document_based_response: {str(e)}")
        return "I encountered an error while searching your documents. Please try again."


def get_file_upload_response(file_names: List[str], file_types: List[str], 
                           user_message: str = "") -> str:
    """
    Generate specialized response for file uploads
    
    Args:
        file_names: List of uploaded file names
        file_types: List of file types
        user_message: Optional user message with files
        
    Returns:
        AI response for file upload
    """
    try:
        # Create context about uploaded files
        files_info = []
        for name, ftype in zip(file_names, file_types):
            files_info.append(f"{name} ({ftype})")
        
        files_context = f"User has uploaded {len(file_names)} file(s): {', '.join(files_info)}"
        
        # Enhanced message for file upload context
        enhanced_message = f"{user_message}\n\nFiles uploaded: {files_context}" if user_message else files_context
        
        # Generate file upload response
        response = ai_service.generate_chat_response(
            query=enhanced_message,
            context_docs=None,
            conversation_history=None,
            response_type="file_upload"
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error in get_file_upload_response: {str(e)}")
        return f"I've received your {len(file_names)} file(s) and they're being processed. You'll be able to ask questions about them shortly."


@cached(ttl=3600, key_prefix="summary_response")
def generate_summary_response(user_id: int, query: str) -> str:
    """
    Generate summary of user's documents based on query
    
    Args:
        user_id: User ID for document retrieval
        query: Summary query
        
    Returns:
        Summary response
    """
    try:
        # Search for relevant documents with higher top_k for summaries
        success, documents = ai_service.search_user_documents(
            query=query,
            user_id=user_id,
            top_k=10,  # More documents for comprehensive summary
            similarity_threshold=0.6  # Lower threshold for broader coverage
        )
        
        if not success or not documents:
            return "I couldn't find any relevant documents to summarize based on your query."
        
        # Generate summary response
        summary_query = f"Create a comprehensive summary based on the following query: {query}"
        
        response = ai_service.generate_chat_response(
            query=summary_query,
            context_docs=documents,
            conversation_history=None,
            response_type="summary"
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error in generate_summary_response: {str(e)}")
        return "I encountered an error while generating the summary. Please try again."


def get_conversation_context_response(user_id: int, query: str, 
                                    conversation_history: List[Dict]) -> str:
    """
    Generate response with both document and conversation context
    
    Args:
        user_id: User ID
        query: User query
        conversation_history: Previous conversation messages
        
    Returns:
        Context-aware AI response
    """
    try:
        # Search both documents and chat history
        doc_success, documents = ai_service.search_user_documents(query, user_id, top_k=3)
        chat_docs = ai_service.search_chat_history(query, user_id, top_k=3)
        
        # Combine all context
        all_context_docs = []
        if doc_success:
            all_context_docs.extend(documents)
        all_context_docs.extend(chat_docs)
        
        # Generate response with full context
        response = ai_service.generate_chat_response(
            query=query,
            context_docs=all_context_docs if all_context_docs else None,
            conversation_history=conversation_history,
            response_type="document_analysis" if all_context_docs else "standard"
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error in get_conversation_context_response: {str(e)}")
        return "I apologize, but I encountered an error processing your request. Please try again."


def get_ai_service_status() -> dict:
    """Get status information about the AI service"""
    try:
        return {
            "status": "operational",
            "embedding_model": current_app.config.get('OPENAI_EMBEDDING_MODEL'),
            "chat_model": current_app.config.get('OPENAI_CHAT_MODEL'),
            "pinecone_index": os.getenv("PINECONE_INDEX_NAME"),
            "performance_metrics": ai_service.get_performance_metrics() if hasattr(ai_service, 'get_performance_metrics') else {}
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Backward compatibility
def get_mr_white_response_legacy(message: str, context: str = "chat", 
                                conversation_history: Optional[List[Dict]] = None) -> str:
    """Legacy function for backward compatibility"""
    return get_mr_white_response(message, context, conversation_history) 
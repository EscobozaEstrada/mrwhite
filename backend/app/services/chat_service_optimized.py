from typing import Optional, List, Dict, Any, Tuple
import os
from flask import current_app
from werkzeug.datastructures import FileStorage
from app.models.user import User
from app.services.ai_service import AIService
from app.services.file_service import FileService
from app.utils.cache import performance_monitor, cached
from app.utils.file_handler_optimized import extract_and_store

# Global AI service instance
ai_service = AIService()


class OptimizedChatService:
    """Optimized service class for handling AI chat operations with enhanced performance"""
    
    @staticmethod
    @performance_monitor
    def process_chat_message(user_id: int, message: str, context: str = "chat", 
                           conversation_history: Optional[List[Dict]] = None,
                           files: Optional[List[FileStorage]] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Optimized chat message processing with AI response generation
        
        Returns:
            Tuple of (success: bool, error_message: str, response_data: Optional[Dict])
        """
        try:
            current_app.logger.info(f"Processing chat message for user {user_id}, context: {context}")
            
            # Set user context for AI tools
            os.environ["CURRENT_USER_ID"] = str(user_id)
            
            # Process files if any
            processed_files = []
            file_processing_results = []
            processed_documents = []
            
            if files:
                success, processed_files, processed_documents, file_processing_results = OptimizedChatService._process_uploaded_files(files, user_id)
                if not success and context == "file_upload":
                    return False, "Error processing files", {"details": file_processing_results}
            
            # Generate optimized AI response
            ai_reply = OptimizedChatService._generate_optimized_ai_response(
                user_id=user_id,
                message=message,
                context=context,
                conversation_history=conversation_history or [],
                processed_files=processed_files,
                processed_documents=processed_documents
            )
            
            return True, "Success", {
                "response": ai_reply,
                "processed_files": processed_files,
                "file_processing_results": file_processing_results,
                "context_used": context,
                "performance_optimized": True
            }
            
        except Exception as e:
            current_app.logger.error(f"Error processing chat message: {str(e)}")
            return False, f"Error generating AI response: {str(e)}", None
    
    @staticmethod
    @performance_monitor
    def _process_uploaded_files(files: List[FileStorage], user_id: int) -> Tuple[bool, List[Dict], List[str], List[str]]:
        """
        Optimized file processing with enhanced error handling
        
        Returns:
            Tuple of (success: bool, processed_files: List[Dict], processed_documents: List[str], processing_results: List[str])
        """
        processed_files = []
        file_processing_results = []
        processed_documents = []
        all_files_processed_successfully = True
        
        current_app.logger.info(f"Processing {len(files)} files for user {user_id}")
        
        for file in files:
            if not file.filename:
                continue
            
            # Validate file before processing
            is_allowed, file_category = FileService.is_allowed_file(file.filename)
            if not is_allowed:
                error_msg = f"File type not allowed: {file.filename}"
                file_processing_results.append(error_msg)
                all_files_processed_successfully = False
                continue
                
            try:
                if file_category == 'images':
                    # Handle image files with FileService
                    result = FileService.process_image_file(file)
                    if result['success']:
                        processed_files.append({
                            'type': 'image',
                            'name': file.filename,
                            'url': result['url']
                        })
                        file_processing_results.append(result['message'])
                    else:
                        all_files_processed_successfully = False
                        file_processing_results.append(result['message'])
                        
                elif file_category == 'documents':
                    # Handle document files with optimized processing
                    success, message, s3_url = extract_and_store(file, user_id)
                    file_processing_results.append(message)
                    
                    if success:
                        processed_files.append({
                            'type': 'file',
                            'name': file.filename,
                            'url': s3_url if s3_url else f"/uploads/{file.filename}"
                        })
                        processed_documents.append(file.filename)
                    else:
                        all_files_processed_successfully = False
                        
                else:
                    # Handle other file types
                    error_msg = f"Unsupported file category: {file_category} for {file.filename}"
                    file_processing_results.append(error_msg)
                    all_files_processed_successfully = False
                        
            except Exception as e:
                all_files_processed_successfully = False
                error_msg = f"Error processing {file.filename}: {str(e)}"
                file_processing_results.append(error_msg)
                current_app.logger.error(error_msg)
        
        current_app.logger.info(f"File processing completed: {len(processed_files)} successful, {len(processed_documents)} documents")
        return all_files_processed_successfully, processed_files, processed_documents, file_processing_results
    
    @staticmethod
    @cached(ttl=300, key_prefix="optimized_ai_response")
    def _generate_optimized_ai_response(user_id: int, message: str, context: str,
                                      conversation_history: List[Dict], 
                                      processed_files: Optional[List[Dict]] = None,
                                      processed_documents: Optional[List[str]] = None) -> str:
        """
        Generate optimized AI response using AIService with smart context detection
        
        Returns:
            AI response string
        """
        try:
            current_app.logger.info(f"Generating optimized AI response for context: {context}")
            
            # Handle file upload responses with specialized logic
            if processed_files and context == "file_upload":
                return OptimizedChatService._handle_optimized_file_upload_response(
                    message, processed_documents, processed_files
                )
            
            # Use AIService smart response for optimal performance
            response = ai_service.get_smart_response(
                user_id=user_id,
                query=message,
                conversation_history=conversation_history
            )
            
            return response
                
        except Exception as e:
            current_app.logger.error(f"Error generating optimized AI response: {str(e)}")
            return "I apologize, but I encountered an error processing your request. Please try again."
    
    @staticmethod
    def _handle_optimized_file_upload_response(message: str, processed_documents: Optional[List[str]], 
                                             processed_files: List[Dict]) -> str:
        """Handle optimized file upload responses with rich context"""
        try:
            # Extract file types for smart response
            file_types = []
            file_names = []
            
            for file_info in processed_files:
                file_names.append(file_info['name'])
                if file_info['type'] not in file_types:
                    file_types.append(file_info['type'])
            
            # Generate specialized file upload response
            from app.utils.openai_helper_optimized import get_file_upload_response
            
            response = get_file_upload_response(
                file_names=file_names,
                file_types=file_types,
                user_message=message
            )
            
            return response
            
        except Exception as e:
            current_app.logger.error(f"Error handling file upload response: {str(e)}")
            # Fallback response
            file_count = len(processed_files) if processed_files else 0
            return f"I've successfully received and processed {file_count} file(s). They're now available in your knowledge base for questions and analysis."
    
    @staticmethod
    @cached(ttl=600, key_prefix="document_query")
    @performance_monitor
    def query_documents_optimized(user_id: int, query: str, top_k: int = 5, 
                                 include_similarity_scores: bool = False) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        Optimized document querying with enhanced results
        
        Returns:
            Tuple of (success: bool, message: str, documents: Optional[List[Dict]])
        """
        try:
            current_app.logger.info(f"Querying documents for user {user_id}: {query[:50]}...")
            
            # Use AIService for optimized search
            success, documents = ai_service.search_user_documents(
                query=query,
                user_id=user_id,
                top_k=top_k,
                similarity_threshold=0.7
            )
            
            if not success:
                return False, "Error querying documents", None
            
            if not documents:
                return True, "No relevant documents found", []
            
            # Convert documents to enhanced dictionaries
            doc_results = []
            for doc in documents:
                doc_dict = {
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'source': doc.metadata.get('source', 'Unknown'),
                    'file_type': doc.metadata.get('file_type', 'unknown'),
                    'processed_at': doc.metadata.get('processed_at'),
                    'content_preview': doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                }
                
                if include_similarity_scores:
                    # This would require modifications to AIService to return scores
                    doc_dict['similarity_score'] = "N/A"  # Placeholder
                
                doc_results.append(doc_dict)
            
            message = f"Found {len(doc_results)} relevant document(s)"
            return True, message, doc_results
            
        except Exception as e:
            current_app.logger.error(f"Error querying documents: {str(e)}")
            return False, "Internal server error", None
    
    @staticmethod
    @performance_monitor
    def generate_summary(user_id: int, query: str = "", file_names: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Generate optimized summary of user's documents
        
        Returns:
            Tuple of (success: bool, summary: str)
        """
        try:
            current_app.logger.info(f"Generating summary for user {user_id}")
            
            # Default query if none provided
            if not query:
                query = "Provide a comprehensive summary of all uploaded documents"
            
            # Use AIService for summary generation
            from app.utils.openai_helper_optimized import generate_summary_response
            
            summary = generate_summary_response(user_id, query)
            
            return True, summary
            
        except Exception as e:
            current_app.logger.error(f"Error generating summary: {str(e)}")
            return False, f"Error generating summary: {str(e)}"
    
    @staticmethod
    @performance_monitor
    def get_conversation_insights(user_id: int, conversation_history: List[Dict]) -> Dict[str, Any]:
        """
        Generate insights about the conversation using AI analysis
        
        Returns:
            Dictionary with conversation insights
        """
        try:
            if not conversation_history:
                return {"insights": "No conversation history available for analysis"}
            
            # Analyze conversation patterns
            user_messages = [msg for msg in conversation_history if msg.get('type') == 'user']
            ai_messages = [msg for msg in conversation_history if msg.get('type') == 'ai']
            
            # Generate insights using AIService
            insights_query = "Analyze this conversation and provide insights about the user's interests, frequently asked topics, and conversation patterns."
            
            # Use a subset of conversation for analysis to avoid token limits
            recent_messages = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            
            insights_response = ai_service.generate_chat_response(
                query=insights_query,
                conversation_history=recent_messages,
                response_type="summary"
            )
            
            return {
                "total_messages": len(conversation_history),
                "user_messages": len(user_messages),
                "ai_messages": len(ai_messages),
                "ai_insights": insights_response,
                "conversation_length": "short" if len(conversation_history) < 5 else "medium" if len(conversation_history) < 20 else "long"
            }
            
        except Exception as e:
            current_app.logger.error(f"Error generating conversation insights: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def get_performance_metrics() -> Dict[str, Any]:
        """Get performance metrics for the optimized chat service"""
        try:
            from app.utils.cache import cache
            
            return {
                "service_type": "OptimizedChatService",
                "ai_service_enabled": True,
                "cache_enabled": True,
                "cache_size": len(cache._cache),
                "performance_monitoring": True,
                "features": [
                    "Smart document retrieval",
                    "Optimized file processing", 
                    "Response caching",
                    "Performance monitoring",
                    "Conversation insights",
                    "Enhanced error handling"
                ]
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def clear_user_cache(user_id: int):
        """Clear all cached data for a specific user"""
        try:
            from app.utils.cache import invalidate_cache_pattern
            
            # Clear user-specific caches
            invalidate_cache_pattern(f"user_{user_id}")
            invalidate_cache_pattern(f"doc_search")
            invalidate_cache_pattern(f"optimized_ai_response")
            
            current_app.logger.info(f"Cleared cache for user {user_id}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error clearing user cache: {str(e)}")
            return False 
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from flask import current_app
import os
import tempfile
from dotenv import load_dotenv
from typing import Tuple, List, Optional
from .s3_handler import upload_file_to_s3, create_bucket_if_not_exists
from app.services.ai_service import AIService
from app.utils.cache import performance_monitor, cached

# Make sure environment variables are loaded
load_dotenv()

# Ensure S3 bucket exists
create_bucket_if_not_exists()

# Global AI service instance
ai_service = AIService()


@performance_monitor
def extract_and_store(file, user_id: int) -> Tuple[bool, str, Optional[str]]:
    """Optimized file processing and storage using AIService"""
    current_app.logger.info(f"Starting extraction for file: {file.filename} for user_id: {user_id}")
    
    # Create temporary file
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    file.save(temp_path)
    
    try:
        # Upload to S3 first
        content_type = getattr(file, 'content_type', None)
        s3_success, s3_message, s3_url = upload_file_to_s3(temp_path, file.filename, content_type)
        
        if not s3_success:
            current_app.logger.warning(f"S3 upload failed: {s3_message}")
            s3_url = f"/uploads/{file.filename}"
        else:
            current_app.logger.info(f"Successfully uploaded to S3: {s3_url}")
        
        # Determine file type and load documents
        file_extension = get_file_extension(file.filename)
        documents = load_documents_by_type(temp_path, file.filename, file_extension)
        
        if not documents:
            return False, f"No content could be extracted from {file.filename}", s3_url
        
        # Add S3 URL to metadata
        for doc in documents:
            doc.metadata["url"] = s3_url
        
        # Use AIService for optimized processing and storage
        success, message = ai_service.process_and_store_documents(
            documents=documents,
            user_id=user_id,
            file_name=file.filename,
            file_type=file_extension
        )
        
        return success, message, s3_url
        
    except Exception as e:
        current_app.logger.error(f"Error in extract_and_store: {str(e)}")
        return False, f"Error processing file: {str(e)}", s3_url
        
    finally:
        # Cleanup temporary files
        try:
            os.unlink(temp_path)
            os.rmdir(temp_dir)
        except Exception as e:
            current_app.logger.warning(f"Error cleaning up temp files: {str(e)}")


def get_file_extension(filename: str) -> str:
    """Extract file extension for processing optimization"""
    if not filename or '.' not in filename:
        return "unknown"
    return filename.lower().split('.')[-1]


def load_documents_by_type(file_path: str, filename: str, file_type: str) -> List[Document]:
    """Load documents based on file type with optimized loaders"""
    try:
        if file_type == 'pdf':
            current_app.logger.info(f"Loading PDF: {filename}")
            loader = PyPDFLoader(file_path)
            return loader.load()
            
        elif file_type == 'txt':
            current_app.logger.info(f"Loading TXT: {filename}")
            loader = TextLoader(file_path, encoding='utf-8')
            return loader.load()
            
        elif file_type in ['doc', 'docx']:
            current_app.logger.info(f"Loading DOC/DOCX: {filename}")
            # For now, treat as text - could add python-docx support later
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return [Document(page_content=content, metadata={"source": filename})]
            except UnicodeDecodeError:
                current_app.logger.warning(f"Could not decode {filename} as UTF-8")
                return []
                
        else:
            current_app.logger.warning(f"Unsupported file type: {file_type}")
            return []
            
    except Exception as e:
        current_app.logger.error(f"Error loading document {filename}: {str(e)}")
        return []


@cached(ttl=300, key_prefix="doc_query")
def query_user_docs(query: str, user_id: int, top_k: Optional[int] = None) -> Tuple[bool, List[Document]]:
    """Optimized document querying using AIService"""
    try:
        if top_k is None:
            top_k = current_app.config.get('VECTOR_SEARCH_TOP_K', 5)
        
        current_app.logger.info(f"Querying documents for user {user_id}: {query[:50]}...")
        
        # Use AIService for optimized search
        success, documents = ai_service.search_user_documents(
            query=query,
            user_id=user_id,
            top_k=top_k,
            similarity_threshold=0.7
        )
        
        if success:
            current_app.logger.info(f"Found {len(documents)} relevant documents")
            return True, documents
        else:
            current_app.logger.info("No documents found")
            return True, []
            
    except Exception as e:
        current_app.logger.error(f"Error querying documents: {str(e)}")
        return False, []


@performance_monitor
def store_chat_message(user_id: int, message_content: str, message_id: int, 
                      message_type: str, conversation_id: int) -> Tuple[bool, str]:
    """Store chat message using optimized AIService"""
    try:
        # Create document for chat storage
        doc = Document(
            page_content=message_content,
            metadata={
                "message_id": str(message_id),
                "conversation_id": str(conversation_id),
                "message_type": message_type,
                "user_id": str(user_id),
                "source": "chat_history",
                "timestamp": current_app._get_current_object().timestamp() if hasattr(current_app._get_current_object(), 'timestamp') else None
            }
        )
        
        # Use AIService to store in vector database
        success, message = ai_service.process_and_store_documents(
            documents=[doc],
            user_id=user_id,
            file_name="chat_history",
            file_type="chat"
        )
        
        return success, message
        
    except Exception as e:
        current_app.logger.error(f"Error storing chat message: {str(e)}")
        return False, f"Error storing message: {str(e)}"


@cached(ttl=300, key_prefix="chat_query")
def query_chat_history(query: str, user_id: int, top_k: Optional[int] = None) -> Tuple[bool, List[Document]]:
    """Query chat history using optimized AIService"""
    try:
        if top_k is None:
            top_k = current_app.config.get('VECTOR_SEARCH_TOP_K', 5)
        
        current_app.logger.info(f"Querying chat history for user {user_id}: {query[:50]}...")
        
        # Use AIService for chat history search
        documents = ai_service.search_chat_history(query, user_id, top_k)
        
        current_app.logger.info(f"Found {len(documents)} relevant chat messages")
        return True, documents
        
    except Exception as e:
        current_app.logger.error(f"Error querying chat history: {str(e)}")
        return False, []


def get_user_namespace(user_id: int) -> str:
    """Get user namespace for documents"""
    return ai_service.get_user_namespace(user_id, "docs")


def get_chat_namespace(user_id: int) -> str:
    """Get user namespace for chat history"""
    return ai_service.get_user_namespace(user_id, "chat")


@cached(ttl=3600, key_prefix="file_summary")
def generate_file_summary(file_content: str, file_name: str, query: str = "") -> str:
    """Generate AI-powered file summary using AIService"""
    try:
        # Create a document for summarization
        doc = Document(page_content=file_content, metadata={"source": file_name})
        
        # Use AIService to generate summary
        summary_query = f"Summarize the key points of this document"
        if query:
            summary_query += f" focusing on: {query}"
        
        response = ai_service.generate_chat_response(
            query=summary_query,
            context_docs=[doc],
            response_type="summary"
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error generating summary: {str(e)}")
        return f"Error generating summary for {file_name}"


def get_file_processing_stats(user_id: int) -> dict:
    """Get file processing statistics for a user"""
    try:
        # This would require implementing stats tracking
        # For now, return basic info
        return {
            "user_id": user_id,
            "total_files": "unknown",  # Would need to implement tracking
            "total_chunks": "unknown",  # Would need to implement tracking
            "last_processed": "unknown",  # Would need to implement tracking
            "ai_service_status": "operational"
        }
    except Exception as e:
        current_app.logger.error(f"Error getting file stats: {str(e)}")
        return {"error": str(e)}


# Backward compatibility functions
def get_user_namespace_legacy(user_id):
    """Legacy function for backward compatibility"""
    return get_user_namespace(user_id)


def get_chat_namespace_legacy(user_id):
    """Legacy function for backward compatibility"""
    return get_chat_namespace(user_id) 
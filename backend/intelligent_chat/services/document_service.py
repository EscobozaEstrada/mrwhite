"""
Document Service
Handles document upload, processing, chunking, and Pinecone storage
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import tempfile
import os

from sqlalchemy import text
from models.base import AsyncSessionLocal
from services.s3_service import S3Service
from services.text_extraction_service import TextExtractionService
from services.memory_service import MemoryService
from config.settings import settings

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for handling document uploads and processing"""
    
    def __init__(self):
        self.s3_service = S3Service()
        self.text_service = TextExtractionService()
        self.memory_service = MemoryService()
    
    def get_user_documents_namespace(self, user_id: int) -> str:
        """Get user-specific documents namespace for better isolation"""
        return f"user_{user_id}_docs"
    
    async def _get_user_dog_profiles(self, user_id: int) -> list:
        """Get user's dog profiles for personalized image analysis"""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT id, name, breed, age, date_of_birth, weight, gender, color, 
                               image_url, image_description, comprehensive_profile 
                        FROM ic_dog_profiles 
                        WHERE user_id = :user_id
                    """),
                    {"user_id": user_id}
                )
                
                dog_profiles = []
                for row in result:
                    profile = {
                        "id": row[0],
                        "name": row[1],
                        "breed": row[2],
                        "age": row[3],
                        "date_of_birth": str(row[4]) if row[4] else None,
                        "weight": float(row[5]) if row[5] else None,
                        "gender": row[6],
                        "color": row[7],
                        "image_url": row[8],
                        "image_description": row[9],
                        "additional_details": row[10].get("additionalDetails") if row[10] else None
                    }
                    dog_profiles.append(profile)
                
                logger.info(f"Retrieved {len(dog_profiles)} dog profiles for user {user_id}")
                return dog_profiles
                
        except Exception as e:
            logger.error(f"Failed to fetch dog profiles for user {user_id}: {str(e)}")
            return []
    
    async def upload_and_process_document(
        self,
        user_id: int,
        conversation_id: Optional[int],
        file_content: bytes,
        filename: str,
        content_type: str,
        dog_profile_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Upload document to S3, extract text, chunk it, and store in Pinecone
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            file_content: File bytes
            filename: Original filename
            content_type: MIME type
            
        Returns:
            Document metadata including status
        """
        doc_id = None
        temp_file_path = None
        
        try:
            # Determine file type
            file_ext = Path(filename).suffix.lower().lstrip('.')
            file_size = len(file_content)
            
            # Create document record first (status: pending)
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        INSERT INTO ic_documents 
                        (user_id, conversation_id, filename, file_type, file_size, 
                         mime_type, s3_key, s3_url, processing_status, created_at, uploaded_at,
                         is_vet_report, dog_profile_id)
                        VALUES (:user_id, :conversation_id, :filename, :file_type, :file_size,
                                :mime_type, '', '', 'pending', :now, :now,
                                :is_vet_report, :dog_profile_id)
                        RETURNING id
                    """),
                    {
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "filename": filename,
                        "file_type": file_ext,
                        "file_size": file_size,
                        "mime_type": content_type,
                        "is_vet_report": dog_profile_id is not None,
                        "dog_profile_id": dog_profile_id,
                        "now": datetime.utcnow()
                    }
                )
                doc_id = result.scalar_one()
                await session.commit()
            
            logger.info(f"Created document record {doc_id} for user {user_id}")
            
            # Upload to S3
            s3_key = f"intelligent-chat/documents/{user_id}/{conversation_id}/{doc_id}_{filename}"
            s3_url = await self.s3_service.upload_file(
                file_content=file_content,
                file_key=s3_key,
                content_type=content_type
            )
            
            logger.info(f"Uploaded document {doc_id} to S3: {s3_url}")
            
            # Update with S3 info and mark as processing
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text("""
                        UPDATE ic_documents 
                        SET s3_key = :s3_key, s3_url = :s3_url, 
                            processing_status = 'processing', updated_at = :now
                        WHERE id = :doc_id
                    """),
                    {"s3_key": s3_key, "s3_url": s3_url, "doc_id": doc_id, "now": datetime.utcnow()}
                )
                await session.commit()
            
            # Download to temp file for text extraction
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                tmp.write(file_content)
                temp_file_path = tmp.name
            
            # Get user's dog profiles for personalized image analysis
            dog_profiles = await self._get_user_dog_profiles(user_id)
            
            # Extract text with personalized context for images
            extracted_text, error_msg = await self.text_service.extract_text_from_file(
                temp_file_path, file_ext, content_type, dog_profiles
            )
            
            if error_msg:
                # Mark as failed
                async with AsyncSessionLocal() as session:
                    await session.execute(
                        text("""
                            UPDATE ic_documents 
                            SET processing_status = 'failed', error_message = :error,
                                updated_at = :now
                            WHERE id = :doc_id
                        """),
                        {"error": error_msg, "doc_id": doc_id, "now": datetime.utcnow()}
                    )
                    await session.commit()
                
                return {
                    "id": doc_id,
                    "filename": filename,
                    "s3_url": s3_url,
                    "status": "failed",
                    "error": error_msg
                }
            
            # Store extracted text
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text("""
                        UPDATE ic_documents 
                        SET extracted_text = :text, updated_at = :now
                        WHERE id = :doc_id
                    """),
                    {"text": extracted_text, "doc_id": doc_id, "now": datetime.utcnow()}
                )
                await session.commit()
            
            logger.info(f"Extracted {len(extracted_text)} chars from document {doc_id}")
            
            # Chunk and store in Pinecone
            if extracted_text and len(extracted_text.strip()) > 0:
                chunks = self._chunk_text(extracted_text, filename)
                
                # Store in Pinecone using user-specific namespace for better isolation
                user_namespace = self.get_user_documents_namespace(user_id)
                pinecone_ids = []
                
                for i, chunk in enumerate(chunks):
                    metadata = {
                        "type": "document",
                        "document_id": str(doc_id),
                        "filename": filename,
                        "file_type": file_ext,
                        "s3_url": s3_url,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "user_id": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Only add conversation_id if it exists (don't set to None - Pinecone rejects null values)
                    if conversation_id:
                        metadata["conversation_id"] = str(conversation_id)
                    
                    if dog_profile_id:
                        metadata["dog_profile_id"] = dog_profile_id
                        metadata["is_vet_report"] = True
                    
                    vector_id = await self.memory_service.store_memory(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        content=chunk,
                        role="document",
                        metadata=metadata,
                        namespace=user_namespace
                    )
                    pinecone_ids.append(vector_id)
                
                # Update with Pinecone info
                async with AsyncSessionLocal() as session:
                    await session.execute(
                        text("""
                            UPDATE ic_documents 
                            SET chunk_count = :chunk_count,
                                pinecone_vectors_stored = true,
                                pinecone_ids = :pinecone_ids,
                                pinecone_namespace = :namespace,
                                processing_status = 'completed',
                                updated_at = :now
                            WHERE id = :doc_id
                        """),
                        {
                            "chunk_count": len(chunks),
                            "pinecone_ids": pinecone_ids,
                            "namespace": user_namespace,
                            "doc_id": doc_id,
                            "now": datetime.utcnow()
                        }
                    )
                    await session.commit()
                
                logger.info(f"Stored {len(chunks)} chunks in Pinecone for document {doc_id}")
            else:
                # No text extracted, mark as completed but empty
                async with AsyncSessionLocal() as session:
                    await session.execute(
                        text("""
                            UPDATE ic_documents 
                            SET processing_status = 'completed',
                                chunk_count = 0,
                                error_message = 'No text content found',
                                updated_at = :now
                            WHERE id = :doc_id
                        """),
                        {"doc_id": doc_id, "now": datetime.utcnow()}
                    )
                    await session.commit()
            
            return {
                "id": doc_id,
                "filename": filename,
                "file_type": file_ext,
                "file_size": file_size,
                "s3_url": s3_url,
                "status": "completed",
                "chunk_count": len(chunks) if extracted_text else 0
            }
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}", exc_info=True)
            
            # Mark as failed if we have doc_id
            if doc_id:
                try:
                    async with AsyncSessionLocal() as session:
                        await session.execute(
                            text("""
                                UPDATE ic_documents 
                                SET processing_status = 'failed',
                                    error_message = :error,
                                    updated_at = :now
                                WHERE id = :doc_id
                            """),
                            {"error": str(e), "doc_id": doc_id, "now": datetime.utcnow()}
                        )
                        await session.commit()
                except Exception as update_err:
                    logger.error(f"Failed to update error status: {update_err}")
            
            raise
        
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")
    
    def _chunk_text(self, text: str, filename: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to chunk
            filename: Original filename (for context)
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text or len(text.strip()) == 0:
            return []
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            
            # If this isn't the last chunk, try to break at a sentence or word
            if end < text_len:
                # Look for sentence break (. ! ?)
                for i in range(end, max(start + chunk_size // 2, end - 100), -1):
                    if text[i] in '.!?\n':
                        end = i + 1
                        break
                else:
                    # No sentence break, look for word break
                    for i in range(end, max(start + chunk_size // 2, end - 50), -1):
                        if text[i].isspace():
                            end = i
                            break
            
            chunk = text[start:end].strip()
            if chunk:
                # Add filename context to first chunk
                if start == 0:
                    chunk = f"[Document: {filename}]\n\n{chunk}"
                chunks.append(chunk)
            
            start = end - overlap if end < text_len else text_len
        
        return chunks
    
    async def link_document_to_message(self, message_id: int, document_id: int):
        """Link a document to a message"""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text("""
                        INSERT INTO ic_message_documents (message_id, document_id, created_at)
                        VALUES (:message_id, :document_id, :now)
                        ON CONFLICT (message_id, document_id) DO NOTHING
                    """),
                    {"message_id": message_id, "document_id": document_id, "now": datetime.utcnow()}
                )
                
                # Also update document's message_id
                await session.execute(
                    text("""
                        UPDATE ic_documents 
                        SET message_id = :message_id
                        WHERE id = :document_id
                    """),
                    {"message_id": message_id, "document_id": document_id}
                )
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to link document {document_id} to message {message_id}: {e}")
            raise
    
    async def get_message_documents(self, message_id: int) -> List[Dict[str, Any]]:
        """Get all documents linked to a message"""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT d.id, d.filename, d.file_type, d.file_size, 
                               d.s3_url, d.processing_status, d.chunk_count
                        FROM ic_documents d
                        JOIN ic_message_documents md ON d.id = md.document_id
                        WHERE md.message_id = :message_id
                        ORDER BY d.created_at
                    """),
                    {"message_id": message_id}
                )
                
                documents = []
                for row in result:
                    documents.append({
                        "id": row[0],
                        "filename": row[1],
                        "file_type": row[2],
                        "file_size": row[3],
                        "s3_url": row[4],
                        "status": row[5],
                        "chunk_count": row[6]
                    })
                
                return documents
                
        except Exception as e:
            logger.error(f"Failed to get documents for message {message_id}: {e}")
            return []








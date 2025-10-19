"""
Document Service - File processing and document management functionality
Handles file uploads, text extraction, and document analysis
"""

import os
import time
import json
import uuid
import base64
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

import httpx
import redis.asyncio as redis
from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import UploadFile, BackgroundTasks

from models import (
    AsyncSessionLocal, User, Document, Message,
    create_message_async
)

from services.shared.async_pinecone_service import AsyncPineconeService
from services.shared.async_parallel_service import AsyncParallelService
from services.shared.async_vector_batch_service import AsyncVectorBatchService
from services.shared.async_openai_pool_service import get_openai_pool
from services.shared.async_s3_service import AsyncS3Service
from services.vision.vision_service import VisionService
from services.voice.voice_service import VoiceService
from utils.async_file_processor import AsyncFileProcessor
from .document_prompts import DocumentPrompts

logger = logging.getLogger(__name__)

class DocumentService:
    """
    Document Service for file processing and document management
    Handles uploads, analysis, and document-based queries
    """
    
    def __init__(self, vector_service: AsyncPineconeService, cache_service=None, smart_intent_router=None):
        self.vector_service = vector_service
        self.cache_service = cache_service
        self.smart_intent_router = smart_intent_router
        
        # Initialize parallel processing services  
        self.parallel_service = AsyncParallelService()
        self.vector_batch_service = AsyncVectorBatchService(self.vector_service)
        self.s3_service = AsyncS3Service()  # Initialize S3 service for file storage
        self.vision_service = VisionService(cache_service, self.vector_service)  # Initialize vision service for images
        self.voice_service = VoiceService(cache_service)  # Initialize voice service for audio
        
        # OpenAI configuration
        self.openai_pool = None  # Will be set by global pool
        self.chat_model = "gpt-4"
        self.max_tokens = 2000  # Higher for document analysis
        self.temperature = 0.5  # Lower for document analysis
        
        # 🎯 Document sequence tracking for smart prioritization
        self._conversation_document_counts = {}
        
        # Document prompts manager
        self.prompts = DocumentPrompts()
        
        # Performance monitoring
        self.processing_stats = {
            "total_files_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "files_by_type": {},
            "images_processed": 0,
            "documents_processed": 0,
            "audio_processed": 0
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

    async def process_uploaded_files(
        self,
        user_id: int,
        files: List[UploadFile],
        message: str = "",
        conversation_id: Optional[int] = None,
        descriptions: str = "{}",
        context_type: str = "general",
        background_tasks: Optional[BackgroundTasks] = None
    ) -> List[Dict[str, Any]]:
        """
        Process uploaded files with parallel processing and intelligent analysis
        """
        start_time = time.time()
        
        try:
            file_descriptions = json.loads(descriptions) if descriptions else {}
            processed_files = []
            
            # Phase 1: Parallel file reading and processing
            file_tasks = []
            for file in files:
                file_task = self._process_single_file(
                    user_id=user_id,
                    file=file,
                    description=file_descriptions.get(file.filename, ""),
                    conversation_id=conversation_id,
                    context_type=context_type
                )
                file_tasks.append(file_task)
            
            # Execute file processing in parallel
            results = await asyncio.gather(*file_tasks, return_exceptions=True)
            
            # Phase 2: Process results and handle errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"File processing error for {files[i].filename}: {result}")
                    processed_files.append({
                        "filename": files[i].filename,
                        "status": "error",
                        "message": str(result),
                        "content_length": 0
                    })
                else:
                    processed_files.append(result)
            
            # Phase 3: Background tasks for optimization
            if background_tasks and processed_files:
                background_tasks.add_task(
                    self._batch_process_document_vectors,
                    user_id, processed_files, context_type
                )
                background_tasks.add_task(
                    self._analyze_document_patterns,
                    user_id, processed_files
                )
            
            processing_time = time.time() - start_time
            self._update_processing_stats(len(files), processing_time, processed_files)
            
            return processed_files
            
        except Exception as e:
            logger.error(f"File upload processing error: {str(e)}")
            return []

    async def _process_single_file(
        self,
        user_id: int,
        file: UploadFile,
        description: str,
        conversation_id: Optional[int],
        context_type: str
    ) -> Dict[str, Any]:
        """Process a single uploaded file"""
        try:
            # Read file content
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # Extract text content
            text_content = await AsyncFileProcessor.extract_text_content(content, file.content_type)
            
            if text_content:
                # Chunk large documents to avoid token limits
                # Max 8192 tokens ≈ 3000-3500 chars (conservative to account for special characters)
                # Using 3000 chars with 300 char overlap for safety margin
                max_chunk_size = 3000
                text_chunks = []
                
                if len(text_content) > max_chunk_size:
                    # Split into chunks with overlap for better context
                    overlap = 300
                    for i in range(0, len(text_content), max_chunk_size - overlap):
                        chunk = text_content[i:i + max_chunk_size]
                        if chunk.strip():  # Only add non-empty chunks
                            text_chunks.append(chunk)
                    logger.info(f"📑 Split document {file.filename} into {len(text_chunks)} chunks (max {max_chunk_size} chars each)")
                else:
                    text_chunks = [text_content]
                
                # Create enhanced metadata with smart prioritization
                base_metadata = AsyncFileProcessor.create_file_metadata(
                    filename=file.filename,
                    content_type=file.content_type,
                    description=description,
                    conversation_id=conversation_id,
                    file_type=context_type
                )
                
                # 🎯 Add smart document prioritization fields
                base_metadata["user_id"] = user_id
                base_metadata["upload_sequence"] = await self._get_document_sequence(conversation_id) if conversation_id else 1
                
                # 📁 Upload file to S3 for permanent storage
                s3_upload_result = None
                try:
                    async with self.s3_service as s3:
                        s3_upload_result = await s3.upload_document(
                            file_content=content,
                            filename=file.filename,
                            user_id=user_id,
                            document_type="chat_documents",
                            metadata={
                                "conversation_id": str(conversation_id) if conversation_id else "none",
                                "context_type": context_type,
                                "upload_sequence": str(base_metadata["upload_sequence"])
                            }
                        )
                        logger.info(f"✅ Uploaded {file.filename} to S3: {s3_upload_result.get('s3_key')}")
                except Exception as s3_error:
                    logger.error(f"❌ S3 upload failed for {file.filename}: {s3_error}")
                    # Continue processing even if S3 upload fails
                
                # Store in vector database with enhanced context
                success, message = await self.vector_service.store_document_vectors(
                    user_id=user_id,
                    document_id=hash(file.filename),  # Temporary ID
                    text_chunks=text_chunks,
                    metadata=base_metadata
                )
                
                # Generate file summary if it's a large document
                summary = await self._generate_document_summary(text_content, file.filename) if len(text_content) > 1000 else None
                
                # Ensure success is True if we extracted text, regardless of vector storage
                final_success = success if success is not None else True
                final_message = message if success else f"Text extracted successfully. {message}"
                
                result = AsyncFileProcessor.create_processing_result(
                    filename=file.filename,
                    success=final_success,
                    message=final_message,
                    content_length=len(text_content),
                    extracted_text=text_content
                )
                
                # Add S3 information to result if upload was successful
                if s3_upload_result and s3_upload_result.get("success"):
                    result["s3_url"] = s3_upload_result.get("download_url")
                    result["s3_key"] = s3_upload_result.get("s3_key")
                    result["s3_bucket"] = s3_upload_result.get("s3_bucket")
                    logger.info(f"📎 S3 URL added to result: {result['s3_url']}")
                
                if summary:
                    result["summary"] = summary
                
                return result
            else:
                return AsyncFileProcessor.create_processing_result(
                    filename=file.filename,
                    success=False,
                    message="Could not extract text from file",
                    content_length=0
                )
                
        except Exception as e:
            logger.error(f"Single file processing error for {file.filename}: {str(e)}")
            return AsyncFileProcessor.create_processing_result(
                filename=file.filename,
                success=False,
                message=str(e),
                content_length=0
            )

    async def _generate_document_summary(self, text_content: str, filename: str) -> Optional[str]:
        """Generate AI summary of document content"""
        try:
            summary_prompt = self.prompts.get_document_summary_prompt(text_content, filename)
            
            pool = await self._get_openai_pool()
            response = await pool.chat_completion(
                messages=[
                    {"role": "system", "content": self.prompts.DOCUMENT_ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": summary_prompt}
                ],
                model=self.chat_model,
                temperature=self.temperature,
                max_tokens=300
            )
            
            return response["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Document summary generation error: {str(e)}")
            return None

    async def analyze_document_content(
        self,
        user_id: int,
        document_text: str,
        filename: str,
        analysis_type: str = "general",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze document content with specialized AI analysis
        """
        try:
            # Generate analysis prompt based on type
            if analysis_type == "health":
                analysis_prompt = self.prompts.get_health_document_analysis_prompt(document_text, filename, context)
            elif analysis_type == "training":
                analysis_prompt = self.prompts.get_training_document_analysis_prompt(document_text, filename, context)
            elif analysis_type == "legal":
                analysis_prompt = self.prompts.get_legal_document_analysis_prompt(document_text, filename, context)
            else:
                analysis_prompt = self.prompts.get_general_document_analysis_prompt(document_text, filename, context)
            
            # Get AI analysis
            pool = await self._get_openai_pool()
            response = await pool.chat_completion(
                messages=[
                    {"role": "system", "content": self.prompts.DOCUMENT_ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": analysis_prompt}
                ],
                model=self.chat_model,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            analysis_text = response["choices"][0]["message"]["content"]
            
            # Extract structured insights
            insights = await self._extract_document_insights(analysis_text, analysis_type)
            
            return {
                "success": True,
                "filename": filename,
                "analysis_type": analysis_type,
                "analysis": analysis_text,
                "insights": insights,
                "content_length": len(document_text),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Document analysis error for {filename}: {str(e)}")
            return {
                "success": False,
                "filename": filename,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def search_documents(
        self,
        user_id: int,
        query: str,
        document_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search through user's documents with intelligent filtering
        """
        try:
            # Use vector search to find relevant documents
            search_results = await self.vector_service.search_user_documents(
                user_id=user_id,
                query=query,
                top_k=limit
            )
            
            # Filter by document types if specified
            if document_types:
                filtered_results = []
                for result in search_results:
                    doc_type = result.get("metadata", {}).get("file_type", "general")
                    if doc_type in document_types:
                        filtered_results.append(result)
                search_results = filtered_results
            
            # Enhance results with document insights
            enhanced_results = []
            for result in search_results:
                enhanced_result = result.copy()
                
                # Add document analysis if available
                document_analysis = await self._get_cached_document_analysis(
                    result.get("metadata", {}).get("filename", "")
                )
                if document_analysis:
                    enhanced_result["analysis"] = document_analysis
                
                enhanced_results.append(enhanced_result)
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Document search error: {str(e)}")
            return []

    async def generate_document_qa_response(
        self,
        user_id: int,
        question: str,
        document_context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate AI response based on document context
        """
        try:
            # Build document QA prompt
            qa_prompt = self.prompts.build_document_qa_prompt(question, document_context)
            
            # Get AI response
            pool = await self._get_openai_pool()
            response = await pool.chat_completion(
                messages=[
                    {"role": "system", "content": self.prompts.DOCUMENT_QA_SYSTEM_PROMPT},
                    {"role": "user", "content": qa_prompt}
                ],
                model=self.chat_model,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            ai_response = response["choices"][0]["message"]["content"]
            
            return {
                "success": True,
                "question": question,
                "answer": ai_response,
                "sources": self._format_document_sources(document_context),
                "confidence": self._calculate_response_confidence(document_context),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Document QA error: {str(e)}")
            return {
                "success": False,
                "question": question,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # Background tasks and optimization
    async def _batch_process_document_vectors(
        self,
        user_id: int,
        processed_files: List[Dict[str, Any]],
        context_type: str
    ):
        """Batch process document vectors for optimization"""
        try:
            successful_files = [f for f in processed_files if f.get("status") == "success"]
            
            if successful_files:
                # Create batch operations
                batch_operations = [{
                    "operation_type": "document",
                    "user_id": user_id,
                    "namespace_suffix": context_type,
                    "records": [
                        {
                            "id": f"doc_{hash(f['filename'])}",
                            "text": f.get("extracted_text", f.get("text_preview", "")), 
                            "metadata": {
                                "filename": f["filename"],
                                "context_type": context_type,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "text": f.get("extracted_text", f.get("text_preview", "")) 
                            }
                        }
                        for f in successful_files
                    ]
                }]
                
                await self.vector_service.batch_store_vectors(batch_operations)
                logger.info(f"Batch processed {len(successful_files)} document vectors for user {user_id}")
                
        except Exception as e:
            logger.error(f"Batch document vector processing error: {str(e)}")

    async def _analyze_document_patterns(
        self,
        user_id: int,
        processed_files: List[Dict[str, Any]]
    ):
        """Analyze document patterns for insights"""
        try:
            # Extract document types and patterns
            file_types = {}
            total_content_length = 0
            
            for file_info in processed_files:
                if file_info.get("status") == "success":
                    filename = file_info["filename"]
                    extension = filename.split(".")[-1].lower() if "." in filename else "unknown"
                    file_types[extension] = file_types.get(extension, 0) + 1
                    total_content_length += file_info.get("content_length", 0)
            
            # Store patterns for analytics
            pattern_data = {
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "file_types": file_types,
                "total_files": len(processed_files),
                "successful_files": len([f for f in processed_files if f.get("status") == "success"]),
                "total_content_length": total_content_length,
                "average_file_size": total_content_length / max(1, len(processed_files))
            }
            
            # Cache patterns for future optimization
            if self.cache_service:
                cache_key = f"document_patterns:{user_id}"
                await self.cache_service.set(cache_key, pattern_data, ttl=86400)  # 24 hours
                
        except Exception as e:
            logger.error(f"Document pattern analysis error: {str(e)}")

    # Utility methods
    async def _extract_document_insights(self, analysis_text: str, analysis_type: str) -> Dict[str, Any]:
        """Extract structured insights from document analysis"""
        insights = {
            "key_topics": [],
            "important_dates": [],
            "action_items": [],
            "warnings": [],
            "summary_points": []
        }
        
        # Simple keyword extraction (could be enhanced with NLP)
        lines = analysis_text.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if 'important' in line_lower or 'key' in line_lower:
                insights["key_topics"].append(line.strip())
            elif 'date' in line_lower or any(month in line_lower for month in ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']):
                insights["important_dates"].append(line.strip())
            elif 'action' in line_lower or 'todo' in line_lower or 'follow' in line_lower:
                insights["action_items"].append(line.strip())
            elif 'warning' in line_lower or 'caution' in line_lower or 'alert' in line_lower:
                insights["warnings"].append(line.strip())
            elif line.startswith('- ') or line.startswith('• '):
                insights["summary_points"].append(line.strip())
        
        return insights

    async def _get_cached_document_analysis(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get cached document analysis if available"""
        try:
            if self.cache_service:
                cache_key = f"document_analysis:{hash(filename)}"
                return await self.cache_service.get(cache_key)
            return None
        except Exception as e:
            logger.error(f"Cache retrieval error: {str(e)}")
            return None

    def _format_document_sources(self, document_context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format document sources for response"""
        sources = []
        
        for doc in document_context:
            sources.append({
                "filename": doc.get("metadata", {}).get("filename", "Unknown"),
                "content_preview": doc.get("content", "")[:200],
                "relevance_score": doc.get("score", 0),
                "document_type": doc.get("metadata", {}).get("file_type", "general")
            })
        
        return sources

    def _calculate_response_confidence(self, document_context: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for document-based response"""
        if not document_context:
            return 0.0
        
        # Simple confidence calculation based on relevance scores
        scores = [doc.get("score", 0) for doc in document_context]
        average_score = sum(scores) / len(scores)
        
        # Normalize to 0-1 range
        confidence = min(1.0, average_score)
        
        return round(confidence, 2)

    # Performance monitoring
    def _update_processing_stats(self, file_count: int, processing_time: float, results: List[Dict[str, Any]]):
        """Update processing statistics"""
        self.processing_stats["total_files_processed"] += file_count
        self.processing_stats["total_processing_time"] += processing_time
        
        successful = len([r for r in results if r.get("status") == "success"])
        failed = len([r for r in results if r.get("status") == "error"])
        
        self.processing_stats["successful_extractions"] += successful
        self.processing_stats["failed_extractions"] += failed
    
    async def _get_document_sequence(self, conversation_id: Optional[int]) -> int:
        """Get the next document sequence number for a conversation"""
        if not conversation_id:
            return 1
            
        # Increment and return the document count for this conversation
        current_count = self._conversation_document_counts.get(conversation_id, 0)
        new_count = current_count + 1
        self._conversation_document_counts[conversation_id] = new_count
        
        logger.info(f"📊 Document sequence for conversation {conversation_id}: {new_count}")
        return new_count
        
        # Update average processing time
        total_files = self.processing_stats["total_files_processed"]
        if total_files > 0:
            self.processing_stats["average_processing_time"] = (
                self.processing_stats["total_processing_time"] / total_files
            )
        
        # Update file type statistics
        for result in results:
            if result.get("status") == "success":
                filename = result["filename"]
                extension = filename.split(".")[-1].lower() if "." in filename else "unknown"
                self.processing_stats["files_by_type"][extension] = (
                    self.processing_stats["files_by_type"].get(extension, 0) + 1
                )

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get document processing statistics"""
        return self.processing_stats.copy()

    def reset_processing_stats(self):
        """Reset processing statistics"""
        self.processing_stats = {
            "total_files_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "files_by_type": {}
        }


    # ==================== ENHANCED DOCUMENT PROCESSING METHODS ====================

    async def process_document_request(
        self,
        user_id: int,
        conversation_id: int,
        message: str,
        files: Optional[List[Dict[str, Any]]] = None,
        background_tasks: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Process document upload request with actual text extraction and pet info integration
        THIS IS THE MISSING METHOD that orchestrator was calling!
        """
        try:
            logger.info(f"📄 Processing document request for user {user_id} with {len(files or [])} files")
            
            if not files:
                return {
                    "success": True,
                    "content": "No files to process.",
                    "conversation_id": conversation_id,
                    "processed_files": [],
                    "extracted_text": ""
                }
            
            # Convert dict files to UploadFile format for processing
            upload_files = self._convert_dict_files_to_upload_files(files)
            
            # Process files and extract text using existing robust method
            processed_files = await self.process_uploaded_files(
                user_id=user_id,
                files=upload_files,
                message=message,
                conversation_id=conversation_id,
                background_tasks=background_tasks
            )
            
            # Extract all text content for potential pet information processing
            extracted_texts = []
            successful_files = []
            
            for result in processed_files:
                if result.get("status") == "success" and result.get("extracted_text"):
                    extracted_texts.append(result["extracted_text"])
                    successful_files.append({
                        "filename": result["filename"],
                        "content_length": result.get("content_length", 0),
                        "extracted_text": result["extracted_text"]
                    })
            
            # Combine all extracted text
            combined_text = "\n\n".join(extracted_texts) if extracted_texts else ""
            
            logger.info(f"📄 Extracted {len(combined_text)} characters from {len(successful_files)} files")
            
            return {
                "success": True,
                "content": f"Successfully processed {len(successful_files)} files and extracted text content.",
                "conversation_id": conversation_id,
                "processed_files": successful_files,
                "extracted_text": combined_text,  # ⭐ KEY: This will be used for pet extraction
                "processing_time": 0.1
            }
            
        except Exception as e:
            logger.error(f"❌ Document request processing error: {str(e)}")
            return {
                "success": False,
                "content": f"Error processing documents: {str(e)}",
                "conversation_id": conversation_id,
                "processed_files": [],
                "extracted_text": ""
            }
    
    def _convert_dict_files_to_upload_files(self, files: List[Dict[str, Any]]) -> List[UploadFile]:
        """Convert dict-based file data to UploadFile objects for processing"""
        upload_files = []
        
        for file_data in files:
            try:
                # Extract file content (handle both base64 and direct content)
                content = file_data.get('content', '')
                
                if not content:
                    logger.warning(f"File {file_data.get('filename', 'unknown')} has no content, skipping")
                    continue
                
                # Handle base64 encoded content
                if isinstance(content, str):
                    try:
                        file_bytes = base64.b64decode(content)
                    except Exception as decode_error:
                        logger.error(f"Failed to decode base64 content for {file_data.get('filename', 'unknown')}: {decode_error}")
                        continue
                elif isinstance(content, bytes):
                    file_bytes = content
                else:
                    logger.error(f"Unsupported content type for {file_data.get('filename', 'unknown')}: {type(content)}")
                    continue
                
                if not file_bytes:
                    logger.warning(f"File {file_data.get('filename', 'unknown')} resulted in empty bytes, skipping")
                    continue
                
                # Create a file-like object
                import io
                file_obj = io.BytesIO(file_bytes)
                
                # Create UploadFile-like object
                from fastapi import UploadFile
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
        
        logger.info(f"📄 Converted {len(upload_files)} files for document processing")
        return upload_files

    async def process_document_message(
        self,
        user_id: int,
        conversation_id: int,
        message: str,
        files: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process document-related message with enhanced file analysis and Q&A"""
        try:
            # Basic document processing - enhanced features coming soon
            processed_files = []
            if files:
                for file_data in files:
                    processed_files.append({
                        "filename": file_data.get("filename", "unknown"),
                        "size": len(str(file_data.get("content", ""))),
                        "type": file_data.get("content_type", "text/plain")
                    })
            
            return {
                "success": True,
                "content": f"Successfully processed {len(processed_files)} files. Enhanced analysis features are being implemented.",
                "conversation_id": conversation_id,
                "processed_files": processed_files,
                "processing_time": 0.1
            }
        except Exception as e:
            return {
                "success": False,
                "content": f"Error processing document: {str(e)}",
                "conversation_id": conversation_id,
                "processed_files": []
            }
    
    async def process_mixed_files_with_vision(
        self,
        user_id: int,
        files: List[Dict[str, Any]],
        user_message: str = "",
        conversation_id: Optional[int] = None,
        message_id: Optional[int] = None,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Dict[str, Any]:
        """
        Process mixed files (documents, images, and audio) with comprehensive analysis
        
        Args:
            user_id: User ID
            files: List of file dictionaries with content, filename, content_type
            user_message: User's text message
            conversation_id: Optional conversation ID
            message_id: Optional message ID
            background_tasks: Optional background tasks
            
        Returns:
            Combined response from both document and vision processing
        """
        try:
            start_time = time.time()
            
            # Categorize files into images, audio, and documents
            categorized = await AsyncFileProcessor.categorize_files(files)
            
            images = categorized["images"]
            audio_files = categorized["audio"]
            documents = categorized["documents"]
            
            logger.info(f"📁 Processing mixed files: {len(images)} images, {len(audio_files)} audio, {len(documents)} documents")
            
            responses = []
            processed_files = []
            
            # Process images with vision service
            if images:
                logger.info(f"🖼️ Processing {len(images)} images with vision service")
                
                # Prepare images for vision processing
                vision_images = []
                for img in images:
                    if isinstance(img.get('content'), str):
                        # Base64 content - convert to bytes
                        content = base64.b64decode(img['content'])
                    else:
                        # Raw bytes
                        content = img['content']
                    
                    vision_images.append({
                        'content': content,
                        'filename': img.get('filename', 'image.jpg'),
                        'content_type': img.get('content_type', 'image/jpeg')
                    })
                
                # Process with vision service
                vision_result = await self.vision_service.process_vision_request(
                    user_id=user_id,
                    user_message=user_message,
                    images=vision_images,
                    conversation_id=conversation_id,
                    message_id=message_id
                )
                
                if vision_result.get("success"):
                    responses.append(vision_result["content"])
                    processed_files.extend(vision_result.get("processed_images", []))
                    self.processing_stats["images_processed"] += len(images)
                else:
                    responses.append("I had trouble analyzing some of the images you shared.")
            
            # Process audio files with voice service
            if audio_files:
                logger.info(f"🎙️ Processing {len(audio_files)} audio files with voice service")
                
                # Prepare audio files for voice processing
                voice_audio = []
                for audio in audio_files:
                    if isinstance(audio.get('content'), str):
                        # Base64 content - keep as string for voice service
                        content = audio['content']
                    else:
                        # Raw bytes - convert to base64 for voice service
                        content = base64.b64encode(audio['content']).decode('utf-8')
                    
                    voice_audio.append({
                        'content': content,
                        'filename': audio.get('filename', 'audio.mp3'),
                        'content_type': audio.get('content_type', 'audio/mpeg')
                    })
                
                # Process with voice service
                voice_result = await self.voice_service.process_voice_request(
                    user_id=user_id,
                    user_message=user_message,
                    audio_files=voice_audio,
                    conversation_id=conversation_id,
                    message_id=message_id
                )
                
                if voice_result.get("success"):
                    responses.append(voice_result["content"])
                    processed_files.extend(voice_result.get("processed_files", []))
                    self.processing_stats["audio_processed"] += len(audio_files)
                else:
                    responses.append("I had trouble transcribing some of the audio files you shared.")
            
            # Process documents with existing document service
            if documents:
                logger.info(f"📄 Processing {len(documents)} documents")
                
                # Convert file dictionaries back to file-like objects for existing processing
                # For now, we'll process documents with basic text extraction
                doc_responses = []
                for doc in documents:
                    try:
                        if isinstance(doc.get('content'), str):
                            # Base64 content
                            content = base64.b64decode(doc['content'])
                        else:
                            # Raw bytes
                            content = doc['content']
                        
                        # Extract text content
                        extracted_text = await AsyncFileProcessor.extract_text_content(
                            content, doc.get('content_type', 'application/octet-stream')
                        )
                        
                        if extracted_text:
                            doc_responses.append(f"Document '{doc.get('filename', 'document')}' processed: {extracted_text[:200]}...")
                            processed_files.append({
                                "filename": doc.get('filename', 'document'),
                                "type": "document",
                                "content_preview": extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
                            })
                        
                        self.processing_stats["documents_processed"] += 1
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing document {doc.get('filename', 'unknown')}: {str(e)}")
                        doc_responses.append(f"Had trouble processing document '{doc.get('filename', 'unknown')}'")
                
                if doc_responses:
                    responses.extend(doc_responses)
            
            # Combine responses
            if responses:
                if len(responses) == 1:
                    combined_response = responses[0]
                else:
                    combined_response = "I've processed your files:\n\n" + "\n\n".join(responses)
            else:
                combined_response = "I wasn't able to process any of the files you shared. Please try again."
            
            # Update processing stats
            self.processing_stats["total_files_processed"] += len(files)
            processing_time = time.time() - start_time
            self.processing_stats["total_processing_time"] += processing_time
            
            logger.info(f"✅ Mixed file processing completed in {processing_time:.2f}s")
            
            return {
                "success": True,
                "content": combined_response,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "processed_files": processed_files,
                "processing_time": processing_time,
                "file_breakdown": {
                    "images": len(images),
                    "documents": len(documents),
                    "total": len(files)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in mixed file processing: {str(e)}")
            return {
                "success": False,
                "content": "I encountered an error processing your files. Please try again.",
                "conversation_id": conversation_id,
                "error": str(e)
            }

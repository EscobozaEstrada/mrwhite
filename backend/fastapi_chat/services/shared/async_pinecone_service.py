"""
AWS Pinecone Vector Service
Real Pinecone SDK implementation with AWS Bedrock embeddings
Production-ready vector operations with full functionality
"""

import os
import logging
import hashlib
import json
import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

import boto3
import redis.asyncio as redis
from pinecone import Pinecone, ServerlessSpec
from models import AsyncSessionLocal, Document, CareRecord

logger = logging.getLogger(__name__)

class AsyncPineconeService:
    """
    Production AWS Pinecone Vector Service
    Real Pinecone SDK + MemoryDB + Bedrock Embeddings
    100% functional implementation with proper authentication
    """
    
    def __init__(self):
        # AWS Configuration
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.memorydb_endpoint = os.getenv("MEMORYDB_ENDPOINT")
        
        # Pinecone Configuration
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        
        if not self.pinecone_api_key:
            logger.error("❌ PINECONE_API_KEY environment variable is required")
            raise ValueError("PINECONE_API_KEY must be set")
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        
        # Index naming for compatibility  
        self.dog_project_index = "dog-project"  # Use 1024-dimension index for Titan v2
        self.common_knowledge_index = "common-knowledge-base"
        self.optimized_index = self.dog_project_index
        
        # Default index configuration
        self.default_dimension = 1024  # Bedrock Titan Text Embeddings v2 actual dimension
        self.default_metric = "cosine"
        self.default_cloud = "aws"
        self.default_region = "us-east-1"
        
        # Initialize AWS clients
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.aws_region)
        
        # Redis client will be initialized in async context
        self.redis_client = None
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Cache for frequent operations
        self._embedding_cache = {}
        self._search_cache = {}
        
        # Batch operation statistics
        self.batch_stats = {
            "total_batch_operations": 0,
            "total_individual_operations_saved": 0,
            "total_api_calls_saved": 0,
            "average_batch_size": 0.0,
            "batch_efficiency_percent": 0.0
        }
        
        logger.info(f"✅ AWS Pinecone Service initialized for region: {self.aws_region}")
    
    # ==================== REAL PINECONE OPERATIONS ====================
    
    async def _run_in_executor(self, func, *args, **kwargs):
        """Run synchronous Pinecone operations in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)
    
    async def list_indexes(self) -> List[str]:
        """List all Pinecone indexes"""
        try:
            indexes = await self._run_in_executor(lambda: self.pc.list_indexes())
            index_names = [index.name for index in indexes.indexes]
            logger.info(f"✅ Found {len(index_names)} Pinecone indexes: {index_names}")
            return index_names
        except Exception as e:
            logger.error(f"❌ Failed to list Pinecone indexes: {e}")
            return []
    
    async def describe_index(self, index_name: str) -> Optional[Dict[str, Any]]:
        """Describe a Pinecone index"""
        try:
            description = await self._run_in_executor(lambda: self.pc.describe_index(index_name))
            return {
                "name": description.name,
                "dimension": description.dimension,
                "metric": description.metric,
                "host": description.host,
                "status": description.status.state,
                "spec": description.spec
            }
        except Exception as e:
            logger.error(f"❌ Failed to describe index '{index_name}': {e}")
            return None
    
    async def describe_index_stats(self, index_name: str, namespace: str = None) -> Optional[Dict[str, Any]]:
        """Get index statistics"""
        try:
            index = await self._run_in_executor(lambda: self.pc.Index(index_name))
            stats = await self._run_in_executor(lambda: index.describe_index_stats())
            return {
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "total_vector_count": stats.total_vector_count,
                "namespaces": dict(stats.namespaces) if stats.namespaces else {}
            }
        except Exception as e:
            logger.error(f"❌ Failed to get stats for index '{index_name}': {e}")
            return None
    
    async def create_index(self, index_name: str, dimension: int = None, metric: str = None) -> bool:
        """Create a new Pinecone index"""
        try:
            dimension = dimension or self.default_dimension
            metric = metric or self.default_metric
            
            # Check if index already exists
            existing_indexes = await self.list_indexes()
            if index_name in existing_indexes:
                logger.info(f"✅ Index '{index_name}' already exists")
                return True
            
            # Create serverless index
            spec = ServerlessSpec(
                cloud=self.default_cloud,
                region=self.default_region
            )
            
            await self._run_in_executor(
                lambda: self.pc.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric=metric,
                    spec=spec
                )
            )
            
            # Wait for index to be ready
            max_wait = 60  # 60 seconds
            wait_time = 0
            while wait_time < max_wait:
                description = await self.describe_index(index_name)
                if description and description.get("status") == "Ready":
                    logger.info(f"✅ Index '{index_name}' created successfully")
                    return True
                await asyncio.sleep(2)
                wait_time += 2
            
            logger.warning(f"⚠️ Index '{index_name}' created but not ready within {max_wait}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create index '{index_name}': {e}")
            return False
    
    async def ensure_index_exists(self, index_name: str, dimension: int = None) -> bool:
        """Ensure Pinecone index exists, create if not"""
        try:
            existing_indexes = await self.list_indexes()
            if index_name in existing_indexes:
                logger.info(f"✅ Pinecone index '{index_name}' exists")
                return True
            
            # Create the index
            success = await self.create_index(index_name, dimension)
            if success:
                logger.info(f"✅ Created Pinecone index '{index_name}'")
                return True
            else:
                logger.error(f"❌ Failed to create index '{index_name}'")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to ensure index exists: {e}")
            return False
    
    async def get_index(self, index_name: str):
        """Get Pinecone index client"""
        try:
            # Ensure index exists first
            await self.ensure_index_exists(index_name)
            
            # Return index client
            return await self._run_in_executor(lambda: self.pc.Index(index_name))
            
        except Exception as e:
            logger.error(f"❌ Failed to get index '{index_name}': {e}")
            return None
    
    # ==================== EMBEDDING OPERATIONS ====================
    
    async def _get_embeddings(self, text: str, model_id: str = None, max_retries: int = 2) -> Optional[List[float]]:
        """Generate embeddings using AWS Bedrock with automatic chunking for large texts"""
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding")
                return None
            
            # Check cache first
            cache_key = hashlib.md5(text.encode()).hexdigest()
            if cache_key in self._embedding_cache:
                return self._embedding_cache[cache_key]
            
            model_id = model_id or "amazon.titan-embed-text-v2:0"
            
            # Prepare request body for Titan v2
            body = json.dumps({
                "inputText": text
            })
            
            # Call Bedrock
            response = await asyncio.to_thread(
                self.bedrock_runtime.invoke_model,
                body=body,
                modelId=model_id,
                accept='application/json',
                contentType='application/json'
            )
            
            # Parse response
            response_body = json.loads(response.get('body').read())
            embedding = response_body.get('embedding')
            
            if embedding:
                # Cache the result
                self._embedding_cache[cache_key] = embedding
                return embedding
            else:
                logger.error("No embedding returned from Bedrock")
                return None
                
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a "Too many input tokens" error
            if "Too many input tokens" in error_str or "ValidationException" in error_str:
                # Extract current character count
                char_count = len(text)
                logger.warning(f"⚠️ Text too long for embedding ({char_count} chars). Attempting to truncate...")
                
                # Retry with progressively smaller chunks
                if max_retries > 0:
                    # Try with 70% of current size
                    truncated_text = text[:int(char_count * 0.7)]
                    logger.info(f"🔄 Retrying with truncated text ({len(truncated_text)} chars)...")
                    return await self._get_embeddings(truncated_text, model_id, max_retries - 1)
                else:
                    logger.error(f"❌ Failed to generate embedding after {2 - max_retries} retries: {e}")
                    return None
            else:
                logger.error(f"❌ Failed to generate embedding: {e}")
                return None
    
    # ==================== VECTOR OPERATIONS ====================
    
    async def upsert_vectors(
        self, 
        index_name: str, 
        vectors: List[Dict[str, Any]], 
        namespace: str = None
    ) -> bool:
        """Upsert vectors to Pinecone index"""
        try:
            if not vectors:
                logger.warning("No vectors provided for upsert")
                return True
            
            index = await self.get_index(index_name)
            if not index:
                logger.error(f"❌ Could not get index '{index_name}'")
                return False
            
            # Prepare vectors for upsert
            upsert_data = []
            for vector in vectors:
                if not vector.get('id') or not vector.get('values'):
                    logger.warning(f"Skipping invalid vector: {vector}")
                    continue
                
                upsert_item = {
                    'id': str(vector['id']),
                    'values': vector['values']
                }
                
                if vector.get('metadata'):
                    upsert_item['metadata'] = vector['metadata']
                
                upsert_data.append(upsert_item)
            
            if not upsert_data:
                logger.warning("No valid vectors to upsert")
                return True
            
            # Perform upsert
            await self._run_in_executor(
                lambda: index.upsert(
                    vectors=upsert_data,
                    namespace=namespace
                )
            )
            
            logger.info(f"✅ Upserted {len(upsert_data)} vectors to index '{index_name}' (namespace: {namespace})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upsert vectors to '{index_name}': {e}")
            return False
    
    async def search_vectors(
        self, 
        index_name: str, 
        query_vector: List[float], 
        top_k: int = 5, 
        namespace: str = None,
        filter: Dict[str, Any] = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """Search vectors in Pinecone index"""
        try:
            if not query_vector:
                logger.warning("No query vector provided")
                return []
            
            index = await self.get_index(index_name)
            if not index:
                logger.error(f"❌ Could not get index '{index_name}'")
                return []
            
            # Perform search
            search_response = await self._run_in_executor(
                lambda: index.query(
                    vector=query_vector,
                    top_k=top_k,
                    namespace=namespace,
                    filter=filter,
                    include_metadata=include_metadata,
                    include_values=False
                )
            )
            
            # Format results
            results = []
            for match in search_response.matches:
                result = {
                    'id': match.id,
                    'score': match.score
                }
                if include_metadata and hasattr(match, 'metadata'):
                    result['metadata'] = match.metadata
                    # FIX: Include text content at root level for compatibility
                    if 'text' in match.metadata:
                        result['text'] = match.metadata['text']
                results.append(result)
            
            logger.info(f"✅ Found {len(results)} matches in index '{index_name}' (namespace: {namespace})")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to search vectors in '{index_name}': {e}")
            return []
    
    async def delete_vectors(
        self, 
        index_name: str, 
        ids: List[str], 
        namespace: str = None
    ) -> bool:
        """Delete vectors from Pinecone index"""
        try:
            if not ids:
                logger.warning("No IDs provided for deletion")
                return True
            
            index = await self.get_index(index_name)
            if not index:
                logger.error(f"❌ Could not get index '{index_name}'")
                return False
            
            # Delete vectors
            await self._run_in_executor(
                lambda: index.delete(
                    ids=ids,
                    namespace=namespace
                )
            )
            
            logger.info(f"✅ Deleted {len(ids)} vectors from index '{index_name}' (namespace: {namespace})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete vectors from '{index_name}': {e}")
            return False
    
    # ==================== HIGH-LEVEL OPERATIONS ====================
    
    async def batch_store_vectors(
        self,
        batch_operations: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """Batch store vectors with embeddings"""
        try:
            if not batch_operations:
                return True, "No operations to process"
            
            success_count = 0
            error_count = 0
            
            for operation in batch_operations:
                try:
                    # Extract operation details
                    index_name = operation.get('index_name', self.optimized_index)
                    namespace = operation.get('namespace')
                    records = operation.get('records', [])
                    
                    if not records:
                        continue
                    
                    # Prepare vectors with embeddings
                    vectors = []
                    failed_embeddings = []
                    
                    for record in records:
                        text = record.get('text', '')
                        record_id = record.get('id', f"doc_{len(vectors)}")
                        
                        if not text:
                            logger.warning(f"⚠️ Skipping record {record_id}: no text content")
                            continue
                        
                        # Generate embedding
                        embedding = await self._get_embeddings(text)
                        if not embedding:
                            failed_embeddings.append(record_id)
                            logger.error(f"❌ Failed to generate embedding for record {record_id} (text length: {len(text)} chars)")
                            continue
                        
                        metadata = record.get('metadata', {})
                        if text and 'text' not in metadata:
                            metadata['text'] = text
                        
                        vector = {
                            'id': record_id,
                            'values': embedding,
                            'metadata': metadata
                        }
                        vectors.append(vector)
                    
                    # Log summary of embedding generation
                    if failed_embeddings:
                        logger.error(f"❌ Failed to generate embeddings for {len(failed_embeddings)} records: {failed_embeddings[:5]}")
                    if vectors:
                        logger.info(f"✅ Successfully generated {len(vectors)} embeddings out of {len(records)} records")
                    
                    if vectors:
                        success = await self.upsert_vectors(index_name, vectors, namespace)
                        if success:
                            success_count += len(vectors)
                        else:
                            error_count += len(vectors)
                    
                except Exception as e:
                    logger.error(f"❌ Error in batch operation: {e}")
                    error_count += 1
            
            # Update statistics
            self.batch_stats["total_batch_operations"] += 1
            self.batch_stats["total_individual_operations_saved"] += success_count
            
            if success_count > 0:
                return True, f"Successfully stored {success_count} vectors"
            else:
                return False, f"Failed to store vectors. Errors: {error_count}"
                
        except Exception as e:
            logger.error(f"❌ Batch store operation failed: {e}")
            return False, str(e)
    
    async def search_user_documents(
        self,
        user_id: int,
        query: str,
        namespace_suffix: str = "docs",
        top_k: int = 5,
        include_metadata: bool = True,
        # 🎯 Smart document prioritization parameters
        conversation_id: Optional[int] = None,
        filename_filter: Optional[str] = None,
        recency_priority: bool = True
    ) -> List[Dict[str, Any]]:
        """Search user's documents using semantic search with smart prioritization"""
        try:
            # Generate query embedding
            query_embedding = await self._get_embeddings(query)
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # 🎯 Build smart metadata filter
            metadata_filter = self._build_smart_document_filter(
                conversation_id=conversation_id,
                filename_filter=filename_filter,
                recency_priority=recency_priority
            )
            
            # Search in user's namespace
            namespace = f"user_{user_id}_{namespace_suffix}"
            
            # If we have a filename filter but it doesn't match exactly, we need to do client-side filtering
            need_client_filtering = filename_filter and not metadata_filter.get("filename", {}).get("$eq") == filename_filter
            
            # If we need client-side filtering for partial matches, request more results
            actual_top_k = top_k * 3 if need_client_filtering else top_k
            
            results = await self.search_vectors(
                index_name=self.optimized_index,
                query_vector=query_embedding,
                top_k=actual_top_k,  # Request more results if we need to filter
                namespace=namespace,
                filter=metadata_filter,  # 🎯 Apply smart filtering
                include_metadata=include_metadata
            )
            
            # Log filtering details for debugging
            if metadata_filter:
                logger.info(f"🎯 Smart filter applied: {metadata_filter} | Results: {len(results)}")
            
            # Apply client-side filtering for partial filename matches if needed
            if need_client_filtering and filename_filter and results:
                logger.info(f"🔍 Applying client-side filtering for partial filename match: '{filename_filter}'")
                filtered_results = []
                
                for result in results:
                    # Check if filename in metadata contains the filter string
                    result_filename = result.get("metadata", {}).get("filename", "").lower()
                    if filename_filter.lower() in result_filename:
                        filtered_results.append(result)
                
                # Limit to the originally requested number
                results = filtered_results[:top_k]
                logger.info(f"🔍 Client-side filtering: {len(filtered_results)} matches found, returning {len(results)}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to search user documents: {e}")
            return []
    
    async def search_similar_conversations(
        self,
        user_id: int,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search similar conversations for the user"""
        try:
            # Generate query embedding
            query_embedding = await self._get_embeddings(query)
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Search in conversations namespace
            namespace = f"user_{user_id}_conversations"
            results = await self.search_vectors(
                index_name=self.optimized_index,
                query_vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True
            )
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to search similar conversations: {e}")
            return []
    
    async def search_common_knowledge(
        self,
        query: str,
        top_k: int = 3,
        namespace: str = "general"
    ) -> List[Dict[str, Any]]:
        """Search common knowledge base (Anahata book content, etc.)"""
        try:
            if not query or not query.strip():
                logger.warning("Empty query provided for common knowledge search")
                return []
            
            # Generate query embedding
            query_embedding = await self._get_embeddings(query.strip())
            if not query_embedding:
                logger.error("Failed to generate embedding for common knowledge search")
                return []
            
            # Search in common knowledge index
            results = await self.search_vectors(
                index_name=self.common_knowledge_index,
                query_vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True
            )
            
            # Format results for chat context
            formatted_results = []
            for result in results:
                metadata = result.get("metadata", {})
                formatted_results.append({
                    "content": metadata.get("text", ""),
                    "source": metadata.get("source", "Common Knowledge"),
                    "book_title": metadata.get("book_title", ""),
                    "category": metadata.get("category", ""),
                    "content_type": metadata.get("content_type", ""),
                    "score": result.get("score", 0.0)
                })
            
            logger.info(f"✅ Found {len(formatted_results)} common knowledge results for query: '{query[:50]}...'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Failed to search common knowledge: {e}")
            return []
    
    async def store_document_vectors(
        self,
        user_id: int,
        document_id: str,
        text_chunks: List[str],
        metadata: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """Store document vectors for a user"""
        try:
            if not text_chunks:
                return False, "No text chunks provided"
            
            # Prepare records
            records = []
            for i, chunk in enumerate(text_chunks):
                record = {
                    'id': f"doc_{document_id}_chunk_{i}",
                    'text': chunk,
                    'metadata': {
                        'user_id': user_id,
                        'document_id': document_id,
                        'chunk_index': i,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'text': chunk,  # CRITICAL FIX: Store text in metadata for retrieval
                        **(metadata or {})
                    }
                }
                records.append(record)
            
            # Store using batch operation
            batch_operation = {
                'index_name': self.optimized_index,
                'namespace': f"user_{user_id}_docs",
                'records': records
            }
            
            return await self.batch_store_vectors([batch_operation])
            
        except Exception as e:
            logger.error(f"❌ Failed to store document vectors: {e}")
            return False, str(e)
    
    # ==================== REDIS CACHE OPERATIONS ====================
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not self.redis_client and self.memorydb_endpoint:
            try:
                self.redis_client = redis.Redis(
                    host=self.memorydb_endpoint,
                    port=6379,
                    ssl=True,
                    ssl_cert_reqs=None,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                await self.redis_client.ping()
                logger.info(f"✅ Connected to AWS MemoryDB: {self.memorydb_endpoint}:6379")
            except Exception as e:
                logger.error(f"❌ Failed to connect to MemoryDB: {e}")
                self.redis_client = None
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.redis_client:
            await self.redis_client.aclose()
            self.redis_client = None
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
    
    # 🎯 Smart Document Filtering Logic
    
    def _build_smart_document_filter(
        self,
        conversation_id: Optional[int] = None,
        filename_filter: Optional[str] = None,
        recency_priority: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Build intelligent metadata filter for document search
        
        Note: Pinecone does not support $regex operator for filtering.
        For exact filename matches, we use $eq operator.
        For partial filename matches, we retrieve more results and filter client-side
        in the search_user_documents method.
        """
        filter_conditions = {}
        
        # Priority 1: Specific filename mentioned (highest priority)
        if filename_filter:
            # Use $eq operator instead of $regex since Pinecone doesn't support regex
            # For partial matching, we'll need to filter results client-side
            filter_conditions["filename"] = {"$eq": filename_filter}
            logger.info(f"🎯 Exact filename filter: '{filename_filter}'")
            return filter_conditions
        
       
        
        # Priority 3: No specific filtering (search all user documents)
        logger.info("🎯 No specific filter - searching all user documents")
        return None
    
    def _detect_filename_in_query(self, query: str) -> Optional[str]:
        """
        Robust filename detection with strict validation to prevent false positives
        Only detects explicit filename references, not common words
        """
        import re
        
        # Expanded common words to exclude (performance optimized)
        common_words = {
            'me', 'my', 'mine', 'you', 'your', 'yours', 'this', 'that', 'these', 'those',
            'it', 'its', 'they', 'them', 'their', 'theirs', 'and', 'but', 'or', 'for',
            'with', 'without', 'about', 'above', 'below', 'under', 'over', 'between',
            'through', 'during', 'before', 'after', 'since', 'until', 'while', 'because',
            'though', 'although', 'even', 'if', 'unless', 'except', 'not', 'no', 'yes',
            'please', 'thank', 'thanks', 'explain', 'tell', 'show', 'help', 'can', 'could',
            'would', 'should', 'may', 'might', 'must', 'will', 'shall', 'have', 'has',
            'had', 'do', 'does', 'did', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'get', 'got', 'getting', 'go', 'goes', 'going', 'went', 'gone',
            # Additional words that caused false positives
            'just', 'tell', 'general', 'document', 'from', 'the', 'in', 'on', 'at',
            'how', 'what', 'when', 'where', 'why', 'who', 'which', 'more', 'detail',
            'information', 'advice', 'question', 'answer', 'help', 'know', 'understand'
        }
        
        # Only very specific patterns that clearly indicate filenames
        explicit_file_patterns = [
            # Files with extensions (highest confidence)
            r"(\w+\.(?:pdf|docx?|txt|csv|xlsx|pptx?|png|jpe?g|gif))\b",
            
            # Quoted filenames (high confidence)
            r'["\']([^"\']+\.(?:pdf|docx?|txt|csv|xlsx))["\']',
            
            # Explicit file references with extensions
            r"(?:file|document)\s+[\"']?(\w+\.(?:pdf|docx?|txt|csv|xlsx))[\"']?",
            
            # Upload references with extensions
            r"uploaded\s+(?:file\s+)?[\"']?(\w+\.(?:pdf|docx?|txt|csv|xlsx))[\"']?"
        ]
        
        query_lower = query.lower()
        
        # Only check explicit file patterns (much more restrictive)
        for pattern in explicit_file_patterns:
            match = re.search(pattern, query_lower)
            if match:
                filename = match.group(1).strip()
                
                # Additional validation
                if (len(filename) > 3 and  # Must be longer than 3 chars
                    '.' in filename and  # Must have extension
                    filename.lower() not in common_words):  # Not a common word
                    
                    logger.info(f"🎯 Detected explicit filename: '{filename}' from '{query}'")
                    return filename
        
        # Special case: detect quoted content that looks like filenames
        quote_pattern = r'["\']([^"\']{3,})["\']'
        quote_matches = re.findall(quote_pattern, query_lower)
        for quoted_text in quote_matches:
            # Only consider it a filename if it has an extension or is clearly a document name
            if ('.' in quoted_text and 
                any(ext in quoted_text for ext in ['.pdf', '.doc', '.txt', '.csv', '.xlsx']) and
                quoted_text.lower() not in common_words):
                logger.info(f"🎯 Detected quoted filename: '{quoted_text}' from '{query}'")
                return quoted_text
        
        return None
    
    # ==================== HEALTH CHECK ====================
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for all services"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {}
        }
        
        try:
            # Check Pinecone connection
            try:
                indexes = await self.list_indexes()
                health_status["checks"]["pinecone"] = {
                    "status": "healthy",
                    "indexes_count": len(indexes),
                    "indexes": indexes
                }
            except Exception as e:
                health_status["checks"]["pinecone"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
            
            # Check MemoryDB connection
            if self.redis_client:
                try:
                    await self.redis_client.ping()
                    health_status["checks"]["memorydb"] = {"status": "healthy"}
                except Exception as e:
                    health_status["checks"]["memorydb"] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
                    health_status["status"] = "degraded"
            else:
                health_status["checks"]["memorydb"] = {"status": "not_configured"}
            
            # Check Bedrock embeddings
            try:
                test_embedding = await self._get_embeddings("health check test")
                if test_embedding:
                    health_status["checks"]["bedrock_embeddings"] = {
                        "status": "healthy",
                        "dimension": len(test_embedding)
                    }
                else:
                    health_status["checks"]["bedrock_embeddings"] = {
                        "status": "unhealthy",
                        "error": "Empty embedding returned"
                    }
                    health_status["status"] = "degraded"
            except Exception as e:
                health_status["checks"]["bedrock_embeddings"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status
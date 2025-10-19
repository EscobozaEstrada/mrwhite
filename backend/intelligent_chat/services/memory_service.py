"""
Memory Service for contextual retrieval and re-ranking
Implements Anthropic's contextual retrieval approach
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from utils.pinecone_client import PineconeClient
from utils.embeddings import EmbeddingService
from config.settings import settings

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for intelligent memory retrieval and management"""
    
    def __init__(self):
        """Initialize memory service"""
        self.pinecone = PineconeClient()
        self.embeddings = EmbeddingService()
        
        # Retrieval parameters
        self.default_top_k = settings.DEFAULT_TOP_K
        self.health_mode_top_k = settings.HEALTH_MODE_TOP_K
        self.wayofdog_mode_top_k = settings.WAYOFDOG_MODE_TOP_K
        self.rerank_top_n = settings.RERANK_TOP_N
        self.health_mode_rerank_top_n = settings.HEALTH_MODE_RERANK_TOP_N
    
    async def retrieve_memories(
        self,
        query: str,
        user_id: int,
        active_mode: Optional[str] = None,
        dog_profile_id: Optional[int] = None,
        limit: int = None,
        conversation_id: Optional[int] = None,
        skip_document_search: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories with contextual retrieval and re-ranking
        
        Args:
            query: User query
            user_id: User ID for filtering
            active_mode: Active mode (reminders, health, wayofdog)
            dog_profile_id: Selected dog profile ID
            limit: Number of results (default based on mode)
            conversation_id: Conversation ID for retrieving previously attached documents
            skip_document_search: If True, skip semantic document search (used when documents are explicitly attached)
        
        Returns:
            List of relevant memories with scores
        """
        try:
            # Determine retrieval strategy based on mode
            if active_mode == "health":
                return await self._retrieve_health_memories(query, user_id, dog_profile_id, limit)
            elif active_mode == "wayofdog":
                return await self._retrieve_book_memories(query, user_id, limit)
            elif active_mode == "reminders":
                return await self._retrieve_reminder_context(query, user_id, limit)
            else:
                return await self._retrieve_general_memories(query, user_id, limit, conversation_id, skip_document_search)
                
        except Exception as e:
            logger.error(f"❌ Memory retrieval failed: {str(e)}", exc_info=True)
            # Return empty list but log the full traceback
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
    
    async def _retrieve_health_memories(
        self,
        query: str,
        user_id: int,
        dog_profile_id: Optional[int],
        limit: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Retrieve health-related memories (vet reports + user docs + book health content)"""
        top_k = limit or self.health_mode_top_k
        
        # Generate query embedding
        query_embedding = await self.embeddings.generate_embedding(query)
        
        # 1. Search user documents namespace for vet reports (HIGHEST PRIORITY)
        user_docs_namespace = f"user_{user_id}_docs"
        vet_reports_filter = {"user_id": user_id, "is_vet_report": True}
        if dog_profile_id:
            vet_reports_filter["dog_profile_id"] = dog_profile_id
        
        vet_memories = await self.pinecone.query_vectors(
            query_vector=query_embedding,
            namespace=user_docs_namespace,
            top_k=5,  # Top 5 vet report chunks
            filter=vet_reports_filter
        )
        
        # 2. Search user documents namespace (prioritize vet reports if dog selected)
        user_docs_namespace = f"user_{user_id}_docs"
        doc_filter = {"user_id": user_id}
        
        if dog_profile_id:
            doc_filter["dog_profile_id"] = dog_profile_id
        
        doc_memories = await self.pinecone.query_vectors(
            query_vector=query_embedding,
            namespace=user_docs_namespace,
            top_k=5,
            filter=doc_filter
        )
        
        if len(doc_memories) < 3 and dog_profile_id:
            fallback_memories = await self.pinecone.query_vectors(
                query_vector=query_embedding,
                namespace=user_docs_namespace,
                top_k=3,
                filter={"user_id": user_id}
            )
            doc_memories.extend(fallback_memories)
        
        # 3. Search book namespace for health-related expert knowledge
        # Filter by health topics: health, medical, vet, symptoms, nutrition, grooming
        from config.settings import settings
        book_namespace = f"book-content-{settings.ENVIRONMENT}"
        
        book_health_filter = {
            "topics": {"$in": ["health", "nutrition", "grooming"]}
        }
        
        book_health_memories = await self.pinecone.query_vectors(
            query_vector=query_embedding,
            namespace=book_namespace,
            top_k=5,  # Top 5 book chunks on health
            filter=book_health_filter
        )
        
        # Fallback: if no health-specific chunks, search all book content
        if len(book_health_memories) < 3:
            book_general_memories = await self.pinecone.query_vectors(
                query_vector=query_embedding,
                namespace=book_namespace,
                top_k=3
            )
            book_health_memories.extend(book_general_memories)
        
        # 4. Combine with priority weighting
        all_memories = []
        
        # Add vet reports with HIGHEST priority boost (user's actual medical records)
        for mem in vet_memories:
            mem["priority_boost"] = 2.0  # 2x weight
            mem["source_type"] = "vet_report"
            all_memories.append(mem)
        
        # Add user documents with HIGH priority (boost vet reports even higher)
        for mem in doc_memories:
            metadata = mem.get("metadata", {})
            if metadata.get("is_vet_report"):
                mem["priority_boost"] = 2.5
                mem["source_type"] = "vet_report_doc"
            else:
                mem["priority_boost"] = 1.5
                mem["source_type"] = "user_document"
            all_memories.append(mem)
        
        # Add book content with EXPERT priority (authoritative health knowledge)
        for mem in book_health_memories:
            mem["priority_boost"] = 1.3  # 1.3x weight
            mem["source_type"] = "book"
            all_memories.append(mem)
        
        # 5. Re-rank with priority weighting (use 7 chunks for health mode)
        reranked = await self._rerank_memories(query, all_memories, self.health_mode_rerank_top_n)
        
        logger.info(f"✅ Retrieved {len(reranked)} health memories (vet:{len(vet_memories)}, docs:{len(doc_memories)}, book:{len(book_health_memories)})")
        return reranked
    
    async def _retrieve_book_memories(
        self,
        query: str,
        user_id: int,
        limit: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve Way of Dog memories with priority on user's book notes and reflections
        """
        top_k = limit or self.wayofdog_mode_top_k
        query_embedding = await self.embeddings.generate_embedding(query)
        
        # 1. Search user's book notes namespace (HIGHEST priority - their spiritual journey)
        # Book notes are stored in dog-project index with namespace: user_{user_id}_book_notes
        user_notes_namespace = f"user_{user_id}_book_notes"
        try:
            user_notes = await self.pinecone.query_vectors(
                query_vector=query_embedding,
                namespace=user_notes_namespace,
                top_k=top_k,
                filter={"user_id": user_id}
            )
            logger.info(f"🔍 Found {len(user_notes)} user book notes in namespace {user_notes_namespace}")
        except Exception as e:
            logger.warning(f"⚠️ Could not retrieve from {user_notes_namespace}: {e}")
            user_notes = []
        
        # 2. Search book content for relevant passages (HIGH priority - source wisdom)
        book_namespace = f"book-content-{settings.ENVIRONMENT}"
        book_content = await self.pinecone.query_vectors(
            query_vector=query_embedding,
            namespace=book_namespace,
            top_k=top_k
        )
        logger.info(f"🔍 Found {len(book_content)} book content chunks")
        
        # 3. Search general conversations for context (MEDIUM priority)
        conversation_memories = await self.pinecone.query_vectors(
            query_vector=query_embedding,
            namespace=self.pinecone.namespace_conversations,
            top_k=min(top_k, 3),  # Fewer conversation memories
            filter={"user_id": user_id}
        )
        logger.info(f"🔍 Found {len(conversation_memories)} conversation memories")
        
        # 4. Combine with priority weighting
        all_memories = []
        
        # Add user book notes with HIGHEST priority (their personal reflections)
        for mem in user_notes:
            mem["priority_boost"] = 3.0  # 3x weight - highest priority
            mem["source_type"] = "user_book_note"
            all_memories.append(mem)
        
        # Add book content with HIGH priority (source wisdom)
        for mem in book_content:
            mem["priority_boost"] = 2.0  # 2x weight
            mem["source_type"] = "book"
            all_memories.append(mem)
        
        # Add conversations with MEDIUM priority (contextual background)
        for mem in conversation_memories:
            mem["priority_boost"] = 1.0  # 1x weight
            mem["source_type"] = "conversation"
            all_memories.append(mem)
        
        # 5. Re-rank with priority weighting
        reranked = await self._rerank_memories(query, all_memories, top_k)
        
        # CRITICAL FIX: If user notes exist but aren't in top results, FORCE them to appear
        # This ensures user's personal comments are ALWAYS shown when they exist
        user_note_ids = {id(note) for note in user_notes}
        reranked_note_ids = {id(mem) for mem in reranked if mem.get("source_type") == "user_book_note"}
        
        if user_notes and not reranked_note_ids:
            logger.warning(f"⚠️ User notes were retrieved but excluded by reranking! Forcing them to appear.")
            # Remove lowest priority items and add user notes
            num_notes_to_add = min(len(user_notes), 5)  # Add top 5 user notes
            reranked = reranked[:top_k - num_notes_to_add] + user_notes[:num_notes_to_add]
        
        # DEBUG: Check source_types after reranking
        reranked_source_types = [m.get("source_type") for m in reranked]
        logger.info(f"🔍 DEBUG: Source types after reranking: {reranked_source_types}")
        
        logger.info(f"✅ Retrieved {len(reranked)} Way of Dog memories (notes:{len(user_notes)}, book:{len(book_content)}, conversations:{len(conversation_memories)})")
        return reranked
    
    async def _retrieve_reminder_context(
        self,
        query: str,
        user_id: int,
        limit: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Retrieve conversation context for reminders"""
        top_k = limit or 5
        
        query_embedding = await self.embeddings.generate_embedding(query)
        
        # Search conversation namespace for reminder context
        memories = await self.pinecone.query_vectors(
            query_vector=query_embedding,
            namespace=self.pinecone.namespace_conversations,
            top_k=top_k,
            filter={
                "user_id": user_id,
                "active_mode": "reminders"
            }
        )
        
        logger.info(f"✅ Retrieved {len(memories)} reminder context memories")
        return memories
    
    async def _retrieve_general_memories(
        self,
        query: str,
        user_id: int,
        limit: Optional[int],
        conversation_id: Optional[int] = None,
        skip_document_search: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve general memories from all sources (including book for dog-related queries)"""
        top_k = limit or self.default_top_k
        
        query_embedding = await self.embeddings.generate_embedding(query)
        
        # Detect if query is about documents (summary, read, story, document, images, etc.)
        query_lower = query.lower()
        document_keywords = ['summarize', 'summary', 'read', 'story', 'document', 'pdf', 'file', 'uploaded', 'shared', 'image', 'images', 'photo', 'photos', 'picture', 'pictures', 'show']
        is_document_query = any(keyword in query_lower for keyword in document_keywords)
        
        # Detect if specifically asking for images/photos
        image_keywords = ['image', 'images', 'photo', 'photos', 'picture', 'pictures']
        is_image_query = any(keyword in query_lower for keyword in image_keywords)
        
        # Detect if asking for "images I shared/uploaded" OR "images of [dog]" - indicating they want ALL previous images
        reference_keywords = [
            'i shared', 'i uploaded', 'i sent', 'i gave', 'that i', 'i provided',
            'share the', 'show me the', 'send me', 'give me the', 'all the',
            'images of', 'pictures of', 'photos of'
        ]
        is_reference_query = any(keyword in query_lower for keyword in reference_keywords) and is_image_query
        
        # Detect if query is dog-related (for book integration)
        dog_keywords = [
            'dog', 'puppy', 'breed', 'training', 'train', 'behavior', 'behave',
            'nutrition', 'food', 'diet', 'feed', 'feeding', 'eat', 'eating',
            'exercise', 'walk', 'play', 'grooming', 'groom', 'brush', 'bath',
            'health', 'vet', 'sick', 'illness', 'symptom', 'medical',
            'bark', 'barking', 'bite', 'biting', 'aggression', 'aggressive',
            'anxiety', 'anxious', 'fear', 'scared', 'socialization', 'socialize',
            'leash', 'collar', 'harness', 'crate', 'potty', 'house training'
        ]
        is_dog_related = any(keyword in query_lower for keyword in dog_keywords)
        
        # If asking about documents, retrieve MORE document chunks and FEWER conversation chunks
        if is_document_query:
            doc_top_k = 20  # Get 20 document chunks for better context
            conv_top_k = 2   # Only 2 conversation chunks
            logger.info(f"📚 Document query detected - retrieving {doc_top_k} document chunks")
        else:
            doc_top_k = top_k // 2
            conv_top_k = top_k // 2
        
        # Search multiple namespaces
        conversations = await self.pinecone.query_vectors(
            query_vector=query_embedding,
            namespace=self.pinecone.namespace_conversations,
            top_k=conv_top_k,
            filter={"user_id": user_id}
        )
        
        # Search user-specific documents namespace (skip if documents are explicitly attached)
        documents = []
        if not skip_document_search:
            user_documents_namespace = f"user_{user_id}_docs"
            logger.info(f"🔍 Searching documents in namespace: {user_documents_namespace}")
            
            # Build filter - EXCLUDE vet reports in General Mode (Health Mode only)
            doc_filter = {"user_id": user_id}
            
            # Exclude vet reports from General Mode
            doc_filter["is_vet_report"] = {"$ne": True}
            logger.info(f"🚫 Excluding vet reports from General Mode (Health Mode only)")
            
            # Additionally filter for images if specifically requested
            if is_image_query:
                doc_filter["file_type"] = {"$in": ["jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff"]}
                logger.info(f"🖼️ Filtering for image file types only")
            
            documents = await self.pinecone.query_vectors(
                query_vector=query_embedding,
                namespace=user_documents_namespace,
                top_k=doc_top_k,
                filter=doc_filter
            )
            logger.info(f"📄 Found {len(documents)} document chunks from semantic search")
        else:
            logger.info(f"⏭️ Skipping document semantic search (documents explicitly attached to message)")
        
        # 🔥 NEW: If user is asking for "images/documents I shared", get ALL from conversation history
        if is_reference_query and conversation_id:
            logger.info(f"🔍 User asking for previously shared items - retrieving ALL from conversation {conversation_id}")
            from sqlalchemy import text
            from models.base import AsyncSessionLocal
            
            async with AsyncSessionLocal() as session:
                # Get all unique document IDs from this conversation
                result = await session.execute(
                    text("""
                        SELECT DISTINCT d.id, d.filename, d.file_type, d.s3_url, 
                               d.extracted_text, d.created_at
                        FROM ic_documents d
                        JOIN ic_message_documents md ON d.id = md.document_id
                        JOIN ic_messages m ON md.message_id = m.id
                        WHERE m.conversation_id = :conversation_id
                          AND m.user_id = :user_id
                        ORDER BY d.created_at DESC
                    """),
                    {"conversation_id": conversation_id, "user_id": user_id}
                )
                
                conversation_docs = []
                for row in result:
                    doc_id, filename, file_type, s3_url, extracted_text, created_at = row
                    
                    # Only include images if it's an image query
                    if is_image_query and file_type not in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff']:
                        continue
                    
                    conversation_docs.append({
                        "text": f"[Document: {filename}]\n\n{extracted_text or ''}",
                        "metadata": {
                            "document_id": doc_id,
                            "filename": filename,
                            "file_type": file_type,
                            "s3_url": s3_url,
                            "user_id": user_id,
                            "source_type": "document",
                            "created_at": created_at.isoformat() if created_at else None
                        },
                        "score": 0.95,  # High score since user explicitly asked
                        "priority_boost": 1.2  # Boost priority
                    })
                
                logger.info(f"📎 Found {len(conversation_docs)} previously attached documents in conversation")
                
                # Prepend conversation docs to the semantic search results
                documents = conversation_docs + documents
        
        # If query is dog-related, also search book content (low priority)
        book_memories = []
        if is_dog_related:
            from config.settings import settings
            book_namespace = f"book-content-{settings.ENVIRONMENT}"
            
            logger.info(f"🐕 Dog-related query detected - searching book content")
            
            book_memories = await self.pinecone.query_vectors(
                query_vector=query_embedding,
                namespace=book_namespace,
                top_k=3  # Only 3 book chunks (low priority)
            )
            logger.info(f"📖 Found {len(book_memories)} book chunks")
        
        # Combine all memories with priority weighting
        all_memories = []
        
        # Add conversations (standard priority)
        for mem in conversations:
            all_memories.append(mem)
        
        # Add user documents (standard priority)
        for mem in documents:
            all_memories.append(mem)
        
        # Add book content (LOWER priority than personal context)
        for mem in book_memories:
            mem["priority_boost"] = 0.8  # 0.8x weight (LOWER than personal context)
            mem["source_type"] = "book"
            all_memories.append(mem)
        
        # For document queries, return more results
        rerank_limit = 15 if is_document_query else self.rerank_top_n
        reranked = await self._rerank_memories(query, all_memories, rerank_limit)
        
        logger.info(f"✅ Retrieved {len(reranked)} general memories (conversations: {len(conversations)}, docs: {len(documents)}, book: {len(book_memories)})")
        return reranked
    
    async def _rerank_memories(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        top_n: int
    ) -> List[Dict[str, Any]]:
        """
        Re-rank memories using multiple signals
        
        Args:
            query: Original query
            memories: Retrieved memories with scores
            top_n: Number of top results to return
        
        Returns:
            Re-ranked memories
        """
        if not memories:
            return []
        
        # Score memories based on:
        # 1. Semantic similarity (already in score)
        # 2. Recency (time decay)
        # 3. Relevance to query (keyword matching)
        
        query_keywords = set(query.lower().split())
        current_time = datetime.utcnow()
        
        for memory in memories:
            metadata = memory.get("metadata", {})
            base_score = memory.get("score", 0.0)
            
            # Recency boost (decay over time)
            created_at_str = metadata.get("created_at")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    days_old = (current_time - created_at).days
                    recency_score = max(0, 1.0 - (days_old / 365))  # Decay over a year
                except:
                    recency_score = 0.5
            else:
                recency_score = 0.5
            
            # Keyword relevance
            content = metadata.get("text", "").lower()
            matching_keywords = len(query_keywords.intersection(set(content.split())))
            keyword_score = min(1.0, matching_keywords / max(1, len(query_keywords)))
            
            # Apply priority boost if present (for health mode: vet reports > docs > book)
            priority_boost = memory.get("priority_boost", 1.0)
            
            # Combined score (weighted)
            memory["rerank_score"] = (
                base_score * 0.6 +          # Semantic similarity (60%)
                recency_score * 0.2 +       # Recency (20%)
                keyword_score * 0.2         # Keyword match (20%)
            ) * priority_boost              # Apply priority multiplier
        
        # Sort by rerank score
        reranked = sorted(memories, key=lambda x: x.get("rerank_score", 0), reverse=True)
        
        return reranked[:top_n]
    
    async def store_conversation_memory(
        self,
        user_id: int,
        conversation_id: int,
        message_id: int,
        content: str,
        role: str,
        active_mode: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store conversation message in Pinecone
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            message_id: Message ID
            content: Message content
            role: Message role (user/assistant)
            active_mode: Active mode
            metadata: Additional metadata
        
        Returns:
            True if successful
        """
        try:
            # Generate embedding
            embedding = await self.embeddings.generate_embedding(content)
            
            # Prepare metadata
            vector_metadata = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "role": role,
                "text": content[:1000],  # Store preview
                "created_at": datetime.utcnow().isoformat(),
                "active_mode": active_mode or "general"
            }
            
            if metadata:
                vector_metadata.update(metadata)
            
            # Upsert to Pinecone
            vectors = [{
                "id": f"msg_{message_id}",
                "values": embedding,
                "metadata": vector_metadata
            }]
            
            await self.pinecone.upsert_vectors(
                vectors=vectors,
                namespace=self.pinecone.namespace_conversations
            )
            
            logger.info(f"✅ Stored conversation memory: msg_{message_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store conversation memory: {str(e)}")
            return False
    
    async def store_document_memory(
        self,
        user_id: int,
        document_id: int,
        chunks: List[Dict[str, Any]],
        document_metadata: Dict[str, Any]
    ) -> bool:
        """
        Store document chunks in Pinecone
        
        Args:
            user_id: User ID
            document_id: Document ID
            chunks: List of text chunks with metadata
            document_metadata: Document-level metadata
        
        Returns:
            True if successful
        """
        try:
            vectors = []
            
            for chunk in chunks:
                # Generate contextual embedding
                chunk_text = chunk.get("text", "")
                context = f"Document: {document_metadata.get('filename', 'Unknown')}, Type: {document_metadata.get('file_type', 'Unknown')}"
                
                embedding = await self.embeddings.generate_contextual_embedding(
                    chunk=chunk_text,
                    context=context
                )
                
                # Prepare metadata
                vector_metadata = {
                    "user_id": user_id,
                    "document_id": document_id,
                    "chunk_index": chunk.get("chunk_index", 0),
                    "total_chunks": chunk.get("total_chunks", 1),
                    "text": chunk_text[:1000],
                    "filename": document_metadata.get("filename", ""),
                    "file_type": document_metadata.get("file_type", ""),
                    "created_at": datetime.utcnow().isoformat()
                }
                
                vectors.append({
                    "id": f"doc_{document_id}_chunk_{chunk.get('chunk_index', 0)}",
                    "values": embedding,
                    "metadata": vector_metadata
                })
            
            # Batch upsert
            await self.pinecone.upsert_vectors(
                vectors=vectors,
                namespace=self.pinecone.namespace_documents
            )
            
            logger.info(f"✅ Stored {len(vectors)} document chunks: doc_{document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store document memory: {str(e)}")
            return False
    
    async def store_memory(
        self,
        user_id: int,
        conversation_id: int,
        content: str,
        role: str,
        metadata: Dict[str, Any],
        namespace: str
    ) -> str:
        """
        Generic method to store any type of memory in Pinecone
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            content: Content to store (chunk text)
            role: Role type (e.g., "document", "user", "assistant")
            metadata: Metadata for the vector
            namespace: Pinecone namespace to use
        
        Returns:
            Vector ID
        """
        try:
            # Generate embedding with context for documents (contextual retrieval)
            if role == "document" and metadata.get("filename"):
                context = f"Document: {metadata.get('filename', 'Unknown')}, Type: {metadata.get('file_type', 'Unknown')}"
                embedding = await self.embeddings.generate_contextual_embedding(
                    chunk=content,
                    context=context
                )
                logger.debug(f"🔍 Generated contextual embedding for document chunk")
            else:
                embedding = await self.embeddings.generate_embedding(content)
            
            # Create unique vector ID
            vector_id = f"{role}_{metadata.get('document_id', '')}_{metadata.get('chunk_index', 0)}_{datetime.utcnow().timestamp()}"
            
            # Prepare metadata
            vector_metadata = {
                "user_id": user_id,
                "role": role,
                "text": content[:1000],  # Store preview
                "created_at": datetime.utcnow().isoformat(),
            }
            
            # Only add conversation_id if it exists (Pinecone rejects null values)
            if conversation_id:
                vector_metadata["conversation_id"] = conversation_id
            
            vector_metadata.update(metadata)
            
            # Upsert to Pinecone
            vectors = [{
                "id": vector_id,
                "values": embedding,
                "metadata": vector_metadata
            }]
            
            await self.pinecone.upsert_vectors(
                vectors=vectors,
                namespace=namespace
            )
            
            logger.info(f"✅ Stored memory: {vector_id} in {namespace}")
            return vector_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store memory: {str(e)}")
            raise
    
    async def clear_conversation_memories(
        self,
        user_id: int,
        conversation_id: Optional[int] = None
    ) -> bool:
        """
        Clear ONLY conversation memories (for "Clear Chat Only" button)
        Leaves documents, vet reports, and book notes untouched
        
        Args:
            user_id: User ID
            conversation_id: Optional conversation ID to filter by
        
        Returns:
            True if successful
        """
        try:
            # Clear only from conversation namespace
            filter_dict = {"user_id": user_id}
            if conversation_id:
                filter_dict["conversation_id"] = conversation_id
            
            await self.pinecone.delete_by_filter(
                filter=filter_dict,
                namespace=self.pinecone.namespace_conversations
            )
            logger.info(f"✅ Cleared conversation memories for user {user_id} (conversation: {conversation_id})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to clear conversation memories: {str(e)}")
            return False
    
    async def clear_user_memories(
        self,
        user_id: int,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Clear all memories for a user (for clear chat functionality)
        
        Args:
            user_id: User ID
            namespace: Specific namespace (or all if None)
        
        Returns:
            True if successful
        """
        try:
            filter_dict = {"user_id": user_id}
            
            if namespace:
                # Clear specific namespace
                await self.pinecone.delete_by_filter(
                    filter=filter_dict,
                    namespace=namespace
                )
                logger.info(f"✅ Cleared user {user_id} memories from {namespace}")
            else:
                # Clear all shared namespaces (filter by user_id)
                shared_namespaces = [
                    self.pinecone.namespace_conversations,
                    self.pinecone.namespace_documents,
                    self.pinecone.namespace_vet_reports,
                ]
                
                for ns in shared_namespaces:
                    try:
                        await self.pinecone.delete_by_filter(
                            filter=filter_dict,
                            namespace=ns
                        )
                        logger.info(f"✅ Cleared user {user_id} from shared namespace: {ns}")
                    except Exception as e:
                        logger.error(f"❌ Failed to clear {ns}: {e}")
                
                # Clear user-specific namespaces (delete entirely)
                user_namespaces = [
                    f"user_{user_id}_docs",
                    f"user_{user_id}_book_notes",
                ]
                
                for ns in user_namespaces:
                    try:
                        # Delete all vectors in user-specific namespace
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None,
                            lambda ns=ns: self.pinecone.index.delete(
                                delete_all=True,
                                namespace=ns
                            )
                        )
                        logger.info(f"✅ Deleted user-specific namespace: {ns}")
                    except Exception as e:
                        # Namespace might not exist - that's okay
                        logger.warning(f"⚠️ Could not delete namespace {ns}: {e}")
                
                logger.info(f"✅ Cleared all memories for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to clear memories: {str(e)}")
            return False
    
    async def clear_user_memories_complete(
        self,
        user_id: int,
        include_s3: bool = False
    ) -> bool:
        """
        Completely clear all memories for a user (for account deletion)
        Includes shared namespaces, user-specific namespaces, and optionally S3 files
        
        Args:
            user_id: User ID
            include_s3: Whether to also delete S3 files
        
        Returns:
            True if successful
        """
        try:
            filter_dict = {"user_id": user_id}
            
            # 1. Clear shared namespaces (filter by user_id)
            shared_namespaces = [
                self.pinecone.namespace_conversations,
                self.pinecone.namespace_documents,
                self.pinecone.namespace_vet_reports,
            ]
            
            for ns in shared_namespaces:
                try:
                    await self.pinecone.delete_by_filter(
                        filter=filter_dict,
                        namespace=ns
                    )
                    logger.info(f"✅ Cleared user {user_id} from shared namespace: {ns}")
                except Exception as e:
                    logger.error(f"❌ Failed to clear {ns}: {e}")
            
            # 2. Clear user-specific namespaces (delete entirely)
            user_namespaces = [
                f"user_{user_id}_docs",
                f"user_{user_id}_book_notes",
            ]
            
            for ns in user_namespaces:
                try:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda ns=ns: self.pinecone.index.delete(
                            delete_all=True,
                            namespace=ns
                        )
                    )
                    logger.info(f"✅ Deleted user-specific namespace: {ns}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not delete namespace {ns}: {e}")
            
            # 3. Delete S3 files if requested (for account deletion)
            if include_s3:
                try:
                    from utils.s3_client import S3Client
                    s3_client = S3Client()
                    prefix = f"intelligent-chat/user_{user_id}/"
                    await s3_client.delete_folder(prefix)
                    logger.info(f"✅ Deleted S3 files for user {user_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to delete S3 files: {e}")
            
            logger.info(f"✅ Completely cleared all data for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to clear complete memories: {str(e)}")
            return False







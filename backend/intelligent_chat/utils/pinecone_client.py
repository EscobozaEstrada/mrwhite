"""
Pinecone Client for vector database operations
"""
import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
import asyncio

from config.settings import settings

logger = logging.getLogger(__name__)


class PineconeClient:
    """Client for Pinecone vector database operations"""
    
    def __init__(self):
        """Initialize Pinecone client"""
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        self.dimension = settings.EMBEDDING_DIMENSION
        
        # Namespace mappings
        self.namespace_documents = settings.PINECONE_NAMESPACE_DOCUMENTS
        self.namespace_vet_reports = settings.PINECONE_NAMESPACE_VET_REPORTS
        self.namespace_conversations = settings.PINECONE_NAMESPACE_CONVERSATIONS
        self.namespace_book_comments = settings.PINECONE_NAMESPACE_BOOK_COMMENTS
        
        # Get or create index
        self._ensure_index_exists()
        self.index = self.pc.Index(self.index_name)
    
    def _ensure_index_exists(self):
        """Ensure the index exists, create if not"""
        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info(f"📊 Creating Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                logger.info(f"✅ Index created: {self.index_name}")
            else:
                logger.info(f"✅ Index exists: {self.index_name}")
                
        except Exception as e:
            logger.error(f"❌ Failed to ensure index exists: {str(e)}")
            raise
    
    async def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str
    ) -> Dict[str, int]:
        """
        Upsert vectors to Pinecone
        
        Args:
            vectors: List of dicts with id, values, metadata
            namespace: Namespace to upsert into
        
        Returns:
            Dict with upserted count
        """
        try:
            # Pinecone SDK is sync, run in executor for async compatibility
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.index.upsert(
                    vectors=vectors,
                    namespace=namespace
                )
            )
            
            logger.info(f"✅ Upserted {result.upserted_count} vectors to namespace '{namespace}'")
            return {"upserted_count": result.upserted_count}
            
        except Exception as e:
            logger.error(f"❌ Failed to upsert vectors: {str(e)}")
            raise
    
    async def query_vectors(
        self,
        query_vector: List[float],
        namespace: str,
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_values: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Query vectors from Pinecone
        
        Args:
            query_vector: Query embedding vector
            namespace: Namespace to query
            top_k: Number of results to return
            filter: Metadata filters
            include_metadata: Include metadata in results
            include_values: Include vector values in results
        
        Returns:
            List of matches with id, score, metadata
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.index.query(
                    vector=query_vector,
                    namespace=namespace,
                    top_k=top_k,
                    filter=filter,
                    include_metadata=include_metadata,
                    include_values=include_values
                )
            )
            
            matches = []
            for match in result.matches:
                matches.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata if include_metadata else None,
                    "values": match.values if include_values else None
                })
            
            logger.info(f"✅ Retrieved {len(matches)} matches from namespace '{namespace}'")
            return matches
            
        except Exception as e:
            logger.error(f"❌ Failed to query vectors: {str(e)}")
            raise
    
    async def delete_vectors(
        self,
        ids: List[str],
        namespace: str
    ) -> bool:
        """
        Delete vectors by IDs
        
        Args:
            ids: List of vector IDs to delete
            namespace: Namespace to delete from
        
        Returns:
            True if successful
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.index.delete(
                    ids=ids,
                    namespace=namespace
                )
            )
            
            logger.info(f"✅ Deleted {len(ids)} vectors from namespace '{namespace}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete vectors: {str(e)}")
            return False
    
    async def delete_by_filter(
        self,
        filter: Dict[str, Any],
        namespace: str
    ) -> bool:
        """
        Delete vectors by metadata filter
        
        Args:
            filter: Metadata filter
            namespace: Namespace to delete from
        
        Returns:
            True if successful
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.index.delete(
                    filter=filter,
                    namespace=namespace
                )
            )
            
            logger.info(f"✅ Deleted vectors by filter from namespace '{namespace}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete by filter: {str(e)}")
            return False
    
    async def fetch_vectors(
        self,
        ids: List[str],
        namespace: str
    ) -> Dict[str, Any]:
        """
        Fetch vectors by IDs
        
        Args:
            ids: List of vector IDs
            namespace: Namespace to fetch from
        
        Returns:
            Dict of vectors
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.index.fetch(
                    ids=ids,
                    namespace=namespace
                )
            )
            
            vectors = {}
            for vid, vector_data in result.vectors.items():
                vectors[vid] = {
                    "id": vector_data.id,
                    "values": vector_data.values,
                    "metadata": vector_data.metadata
                }
            
            logger.info(f"✅ Fetched {len(vectors)} vectors from namespace '{namespace}'")
            return vectors
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch vectors: {str(e)}")
            raise
    
    async def get_index_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get index statistics
        
        Args:
            namespace: Optional namespace to filter stats
        
        Returns:
            Index statistics
        """
        try:
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                None,
                lambda: self.index.describe_index_stats()
            )
            
            if namespace:
                namespace_stats = stats.namespaces.get(namespace, {})
                return {
                    "namespace": namespace,
                    "vector_count": namespace_stats.vector_count if namespace_stats else 0
                }
            
            total_vectors = sum(ns.vector_count for ns in stats.namespaces.values())
            return {
                "total_vectors": total_vectors,
                "dimension": stats.dimension,
                "namespaces": {
                    ns_name: {"vector_count": ns.vector_count}
                    for ns_name, ns in stats.namespaces.items()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get index stats: {str(e)}")
            raise
    
    async def clear_namespace(self, namespace: str) -> bool:
        """
        Clear all vectors in a namespace
        
        Args:
            namespace: Namespace to clear
        
        Returns:
            True if successful
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.index.delete(
                    delete_all=True,
                    namespace=namespace
                )
            )
            
            logger.info(f"✅ Cleared namespace '{namespace}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to clear namespace: {str(e)}")
            return False
    
    def get_namespace_for_type(self, content_type: str) -> str:
        """
        Get appropriate namespace for content type
        
        Args:
            content_type: Type of content
        
        Returns:
            Namespace string
        """
        namespace_map = {
            "document": self.namespace_documents,
            "vet_report": self.namespace_vet_reports,
            "conversation": self.namespace_conversations,
            "book_comment": self.namespace_book_comments,
        }
        
        return namespace_map.get(content_type, self.namespace_documents)







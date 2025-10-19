"""
Common Knowledge Base Service

This service integrates the common knowledge base (Way of the Dog book) 
with existing chat and health AI functionality.
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from flask import current_app

logger = logging.getLogger(__name__)

class CommonKnowledgeService:
    def __init__(self):
        """Initialize the common knowledge service"""
        
        # Pinecone configuration
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        self.index_name = "common-knowledge-base"
        self.namespace = "way-of-the-dog"
        
        # Initialize Pinecone
        try:
            self.pc = Pinecone(api_key=self.pinecone_api_key)
            self.index = self.pc.Index(self.index_name)
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {str(e)}")
            self.pc = None
            self.index = None
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
            chunk_size=1000
        )
        
        # Create vector store
        if self.index:
            self.vectorstore = PineconeVectorStore(
                index=self.index,
                embedding=self.embeddings,
                namespace=self.namespace
            )
        else:
            self.vectorstore = None
            
        self.is_available = self.vectorstore is not None
    
    def is_service_available(self) -> bool:
        """Check if the common knowledge base service is available"""
        return self.is_available
    
    def search_common_knowledge(self, query: str, top_k: int = 5, 
                              min_relevance_score: float = 0.1) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Search the common knowledge base for relevant information
        
        Args:
            query: Search query
            top_k: Number of results to return
            min_relevance_score: Minimum relevance score for results
            
        Returns:
            Tuple of (success, results)
        """
        if not self.is_available:
            logger.warning("Common knowledge base service not available")
            return False, []
        
        try:
            # Perform similarity search
            docs = self.vectorstore.similarity_search_with_score(
                query,
                k=top_k,
                namespace=self.namespace
            )
            
            # Filter by relevance score and format results
            results = []
            for doc, score in docs:
                # Convert distance to similarity score (higher is better)
                similarity_score = 1 - score if score <= 1 else 1 / (1 + score)
                
                if similarity_score >= min_relevance_score:
                    result = {
                        'content': doc.page_content,
                        'metadata': doc.metadata,
                        'relevance_score': similarity_score,
                        'source': doc.metadata.get('source', 'The Way of the Dog Anahata'),
                        'source_type': 'common_knowledge',
                        'chunk_index': doc.metadata.get('chunk_index', 0),
                        'book_title': doc.metadata.get('book_title', 'The Way of the Dog Anahata')
                    }
                    results.append(result)
            
            logger.info(f"Common knowledge search for '{query}' returned {len(results)} relevant results")
            return True, results
            
        except Exception as e:
            logger.error(f"Error searching common knowledge base: {str(e)}")
            return False, []
    
    def search_anahata_specific(self, query: str, top_k: int = 3) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Search for Anahata-specific content with enhanced filtering
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            Tuple of (success, results)
        """
        # Enhance query for Anahata-specific search
        enhanced_query = f"Anahata {query}"
        
        success, results = self.search_common_knowledge(
            enhanced_query, 
            top_k=top_k * 2,  # Get more results to filter
            min_relevance_score=0.6  # Lower threshold for Anahata searches
        )
        
        if not success:
            return False, []
        
        # Filter for Anahata-specific content
        anahata_results = []
        for result in results:
            content_lower = result['content'].lower()
            if any(term in content_lower for term in ['anahata', 'training', 'philosophy', 'approach', 'method']):
                anahata_results.append(result)
        
        return True, anahata_results[:top_k]
    
    def get_contextual_information(self, query: str, context_type: str = "general") -> Dict[str, Any]:
        """
        Get contextual information from the common knowledge base
        
        Args:
            query: Search query
            context_type: Type of context (general, training, philosophy, health)
            
        Returns:
            Dictionary with contextual information
        """
        if not self.is_available:
            return {
                'available': False,
                'context': [],
                'summary': "Common knowledge base not available"
            }
        
        # Adjust search based on context type
        if context_type == "training":
            enhanced_query = f"dog training methods {query}"
        elif context_type == "philosophy":
            enhanced_query = f"Anahata philosophy approach {query}"
        elif context_type == "health":
            enhanced_query = f"dog health care {query}"
        else:
            enhanced_query = query
        
        success, results = self.search_common_knowledge(enhanced_query, top_k=3)
        
        if not success or not results:
            return {
                'available': True,
                'context': [],
                'summary': f"No relevant information found for '{query}'"
            }
        
        # Create summary from results
        context_snippets = [result['content'][:300] + "..." for result in results]
        summary = f"Found {len(results)} relevant references from 'The Way of the Dog Anahata'"
        
        return {
            'available': True,
            'context': results,
            'context_snippets': context_snippets,
            'summary': summary,
            'source_book': "The Way of the Dog Anahata"
        }
    
    def enhance_query_with_common_knowledge(self, original_query: str, 
                                          max_context_length: int = 1000) -> Dict[str, Any]:
        """
        Enhance a query with relevant context from the common knowledge base
        
        Args:
            original_query: Original user query
            max_context_length: Maximum length of context to include
            
        Returns:
            Dictionary with enhanced query information
        """
        if not self.is_available:
            return {
                'enhanced_query': original_query,
                'common_knowledge_context': "",
                'sources_used': [],
                'enhancement_applied': False
            }
        
        # Search for relevant context
        success, results = self.search_common_knowledge(original_query, top_k=3)
        
        if not success or not results:
            return {
                'enhanced_query': original_query,
                'common_knowledge_context': "",
                'sources_used': [],
                'enhancement_applied': False
            }
        
        # Build context from results
        context_parts = []
        sources_used = []
        current_length = 0
        
        for result in results:
            content = result['content']
            if current_length + len(content) <= max_context_length:
                context_parts.append(content)
                sources_used.append({
                    'source': result['source'],
                    'chunk_index': result['chunk_index'],
                    'relevance_score': result['relevance_score']
                })
                current_length += len(content)
            else:
                # Add partial content if it fits
                remaining_space = max_context_length - current_length
                if remaining_space > 100:  # Only add if meaningful
                    context_parts.append(content[:remaining_space] + "...")
                    sources_used.append({
                        'source': result['source'],
                        'chunk_index': result['chunk_index'],
                        'relevance_score': result['relevance_score'],
                        'partial': True
                    })
                break
        
        common_knowledge_context = "\n\n".join(context_parts)
        
        # Create enhanced query
        enhanced_query = f"""
Original Query: {original_query}

Relevant Context from 'The Way of the Dog Anahata':
{common_knowledge_context}

Please provide a comprehensive response that considers both the specific query and the relevant context from the book.
        """.strip()
        
        return {
            'enhanced_query': enhanced_query,
            'common_knowledge_context': common_knowledge_context,
            'sources_used': sources_used,
            'enhancement_applied': True,
            'context_length': len(common_knowledge_context)
        }
    
    def get_book_overview(self) -> Dict[str, Any]:
        """Get an overview of the book content"""
        if not self.is_available:
            return {
                'available': False,
                'overview': "Common knowledge base not available"
            }
        
        try:
            # Get index stats
            stats = self.index.describe_index_stats()
            namespace_stats = stats.namespaces.get(self.namespace, {})
            
            # Search for overview content
            overview_queries = [
                "Anahata introduction overview",
                "book summary main concepts",
                "dog training philosophy"
            ]
            
            overview_content = []
            for query in overview_queries:
                success, results = self.search_common_knowledge(query, top_k=2)
                if success and results:
                    overview_content.extend(results)
            
            return {
                'available': True,
                'vector_count': namespace_stats.get('vector_count', 0),
                'book_title': "The Way of the Dog Anahata",
                'content_samples': overview_content[:3],
                'overview': f"Knowledge base contains {namespace_stats.get('vector_count', 0)} chunks from 'The Way of the Dog Anahata'"
            }
            
        except Exception as e:
            logger.error(f"Error getting book overview: {str(e)}")
            return {
                'available': False,
                'overview': f"Error accessing book overview: {str(e)}"
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the common knowledge service"""
        try:
            if not self.is_available:
                return {
                    'status': 'unavailable',
                    'message': 'Common knowledge base service not initialized',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Test search
            success, results = self.search_common_knowledge("test", top_k=1)
            
            if success:
                # Get index stats
                stats = self.index.describe_index_stats()
                namespace_stats = stats.namespaces.get(self.namespace, {})
                
                return {
                    'status': 'healthy',
                    'message': 'Common knowledge base service operational',
                    'vector_count': namespace_stats.get('vector_count', 0),
                    'test_search_successful': True,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'degraded',
                    'message': 'Common knowledge base accessible but search failed',
                    'test_search_successful': False,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Health check failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }

    def get_relevant_knowledge(self, query: str, top_k: int = 3) -> List[Any]:
        """
        Get relevant knowledge from the common knowledge base
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of relevant knowledge documents
        """
        if not self.is_available:
            return []
        
        try:
            success, results = self.search_common_knowledge(query, top_k=top_k)
            
            if not success or not results:
                return []
            
            # Convert to Document objects for compatibility with other knowledge sources
            from langchain_core.documents import Document
            
            documents = []
            for result in results:
                documents.append(Document(
                    page_content=result['content'],
                    metadata={
                        'source': result['source'],
                        'source_type': 'common_knowledge',
                        'relevance_score': result['relevance_score'],
                        'book_title': result['book_title']
                    }
                ))
            
            return documents
            
        except Exception as e:
            current_app.logger.error(f"Error getting relevant knowledge: {str(e)}")
            return []

# Global instance
common_knowledge_service = CommonKnowledgeService()

def get_common_knowledge_service() -> CommonKnowledgeService:
    """Get the global common knowledge service instance"""
    return common_knowledge_service

"""
Embedding generation service using AWS Bedrock
"""
import logging
import json
from typing import List, Union
import boto3
from botocore.exceptions import ClientError

from config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using AWS Bedrock"""
    
    def __init__(self):
        """Initialize Bedrock client"""
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.model_id = settings.BEDROCK_EMBEDDING_MODEL_ID
        self.dimension = settings.EMBEDDING_DIMENSION
        self.max_tokens = settings.EMBEDDING_MAX_TOKENS
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector (1024 dimensions for Titan)
        """
        # Truncate if too long
        if len(text) > self.max_tokens * 4:  # Rough character estimate
            text = text[:self.max_tokens * 4]
            logger.warning(f"⚠️  Text truncated to {self.max_tokens * 4} characters")
        
        try:
            # Prepare request body for Titan embeddings
            request_body = {
                "inputText": text
            }
            
            # Invoke model
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding')
            
            if not embedding:
                raise Exception("No embedding returned from model")
            
            logger.debug(f"✅ Generated embedding (dim={len(embedding)})")
            return embedding
            
        except ClientError as e:
            logger.error(f"❌ Bedrock embedding failed: {str(e)}")
            raise Exception(f"Failed to generate embedding: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Embedding generation error: {str(e)}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of input texts
            batch_size: Number of texts to process at once
        
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            for text in batch:
                try:
                    embedding = await self.generate_embedding(text)
                    embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"❌ Failed to generate embedding for text {i}: {str(e)}")
                    # Use zero vector as fallback
                    embeddings.append([0.0] * self.dimension)
        
        logger.info(f"✅ Generated {len(embeddings)} embeddings")
        return embeddings
    
    async def generate_contextual_embedding(self, chunk: str, context: str) -> List[float]:
        """
        Generate embedding with additional context (for contextual retrieval)
        
        Args:
            chunk: Text chunk to embed
            context: Contextual information (e.g., document title, metadata)
        
        Returns:
            Embedding vector
        """
        # Combine context + chunk for richer embedding
        enriched_text = f"{context}\n\n{chunk}"
        
        return await self.generate_embedding(enriched_text)
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
        
        Returns:
            Cosine similarity score (0-1)
        """
        import numpy as np
        
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)







"""
Chunking Service
Splits text into chunks for embedding and storage
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for chunking text into manageable pieces"""
    
    def __init__(self):
        self.chunk_size = 1000  # characters per chunk
        self.chunk_overlap = 200  # overlap between chunks for context
    
    async def chunk_text(
        self,
        text: str,
        document_id: int,
        filename: str
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks with overlap
        
        Args:
            text: Full text to chunk
            document_id: ID of the document
            filename: Name of the file
        
        Returns:
            List of chunks with metadata
        """
        try:
            if not text or not text.strip():
                logger.warning(f"Empty text for document {document_id}")
                return []
            
            chunks = []
            text_length = len(text)
            start = 0
            chunk_index = 0
            
            while start < text_length:
                # Get chunk with overlap
                end = start + self.chunk_size
                chunk_text = text[start:end]
                
                # Try to break at sentence or word boundary
                if end < text_length:
                    # Look for sentence end
                    last_period = chunk_text.rfind('.')
                    last_newline = chunk_text.rfind('\n')
                    last_space = chunk_text.rfind(' ')
                    
                    break_point = max(last_period, last_newline, last_space)
                    
                    if break_point > self.chunk_size * 0.5:  # At least 50% of chunk size
                        chunk_text = chunk_text[:break_point + 1]
                        end = start + len(chunk_text)
                
                # Create chunk metadata
                chunk = {
                    "text": chunk_text.strip(),
                    "chunk_index": chunk_index,
                    "start_char": start,
                    "end_char": end,
                    "document_id": document_id,
                    "filename": filename
                }
                
                chunks.append(chunk)
                
                # Move to next chunk with overlap
                start = end - self.chunk_overlap
                chunk_index += 1
            
            logger.info(f"✅ Created {len(chunks)} chunks for document {document_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Chunking failed: {e}")
            raise Exception(f"Failed to chunk text: {str(e)}")


# Singleton instance
chunking_service = ChunkingService()







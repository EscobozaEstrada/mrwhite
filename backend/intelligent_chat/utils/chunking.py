"""
Text chunking service for documents
"""
import logging
from typing import List, Dict, Any
import re

from config.settings import settings

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for intelligently chunking documents"""
    
    def __init__(self):
        """Initialize chunking service"""
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        self.vet_report_chunk_size = settings.VET_REPORT_CHUNK_SIZE
        self.vet_report_chunk_overlap = settings.VET_REPORT_CHUNK_OVERLAP
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = None,
        overlap: int = None,
        is_vet_report: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Chunk text into overlapping segments
        
        Args:
            text: Input text
            chunk_size: Maximum tokens per chunk (default from settings)
            overlap: Token overlap between chunks (default from settings)
            is_vet_report: Use vet report chunking parameters
        
        Returns:
            List of chunks with metadata
        """
        # Use vet report settings if specified
        if is_vet_report:
            chunk_size = self.vet_report_chunk_size
            overlap = self.vet_report_chunk_overlap
        else:
            chunk_size = chunk_size or self.chunk_size
            overlap = overlap or self.chunk_overlap
        
        # Rough token estimate: 1 token ≈ 4 characters
        max_chars = chunk_size * 4
        overlap_chars = overlap * 4
        
        # Split text into paragraphs first
        paragraphs = self._split_paragraphs(text)
        
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            # If single paragraph exceeds chunk size, split it
            if len(para) > max_chars:
                # First, add current chunk if not empty
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_index": chunk_index,
                        "char_count": len(current_chunk),
                        "token_estimate": len(current_chunk) // 4
                    })
                    chunk_index += 1
                    current_chunk = ""
                
                # Split long paragraph by sentences
                sentences = self._split_sentences(para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > max_chars:
                        if current_chunk:
                            chunks.append({
                                "text": current_chunk.strip(),
                                "chunk_index": chunk_index,
                                "char_count": len(current_chunk),
                                "token_estimate": len(current_chunk) // 4
                            })
                            chunk_index += 1
                            
                            # Add overlap from previous chunk
                            overlap_text = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else current_chunk
                            current_chunk = overlap_text + " " + sentence
                        else:
                            # Sentence itself is too long, force split
                            current_chunk = sentence[:max_chars]
                    else:
                        current_chunk += " " + sentence if current_chunk else sentence
            else:
                # Normal paragraph processing
                if len(current_chunk) + len(para) > max_chars:
                    # Save current chunk
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_index": chunk_index,
                        "char_count": len(current_chunk),
                        "token_estimate": len(current_chunk) // 4
                    })
                    chunk_index += 1
                    
                    # Start new chunk with overlap
                    overlap_text = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else current_chunk
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk += "\n\n" + para if current_chunk else para
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_index": chunk_index,
                "char_count": len(current_chunk),
                "token_estimate": len(current_chunk) // 4
            })
        
        # Add total chunks info
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk["total_chunks"] = total_chunks
        
        logger.info(f"✅ Created {total_chunks} chunks from {len(text)} characters")
        return chunks
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Split by double newlines or more
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Split by sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def add_context_to_chunk(
        self,
        chunk_text: str,
        document_name: str,
        document_type: str,
        page_number: int = None,
        chapter: str = None
    ) -> str:
        """
        Add contextual information to chunk (for contextual retrieval)
        
        Args:
            chunk_text: Original chunk text
            document_name: Name of the document
            document_type: Type of document (pdf, docx, etc.)
            page_number: Page number (if available)
            chapter: Chapter name (if available)
        
        Returns:
            Enriched chunk with context
        """
        context_parts = [f"Document: {document_name}"]
        
        if document_type:
            context_parts.append(f"Type: {document_type}")
        
        if page_number:
            context_parts.append(f"Page: {page_number}")
        
        if chapter:
            context_parts.append(f"Section: {chapter}")
        
        context = ", ".join(context_parts)
        
        # Format: Context header + chunk
        enriched_chunk = f"[{context}]\n\n{chunk_text}"
        
        return enriched_chunk
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract keywords from text (simple frequency-based)
        
        Args:
            text: Input text
            top_n: Number of keywords to return
        
        Returns:
            List of keywords
        """
        # Remove punctuation and convert to lowercase
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        
        # Common stop words
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'with', 'was', 'this', 'that', 'from', 'have', 'had', 'they', 'will', 'been', 'has', 'can', 'about', 'into', 'than', 'them', 'out', 'only', 'more', 'when', 'over', 'such', 'should', 'our', 'there', 'their'}
        
        # Filter stop words
        words = [w for w in words if w not in stop_words]
        
        # Count frequency
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top N
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, freq in sorted_words[:top_n]]







import logging
import re
import uuid
from typing import List, Dict, Any, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class ContentChunk:
    """Represents a chunk of content with metadata for processing"""
    
    def __init__(self, content: str, chunk_id: str, order: int, 
                 start_pos: int, end_pos: int, overlap_before: str = "", overlap_after: str = ""):
        self.content = content
        self.chunk_id = chunk_id
        self.order = order
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.overlap_before = overlap_before
        self.overlap_after = overlap_after
        self.processed_content = None
        self.is_processed = False
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for serialization"""
        return {
            "chunk_id": self.chunk_id,
            "order": self.order,
            "content": self.content,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "overlap_before": self.overlap_before,
            "overlap_after": self.overlap_after,
            "processed_content": self.processed_content,
            "is_processed": self.is_processed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentChunk':
        """Create chunk from dictionary"""
        chunk = cls(
            content=data["content"],
            chunk_id=data["chunk_id"],
            order=data["order"],
            start_pos=data["start_pos"],
            end_pos=data["end_pos"],
            overlap_before=data.get("overlap_before", ""),
            overlap_after=data.get("overlap_after", "")
        )
        chunk.processed_content = data.get("processed_content")
        chunk.is_processed = data.get("is_processed", False)
        return chunk


class ContentChunkingService:
    """Service for chunking and merging content for AI processing"""
    
    def __init__(self):
        pass
    
    def chunk_content(self, content: str, max_chunk_size: int = 1500, 
                     overlap_percentage: float = 0.15) -> List[ContentChunk]:
        """
        Split content into chunks with overlap
        
        Args:
            content: The full content to chunk
            max_chunk_size: Maximum size of each chunk in characters
            overlap_percentage: Percentage of overlap between chunks (0.0-1.0)
            
        Returns:
            List of ContentChunk objects
        """
        if not content:
            logger.warning("Empty content provided for chunking")
            return []
        
        # Find paragraph boundaries
        paragraphs = self._split_into_paragraphs(content)
        
        # Calculate overlap size
        overlap_size = int(max_chunk_size * overlap_percentage)
        effective_chunk_size = max_chunk_size - overlap_size
        
        chunks = []
        current_chunk_content = ""
        current_start_pos = 0
        current_pos = 0
        chunk_order = 0
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed the chunk size,
            # finalize the current chunk and start a new one
            if len(current_chunk_content) + len(paragraph) > effective_chunk_size and current_chunk_content:
                # Create overlap for next chunk
                overlap_text = current_chunk_content[-overlap_size:] if len(current_chunk_content) > overlap_size else current_chunk_content
                
                # Create the chunk
                chunk = ContentChunk(
                    content=current_chunk_content,
                    chunk_id=str(uuid.uuid4()),
                    order=chunk_order,
                    start_pos=current_start_pos,
                    end_pos=current_pos,
                    overlap_after=overlap_text
                )
                
                # Add the chunk to our list
                chunks.append(chunk)
                
                # Start new chunk with overlap
                current_chunk_content = overlap_text
                current_start_pos = current_pos - len(overlap_text)
                chunk_order += 1
            
            # Add paragraph to current chunk
            current_chunk_content += paragraph
            current_pos += len(paragraph)
        
        # Add the last chunk if there's content left
        if current_chunk_content:
            chunk = ContentChunk(
                content=current_chunk_content,
                chunk_id=str(uuid.uuid4()),
                order=chunk_order,
                start_pos=current_start_pos,
                end_pos=current_pos
            )
            chunks.append(chunk)
        
        # Set overlap_before for chunks after the first one
        for i in range(1, len(chunks)):
            chunks[i].overlap_before = chunks[i-1].overlap_after
        
        logger.info(f"Split content into {len(chunks)} chunks")
        return chunks
    
    def _split_into_paragraphs(self, content: str) -> List[str]:
        """
        Split content into paragraphs, preserving paragraph boundaries
        """
        # Split by double newlines (paragraph boundaries)
        paragraphs = re.split(r'(\n\s*\n)', content)
        
        # Recombine the split parts to keep the separators
        result = []
        for i in range(0, len(paragraphs), 2):
            paragraph = paragraphs[i]
            separator = paragraphs[i+1] if i+1 < len(paragraphs) else ""
            result.append(paragraph + separator)
        
        return result
    
    def merge_processed_chunks(self, chunks: List[ContentChunk]) -> str:
        """
        Merge processed chunks back into a single content string
        
        Args:
            chunks: List of processed ContentChunk objects
            
        Returns:
            Merged content string
        """
        if not chunks:
            return ""
        
        # Sort chunks by order
        sorted_chunks = sorted(chunks, key=lambda x: x.order)
        
        # Check if all chunks are processed
        unprocessed = [chunk.chunk_id for chunk in sorted_chunks if not chunk.is_processed]
        if unprocessed:
            logger.warning(f"Some chunks are not processed: {unprocessed}")
        
        # Use the processed content if available, otherwise use original content
        result = ""
        
        for i, chunk in enumerate(sorted_chunks):
            content = chunk.processed_content if chunk.is_processed and chunk.processed_content else chunk.content
            
            # For all chunks except the first one, remove the overlap from the beginning
            if i > 0 and chunk.overlap_before:
                # Find where the overlap ends in the current content
                overlap_end = self._find_overlap_end(chunk.overlap_before, content)
                if overlap_end > 0:
                    content = content[overlap_end:]
            
            result += content
        
        return result
    
    def _find_overlap_end(self, overlap_text: str, content: str) -> int:
        """
        Find where the overlap text ends in the content
        Returns the position after the overlap
        """
        # Use difflib to find the best match for the overlap text
        matcher = SequenceMatcher(None, overlap_text, content[:len(overlap_text)*2])
        match = matcher.find_longest_match(0, len(overlap_text), 0, len(content[:len(overlap_text)*2]))
        
        if match.size > len(overlap_text) * 0.7:  # If we found a good match (70% of overlap)
            return match.b + match.size
        
        return 0
    
    def resolve_conflicts(self, chunk1: ContentChunk, chunk2: ContentChunk) -> Tuple[str, str]:
        """
        Resolve conflicts in overlapping regions between two chunks
        
        Args:
            chunk1: First chunk
            chunk2: Second chunk
            
        Returns:
            Tuple of (resolved_content1, resolved_content2)
        """
        # Get processed content or fall back to original
        content1 = chunk1.processed_content if chunk1.is_processed and chunk1.processed_content else chunk1.content
        content2 = chunk2.processed_content if chunk2.is_processed and chunk2.processed_content else chunk2.content
        
        # If there's no overlap, just return the original content
        if not chunk1.overlap_after or not chunk2.overlap_before:
            return content1, content2
        
        # Find the overlap region in both chunks
        overlap = chunk1.overlap_after
        
        # Find where the overlap appears in both contents
        overlap_end1 = len(content1)
        overlap_start2 = 0
        
        # Use sequence matcher to find the best match for the overlap
        matcher1 = SequenceMatcher(None, content1[-len(overlap)*2:], overlap)
        match1 = matcher1.find_longest_match(0, len(content1[-len(overlap)*2:]), 0, len(overlap))
        
        matcher2 = SequenceMatcher(None, overlap, content2[:len(overlap)*2])
        match2 = matcher2.find_longest_match(0, len(overlap), 0, len(content2[:len(overlap)*2]))
        
        if match1.size > 0:
            overlap_end1 = len(content1) - len(content1[-len(overlap)*2:]) + match1.a
        
        if match2.size > 0:
            overlap_start2 = match2.b + match2.size
        
        # If the overlap regions are identical, no conflict resolution needed
        if content1[overlap_end1-len(overlap):overlap_end1] == content2[0:overlap_start2]:
            return content1, content2
        
        # Determine which version to use based on edit significance
        # Here we're using a simple heuristic: prefer the version with more changes
        # A more sophisticated approach would analyze the semantic changes
        
        # Calculate how different each processed version is from the original
        orig_overlap = overlap
        proc_overlap1 = content1[overlap_end1-len(overlap):overlap_end1]
        proc_overlap2 = content2[0:overlap_start2]
        
        diff1 = SequenceMatcher(None, orig_overlap, proc_overlap1).ratio()
        diff2 = SequenceMatcher(None, orig_overlap, proc_overlap2).ratio()
        
        # The version with lower similarity ratio has more changes
        if diff1 <= diff2:
            # Use version from chunk1
            return content1, content2[overlap_start2:]
        else:
            # Use version from chunk2
            return content1[:overlap_end1-len(overlap)], content2
    
    def get_chunk_for_edit(self, content: str, edit_query: str, chunks: List[ContentChunk]) -> List[ContentChunk]:
        """
        Find the most relevant chunks for an edit query
        
        Args:
            content: Full content
            edit_query: User's edit query
            chunks: List of content chunks
            
        Returns:
            List of relevant chunks to process
        """
        # For global edits that affect the entire content
        global_edit_keywords = [
            "all", "entire", "throughout", "everywhere", "whole", 
            "complete", "full", "every", "change all", "replace all",
            "style", "tone", "voice", "format", "rewrite"
        ]
        
        # Check if this is a global edit
        is_global_edit = any(keyword in edit_query.lower() for keyword in global_edit_keywords)
        
        if is_global_edit:
            logger.info("Detected global edit request, processing all chunks")
            return chunks
        
        # For targeted edits, try to find the most relevant chunk(s)
        # Extract key terms from the edit query
        import re
        from collections import Counter
        
        # Extract important words (nouns, verbs, adjectives)
        words = re.findall(r'\b\w{3,}\b', edit_query.lower())
        word_counts = Counter(words)
        
        # Score each chunk based on keyword matches
        chunk_scores = []
        for chunk in chunks:
            score = 0
            for word, count in word_counts.items():
                score += chunk.content.lower().count(word) * count
            chunk_scores.append((chunk, score))
        
        # Sort chunks by relevance score
        sorted_chunks = [chunk for chunk, score in sorted(chunk_scores, key=lambda x: x[1], reverse=True)]
        
        # Return the most relevant chunks (at least 1, at most 3)
        relevant_chunks = sorted_chunks[:min(3, len(sorted_chunks))]
        if not relevant_chunks:
            # Fallback to the first chunk if no relevant chunks found
            relevant_chunks = [chunks[0]]
        
        logger.info(f"Selected {len(relevant_chunks)} relevant chunks for targeted edit")
        return relevant_chunks 
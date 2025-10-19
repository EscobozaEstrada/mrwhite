#!/usr/bin/env python3
"""
Book Indexing Script - Process and index "The Way of the Dog" into Pinecone

This script:
1. Extracts text from the PDF
2. Intelligently chunks the content
3. Detects chapters and topics
4. Generates embeddings with contextual retrieval
5. Stores in Pinecone 'book-content-{env}' namespace

Usage:
    python scripts/index_book.py --pdf path/to/book.pdf --namespace book-content-prod
"""

import sys
import os
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
script_dir = Path(__file__).parent
env_local = script_dir.parent / ".env.local"
env_parent = script_dir.parent.parent / ".env"

if env_local.exists():
    load_dotenv(env_local)
    print(f"✅ Loaded environment from: {env_local}")
else:
    load_dotenv(env_parent)
    print(f"✅ Loaded environment from: {env_parent}")

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyPDF2 import PdfReader
from utils.embeddings import EmbeddingService
from utils.pinecone_client import PineconeClient
from config.settings import settings

print("✅ Imports successful")


class BookProcessor:
    """Process and index a book into Pinecone"""
    
    def __init__(self, pdf_path: str, namespace: str):
        self.pdf_path = pdf_path
        self.namespace = namespace
        self.embeddings = EmbeddingService()
        self.pinecone = PineconeClient()
        
        # Topic keywords for classification
        self.topic_keywords = {
            "training": ["train", "training", "command", "obedience", "discipline", "teach", "learn", "practice"],
            "behavior": ["behavior", "behaviour", "bark", "aggression", "anxiety", "fear", "socialization", "reactive"],
            "health": ["health", "medical", "vet", "veterinary", "illness", "disease", "symptom", "medication", "vaccine"],
            "nutrition": ["food", "diet", "nutrition", "feed", "eating", "meal", "vitamin", "supplement"],
            "exercise": ["exercise", "walk", "play", "activity", "physical", "fitness", "energy"],
            "grooming": ["groom", "grooming", "brush", "bath", "clean", "hygiene", "coat", "fur"],
            "psychology": ["psychology", "mind", "emotion", "mental", "consciousness", "awareness", "spirit"],
            "bonding": ["bond", "bonding", "relationship", "trust", "connection", "love", "attachment"],
            "communication": ["communicate", "communication", "language", "signal", "body language", "understand"]
        }
    
    def extract_text_from_pdf(self) -> List[Dict[str, Any]]:
        """Extract text from PDF page by page"""
        print(f"\n📖 Reading PDF: {self.pdf_path}")
        
        try:
            reader = PdfReader(self.pdf_path)
            total_pages = len(reader.pages)
            print(f"📄 Total pages: {total_pages}")
            
            pages_data = []
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                
                if text and len(text.strip()) > 50:  # Skip mostly empty pages
                    pages_data.append({
                        "page": page_num,
                        "text": text.strip(),
                        "word_count": len(text.split())
                    })
                
                # Progress indicator
                if page_num % 10 == 0:
                    print(f"  Processed {page_num}/{total_pages} pages...")
            
            print(f"✅ Extracted text from {len(pages_data)} pages")
            return pages_data
            
        except Exception as e:
            print(f"❌ Error reading PDF: {e}")
            raise
    
    def detect_chapter(self, text: str, page_num: int) -> Optional[str]:
        """Detect chapter titles from text"""
        # Look for common chapter patterns
        patterns = [
            r'^CHAPTER\s+\d+[:\s]+(.+)',
            r'^Chapter\s+\d+[:\s]+(.+)',
            r'^\d+\.\s+([A-Z][^.]+)',
            r'^([A-Z][A-Z\s]{10,50})\s*$',  # All caps titles
        ]
        
        lines = text.split('\n')[:5]  # Check first 5 lines
        
        for line in lines:
            line = line.strip()
            for pattern in patterns:
                match = re.search(pattern, line, re.MULTILINE)
                if match:
                    chapter_title = match.group(1).strip() if match.lastindex else match.group(0).strip()
                    if len(chapter_title) < 100:  # Reasonable chapter title length
                        return chapter_title
        
        return None
    
    def detect_topics(self, text: str) -> List[str]:
        """Detect topics from text based on keywords"""
        text_lower = text.lower()
        detected_topics = []
        
        for topic, keywords in self.topic_keywords.items():
            # Count keyword matches
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches >= 2:  # At least 2 keyword matches
                detected_topics.append(topic)
        
        return detected_topics if detected_topics else ["general"]
    
    def chunk_text(self, pages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Chunk text intelligently by sections and paragraphs"""
        print("\n✂️ Chunking text...")
        
        chunks = []
        current_chunk = ""
        current_page = None
        current_chapter = "Introduction"
        chunk_index = 0
        
        # Target chunk size (in characters)
        min_chunk_size = 500
        max_chunk_size = 2000
        
        for page_data in pages_data:
            page_num = page_data["page"]
            text = page_data["text"]
            
            # Check for chapter title
            detected_chapter = self.detect_chapter(text, page_num)
            if detected_chapter:
                # Save current chunk before starting new chapter
                if current_chunk and len(current_chunk) >= min_chunk_size:
                    chunks.append({
                        "chunk_id": f"book_page_{current_page}_chunk_{chunk_index}",
                        "text": current_chunk.strip(),
                        "page": current_page,
                        "chapter": current_chapter,
                        "topics": self.detect_topics(current_chunk),
                        "chunk_index": chunk_index
                    })
                    chunk_index += 1
                    current_chunk = ""
                
                current_chapter = detected_chapter
                print(f"  📑 Found chapter: {current_chapter} (page {page_num})")
            
            # Split by paragraphs
            paragraphs = text.split('\n\n')
            
            for para in paragraphs:
                para = para.strip()
                if not para or len(para) < 50:
                    continue
                
                # Add to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                    current_page = page_num
                
                # Check if chunk is ready
                if len(current_chunk) >= max_chunk_size:
                    chunks.append({
                        "chunk_id": f"book_page_{current_page}_chunk_{chunk_index}",
                        "text": current_chunk.strip(),
                        "page": current_page,
                        "chapter": current_chapter,
                        "topics": self.detect_topics(current_chunk),
                        "chunk_index": chunk_index
                    })
                    chunk_index += 1
                    current_chunk = ""
                    current_page = None
        
        # Add final chunk
        if current_chunk and len(current_chunk) >= min_chunk_size:
            chunks.append({
                "chunk_id": f"book_page_{current_page}_chunk_{chunk_index}",
                "text": current_chunk.strip(),
                "page": current_page,
                "chapter": current_chapter,
                "topics": self.detect_topics(current_chunk),
                "chunk_index": chunk_index
            })
        
        print(f"✅ Created {len(chunks)} chunks")
        
        # Print statistics
        chapters = set(chunk["chapter"] for chunk in chunks)
        print(f"📚 Detected {len(chapters)} chapters")
        
        topics_count = {}
        for chunk in chunks:
            for topic in chunk["topics"]:
                topics_count[topic] = topics_count.get(topic, 0) + 1
        
        print(f"🏷️ Topic distribution:")
        for topic, count in sorted(topics_count.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {topic}: {count} chunks")
        
        return chunks
    
    async def generate_embeddings_and_upsert(self, chunks: List[Dict[str, Any]]) -> None:
        """Generate embeddings with contextual retrieval and upsert to Pinecone"""
        print(f"\n🧠 Generating embeddings and uploading to Pinecone...")
        print(f"📍 Namespace: {self.namespace}")
        
        batch_size = 100
        total_chunks = len(chunks)
        
        for i in range(0, total_chunks, batch_size):
            batch = chunks[i:i + batch_size]
            vectors = []
            
            for chunk in batch:
                # Create context for contextual retrieval
                context = f"""
Book: The Way of the Dog by Anahata Graceland
Chapter: {chunk['chapter']}
Page: {chunk['page']}
Topics: {', '.join(chunk['topics'])}
                """.strip()
                
                # Generate contextual embedding
                embedding = await self.embeddings.generate_contextual_embedding(
                    chunk=chunk["text"],
                    context=context
                )
                
                # Prepare vector for Pinecone
                vectors.append({
                    "id": chunk["chunk_id"],
                    "values": embedding,
                    "metadata": {
                        "text": chunk["text"][:1000],  # Store preview (Pinecone limit)
                        "page": chunk["page"],
                        "chapter": chunk["chapter"],
                        "topics": chunk["topics"],
                        "source": "The Way of the Dog",
                        "author": "Anahata Graceland",
                        "content_type": "book",
                        "chunk_index": chunk["chunk_index"],
                        "indexed_at": datetime.utcnow().isoformat()
                    }
                })
            
            # Upsert batch to Pinecone
            await self.pinecone.upsert_vectors(
                vectors=vectors,
                namespace=self.namespace
            )
            
            progress = min(i + batch_size, total_chunks)
            print(f"  ✅ Uploaded {progress}/{total_chunks} chunks ({progress * 100 // total_chunks}%)")
        
        print(f"✅ Successfully indexed {total_chunks} chunks to Pinecone!")
    
    async def process_and_index(self) -> Dict[str, Any]:
        """Main processing pipeline"""
        print("=" * 70)
        print("📚 BOOK INDEXING PIPELINE")
        print("=" * 70)
        print(f"Book: The Way of the Dog by Anahata Graceland")
        print(f"PDF: {self.pdf_path}")
        print(f"Namespace: {self.namespace}")
        print("=" * 70)
        
        start_time = datetime.now()
        
        # Step 1: Extract text
        pages_data = self.extract_text_from_pdf()
        
        # Step 2: Chunk text
        chunks = self.chunk_text(pages_data)
        
        # Step 3: Generate embeddings and upload
        await self.generate_embeddings_and_upsert(chunks)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Summary
        summary = {
            "total_pages": len(pages_data),
            "total_chunks": len(chunks),
            "namespace": self.namespace,
            "duration_seconds": duration,
            "indexed_at": end_time.isoformat()
        }
        
        print("\n" + "=" * 70)
        print("✅ INDEXING COMPLETE!")
        print("=" * 70)
        print(f"📄 Total pages processed: {summary['total_pages']}")
        print(f"✂️ Total chunks created: {summary['total_chunks']}")
        print(f"⏱️ Time taken: {duration:.2f} seconds")
        print(f"📍 Pinecone namespace: {summary['namespace']}")
        print("=" * 70)
        
        # Save summary
        summary_path = Path(__file__).parent / "book_index_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"📝 Summary saved to: {summary_path}")
        
        return summary


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Index 'The Way of the Dog' book into Pinecone")
    parser.add_argument(
        "--pdf",
        type=str,
        default="../../../frontend/public/books/the-way-of-the-dog-anahata.pdf",
        help="Path to the PDF file"
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default=f"book-content-{settings.ENVIRONMENT}",
        help="Pinecone namespace to use"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process book but don't upload to Pinecone (for testing)"
    )
    
    args = parser.parse_args()
    
    # Resolve PDF path
    script_dir = Path(__file__).parent
    pdf_path = (script_dir / args.pdf).resolve()
    
    if not pdf_path.exists():
        print(f"❌ Error: PDF not found at {pdf_path}")
        return 1
    
    print(f"✅ Found PDF: {pdf_path}")
    
    # Process and index
    processor = BookProcessor(str(pdf_path), args.namespace)
    
    if args.dry_run:
        print("\n🧪 DRY RUN MODE - Will not upload to Pinecone")
        pages_data = processor.extract_text_from_pdf()
        chunks = processor.chunk_text(pages_data)
        print(f"\n✅ Dry run complete: {len(chunks)} chunks would be created")
        return 0
    
    try:
        summary = await processor.process_and_index()
        return 0
    except Exception as e:
        print(f"\n❌ Error during indexing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


#!/usr/bin/env python3
"""
Common Knowledge Base Creator

This script processes the "Way of the Dog" book and stores it in Pinecone
as a common knowledge base that will be searched for all queries.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import hashlib

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.schema import Document
import pinecone
from pinecone import Pinecone
import PyPDF2
import fitz  # PyMuPDF - better for text extraction

# Import app configuration
from app import create_app
from app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CommonKnowledgeBaseCreator:
    def __init__(self):
        """Initialize the knowledge base creator"""
        self.app = create_app()
        self.app.app_context().push()
        
        # Pinecone configuration
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        self.index_name = "common-knowledge-base"
        self.namespace = "way-of-the-dog"
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
            chunk_size=1000
        )
        
        # Text splitter configuration
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def create_pinecone_index(self):
        """Create or ensure Pinecone index exists"""
        try:
            # Check if index exists
            existing_indexes = [index.name for index in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating new Pinecone index: {self.index_name}")
                
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1536,  # OpenAI ada-002 embedding dimension
                    metric="cosine",
                    spec={
                        "serverless": {
                            "cloud": "aws",
                            "region": self.pinecone_environment
                        }
                    }
                )
                logger.info(f"Successfully created index: {self.index_name}")
            else:
                logger.info(f"Index {self.index_name} already exists")
                
            return True
            
        except Exception as e:
            logger.error(f"Error creating Pinecone index: {str(e)}")
            return False
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using PyMuPDF for better text extraction"""
        try:
            logger.info(f"Extracting text from PDF: {pdf_path}")
            
            # Open PDF with PyMuPDF
            doc = fitz.open(pdf_path)
            text_content = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                
                # Clean up the text
                text = text.replace('\n\n\n', '\n\n')  # Remove excessive line breaks
                text = text.replace('\t', ' ')  # Replace tabs with spaces
                
                text_content += f"\n--- Page {page_num + 1} ---\n{text}\n"
            
            doc.close()
            
            logger.info(f"Successfully extracted {len(text_content)} characters from PDF")
            return text_content
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            
            # Fallback to PyPDF2
            try:
                logger.info("Trying fallback extraction with PyPDF2...")
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text_content = ""
                    
                    for page_num, page in enumerate(reader.pages):
                        text = page.extract_text()
                        text_content += f"\n--- Page {page_num + 1} ---\n{text}\n"
                
                logger.info(f"Fallback extraction successful: {len(text_content)} characters")
                return text_content
                
            except Exception as fallback_error:
                logger.error(f"Fallback extraction also failed: {str(fallback_error)}")
                raise
    
    def create_document_chunks(self, text_content: str, pdf_path: str) -> List[Document]:
        """Split text into chunks and create Document objects"""
        try:
            logger.info("Creating document chunks...")
            
            # Split the text into chunks
            text_chunks = self.text_splitter.split_text(text_content)
            
            # Create Document objects with metadata
            documents = []
            for i, chunk in enumerate(text_chunks):
                # Create a unique ID for this chunk
                chunk_id = hashlib.md5(f"{pdf_path}_{i}_{chunk[:100]}".encode()).hexdigest()
                
                metadata = {
                    "source": "The Way of the Dog Anahata",
                    "source_type": "book",
                    "chunk_index": i,
                    "total_chunks": len(text_chunks),
                    "file_path": pdf_path,
                    "chunk_id": chunk_id,
                    "created_at": datetime.now().isoformat(),
                    "knowledge_base": "common",
                    "category": "general_knowledge",
                    "book_title": "The Way of the Dog Anahata",
                    "content_type": "educational_content"
                }
                
                doc = Document(
                    page_content=chunk,
                    metadata=metadata
                )
                documents.append(doc)
            
            logger.info(f"Created {len(documents)} document chunks")
            return documents
            
        except Exception as e:
            logger.error(f"Error creating document chunks: {str(e)}")
            raise
    
    def store_in_pinecone(self, documents: List[Document]) -> bool:
        """Store documents in Pinecone vector database"""
        try:
            logger.info(f"Storing {len(documents)} documents in Pinecone...")
            
            # Connect to the index
            index = self.pc.Index(self.index_name)
            
            # Create vector store
            vectorstore = PineconeVectorStore(
                index=index,
                embedding=self.embeddings,
                namespace=self.namespace
            )
            
            # Add documents in batches to avoid rate limits
            batch_size = 50
            successful_batches = 0
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                try:
                    # Add batch to vector store
                    vectorstore.add_documents(batch)
                    successful_batches += 1
                    logger.info(f"Successfully stored batch {successful_batches} ({len(batch)} documents)")
                    
                except Exception as batch_error:
                    logger.error(f"Error storing batch {i//batch_size + 1}: {str(batch_error)}")
                    continue
            
            logger.info(f"Successfully stored {successful_batches} batches in Pinecone")
            return True
            
        except Exception as e:
            logger.error(f"Error storing documents in Pinecone: {str(e)}")
            return False
    
    def verify_storage(self) -> Dict[str, Any]:
        """Verify that documents were stored correctly"""
        try:
            logger.info("Verifying document storage...")
            
            # Connect to the index
            index = self.pc.Index(self.index_name)
            
            # Get index stats
            stats = index.describe_index_stats()
            
            # Create vector store for testing
            vectorstore = PineconeVectorStore(
                index=index,
                embedding=self.embeddings,
                namespace=self.namespace
            )
            
            # Test search with a simple query
            test_query = "Anahata dog training"
            test_results = vectorstore.similarity_search(
                test_query,
                k=3,
                namespace=self.namespace
            )
            
            verification_results = {
                "index_stats": stats,
                "namespace_vector_count": stats.namespaces.get(self.namespace, {}).get('vector_count', 0),
                "test_query": test_query,
                "test_results_count": len(test_results),
                "sample_result": test_results[0].page_content[:200] if test_results else None,
                "verification_status": "success" if test_results else "failed"
            }
            
            logger.info(f"Verification complete: {verification_results['verification_status']}")
            logger.info(f"Stored vectors in namespace '{self.namespace}': {verification_results['namespace_vector_count']}")
            
            return verification_results
            
        except Exception as e:
            logger.error(f"Error during verification: {str(e)}")
            return {"verification_status": "error", "error": str(e)}
    
    def create_knowledge_base(self, pdf_path: str) -> Dict[str, Any]:
        """Main method to create the common knowledge base"""
        logger.info("=== Starting Common Knowledge Base Creation ===")
        
        results = {
            "status": "started",
            "pdf_path": pdf_path,
            "steps_completed": [],
            "errors": []
        }
        
        try:
            # Step 1: Create Pinecone index
            logger.info("Step 1: Creating Pinecone index...")
            if self.create_pinecone_index():
                results["steps_completed"].append("pinecone_index_created")
            else:
                results["errors"].append("Failed to create Pinecone index")
                return results
            
            # Step 2: Extract text from PDF
            logger.info("Step 2: Extracting text from PDF...")
            text_content = self.extract_text_from_pdf(pdf_path)
            if text_content:
                results["steps_completed"].append("text_extracted")
                results["text_length"] = len(text_content)
            else:
                results["errors"].append("Failed to extract text from PDF")
                return results
            
            # Step 3: Create document chunks
            logger.info("Step 3: Creating document chunks...")
            documents = self.create_document_chunks(text_content, pdf_path)
            if documents:
                results["steps_completed"].append("documents_chunked")
                results["total_chunks"] = len(documents)
            else:
                results["errors"].append("Failed to create document chunks")
                return results
            
            # Step 4: Store in Pinecone
            logger.info("Step 4: Storing documents in Pinecone...")
            if self.store_in_pinecone(documents):
                results["steps_completed"].append("documents_stored")
            else:
                results["errors"].append("Failed to store documents in Pinecone")
                return results
            
            # Step 5: Verify storage
            logger.info("Step 5: Verifying storage...")
            verification = self.verify_storage()
            results["verification"] = verification
            
            if verification.get("verification_status") == "success":
                results["steps_completed"].append("storage_verified")
                results["status"] = "completed_successfully"
            else:
                results["errors"].append("Storage verification failed")
                results["status"] = "completed_with_errors"
            
            logger.info("=== Common Knowledge Base Creation Complete ===")
            return results
            
        except Exception as e:
            logger.error(f"Unexpected error during knowledge base creation: {str(e)}")
            results["errors"].append(f"Unexpected error: {str(e)}")
            results["status"] = "failed"
            return results

def main():
    """Main execution function"""
    # PDF file path - use the current system path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "The Way of the Dog Anahata 2025-5-13.docx (1).pdf")
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        print(f"❌ Error: PDF file not found at {pdf_path}")
        return
    
    # Create knowledge base
    creator = CommonKnowledgeBaseCreator()
    results = creator.create_knowledge_base(pdf_path)
    
    # Print results
    print("\n" + "="*60)
    print("📚 COMMON KNOWLEDGE BASE CREATION RESULTS")
    print("="*60)
    
    print(f"📄 PDF File: {results.get('pdf_path', 'Unknown')}")
    print(f"📊 Status: {results.get('status', 'Unknown')}")
    
    if results.get('text_length'):
        print(f"📝 Text Extracted: {results['text_length']:,} characters")
    
    if results.get('total_chunks'):
        print(f"📦 Document Chunks: {results['total_chunks']:,}")
    
    print(f"\n✅ Steps Completed: {len(results.get('steps_completed', []))}")
    for step in results.get('steps_completed', []):
        print(f"   ✓ {step.replace('_', ' ').title()}")
    
    if results.get('errors'):
        print(f"\n❌ Errors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"   ✗ {error}")
    
    verification = results.get('verification', {})
    if verification:
        print(f"\n🔍 Verification Results:")
        print(f"   📊 Vectors Stored: {verification.get('namespace_vector_count', 0):,}")
        print(f"   �� Test Query: '{verification.get('test_query', 'N/A')}'")
        print(f"   📝 Test Results: {verification.get('test_results_count', 0)}")
        
        if verification.get('sample_result'):
            print(f"   📄 Sample Content: {verification['sample_result']}...")
    
    if results.get('status') == 'completed_successfully':
        print(f"\n🎉 SUCCESS: Common knowledge base created successfully!")
        print(f"📍 Index: common-knowledge-base")
        print(f"📍 Namespace: way-of-the-dog")
    else:
        print(f"\n⚠️ Process completed with issues. Check logs for details.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script for document context tracking functionality
"""

import os
import sys
import logging
from dotenv import load_dotenv
from flask import Flask, g

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_app():
    """Create a minimal Flask app for testing"""
    app = Flask(__name__)
    
    # Load configuration
    app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    app.config['OPENAI_CHAT_MODEL'] = os.getenv('OPENAI_CHAT_MODEL', 'gpt-4')
    app.config['OPENAI_EMBEDDING_MODEL'] = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')
    app.config['PINECONE_API_KEY'] = os.getenv('PINECONE_API_KEY')
    app.config['PINECONE_INDEX_NAME'] = os.getenv('PINECONE_INDEX_NAME')
    app.config['PINECONE_DIMENSION'] = int(os.getenv('PINECONE_DIMENSION', '1536'))
    app.config['PINECONE_METRIC'] = os.getenv('PINECONE_METRIC', 'cosine')
    app.config['VECTOR_SEARCH_TOP_K'] = int(os.getenv('VECTOR_SEARCH_TOP_K', '5'))
    
    return app

def test_document_context():
    """Test the document context tracking functionality"""
    try:
        # Create a minimal Flask app
        app = create_app()
        
        # Set up Flask context
        with app.app_context():
            # Set up user context
            g.user_id = int(os.getenv("TEST_USER_ID", "1"))
            
            # Import the necessary modules
            from app.utils.conversation_context_manager import get_context_manager
            from app.utils.langgraph_helper_enhanced import process_with_enhanced_graph
            
            # Get the context manager
            context_manager = get_context_manager()
            
            # Set up test parameters
            user_id = g.user_id
            user_email = os.getenv("TEST_USER_EMAIL", "test@example.com")
            conversation_id = int(os.getenv("TEST_CONVERSATION_ID", "1"))
            
            # Set environment variable for tools to access
            os.environ["CURRENT_USER_ID"] = str(user_id)
            
            # 1. Register a document upload
            document_names = ["test_document.pdf", "sample_data.csv"]
            document_metadata = {
                "test_document.pdf": {
                    "type": "application/pdf",
                    "summary": "This is a test document about company XYZ",
                    "key_insights": ["Company XYZ was founded in 2010", "Annual revenue is $10M", "Headquarters in New York"],
                    "upload_time": "2023-07-15T10:30:00Z"
                },
                "sample_data.csv": {
                    "type": "text/csv",
                    "summary": "CSV file containing sales data for Q2 2023",
                    "key_insights": ["Total sales: $2.5M", "Top product: Widget A", "Growth: 15%"],
                    "upload_time": "2023-07-15T10:30:00Z"
                }
            }
            
            # Register the document upload
            context_manager.register_document_upload(
                user_id=user_id,
                conversation_id=conversation_id,
                document_names=document_names,
                document_metadata=document_metadata
            )
            
            logger.info("Registered document upload")
            
            # 2. Test document context detection
            test_queries = [
                # Explicit document queries
                {"query": "Summarize my documents", "expected": True},
                {"query": "What's in the test document?", "expected": True},
                {"query": "Tell me about the CSV file", "expected": True},
                
                # Implicit document queries (entity questions)
                {"query": "What is the company name?", "expected": True},
                {"query": "When was the company founded?", "expected": True},
                {"query": "How much revenue does it have?", "expected": True},
                
                # Non-document queries
                {"query": "What's the weather today?", "expected": False},
                {"query": "Tell me a joke", "expected": False}
            ]
            
            # Test each query
            for test in test_queries:
                query = test["query"]
                expected = test["expected"]
                
                # Check if the query is detected as a document query
                result = context_manager.is_document_query(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    query=query
                )
                
                logger.info(f"Query: '{query}' - Expected: {expected}, Result: {result}")
                
                # If the detection doesn't match expectations, log a warning
                if result != expected:
                    logger.warning(f"❌ Detection mismatch for query: '{query}' - Expected: {expected}, Got: {result}")
                else:
                    logger.info(f"✅ Detection correct for query: '{query}'")
            
            # 3. Test document query processing
            logger.info("\nTesting document query processing:")
            
            # Create a simple conversation history
            conversation_history = [
                {"type": "user", "content": "I uploaded some documents about company XYZ"},
                {"type": "ai", "content": "I've processed your documents. You can ask me questions about them."}
            ]
            
            # Process a document query
            query = "What is the company name mentioned in the document?"
            logger.info(f"Processing query: '{query}'")
            
            response = process_with_enhanced_graph(
                user_id=user_id,
                user_email=user_email,
                conversation_id=conversation_id,
                query=query,
                conversation_history=conversation_history
            )
            
            logger.info(f"Response: {response[:200]}...")
            
    except Exception as e:
        logger.error(f"Error in test_document_context: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Starting document context test")
    test_document_context()
    logger.info("Document context test completed") 
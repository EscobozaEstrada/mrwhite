#!/usr/bin/env python
"""
Test Knowledge Search Script
---------------------------
This script tests the knowledge search functionality by performing a search query.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv
import argparse

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_search(user_id, query, top_k=10):
    """Test the knowledge search functionality"""
    try:
        # Import Flask app and services
        from app import create_app
        from app.services.pinecone_integration_service import PineconeBookNotesService
        
        # Create app context
        app = create_app()
        with app.app_context():
            # Create Pinecone service
            pinecone_service = PineconeBookNotesService()
            
            # Check if Pinecone is initialized
            if pinecone_service.index is None:
                logger.warning("⚠️ Pinecone not initialized. Running in simulated mode.")
            
            # Perform search
            logger.info(f"🔍 Searching for: '{query}'")
            result = pinecone_service.search_user_knowledge_base(
                user_id=user_id,
                query=query,
                top_k=top_k
            )
            
            # Print results
            if result.get('success', False):
                matches = result.get('results', {}).get('matches', [])
                logger.info(f"✅ Found {len(matches)} results")
                
                if matches:
                    logger.info("\n🔍 Search Results:")
                    for i, match in enumerate(matches):
                        score = match.get('score', 0) * 100
                        text = match.get('text', match.get('metadata', {}).get('text', 'No text'))
                        book_title = match.get('metadata', {}).get('book_title', 'Unknown')
                        page = match.get('metadata', {}).get('page_number', 'N/A')
                        
                        logger.info(f"\n[{i+1}] Score: {score:.1f}%")
                        logger.info(f"Book: {book_title}, Page: {page}")
                        logger.info(f"Text: {text[:100]}...")
                else:
                    logger.info("❌ No results found")
            else:
                logger.error(f"❌ Search failed: {result.get('message', 'Unknown error')}")
                
            return result
            
    except Exception as e:
        logger.error(f"❌ Error testing search: {str(e)}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return {"success": False, "message": str(e)}

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Test Knowledge Search')
    parser.add_argument('--user', type=int, required=True, help='User ID to search for')
    parser.add_argument('--query', type=str, required=True, help='Search query')
    parser.add_argument('--top-k', type=int, default=10, help='Number of results to return')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Test search
    test_search(args.user, args.query, args.top_k)

if __name__ == "__main__":
    main() 
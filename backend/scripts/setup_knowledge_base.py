#!/usr/bin/env python
"""
Setup Knowledge Base Script
---------------------------
This script initializes the Pinecone knowledge base and backfills existing notes.
Run this script after setting up the Pinecone API key in your environment.
"""

import os
import sys
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

def setup_pinecone():
    """Initialize Pinecone and create the knowledge base index if it doesn't exist"""
    try:
        from pinecone import Pinecone
        
        # Check if Pinecone API key is set
        api_key = os.getenv('PINECONE_API_KEY')
        
        if not api_key:
            logger.error("❌ PINECONE_API_KEY not set in environment")
            return False
            
        # Initialize Pinecone with new API
        pc = Pinecone(api_key=api_key)
        logger.info("✅ Pinecone initialized successfully")
        
        # Check if index exists
        index_name = 'common-knowledge-base'
        
        # Use environment variables for dimension and metric if available
        dimension = int(os.getenv('PINECONE_DIMENSION', '1536'))
        metric = os.getenv('PINECONE_METRIC', 'cosine')
        
        if index_name not in pc.list_indexes().names():
            # Create index
            logger.info(f"🔧 Creating new Pinecone index: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric
            )
            logger.info(f"✅ Created Pinecone index: {index_name}")
        else:
            logger.info(f"✅ Pinecone index already exists: {index_name}")
            
        return True
        
    except ImportError:
        logger.error("❌ Pinecone package not installed. Run: pip install pinecone-client")
        return False
    except Exception as e:
        logger.error(f"❌ Error setting up Pinecone: {str(e)}")
        return False

def backfill_notes(user_id=None):
    """Backfill existing notes to the knowledge base"""
    try:
        # Import Flask app and models
        from app import create_app
        from app.models.db import db
        from app.models.user_book import UserBookNote, UserBookCopy
        from app.services.pinecone_integration_service import PineconeBookNotesService
        
        # Create app context
        app = create_app()
        with app.app_context():
            # Create query
            query = UserBookNote.query
            
            # Filter by user_id if provided
            if user_id:
                query = query.filter_by(user_id=user_id)
                
            # Get all notes
            notes = query.all()
            logger.info(f"📝 Found {len(notes)} notes to backfill")
            
            if not notes:
                logger.info("ℹ️ No notes found to backfill")
                return True
                
            # Create Pinecone service
            pinecone_service = PineconeBookNotesService()
            success_count = 0
            error_count = 0
            
            # Process notes
            for i, note in enumerate(notes):
                # Get the book copy to get the book title
                book_copy = UserBookCopy.query.get(note.book_copy_id)
                book_title = book_copy.book_title if book_copy else 'Unknown'
                
                # Convert to dict
                note_data = {
                    'id': note.id,
                    'note_text': note.note_text,
                    'note_type': note.note_type,
                    'color': note.color,
                    'page_number': note.page_number,
                    'book_copy_id': note.book_copy_id,
                    'book_title': book_title,
                    'selected_text': note.selected_text if hasattr(note, 'selected_text') else '',
                    'pdf_coordinates': note.pdf_coordinates if hasattr(note, 'pdf_coordinates') else {}
                }
                
                # Add to knowledge base
                result = pinecone_service.add_note_to_knowledge_base(note.user_id, note_data)
                
                if result.get('success', False):
                    success_count += 1
                    logger.info(f"✅ [{i+1}/{len(notes)}] Added note {note.id} to knowledge base")
                else:
                    error_count += 1
                    logger.error(f"❌ [{i+1}/{len(notes)}] Failed to add note {note.id} to knowledge base: {result.get('message', 'Unknown error')}")
            
            logger.info(f"🎉 Backfill complete: {success_count} successful, {error_count} failed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error backfilling notes: {str(e)}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Setup Knowledge Base')
    parser.add_argument('--user', type=int, help='Specific user ID to backfill notes for')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Setup Pinecone
    logger.info("🚀 Setting up Pinecone...")
    if not setup_pinecone():
        logger.error("❌ Failed to set up Pinecone. Exiting.")
        sys.exit(1)
    
    # Backfill notes
    logger.info("🚀 Backfilling notes...")
    if not backfill_notes(args.user):
        logger.error("❌ Failed to backfill notes. Exiting.")
        sys.exit(1)
    
    logger.info("✅ Knowledge base setup complete!")

if __name__ == "__main__":
    main() 
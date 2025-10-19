from app import db
from app.models.enhanced_book import EnhancedBookChapter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    try:
        logger.info("Starting migration to add last_chat_fetch_at column...")
        db.create_all()
        logger.info("Migration completed successfully!")
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

if __name__ == "__main__":
    run_migration() 
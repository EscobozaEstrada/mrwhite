"""
Add display_order column to user_images table for gallery reordering
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column, Integer
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_database_url():
    """Get database URL from environment variables"""
    # Try to get from environment or use the SQLite file directly
    from dotenv import load_dotenv
    load_dotenv()
    
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Default to the health_tracker.db in migrations folder
    return 'sqlite:///migrations/health_tracker.db'

def run_migration():
    """Add display_order column to user_images table"""
    
    try:
        # Get database URL
        database_url = get_database_url()
        print(f"Using database: {database_url}")
        
        # Create engine
        engine = create_engine(database_url)
        
        # Check if user_images table exists
        inspector = inspect(engine)
        if 'user_images' not in inspector.get_table_names():
            print("❌ Table 'user_images' does not exist in the database")
            print("Please run the create_user_images_table.py migration first")
            return
        
        print("🗃️  Adding display_order column to user_images table...")
        
        # Check if column already exists
        columns = [col['name'] for col in inspector.get_columns('user_images')]
        if 'display_order' in columns:
            print("Column 'display_order' already exists, skipping creation")
        else:
            # Add the column - PostgreSQL syntax
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE user_images ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 0"))
                conn.commit()
                print("Column 'display_order' added successfully")
        
        # Update existing records to set display_order based on id
        with engine.connect() as conn:
            conn.execute(text("UPDATE user_images SET display_order = id WHERE display_order = 0 OR display_order IS NULL"))
            conn.commit()
            print("Updated display_order values for existing records")
        
        # Create index for better query performance if it doesn't exist
        # First check if index exists
        with engine.connect() as conn:
            # PostgreSQL-specific query to check if index exists
            index_exists_query = text("""
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_user_images_display_order'
            """)
            
            try:
                result = conn.execute(index_exists_query).fetchone()
                if not result:
                    # Create the index
                    conn.execute(text(
                        "CREATE INDEX idx_user_images_display_order ON user_images(user_id, display_order)"
                    ))
                    conn.commit()
                    print("Created index idx_user_images_display_order")
                else:
                    print("Index idx_user_images_display_order already exists")
            except ProgrammingError:
                # If the index check fails, try to create it anyway
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_user_images_display_order ON user_images(user_id, display_order)"
                ))
                conn.commit()
                print("Created index idx_user_images_display_order")
        
        print("✅ display_order column added successfully!")
        
        # Verify column exists
        columns = [col['name'] for col in inspector.get_columns('user_images')]
        if 'display_order' in columns:
            print("✅ Column verification successful!")
        else:
            print("❌ Column verification failed!")
            
    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error adding display_order column: {str(e)}")

if __name__ == "__main__":
    run_migration() 
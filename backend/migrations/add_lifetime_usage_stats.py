"""
Migration: Add lifetime_usage_stats to User Model in FastAPI

This migration adds the lifetime_usage_stats JSON column to the users table
for per-type daily usage tracking in the FastAPI system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text
from datetime import datetime

def upgrade():
    """Add lifetime_usage_stats column to users table if it doesn't exist"""
    
    app = create_app()
    with app.app_context():
        print("Starting lifetime_usage_stats migration...")
        
        # Check if column already exists
        check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' AND column_name='lifetime_usage_stats'
        """
        
        result = db.session.execute(text(check_query))
        if result.fetchone():
            print("✅ Column lifetime_usage_stats already exists, skipping...")
            return
        
        # Add new column to users table
        migration_queries = [
            # Add JSON column for per-type daily usage tracking
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS lifetime_usage_stats JSON DEFAULT '{}'",
        ]
        
        for query in migration_queries:
            try:
                db.session.execute(text(query))
                print(f"✅ Executed: {query[:50]}...")
            except Exception as e:
                print(f"❌ Failed: {query[:50]}... - {str(e)}")
        
        # Commit the schema changes
        db.session.commit()
        print("✅ Schema migration completed")
        
        # Initialize existing users with empty JSON structure
        print("Initializing existing users with per-type daily usage tracking...")
        
        try:
            # Get today's date for initialization
            today = datetime.now().date().isoformat()
            
            # Initialize all users with empty daily usage tracking
            init_query = text("""
                UPDATE users SET 
                    lifetime_usage_stats = jsonb_build_object(
                        'daily_usage', jsonb_build_object(
                            :today, jsonb_build_object(
                                'chat', 0,
                                'document', 0,
                                'health', 0,
                                'voice_message', 0
                            )
                        )
                    )
                WHERE lifetime_usage_stats IS NULL OR lifetime_usage_stats = '{}'::json
            """)
            
            db.session.execute(init_query, {"today": today})
            db.session.commit()
            
            print("✅ Initialized all users with per-type daily usage tracking")
            
        except Exception as e:
            print(f"❌ User initialization failed: {str(e)}")
            db.session.rollback()
        
        print("✅ Migration completed successfully")

def downgrade():
    """Remove lifetime_usage_stats column from users table"""
    
    app = create_app()
    with app.app_context():
        print("Starting lifetime_usage_stats downgrade...")
        
        # Remove column
        try:
            db.session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS lifetime_usage_stats"))
            db.session.commit()
            print("✅ Removed lifetime_usage_stats column")
        except Exception as e:
            print(f"❌ Failed to remove column: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    upgrade()








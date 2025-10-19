#!/usr/bin/env python3
"""
Migration: Add last_chat_fetch_at to Enhanced Book Chapters
Adds a timestamp column to track when chats were last fetched for a chapter
"""

import os
import sys
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def add_last_chat_fetch_at_column():
    """Add last_chat_fetch_at column to enhanced_book_chapters table"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🗄️ Adding last_chat_fetch_at column to enhanced_book_chapters table...")
            
            # Add the column
            db.session.execute(text('''
            ALTER TABLE enhanced_book_chapters 
            ADD COLUMN IF NOT EXISTS last_chat_fetch_at TIMESTAMP WITH TIME ZONE
            '''))
            
            # Set default value for existing chapters (use created_at)
            db.session.execute(text('''
            UPDATE enhanced_book_chapters
            SET last_chat_fetch_at = created_at
            WHERE last_chat_fetch_at IS NULL
            '''))
            
            # Create an index for better query performance
            db.session.execute(text('''
            CREATE INDEX IF NOT EXISTS ix_enhanced_book_chapters_last_chat_fetch_at 
            ON enhanced_book_chapters (last_chat_fetch_at)
            '''))
            
            db.session.commit()
            print("✅ last_chat_fetch_at column added successfully and initialized with created_at")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding last_chat_fetch_at column: {str(e)}")
            return False

def check_column_exists():
    """Check if the last_chat_fetch_at column already exists"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column exists
            result = db.session.execute(text('''
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'enhanced_book_chapters' AND column_name = 'last_chat_fetch_at'
            );
            '''))
            
            exists = result.scalar()
            
            if exists:
                print("✅ last_chat_fetch_at column already exists")
                return True
            else:
                print("❓ last_chat_fetch_at column does not exist yet")
                return False
                
        except Exception as e:
            print(f"❌ Error checking for last_chat_fetch_at column: {str(e)}")
            return False

def run_migration():
    """Run the migration to add last_chat_fetch_at column if it doesn't exist"""
    
    if not check_column_exists():
        success = add_last_chat_fetch_at_column()
        if success:
            print("✅ last_chat_fetch_at column migration completed successfully")
            return True
        else:
            print("❌ last_chat_fetch_at column migration failed")
            return False
    else:
        # Even if the column exists, we should update NULL values to created_at
        app = create_app()
        with app.app_context():
            try:
                print("🔄 Updating NULL last_chat_fetch_at values to created_at...")
                db.session.execute(text('''
                UPDATE enhanced_book_chapters
                SET last_chat_fetch_at = created_at
                WHERE last_chat_fetch_at IS NULL
                '''))
                db.session.commit()
                print("✅ Updated NULL last_chat_fetch_at values to created_at")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error updating NULL last_chat_fetch_at values: {str(e)}")
        
        print("⏭️ Skipping column creation (column already exists)")
        return True

if __name__ == "__main__":
    print("🚀 Running last_chat_fetch_at column migration...")
    run_migration() 
#!/usr/bin/env python3
import os
import sys

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def add_cover_image_field():
    """Add cover_image field to enhanced_books table if it doesn't exist"""
    app = create_app()
    with app.app_context():
        # Check if the column already exists
        check_query = text("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name='enhanced_books' AND column_name='cover_image'
        );
        """)
        
        result = db.session.execute(check_query).scalar()
        
        if not result:
            # Add the cover_image column
            add_column_query = text("""
            ALTER TABLE enhanced_books 
            ADD COLUMN cover_image VARCHAR(255);
            """)
            
            db.session.execute(add_column_query)
            db.session.commit()
            print("✅ Added cover_image column to enhanced_books table")
        else:
            print("⏭️ cover_image column already exists in enhanced_books table")

if __name__ == "__main__":
    add_cover_image_field() 
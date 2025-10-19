#!/usr/bin/env python3
"""
Database Migration: Add Dog Image Column
Adds dog_image column to users table to store S3 URL of uploaded dog images
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def upgrade():
    """Add dog_image column to users table"""
    print("🐕 Adding dog_image column to users table...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if we're using SQLite or PostgreSQL
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            is_sqlite = 'sqlite' in database_url.lower()
            
            # Add dog_image column
            conn = db.engine.connect()
            
            # SQLite and PostgreSQL have slightly different syntax
            if is_sqlite:
                conn.execute(text('ALTER TABLE users ADD COLUMN dog_image TEXT'))
            else:
                conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS dog_image TEXT'))
            
            print("✅ Successfully added dog_image column to users table")
            conn.close()
            
        except Exception as e:
            print(f"❌ Error adding dog_image column: {str(e)}")
            raise e

if __name__ == '__main__':
    upgrade() 
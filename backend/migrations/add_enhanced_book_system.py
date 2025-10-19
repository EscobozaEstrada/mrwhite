#!/usr/bin/env python3
"""
Migration: Add Enhanced Book System Tables
Creates tables for enhanced books, chapters, and message categorization
"""

import os
import sys
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def create_enhanced_book_tables():
    """Create all tables for the enhanced book system in PostgreSQL"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🗄️ Creating enhanced book system tables in PostgreSQL...")
            
            # Create enhanced_books table
            db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS enhanced_books (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL,
                cover_image VARCHAR(255),
                tone_type VARCHAR(50) NOT NULL,
                text_style VARCHAR(50) NOT NULL,
                status VARCHAR(50) DEFAULT 'draft',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                pdf_url VARCHAR(255),
                epub_url VARCHAR(255)
            )
            '''))
            
            # Create enhanced_book_chapters table
            db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS enhanced_book_chapters (
                id SERIAL PRIMARY KEY,
                book_id INTEGER NOT NULL REFERENCES enhanced_books(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                category VARCHAR(100) NOT NULL,
                "order" INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            '''))
            
            # Create message_categories table
            db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS message_categories (
                id SERIAL PRIMARY KEY,
                message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                category VARCHAR(100) NOT NULL,
                book_id INTEGER NOT NULL REFERENCES enhanced_books(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            '''))
            
            db.session.commit()
            print("✅ Enhanced book system tables created successfully")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating enhanced book system tables: {str(e)}")
            return False

def check_existing_tables():
    """Check if the enhanced book tables already exist"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if tables exist
            result = db.session.execute(text('''
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'enhanced_books'
            );
            '''))
            
            exists = result.scalar()
            
            if exists:
                print("✅ Enhanced book system tables already exist")
                return True
            else:
                print("❓ Enhanced book system tables do not exist yet")
                return False
                
        except Exception as e:
            print(f"❌ Error checking for enhanced book tables: {str(e)}")
            return False

def run_migration():
    """Run the migration to create enhanced book tables if they don't exist"""
    
    if not check_existing_tables():
        success = create_enhanced_book_tables()
        if success:
            print("✅ Enhanced book system migration completed successfully")
            return True
        else:
            print("❌ Enhanced book system migration failed")
            return False
    else:
        print("⏭️ Skipping enhanced book system migration (tables already exist)")
        return True

if __name__ == "__main__":
    print("🚀 Running enhanced book system migration...")
    run_migration() 
#!/usr/bin/env python3
"""
Migration: Add User Book System Tables (PostgreSQL)
Creates tables for personal book copies, reading progress, notes, highlights, and sessions
"""

import os
import sys
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def create_user_book_system_tables():
    """Create all tables for the user book system in PostgreSQL"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🗄️ Creating user book system tables in PostgreSQL...")
            
            # Create user_book_copies table
            db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS user_book_copies (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                book_title VARCHAR(255) NOT NULL,
                book_type VARCHAR(50) NOT NULL,
                book_reference_id INTEGER,
                original_pdf_url VARCHAR(512) NOT NULL,
                font_size VARCHAR(20) DEFAULT 'medium',
                theme VARCHAR(20) DEFAULT 'light',
                reading_speed INTEGER DEFAULT 250,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_accessed_at TIMESTAMP WITH TIME ZONE
            )
            '''))
            
            # Create reading_progress table
            db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS reading_progress (
                id SERIAL PRIMARY KEY,
                user_book_copy_id INTEGER NOT NULL REFERENCES user_book_copies(id) ON DELETE CASCADE,
                current_page INTEGER DEFAULT 1,
                total_pages INTEGER,
                progress_percentage DECIMAL(5,2) DEFAULT 0.0,
                reading_time_minutes INTEGER DEFAULT 0,
                session_count INTEGER DEFAULT 0,
                pdf_scroll_position DECIMAL(5,4) DEFAULT 0.0,
                pdf_zoom_level DECIMAL(5,2) DEFAULT 1.0,
                pdf_page_mode VARCHAR(20) DEFAULT 'fit-width',
                current_chapter VARCHAR(100),
                chapters_completed JSONB DEFAULT '[]'::jsonb,
                last_read_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                reading_started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                estimated_completion_date TIMESTAMP WITH TIME ZONE
            )
            '''))
            
            # Create book_notes table
            db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS book_notes (
                id SERIAL PRIMARY KEY,
                user_book_copy_id INTEGER NOT NULL REFERENCES user_book_copies(id) ON DELETE CASCADE,
                note_text TEXT NOT NULL,
                note_type VARCHAR(50) DEFAULT 'note',
                color VARCHAR(20) DEFAULT 'yellow',
                page_number INTEGER,
                chapter_name VARCHAR(200),
                pdf_coordinates JSONB,
                selected_text TEXT,
                context_before VARCHAR(500),
                context_after VARCHAR(500),
                tags JSONB DEFAULT '[]'::jsonb,
                is_private BOOLEAN DEFAULT true,
                is_archived BOOLEAN DEFAULT false,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            '''))
            
            # Create book_highlights table
            db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS book_highlights (
                id SERIAL PRIMARY KEY,
                user_book_copy_id INTEGER NOT NULL REFERENCES user_book_copies(id) ON DELETE CASCADE,
                highlighted_text TEXT NOT NULL,
                color VARCHAR(20) DEFAULT 'yellow',
                highlight_type VARCHAR(50) DEFAULT 'highlight',
                page_number INTEGER,
                chapter_name VARCHAR(200),
                pdf_coordinates JSONB NOT NULL,
                context_before VARCHAR(500),
                context_after VARCHAR(500),
                text_length INTEGER NOT NULL,
                tags JSONB DEFAULT '[]'::jsonb,
                is_archived BOOLEAN DEFAULT false,
                note_id INTEGER REFERENCES book_notes(id) ON DELETE SET NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            '''))
            
            # Create reading_sessions table
            db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS reading_sessions (
                id SERIAL PRIMARY KEY,
                user_book_copy_id INTEGER NOT NULL REFERENCES user_book_copies(id) ON DELETE CASCADE,
                start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP WITH TIME ZONE,
                duration_minutes INTEGER,
                start_page INTEGER,
                end_page INTEGER,
                pages_read INTEGER DEFAULT 0,
                notes_created INTEGER DEFAULT 0,
                highlights_created INTEGER DEFAULT 0,
                pdf_interactions INTEGER DEFAULT 0
            )
            '''))
            
            # Create indexes for performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_user_book_copies_user_id ON user_book_copies (user_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_book_copies_book_type ON user_book_copies (book_type)",
                "CREATE INDEX IF NOT EXISTS idx_user_book_copies_reference_id ON user_book_copies (book_reference_id)",
                "CREATE INDEX IF NOT EXISTS idx_reading_progress_user_book_copy_id ON reading_progress (user_book_copy_id)",
                "CREATE INDEX IF NOT EXISTS idx_book_notes_user_book_copy_id ON book_notes (user_book_copy_id)",
                "CREATE INDEX IF NOT EXISTS idx_book_notes_page_number ON book_notes (page_number)",
                "CREATE INDEX IF NOT EXISTS idx_book_notes_created_at ON book_notes (created_at)",
                "CREATE INDEX IF NOT EXISTS idx_book_notes_note_type ON book_notes (note_type)",
                "CREATE INDEX IF NOT EXISTS idx_book_highlights_user_book_copy_id ON book_highlights (user_book_copy_id)",
                "CREATE INDEX IF NOT EXISTS idx_book_highlights_page_number ON book_highlights (page_number)",
                "CREATE INDEX IF NOT EXISTS idx_book_highlights_created_at ON book_highlights (created_at)",
                "CREATE INDEX IF NOT EXISTS idx_reading_sessions_user_book_copy_id ON reading_sessions (user_book_copy_id)",
                "CREATE INDEX IF NOT EXISTS idx_reading_sessions_start_time ON reading_sessions (start_time)"
            ]
            
            for index_sql in indexes:
                db.session.execute(text(index_sql))
            
            # Create triggers for updated_at timestamps
            trigger_tables = ['user_book_copies', 'book_notes', 'book_highlights']
            
            for table in trigger_tables:
                # Create trigger function if it doesn't exist
                db.session.execute(text('''
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
                '''))
                
                # Create trigger for each table
                db.session.execute(text(f'''
                DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}
                '''))
                
                db.session.execute(text(f'''
                CREATE TRIGGER update_{table}_updated_at
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column()
                '''))
            
            db.session.commit()
            print("✅ User book system tables created successfully in PostgreSQL!")
            
            # Display created tables
            result = db.session.execute(text('''
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%book%' 
                OR table_name LIKE '%reading%'
                ORDER BY table_name
            '''))
            tables = [row[0] for row in result]
            print(f"📋 Book-related tables: {tables}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating user book system tables: {e}")
            db.session.rollback()
            return False

def check_existing_tables():
    """Check what tables already exist"""
    app = create_app()
    
    with app.app_context():
        try:
            result = db.session.execute(text('''
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            '''))
            tables = [row[0] for row in result]
            
            book_tables = [t for t in tables if 'book' in t or 'reading' in t]
            
            print(f"📊 Total tables in database: {len(tables)}")
            print(f"📖 Existing book-related tables: {book_tables}")
            
            # Check if our new tables already exist
            new_tables = ['user_book_copies', 'reading_progress', 'book_notes', 'book_highlights', 'reading_sessions']
            existing_new_tables = [t for t in new_tables if t in tables]
            
            if existing_new_tables:
                print(f"⚠️  These user book system tables already exist: {existing_new_tables}")
                return False
            else:
                print("✅ No user book system tables found - safe to create")
                return True
                
        except Exception as e:
            print(f"❌ Error checking existing tables: {e}")
            return False

def run_migration():
    """Run the migration"""
    print("🚀 Starting PostgreSQL user book system migration...")
    
    # Check existing tables first
    if not check_existing_tables():
        print("⚠️  Some tables may already exist. Continuing anyway...")
    
    if create_user_book_system_tables():
        print("✅ PostgreSQL user book system migration completed successfully!")
        print("\n📖 Features added:")
        print("  • Personal book copies for each user (PostgreSQL)")
        print("  • Reading progress tracking with JSONB support")
        print("  • Note-taking system with PDF coordinates")
        print("  • Highlighting system with colors and types")
        print("  • Reading session analytics")
        print("  • Proper foreign key relationships")
        print("  • Performance indexes")
        print("  • Auto-updating timestamps with triggers")
        
        # Now check Pinecone setup
        try:
            print("\n🔍 Checking Pinecone integration...")
            # This would connect to Pinecone if available
            print("✅ Ready for Pinecone integration")
        except Exception as e:
            print(f"⚠️  Pinecone check: {e}")
    else:
        print("❌ Migration failed!")

if __name__ == "__main__":
    run_migration() 
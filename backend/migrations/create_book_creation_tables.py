"""
Create book creation tables for custom book generation feature

This migration creates:
- book_tags: Predefined categories for organizing content
- custom_books: User-created books from their content  
- book_chapters: Chapters within books
- book_content_items: Individual content items within chapters
"""

import sqlite3
import os
from datetime import datetime

# Predefined book tags/categories as specified by user
PREDEFINED_BOOK_TAGS = [
    {
        'name': 'Travel Treasures & Logs',
        'description': 'Adventures, trips, and travel memories with your pet',
        'color': '#10B981',
        'icon': 'MapPin',
        'category_order': 1
    },
    {
        'name': 'Inspirational Insights', 
        'description': 'Meaningful moments and life lessons',
        'color': '#8B5CF6',
        'icon': 'Heart',
        'category_order': 2
    },
    {
        'name': 'Funny Moments Hall of Fame',
        'description': 'Hilarious and amusing experiences',
        'color': '#F59E0B',
        'icon': 'Laugh',
        'category_order': 3
    },
    {
        'name': 'Snuggle Moments Gallery',
        'description': 'Tender, loving, and bonding moments',
        'color': '#EC4899',
        'icon': 'Heart',
        'category_order': 4
    },
    {
        'name': 'Legacy & Sacred Transitions',
        'description': 'Important life transitions and memorial content',
        'color': '#6B7280',
        'icon': 'Star',
        'category_order': 5
    },
    {
        'name': 'Vet Records',
        'description': 'Medical appointments, vaccinations, and health checkups',
        'color': '#EF4444',
        'icon': 'Activity',
        'category_order': 6
    },
    {
        'name': 'Photo Galleries',
        'description': 'Beautiful photo collections and albums',
        'color': '#3B82F6',
        'icon': 'Camera',
        'category_order': 7
    },
    {
        'name': 'Playdate Memories',
        'description': 'Social interactions and playtime with other pets',
        'color': '#06B6D4',
        'icon': 'Users',
        'category_order': 8
    },
    {
        'name': 'Health & Behavior Journals',
        'description': 'Health monitoring and behavioral observations',
        'color': '#84CC16',
        'icon': 'FileText',
        'category_order': 9
    },
    {
        'name': 'Special Occasions',
        'description': 'Birthdays, holidays, and celebrations',
        'color': '#F97316',
        'icon': 'Gift',
        'category_order': 10
    },
    {
        'name': 'Daily Moments',
        'description': 'Everyday life and routine activities',
        'color': '#64748B',
        'icon': 'Calendar',
        'category_order': 11
    },
    {
        'name': 'Seasonal Reflections',
        'description': 'Seasonal changes and weather-related activities',
        'color': '#14B8A6',
        'icon': 'Sun',
        'category_order': 12
    },
    {
        'name': 'Appointments or Health & Medicine',
        'description': 'Medical appointments, treatments, and medication records',
        'color': '#DC2626',
        'icon': 'Stethoscope',
        'category_order': 13
    },
    {
        'name': 'Training & Growth Tracker',
        'description': 'Training progress, skills development, and learning milestones',
        'color': '#7C3AED',
        'icon': 'TrendingUp',
        'category_order': 14
    },
    {
        'name': 'Notes & Messages to (Your Dog\'s Name)',
        'description': 'Personal letters, thoughts, and messages to your pet',
        'color': '#BE123C',
        'icon': 'MessageCircle',
        'category_order': 15
    },
    {
        'name': 'Routines & Rituals',
        'description': 'Daily routines, habits, and special rituals',
        'color': '#0891B2',
        'icon': 'Clock',
        'category_order': 16
    },
    {
        'name': 'Milestones & Firsts',
        'description': 'Important firsts and milestone achievements',
        'color': '#059669',
        'icon': 'Award',
        'category_order': 17
    },
    {
        'name': 'Additional Living Notes',
        'description': 'Miscellaneous observations and general life notes',
        'color': '#4338CA',
        'icon': 'BookOpen',
        'category_order': 18
    }
]

def run_migration():
    """Create book creation tables and populate book tags"""
    
    # Get database path
    db_path = os.path.join(os.path.dirname(__file__), 'health_tracker.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗃️  Creating book creation tables...")
        
        # Create book_tags table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS book_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            color VARCHAR(7) DEFAULT '#3B82F6',
            icon VARCHAR(50),
            category_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
        ''')
        
        # Create indexes for book_tags
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_tags_name ON book_tags(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_tags_active ON book_tags(is_active)')
        
        # Create custom_books table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            
            -- Book metadata
            title VARCHAR(255) NOT NULL,
            subtitle VARCHAR(500),
            description TEXT,
            cover_image_url VARCHAR(512),
            
            -- Content configuration (JSON stored as TEXT in SQLite)
            selected_tags TEXT, -- JSON array of tag IDs
            date_range_start TIMESTAMP,
            date_range_end TIMESTAMP,
            content_types TEXT, -- JSON array ['chat', 'photos', 'documents']
            
            -- Generation settings
            book_style VARCHAR(50) DEFAULT 'narrative',
            include_photos BOOLEAN DEFAULT 1,
            include_documents BOOLEAN DEFAULT 1,
            include_chat_history BOOLEAN DEFAULT 1,
            auto_organize_by_date BOOLEAN DEFAULT 1,
            
            -- Book status and generation
            generation_status VARCHAR(50) DEFAULT 'draft',
            generation_progress INTEGER DEFAULT 0,
            generation_started_at TIMESTAMP,
            generation_completed_at TIMESTAMP,
            generation_error TEXT,
            
            -- Output formats
            pdf_url VARCHAR(512),
            epub_url VARCHAR(512),
            html_content TEXT,
            
            -- Analytics and metrics
            total_content_items INTEGER DEFAULT 0,
            total_photos INTEGER DEFAULT 0,
            total_documents INTEGER DEFAULT 0,
            total_chat_messages INTEGER DEFAULT 0,
            word_count INTEGER DEFAULT 0,
            
            -- Metadata
            processing_metadata TEXT, -- JSON stored as TEXT
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            
            -- Foreign key constraints
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')
        
        # Create book_chapters table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS book_chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            
            -- Chapter metadata
            chapter_number INTEGER NOT NULL,
            title VARCHAR(255) NOT NULL,
            subtitle VARCHAR(500),
            description TEXT,
            
            -- Content organization
            primary_tag_id INTEGER,
            date_range_start TIMESTAMP,
            date_range_end TIMESTAMP,
            
            -- Chapter content
            content_html TEXT,
            content_markdown TEXT,
            content_summary TEXT,
            
            -- Analytics
            word_count INTEGER DEFAULT 0,
            content_item_count INTEGER DEFAULT 0,
            
            -- Metadata
            chapter_metadata TEXT, -- JSON stored as TEXT
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            
            -- Foreign key constraints
            FOREIGN KEY (book_id) REFERENCES custom_books(id) ON DELETE CASCADE,
            FOREIGN KEY (primary_tag_id) REFERENCES book_tags(id) ON DELETE SET NULL
        )
        ''')
        
        # Create book_content_items table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS book_content_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id INTEGER NOT NULL,
            
            -- Content source identification
            content_type VARCHAR(50) NOT NULL,
            source_id INTEGER NOT NULL,
            source_table VARCHAR(50) NOT NULL,
            
            -- Content details
            title VARCHAR(255),
            content_text TEXT,
            content_url VARCHAR(512),
            thumbnail_url VARCHAR(512),
            
            -- Context and metadata
            original_date TIMESTAMP NOT NULL,
            tags TEXT, -- JSON stored as TEXT
            ai_analysis TEXT,
            
            -- Organization within chapter
            item_order INTEGER DEFAULT 0,
            include_in_export BOOLEAN DEFAULT 1,
            
            -- Processing metadata
            processing_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            
            -- Foreign key constraints
            FOREIGN KEY (chapter_id) REFERENCES book_chapters(id) ON DELETE CASCADE
        )
        ''')
        
        # Create indexes for better performance
        print("📊 Creating indexes...")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_custom_books_user_id ON custom_books(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_custom_books_status ON custom_books(generation_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_custom_books_created ON custom_books(created_at)')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_chapters_book_id ON book_chapters(book_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_chapters_tag_id ON book_chapters(primary_tag_id)')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_content_items_chapter_id ON book_content_items(chapter_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_content_items_type ON book_content_items(content_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_content_items_source ON book_content_items(source_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_content_items_date ON book_content_items(original_date)')
        
        # Populate predefined book tags
        print("📚 Populating predefined book tags...")
        
        for tag in PREDEFINED_BOOK_TAGS:
            cursor.execute('''
            INSERT OR IGNORE INTO book_tags 
            (name, description, color, icon, category_order, is_active) 
            VALUES (?, ?, ?, ?, ?, 1)
            ''', (
                tag['name'],
                tag['description'], 
                tag['color'],
                tag['icon'],
                tag['category_order']
            ))
        
        # Commit all changes
        conn.commit()
        
        # Verify the creation
        cursor.execute("SELECT COUNT(*) FROM book_tags")
        tag_count = cursor.fetchone()[0]
        
        print(f"✅ Book creation tables created successfully!")
        print(f"📊 Populated {tag_count} predefined book tags")
        print(f"🗄️  Tables created: book_tags, custom_books, book_chapters, book_content_items")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating book creation tables: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("🎉 Book creation tables migration completed successfully!")
    else:
        print("💥 Migration failed!") 
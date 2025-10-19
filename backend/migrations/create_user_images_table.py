"""
Create user_images table for storing uploaded images with comprehensive metadata

This migration creates the user_images table to support:
- Image file storage with S3 integration
- OpenAI Vision API analysis results
- Image metadata (dimensions, format, EXIF, etc.)
- Chat context linking
- Gallery functionality
- Soft deletion support
"""

import sqlite3
import os
from datetime import datetime

def run_migration():
    """Create user_images table"""
    
    # Get database path
    db_path = os.path.join(os.path.dirname(__file__), 'health_tracker.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗃️  Creating user_images table...")
        
        # Create user_images table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            
            -- File information
            filename VARCHAR(255) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            s3_url TEXT NOT NULL,
            s3_key VARCHAR(500) NOT NULL,
            
            -- AI Analysis
            description TEXT,
            analysis_data TEXT, -- JSON stored as TEXT in SQLite
            
            -- Image metadata
            image_metadata TEXT, -- JSON stored as TEXT in SQLite
            
            -- Chat context (optional)
            conversation_id INTEGER,
            message_id INTEGER,
            
            -- Status and timestamps
            is_deleted BOOLEAN DEFAULT 0 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            deleted_at TIMESTAMP,
            
            -- Foreign key constraints
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL
        )
        ''')
        
        # Create indexes for better query performance
        print("📊 Creating indexes...")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_images_user_id ON user_images(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_images_created_at ON user_images(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_images_is_deleted ON user_images(is_deleted)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_images_conversation_id ON user_images(conversation_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_images_message_id ON user_images(message_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_images_user_active ON user_images(user_id, is_deleted)')
        
        # Create trigger to update updated_at timestamp
        print("⚡ Creating triggers...")
        
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_user_images_updated_at
        AFTER UPDATE ON user_images
        FOR EACH ROW
        BEGIN
            UPDATE user_images SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END
        ''')
        
        conn.commit()
        
        print("✅ user_images table created successfully!")
        print("📝 Table features:")
        print("   - Image file storage with S3 integration")
        print("   - OpenAI Vision API analysis results")
        print("   - Comprehensive image metadata")
        print("   - Chat context linking")
        print("   - Gallery functionality")
        print("   - Soft deletion support")
        print("   - Optimized indexes for performance")
        
        # Verify table creation
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_images'")
        if cursor.fetchone():
            print("✅ Table verification successful!")
        else:
            print("❌ Table verification failed!")
            
    except sqlite3.Error as e:
        print(f"❌ Error creating user_images table: {e}")
        conn.rollback()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()

def rollback_migration():
    """Drop user_images table"""
    
    db_path = os.path.join(os.path.dirname(__file__), 'health_tracker.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗑️  Rolling back user_images table...")
        
        # Drop triggers first
        cursor.execute('DROP TRIGGER IF EXISTS update_user_images_updated_at')
        
        # Drop indexes
        cursor.execute('DROP INDEX IF EXISTS idx_user_images_user_id')
        cursor.execute('DROP INDEX IF EXISTS idx_user_images_created_at')
        cursor.execute('DROP INDEX IF EXISTS idx_user_images_is_deleted')
        cursor.execute('DROP INDEX IF EXISTS idx_user_images_conversation_id')
        cursor.execute('DROP INDEX IF EXISTS idx_user_images_message_id')
        cursor.execute('DROP INDEX IF EXISTS idx_user_images_user_active')
        
        # Drop table
        cursor.execute('DROP TABLE IF EXISTS user_images')
        
        conn.commit()
        print("✅ user_images table rolled back successfully!")
        
    except sqlite3.Error as e:
        print(f"❌ Error rolling back user_images table: {e}")
        conn.rollback()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
    else:
        run_migration() 
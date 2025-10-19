"""
Create image_folders and folder_images tables for organizing images in the gallery

This migration creates:
- image_folders table for storing folder information
- folder_images table for associating images with folders
"""

import sqlite3
import os
from datetime import datetime

def run_migration():
    """Create folder-related tables"""
    
    # Get database path
    db_path = os.path.join(os.path.dirname(__file__), 'health_tracker.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗃️  Creating image_folders table...")
        
        # Create image_folders table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            
            -- Folder information
            name VARCHAR(255) NOT NULL,
            description TEXT,
            
            -- Display order
            display_order INTEGER DEFAULT 0 NOT NULL,
            
            -- Status and timestamps
            is_deleted BOOLEAN DEFAULT 0 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            deleted_at TIMESTAMP,
            
            -- Foreign key constraints
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')
        
        # Create indexes for image_folders
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_folders_user_id ON image_folders(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_folders_is_deleted ON image_folders(is_deleted)')
        
        print("🗃️  Creating folder_images table...")
        
        # Create folder_images table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS folder_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id INTEGER NOT NULL,
            image_id INTEGER NOT NULL,
            
            -- Display order within folder
            display_order INTEGER DEFAULT 0 NOT NULL,
            
            -- Timestamps
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            
            -- Constraints
            UNIQUE(folder_id, image_id),
            
            -- Foreign key constraints
            FOREIGN KEY (folder_id) REFERENCES image_folders(id) ON DELETE CASCADE,
            FOREIGN KEY (image_id) REFERENCES user_images(id) ON DELETE CASCADE
        )
        ''')
        
        # Create indexes for folder_images
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_folder_images_folder_id ON folder_images(folder_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_folder_images_image_id ON folder_images(image_id)')
        
        conn.commit()
        print("✅ Successfully created folder tables")
        return True
        
    except Exception as e:
        print(f"❌ Error creating folder tables: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Run migration when file is executed directly
if __name__ == "__main__":
    run_migration() 
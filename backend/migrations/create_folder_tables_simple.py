#!/usr/bin/env python
"""
Simple migration script to create folder tables
"""

import os
import sqlite3
import sys

def main():
    # Find the database file
    db_path = None
    
    # Check common locations
    possible_locations = [
        'health_tracker.db',
        'backend/health_tracker.db',
        'backend/app/health_tracker.db',
        'backend/instance/health_tracker.db',
        'app/health_tracker.db',
        'instance/health_tracker.db'
    ]
    
    for location in possible_locations:
        if os.path.exists(location):
            db_path = location
            break
    
    if not db_path:
        print("Could not find database file. Please enter the path to your database:")
        db_path = input().strip()
        if not os.path.exists(db_path):
            print(f"Error: File {db_path} does not exist.")
            return False
    
    print(f"Using database: {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create image_folders table
        print("Creating image_folders table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            display_order INTEGER DEFAULT 0 NOT NULL,
            is_deleted BOOLEAN DEFAULT 0 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            deleted_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')
        
        # Create folder_images table
        print("Creating folder_images table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS folder_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id INTEGER NOT NULL,
            image_id INTEGER NOT NULL,
            display_order INTEGER DEFAULT 0 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            UNIQUE(folder_id, image_id),
            FOREIGN KEY (folder_id) REFERENCES image_folders(id) ON DELETE CASCADE,
            FOREIGN KEY (image_id) REFERENCES user_images(id) ON DELETE CASCADE
        )
        ''')
        
        # Create indexes
        print("Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_folders_user_id ON image_folders(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_folders_is_deleted ON image_folders(is_deleted)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_folder_images_folder_id ON folder_images(folder_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_folder_images_image_id ON folder_images(image_id)')
        
        # Commit changes
        conn.commit()
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='image_folders' OR name='folder_images')")
        created_tables = cursor.fetchall()
        
        if len(created_tables) == 2:
            print("Success! Tables created:")
            for table in created_tables:
                print(f"- {table[0]}")
            return True
        else:
            print("Warning: Not all tables were created.")
            print("Created tables:")
            for table in created_tables:
                print(f"- {table[0]}")
            return False
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = main()
    if success:
        print("Migration completed successfully.")
    else:
        print("Migration failed or completed with warnings.")
        sys.exit(1) 
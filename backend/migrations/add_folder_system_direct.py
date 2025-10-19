#!/usr/bin/env python3
"""
Migration: Add Folder System for Gallery Images (Direct DB Connection)
Creates tables for organizing images into folders
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

def run_migration():
    """Create folder system tables directly with psycopg2"""
    
    # Load environment variables
    load_dotenv()
    
    # Get database connection info from environment
    db_host = os.getenv('DATABASE_HOST')
    db_port = os.getenv('DATABASE_PORT', '5432')
    db_name = os.getenv('DATABASE_NAME', 'health_tracker')
    db_user = os.getenv('DATABASE_USER', 'postgres')
    db_password = os.getenv('DATABASE_PASSWORD', '')
    
    # Allow overriding with DATABASE_URL if available
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgresql://'):
        # Parse DATABASE_URL
        from urllib.parse import urlparse
        url = urlparse(database_url)
        db_user = url.username
        db_password = url.password
        db_host = url.hostname
        db_port = url.port or '5432'
        db_name = url.path[1:]  # Remove leading slash
    
    print(f"🔄 Connecting to PostgreSQL database: {db_name} on {db_host}:{db_port}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        
        # Set isolation level for DDL operations
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Create cursor
        cursor = conn.cursor()
        
        print("✅ Connected to PostgreSQL database")
        
        # Check if tables already exist
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'image_folders')")
        image_folders_exists = cursor.fetchone()[0]
        
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'folder_images')")
        folder_images_exists = cursor.fetchone()[0]
        
        if image_folders_exists and folder_images_exists:
            print("✅ Folder system tables already exist, skipping creation")
            return True
        
        # Check if old folder table exists
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'folder')")
        old_table_exists = cursor.fetchone()[0]
        
        if old_table_exists:
            print("🗑️ Removing old folder table...")
            cursor.execute("DROP TABLE IF EXISTS folder CASCADE")
            print("✅ Old folder table removed")
        
        print("🗃️ Creating image_folders table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_folders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            display_order INTEGER DEFAULT 0 NOT NULL,
            is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            deleted_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')
        
        print("🗃️ Creating folder_images table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS folder_images (
            id SERIAL PRIMARY KEY,
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
        
        print("📊 Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_folders_user_id ON image_folders(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_folders_is_deleted ON image_folders(is_deleted)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_folder_images_folder_id ON folder_images(folder_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_folder_images_image_id ON folder_images(image_id)')
        
        print("⚡ Creating triggers for updated_at timestamps...")
        # Create function for auto-updating updated_at timestamp
        cursor.execute('''
        CREATE OR REPLACE FUNCTION update_modified_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        ''')
        
        # Create triggers for updated_at timestamps
        cursor.execute('''
        DROP TRIGGER IF EXISTS update_image_folders_modtime ON image_folders;
        CREATE TRIGGER update_image_folders_modtime
        BEFORE UPDATE ON image_folders
        FOR EACH ROW
        EXECUTE FUNCTION update_modified_column();
        ''')
        
        cursor.execute('''
        DROP TRIGGER IF EXISTS update_folder_images_modtime ON folder_images;
        CREATE TRIGGER update_folder_images_modtime
        BEFORE UPDATE ON folder_images
        FOR EACH ROW
        EXECUTE FUNCTION update_modified_column();
        ''')
        
        # Verify tables were created
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name IN ('image_folders', 'folder_images')")
        created_tables = cursor.fetchall()
        
        if len(created_tables) == 2:
            print("✅ Successfully created folder system tables!")
            for table in created_tables:
                print(f"  - {table[0]}")
            return True
        else:
            print("⚠️ Not all tables were created. Found:")
            for table in created_tables:
                print(f"  - {table[0]}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating folder system tables: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("✅ Migration completed successfully")
        sys.exit(0)
    else:
        print("❌ Migration failed")
        sys.exit(1) 
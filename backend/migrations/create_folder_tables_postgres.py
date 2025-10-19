#!/usr/bin/env python
"""
Simple migration script to create folder tables in PostgreSQL
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def main():
    # Get database connection info from environment or use defaults
    db_host = os.environ.get('DATABASE_HOST')
    db_port = os.environ.get('DATABASE_PORT', '5432')
    db_name = os.environ.get('DATABASE_NAME', 'health_tracker')
    db_user = os.environ.get('DATABASE_USER', 'postgres')
    db_password = os.environ.get('DATABASE_PASSWORD', '')
    
    print(f"Connecting to PostgreSQL database: {db_name} on {db_host}:{db_port}")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        
        # Set isolation level for table creation
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Create cursor
        cursor = conn.cursor()
        
        print("Connected to PostgreSQL database")
        
        # Check if old folder table exists and drop it
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'folder')")
        if cursor.fetchone()[0]:
            print("Dropping old folder table...")
            cursor.execute("DROP TABLE IF EXISTS folder CASCADE")
            print("Old folder table dropped")
        
        # Create image_folders table
        print("Creating image_folders table...")
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
        
        # Create folder_images table
        print("Creating folder_images table...")
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
        
        # Create indexes
        print("Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_folders_user_id ON image_folders(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_folders_is_deleted ON image_folders(is_deleted)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_folder_images_folder_id ON folder_images(folder_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_folder_images_image_id ON folder_images(image_id)')
        
        # Add trigger for updated_at timestamp
        print("Creating triggers for updated_at timestamps...")
        cursor.execute('''
        CREATE OR REPLACE FUNCTION update_modified_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        ''')
        
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
        import traceback
        traceback.print_exc()
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
#!/usr/bin/env python3
"""
Migration: Add Folder System for Gallery Images
Creates tables for organizing images into folders
"""

import os
import sys
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError

def get_database_url():
    """Get database URL from environment variables"""
    # Try to get from environment or use the SQLite file directly
    from dotenv import load_dotenv
    load_dotenv()
    
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Default to the health_tracker.db in migrations folder
    return 'sqlite:///migrations/health_tracker.db'

def check_existing_tables(engine):
    """Check if the folder tables already exist"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    tables_exist = 'image_folders' in existing_tables and 'folder_images' in existing_tables
    old_table_exists = 'folder' in existing_tables
    
    return tables_exist, old_table_exists

def run_migration():
    """Create folder system tables"""
    try:
        # Import Flask app and SQLAlchemy
        from app import create_app, db
        
        # Create app context
        app = create_app()
        
        with app.app_context():
            print("🔄 Starting folder system migration...")
            
            # Check if tables already exist
            tables_exist, old_table_exists = check_existing_tables(db.engine)
            
            if tables_exist:
                print("✅ Folder system tables already exist, skipping creation")
                return True
            
            # Drop old folder table if it exists
            if old_table_exists:
                print("🗑️ Removing old folder table...")
                db.session.execute(text('DROP TABLE IF EXISTS folder CASCADE'))
                db.session.commit()
                print("✅ Old folder table removed")
            
            print("🗃️ Creating image_folders table...")
            db.session.execute(text('''
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
            '''))
            
            print("🗃️ Creating folder_images table...")
            db.session.execute(text('''
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
            '''))
            
            print("📊 Creating indexes...")
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_image_folders_user_id ON image_folders(user_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_image_folders_is_deleted ON image_folders(is_deleted)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_folder_images_folder_id ON folder_images(folder_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_folder_images_image_id ON folder_images(image_id)'))
            
            print("⚡ Creating triggers for updated_at timestamps...")
            try:
                # Create function for auto-updating updated_at timestamp
                db.session.execute(text('''
                CREATE OR REPLACE FUNCTION update_modified_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                '''))
                
                # Create triggers for updated_at timestamps
                db.session.execute(text('''
                DROP TRIGGER IF EXISTS update_image_folders_modtime ON image_folders;
                CREATE TRIGGER update_image_folders_modtime
                BEFORE UPDATE ON image_folders
                FOR EACH ROW
                EXECUTE FUNCTION update_modified_column();
                '''))
                
                db.session.execute(text('''
                DROP TRIGGER IF EXISTS update_folder_images_modtime ON folder_images;
                CREATE TRIGGER update_folder_images_modtime
                BEFORE UPDATE ON folder_images
                FOR EACH ROW
                EXECUTE FUNCTION update_modified_column();
                '''))
            except Exception as e:
                print(f"⚠️ Could not create triggers (this is normal for SQLite): {str(e)}")
            
            # Commit all changes
            db.session.commit()
            
            # Verify tables were created
            tables_exist, _ = check_existing_tables(db.engine)
            if tables_exist:
                print("✅ Successfully created folder system tables!")
                return True
            else:
                print("❌ Failed to create folder system tables")
                return False
                
    except SQLAlchemyError as e:
        print(f"❌ Database error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error creating folder system tables: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("✅ Migration completed successfully")
        sys.exit(0)
    else:
        print("❌ Migration failed")
        sys.exit(1) 
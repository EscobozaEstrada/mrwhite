"""
Database migration script to add care archive tables
Run this script to add the new tables for the care archive system
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import sys
import os

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.care_record import CareRecord, Document, KnowledgeBase

def create_care_archive_tables():
    """Create all care archive related tables"""
    try:
        app = create_app()
        
        with app.app_context():
            print("Creating care archive tables...")
            
            # Create all tables
            db.create_all()
            
            print("✅ Care archive tables created successfully!")
            print("Tables created:")
            print("- care_records")
            print("- documents") 
            print("- knowledge_bases")
            print("- attachments (from existing message model)")
            
            # Add some indexes for performance
            print("\nAdding performance indexes...")
            
            # Add additional indexes if needed
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_care_records_user_category 
                ON care_records(user_id, category);
            """)
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_user_processing 
                ON documents(user_id, processing_status);
            """)
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_care_records_reminder_date 
                ON care_records(reminder_date) WHERE reminder_date IS NOT NULL;
            """)
            
            print("✅ Performance indexes added!")
            
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        raise

def add_sample_care_categories():
    """Add sample care categories for testing"""
    try:
        app = create_app()
        
        with app.app_context():
            # This would be handled by the application logic
            # Just printing the available categories
            print("\n📋 Available Care Categories:")
            categories = [
                "vaccination", "vet_visit", "medication", "milestone",
                "grooming", "training", "diet", "exercise", "behavior", "other"
            ]
            
            for category in categories:
                print(f"- {category}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("🏥 Mr. White Care Archive Database Migration")
    print("=" * 50)
    
    create_care_archive_tables()
    add_sample_care_categories()
    
    print("\n🎉 Migration completed successfully!")
    print("\nNext steps:")
    print("1. Restart your Flask application")
    print("2. Test the new care archive endpoints")
    print("3. Upload some documents to test the system") 
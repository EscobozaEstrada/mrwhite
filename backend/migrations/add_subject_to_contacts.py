"""
Database Migration: Add Subject Field to Contacts Table

This migration adds a subject field to the contacts table to support:
- Better organization of contact messages
- Improved email subject lines
- Reduced chance of emails going to spam

Run with: python migrations/add_subject_to_contacts.py
"""

import sys
import os
from sqlalchemy import text

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def run_migration():
    """Add subject field to contacts table"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 Starting migration: Add subject field to contacts table...")
            
            # Check if migration already applied
            check_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'contacts' AND column_name = 'subject';
            """
            
            result = db.session.execute(text(check_sql)).fetchone()
            if result:
                print("✅ Migration already applied - subject column exists")
                return
            
            # Add subject column to contacts table
            migration_sql = """
            ALTER TABLE contacts ADD COLUMN subject VARCHAR(200);
            """
            
            # Execute migration
            db.session.execute(text(migration_sql))
            db.session.commit()
            print("✅ Successfully added subject field to contacts table")
            
        except Exception as e:
            print(f"❌ Error adding subject field: {str(e)}")
            db.session.rollback()
            raise

def rollback_migration():
    """Remove subject field from contacts table"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 Rolling back: Remove subject field from contacts table...")
            
            # Check if column exists before attempting to drop
            check_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'contacts' AND column_name = 'subject';
            """
            
            result = db.session.execute(text(check_sql)).fetchone()
            if not result:
                print("✅ Nothing to rollback - subject column doesn't exist")
                return
            
            # Drop the subject column
            rollback_sql = """
            ALTER TABLE contacts DROP COLUMN subject;
            """
            
            # Execute rollback
            db.session.execute(text(rollback_sql))
            db.session.commit()
            print("✅ Successfully removed subject field from contacts table")
            
        except Exception as e:
            print(f"❌ Error removing subject field: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Contacts Subject Field Migration')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migration()
    else:
        run_migration() 
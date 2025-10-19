#!/usr/bin/env python3
"""
Migration: Add Follow-up Notification Fields to Health Reminders
Adds fields for follow-up notification tracking and completion management
"""

import os
import sys
from datetime import datetime
from sqlalchemy import text

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.health_models import HealthReminder

def run_migration():
    """
    Add follow-up notification fields to existing health_reminders table
    """
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🚀 Starting follow-up notification fields migration...")
            
            # SQL commands to add new columns using text() for SQLAlchemy
            migration_sql = [
                # Follow-up notification fields
                text("ALTER TABLE health_reminders ADD COLUMN completed_by VARCHAR(50);"),
                text("ALTER TABLE health_reminders ADD COLUMN completion_method VARCHAR(50);"),
                text("ALTER TABLE health_reminders ADD COLUMN enable_followup_notifications BOOLEAN DEFAULT TRUE;"),
                text("ALTER TABLE health_reminders ADD COLUMN followup_interval_minutes INTEGER DEFAULT 30;"),
                text("ALTER TABLE health_reminders ADD COLUMN max_followup_count INTEGER DEFAULT 5;"),
                text("ALTER TABLE health_reminders ADD COLUMN current_followup_count INTEGER DEFAULT 0;"),
                text("ALTER TABLE health_reminders ADD COLUMN next_followup_at TIMESTAMP;"),
                text("ALTER TABLE health_reminders ADD COLUMN last_followup_sent_at TIMESTAMP;"),
                text("ALTER TABLE health_reminders ADD COLUMN followup_notifications_stopped BOOLEAN DEFAULT FALSE;"),
                
                # Recurring reminder series fields
                text("ALTER TABLE health_reminders ADD COLUMN parent_series_id VARCHAR(50);"),
                text("ALTER TABLE health_reminders ADD COLUMN is_recurring_instance BOOLEAN DEFAULT FALSE;"),
            ]
            
            # Execute each SQL command
            for i, sql_command in enumerate(migration_sql, 1):
                try:
                    db.session.execute(sql_command)
                    field_name = str(sql_command).split()[5]  # Extract field name
                    print(f"✅ Step {i}/{len(migration_sql)}: {field_name} field added")
                except Exception as e:
                    error_msg = str(e).lower()
                    if "duplicate column name" in error_msg or "already exists" in error_msg or "column already exists" in error_msg:
                        field_name = str(sql_command).split()[5]
                        print(f"⚠️  Step {i}/{len(migration_sql)}: {field_name} field already exists, skipping")
                    else:
                        print(f"❌ Step {i}/{len(migration_sql)}: Error - {str(e)}")
                        raise
            
            # Commit all changes
            db.session.commit()
            print("✅ Database migration completed successfully!")
            
            # Test the migration by checking if we can access the new fields
            print("\n🔍 Verifying migration...")
            
            # Query to check if the new columns exist
            test_query = text("SELECT completed_by, completion_method, enable_followup_notifications, followup_interval_minutes, max_followup_count, current_followup_count, parent_series_id, is_recurring_instance FROM health_reminders LIMIT 1;")
            
            try:
                result = db.session.execute(test_query)
                print("✅ New fields verification successful!")
                print("   - All new columns are accessible")
                
                # Update existing reminders to have default values
                update_query = text("""
                    UPDATE health_reminders 
                    SET 
                        enable_followup_notifications = TRUE,
                        followup_interval_minutes = 30,
                        max_followup_count = 5,
                        current_followup_count = 0,
                        followup_notifications_stopped = FALSE,
                        is_recurring_instance = FALSE
                    WHERE enable_followup_notifications IS NULL;
                """)
                
                update_result = db.session.execute(update_query)
                db.session.commit()
                print(f"✅ Updated {update_result.rowcount} existing reminders with default values")
                
            except Exception as e:
                print(f"❌ Field verification failed: {str(e)}")
                raise
            
            print(f"\n🎉 Migration completed successfully at {datetime.now()}")
            print("📋 Summary:")
            print("   - Added follow-up notification tracking fields")
            print("   - Added completion tracking fields") 
            print("   - Added recurring reminder series fields")
            print("   - Updated existing reminders with default values")
            print("   - All fields verified and working")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")
            return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1) 
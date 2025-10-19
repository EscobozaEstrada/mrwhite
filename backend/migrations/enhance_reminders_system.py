#!/usr/bin/env python3
"""
Database migration to enhance reminder system with time-based scheduling and recurring reminders
"""

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def enhance_reminders_system(db_path="migrations/health_tracker.db"):
    """
    Enhance the reminders system with:
    1. Time-based scheduling (due_time, reminder_time)
    2. Recurring reminders functionality
    3. Enhanced notification tracking
    4. SMS support
    """
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Starting reminder system enhancement migration...")
        
        # 1. Add new columns to existing health_reminders table
        enhancement_queries = [
            # Time-based scheduling
            "ALTER TABLE health_reminders ADD COLUMN due_time TIME",
            "ALTER TABLE health_reminders ADD COLUMN reminder_time TIME",
            "ALTER TABLE health_reminders ADD COLUMN updated_at DATETIME",
            
            # Enhanced notification settings
            "ALTER TABLE health_reminders ADD COLUMN send_sms BOOLEAN DEFAULT FALSE",
            "ALTER TABLE health_reminders ADD COLUMN hours_before_reminder INTEGER DEFAULT 0",
            
            # Recurring reminder settings
            "ALTER TABLE health_reminders ADD COLUMN recurrence_type VARCHAR(20) DEFAULT 'none'",
            "ALTER TABLE health_reminders ADD COLUMN recurrence_interval INTEGER DEFAULT 1",
            "ALTER TABLE health_reminders ADD COLUMN recurrence_end_date DATE",
            "ALTER TABLE health_reminders ADD COLUMN max_occurrences INTEGER",
            "ALTER TABLE health_reminders ADD COLUMN current_occurrence INTEGER DEFAULT 1",
            
            # Notification tracking
            "ALTER TABLE health_reminders ADD COLUMN last_notification_sent DATETIME",
            "ALTER TABLE health_reminders ADD COLUMN notification_attempts INTEGER DEFAULT 0",
            
            # Metadata
            "ALTER TABLE health_reminders ADD COLUMN metadata TEXT"  # JSON as TEXT
        ]
        
        for query in enhancement_queries:
            try:
                cursor.execute(query)
                print(f"✅ Executed: {query}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"⚠️  Column already exists: {query}")
                else:
                    print(f"❌ Error: {query} - {e}")
        
        # 2. Create reminder_notifications table for tracking individual notifications
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminder_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                notification_type VARCHAR(20) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'delivered')),
                scheduled_at DATETIME NOT NULL,
                sent_at DATETIME,
                delivered_at DATETIME,
                subject VARCHAR(255),
                message TEXT,
                recipient VARCHAR(255) NOT NULL,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reminder_id) REFERENCES health_reminders(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        print("✅ Created reminder_notifications table")
        
        # 3. Create indexes for better performance
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_reminder_notifications_reminder_id ON reminder_notifications(reminder_id)",
            "CREATE INDEX IF NOT EXISTS idx_reminder_notifications_user_id ON reminder_notifications(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_reminder_notifications_scheduled_at ON reminder_notifications(scheduled_at)",
            "CREATE INDEX IF NOT EXISTS idx_reminder_notifications_status ON reminder_notifications(status)",
            "CREATE INDEX IF NOT EXISTS idx_health_reminders_due_date_time ON health_reminders(due_date, due_time)",
            "CREATE INDEX IF NOT EXISTS idx_health_reminders_reminder_date_time ON health_reminders(reminder_date, reminder_time)",
            "CREATE INDEX IF NOT EXISTS idx_health_reminders_status ON health_reminders(status)",
            "CREATE INDEX IF NOT EXISTS idx_health_reminders_recurrence_type ON health_reminders(recurrence_type)"
        ]
        
        for query in index_queries:
            cursor.execute(query)
            print(f"✅ Created index: {query}")
        
        # 4. Update existing reminders with default values
        cursor.execute("""
            UPDATE health_reminders 
            SET updated_at = CURRENT_TIMESTAMP,
                recurrence_type = COALESCE(recurrence_type, 'none'),
                current_occurrence = COALESCE(current_occurrence, 1),
                notification_attempts = COALESCE(notification_attempts, 0),
                hours_before_reminder = COALESCE(hours_before_reminder, 0),
                send_sms = COALESCE(send_sms, 0)
            WHERE updated_at IS NULL OR recurrence_type IS NULL
        """)
        
        # Commit changes
        conn.commit()
        print("✅ All reminder system enhancements applied successfully!")
        
        # 5. Verify the changes
        cursor.execute("PRAGMA table_info(health_reminders)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"📊 Health reminders table now has {len(columns)} columns:")
        for col in sorted(columns):
            print(f"   - {col}")
        
        cursor.execute("PRAGMA table_info(reminder_notifications)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"📊 Reminder notifications table has {len(columns)} columns:")
        for col in sorted(columns):
            print(f"   - {col}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error enhancing reminder system: {str(e)}")
        print(f"❌ Migration failed: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

def rollback_enhancement(db_path="migrations/health_tracker.db"):
    """Rollback the reminder enhancement (use with caution)"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Rolling back reminder system enhancements...")
        
        # Drop reminder_notifications table
        cursor.execute("DROP TABLE IF EXISTS reminder_notifications")
        print("✅ Dropped reminder_notifications table")
        
        # Note: SQLite doesn't support DROP COLUMN, so we can't easily remove the added columns
        # In production, you would need to create a new table and migrate data
        print("⚠️  Note: Added columns to health_reminders table cannot be easily removed in SQLite")
        print("   Consider using a new migration to recreate the table if needed")
        
        conn.commit()
        print("✅ Rollback completed!")
        
    except Exception as e:
        print(f"❌ Rollback failed: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_enhancement()
    else:
        enhance_reminders_system() 
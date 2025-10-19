#!/usr/bin/env python3
"""
Database Migration: Fix Hardcoded Message Timestamps
This script fixes any messages in the database that have a hardcoded timestamp of 2025-07-11T09:49:28.146600
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.message import Message
from datetime import datetime, timezone
from sqlalchemy import text

def fix_hardcoded_timestamps():
    """Fix hardcoded timestamps in the messages table"""
    print("🕒 Fixing hardcoded timestamps in messages table...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Find messages with hardcoded timestamps
            hardcoded_timestamp = '2025-07-11T09:49:28.146600'
            
            # Direct SQL approach for better performance with large tables
            query = text("""
                UPDATE messages 
                SET created_at = :current_time
                WHERE created_at = :hardcoded_time
            """)
            
            current_time = datetime.now(timezone.utc)
            result = db.session.execute(
                query, 
                {'current_time': current_time, 'hardcoded_time': hardcoded_timestamp}
            )
            
            affected_rows = result.rowcount
            db.session.commit()
            
            print(f"✅ Fixed {affected_rows} messages with hardcoded timestamps")
            print(f"🕒 New timestamp: {current_time}")
            
            # Also update any other tables that might reference this timestamp
            # Add more tables as needed
            
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    fix_hardcoded_timestamps() 
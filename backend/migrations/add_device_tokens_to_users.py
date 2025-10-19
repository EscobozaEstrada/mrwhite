#!/usr/bin/env python3
"""
Migration to add device token support to users table
"""

import sqlite3
import psycopg2
import os
from datetime import datetime

def add_device_tokens_to_users(db_path="migrations/health_tracker.db"):
    """
    Add device token fields to the users table
    """
    print(f"🔄 Adding device token fields to users table...")
    
    # Check if we're using PostgreSQL or SQLite
    if os.getenv('DATABASE_URL'):
        # PostgreSQL
        try:
            import psycopg2
            from urllib.parse import urlparse
            
            database_url = os.getenv('DATABASE_URL')
            parsed = urlparse(database_url)
            
            conn = psycopg2.connect(
                host=parsed.hostname,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password,
                port=parsed.port or 5432
            )
            cursor = conn.cursor()
            
            # Add device token fields
            queries = [
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS device_tokens JSONB DEFAULT '{}'::jsonb",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS push_notifications_enabled BOOLEAN DEFAULT TRUE",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_device_token_update TIMESTAMP"
            ]
            
            for query in queries:
                try:
                    cursor.execute(query)
                    print(f"✅ Executed: {query}")
                except Exception as e:
                    print(f"⚠️  Error (may already exist): {query} - {e}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ PostgreSQL migration error: {e}")
    else:
        # SQLite
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Add device token fields
            queries = [
                "ALTER TABLE users ADD COLUMN device_tokens TEXT DEFAULT '{}'",
                "ALTER TABLE users ADD COLUMN push_notifications_enabled BOOLEAN DEFAULT TRUE",
                "ALTER TABLE users ADD COLUMN last_device_token_update DATETIME"
            ]
            
            for query in queries:
                try:
                    cursor.execute(query)
                    print(f"✅ Executed: {query}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"⚠️  Column already exists: {query}")
                    else:
                        print(f"❌ Error: {query} - {e}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ SQLite migration error: {e}")
    
    print("✅ Device token fields migration completed!")

if __name__ == "__main__":
    add_device_tokens_to_users() 
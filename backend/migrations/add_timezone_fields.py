#!/usr/bin/env python3
"""
Database Migration: Add Timezone Management Fields
Adds AI-powered timezone and time management fields to users table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.user import User

def upgrade():
    """Add timezone management fields to users table"""
    print("🕐 Adding timezone management fields to users table...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if we're using SQLite or PostgreSQL
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            is_sqlite = 'sqlite' in database_url.lower()
            
            # Add timezone management fields
            timezone_fields = [
                ('timezone', 'VARCHAR(50)', 'UTC'),
                ('location_city', 'VARCHAR(100)', None),
                ('location_country', 'VARCHAR(100)', None),
                ('auto_detect_timezone', 'BOOLEAN', True),
                ('time_format_24h', 'BOOLEAN', False)
            ]
            
            for field_name, field_type, default_value in timezone_fields:
                try:
                    if is_sqlite:
                        if default_value is not None:
                            if isinstance(default_value, bool):
                                default_sql = f"DEFAULT {1 if default_value else 0}"
                            elif isinstance(default_value, str):
                                default_sql = f"DEFAULT '{default_value}'"
                            else:
                                default_sql = f"DEFAULT {default_value}"
                        else:
                            default_sql = ""
                        
                        db.session.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_type} {default_sql}")
                    else:
                        # PostgreSQL
                        if default_value is not None:
                            if isinstance(default_value, bool):
                                default_sql = f"DEFAULT {str(default_value).lower()}"
                            elif isinstance(default_value, str):
                                default_sql = f"DEFAULT '{default_value}'"
                            else:
                                default_sql = f"DEFAULT {default_value}"
                        else:
                            default_sql = ""
                        
                        db.session.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_type} {default_sql}")
                    
                    print(f"✅ Added {field_name} field")
                    
                except Exception as e:
                    if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                        print(f"⚠️  {field_name} field already exists, skipping")
                    else:
                        print(f"❌ Error adding {field_name} field: {str(e)}")
                        raise
            
            # Add preferred_reminder_times JSON field
            try:
                if is_sqlite:
                    db.session.execute("ALTER TABLE users ADD COLUMN preferred_reminder_times TEXT DEFAULT '{}'")
                else:
                    db.session.execute("ALTER TABLE users ADD COLUMN preferred_reminder_times JSONB DEFAULT '{}'")
                print("✅ Added preferred_reminder_times field")
                
            except Exception as e:
                if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                    print("⚠️  preferred_reminder_times field already exists, skipping")
                else:
                    print(f"❌ Error adding preferred_reminder_times field: {str(e)}")
                    raise
            
            db.session.commit()
            
            # Update existing users with default timezone
            print("\n🔄 Updating existing users with default timezone...")
            users = User.query.all()
            updated_count = 0
            
            for user in users:
                if not user.timezone:
                    user.timezone = 'UTC'
                    user.auto_detect_timezone = True
                    user.time_format_24h = False
                    if not user.preferred_reminder_times:
                        user.preferred_reminder_times = {}
                    updated_count += 1
            
            db.session.commit()
            print(f"✅ Updated {updated_count} users with default timezone settings")
            
            print("\n🎉 Successfully added timezone management fields!")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            db.session.rollback()
            raise

def downgrade():
    """Remove timezone management fields from users table"""
    print("🔄 Removing timezone management fields from users table...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Note: SQLite doesn't support dropping columns easily
            # This is mainly for PostgreSQL
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            is_sqlite = 'sqlite' in database_url.lower()
            
            if is_sqlite:
                print("⚠️  SQLite doesn't support dropping columns easily. Manual cleanup required.")
                return
            
            # Remove timezone fields
            timezone_fields = [
                'timezone',
                'location_city', 
                'location_country',
                'auto_detect_timezone',
                'time_format_24h',
                'preferred_reminder_times'
            ]
            
            for field_name in timezone_fields:
                try:
                    db.session.execute(f"ALTER TABLE users DROP COLUMN {field_name}")
                    print(f"✅ Removed {field_name} field")
                except Exception as e:
                    print(f"⚠️  Error removing {field_name} field: {str(e)}")
            
            db.session.commit()
            print("✅ Successfully removed timezone management fields!")
            
        except Exception as e:
            print(f"❌ Downgrade failed: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Timezone Management Migration')
    parser.add_argument('--downgrade', action='store_true', help='Downgrade migration')
    args = parser.parse_args()
    
    if args.downgrade:
        downgrade()
    else:
        upgrade() 
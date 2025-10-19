"""
Database Migration: Add Health-Specific Fields to Care Records

This migration adds essential health tracking fields to support:
- Multi-pet household management
- Structured symptom tracking
- Medication management
- Health risk assessment
- Better health context for AI

Run with: python migrations/add_health_fields_to_care_records.py
"""

import sys
import os
from datetime import datetime
from sqlalchemy import text

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def run_migration():
    """Add health-specific fields to care_records table"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 Starting migration: Add health fields to care_records...")
            
            # Check if migration already applied
            check_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'care_records' AND column_name = 'pet_name';
            """
            
            result = db.session.execute(text(check_sql)).fetchone()
            if result:
                print("✅ Migration already applied - pet_name column exists")
                return
            
            # Add new columns to care_records table
            migration_sql = """
            -- Pet identification fields
            ALTER TABLE care_records ADD COLUMN pet_name VARCHAR(100);
            ALTER TABLE care_records ADD COLUMN pet_breed VARCHAR(100);
            ALTER TABLE care_records ADD COLUMN pet_age INTEGER;
            ALTER TABLE care_records ADD COLUMN pet_weight FLOAT;
            
            -- Health-specific fields
            ALTER TABLE care_records ADD COLUMN severity_level INTEGER;
            ALTER TABLE care_records ADD COLUMN symptoms JSON;
            ALTER TABLE care_records ADD COLUMN medications JSON;
            ALTER TABLE care_records ADD COLUMN follow_up_required BOOLEAN DEFAULT FALSE;
            ALTER TABLE care_records ADD COLUMN follow_up_date TIMESTAMP;
            ALTER TABLE care_records ADD COLUMN health_tags JSON;
            
            -- Create indexes for better performance
            CREATE INDEX IF NOT EXISTS idx_care_records_pet_name ON care_records(pet_name);
            CREATE INDEX IF NOT EXISTS idx_care_records_follow_up_date ON care_records(follow_up_date);
            """
            
            # Execute migration
            for statement in migration_sql.split(';'):
                if statement.strip():
                    db.session.execute(text(statement.strip()))
            
            db.session.commit()
            print("✅ Successfully added health fields to care_records table")
            
            # Verify migration
            verify_sql = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'care_records' 
            AND column_name IN ('pet_name', 'pet_breed', 'pet_age', 'pet_weight', 'severity_level', 'symptoms', 'medications', 'follow_up_required', 'follow_up_date', 'health_tags')
            ORDER BY column_name;
            """
            
            columns = db.session.execute(text(verify_sql)).fetchall()
            print(f"📊 Added {len(columns)} new health fields:")
            for col in columns:
                print(f"  - {col.column_name} ({col.data_type})")
            
            print("\n🎉 Migration completed successfully!")
            print("\n📝 Next steps:")
            print("1. Update frontend forms to include pet_name field")
            print("2. Run backfill script to populate pet_name for existing records")
            print("3. Test health AI with enhanced care record data")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

def rollback_migration():
    """Rollback the migration (remove added fields)"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 Rolling back migration: Remove health fields from care_records...")
            
            rollback_sql = """
            -- Drop indexes
            DROP INDEX IF EXISTS idx_care_records_pet_name;
            DROP INDEX IF EXISTS idx_care_records_follow_up_date;
            
            -- Remove added columns
            ALTER TABLE care_records DROP COLUMN IF EXISTS pet_name;
            ALTER TABLE care_records DROP COLUMN IF EXISTS pet_breed;
            ALTER TABLE care_records DROP COLUMN IF EXISTS pet_age;
            ALTER TABLE care_records DROP COLUMN IF EXISTS pet_weight;
            ALTER TABLE care_records DROP COLUMN IF EXISTS severity_level;
            ALTER TABLE care_records DROP COLUMN IF EXISTS symptoms;
            ALTER TABLE care_records DROP COLUMN IF EXISTS medications;
            ALTER TABLE care_records DROP COLUMN IF EXISTS follow_up_required;
            ALTER TABLE care_records DROP COLUMN IF EXISTS follow_up_date;
            ALTER TABLE care_records DROP COLUMN IF EXISTS health_tags;
            """
            
            for statement in rollback_sql.split(';'):
                if statement.strip():
                    db.session.execute(text(statement.strip()))
            
            db.session.commit()
            print("✅ Migration rollback completed successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Rollback failed: {str(e)}")
            return False
        
        return True

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Care Records Health Fields Migration')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migration()
    else:
        run_migration() 
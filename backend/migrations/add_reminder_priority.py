#!/usr/bin/env python3
"""
Migration script to add priority field to health_reminders table
"""

import os
import sys
import logging
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Add priority column to health_reminders table"""
    try:
        logger.info("Starting migration: Adding priority column to health_reminders table")
        
        # Check if column already exists (PostgreSQL syntax)
        check_sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='health_reminders' AND column_name='priority'
        """)
        result = db.session.execute(check_sql)
        columns = [row[0] for row in result]
        
        if 'priority' in columns:
            logger.info("Column 'priority' already exists in health_reminders table. Skipping.")
            return
        
        # Add priority column with default value 'medium' (PostgreSQL syntax)
        add_column_sql = text("ALTER TABLE health_reminders ADD COLUMN priority VARCHAR(20) DEFAULT 'medium'")
        db.session.execute(add_column_sql)
        db.session.commit()
        
        logger.info("Successfully added priority column to health_reminders table")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        db.session.rollback()
        raise

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_migration()
        logger.info("Migration completed successfully") 
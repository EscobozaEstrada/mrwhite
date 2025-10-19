"""
Migration to add dog_name column to users table
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import sys
from sqlalchemy import text

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.user import User

def run_migration():
    """Add dog_name column to users table if it doesn't exist"""
    app = create_app()
    
    with app.app_context():
        # Check if the column exists
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'dog_name' not in columns:
            print("Adding dog_name column to users table...")
            
            # Add the column using the newer SQLAlchemy syntax
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE users ADD COLUMN dog_name VARCHAR(100);'))
            
            print("Migration completed successfully!")
        else:
            print("dog_name column already exists in users table.")

if __name__ == "__main__":
    run_migration() 
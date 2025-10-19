#!/usr/bin/env python3
"""
WSGI entry point for production deployment
"""
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

# Create the Flask application
application = create_app()

# Initialize database tables
with application.app_context():
    db.create_all()

if __name__ == "__main__":
    application.run() 
#!/usr/bin/env python3
"""
IC Image Sync Test Script
Test script to verify IC image synchronization to user_images table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.services.ic_image_sync_service import ICImageSyncService

def test_ic_sync():
    """Test IC image sync functionality"""
    app = create_app()
    
    with app.app_context():
        sync_service = ICImageSyncService()
        
        # Test with a specific user (you can change this)
        test_user_id = 1  # Change this to a real user ID
        
        print(f"🔍 Testing IC image sync for user {test_user_id}")
        
        # Get sync status
        print("\n📊 Getting sync status...")
        status = sync_service.get_sync_status(test_user_id)
        print(f"Status: {status}")
        
        # Sync images
        print("\n🔄 Syncing IC images...")
        result = sync_service.sync_ic_images_to_gallery(test_user_id, limit=10)
        print(f"Sync result: {result}")
        
        # Get updated status
        print("\n📊 Getting updated sync status...")
        updated_status = sync_service.get_sync_status(test_user_id)
        print(f"Updated status: {updated_status}")

if __name__ == "__main__":
    test_ic_sync()

#!/usr/bin/env python3
"""
Check the last_chat_fetch_at value for a specific chapter
"""

from app import create_app, db
from app.models.enhanced_book import EnhancedBookChapter

def check_chapter():
    """Check chapter last_chat_fetch_at value"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get the chapter
            chapter = EnhancedBookChapter.query.get(18)
            
            if chapter:
                print(f"Chapter ID: {chapter.id}")
                print(f"Title: {chapter.title}")
                print(f"Category: {chapter.category}")
                print(f"Last fetch time: {chapter.last_chat_fetch_at}")
            else:
                print("Chapter not found")
                
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_chapter() 
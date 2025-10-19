"""
Run the comprehensive Intelligent Chat schema migration
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import get_db_session
from sqlalchemy import text


async def run_migration():
    """Execute the comprehensive migration SQL file"""
    print("=" * 80)
    print("INTELLIGENT CHAT - COMPREHENSIVE SCHEMA MIGRATION")
    print("=" * 80)
    print()
    
    # Read the migration file
    migration_file = Path(__file__).parent / "000_comprehensive_intelligent_chat_schema.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"📄 Reading migration file: {migration_file.name}")
    with open(migration_file, 'r') as f:
        sql_content = f.read()
    
    # Get database session
    print("🔌 Connecting to database...")
    async for session in get_db_session():
        try:
            # Execute the migration
            print("🚀 Executing migration SQL...")
            print()
            
            await session.execute(text(sql_content))
            await session.commit()
            
            print()
            print("=" * 80)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print()
            print("All tables have been created:")
            print("  ✓ ic_conversations")
            print("  ✓ ic_messages (with triggers for date_group and search_vector)")
            print("  ✓ ic_conversation_context")
            print("  ✓ ic_dog_profiles")
            print("  ✓ ic_documents")
            print("  ✓ ic_message_documents")
            print("  ✓ ic_vet_reports")
            print("  ✓ ic_message_feedback")
            print("  ✓ ic_user_corrections")
            print("  ✓ ic_user_preferences")
            print("  ✓ ic_reminders")
            print("  ✓ ic_book_comments_access")
            print("  ✓ ic_credit_usage")
            print()
            print("All indexes and triggers have been created.")
            print("Foreign key constraints are in place.")
            print()
            print("🎉 Your Intelligent Chat system is ready to use!")
            print()
            
            return True
            
        except Exception as e:
            print()
            print("=" * 80)
            print("❌ MIGRATION FAILED!")
            print("=" * 80)
            print(f"Error: {str(e)}")
            print()
            print("Please check:")
            print("  1. Database connection is working")
            print("  2. Required tables (users, pet_profiles, book_notes) exist")
            print("  3. PostgreSQL permissions are correct")
            print()
            await session.rollback()
            return False


def main():
    """Main entry point"""
    print()
    result = asyncio.run(run_migration())
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()


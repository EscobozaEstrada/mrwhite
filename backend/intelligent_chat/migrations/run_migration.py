"""
Migration Script for Intelligent Chat System
Runs the initial schema migration
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text


async def run_migration():
    """Run the initial schema migration"""
    migration_file = Path(__file__).parent / "001_create_initial_schema.sql"
    
    print("🚀 Starting Intelligent Chat System Migration...")
    print(f"📄 Reading migration file: {migration_file}")
    
    # Get database URL
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL environment variable not found!")
        print("Please set DATABASE_URL in your .env file")
        return
    
    # Convert to async URL
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    print(f"📊 Connecting to database...")
    
    # Create async engine
    engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
    
    # Read the SQL file
    with open(migration_file, 'r') as f:
        sql_content = f.read()
    
    print(f"📊 Executing migration SQL...")
    
    # Execute the entire SQL content at once (PostgreSQL can handle multiple statements)
    async with engine.begin() as conn:
        try:
            await conn.execute(text(sql_content))
            
            print("✅ Migration completed successfully!")
            print("\n📋 Created tables:")
            print("   - ic_conversations")
            print("   - ic_messages")
            print("   - ic_documents")
            print("   - ic_vet_reports")
            print("   - ic_reminders")
            print("   - ic_user_corrections")
            print("   - ic_message_feedback")
            print("   - ic_user_preferences")
            print("   - ic_conversation_context")
            print("   - ic_credit_usage")
            print("   - ic_book_comments_access")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migration())


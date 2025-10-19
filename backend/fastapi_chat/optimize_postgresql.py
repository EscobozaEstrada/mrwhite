#!/usr/bin/env python3
"""
PostgreSQL Performance Optimization Script
Creates optimal indexes for FastAPI chat service
"""

import os
import asyncio
import logging
from sqlalchemy import text
from models import async_engine

logger = logging.getLogger(__name__)

# Performance optimization SQL commands
OPTIMIZATION_SQL = [
    # ==================== INDEX OPTIMIZATIONS ====================
    
    # Conversations table - optimized for user queries
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_user_updated 
    ON conversations(user_id, updated_at DESC) 
    WHERE user_id IS NOT NULL;
    """,
    
    # Messages table - optimized for conversation queries  
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_conversation_created
    ON messages(conversation_id, created_at DESC)
    WHERE conversation_id IS NOT NULL;
    """,
    
    # Messages table - optimized for bookmarked messages
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_bookmarked
    ON messages(conversation_id, is_bookmarked, created_at DESC)
    WHERE is_bookmarked = true;
    """,
    
    # Users table - optimized for authentication
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active
    ON users(email) 
    WHERE email IS NOT NULL;
    """,
    
    # Attachments table - optimized for message queries
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_attachments_message
    ON attachments(message_id)
    WHERE message_id IS NOT NULL;
    """,
    
    # ==================== PERFORMANCE TUNING ====================
    
    # Enable query plan optimization
    "SET shared_preload_libraries = 'pg_stat_statements';",
    
    # Optimize for async workloads
    "SET max_connections = 100;",
    "SET shared_buffers = '256MB';",
    "SET effective_cache_size = '1GB';",
    "SET work_mem = '4MB';",
    "SET maintenance_work_mem = '64MB';",
    
    # Enable auto-vacuum for high-write workloads
    "ALTER TABLE conversations SET (autovacuum_vacuum_scale_factor = 0.1);",
    "ALTER TABLE messages SET (autovacuum_vacuum_scale_factor = 0.1);",
    
    # ==================== STATISTICS UPDATES ====================
    
    # Update table statistics for query optimization
    "ANALYZE conversations;",
    "ANALYZE messages;", 
    "ANALYZE users;",
    "ANALYZE attachments;",
]

async def optimize_database():
    """Apply PostgreSQL optimizations for chat service"""
    try:
        async with async_engine.begin() as conn:
            logger.info("🚀 Starting PostgreSQL optimization...")
            
            for i, sql in enumerate(OPTIMIZATION_SQL, 1):
                try:
                    logger.info(f"📊 Applying optimization {i}/{len(OPTIMIZATION_SQL)}")
                    await conn.execute(text(sql))
                    logger.info(f"✅ Optimization {i} completed")
                except Exception as e:
                    # Some optimizations may fail if already applied
                    if "already exists" in str(e).lower():
                        logger.info(f"⏭️  Optimization {i} already applied")
                    else:
                        logger.warning(f"⚠️  Optimization {i} failed: {e}")
            
            logger.info("🎯 PostgreSQL optimization completed!")
            
    except Exception as e:
        logger.error(f"❌ Database optimization failed: {e}")
        raise

async def check_performance():
    """Check current database performance metrics"""
    try:
        async with async_engine.begin() as conn:
            logger.info("📈 Checking database performance...")
            
            # Check table sizes
            table_sizes = await conn.execute(text("""
                SELECT schemaname, tablename, 
                       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """))
            
            logger.info("📋 Table sizes:")
            for row in table_sizes:
                logger.info(f"  {row.tablename}: {row.size}")
            
            # Check index usage
            index_usage = await conn.execute(text("""
                SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE schemaname = 'public'
                ORDER BY idx_tup_read DESC
                LIMIT 10;
            """))
            
            logger.info("🔍 Index usage (top 10):")
            for row in index_usage:
                logger.info(f"  {row.indexname}: {row.idx_tup_read} reads, {row.idx_tup_fetch} fetches")
                
    except Exception as e:
        logger.error(f"❌ Performance check failed: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        await optimize_database()
        await check_performance()
    
    asyncio.run(main())
"""
Account Deletion Service for Intelligent Chat
Handles complete cleanup of user data from ic_* tables, Pinecone, and S3
"""
import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, text

from models.conversation import (
    Message,
    Conversation,
    ConversationContext,
    MessageFeedback,
    UserCorrection
)
from models.dog_profile import DogProfile
from models.document import Document, VetReport
from models.user_preference import UserPreference
from services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class AccountDeletionService:
    """Service for complete account deletion from intelligent chat system"""
    
    def __init__(self):
        self.memory_service = MemoryService()
    
    async def delete_user_data_complete(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Completely delete all user data from intelligent chat system
        
        Args:
            db: Database session
            user_id: User ID to delete
        
        Returns:
            Dict with deletion statistics
        """
        stats = {
            "messages_deleted": 0,
            "conversations_deleted": 0,
            "documents_deleted": 0,
            "dog_profiles_deleted": 0,
            "pinecone_cleared": False,
            "s3_cleared": False
        }
        
        try:
            logger.info(f"🗑️ Starting complete data deletion for user {user_id}")
            
            # 1. Get all conversation IDs for this user
            conv_result = await db.execute(
                text("SELECT id FROM ic_conversations WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            conversation_ids = [row[0] for row in conv_result.fetchall()]
            stats["conversations_deleted"] = len(conversation_ids)
            
            # 2. Get all message IDs for these conversations
            if conversation_ids:
                msg_result = await db.execute(
                    text("SELECT id FROM ic_messages WHERE conversation_id = ANY(:conv_ids)"),
                    {"conv_ids": conversation_ids}
                )
                message_ids = [row[0] for row in msg_result.fetchall()]
                stats["messages_deleted"] = len(message_ids)
                
                # 3. Delete message-related data (foreign key order matters!)
                if message_ids:
                    # Delete message feedback
                    await db.execute(
                        text("DELETE FROM ic_message_feedback WHERE message_id = ANY(:msg_ids)"),
                        {"msg_ids": message_ids}
                    )
                    logger.info(f"✅ Deleted message feedback for user {user_id}")
                    
                    # Delete message-document associations
                    await db.execute(
                        text("DELETE FROM ic_message_document WHERE message_id = ANY(:msg_ids)"),
                        {"msg_ids": message_ids}
                    )
                    logger.info(f"✅ Deleted message-document links for user {user_id}")
                
                # 4. Delete user corrections
                await db.execute(
                    text("DELETE FROM ic_user_corrections WHERE conversation_id = ANY(:conv_ids)"),
                    {"conv_ids": conversation_ids}
                )
                logger.info(f"✅ Deleted user corrections for user {user_id}")
                
                # 5. Delete conversation context
                await db.execute(
                    text("DELETE FROM ic_conversation_context WHERE conversation_id = ANY(:conv_ids)"),
                    {"conv_ids": conversation_ids}
                )
                logger.info(f"✅ Deleted conversation context for user {user_id}")
                
                # 6. Delete messages
                await db.execute(
                    text("DELETE FROM ic_messages WHERE conversation_id = ANY(:conv_ids)"),
                    {"conv_ids": conversation_ids}
                )
                logger.info(f"✅ Deleted {stats['messages_deleted']} messages for user {user_id}")
            
            # 7. Delete conversations
            await db.execute(
                text("DELETE FROM ic_conversations WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            logger.info(f"✅ Deleted {stats['conversations_deleted']} conversations for user {user_id}")
            
            # 8. Count and delete documents
            doc_count_result = await db.execute(
                text("SELECT COUNT(*) FROM ic_documents WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            stats["documents_deleted"] = doc_count_result.scalar()
            
            await db.execute(
                text("DELETE FROM ic_vet_reports WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            await db.execute(
                text("DELETE FROM ic_documents WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            logger.info(f"✅ Deleted {stats['documents_deleted']} documents for user {user_id}")
            
            # 9. Count and delete dog profiles
            dog_count_result = await db.execute(
                text("SELECT COUNT(*) FROM ic_dog_profiles WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            stats["dog_profiles_deleted"] = dog_count_result.scalar()
            
            await db.execute(
                text("DELETE FROM ic_dog_profiles WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            logger.info(f"✅ Deleted {stats['dog_profiles_deleted']} dog profiles for user {user_id}")
            
            # 10. Delete user preferences
            await db.execute(
                text("DELETE FROM ic_user_preferences WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            logger.info(f"✅ Deleted user preferences for user {user_id}")
            
            # 11. Delete book comments access logs
            await db.execute(
                text("DELETE FROM ic_book_comments_access WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            logger.info(f"✅ Deleted book comments access logs for user {user_id}")
            
            # 12. Delete credit usage tracking
            await db.execute(
                text("DELETE FROM ic_credit_usage WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            logger.info(f"✅ Deleted credit usage tracking for user {user_id}")
            
            # Commit all database deletions
            await db.commit()
            logger.info(f"✅ All database deletions committed for user {user_id}")
            
            # 13. Clear Pinecone vectors (all namespaces + user-specific + S3)
            try:
                pinecone_success = await self.memory_service.clear_user_memories_complete(
                    user_id=user_id,
                    include_s3=True  # Also delete S3 files
                )
                stats["pinecone_cleared"] = pinecone_success
                stats["s3_cleared"] = pinecone_success  # S3 is included in this call
                
                if pinecone_success:
                    logger.info(f"✅ Cleared Pinecone and S3 data for user {user_id}")
                else:
                    logger.warning(f"⚠️ Pinecone/S3 clearing had issues for user {user_id}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to clear Pinecone/S3 for user {user_id}: {e}")
                stats["pinecone_cleared"] = False
                stats["s3_cleared"] = False
            
            logger.info(f"✅ COMPLETE: Deleted all data for user {user_id}")
            logger.info(f"📊 Deletion stats: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Account deletion failed for user {user_id}: {str(e)}")
            await db.rollback()
            raise
    
    async def get_user_data_summary(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict[str, int]:
        """
        Get summary of user's data before deletion (for confirmation)
        
        Args:
            db: Database session
            user_id: User ID
        
        Returns:
            Dict with data counts
        """
        try:
            summary = {}
            
            # Count conversations
            conv_result = await db.execute(
                text("SELECT COUNT(*) FROM ic_conversations WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            summary["conversations"] = conv_result.scalar()
            
            # Count messages
            msg_result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM ic_messages 
                    WHERE conversation_id IN (
                        SELECT id FROM ic_conversations WHERE user_id = :user_id
                    )
                """),
                {"user_id": user_id}
            )
            summary["messages"] = msg_result.scalar()
            
            # Count documents
            doc_result = await db.execute(
                text("SELECT COUNT(*) FROM ic_documents WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            summary["documents"] = doc_result.scalar()
            
            # Count dog profiles
            dog_result = await db.execute(
                text("SELECT COUNT(*) FROM ic_dog_profiles WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            summary["dog_profiles"] = dog_result.scalar()
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Failed to get user data summary: {str(e)}")
            return {}



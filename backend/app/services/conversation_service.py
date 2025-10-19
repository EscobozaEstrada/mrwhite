from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from flask import current_app
from sqlalchemy.orm import joinedload
from app import db
from app.models.conversation import Conversation
from app.models.message import Message, Attachment
from app.utils.file_handler import store_chat_message
from app.utils.cache import cached, invalidate_user_cache, performance_monitor


class ConversationService:
    """Service class for handling conversation operations"""
    
    @staticmethod
    @performance_monitor
    def get_user_conversations(user_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user with optimized query
        
        Args:
            user_id: User ID
            limit: Optional limit for number of conversations
            
        Returns:
            List of conversation dictionaries
        """
        try:
            query = (Conversation.query
                    .filter_by(user_id=user_id)
                    .order_by(Conversation.updated_at.desc()))
            
            if limit:
                query = query.limit(limit)
            
            conversations = query.all()
            return [conv.to_dict() for conv in conversations]
            
        except Exception as e:
            current_app.logger.error(f"Error getting user conversations: {str(e)}")
            return []
    
    @staticmethod
    def get_conversation_with_messages(conversation_id: int, user_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Get conversation with messages using optimized query with joins
        
        Returns:
            Tuple of (success: bool, message: str, data: Optional[Dict])
        """
        try:
            # Use joinedload to fetch conversation with messages and attachments in one query
            conversation = (Conversation.query
                          .options(joinedload(Conversation.messages).joinedload(Message.attachments))
                          .filter_by(id=conversation_id, user_id=user_id)
                          .first())
            
            if not conversation:
                return False, 'Conversation not found', None
            
            # Sort messages by creation date
            sorted_messages = sorted(conversation.messages, key=lambda m: m.created_at)
            
            return True, 'Success', {
                'conversation': conversation.to_dict(),
                'messages': [msg.to_dict() for msg in sorted_messages]
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting conversation: {str(e)}")
            return False, 'Internal server error', None
    
    @staticmethod
    def create_conversation(user_id: int, title: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create a new conversation with retry logic for database timeouts
        
        Returns:
            Tuple of (success: bool, message: str, conversation_data: Optional[Dict])
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if not title:
                    title = current_app.config.get('DEFAULT_CONVERSATION_TITLE', 'New Conversation')
                
                conversation = Conversation(user_id=user_id, title=title)
                db.session.add(conversation)
                
                # Use shorter timeout for commit
                db.session.commit()
                
                # Invalidate user cache
                try:
                    invalidate_user_cache(user_id)
                except Exception as cache_error:
                    current_app.logger.warning(f"Cache invalidation failed: {str(cache_error)}")
                
                current_app.logger.info(f"Conversation created successfully for user {user_id}")
                return True, 'Conversation created successfully', conversation.to_dict()
                
            except Exception as e:
                db.session.rollback()
                retry_count += 1
                error_msg = str(e)
                
                current_app.logger.error(f"Error creating conversation (attempt {retry_count}/{max_retries}): {error_msg}")
                
                # Check if it's a timeout or connection error
                if any(keyword in error_msg.lower() for keyword in ['timeout', 'connection', 'closed']):
                    if retry_count < max_retries:
                        current_app.logger.info(f"Retrying conversation creation due to connection issue...")
                        # Wait a bit before retrying
                        import time
                        time.sleep(0.5)
                        continue
                
                # If it's not a retryable error or we've exhausted retries
                if retry_count >= max_retries:
                    return False, 'Database connection issue. Please try again in a moment.', None
        
        # This shouldn't be reached, but just in case
        return False, 'Unable to create conversation after multiple attempts', None
    
    @staticmethod
    def update_conversation(conversation_id: int, user_id: int, title: Optional[str] = None, 
                          is_bookmarked: Optional[bool] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Update conversation details
        
        Returns:
            Tuple of (success: bool, message: str, conversation_data: Optional[Dict])
        """
        try:
            conversation = Conversation.query.filter_by(id=conversation_id, user_id=user_id).first()
            
            if not conversation:
                return False, 'Conversation not found', None
            
            # Update fields if provided
            if title is not None:
                conversation.title = title
            
            if is_bookmarked is not None:
                conversation.is_bookmarked = is_bookmarked
            
            conversation.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Invalidate user cache
            invalidate_user_cache(user_id)
            
            return True, 'Conversation updated successfully', conversation.to_dict()
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating conversation: {str(e)}")
            return False, 'Internal server error', None
    
    @staticmethod
    def delete_conversation(conversation_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Delete a conversation and all associated messages
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            conversation = Conversation.query.filter_by(id=conversation_id, user_id=user_id).first()
            
            if not conversation:
                return False, 'Conversation not found'
            
            db.session.delete(conversation)
            db.session.commit()
            
            return True, 'Conversation deleted successfully'
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting conversation: {str(e)}")
            return False, 'Internal server error'
    
    @staticmethod
    def add_message(conversation_id: int, user_id: int, content: str, message_type: str = 'user',
                   attachments: Optional[List[Dict[str, Any]]] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Add a message to a conversation
        
        Returns:
            Tuple of (success: bool, message: str, message_data: Optional[Dict])
        """
        try:
            # Verify conversation belongs to user
            conversation = Conversation.query.filter_by(id=conversation_id, user_id=user_id).first()
            
            if not conversation:
                return False, 'Conversation not found', None
            
            # Create message
            message = Message(
                conversation_id=conversation_id,
                content=content,
                type=message_type
            )
            
            db.session.add(message)
            db.session.flush()  # Get message ID for attachments
            
            # Add attachments if provided
            if attachments:
                for attachment_data in attachments:
                    attachment = Attachment(
                        message_id=message.id,
                        type=attachment_data.get('type', 'file'),
                        url=attachment_data.get('url', ''),
                        name=attachment_data.get('name', '')
                    )
                    db.session.add(attachment)
            
            # Update conversation timestamp
            conversation.updated_at = datetime.now(timezone.utc)
            
            # Update conversation title if it's the first user message and title is default
            if (message_type == 'user' and 
                conversation.title in ['New Conversation', current_app.config.get('DEFAULT_CONVERSATION_TITLE', 'New Conversation')] and
                len(content.strip()) > 0):
                conversation.title = content[:50] + "..." if len(content) > 50 else content
            
            db.session.commit()
            
            # Store message in vector database for RAG
            if message_type in ['user', 'ai']:
                try:
                    store_result, store_message = store_chat_message(
                        user_id=user_id,
                        message_content=content,
                        message_id=message.id,
                        message_type=message_type,
                        conversation_id=conversation_id
                    )
                    if not store_result:
                        current_app.logger.warning(f"Failed to store message in vector DB: {store_message}")
                except Exception as e:
                    current_app.logger.warning(f"Error storing message in vector DB: {str(e)}")
            
            return True, 'Message added successfully', message.to_dict()
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding message: {str(e)}")
            return False, 'Internal server error', None
    
    @staticmethod
    def toggle_message_bookmark(message_id: int, user_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Toggle bookmark status of a message
        
        Returns:
            Tuple of (success: bool, message: str, message_data: Optional[Dict])
        """
        try:
            message = (Message.query
                      .join(Conversation)
                      .filter(Message.id == message_id, Conversation.user_id == user_id)
                      .first())
            
            if not message:
                return False, 'Message not found', None
            
            message.is_bookmarked = not message.is_bookmarked
            message.bookmark_date = datetime.now(timezone.utc) if message.is_bookmarked else None
            db.session.commit()
            
            return True, 'Bookmark updated successfully', message.to_dict()
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error toggling message bookmark: {str(e)}")
            return False, 'Internal server error', None
    
    @staticmethod
    def toggle_message_reaction(message_id: int, user_id: int, reaction_type: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Toggle like/dislike reaction on a message
        
        Returns:
            Tuple of (success: bool, message: str, message_data: Optional[Dict])
        """
        try:
            if reaction_type not in ['like', 'dislike']:
                return False, 'Invalid reaction type', None
            
            message = (Message.query
                      .join(Conversation)
                      .filter(Message.id == message_id, Conversation.user_id == user_id)
                      .first())
            
            if not message:
                return False, 'Message not found', None
            
            if reaction_type == 'like':
                message.liked = not message.liked
                if message.liked:
                    message.disliked = False
            elif reaction_type == 'dislike':
                message.disliked = not message.disliked
                if message.disliked:
                    message.liked = False
            
            db.session.commit()
            
            return True, 'Reaction updated successfully', message.to_dict()
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error toggling message reaction: {str(e)}")
            return False, 'Internal server error', None
    
    @staticmethod
    def get_bookmarked_messages(user_id: int) -> List[Dict[str, Any]]:
        """
        Get all bookmarked messages for a user
        
        Returns:
            List of bookmarked message dictionaries
        """
        try:
            bookmarked_messages = (Message.query
                                 .join(Conversation)
                                 .filter(Conversation.user_id == user_id, Message.is_bookmarked == True)
                                 .order_by(Message.bookmark_date.desc())
                                 .all())
            
            return [msg.to_dict() for msg in bookmarked_messages]
            
        except Exception as e:
            current_app.logger.error(f"Error getting bookmarked messages: {str(e)}")
            return []
    
    @staticmethod
    def get_bookmarked_conversations(user_id: int) -> List[Dict[str, Any]]:
        """
        Get all bookmarked conversations for a user
        
        Returns:
            List of bookmarked conversation dictionaries
        """
        try:
            bookmarked_conversations = (Conversation.query
                                      .filter_by(user_id=user_id, is_bookmarked=True)
                                      .order_by(Conversation.updated_at.desc())
                                      .all())
            
            return [conv.to_dict() for conv in bookmarked_conversations]
            
        except Exception as e:
            current_app.logger.error(f"Error getting bookmarked conversations: {str(e)}")
            return []
    
    @staticmethod
    def delete_all_user_conversations(user_id: int) -> Tuple[bool, str]:
        """
        Delete all conversations and associated messages for a user
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # First, get all conversation IDs for the user
            conversation_ids = [conv.id for conv in Conversation.query.filter_by(user_id=user_id).all()]
            
            if not conversation_ids:
                return True, 'No conversations to delete'
            
            # Import Attachment model for proper deletion order
            from app.models.message import Attachment
            
            # Get all message IDs for these conversations
            messages = Message.query.filter(Message.conversation_id.in_(conversation_ids)).all()
            message_ids = [msg.id for msg in messages]
            
            if message_ids:
                # Delete attachments first (foreign key constraint)
                Attachment.query.filter(Attachment.message_id.in_(message_ids)).delete(synchronize_session=False)
            
            # Then delete all messages for these conversations
            Message.query.filter(Message.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
            
            # Finally delete all conversations
            Conversation.query.filter_by(user_id=user_id).delete(synchronize_session=False)
            
            # Commit the changes
            db.session.commit()
            
            # Invalidate user cache
            invalidate_user_cache(user_id)
            
            return True, f'Successfully deleted all conversations and their messages'
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting all conversations: {str(e)}")
            return False, 'Internal server error' 
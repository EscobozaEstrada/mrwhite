from typing import Dict, Optional
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.care_record import CareRecord, Document
import logging

class UsageTrackingService:
    """Service to track and enforce usage limits for free users"""
    
    # Free tier limits
    FREE_LIMITS = {
        'chat_messages_per_day': 10,
        'chat_messages_per_month': 100,
        'documents_per_month': 5,
        'care_records_per_month': 20,
        'conversations_total': 5
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_user_usage(self, user_id: int) -> Dict:
        """Get comprehensive usage stats for a user"""
        try:
            user = User.query.get(user_id)
            if not user:
                return {}
            
            # Premium users have unlimited usage
            if user.is_premium and user.subscription_status == 'active':
                return {
                    'is_premium': True,
                    'unlimited': True
                }
            
            today = datetime.now().date()
            month_start = datetime.now().replace(day=1).date()
            
            # Chat message usage
            daily_messages = self._count_daily_messages(user_id, today)
            monthly_messages = self._count_monthly_messages(user_id, month_start)
            
            # Document usage
            monthly_documents = self._count_monthly_documents(user_id, month_start)
            
            # Care records usage
            monthly_care_records = self._count_monthly_care_records(user_id, month_start)
            
            # Total conversations
            total_conversations = self._count_total_conversations(user_id)
            
            return {
                'is_premium': False,
                'unlimited': False,
                'usage': {
                    'chat_messages_today': daily_messages,
                    'chat_messages_this_month': monthly_messages,
                    'documents_this_month': monthly_documents,
                    'care_records_this_month': monthly_care_records,
                    'total_conversations': total_conversations
                },
                'limits': self.FREE_LIMITS,
                'remaining': {
                    'chat_messages_today': max(0, self.FREE_LIMITS['chat_messages_per_day'] - daily_messages),
                    'chat_messages_this_month': max(0, self.FREE_LIMITS['chat_messages_per_month'] - monthly_messages),
                    'documents_this_month': max(0, self.FREE_LIMITS['documents_per_month'] - monthly_documents),
                    'care_records_this_month': max(0, self.FREE_LIMITS['care_records_per_month'] - monthly_care_records),
                    'conversations': max(0, self.FREE_LIMITS['conversations_total'] - total_conversations)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user usage: {str(e)}")
            return {}
    
    def check_chat_limit(self, user_id: int) -> tuple[bool, str]:
        """Check if user can send more chat messages"""
        user = User.query.get(user_id)
        if user and user.is_premium and user.subscription_status == 'active':
            return True, "Premium user - unlimited access"
        
        usage = self.get_user_usage(user_id)
        if not usage or usage.get('unlimited'):
            return True, "No limits"
        
        # Check daily limit
        daily_remaining = usage['remaining']['chat_messages_today']
        if daily_remaining <= 0:
            return False, f"Daily limit reached ({self.FREE_LIMITS['chat_messages_per_day']} messages). Upgrade to Elite Pack for unlimited access."
        
        # Check monthly limit
        monthly_remaining = usage['remaining']['chat_messages_this_month']
        if monthly_remaining <= 0:
            return False, f"Monthly limit reached ({self.FREE_LIMITS['chat_messages_per_month']} messages). Upgrade to Elite Pack for unlimited access."
        
        return True, f"You have {daily_remaining} messages remaining today"
    
    def check_document_limit(self, user_id: int) -> tuple[bool, str]:
        """Check if user can upload more documents"""
        user = User.query.get(user_id)
        if user and user.is_premium and user.subscription_status == 'active':
            return True, "Premium user - unlimited access"
        
        usage = self.get_user_usage(user_id)
        if not usage or usage.get('unlimited'):
            return True, "No limits"
        
        remaining = usage['remaining']['documents_this_month']
        if remaining <= 0:
            return False, f"Monthly document limit reached ({self.FREE_LIMITS['documents_per_month']} documents). Upgrade to Elite Pack for unlimited uploads."
        
        return True, f"You can upload {remaining} more documents this month"
    
    def check_care_record_limit(self, user_id: int) -> tuple[bool, str]:
        """Check if user can create more care records"""
        user = User.query.get(user_id)
        if user and user.is_premium and user.subscription_status == 'active':
            return True, "Premium user - unlimited access"
        
        usage = self.get_user_usage(user_id)
        if not usage or usage.get('unlimited'):
            return True, "No limits"
        
        remaining = usage['remaining']['care_records_this_month']
        if remaining <= 0:
            return False, f"Monthly care record limit reached ({self.FREE_LIMITS['care_records_per_month']} records). Upgrade to Elite Pack for unlimited records."
        
        return True, f"You can create {remaining} more care records this month"
    
    def check_conversation_limit(self, user_id: int) -> tuple[bool, str]:
        """Check if user can create more conversations"""
        user = User.query.get(user_id)
        if user and user.is_premium and user.subscription_status == 'active':
            return True, "Premium user - unlimited access"
        
        usage = self.get_user_usage(user_id)
        if not usage or usage.get('unlimited'):
            return True, "No limits"
        
        remaining = usage['remaining']['conversations']
        if remaining <= 0:
            return False, f"Conversation limit reached ({self.FREE_LIMITS['conversations_total']} conversations). Upgrade to Elite Pack for unlimited conversations."
        
        return True, f"You can create {remaining} more conversations"
    
    def _count_daily_messages(self, user_id: int, date: datetime) -> int:
        """Count messages sent by user today"""
        start_datetime = datetime.combine(date, datetime.min.time())
        end_datetime = start_datetime + timedelta(days=1)
        
        return Message.query.join(Conversation).filter(
            Conversation.user_id == user_id,
            Message.type == 'user',
            Message.created_at >= start_datetime,
            Message.created_at < end_datetime
        ).count()
    
    def _count_monthly_messages(self, user_id: int, month_start: datetime) -> int:
        """Count messages sent by user this month"""
        return Message.query.join(Conversation).filter(
            Conversation.user_id == user_id,
            Message.type == 'user',
            Message.created_at >= month_start
        ).count()
    
    def _count_monthly_documents(self, user_id: int, month_start: datetime) -> int:
        """Count documents uploaded by user this month"""
        return Document.query.filter(
            Document.user_id == user_id,
            Document.created_at >= month_start
        ).count()
    
    def _count_monthly_care_records(self, user_id: int, month_start: datetime) -> int:
        """Count care records created by user this month"""
        return CareRecord.query.filter(
            CareRecord.user_id == user_id,
            CareRecord.created_at >= month_start
        ).count()
    
    def _count_total_conversations(self, user_id: int) -> int:
        """Count total conversations created by user"""
        return Conversation.query.filter_by(user_id=user_id).count()
    
    def record_usage(self, user_id: int, action: str, metadata: dict = None):
        """Record usage action for analytics"""
        try:
            # This could be extended to store usage logs in a separate table
            # For now, just log for analytics
            self.logger.info(f"Usage recorded - User: {user_id}, Action: {action}, Metadata: {metadata}")
        except Exception as e:
            self.logger.error(f"Error recording usage: {str(e)}") 
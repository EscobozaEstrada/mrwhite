from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
import logging
import json

class CreditSystemService:
    """Credit-based system for Elite subscription plan with credit top-ups"""
    
    # Credit costs for different actions (in credits where 1 credit = $0.01)
    CREDIT_COSTS = {
        # Chat & AI Features
        'chat_message_basic': 2,      # $0.02 - Basic chat response
        'chat_message_advanced': 5,   # $0.05 - Advanced chat with context
        'chat_message_health': 8,     # $0.08 - Health analysis
        'document_upload': 8,         # $0.08 - Document processing
        'document_analysis': 12,      # $0.12 - AI document analysis
        'voice_message': 3,           # $0.03 - Voice processing
        'health_assessment': 15,      # $0.15 - Comprehensive health assessment
        'care_record_ai': 6,          # $0.06 - AI-powered care record analysis
        
        # Premium Features (Elite only)
        'enhanced_chat': 8,           # $0.08 - Enhanced chat with memory
        'care_archive_search': 4,     # $0.04 - Search through care archive
        'health_insights': 20,        # $0.20 - AI health insights generation
        'care_summary': 15,           # $0.15 - Comprehensive care summary
        
        # File & Storage
        'file_storage_gb': 1,         # $0.01 per GB per month
        'large_document': 15,         # $0.15 for documents >10MB
    }
    
    # Subscription plans configuration
    SUBSCRIPTION_PLANS = {
        'free': {
            'name': 'Free Companion',
            'daily_free_credits': 10,     # $0.10 worth of free credits daily
            'monthly_credit_allowance': 0,
            'price': 0,
            'features': ['basic_chat', 'limited_uploads'],
            'can_purchase_credits': False  # Free users must upgrade to buy credits
        },
        'elite': {
            'name': 'Elite Pack',
            'daily_free_credits': 0,      # No daily free credits for Elite
            'monthly_credit_allowance': 3000,  # $30.00 worth of credits monthly
            'price': 28.95,
            'features': ['all_features', 'premium_support', 'unlimited_conversations'],
            'can_purchase_credits': True   # Elite users can buy additional credits
        }
    }
    
    # Credit purchase packages (only for Elite users)
    CREDIT_PACKAGES = {
        'small': {'credits': 500, 'price': 4.99, 'bonus': 50},       # $4.99 for $5.50 worth
        'medium': {'credits': 1000, 'price': 9.99, 'bonus': 150},    # $9.99 for $11.50 worth
        'large': {'credits': 2000, 'price': 19.99, 'bonus': 400},    # $19.99 for $24.00 worth
        'xlarge': {'credits': 5001, 'price': 49.99, 'bonus': 1200},  # $49.99 for $62.00 worth
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_and_deduct_credits(self, user_id: int, action: str, metadata: Dict = None) -> Tuple[bool, str, int]:
        """
        Check if user has enough credits and deduct them
        
        Returns:
            Tuple of (success: bool, message: str, credits_deducted: int)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found", 0
            
            # Calculate credit cost
            base_cost = self.CREDIT_COSTS.get(action, 3)
            total_cost = self._calculate_dynamic_cost(action, base_cost, metadata)
            
            # Check user's subscription and available credits
            available_credits = self._get_available_credits(user)
            
            # For Elite users, check if they have access to the feature
            if user.is_premium and user.subscription_status == 'active':
                # Elite users can use all features if they have credits
                if available_credits < total_cost:
                    shortage = total_cost - available_credits
                    return False, f"Insufficient credits. Need {total_cost} credits (${total_cost/100:.2f}), have {available_credits} (${available_credits/100:.2f}). Purchase {shortage} more credits to continue.", 0
            else:
                # Free users have limited access
                free_plan = self.SUBSCRIPTION_PLANS['free']
                if action not in ['chat_message_basic', 'document_upload'] or available_credits < total_cost:
                    return False, f"Upgrade to Elite Pack for full access to all features and monthly credit allowance.", 0
            
            # Deduct credits
            self._deduct_credits(user, total_cost, action, metadata)
            
            return True, f"Success. {total_cost} credits deducted (${total_cost/100:.2f}).", total_cost
            
        except Exception as e:
            self.logger.error(f"Error checking/deducting credits: {str(e)}")
            return False, "Credit system error", 0
    
    def add_credits(self, user_id: int, amount: int, source: str = 'purchase', metadata: Dict = None) -> bool:
        """Add credits to user account"""
        try:
            user = User.query.get(user_id)
            if not user:
                self.logger.error(f"User {user_id} not found when adding credits")
                return False
            
            # Only Elite users can purchase additional credits
            if source == 'purchase' and not (user.is_premium and user.subscription_status == 'active'):
                self.logger.error(f"User {user_id} cannot purchase credits - Premium: {user.is_premium}, Status: {user.subscription_status}")
                return False
            
            # Log the operation
            balance_before = user.credits_balance
            purchased_before = user.total_credits_purchased
            
            self.logger.info(f"Adding {amount} credits to user {user_id} (source: {source})")
            self.logger.info(f"Before: Balance={balance_before}, Total purchased={purchased_before}")
            
            # Update balances
            user.credits_balance += amount
            
            if source == 'purchase':
                user.total_credits_purchased += amount
            
            # Record transaction before committing
            self._record_credit_transaction(user_id, amount, source, metadata)
            
            # Commit the changes
            db.session.commit()
            
            # Refresh and verify the changes
            db.session.refresh(user)
            balance_after = user.credits_balance
            purchased_after = user.total_credits_purchased
            
            self.logger.info(f"After: Balance={balance_after}, Total purchased={purchased_after}")
            
            # Verify the changes
            if balance_after == balance_before + amount:
                self.logger.info(f"✅ Credit addition verified for user {user_id}: {balance_before} + {amount} = {balance_after}")
                
                if source == 'purchase' and purchased_after == purchased_before + amount:
                    self.logger.info(f"✅ Purchase tracking verified: {purchased_before} + {amount} = {purchased_after}")
                elif source != 'purchase':
                    self.logger.info(f"✅ Non-purchase credit addition completed")
                    
                return True
            else:
                self.logger.error(f"❌ Credit addition verification failed for user {user_id}: Expected {balance_before + amount}, got {balance_after}")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Error adding credits to user {user_id}: {str(e)}")
            db.session.rollback()
            return False
    
    def get_user_credit_status(self, user_id: int) -> Dict:
        """Get comprehensive credit status for user"""
        try:
            user = User.query.get(user_id)
            if not user:
                return {}
            
            # Reset daily/monthly credits if needed
            self._check_and_reset_credits(user)
            
            # Determine user plan
            if user.is_premium and user.subscription_status == 'active':
                plan_key = 'elite'
            else:
                plan_key = 'free'
            
            plan_info = self.SUBSCRIPTION_PLANS[plan_key]
            available_credits = self._get_available_credits(user)
            
            return {
                'credits_balance': user.credits_balance,
                'available_credits': available_credits,
                'subscription_plan': plan_key,
                'plan_info': plan_info,
                'daily_free_credits_claimed': user.daily_free_credits_claimed,
                'is_elite': user.is_premium and user.subscription_status == 'active',
                'can_purchase_credits': plan_info['can_purchase_credits'],
                'total_credits_purchased': user.total_credits_purchased,
                'credits_used_today': user.credits_used_today,
                'credits_used_this_month': user.credits_used_this_month,
                'credit_packages': self.CREDIT_PACKAGES if plan_info['can_purchase_credits'] else {},
                'credit_costs': self.CREDIT_COSTS,
                'estimated_daily_cost': self._estimate_daily_cost(user),
                'days_until_monthly_refill': self._days_until_monthly_refill(),
                'monthly_allowance_used': self._get_monthly_allowance_used(user),
                'cost_breakdown': self._get_usage_cost_breakdown(user)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting credit status: {str(e)}")
            return {}
    
    def claim_daily_credits(self, user_id: int) -> Tuple[bool, str, int]:
        """Claim daily free credits (only for free users)"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found", 0
            
            # Only free users get daily credits
            if user.is_premium and user.subscription_status == 'active':
                return False, "Elite users receive monthly credit allowance instead of daily credits", 0
            
            if user.daily_free_credits_claimed:
                return False, "Daily credits already claimed", 0
            
            plan_info = self.SUBSCRIPTION_PLANS['free']
            daily_credits = plan_info['daily_free_credits']
            
            user.credits_balance += daily_credits
            user.daily_free_credits_claimed = True
            
            self._record_credit_transaction(user_id, daily_credits, 'daily_free', {'plan': 'free'})
            
            db.session.commit()
            
            return True, f"Claimed {daily_credits} daily credits", daily_credits
            
        except Exception as e:
            self.logger.error(f"Error claiming daily credits: {str(e)}")
            return False, "Error claiming credits", 0
    
    def refill_monthly_credits(self, user_id: int) -> Tuple[bool, str, int]:
        """Refill monthly credit allowance for Elite users"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found", 0
            
            # Only Elite users get monthly allowance
            if not (user.is_premium and user.subscription_status == 'active'):
                return False, "Only Elite users receive monthly credit allowance", 0
            
            plan_info = self.SUBSCRIPTION_PLANS['elite']
            monthly_allowance = plan_info['monthly_credit_allowance']
            
            # Add monthly allowance to balance
            user.credits_balance += monthly_allowance
            
            # Reset monthly usage tracking
            user.credits_used_this_month = 0
            
            self._record_credit_transaction(user_id, monthly_allowance, 'monthly_allowance', {'plan': 'elite'})
            
            db.session.commit()
            
            return True, f"Monthly allowance of {monthly_allowance} credits added", monthly_allowance
            
        except Exception as e:
            self.logger.error(f"Error refilling monthly credits: {str(e)}")
            return False, "Error refilling credits", 0
    
    def _get_available_credits(self, user: User) -> int:
        """Get total available credits including unclaimed daily credits"""
        base_credits = user.credits_balance
        
        # Add unclaimed daily credits for free users only
        if not (user.is_premium and user.subscription_status == 'active'):
            if not user.daily_free_credits_claimed:
                plan_info = self.SUBSCRIPTION_PLANS['free']
                base_credits += plan_info['daily_free_credits']
        
        return base_credits
    
    def _calculate_dynamic_cost(self, action: str, base_cost: int, metadata: Dict = None) -> int:
        """Calculate dynamic cost based on complexity and usage"""
        if not metadata:
            return base_cost
        
        complexity_multiplier = 1.0
        
        if action == 'chat_message_advanced':
            if metadata.get('context_length', 0) > 5001:
                complexity_multiplier = 1.5
            if metadata.get('document_context', False):
                complexity_multiplier *= 1.3
        
        elif action == 'document_upload':
            file_size_mb = metadata.get('file_size_mb', 1)
            if file_size_mb > 10:
                complexity_multiplier = 2.0
            elif file_size_mb > 5:
                complexity_multiplier = 1.5
        
        elif action == 'health_assessment':
            if metadata.get('comprehensive', False):
                complexity_multiplier = 1.8
        
        return int(base_cost * complexity_multiplier)
    
    def _deduct_credits(self, user: User, amount: int, action: str, metadata: Dict = None):
        """Deduct credits from user account"""
        # For free users, try to use daily free credits first
        if not (user.is_premium and user.subscription_status == 'active'):
            if not user.daily_free_credits_claimed:
                plan_info = self.SUBSCRIPTION_PLANS['free']
                daily_credits = plan_info['daily_free_credits']
                
                if amount <= daily_credits:
                    user.daily_free_credits_claimed = True
                    remaining_daily = daily_credits - amount
                    user.credits_balance += remaining_daily
                else:
                    user.daily_free_credits_claimed = True
                    user.credits_balance -= (amount - daily_credits)
            else:
                user.credits_balance -= amount
        else:
            # Elite users use their balance directly
            user.credits_balance -= amount
        
        # Update usage counters
        today = datetime.now().date()
        if user.last_credit_reset_date != today:
            user.credits_used_today = 0
            user.last_credit_reset_date = today
        
        user.credits_used_today += amount
        user.credits_used_this_month += amount
        
        # Record transaction
        self._record_credit_transaction(user.id, -amount, 'usage', {
            'action': action,
            'metadata': metadata
        })
        
        db.session.commit()
    
    def _check_and_reset_credits(self, user: User):
        """Reset daily credits and handle monthly refills"""
        today = datetime.now().date()
        
        # Reset daily credits for free users
        if user.last_credit_reset_date != today:
            if not (user.is_premium and user.subscription_status == 'active'):
                user.daily_free_credits_claimed = False
            user.credits_used_today = 0
            user.last_credit_reset_date = today
            db.session.commit()
        
        # Check for monthly refill for Elite users
        if user.is_premium and user.subscription_status == 'active':
            # Check if it's time for monthly refill (rough implementation)
            if user.subscription_start_date:
                days_since_start = (today - user.subscription_start_date.date()).days
                if days_since_start > 0 and days_since_start % 30 == 0:
                    # Time for monthly refill
                    self.refill_monthly_credits(user.id)
    
    def _record_credit_transaction(self, user_id: int, amount: int, transaction_type: str, metadata: Dict = None):
        """Record credit transaction for analytics"""
        self.logger.info(f"Credit transaction - User: {user_id}, Amount: {amount}, Type: {transaction_type}, Metadata: {metadata}")
    
    def _estimate_daily_cost(self, user: User) -> float:
        """Estimate user's daily cost based on usage patterns"""
        return user.credits_used_today / 100.0
    
    def _days_until_monthly_refill(self) -> int:
        """Calculate days until next monthly refill"""
        today = datetime.now().date()
        next_month = today.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)
        return (next_month - today).days
    
    def _get_monthly_allowance_used(self, user: User) -> float:
        """Get percentage of monthly allowance used"""
        if not (user.is_premium and user.subscription_status == 'active'):
            return 0
        
        plan_info = self.SUBSCRIPTION_PLANS['elite']
        monthly_allowance = plan_info['monthly_credit_allowance']
        
        if monthly_allowance == 0:
            return 0
        
        return min(100, (user.credits_used_this_month / monthly_allowance) * 100)
    
    def _get_usage_cost_breakdown(self, user: User) -> Dict:
        """Get breakdown of usage costs"""
        return {
            'chat_messages': user.credits_used_today * 0.4,
            'document_processing': user.credits_used_today * 0.3,
            'health_features': user.credits_used_today * 0.2,
            'other': user.credits_used_today * 0.1
        }
    
    def estimate_action_cost(self, action: str, metadata: Dict = None) -> Dict:
        """Estimate cost for an action before execution"""
        base_cost = self.CREDIT_COSTS.get(action, 3)
        total_cost = self._calculate_dynamic_cost(action, base_cost, metadata)
        
        return {
            'action': action,
            'base_cost_credits': base_cost,
            'total_cost_credits': total_cost,
            'cost_usd': total_cost / 100.0,
            'metadata': metadata
        } 
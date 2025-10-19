from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.credit_transaction import CreditTransaction
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
        'book_generation': 10,        # $0.10 - Book generation
        
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
            'daily_free_credits': 20,     # $0.20 worth of free credits daily (10 messages at 2 credits each)
            'monthly_credit_allowance': 0,
            'price': 0,
            'features': ['basic_chat', 'limited_uploads'],
            'can_purchase_credits': False  # Free users must upgrade to buy credits
        },
        'elite': {
            'name': 'Elite Pack',
            'daily_free_credits': 0,      # No daily free credits for Elite
            'monthly_credit_allowance': 3000,  # $30.00 worth of credits monthly
            'price': 19.95,
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
        """Add credits to user account with duplicate prevention"""
        try:
            user = User.query.get(user_id)
            if not user:
                self.logger.error(f"User {user_id} not found when adding credits")
                return False
            
            # Check for duplicate payments using payment identifiers
            if metadata:
                payment_intent_id = metadata.get('payment_intent_id')
                checkout_session_id = metadata.get('checkout_session_id')
                
                if payment_intent_id and CreditTransaction.is_payment_processed(payment_intent_id=payment_intent_id):
                    self.logger.warning(f"🔄 Payment already processed - Payment Intent: {payment_intent_id}")
                    return True  # Return True since the payment was already processed successfully
                
                if checkout_session_id and CreditTransaction.is_payment_processed(checkout_session_id=checkout_session_id):
                    self.logger.warning(f"🔄 Payment already processed - Checkout Session: {checkout_session_id}")
                    return True  # Return True since the payment was already processed successfully
            
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
            
            # Check if user has unclaimed daily credits
            unclaimed_daily_credits = 0
            if not (user.is_premium and user.subscription_status == 'active') and not user.daily_free_credits_claimed:
                unclaimed_daily_credits = plan_info['daily_free_credits']
            
            return {
                'credits_balance': user.credits_balance,
                'available_credits': available_credits,
                'unclaimed_daily_credits': unclaimed_daily_credits,
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
                'days_until_monthly_refill': self._days_until_monthly_refill(user_id=user_id),
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
            
            # Update last refill date to prevent multiple refills in the same month
            user.last_monthly_refill_date = datetime.now().date()
            
            self._record_credit_transaction(user_id, monthly_allowance, 'monthly_allowance', {'plan': 'elite'})
            
            db.session.commit()
            
            return True, f"Monthly allowance of {monthly_allowance} credits added", monthly_allowance
            
        except Exception as e:
            self.logger.error(f"Error refilling monthly credits: {str(e)}")
            return False, "Error refilling credits", 0
    
    def _get_available_credits(self, user: User) -> int:
        """Get actual available credits (no auto-inclusion of unclaimed daily credits)"""
        # Only return actual credits balance, not potential unclaimed credits
        # Users must manually claim daily credits to get them
        return user.credits_balance
    
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
        # All users (free and Elite) use their actual credits_balance
        # No automatic daily credit usage - users must manually claim daily credits first
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
        if user.is_premium and user.subscription_status == 'active' and user.subscription_start_date:
            # Get the subscription start day
            start_date = user.subscription_start_date.date()
            start_day = start_date.day
            
            # Check if today is the monthly anniversary of the subscription start date
            if today.day == start_day:
                # Debug logging for refill logic
                self.logger.info(f"🔍 Debug refill check for user {user.id}: today={today}, last_refill={user.last_monthly_refill_date}, start_day={start_day}, sub_start={start_date}")
                
                # Skip refill if subscription was created today (new subscribers should wait for first anniversary)
                if start_date == today:
                    self.logger.info(f"⏭️ Monthly refill skipped for user {user.id} - subscription created today, waiting for first anniversary")
                    return
                
                # More robust check: prevent multiple refills on the same day
                if user.last_monthly_refill_date is None or user.last_monthly_refill_date != today:
                    self.logger.info(f"🎯 Proceeding with refill for user {user.id}: condition met (last_refill={user.last_monthly_refill_date} != today={today})")
                    # Time for monthly refill - only if we haven't refilled today
                    success, message, amount = self.refill_monthly_credits(user.id)
                    if success:
                        self.logger.info(f"✅ Monthly refill successful for user {user.id}: {amount} credits added on anniversary day {start_day}")
                    else:
                        self.logger.error(f"❌ Monthly refill failed for user {user.id}: {message}")
                else:
                    self.logger.info(f"⏭️ Monthly refill skipped for user {user.id} - already refilled today (last refill: {user.last_monthly_refill_date})")
            
            # Handle edge case for months with fewer days than the subscription start day
            elif today.day == self._get_last_day_of_month(today) and start_day > today.day:
                # It's the last day of the month and the subscription start day doesn't exist this month
                
                # Skip refill if subscription was created today (new subscribers should wait for first anniversary)
                if start_date == today:
                    self.logger.info(f"⏭️ Monthly refill skipped for user {user.id} - subscription created today, waiting for first anniversary (edge case)")
                    return
                
                # More robust check: prevent multiple refills on the same day
                if user.last_monthly_refill_date is None or user.last_monthly_refill_date != today:
                    # Time for monthly refill - only if we haven't refilled today
                    success, message, amount = self.refill_monthly_credits(user.id)
                    if success:
                        self.logger.info(f"✅ Monthly refill successful for user {user.id}: {amount} credits added on last day of month (subscription day {start_day} doesn't exist this month)")
                    else:
                        self.logger.error(f"❌ Monthly refill failed for user {user.id}: {message}")
                else:
                    self.logger.info(f"⏭️ Monthly refill skipped for user {user.id} - already refilled today (last refill: {user.last_monthly_refill_date})")

    def _get_last_day_of_month(self, date):
        """Get the last day of the month for a given date"""
        if date.month == 12:
            next_month = date.replace(year=date.year + 1, month=1, day=1)
        else:
            next_month = date.replace(month=date.month + 1, day=1)
        
        return (next_month - timedelta(days=1)).day
    
    def _record_credit_transaction(self, user_id: int, amount: int, transaction_type: str, metadata: Dict = None):
        """Record credit transaction for analytics and duplicate prevention"""
        try:
            # Extract payment identifiers for duplicate prevention
            payment_intent_id = metadata.get('payment_intent_id') if metadata else None
            checkout_session_id = metadata.get('checkout_session_id') if metadata else None
            
            # Create transaction record - using the constructor parameter names
            transaction = CreditTransaction(
                user_id=user_id,
                amount=amount,
                transaction_type=transaction_type,
                payment_intent_id=payment_intent_id,
                checkout_session_id=checkout_session_id,
                metadata=metadata  # This gets converted to transaction_metadata in the constructor
            )
            
            db.session.add(transaction)
            db.session.flush()  # Ensure transaction gets an ID
            self.logger.info(f"✅ Credit transaction created - ID: {transaction.id}, User: {user_id}, Amount: {amount}, Type: {transaction_type}, Action: {metadata.get('action', 'N/A') if metadata else 'N/A'}")
            
        except Exception as e:
            self.logger.error(f"❌ Error recording credit transaction: {str(e)}")
            self.logger.error(f"❌ Transaction details - User: {user_id}, Amount: {amount}, Type: {transaction_type}, Metadata: {metadata}")
            # Don't raise exception - transaction recording shouldn't break the main flow
    
    def _estimate_daily_cost(self, user: User) -> float:
        """Estimate user's daily cost based on usage patterns"""
        return user.credits_used_today / 100.0
    
    def _days_until_monthly_refill(self, user_id=None) -> int:
        """Calculate days until next monthly refill based on subscription start date"""
        today = datetime.now().date()
        
        # If user_id is provided, calculate based on their subscription start date
        if user_id:
            user = User.query.get(user_id)
            if user and user.is_premium and user.subscription_status == 'active':
                # Handle new elite users who don't have a subscription_start_date yet
                if not user.subscription_start_date:
                    # For new elite users, assume subscription started today, next refill in 30 days
                    return 30
                # Get the subscription start day
                start_date = user.subscription_start_date.date()
                start_day = start_date.day
                
                # Calculate the next refill date (same day of the month)
                current_year = today.year
                current_month = today.month
                
                # Try to create a date for the same day this month
                try:
                    this_month_refill = today.replace(day=start_day)
                except ValueError:
                    # Handle months with fewer days (e.g., subscription started on 31st)
                    # Use the last day of the month instead
                    if current_month == 2:  # February
                        this_month_refill = today.replace(day=28 if current_year % 4 != 0 else 29)
                    elif current_month in [4, 6, 9, 11]:  # 30-day months
                        this_month_refill = today.replace(day=30)
                    else:
                        this_month_refill = today.replace(day=31)
                
                # If today is on or past the refill date for this month, move to next month
                if today >= this_month_refill:
                    next_month = current_month + 1 if current_month < 12 else 1
                    next_year = current_year if current_month < 12 else current_year + 1
                    
                    try:
                        next_refill = today.replace(year=next_year, month=next_month, day=start_day)
                    except ValueError:
                        # Handle months with fewer days
                        if next_month == 2:  # February
                            next_refill = today.replace(year=next_year, month=next_month, 
                                                        day=28 if next_year % 4 != 0 else 29)
                        elif next_month in [4, 6, 9, 11]:  # 30-day months
                            next_refill = today.replace(year=next_year, month=next_month, day=30)
                        else:
                            next_refill = today.replace(year=next_year, month=next_month, day=31)
                else:
                    next_refill = this_month_refill
                
                self.logger.info(f"Next refill date for user {user_id}: {next_refill} (based on subscription start: {start_date})")
                return (next_refill - today).days
        
        # Default calculation (first day of next month) if no user_id or no subscription data
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
        """Get breakdown of actual usage costs by feature type"""
        try:
            from datetime import datetime, timezone
            
            # Get today's date for filtering transactions
            today = datetime.now(timezone.utc).date()
            
            # Get today's credit transactions for usage tracking
            today_transactions = CreditTransaction.query.filter(
                CreditTransaction.user_id == user.id,
                CreditTransaction.transaction_type == 'usage',
                CreditTransaction.created_at >= datetime.combine(today, datetime.min.time().replace(tzinfo=timezone.utc))
            ).all()
            
            # Initialize breakdown with zeros
            breakdown = {
                'chat_messages': 0,
                'document_processing': 0, 
                'health_features': 0,
                'book_generation': 0,
                'voice_processing': 0
            }
            
            # Aggregate credits spent by action type
            for transaction in today_transactions:
                metadata = transaction.get_metadata()
                if metadata and 'action' in metadata:
                    action = metadata['action']
                    credits_spent = abs(transaction.amount)  # Amount is negative for usage
                    
                    # Map actions to breakdown categories
                    if action in ['chat_message_basic', 'chat_message_advanced', 'chat']:
                        breakdown['chat_messages'] += credits_spent
                    elif action in ['document_upload', 'document_analysis', 'document']:
                        breakdown['document_processing'] += credits_spent
                    elif action in ['health_assessment', 'chat_message_health', 'health']:
                        breakdown['health_features'] += credits_spent
                    elif action in ['book_generation']:
                        breakdown['book_generation'] += credits_spent
                    elif action in ['voice_message']:
                        breakdown['voice_processing'] += credits_spent
                    # Note: Unrecognized actions are ignored (no 'other' category)
            
            # Check if there's a significant mismatch between calculated total and user.credits_used_today
            calculated_total = sum(breakdown.values())
            if calculated_total != user.credits_used_today and user.credits_used_today > 0:
                # Log the mismatch but don't add to 'other' - we're removing that category
                untracked_usage = user.credits_used_today - calculated_total
                if untracked_usage > 0:
                    self.logger.warning(f"Credit usage mismatch detected for user {user.id}: calculated={calculated_total}, actual={user.credits_used_today}, difference={untracked_usage}")
            
            return breakdown
            
        except Exception as e:
            self.logger.error(f"Error calculating usage breakdown: {str(e)}")
            # Return zeros if error occurs
            return {
                'chat_messages': 0,
                'document_processing': 0,
                'health_features': 0,
                'book_generation': 0,
                'voice_processing': 0
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
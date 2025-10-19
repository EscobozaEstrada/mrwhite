"""
Async Authentication Service for FastAPI Chat Service
Handles user authentication, JWT tokens, and user management
"""

import os
import jwt
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import AsyncSessionLocal, User

logger = logging.getLogger(__name__)

class AsyncAuthService:
    """
    Async authentication service
    Handles JWT tokens, user authentication, and user management
    """
    
    def __init__(self):
        self.jwt_secret = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET or SECRET_KEY environment variable is required")
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # ==================== JWT TOKEN MANAGEMENT ====================
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT access token for user"""
        try:
            # Token payload
            payload = {
                "id": user_data["id"],
                "email": user_data["email"],
                "username": user_data.get("username"),
                "is_premium": user_data.get("is_premium", False),
                "credits_balance": user_data.get("credits_balance", 0),
                "subscription_tier": user_data.get("subscription_tier", "free"),
                "exp": datetime.now(timezone.utc) + timedelta(hours=self.jwt_expiration_hours),
                "iat": datetime.now(timezone.utc)
            }
            
            # Encode token
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            
            logger.info(f"✅ Created access token for user {user_data['id']}")
            return token
            
        except Exception as e:
            logger.error(f"❌ Token creation error: {str(e)}")
            raise e
    
    def verify_access_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Verify JWT access token"""
        try:
            # Decode token
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm]
            )
            
            # Check expiration
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                if exp_datetime < datetime.now(timezone.utc):
                    return False, None, "Token has expired"
            
            return True, payload, None
            
        except jwt.ExpiredSignatureError:
            return False, None, "Token has expired"
        except jwt.InvalidTokenError as e:
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            logger.error(f"❌ Token verification error: {str(e)}")
            return False, None, f"Token verification failed: {str(e)}"
    
    def refresh_access_token(self, token: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Refresh access token if valid"""
        try:
            # Verify current token
            is_valid, payload, error = self.verify_access_token(token)
            
            if not is_valid:
                return False, None, error
            
            # Create new token with same data
            new_token = self.create_access_token(payload)
            
            return True, new_token, None
            
        except Exception as e:
            logger.error(f"❌ Token refresh error: {str(e)}")
            return False, None, str(e)
    
    # ==================== USER AUTHENTICATION ====================
    
    async def authenticate_user(
        self, 
        email: str, 
        password: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Authenticate user with email and password"""
        try:
            async with AsyncSessionLocal() as session:
                # Get user by email
                query = select(User).where(User.email == email)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
                
                if not user:
                    return False, None, "User not found"
                
                # Verify password
                if not self._verify_password(password, user.password_hash):
                    return False, None, "Invalid password"
                
                # Return user data
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "is_premium": user.is_premium,
                    "credits_balance": user.credits_balance,
                    "subscription_tier": user.subscription_tier,
                    "created_at": user.created_at.isoformat()
                }
                
                logger.info(f"✅ User {email} authenticated successfully")
                return True, user_data, None
                
        except Exception as e:
            logger.error(f"❌ Authentication error: {str(e)}")
            return False, None, str(e)
    
    async def get_user_by_id(self, user_id: int) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Get user data by ID"""
        try:
            async with AsyncSessionLocal() as session:
                query = select(User).where(User.id == user_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
                
                if not user:
                    return False, None, "User not found"
                
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "is_premium": user.is_premium,
                    "credits_balance": user.credits_balance,
                    "credits_used_today": user.credits_used_today,
                    "credits_used_this_month": user.credits_used_this_month,
                    "subscription_tier": user.subscription_tier,
                    "timezone": user.timezone,
                    "location_city": user.location_city,
                    "location_country": user.location_country,
                    "created_at": user.created_at.isoformat()
                }
                
                return True, user_data, None
                
        except Exception as e:
            logger.error(f"❌ Get user error: {str(e)}")
            return False, None, str(e)
    
    async def get_user_from_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Get fresh user data from token (validates against database)"""
        try:
            # Verify token
            is_valid, payload, error = self.verify_access_token(token)
            if not is_valid:
                return False, None, error
            
            # Get fresh user data from database
            user_id = payload.get("id")
            if not user_id:
                return False, None, "Invalid token payload"
            
            return await self.get_user_by_id(user_id)
            
        except Exception as e:
            logger.error(f"❌ Get user from token error: {str(e)}")
            return False, None, str(e)
    
    # ==================== USER MANAGEMENT ====================
    
    async def create_user(
        self,
        email: str,
        password: str,
        username: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Create new user account"""
        try:
            async with AsyncSessionLocal() as session:
                # Check if user already exists
                existing_query = select(User).where(User.email == email)
                existing_result = await session.execute(existing_query)
                existing_user = existing_result.scalar_one_or_none()
                
                if existing_user:
                    return False, None, "User already exists with this email"
                
                # Hash password
                password_hash = self._hash_password(password)
                
                # Create user
                from datetime import datetime, timezone
                new_user = User(
                    email=email,
                    username=username,
                    password_hash=password_hash,
                    is_premium=False,
                    credits_balance=0,  # No initial credits - they claim daily credits
                    subscription_tier="free",
                    credits_used_today=0,  # Explicitly initialize
                    last_credit_reset_date=datetime.now(timezone.utc).date()  # Initialize reset date
                )
                
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                
                user_data = {
                    "id": new_user.id,
                    "email": new_user.email,
                    "username": new_user.username,
                    "is_premium": new_user.is_premium,
                    "credits_balance": new_user.credits_balance,
                    "subscription_tier": new_user.subscription_tier,
                    "created_at": new_user.created_at.isoformat()
                }
                
                logger.info(f"✅ Created new user: {email}")
                return True, user_data, None
                
        except Exception as e:
            logger.error(f"❌ Create user error: {str(e)}")
            return False, None, str(e)
    
    async def update_user_credits(
        self,
        user_id: int,
        credits_change: int,
        operation_type: str = "deduct"
    ) -> Tuple[bool, Optional[str]]:
        """Update user credits"""
        try:
            async with AsyncSessionLocal() as session:
                # Get user
                query = select(User).where(User.id == user_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
                
                if not user:
                    return False, "User not found"
                
                # Update credits
                if operation_type == "deduct":
                    user.credits_balance = max(0, user.credits_balance - credits_change)
                    user.credits_used_today += credits_change
                    user.credits_used_this_month += credits_change
                elif operation_type == "add":
                    user.credits_balance += credits_change
                
                await session.commit()
                
                logger.info(f"✅ Updated credits for user {user_id}: {operation_type} {credits_change}")
                return True, None
                
        except Exception as e:
            logger.error(f"❌ Update credits error: {str(e)}")
            return False, str(e)
    
    async def update_user_subscription(
        self,
        user_id: int,
        subscription_tier: str,
        is_premium: bool
    ) -> Tuple[bool, Optional[str]]:
        """Update user subscription"""
        try:
            async with AsyncSessionLocal() as session:
                # Get user
                query = select(User).where(User.id == user_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
                
                if not user:
                    return False, "User not found"
                
                # Update subscription
                user.subscription_tier = subscription_tier
                user.is_premium = is_premium
                
                # Note: Credits are handled by the payment webhook, not here
                
                await session.commit()
                
                logger.info(f"✅ Updated subscription for user {user_id}: {subscription_tier}")
                return True, None
                
        except Exception as e:
            logger.error(f"❌ Update subscription error: {str(e)}")
            return False, str(e)
    
    # ==================== PASSWORD UTILITIES ====================
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        try:
            # Generate salt and hash password
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
            return password_hash.decode('utf-8')
            
        except Exception as e:
            logger.error(f"❌ Password hashing error: {str(e)}")
            raise e
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'), 
                password_hash.encode('utf-8')
            )
            
        except Exception as e:
            logger.error(f"❌ Password verification error: {str(e)}")
            return False
    
    # ==================== USER VALIDATION ====================
    
    def validate_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """Validate email format"""
        import re
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not email or not re.match(email_pattern, email):
            return False, "Invalid email format"
        
        if len(email) > 100:
            return False, "Email too long"
        
        return True, None
    
    def validate_password(self, password: str) -> Tuple[bool, Optional[str]]:
        """Validate password strength"""
        if not password:
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        
        if len(password) > 128:
            return False, "Password too long"
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not (has_letter and has_number):
            return False, "Password must contain at least one letter and one number"
        
        return True, None
    
    def validate_username(self, username: str) -> Tuple[bool, Optional[str]]:
        """Validate username"""
        if not username:
            return False, "Username is required"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        if len(username) > 50:
            return False, "Username too long"
        
        # Check for valid characters (alphanumeric and underscore)
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        return True, None
    
    # ==================== USAGE STATISTICS ====================
    
    async def get_user_usage_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user usage statistics"""
        try:
            async with AsyncSessionLocal() as session:
                query = select(User).where(User.id == user_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
                
                if not user:
                    return {"error": "User not found"}
                
                # Calculate remaining credits and limits
                daily_limit = 50 if user.subscription_tier == "free" else 1000
                monthly_limit = 1000 if user.subscription_tier == "free" else 10000
                
                remaining_today = max(0, daily_limit - user.credits_used_today)
                remaining_month = max(0, monthly_limit - user.credits_used_this_month)
                
                return {
                    "credits_balance": user.credits_balance,
                    "credits_used_today": user.credits_used_today,
                    "credits_used_this_month": user.credits_used_this_month,
                    "remaining": {
                        "credits": user.credits_balance,
                        "daily": remaining_today,
                        "monthly": remaining_month
                    },
                    "limits": {
                        "daily": daily_limit,
                        "monthly": monthly_limit
                    },
                    "subscription_tier": user.subscription_tier,
                    "is_premium": user.is_premium
                }
                
        except Exception as e:
            logger.error(f"❌ Get usage stats error: {str(e)}")
            return {"error": str(e)} 
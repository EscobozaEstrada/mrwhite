"""
Async Middleware for FastAPI Chat Service
Handles authentication, authorization, credits, and usage tracking
"""

import os
import jwt
import time
import logging
import aiohttp
from typing import Dict, Any, Optional, Callable, Tuple
from datetime import datetime, timezone

from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, CreditTransaction, AsyncSessionLocal

logger = logging.getLogger(__name__)

# JWT Configuration (matching Flask config)
JWT_SECRET = os.getenv("SECRET_KEY")
if not JWT_SECRET:
    raise ValueError("SECRET_KEY environment variable is required for JWT authentication")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Security scheme (optional to support both Bearer and Cookie auth)
security = HTTPBearer(auto_error=False)

# ==================== AUTHENTICATION MIDDLEWARE ====================

async def get_current_user_from_token(token: str) -> Dict[str, Any]:
    """Decode JWT token and get user data"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("id")
        email = payload.get("email")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        return {
            "id": user_id,
            "email": email,
            "username": payload.get("username"),
            "is_premium": payload.get("is_premium", False),
            "credits_balance": payload.get("credits_balance", 0),
            "subscription_tier": payload.get("subscription_tier", "free")
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def try_flask_auth_fallback(request: Request) -> Optional[Dict[str, Any]]:
    """
    Fallback authentication by checking Flask backend
    Used when cookie token is not available to FastAPI due to port differences
    """
    try:
        # Get Flask backend URL
        flask_base_url = os.getenv("FLASK_BASE_URL")
        
        # Forward the original request cookies to Flask auth endpoint
        cookies = dict(request.cookies)
        
        if not cookies:
            return None
            
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{flask_base_url}/api/auth/me",
                cookies=cookies,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    user_data = await response.json()
                    
                    # Convert Flask user data format to FastAPI format
                    if isinstance(user_data, dict) and "id" in user_data:
                        logger.info(f"✅ Flask auth fallback successful for user {user_data.get('id')}")
                        return {
                            "id": user_data["id"],
                            "email": user_data.get("email"),
                            "username": user_data.get("username"),
                            "is_premium": user_data.get("is_premium", False),
                            "credits_balance": user_data.get("credits_balance", 0),
                            "subscription_tier": user_data.get("subscription_tier", "free")
                        }
                else:
                    logger.debug(f"Flask auth fallback failed: {response.status}")
                    return None
                    
    except Exception as e:
        logger.debug(f"Flask auth fallback error: {str(e)}")
        return None

async def require_auth_async(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Async authentication dependency - supports both Bearer token and Cookie auth
    Replaces Flask @require_auth decorator
    """
    try:
        # Try to get token from Authorization header first, then cookies
        token = None
        if credentials:
            token = credentials.credentials
        else:
            # Check for token in cookies (Flask compatibility)
            token = request.cookies.get("token")
        
        # If no token found, try fallback authentication via Flask backend
        if not token:
            user_data = await try_flask_auth_fallback(request)
            if user_data:
                return user_data
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        user_data = await get_current_user_from_token(token)
        
        # Verify user exists in database and handle daily reset
        async with AsyncSessionLocal() as session:
            query = select(User).where(User.id == user_data["id"])
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            
            # Check for daily reset (CRITICAL FIX)
            today = datetime.now(timezone.utc).date()
            last_reset = user.last_credit_reset_date if hasattr(user, 'last_credit_reset_date') else None
            
            if last_reset != today:
                logger.info(f"🔄 Daily reset for user {user.id}: {last_reset} -> {today}")
                # Reset daily usage counter (backward compatibility)
                user.credits_used_today = 0
                user.last_credit_reset_date = today
                
                # Reset per-type daily usage in JSON (NEW: part of the fix!)
                usage_stats = user.lifetime_usage_stats or {}
                if 'daily_usage' not in usage_stats:
                    usage_stats['daily_usage'] = {}
                
                # Initialize today with all zeros (clean slate)
                today_iso = today.isoformat()
                usage_stats['daily_usage'][today_iso] = {
                    'chat': 0,
                    'document': 0,
                    'health': 0,
                    'voice_message': 0
                }
                user.lifetime_usage_stats = usage_stats
                
                await session.commit()
                logger.info(f"✅ Daily reset completed for user {user.id} (total + per-type usage reset)")
            
            # Update user data with fresh database info
            user_data.update({
                "is_premium": user.is_premium,
                "credits_balance": user.credits_balance,
                "credits_used_today": user.credits_used_today,
                "credits_used_this_month": user.credits_used_this_month,
                "subscription_tier": user.subscription_tier
            })
        
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# ==================== AUTHORIZATION MIDDLEWARE ====================

async def require_premium_async(
    current_user: Dict[str, Any] = Depends(require_auth_async)
) -> Dict[str, Any]:
    """
    Async premium requirement dependency
    Replaces Flask @premium_required decorator
    """
    if not current_user.get("is_premium", False):
        raise HTTPException(
            status_code=403, 
            detail="Premium subscription required for this feature"
        )
    
    return current_user

# ==================== CREDITS MIDDLEWARE ====================

CREDIT_COSTS = {
    "chat": 2,                    # $0.02 - Basic chat response (was 1, now 2)
    "document": 4,                # $0.08 - Document processing (was 3, now 8)
    "health": 8,                  # $0.08 - Health analysis (was 2, now 8)
    "book_generation": 10,        # $0.10 - Book generation
    "premium_feature": 5,         # $0.05 - Premium features
    "enhanced_chat": 8,           # $0.08 - Enhanced chat with memory
    "voice_message": 3,           # $0.03 - Voice processing
    "health_assessment": 15,      # $0.15 - Comprehensive health assessment
    "care_record_ai": 6,          # $0.06 - AI-powered care record analysis
    "care_archive_search": 4,     # $0.04 - Search through care archive
    "health_insights": 20,        # $0.20 - AI health insights generation
    "care_summary": 15            # $0.15 - Comprehensive care summary
}

DAILY_LIMITS = {
    "free": {
        "chat": 50,
        "health": 0,  # Free users cannot use health mode - Elite only feature
        "document": 5,
        "voice_message": 0,  # Free users cannot use voice messages - Elite only feature
        "book_generation": 2
    },
    "elite": {
        "chat": 1000,
        "health": 500,
        "document": 200,
        "voice_message": 100,
        "book_generation": 10
    }
}

def require_credits_async(credit_type: str):
    """
    Factory function for credit requirement dependencies
    Replaces Flask @require_chat_credits, @require_health_credits decorators
    """
    async def _require_credits(
        current_user: Dict[str, Any] = Depends(require_auth_async)
    ):
        return await _check_credits_dependency(current_user, credit_type)
    
    return Depends(_require_credits)

async def _check_credits_dependency(
    current_user: Dict[str, Any], 
    credit_type: str
) -> Dict[str, Any]:
    """Check if user has sufficient credits for the operation"""
    user_id = current_user["id"]
    subscription_tier = current_user.get("subscription_tier", "free")
    credits_balance = current_user.get("credits_balance")
    credits_used_today = current_user.get("credits_used_today")
    
    # Get credit cost and daily limit
    credit_cost = CREDIT_COSTS.get(credit_type)
    daily_limit = DAILY_LIMITS.get(subscription_tier, DAILY_LIMITS["free"])
    type_daily_limit = daily_limit.get(credit_type)
    
    # Check daily usage limit
    if credits_used_today >= type_daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily {credit_type} limit exceeded. Upgrade to premium for higher limits."
        )
    
    # Check credit balance for all users (free and elite)
    if credits_balance < credit_cost:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {credit_cost} credits for {credit_type}. Claim your daily free credits to continue or upgrade to premium for more credits."
        )
    
    # Deduct credits asynchronously
    try:
        await deduct_credits_async(user_id, credit_type, credit_cost)
    except Exception as e:
        logger.error(f"Credit deduction failed for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Credit processing failed"
        )
    
    return current_user

async def update_daily_usage_by_type(user, credit_type: str, amount: int):
    """Update daily usage tracking by credit type in JSON field"""
    import json
    from datetime import datetime, timezone
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    # Get existing usage stats
    usage_stats = user.lifetime_usage_stats or {}
    if 'daily_usage' not in usage_stats:
        usage_stats['daily_usage'] = {}
    
    # Initialize today's usage if not exists
    if today not in usage_stats['daily_usage']:
        usage_stats['daily_usage'][today] = {
            'chat': 0,
            'document': 0,
            'health': 0,
            'voice_message': 0
        }
    
    # Update specific credit type usage
    if credit_type in usage_stats['daily_usage'][today]:
        usage_stats['daily_usage'][today][credit_type] += amount
    else:
        usage_stats['daily_usage'][today][credit_type] = amount
    
    # Clean up old daily usage data (keep only last 7 days for performance)
    if len(usage_stats['daily_usage']) > 7:
        sorted_dates = sorted(usage_stats['daily_usage'].keys(), reverse=True)
        for old_date in sorted_dates[7:]:
            del usage_stats['daily_usage'][old_date]
    
    # Update user's lifetime_usage_stats
    user.lifetime_usage_stats = usage_stats
    
    logger.info(f"📊 Updated daily usage for user {user.id}: {credit_type} +{amount} (today: {usage_stats['daily_usage'][today]})")

async def get_daily_usage_by_type(user, credit_type: str) -> int:
    """Get daily usage for a specific credit type from JSON field"""
    from datetime import datetime, timezone
    
    today = datetime.now(timezone.utc).date().isoformat()
    usage_stats = user.lifetime_usage_stats or {}
    
    if 'daily_usage' not in usage_stats:
        return 0
    
    if today not in usage_stats['daily_usage']:
        return 0
        
    return usage_stats['daily_usage'][today].get(credit_type, 0)

async def deduct_credits_async(user_id: int, credit_type: str, amount: int):
    """Deduct credits from user account asynchronously with per-type tracking"""
    async with AsyncSessionLocal() as session:
        try:
            # Get current user data
            query = select(User).where(User.id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValueError("User not found")
            
            # Update credits - deduct from balance for all users
            user.credits_balance = max(0, (user.credits_balance or 0) - amount)
            
            # Update total daily usage (for backward compatibility)
            user.credits_used_today = (user.credits_used_today or 0) + amount
            
            # Update per-type daily usage (NEW: the fix for the bug!)
            await update_daily_usage_by_type(user, credit_type, amount)
            
            # Update monthly usage
            user.credits_used_this_month += amount
            
            # Create transaction record for usage tracking
            transaction = CreditTransaction(
                user_id=user_id,
                amount=-amount,  # Negative for usage deduction
                transaction_type='usage',
                transaction_metadata={'action': credit_type}
            )
            session.add(transaction)
            
            await session.commit()
            
            logger.info(f"Credits deducted: user={user_id}, type={credit_type}, amount={amount}, transaction_id={transaction.id}")
            
        except Exception as e:
            await session.rollback()
            raise e

# ==================== DYNAMIC CREDITS MIDDLEWARE ====================

async def _analyze_request_for_credits(request: Request, user_subscription_tier: str = "free") -> Tuple[str, int]:
    """
    Analyze incoming request to determine appropriate credit type and cost
    Takes user subscription tier to ensure Elite-only features are properly gated
    """
    try:
        # Get request body
        body = {}
        if request.headers.get("content-type") == "application/json":
            body = await request.json()
        
        # Check for files (document/image processing)
        has_files = bool(body.get("files"))
        
        # Check for health mode ONLY when explicitly enabled by Elite users
        is_health_mode = False
        if user_subscription_tier == "elite":  # Only Elite users can use health mode
            # Only charge health credits when user explicitly enables health mode
            # Do NOT auto-detect based on keywords - user must toggle health mode ON
            context = body.get("context", "").lower()
            is_health_mode = (
                context == "health" or
                body.get("health_mode") == True
            )
        
        # Check for voice data (Elite feature)
        has_voice = False
        if user_subscription_tier == "elite" and has_files:  # Voice is Elite-only
            files = body.get("files", [])
            has_voice = any(
                file.get("content_type", "").startswith("audio/") 
                for file in files
            )
        
        # Determine credit type based on features (priority order matters)
        if has_voice:
            logger.info(f"🎙️ Voice message detected (Elite user) - charging voice_message credits")
            return "voice_message", CREDIT_COSTS["voice_message"]
        elif is_health_mode:
            logger.info(f"🏥 Health mode explicitly enabled (Elite user) - charging health credits")
            return "health", CREDIT_COSTS["health"]
        elif has_files:
            logger.info(f"📁 Files detected - charging document credits")
            return "document", CREDIT_COSTS["document"]
        else:
            logger.info(f"💬 Basic chat detected - charging chat credits")
            return "chat", CREDIT_COSTS["chat"]
            
    except Exception as e:
        logger.warning(f"Credit analysis failed, defaulting to chat: {e}")
        return "chat", CREDIT_COSTS["chat"]

def require_dynamic_credits_async():
    """
    Smart dependency that analyzes request content to determine appropriate credits
    """
    async def _dynamic_credit_analysis(
        request: Request,
        current_user: Dict[str, Any] = Depends(require_auth_async)
    ):
        # Get user subscription tier first
        subscription_tier = current_user.get("subscription_tier", "free")
        
        # Analyze request to determine credit type and cost
        credit_type, credit_cost = await _analyze_request_for_credits(request, subscription_tier)
        
        # Use existing credit deduction logic with per-type daily usage tracking
        user_id = current_user["id"]
        credits_balance = current_user.get("credits_balance")
        credits_used_today = current_user.get("credits_used_today")  # Total usage (for reference)
        
        # Get fresh user data to check per-type daily usage
        async with AsyncSessionLocal() as session:
            query = select(User).where(User.id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            
            # Get per-type daily usage (THE FIX!)
            type_used_today = await get_daily_usage_by_type(user, credit_type)
        
        # DEBUG: Log all values to understand the issue
        logger.info(f"🔍 DEBUG Credit Check - User: {user_id}, Tier: {subscription_tier}, Credit Type: {credit_type}")
        logger.info(f"🔍 DEBUG Current Values - Balance: {credits_balance}, Total Used Today: {credits_used_today}")
        logger.info(f"🔍 DEBUG Per-Type Usage - {credit_type.upper()} Used Today: {type_used_today}")
        
        # Get daily limit for this credit type
        daily_limit = DAILY_LIMITS.get(subscription_tier, DAILY_LIMITS["free"])
        type_daily_limit = daily_limit.get(credit_type)
        
        logger.info(f"🔍 DEBUG Limits - Daily Limit Config: {daily_limit}, Type Limit ({credit_type}): {type_daily_limit}")
        
        # Check daily usage limit using PER-TYPE usage (CRITICAL FIX!)
        if type_daily_limit and type_used_today >= type_daily_limit:
            logger.warning(f"🚫 User {user_id} exceeded daily {credit_type} limit: {type_used_today}/{type_daily_limit}")
            logger.warning(f"🚫 DEBUG - Per-type comparison: {type_used_today} >= {type_daily_limit} = {type_used_today >= type_daily_limit}")
            raise HTTPException(
                status_code=429,
                detail=f"Daily {credit_type} limit exceeded ({type_used_today}/{type_daily_limit}). Upgrade to premium for higher limits."
            )
        
        logger.info(f"✅ DEBUG Credit Check Passed - User {user_id} within {credit_type} limits ({type_used_today}/{type_daily_limit})")
        
        # Check credit balance for all users (free and elite)
        if credits_balance < credit_cost:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {credit_cost} credits for {credit_type}. Claim your daily free credits to continue or upgrade to premium for more credits."
            )
        
        # Deduct credits asynchronously
        try:
            await deduct_credits_async(user_id, credit_type, credit_cost)
            logger.info(f"✅ Dynamic credits deducted: {credit_cost} credits for {credit_type}")
        except Exception as e:
            logger.error(f"Credit deduction failed for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Credit processing failed"
            )
        
        return current_user
    
    return Depends(_dynamic_credit_analysis)

# ==================== USAGE TRACKING MIDDLEWARE ====================

async def usage_tracking_middleware(request: Request, call_next):
    """
    Async middleware for usage tracking and performance monitoring
    Replaces Flask usage tracking functionality
    """
    start_time = time.time()
    
    # Track request
    user_id = None
    endpoint = request.url.path
    method = request.method
    
    try:
        # Try to get user ID from token if present
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                user_data = await get_current_user_from_token(token)
                user_id = user_data.get("id")
            except:
                pass  # Ignore auth errors in middleware
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log usage (async background task would be better)
        await log_usage_async(
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            status_code=response.status_code,
            processing_time=processing_time
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Usage tracking error: {str(e)}")
        # Continue processing even if tracking fails
        response = await call_next(request)
        return response

async def log_usage_async(
    user_id: Optional[int],
    endpoint: str,
    method: str,
    status_code: int,
    processing_time: float
):
    """Log usage data asynchronously"""
    try:
        # In production, this would go to a dedicated analytics service
        # For now, just log to application logs
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "processing_time": processing_time
        }
        
        logger.info(f"Usage: {log_data}")
        
        # Could also store in Redis or dedicated analytics DB
        
    except Exception as e:
        logger.error(f"Usage logging failed: {str(e)}")

# ==================== RATE LIMITING MIDDLEWARE ====================

RATE_LIMITS = {
    "free": {
        "requests_per_minute": 30,
        "requests_per_hour": 500
    },
    "elite": {
        "requests_per_minute": 100,
        "requests_per_hour": 2000
    }
}

async def check_rate_limit_async(
    current_user: Dict[str, Any],
    redis_client,
    window: str = "minute"
) -> bool:
    """Check if user is within rate limits"""
    try:
        user_id = current_user["id"]
        subscription_tier = current_user.get("subscription_tier", "free")
        
        # Get rate limits for user tier
        limits = RATE_LIMITS.get(subscription_tier, RATE_LIMITS["free"])
        
        if window == "minute":
            limit = limits["requests_per_minute"]
            key = f"rate_limit:minute:{user_id}"
            ttl = 60
        else:  # hour
            limit = limits["requests_per_hour"]
            key = f"rate_limit:hour:{user_id}"
            ttl = 3600
        
        # Check current count
        current_count = await redis_client.get(key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)
        
        if current_count >= limit:
            return False
        
        # Increment counter
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        await pipe.execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Rate limiting service unavailable: {str(e)}")
        # Fail closed - reject requests when rate limiting is unavailable
        # This prevents DoS attacks when Redis is down
        raise HTTPException(
            status_code=503, 
            detail="Rate limiting service temporarily unavailable. Please try again later."
        )

# ==================== CONTENT VALIDATION MIDDLEWARE ====================

async def validate_json_content_async(request: Request):
    """
    Async JSON content validation
    Replaces Flask @validate_json_content decorator
    """
    try:
        if request.headers.get("content-type") == "application/json":
            body = await request.json()
            if not isinstance(body, dict):
                raise HTTPException(
                    status_code=400,
                    detail="Request body must be a valid JSON object"
                )
        return True
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request body"
        )
    except Exception as e:
        logger.error(f"JSON validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Request validation failed"
        )

# ==================== ERROR HANDLING HELPERS ====================

def create_error_response(
    status_code: int,
    message: str,
    error_code: Optional[str] = None
) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "success": False,
        "message": message,
        "error_code": error_code,
        "timestamp": datetime.now(timezone.utc).isoformat()
    } 
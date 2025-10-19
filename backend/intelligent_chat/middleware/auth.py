"""
Authentication Middleware for Intelligent Chat System
Handles JWT authentication and user verification
"""

import os
import jwt
import logging
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db

logger = logging.getLogger("middleware.auth")

# JWT Configuration
JWT_SECRET = os.getenv("SECRET_KEY")
if not JWT_SECRET:
    logger.warning("⚠️ SECRET_KEY not found, using default (INSECURE for production!)")
    JWT_SECRET = "dev-secret-key-change-in-production"
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Security scheme
security = HTTPBearer(auto_error=False)


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
        # Get Flask backend URL (default to port 5001)
        flask_base_url = os.getenv("FLASK_BASE_URL", "http://localhost:5001")
        
        # Forward the original request cookies to Flask auth endpoint
        cookies = dict(request.cookies)
        
        logger.info(f"🔍 Flask fallback - Cookies received: {list(cookies.keys())}")
        
        if not cookies:
            logger.info("🔍 Flask fallback - No cookies found")
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

async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Authentication dependency - extracts user from JWT token
    Use this on all protected routes
    """
    try:
        # Try to get token from Authorization header first, then cookies
        token = None
        if credentials:
            token = credentials.credentials
            logger.info(f"🔑 Token from Authorization header: {token[:20]}...")
        else:
            # Check for token in cookies (for browser-based auth)
            token = request.cookies.get("token")
            if token:
                logger.info(f"🔑 Token from cookie: {token[:20]}...")
            else:
                logger.info(f"🔍 No token in Authorization or cookies. Cookies present: {list(request.cookies.keys())}")
        
        # If no token found, try fallback authentication via Flask backend
        if not token:
            logger.info("🔄 Attempting Flask auth fallback...")
            user_data = await try_flask_auth_fallback(request)
            if user_data:
                return user_data
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        user_data = await get_current_user_from_token(token)
        
        # Verify user exists in database
        result = await db.execute(
            text("SELECT id, email, username, is_premium, credits_balance, subscription_tier FROM users WHERE id = :user_id"),
            {"user_id": user_data["id"]}
        )
        user_row = result.fetchone()
        
        if not user_row:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Update user data with fresh database info
        user_data.update({
            "id": user_row[0],
            "email": user_row[1],
            "username": user_row[2],
            "is_premium": user_row[3],
            "credits_balance": user_row[4],
            "subscription_tier": user_row[5] or "free"
        })
        
        logger.info(f"✅ Authenticated user: {user_data['id']} ({user_data['email']})")
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def require_premium(
    current_user: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Premium requirement dependency
    Use this on premium-only routes
    """
    if not current_user.get("is_premium", False):
        raise HTTPException(
            status_code=403, 
            detail="Premium subscription required for this feature"
        )
    
    return current_user


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - returns user if authenticated, None otherwise
    Use this on routes that work with or without auth
    """
    try:
        return await require_auth(request, credentials, db)
    except HTTPException:
        return None

"""
Agent State Service - Manages persistent state for LangGraph agents using Redis.
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis

from config.settings import Settings

logger = logging.getLogger(__name__)
settings = Settings()


class AgentStateService:
    """
    Manages agent state persistence using Redis or in-memory fallback.
    States have TTL of 1 hour and are cleared after task completion.
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.state_ttl = 3600  # 1 hour
        self.in_memory_states: Dict[str, tuple[Dict[str, Any], datetime]] = {}  # Fallback
        
    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if not self.redis_client:
            # Check if Redis URL is configured
            if not settings.REDIS_URL or settings.REDIS_URL == "":
                raise ValueError("Redis URL not configured")
            
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client
    
    def _get_state_key(self, user_id: int, conversation_id: int, mode: str) -> str:
        """Generate Redis key for agent state."""
        return f"agent_state:{mode}:user_{user_id}:conv_{conversation_id}"
    
    async def save_state(
        self,
        user_id: int,
        conversation_id: int,
        mode: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        Save agent state to Redis with TTL (or in-memory fallback).
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            mode: Agent mode (e.g., "reminders", "health")
            state: State dictionary to save
            
        Returns:
            True if successful
        """
        key = self._get_state_key(user_id, conversation_id, mode)
        
        try:
            client = await self._get_client()
            
            # Serialize state
            state_json = json.dumps(state, default=str)
            
            # Save with TTL
            await client.setex(key, self.state_ttl, state_json)
            
            logger.info(f"✅ Saved agent state to Redis: {key}")
            return True
            
        except Exception as e:
            # Fallback to in-memory storage
            logger.warning(f"⚠️ Redis unavailable, using in-memory state: {e}")
            expiry = datetime.now() + timedelta(seconds=self.state_ttl)
            self.in_memory_states[key] = (state, expiry)
            logger.info(f"✅ Saved agent state to memory: {key}")
            return True
    
    async def load_state(
        self,
        user_id: int,
        conversation_id: int,
        mode: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load agent state from Redis (or in-memory fallback).
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            mode: Agent mode
            
        Returns:
            State dictionary or None if not found
        """
        key = self._get_state_key(user_id, conversation_id, mode)
        
        try:
            client = await self._get_client()
            state_json = await client.get(key)
            
            if state_json:
                state = json.loads(state_json)
                
                # Convert datetime strings back to datetime objects
                if state.get("reminder_datetime"):
                    try:
                        state["reminder_datetime"] = datetime.fromisoformat(state["reminder_datetime"])
                    except:
                        pass
                
                logger.info(f"✅ Loaded agent state from Redis: {key}")
                return state
            
            return None
            
        except Exception as e:
            # Fallback to in-memory storage
            logger.warning(f"⚠️ Redis unavailable, checking in-memory state: {e}")
            
            if key in self.in_memory_states:
                state, expiry = self.in_memory_states[key]
                
                # Check if expired
                if datetime.now() > expiry:
                    del self.in_memory_states[key]
                    logger.info(f"⏰ In-memory state expired: {key}")
                    return None
                
                # Convert datetime strings back to datetime objects
                if state.get("reminder_datetime") and isinstance(state["reminder_datetime"], str):
                    try:
                        state["reminder_datetime"] = datetime.fromisoformat(state["reminder_datetime"])
                    except:
                        pass
                
                logger.info(f"✅ Loaded agent state from memory: {key}")
                return state
            
            return None
    
    async def clear_state(
        self,
        user_id: int,
        conversation_id: int,
        mode: str
    ) -> bool:
        """
        Clear agent state from Redis or memory (called after task completion).
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            mode: Agent mode
            
        Returns:
            True if successful
        """
        key = self._get_state_key(user_id, conversation_id, mode)
        
        try:
            client = await self._get_client()
            await client.delete(key)
            logger.info(f"✅ Cleared agent state from Redis: {key}")
            return True
            
        except Exception as e:
            # Fallback to in-memory storage
            logger.warning(f"⚠️ Redis unavailable, clearing from memory: {e}")
            if key in self.in_memory_states:
                del self.in_memory_states[key]
                logger.info(f"✅ Cleared agent state from memory: {key}")
            return True
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()

from typing import Any, Optional, Dict
import json
import time
from functools import wraps
from flask import current_app
import hashlib


class InMemoryCache:
    """Simple in-memory cache implementation"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            entry = self._cache[key]
            if entry['expires_at'] > time.time():
                return entry['value']
            else:
                # Remove expired entry
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache with TTL (time to live) in seconds"""
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl
        }
    
    def delete(self, key: str) -> None:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
    
    def cleanup_expired(self) -> None:
        """Clean up expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry['expires_at'] <= current_time
        ]
        for key in expired_keys:
            del self._cache[key]


# Global cache instance
cache = InMemoryCache()


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_data = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            key = f"{key_prefix}:{f.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(key)
            if cached_result is not None:
                try:
                    current_app.logger.debug(f"Cache hit for key: {key}")
                except RuntimeError:
                    # No Flask application context available
                    pass
                return cached_result
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            cache.set(key, result, ttl)
            
            try:
                current_app.logger.debug(f"Cache miss for key: {key}, result cached")
            except RuntimeError:
                # No Flask application context available
                pass
            
            return result
        return decorated_function
    return decorator


def invalidate_cache_pattern(pattern: str):
    """Invalidate cache entries matching pattern"""
    keys_to_delete = [key for key in cache._cache.keys() if pattern in key]
    for key in keys_to_delete:
        cache.delete(key)


def cache_user_conversations(user_id: int):
    """Cache key for user conversations"""
    return f"user_conversations:{user_id}"


def cache_conversation_messages(conversation_id: int):
    """Cache key for conversation messages"""
    return f"conversation_messages:{conversation_id}"


def invalidate_user_cache(user_id: int):
    """Invalidate all cache entries for a user"""
    invalidate_cache_pattern(f"user_conversations:{user_id}")
    invalidate_cache_pattern(f"conversations:get_user_conversations")  # Invalidate conversations cache
    invalidate_cache_pattern(f"conversation_messages:")  # Invalidate all conversation caches for simplicity


def performance_monitor(operation_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            func_name = operation_name or f.__name__
            
            try:
                result = f(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Try to use Flask logger, fallback to print if no app context
                try:
                    current_app.logger.info(f"{func_name} executed in {execution_time:.4f} seconds")
                except RuntimeError:
                    # No Flask application context available
                    print(f"[INFO] {func_name} executed in {execution_time:.4f} seconds")
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                
                # Try to use Flask logger, fallback to print if no app context
                try:
                    current_app.logger.error(f"{func_name} failed after {execution_time:.4f} seconds: {str(e)}")
                except RuntimeError:
                    # No Flask application context available
                    print(f"[ERROR] {func_name} failed after {execution_time:.4f} seconds: {str(e)}")
                
                raise
        return decorated_function
    
    # Support both @performance_monitor and @performance_monitor("name")
    if callable(operation_name):
        func = operation_name
        operation_name = None
        return decorator(func)
    return decorator 
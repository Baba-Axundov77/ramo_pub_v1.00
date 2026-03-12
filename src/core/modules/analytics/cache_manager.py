# modules/analytics/cache_manager.py — Simple Caching for Analytics
from __future__ import annotations
import functools
import time
import threading
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SimpleCache:
    """Thread-safe simple in-memory cache with TTL"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        with self.lock:
            if key in self.cache:
                item = self.cache[key]
                if time.time() < item['expires']:
                    logger.debug(f"Cache hit for key: {key}")
                    return item['value']
                else:
                    # Expired item, remove it
                    del self.cache[key]
                    logger.debug(f"Cache expired for key: {key}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        with self.lock:
            ttl = ttl or self.default_ttl
            self.cache[key] = {
                'value': value,
                'expires': time.time() + ttl
            }
            logger.debug(f"Cache set for key: {key}, TTL: {ttl}s")
    
    def delete(self, key: str) -> None:
        """Delete specific key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Cache deleted for key: {key}")
    
    def clear(self) -> None:
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
            logger.debug("Cache cleared")
    
    def cleanup_expired(self) -> None:
        """Remove expired entries"""
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, item in self.cache.items()
                if current_time >= item['expires']
            ]
            for key in expired_keys:
                del self.cache[key]
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

# Global cache instance
cache = SimpleCache(default_ttl=300)  # 5 minutes

def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}{func.__name__}_{str(args)}_{str(kwargs)}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            try:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, ttl)
                return result
            except Exception as e:
                logger.error(f"Error in cached function {func.__name__}: {str(e)}")
                # Return function result even if caching fails
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str) -> None:
    """Invalidate cache entries matching pattern"""
    with cache.lock:
        keys_to_delete = [
            key for key in cache.cache.keys()
            if pattern in key
        ]
        for key in keys_to_delete:
            del cache.cache[key]
        logger.debug(f"Invalidated {len(keys_to_delete)} cache entries matching pattern: {pattern}")

# Cache invalidation strategies
def invalidate_order_cache():
    """Invalidate all order-related cache"""
    invalidate_cache_pattern("get_today")
    invalidate_cache_pattern("get_sales")
    invalidate_cache_pattern("get_order")
    invalidate_cache_pattern("get_top_selling")

def invalidate_inventory_cache():
    """Invalidate all inventory-related cache"""
    invalidate_cache_pattern("get_critical")
    invalidate_cache_pattern("inventory")

def invalidate_dashboard_cache():
    """Invalidate all dashboard cache"""
    invalidate_cache_pattern("get_comprehensive")
    invalidate_cache_pattern("dashboard")

# Auto-cleanup thread
def start_cache_cleanup():
    """Start background thread for cache cleanup"""
    def cleanup():
        while True:
            time.sleep(60)  # Check every minute
            cache.cleanup_expired()
    
    cleanup_thread = threading.Thread(target=cleanup, daemon=True)
    cleanup_thread.start()
    logger.info("Cache cleanup thread started")

# Start cleanup thread on import
start_cache_cleanup()

"""
Application-Level Caching System

This module provides comprehensive caching strategies including:
- Redis-based caching
- In-memory caching
- Query result caching
- Cache invalidation strategies
- Cache performance monitoring
"""

import asyncio
import json
import logging
import pickle
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
import redis
from cachetools import TTLCache, LRUCache
import aioredis

logger = logging.getLogger(__name__)


class CacheManager:
    """Comprehensive cache management system"""
    
    def __init__(self, redis_url: str = "redis://localhost:6391"):
        self.redis_url = redis_url
        self.redis_client = redis.from_url(redis_url)
        self.aioredis_client = None
        
        # In-memory caches
        self.query_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes
        self.session_cache = TTLCache(maxsize=10000, ttl=3600)  # 1 hour
        self.user_cache = LRUCache(maxsize=1000)
        
        # Cache statistics
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
        # Cache configuration
        self.default_ttl = 300  # 5 minutes
        self.max_ttl = 86400  # 24 hours
        
        # Initialize async Redis client
        asyncio.create_task(self._initialize_async_client())
    
    async def _initialize_async_client(self):
        """Initialize async Redis client"""
        try:
            self.aioredis_client = aioredis.from_url(self.redis_url)
            logger.info("Async Redis client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize async Redis client: {e}")
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a unique cache key"""
        # Create a hash of the arguments
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        try:
            # Try Redis first
            value = await self.aioredis_client.get(key)
            if value is not None:
                self.cache_stats['hits'] += 1
                return pickle.loads(value)
            
            # Try in-memory caches
            if key in self.query_cache:
                self.cache_stats['hits'] += 1
                return self.query_cache[key]
            
            if key in self.session_cache:
                self.cache_stats['hits'] += 1
                return self.session_cache[key]
            
            if key in self.user_cache:
                self.cache_stats['hits'] += 1
                return self.user_cache[key]
            
            self.cache_stats['misses'] += 1
            return default
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            ttl = ttl or self.default_ttl
            
            # Serialize value
            serialized_value = pickle.dumps(value)
            
            # Set in Redis
            await self.aioredis_client.setex(key, ttl, serialized_value)
            
            # Set in appropriate in-memory cache based on TTL
            if ttl <= 300:  # 5 minutes or less
                self.query_cache[key] = value
            elif ttl <= 3600:  # 1 hour or less
                self.session_cache[key] = value
            else:
                self.user_cache[key] = value
            
            self.cache_stats['sets'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            # Delete from Redis
            await self.aioredis_client.delete(key)
            
            # Delete from in-memory caches
            self.query_cache.pop(key, None)
            self.session_cache.pop(key, None)
            self.user_cache.pop(key, None)
            
            self.cache_stats['deletes'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            # Check Redis
            exists = await self.aioredis_client.exists(key)
            if exists:
                return True
            
            # Check in-memory caches
            return (key in self.query_cache or 
                   key in self.session_cache or 
                   key in self.user_cache)
            
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for cache key"""
        try:
            await self.aioredis_client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Cache expire error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        try:
            keys = await self.aioredis_client.keys(pattern)
            if keys:
                deleted = await self.aioredis_client.delete(*keys)
                
                # Clear from in-memory caches
                for key in keys:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    self.query_cache.pop(key_str, None)
                    self.session_cache.pop(key_str, None)
                    self.user_cache.pop(key_str, None)
                
                return deleted
            return 0
            
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        try:
            result = {}
            
            # Get from Redis
            redis_values = await self.aioredis_client.mget(keys)
            
            for key, value in zip(keys, redis_values):
                if value is not None:
                    result[key] = pickle.loads(value)
                    self.cache_stats['hits'] += 1
                else:
                    # Try in-memory caches
                    if key in self.query_cache:
                        result[key] = self.query_cache[key]
                        self.cache_stats['hits'] += 1
                    elif key in self.session_cache:
                        result[key] = self.session_cache[key]
                        self.cache_stats['hits'] += 1
                    elif key in self.user_cache:
                        result[key] = self.user_cache[key]
                        self.cache_stats['hits'] += 1
                    else:
                        self.cache_stats['misses'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    async def set_many(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values in cache"""
        try:
            ttl = ttl or self.default_ttl
            
            # Prepare Redis pipeline
            pipe = self.aioredis_client.pipeline()
            
            for key, value in data.items():
                serialized_value = pickle.dumps(value)
                pipe.setex(key, ttl, serialized_value)
                
                # Set in appropriate in-memory cache
                if ttl <= 300:
                    self.query_cache[key] = value
                elif ttl <= 3600:
                    self.session_cache[key] = value
                else:
                    self.user_cache[key] = value
            
            # Execute pipeline
            await pipe.execute()
            
            self.cache_stats['sets'] += len(data)
            return True
            
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    def cache_result(self, ttl: Optional[int] = None, key_prefix: str = "func"):
        """Decorator for caching function results"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_cache_key(key_prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Cache result
                await self.set(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator
    
    def cache_query_result(self, ttl: Optional[int] = None):
        """Decorator for caching database query results"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key based on query and parameters
                query_str = str(args[0]) if args else ""
                params_str = str(kwargs)
                cache_key = f"query:{hashlib.md5((query_str + params_str).encode()).hexdigest()}"
                
                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute query
                result = await func(*args, **kwargs)
                
                # Cache result
                await self.set(cache_key, result, ttl or 300)
                
                return result
            
            return wrapper
        return decorator
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a specific user"""
        try:
            pattern = f"user:{user_id}:*"
            await self.clear_pattern(pattern)
            logger.info(f"Invalidated cache for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate user cache: {e}")
    
    async def invalidate_session_cache(self, session_id: str):
        """Invalidate session-related cache entries"""
        try:
            pattern = f"session:{session_id}:*"
            await self.clear_pattern(pattern)
            logger.info(f"Invalidated cache for session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate session cache: {e}")
    
    async def invalidate_table_cache(self, table_name: str):
        """Invalidate all cache entries related to a database table"""
        try:
            pattern = f"table:{table_name}:*"
            await self.clear_pattern(pattern)
            logger.info(f"Invalidated cache for table: {table_name}")
        except Exception as e:
            logger.error(f"Failed to invalidate table cache: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        try:
            total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
            hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            # Get Redis info
            redis_info = await self.aioredis_client.info()
            
            return {
                'hits': self.cache_stats['hits'],
                'misses': self.cache_stats['misses'],
                'sets': self.cache_stats['sets'],
                'deletes': self.cache_stats['deletes'],
                'hit_rate': round(hit_rate, 2),
                'total_requests': total_requests,
                'in_memory_cache_sizes': {
                    'query_cache': len(self.query_cache),
                    'session_cache': len(self.session_cache),
                    'user_cache': len(self.user_cache)
                },
                'redis_info': {
                    'used_memory': redis_info.get('used_memory_human', 'N/A'),
                    'connected_clients': redis_info.get('connected_clients', 0),
                    'total_commands_processed': redis_info.get('total_commands_processed', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    async def optimize_cache(self) -> bool:
        """Optimize cache performance"""
        try:
            # Clear expired entries from in-memory caches
            self.query_cache.clear()
            self.session_cache.clear()
            
            # Keep only recent entries in user cache
            if len(self.user_cache) > 800:  # 80% of max size
                # Remove oldest entries
                items_to_remove = len(self.user_cache) - 500
                for _ in range(items_to_remove):
                    self.user_cache.popitem()
            
            # Optimize Redis memory
            await self.aioredis_client.memory_purge()
            
            logger.info("Cache optimization completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to optimize cache: {e}")
            return False
    
    async def warm_cache(self, warmup_data: Dict[str, Any]) -> bool:
        """Warm up cache with frequently accessed data"""
        try:
            for key, value in warmup_data.items():
                await self.set(key, value, ttl=3600)  # 1 hour TTL
            
            logger.info(f"Cache warmed up with {len(warmup_data)} items")
            return True
            
        except Exception as e:
            logger.error(f"Failed to warm cache: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup cache resources"""
        try:
            if self.aioredis_client:
                await self.aioredis_client.close()
            
            # Clear in-memory caches
            self.query_cache.clear()
            self.session_cache.clear()
            self.user_cache.clear()
            
            logger.info("Cache manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Failed to cleanup cache manager: {e}")


class QueryResultCache:
    """Specialized cache for database query results"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.query_patterns = {}
    
    async def cache_query(self, query: str, params: Dict, result: Any, ttl: int = 300) -> bool:
        """Cache a database query result"""
        try:
            # Generate cache key
            cache_key = self._generate_query_key(query, params)
            
            # Cache the result
            return await self.cache_manager.set(cache_key, result, ttl)
            
        except Exception as e:
            logger.error(f"Failed to cache query: {e}")
            return False
    
    async def get_cached_query(self, query: str, params: Dict) -> Optional[Any]:
        """Get cached query result"""
        try:
            cache_key = self._generate_query_key(query, params)
            return await self.cache_manager.get(cache_key)
            
        except Exception as e:
            logger.error(f"Failed to get cached query: {e}")
            return None
    
    def _generate_query_key(self, query: str, params: Dict) -> str:
        """Generate cache key for query"""
        # Normalize query
        normalized_query = query.strip().lower()
        
        # Create hash of query and parameters
        query_hash = hashlib.md5(
            (normalized_query + str(sorted(params.items()))).encode()
        ).hexdigest()
        
        return f"query:{query_hash}"
    
    async def invalidate_table_queries(self, table_name: str) -> bool:
        """Invalidate all cached queries for a specific table"""
        try:
            pattern = f"query:*"
            keys = await self.cache_manager.aioredis_client.keys(pattern)
            
            # Filter keys that contain the table name
            table_keys = [key for key in keys if table_name.lower() in key.decode().lower()]
            
            if table_keys:
                await self.cache_manager.aioredis_client.delete(*table_keys)
                logger.info(f"Invalidated {len(table_keys)} cached queries for table: {table_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate table queries: {e}")
            return False








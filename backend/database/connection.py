"""
Database connection management and configuration
Replaces Supabase client with direct PostgreSQL connections
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager
import asyncpg
from asyncpg import Pool, Connection
import redis.asyncio as redis
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import json

logger = logging.getLogger(__name__)

# SQLAlchemy setup
Base = declarative_base()
metadata = MetaData()

class DatabaseConfig:
    """Database configuration management"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://suna_user:suna_password@localhost:5432/suna')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '20'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '30'))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))
        
    @property
    def async_database_url(self) -> str:
        """Convert sync URL to async URL for SQLAlchemy"""
        return self.database_url.replace('postgresql://', 'postgresql+asyncpg://')
    
    @property
    def asyncpg_url(self) -> str:
        """Get URL for direct asyncpg connections"""
        return self.database_url

class DatabaseManager:
    """Main database manager class replacing Supabase client"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._pg_pool: Optional[Pool] = None
        self._redis_pool: Optional[redis.ConnectionPool] = None
        self._sqlalchemy_engine = None
        self._session_factory = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connections"""
        if self._initialized:
            return
        
        try:
            # Initialize PostgreSQL connection pool
            self._pg_pool = await asyncpg.create_pool(
                self.config.asyncpg_url,
                min_size=5,
                max_size=self.config.pool_size,
                command_timeout=60,
                server_settings={
                    'jit': 'off',  # Disable JIT for better performance on small queries
                    'application_name': 'suna_backend'
                }
            )
            
            # Initialize Redis connection pool
            self._redis_pool = redis.ConnectionPool.from_url(
                self.config.redis_url,
                max_connections=20,
                retry_on_timeout=True
            )
            
            # Initialize SQLAlchemy async engine
            self._sqlalchemy_engine = create_async_engine(
                self.config.async_database_url,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=os.getenv('DB_ECHO', 'false').lower() == 'true'
            )
            
            # Create session factory
            self._session_factory = async_sessionmaker(
                self._sqlalchemy_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connections
            await self._test_connections()
            
            self._initialized = True
            logger.info("Database connections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            await self.close()
            raise
    
    async def _test_connections(self):
        """Test database connections"""
        # Test PostgreSQL
        async with self._pg_pool.acquire() as conn:
            result = await conn.fetchval('SELECT 1')
            assert result == 1
        
        # Test Redis
        redis_client = redis.Redis(connection_pool=self._redis_pool)
        await redis_client.ping()
        await redis_client.close()
    
    async def close(self):
        """Close all database connections"""
        if self._pg_pool:
            await self._pg_pool.close()
            self._pg_pool = None
        
        if self._redis_pool:
            await self._redis_pool.disconnect()
            self._redis_pool = None
        
        if self._sqlalchemy_engine:
            await self._sqlalchemy_engine.dispose()
            self._sqlalchemy_engine = None
        
        self._session_factory = None
        self._initialized = False
        logger.info("Database connections closed")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Connection, None]:
        """Get a raw asyncpg connection"""
        if not self._initialized:
            await self.initialize()
        
        async with self._pg_pool.acquire() as conn:
            yield conn
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a SQLAlchemy async session"""
        if not self._initialized:
            await self.initialize()
        
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    @asynccontextmanager
    async def get_redis(self) -> AsyncGenerator[redis.Redis, None]:
        """Get a Redis connection"""
        if not self._initialized:
            await self.initialize()
        
        redis_client = redis.Redis(connection_pool=self._redis_pool)
        try:
            yield redis_client
        finally:
            await redis_client.close()
    
    async def execute_query(self, query: str, *args, **kwargs) -> Any:
        """Execute a raw SQL query"""
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args, **kwargs)
    
    async def execute_one(self, query: str, *args, **kwargs) -> Any:
        """Execute a query and return one result"""
        async with self.get_connection() as conn:
            return await conn.fetchrow(query, *args, **kwargs)
    
    async def execute_scalar(self, query: str, *args, **kwargs) -> Any:
        """Execute a query and return scalar value"""
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args, **kwargs)

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for backward compatibility with Supabase patterns
async def get_db_connection():
    """Get database connection (replaces supabase client)"""
    return db_manager.get_connection()

async def get_db_session():
    """Get SQLAlchemy session"""
    return db_manager.get_session()

async def get_redis_connection():
    """Get Redis connection"""
    return db_manager.get_redis()

# Dependency injection for FastAPI
async def get_database():
    """FastAPI dependency for database access"""
    async with db_manager.get_session() as session:
        yield session

async def get_redis():
    """FastAPI dependency for Redis access"""
    async with db_manager.get_redis() as redis_client:
        yield redis_client
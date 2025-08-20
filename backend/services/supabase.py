"""
Centralized database connection management for AgentPress.
Now uses PostgreSQL directly instead of Supabase.
"""

from typing import Optional
from utils.logger import logger
from utils.config import config
import threading
from services.postgresql_db import PostgreSQLConnection, PostgreSQLClient

class DBConnection:
    """Thread-safe singleton database connection manager using PostgreSQL."""
    
    _instance: Optional['DBConnection'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._pg_connection = None
        return cls._instance

    def __init__(self):
        """No initialization needed in __init__ as it's handled in __new__"""
        pass

    async def initialize(self):
        """Initialize the database connection."""
        if self._initialized:
            return
                
        try:
            logger.debug("Initializing PostgreSQL connection")
            
            # Create PostgreSQL connection instance
            self._pg_connection = PostgreSQLConnection()
            await self._pg_connection.initialize()
            
            self._initialized = True
            logger.debug("Database connection initialized with PostgreSQL")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise RuntimeError(f"Failed to initialize database connection: {str(e)}")

    @classmethod
    async def disconnect(cls):
        """Disconnect from the database."""
        if cls._instance and cls._instance._pg_connection:
            logger.debug("Disconnecting from PostgreSQL database")
            try:
                await cls._instance._pg_connection.disconnect()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                cls._instance._initialized = False
                cls._instance._pg_connection = None
                logger.debug("Database disconnected successfully")

    @property
    async def client(self) -> PostgreSQLClient:
        """Get the PostgreSQL client instance (compatible with Supabase client interface)."""
        if not self._initialized:
            logger.debug("PostgreSQL client not initialized, initializing now")
            await self.initialize()
        if not self._pg_connection:
            logger.error("PostgreSQL connection is None after initialization")
            raise RuntimeError("Database not initialized")
        return await self._pg_connection.client

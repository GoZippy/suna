"""
PostgreSQL database connection service to replace Supabase client.
Provides a compatible interface for existing code while using direct PostgreSQL connections.
"""

import asyncio
import json
import uuid
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone
import asyncpg
from asyncpg import Pool, Connection, Record
from utils.logger import logger
from utils.config import config
import threading

class PostgreSQLClient:
    """
    PostgreSQL client that mimics Supabase client interface.
    Provides table() method and query building similar to Supabase.
    """
    
    def __init__(self, connection_pool: Pool):
        self.pool = connection_pool
    
    def table(self, table_name: str) -> 'TableQuery':
        """Create a table query builder"""
        return TableQuery(self.pool, table_name)
    
    async def rpc(self, function_name: str, params: Dict[str, Any] = None) -> 'QueryResult':
        """Call a PostgreSQL function"""
        try:
            async with self.pool.acquire() as conn:
                if params:
                    # Convert params to function call format
                    param_names = list(params.keys())
                    param_values = list(params.values())
                    placeholders = ', '.join([f'${i+1}' for i in range(len(param_values))])
                    query = f"SELECT {function_name}({placeholders})"
                    result = await conn.fetch(query, *param_values)
                else:
                    query = f"SELECT {function_name}()"
                    result = await conn.fetch(query)
                
                return QueryResult([dict(row) for row in result])
        except Exception as e:
            logger.error(f"Error calling function {function_name}: {e}")
            raise

class TableQuery:
    """
    Table query builder that mimics Supabase table interface.
    """
    
    def __init__(self, pool: Pool, table_name: str):
        self.pool = pool
        self.table_name = table_name
        self._select_fields = "*"
        self._where_conditions = []
        self._order_by = []
        self._limit_value = None
        self._offset_value = None
        self._range_start = None
        self._range_end = None
    
    def select(self, fields: str = "*") -> 'TableQuery':
        """Select specific fields"""
        self._select_fields = fields
        return self
    
    def eq(self, column: str, value: Any) -> 'TableQuery':
        """Add equality condition"""
        self._where_conditions.append(f"{column} = ${len(self._where_conditions) + 1}")
        self._values = getattr(self, '_values', [])
        self._values.append(value)
        return self
    
    def neq(self, column: str, value: Any) -> 'TableQuery':
        """Add not equal condition"""
        self._where_conditions.append(f"{column} != ${len(self._where_conditions) + 1}")
        self._values = getattr(self, '_values', [])
        self._values.append(value)
        return self
    
    def lt(self, column: str, value: Any) -> 'TableQuery':
        """Add less than condition"""
        self._where_conditions.append(f"{column} < ${len(self._where_conditions) + 1}")
        self._values = getattr(self, '_values', [])
        self._values.append(value)
        return self
    
    def gt(self, column: str, value: Any) -> 'TableQuery':
        """Add greater than condition"""
        self._where_conditions.append(f"{column} > ${len(self._where_conditions) + 1}")
        self._values = getattr(self, '_values', [])
        self._values.append(value)
        return self
    
    def order(self, column: str, desc: bool = False) -> 'TableQuery':
        """Add order by clause"""
        direction = "DESC" if desc else "ASC"
        self._order_by.append(f"{column} {direction}")
        return self
    
    def limit(self, count: int) -> 'TableQuery':
        """Add limit clause"""
        self._limit_value = count
        return self
    
    def offset(self, count: int) -> 'TableQuery':
        """Add offset clause"""
        self._offset_value = count
        return self
    
    def range(self, start: int, end: int) -> 'TableQuery':
        """Add range (limit/offset) clause"""
        self._range_start = start
        self._range_end = end
        return self
    
    async def execute(self) -> 'QueryResult':
        """Execute the query"""
        try:
            async with self.pool.acquire() as conn:
                query = self._build_select_query()
                values = getattr(self, '_values', [])
                
                logger.debug(f"Executing query: {query} with values: {values}")
                result = await conn.fetch(query, *values)
                
                return QueryResult([dict(row) for row in result])
        except Exception as e:
            logger.error(f"Error executing query on table {self.table_name}: {e}")
            raise
    
    async def insert(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> 'QueryResult':
        """Insert data into table"""
        try:
            async with self.pool.acquire() as conn:
                if isinstance(data, dict):
                    data = [data]
                
                if not data:
                    return QueryResult([])
                
                # Get column names from first record
                columns = list(data[0].keys())
                
                # Generate UUIDs for records that don't have an ID
                for record in data:
                    if 'id' not in record and f'{self.table_name[:-1]}_id' not in record:
                        # Try common ID patterns
                        if self.table_name == 'users':
                            record['id'] = str(uuid.uuid4())
                        elif self.table_name == 'projects':
                            record['project_id'] = str(uuid.uuid4())
                        elif self.table_name == 'threads':
                            record['thread_id'] = str(uuid.uuid4())
                        elif self.table_name == 'messages':
                            record['message_id'] = str(uuid.uuid4())
                        else:
                            record['id'] = str(uuid.uuid4())
                    
                    # Add timestamps if not present
                    if 'created_at' not in record:
                        record['created_at'] = datetime.now(timezone.utc)
                    if 'updated_at' not in record:
                        record['updated_at'] = datetime.now(timezone.utc)
                
                # Rebuild columns list in case we added fields
                columns = list(data[0].keys())
                
                # Build INSERT query
                placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
                query = f"""
                    INSERT INTO {self.table_name} ({', '.join(columns)})
                    VALUES ({placeholders})
                    RETURNING *
                """
                
                results = []
                for record in data:
                    values = [self._convert_value(record[col]) for col in columns]
                    result = await conn.fetchrow(query, *values)
                    results.append(dict(result))
                
                return QueryResult(results)
        except Exception as e:
            logger.error(f"Error inserting into table {self.table_name}: {e}")
            raise
    
    async def update(self, data: Dict[str, Any]) -> 'QueryResult':
        """Update data in table"""
        try:
            async with self.pool.acquire() as conn:
                # Add updated_at timestamp
                data['updated_at'] = datetime.now(timezone.utc)
                
                # Build SET clause
                set_clauses = []
                values = []
                param_index = 1
                
                for column, value in data.items():
                    set_clauses.append(f"{column} = ${param_index}")
                    values.append(self._convert_value(value))
                    param_index += 1
                
                # Add WHERE conditions
                where_values = getattr(self, '_values', [])
                for value in where_values:
                    values.append(value)
                
                where_clause = ""
                if self._where_conditions:
                    # Adjust parameter indices for WHERE conditions
                    adjusted_conditions = []
                    for i, condition in enumerate(self._where_conditions):
                        adjusted_condition = condition.replace(f'${i+1}', f'${param_index + i}')
                        adjusted_conditions.append(adjusted_condition)
                    where_clause = f"WHERE {' AND '.join(adjusted_conditions)}"
                
                query = f"""
                    UPDATE {self.table_name}
                    SET {', '.join(set_clauses)}
                    {where_clause}
                    RETURNING *
                """
                
                result = await conn.fetch(query, *values)
                return QueryResult([dict(row) for row in result])
        except Exception as e:
            logger.error(f"Error updating table {self.table_name}: {e}")
            raise
    
    async def delete(self) -> 'QueryResult':
        """Delete data from table"""
        try:
            async with self.pool.acquire() as conn:
                where_clause = ""
                values = getattr(self, '_values', [])
                
                if self._where_conditions:
                    where_clause = f"WHERE {' AND '.join(self._where_conditions)}"
                
                query = f"""
                    DELETE FROM {self.table_name}
                    {where_clause}
                    RETURNING *
                """
                
                result = await conn.fetch(query, *values)
                return QueryResult([dict(row) for row in result])
        except Exception as e:
            logger.error(f"Error deleting from table {self.table_name}: {e}")
            raise
    
    def _build_select_query(self) -> str:
        """Build SELECT query from current state"""
        query = f"SELECT {self._select_fields} FROM {self.table_name}"
        
        # Add WHERE clause
        if self._where_conditions:
            query += f" WHERE {' AND '.join(self._where_conditions)}"
        
        # Add ORDER BY clause
        if self._order_by:
            query += f" ORDER BY {', '.join(self._order_by)}"
        
        # Add LIMIT and OFFSET
        if self._range_start is not None and self._range_end is not None:
            limit = self._range_end - self._range_start + 1
            query += f" LIMIT {limit} OFFSET {self._range_start}"
        elif self._limit_value is not None:
            query += f" LIMIT {self._limit_value}"
            if self._offset_value is not None:
                query += f" OFFSET {self._offset_value}"
        
        return query
    
    def _convert_value(self, value: Any) -> Any:
        """Convert Python values to PostgreSQL-compatible format"""
        if isinstance(value, dict) or isinstance(value, list):
            return json.dumps(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        return value

class QueryResult:
    """
    Query result wrapper that mimics Supabase response format.
    """
    
    def __init__(self, data: List[Dict[str, Any]], error: Optional[str] = None):
        self.data = data
        self.error = error
        self.count = len(data) if data else 0

class PostgreSQLConnection:
    """
    PostgreSQL connection manager that replaces Supabase DBConnection.
    Maintains compatibility with existing Supabase-based code.
    """
    
    _instance: Optional['PostgreSQLConnection'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._pool = None
        return cls._instance
    
    def __init__(self):
        """No initialization needed in __init__ as it's handled in __new__"""
        pass
    
    async def initialize(self):
        """Initialize the PostgreSQL connection pool"""
        if self._initialized:
            return
        
        try:
            database_url = config.DATABASE_URL or 'postgresql://suna_user:suna_password@localhost:5432/suna'
            
            logger.debug("Initializing PostgreSQL connection pool")
            
            self._pool = await asyncpg.create_pool(
                database_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
                server_settings={
                    'jit': 'off',
                    'application_name': 'suna_backend'
                }
            )
            
            # Test connection
            async with self._pool.acquire() as conn:
                result = await conn.fetchval('SELECT 1')
                assert result == 1
            
            self._initialized = True
            logger.debug("PostgreSQL connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"PostgreSQL initialization error: {e}")
            raise RuntimeError(f"Failed to initialize PostgreSQL connection: {str(e)}")
    
    @classmethod
    async def disconnect(cls):
        """Disconnect from the database"""
        if cls._instance and cls._instance._pool:
            logger.debug("Disconnecting from PostgreSQL database")
            try:
                await cls._instance._pool.close()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                cls._instance._initialized = False
                cls._instance._pool = None
                logger.debug("PostgreSQL database disconnected successfully")
    
    @property
    async def client(self) -> PostgreSQLClient:
        """Get the PostgreSQL client instance (compatible with Supabase client)"""
        if not self._initialized:
            logger.debug("PostgreSQL client not initialized, initializing now")
            await self.initialize()
        if not self._pool:
            logger.error("PostgreSQL pool is None after initialization")
            raise RuntimeError("Database not initialized")
        return PostgreSQLClient(self._pool)

# Alias for backward compatibility
DBConnection = PostgreSQLConnection
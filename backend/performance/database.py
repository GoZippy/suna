"""
Database Performance Optimization

This module provides database query optimization, indexing strategies,
and connection pooling for improved performance.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool, ThreadedConnectionPool
import asyncpg
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import redis

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query: str
    execution_time: float
    rows_returned: int
    timestamp: datetime
    parameters: Optional[Dict] = None
    slow_query: bool = False


@dataclass
class IndexRecommendation:
    """Database index recommendation"""
    table_name: str
    column_name: str
    index_type: str
    estimated_improvement: float
    creation_sql: str


class DatabaseOptimizer:
    """Database performance optimization manager"""
    
    def __init__(self, database_url: str, redis_url: str = "redis://localhost:6391"):
        self.database_url = database_url
        self.redis_url = redis_url
        self.redis_client = redis.from_url(redis_url)
        
        # Connection pools
        self.sync_pool = None
        self.async_pool = None
        self.sqlalchemy_engine = None
        
        # Performance tracking
        self.query_metrics: List[QueryMetrics] = []
        self.slow_query_threshold = 1.0  # seconds
        
        # Initialize connection pools
        self._initialize_pools()
    
    def _initialize_pools(self):
        """Initialize database connection pools"""
        try:
            # SQLAlchemy engine with optimized pooling
            self.sqlalchemy_engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=20,
                max_overflow=30,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            
            # Psycopg2 connection pool for raw SQL
            self.sync_pool = ThreadedConnectionPool(
                minconn=5,
                maxconn=50,
                dsn=self.database_url
            )
            
            logger.info("Database connection pools initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database pools: {e}")
            raise
    
    async def _initialize_async_pool(self):
        """Initialize async connection pool"""
        try:
            self.async_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=50,
                command_timeout=60
            )
            logger.info("Async database pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize async pool: {e}")
            raise
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.async_pool:
            await self._initialize_async_pool()
        
        async with self.async_pool.acquire() as connection:
            yield connection
    
    def get_sync_connection(self):
        """Get synchronous database connection"""
        return self.sync_pool.getconn()
    
    def return_sync_connection(self, conn):
        """Return synchronous database connection to pool"""
        self.sync_pool.putconn(conn)
    
    async def analyze_query_performance(self, query: str, params: Optional[Dict] = None) -> QueryMetrics:
        """Analyze query performance and collect metrics"""
        start_time = datetime.now()
        
        try:
            async with self.get_connection() as conn:
                if params:
                    result = await conn.fetch(query, *params.values())
                else:
                    result = await conn.fetch(query)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                rows_returned = len(result)
                
                metrics = QueryMetrics(
                    query=query,
                    execution_time=execution_time,
                    rows_returned=rows_returned,
                    timestamp=start_time,
                    parameters=params,
                    slow_query=execution_time > self.slow_query_threshold
                )
                
                self.query_metrics.append(metrics)
                
                # Cache slow query metrics
                if metrics.slow_query:
                    await self._cache_slow_query(metrics)
                
                return metrics
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def _cache_slow_query(self, metrics: QueryMetrics):
        """Cache slow query metrics for analysis"""
        key = f"slow_query:{metrics.timestamp.isoformat()}"
        await self.redis_client.setex(
            key,
            3600,  # 1 hour TTL
            str(metrics)
        )
    
    async def generate_index_recommendations(self) -> List[IndexRecommendation]:
        """Generate index recommendations based on query patterns"""
        recommendations = []
        
        try:
            async with self.get_connection() as conn:
                # Analyze slow queries
                slow_queries = await self._get_slow_queries()
                
                for query_metrics in slow_queries:
                    # Simple heuristic-based index recommendations
                    if "WHERE" in query_metrics.query.upper():
                        # Extract table and column names from WHERE clauses
                        table_cols = self._extract_table_columns(query_metrics.query)
                        
                        for table, columns in table_cols.items():
                            for column in columns:
                                recommendation = IndexRecommendation(
                                    table_name=table,
                                    column_name=column,
                                    index_type="BTREE",
                                    estimated_improvement=0.8,  # 80% improvement estimate
                                    creation_sql=f"CREATE INDEX idx_{table}_{column} ON {table} ({column});"
                                )
                                recommendations.append(recommendation)
                
                return recommendations
                
        except Exception as e:
            logger.error(f"Failed to generate index recommendations: {e}")
            return []
    
    def _extract_table_columns(self, query: str) -> Dict[str, List[str]]:
        """Extract table and column names from SQL query"""
        # Simple regex-based extraction (in production, use proper SQL parser)
        import re
        
        table_cols = {}
        
        # Extract FROM clause
        from_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        if from_match:
            table = from_match.group(1)
            
            # Extract WHERE conditions
            where_match = re.search(r'WHERE\s+(.+)', query, re.IGNORECASE)
            if where_match:
                where_clause = where_match.group(1)
                
                # Extract column names from WHERE clause
                columns = re.findall(r'(\w+)\s*[=<>]', where_clause)
                table_cols[table] = columns
        
        return table_cols
    
    async def _get_slow_queries(self) -> List[QueryMetrics]:
        """Get cached slow queries"""
        slow_queries = []
        
        try:
            # Get slow queries from cache
            keys = await self.redis_client.keys("slow_query:*")
            
            for key in keys:
                data = await self.redis_client.get(key)
                if data:
                    # Parse metrics from cache (simplified)
                    slow_queries.append(QueryMetrics(
                        query=data.decode(),
                        execution_time=0.0,
                        rows_returned=0,
                        timestamp=datetime.now()
                    ))
            
            return slow_queries
            
        except Exception as e:
            logger.error(f"Failed to get slow queries: {e}")
            return []
    
    async def optimize_table_indexes(self, table_name: str) -> bool:
        """Optimize indexes for a specific table"""
        try:
            async with self.get_connection() as conn:
                # Get current indexes
                indexes_query = """
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = $1
                """
                current_indexes = await conn.fetch(indexes_query, table_name)
                
                # Get table statistics
                stats_query = """
                SELECT schemaname, tablename, attname, n_distinct, correlation
                FROM pg_stats 
                WHERE tablename = $1
                """
                stats = await conn.fetch(stats_query, table_name)
                
                # Generate optimization recommendations
                recommendations = await self._generate_table_recommendations(
                    table_name, current_indexes, stats
                )
                
                # Apply recommendations
                for rec in recommendations:
                    await conn.execute(rec.creation_sql)
                    logger.info(f"Created index: {rec.creation_sql}")
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to optimize table indexes: {e}")
            return False
    
    async def _generate_table_recommendations(
        self, 
        table_name: str, 
        current_indexes: List, 
        stats: List
    ) -> List[IndexRecommendation]:
        """Generate index recommendations for a specific table"""
        recommendations = []
        
        # Analyze column statistics for index recommendations
        for stat in stats:
            column = stat['attname']
            n_distinct = stat['n_distinct']
            correlation = stat['correlation']
            
            # Recommend indexes for columns with good selectivity
            if n_distinct > 100 and abs(correlation) < 0.8:
                # Check if index already exists
                index_exists = any(
                    column in idx['indexdef'] for idx in current_indexes
                )
                
                if not index_exists:
                    recommendation = IndexRecommendation(
                        table_name=table_name,
                        column_name=column,
                        index_type="BTREE",
                        estimated_improvement=0.7,
                        creation_sql=f"CREATE INDEX idx_{table_name}_{column} ON {table_name} ({column});"
                    )
                    recommendations.append(recommendation)
        
        return recommendations
    
    async def vacuum_analyze_table(self, table_name: str) -> bool:
        """Run VACUUM ANALYZE on a table to update statistics"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(f"VACUUM ANALYZE {table_name};")
                logger.info(f"VACUUM ANALYZE completed for table: {table_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to VACUUM ANALYZE table: {e}")
            return False
    
    async def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """Get detailed table statistics"""
        try:
            async with self.get_connection() as conn:
                # Get table size
                size_query = """
                SELECT 
                    pg_size_pretty(pg_total_relation_size($1)) as total_size,
                    pg_size_pretty(pg_relation_size($1)) as table_size,
                    pg_size_pretty(pg_total_relation_size($1) - pg_relation_size($1)) as index_size
                """
                size_result = await conn.fetchrow(size_query, table_name)
                
                # Get row count
                count_query = f"SELECT COUNT(*) as row_count FROM {table_name}"
                count_result = await conn.fetchrow(count_query)
                
                # Get index information
                index_query = """
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = $1
                """
                indexes = await conn.fetch(index_query, table_name)
                
                return {
                    'table_name': table_name,
                    'total_size': size_result['total_size'],
                    'table_size': size_result['table_size'],
                    'index_size': size_result['index_size'],
                    'row_count': count_result['row_count'],
                    'indexes': [dict(idx) for idx in indexes]
                }
                
        except Exception as e:
            logger.error(f"Failed to get table statistics: {e}")
            return {}
    
    async def optimize_connection_pool(self) -> bool:
        """Optimize connection pool settings based on usage patterns"""
        try:
            # Analyze connection usage
            pool_stats = {
                'total_connections': len(self.sync_pool._pool),
                'available_connections': len([c for c in self.sync_pool._pool if not c.closed]),
                'active_connections': len([c for c in self.sync_pool._pool if not c.closed and c.get_backend_pid()])
            }
            
            # Adjust pool size based on usage
            if pool_stats['active_connections'] > pool_stats['total_connections'] * 0.8:
                # Increase pool size
                new_max_conn = min(100, pool_stats['total_connections'] * 1.5)
                logger.info(f"Increasing connection pool size to {new_max_conn}")
                
            elif pool_stats['active_connections'] < pool_stats['total_connections'] * 0.3:
                # Decrease pool size
                new_max_conn = max(10, pool_stats['total_connections'] * 0.7)
                logger.info(f"Decreasing connection pool size to {new_max_conn}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to optimize connection pool: {e}")
            return False
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        try:
            # Calculate average query execution time
            if self.query_metrics:
                avg_execution_time = sum(
                    m.execution_time for m in self.query_metrics
                ) / len(self.query_metrics)
                
                slow_query_count = sum(
                    1 for m in self.query_metrics if m.slow_query
                )
            else:
                avg_execution_time = 0.0
                slow_query_count = 0
            
            # Get connection pool statistics
            pool_stats = {
                'total_connections': len(self.sync_pool._pool) if self.sync_pool else 0,
                'available_connections': len([c for c in self.sync_pool._pool if not c.closed]) if self.sync_pool else 0
            }
            
            return {
                'total_queries': len(self.query_metrics),
                'average_execution_time': avg_execution_time,
                'slow_query_count': slow_query_count,
                'slow_query_threshold': self.slow_query_threshold,
                'connection_pool_stats': pool_stats,
                'last_optimization': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {}
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.sync_pool:
                self.sync_pool.closeall()
            
            if self.async_pool:
                await self.async_pool.close()
            
            if self.sqlalchemy_engine:
                self.sqlalchemy_engine.dispose()
            
            logger.info("Database optimizer cleanup completed")
            
        except Exception as e:
            logger.error(f"Failed to cleanup database optimizer: {e}")








"""
Performance and load testing for Suna system
"""

import pytest
import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from tests import TEST_CONFIG


@dataclass
class PerformanceMetrics:
    """Performance test metrics"""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float


class LoadTestBase:
    """Base class for load testing"""
    
    def __init__(self, base_url: str, auth_headers: Dict[str, str] = None):
        self.base_url = base_url
        self.auth_headers = auth_headers or {}
        self.results: List[Dict[str, Any]] = []
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a single HTTP request and record metrics"""
        url = f"{self.base_url}{endpoint}"
        headers = {**self.auth_headers, **kwargs.get('headers', {})}
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, **kwargs) as response:
                    response_time = time.time() - start_time
                    
                    result = {
                        'status_code': response.status,
                        'response_time': response_time,
                        'success': 200 <= response.status < 400,
                        'error': None
                    }
                    
                    if response.status >= 400:
                        result['error'] = await response.text()
                    
                    return result
                    
        except Exception as e:
            response_time = time.time() - start_time
            return {
                'status_code': 0,
                'response_time': response_time,
                'success': False,
                'error': str(e)
            }
    
    def calculate_metrics(self, test_name: str) -> PerformanceMetrics:
        """Calculate performance metrics from test results"""
        if not self.results:
            return PerformanceMetrics(
                test_name=test_name,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                average_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                requests_per_second=0.0,
                error_rate=0.0
            )
        
        response_times = [r['response_time'] for r in self.results]
        successful_requests = sum(1 for r in self.results if r['success'])
        failed_requests = len(self.results) - successful_requests
        
        # Calculate percentiles
        sorted_times = sorted(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p99_index = int(len(sorted_times) * 0.99)
        
        total_time = max(response_times) - min(response_times) if response_times else 0
        
        return PerformanceMetrics(
            test_name=test_name,
            total_requests=len(self.results),
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p95_response_time=sorted_times[p95_index] if p95_index < len(sorted_times) else 0,
            p99_response_time=sorted_times[p99_index] if p99_index < len(sorted_times) else 0,
            requests_per_second=len(self.results) / total_time if total_time > 0 else 0,
            error_rate=failed_requests / len(self.results) if self.results else 0
        )


class TestLoadTesting:
    """Load testing scenarios"""
    
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_concurrent_user_registration(self, auth_headers, load_test_config):
        """Test concurrent user registration performance"""
        base_url = load_test_config['base_url']
        num_users = 50
        
        load_test = LoadTestBase(base_url)
        
        # Create concurrent registration requests
        tasks = []
        for i in range(num_users):
            user_data = {
                "email": f"loadtest{i}@example.com",
                "password": "testpassword123",
                "username": f"loadtest{i}",
                "full_name": f"Load Test User {i}"
            }
            
            task = load_test.make_request(
                "POST", 
                "/auth/register", 
                json=user_data
            )
            tasks.append(task)
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        load_test.results = [r for r in results if not isinstance(r, Exception)]
        
        # Calculate metrics
        metrics = load_test.calculate_metrics("Concurrent User Registration")
        
        # Assertions
        assert metrics.error_rate < 0.1  # Less than 10% error rate
        assert metrics.average_response_time < 2.0  # Less than 2 seconds average
        assert metrics.p95_response_time < 5.0  # 95% under 5 seconds
        
        print(f"Registration Load Test Results:")
        print(f"  Total Requests: {metrics.total_requests}")
        print(f"  Success Rate: {(1 - metrics.error_rate) * 100:.1f}%")
        print(f"  Average Response Time: {metrics.average_response_time:.2f}s")
        print(f"  P95 Response Time: {metrics.p95_response_time:.2f}s")
        print(f"  Requests/Second: {metrics.requests_per_second:.1f}")
    
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_concurrent_agent_creation(self, auth_headers, load_test_config):
        """Test concurrent agent creation performance"""
        base_url = load_test_config['base_url']
        num_agents = 30
        
        load_test = LoadTestBase(base_url, auth_headers)
        
        # Create concurrent agent creation requests
        tasks = []
        for i in range(num_agents):
            agent_data = {
                "name": f"Load Test Agent {i}",
                "description": f"Agent created during load test {i}",
                "config": {
                    "model": "llama2:7b",
                    "temperature": 0.7
                }
            }
            
            task = load_test.make_request(
                "POST", 
                "/agents", 
                json=agent_data
            )
            tasks.append(task)
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        load_test.results = [r for r in results if not isinstance(r, Exception)]
        
        # Calculate metrics
        metrics = load_test.calculate_metrics("Concurrent Agent Creation")
        
        # Assertions
        assert metrics.error_rate < 0.05  # Less than 5% error rate
        assert metrics.average_response_time < 1.0  # Less than 1 second average
        assert metrics.p95_response_time < 2.0  # 95% under 2 seconds
        
        print(f"Agent Creation Load Test Results:")
        print(f"  Total Requests: {metrics.total_requests}")
        print(f"  Success Rate: {(1 - metrics.error_rate) * 100:.1f}%")
        print(f"  Average Response Time: {metrics.average_response_time:.2f}s")
        print(f"  P95 Response Time: {metrics.p95_response_time:.2f}s")
        print(f"  Requests/Second: {metrics.requests_per_second:.1f}")
    
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_database_query_performance(self, database_pool, clean_database):
        """Test database query performance under load"""
        from database.optimization import QueryOptimizer
        
        optimizer = QueryOptimizer(database_pool)
        
        # Create test data
        await self._create_test_data(database_pool, 1000)
        
        # Test concurrent queries
        num_queries = 100
        tasks = []
        
        for i in range(num_queries):
            task = self._execute_test_query(database_pool, i)
            tasks.append(task)
        
        # Execute all queries concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Calculate metrics
        successful_queries = [r for r in results if not isinstance(r, Exception)]
        failed_queries = len(results) - len(successful_queries)
        
        query_times = [r['execution_time'] for r in successful_queries]
        
        metrics = PerformanceMetrics(
            test_name="Database Query Performance",
            total_requests=num_queries,
            successful_requests=len(successful_queries),
            failed_requests=failed_queries,
            average_response_time=statistics.mean(query_times) if query_times else 0,
            min_response_time=min(query_times) if query_times else 0,
            max_response_time=max(query_times) if query_times else 0,
            p95_response_time=sorted(query_times)[int(len(query_times) * 0.95)] if query_times else 0,
            p99_response_time=sorted(query_times)[int(len(query_times) * 0.99)] if query_times else 0,
            requests_per_second=num_queries / total_time,
            error_rate=failed_queries / num_queries
        )
        
        # Assertions
        assert metrics.error_rate < 0.01  # Less than 1% error rate
        assert metrics.average_response_time < 0.1  # Less than 100ms average
        assert metrics.p95_response_time < 0.2  # 95% under 200ms
        
        print(f"Database Query Performance Results:")
        print(f"  Total Queries: {metrics.total_requests}")
        print(f"  Success Rate: {(1 - metrics.error_rate) * 100:.1f}%")
        print(f"  Average Query Time: {metrics.average_response_time:.3f}s")
        print(f"  P95 Query Time: {metrics.p95_response_time:.3f}s")
        print(f"  Queries/Second: {metrics.requests_per_second:.1f}")
    
    async def _create_test_data(self, database_pool, num_records: int):
        """Create test data for performance testing"""
        async with database_pool.acquire() as conn:
            # Create users
            for i in range(num_records):
                await conn.execute("""
                    INSERT INTO users (email, username, full_name, hashed_password, is_active)
                    VALUES ($1, $2, $3, $4, $5)
                """, f"perftest{i}@example.com", f"perftest{i}", f"Perf Test User {i}", 
                     "hashed_password", True)
    
    async def _execute_test_query(self, database_pool, query_id: int) -> Dict[str, Any]:
        """Execute a test database query"""
        start_time = time.time()
        
        try:
            async with database_pool.acquire() as conn:
                # Execute a complex query
                result = await conn.fetch("""
                    SELECT u.id, u.email, u.username, 
                           COUNT(a.id) as agent_count,
                           COUNT(w.id) as workflow_count
                    FROM users u
                    LEFT JOIN agents a ON u.id = a.user_id
                    LEFT JOIN agent_workflows w ON a.id = w.agent_id
                    WHERE u.email LIKE $1
                    GROUP BY u.id, u.email, u.username
                    ORDER BY u.id
                    LIMIT 10
                """, f"%perftest{query_id}%")
                
                execution_time = time.time() - start_time
                
                return {
                    'success': True,
                    'execution_time': execution_time,
                    'result_count': len(result)
                }
                
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'execution_time': execution_time,
                'error': str(e)
            }


class TestStressTesting:
    """Stress testing scenarios"""
    
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_high_concurrency_stress(self, auth_headers, load_test_config):
        """Test system behavior under high concurrency stress"""
        base_url = load_test_config['base_url']
        num_requests = 200
        
        load_test = LoadTestBase(base_url, auth_headers)
        
        # Create a mix of different request types
        tasks = []
        
        # 40% GET requests (read operations)
        for i in range(int(num_requests * 0.4)):
            task = load_test.make_request("GET", "/agents")
            tasks.append(task)
        
        # 30% POST requests (create operations)
        for i in range(int(num_requests * 0.3)):
            agent_data = {
                "name": f"Stress Test Agent {i}",
                "description": f"Agent created during stress test {i}",
                "config": {"model": "llama2:7b", "temperature": 0.7}
            }
            task = load_test.make_request("POST", "/agents", json=agent_data)
            tasks.append(task)
        
        # 20% PUT requests (update operations)
        for i in range(int(num_requests * 0.2)):
            update_data = {"name": f"Updated Stress Agent {i}"}
            task = load_test.make_request("PUT", f"/agents/{i+1}", json=update_data)
            tasks.append(task)
        
        # 10% DELETE requests (delete operations)
        for i in range(int(num_requests * 0.1)):
            task = load_test.make_request("DELETE", f"/agents/{i+100}")
            tasks.append(task)
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        load_test.results = [r for r in results if not isinstance(r, Exception)]
        
        # Calculate metrics
        metrics = load_test.calculate_metrics("High Concurrency Stress Test")
        
        # Assertions for stress test
        assert metrics.error_rate < 0.15  # Less than 15% error rate under stress
        assert metrics.average_response_time < 3.0  # Less than 3 seconds average
        assert metrics.p95_response_time < 8.0  # 95% under 8 seconds
        
        print(f"Stress Test Results:")
        print(f"  Total Requests: {metrics.total_requests}")
        print(f"  Success Rate: {(1 - metrics.error_rate) * 100:.1f}%")
        print(f"  Average Response Time: {metrics.average_response_time:.2f}s")
        print(f"  P95 Response Time: {metrics.p95_response_time:.2f}s")
        print(f"  Requests/Second: {metrics.requests_per_second:.1f}")
    
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_memory_leak_detection(self, database_pool, clean_database):
        """Test for memory leaks during extended operation"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Perform many operations to stress memory
        for iteration in range(10):
            # Create and destroy many objects
            await self._memory_stress_operation(database_pool, 100)
            
            # Force garbage collection
            gc.collect()
            
            # Check memory usage
            current_memory = process.memory_info().rss
            memory_increase = (current_memory - initial_memory) / 1024 / 1024  # MB
            
            print(f"Iteration {iteration + 1}: Memory increase: {memory_increase:.2f} MB")
            
            # Memory should not increase excessively
            assert memory_increase < 100  # Less than 100MB increase
        
        print("Memory leak test completed successfully")
    
    async def _memory_stress_operation(self, database_pool, num_operations: int):
        """Perform operations that could cause memory leaks"""
        tasks = []
        
        for i in range(num_operations):
            # Create complex queries with large result sets
            task = self._complex_query_operation(database_pool, i)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _complex_query_operation(self, database_pool, operation_id: int):
        """Execute complex query operation"""
        async with database_pool.acquire() as conn:
            # Execute a query that returns large result sets
            await conn.fetch("""
                SELECT 
                    u.id, u.email, u.username, u.full_name,
                    a.id as agent_id, a.name as agent_name, a.config,
                    w.id as workflow_id, w.name as workflow_name, w.steps,
                    kb.id as kb_id, kb.title, kb.content
                FROM users u
                LEFT JOIN agents a ON u.id = a.user_id
                LEFT JOIN agent_workflows w ON a.id = w.agent_id
                LEFT JOIN knowledge_base kb ON u.id = kb.user_id
                WHERE u.id = $1
            """, operation_id % 10 + 1)


class TestPerformanceMonitoring:
    """Test performance monitoring and alerting"""
    
    @pytest.mark.performance
    async def test_performance_metrics_collection(self, database_pool):
        """Test that performance metrics are properly collected"""
        from admin.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # Start monitoring
        await monitor.start_monitoring(interval=5)
        
        # Perform some operations
        await self._generate_load(database_pool)
        
        # Wait for metrics collection
        await asyncio.sleep(10)
        
        # Get performance summary
        summary = await monitor.get_performance_summary(hours=1)
        
        # Verify metrics were collected
        assert 'metrics_count' in summary
        assert summary['metrics_count']['system'] > 0
        assert summary['metrics_count']['application'] > 0
        assert summary['metrics_count']['database'] > 0
        
        # Stop monitoring
        await monitor.stop_monitoring()
        
        print(f"Performance monitoring test completed:")
        print(f"  System metrics: {summary['metrics_count']['system']}")
        print(f"  Application metrics: {summary['metrics_count']['application']}")
        print(f"  Database metrics: {summary['metrics_count']['database']}")
    
    async def _generate_load(self, database_pool):
        """Generate load for performance monitoring"""
        tasks = []
        
        for i in range(20):
            task = self._database_operation(database_pool, i)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _database_operation(self, database_pool, operation_id: int):
        """Perform database operation for load generation"""
        async with database_pool.acquire() as conn:
            await conn.fetchval("SELECT COUNT(*) FROM users")
            await conn.fetchval("SELECT COUNT(*) FROM agents")
            await conn.fetchval("SELECT COUNT(*) FROM agent_workflows")
    
    @pytest.mark.performance
    async def test_bottleneck_identification(self, database_pool):
        """Test bottleneck identification in performance monitoring"""
        from admin.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # Start monitoring
        await monitor.start_monitoring(interval=5)
        
        # Generate load that could create bottlenecks
        await self._generate_bottleneck_load(database_pool)
        
        # Wait for monitoring
        await asyncio.sleep(15)
        
        # Identify bottlenecks
        bottlenecks = await monitor.identify_bottlenecks()
        
        # Verify bottleneck identification works
        assert isinstance(bottlenecks, list)
        
        # Stop monitoring
        await monitor.stop_monitoring()
        
        print(f"Bottleneck identification test completed:")
        print(f"  Identified bottlenecks: {len(bottlenecks)}")
        for bottleneck in bottlenecks:
            print(f"    - {bottleneck['type']}: {bottleneck['description']}")
    
    async def _generate_bottleneck_load(self, database_pool):
        """Generate load that could create bottlenecks"""
        # Create slow queries
        async with database_pool.acquire() as conn:
            await conn.execute("SELECT pg_sleep(0.1)")  # 100ms delay
        
        # Create many concurrent operations
        tasks = []
        for i in range(50):
            task = self._intensive_operation(database_pool, i)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _intensive_operation(self, database_pool, operation_id: int):
        """Perform intensive operation"""
        async with database_pool.acquire() as conn:
            # Complex query with joins
            await conn.fetch("""
                SELECT 
                    u.id, u.email, u.username,
                    COUNT(a.id) as agent_count,
                    COUNT(w.id) as workflow_count,
                    COUNT(kb.id) as kb_count
                FROM users u
                LEFT JOIN agents a ON u.id = a.user_id
                LEFT JOIN agent_workflows w ON a.id = w.agent_id
                LEFT JOIN knowledge_base kb ON u.id = kb.user_id
                GROUP BY u.id, u.email, u.username
                ORDER BY u.id
            """)








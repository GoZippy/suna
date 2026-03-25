"""
Performance Monitoring System

This module provides comprehensive performance monitoring including:
- System resource monitoring
- Application performance metrics
- Bottleneck identification
- Performance alerts
- Historical performance tracking
"""

import asyncio
import logging
import psutil
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json
import redis
from prometheus_client import Counter, Histogram, Gauge, Summary
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io: Dict[str, float]
    load_average: List[float]


@dataclass
class ApplicationMetrics:
    """Application performance metrics"""
    timestamp: datetime
    request_count: int
    response_time_avg: float
    error_rate: float
    active_connections: int
    memory_usage: float


@dataclass
class DatabaseMetrics:
    """Database performance metrics"""
    timestamp: datetime
    query_count: int
    slow_query_count: int
    connection_count: int
    cache_hit_rate: float
    avg_query_time: float


@dataclass
class PerformanceAlert:
    """Performance alert"""
    timestamp: datetime
    alert_type: str
    severity: str
    message: str
    metrics: Dict[str, Any]
    threshold: float


class PerformanceMonitor:
    """Comprehensive performance monitoring system"""
    
    def __init__(self, redis_url: str = "redis://localhost:6391"):
        self.redis_url = redis_url
        self.redis_client = redis.from_url(redis_url)
        
        # Metrics storage
        self.system_metrics: deque = deque(maxlen=1000)
        self.application_metrics: deque = deque(maxlen=1000)
        self.database_metrics: deque = deque(maxlen=1000)
        self.alerts: deque = deque(maxlen=100)
        
        # Performance thresholds
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'response_time_ms': 1000.0,
            'error_rate_percent': 5.0,
            'slow_query_percent': 10.0
        }
        
        # Prometheus metrics
        self._setup_prometheus_metrics()
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task = None
        
        # Alert callbacks
        self.alert_callbacks: List[Callable] = []
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        # System metrics
        self.cpu_gauge = Gauge('suna_cpu_percent', 'CPU usage percentage')
        self.memory_gauge = Gauge('suna_memory_percent', 'Memory usage percentage')
        self.disk_gauge = Gauge('suna_disk_percent', 'Disk usage percentage')
        self.load_gauge = Gauge('suna_load_average', 'System load average')
        
        # Application metrics
        self.request_counter = Counter('suna_requests_total', 'Total requests')
        self.response_time_histogram = Histogram('suna_response_time_seconds', 'Response time')
        self.error_counter = Counter('suna_errors_total', 'Total errors')
        self.active_connections_gauge = Gauge('suna_active_connections', 'Active connections')
        
        # Database metrics
        self.query_counter = Counter('suna_queries_total', 'Total database queries')
        self.slow_query_counter = Counter('suna_slow_queries_total', 'Slow queries')
        self.cache_hit_rate_gauge = Gauge('suna_cache_hit_rate', 'Cache hit rate')
    
    async def start_monitoring(self, interval: int = 30):
        """Start performance monitoring"""
        if self.is_monitoring:
            logger.warning("Performance monitoring is already running")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval)
        )
        logger.info(f"Performance monitoring started with {interval}s interval")
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self, interval: int):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Collect metrics
                system_metrics = await self._collect_system_metrics()
                application_metrics = await self._collect_application_metrics()
                database_metrics = await self._collect_database_metrics()
                
                # Store metrics
                self.system_metrics.append(system_metrics)
                self.application_metrics.append(application_metrics)
                self.database_metrics.append(database_metrics)
                
                # Update Prometheus metrics
                self._update_prometheus_metrics(system_metrics, application_metrics, database_metrics)
                
                # Check for alerts
                await self._check_alerts(system_metrics, application_metrics, database_metrics)
                
                # Store in Redis for persistence
                await self._store_metrics_redis(system_metrics, application_metrics, database_metrics)
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            
            # Network I/O
            network_io = psutil.net_io_counters()
            network_metrics = {
                'bytes_sent': network_io.bytes_sent,
                'bytes_recv': network_io.bytes_recv,
                'packets_sent': network_io.packets_sent,
                'packets_recv': network_io.packets_recv
            }
            
            # Load average
            load_average = list(psutil.getloadavg())
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                network_io=network_metrics,
                load_average=load_average
            )
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_usage_percent=0.0,
                network_io={},
                load_average=[0.0, 0.0, 0.0]
            )
    
    async def _collect_application_metrics(self) -> ApplicationMetrics:
        """Collect application performance metrics"""
        try:
            # Get metrics from Redis (assuming they're stored there)
            request_count = int(await self.redis_client.get('app:request_count') or 0)
            response_time_avg = float(await self.redis_client.get('app:response_time_avg') or 0.0)
            error_count = int(await self.redis_client.get('app:error_count') or 0)
            active_connections = int(await self.redis_client.get('app:active_connections') or 0)
            
            # Calculate error rate
            total_requests = request_count + error_count
            error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0.0
            
            # Memory usage for current process
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            
            return ApplicationMetrics(
                timestamp=datetime.now(),
                request_count=request_count,
                response_time_avg=response_time_avg,
                error_rate=error_rate,
                active_connections=active_connections,
                memory_usage=memory_usage
            )
            
        except Exception as e:
            logger.error(f"Failed to collect application metrics: {e}")
            return ApplicationMetrics(
                timestamp=datetime.now(),
                request_count=0,
                response_time_avg=0.0,
                error_rate=0.0,
                active_connections=0,
                memory_usage=0.0
            )
    
    async def _collect_database_metrics(self) -> DatabaseMetrics:
        """Collect database performance metrics"""
        try:
            # Get metrics from Redis
            query_count = int(await self.redis_client.get('db:query_count') or 0)
            slow_query_count = int(await self.redis_client.get('db:slow_query_count') or 0)
            connection_count = int(await self.redis_client.get('db:connection_count') or 0)
            cache_hits = int(await self.redis_client.get('cache:hits') or 0)
            cache_misses = int(await self.redis_client.get('cache:misses') or 0)
            avg_query_time = float(await self.redis_client.get('db:avg_query_time') or 0.0)
            
            # Calculate cache hit rate
            total_cache_requests = cache_hits + cache_misses
            cache_hit_rate = (cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0.0
            
            return DatabaseMetrics(
                timestamp=datetime.now(),
                query_count=query_count,
                slow_query_count=slow_query_count,
                connection_count=connection_count,
                cache_hit_rate=cache_hit_rate,
                avg_query_time=avg_query_time
            )
            
        except Exception as e:
            logger.error(f"Failed to collect database metrics: {e}")
            return DatabaseMetrics(
                timestamp=datetime.now(),
                query_count=0,
                slow_query_count=0,
                connection_count=0,
                cache_hit_rate=0.0,
                avg_query_time=0.0
            )
    
    def _update_prometheus_metrics(self, system: SystemMetrics, app: ApplicationMetrics, db: DatabaseMetrics):
        """Update Prometheus metrics"""
        try:
            # System metrics
            self.cpu_gauge.set(system.cpu_percent)
            self.memory_gauge.set(system.memory_percent)
            self.disk_gauge.set(system.disk_usage_percent)
            self.load_gauge.set(system.load_average[0])
            
            # Application metrics
            self.request_counter.inc(app.request_count)
            self.response_time_histogram.observe(app.response_time_avg / 1000)  # Convert to seconds
            self.error_counter.inc(int(app.error_rate * app.request_count / 100))
            self.active_connections_gauge.set(app.active_connections)
            
            # Database metrics
            self.query_counter.inc(db.query_count)
            self.slow_query_counter.inc(db.slow_query_count)
            self.cache_hit_rate_gauge.set(db.cache_hit_rate)
            
        except Exception as e:
            logger.error(f"Failed to update Prometheus metrics: {e}")
    
    async def _check_alerts(self, system: SystemMetrics, app: ApplicationMetrics, db: DatabaseMetrics):
        """Check for performance alerts"""
        alerts = []
        
        # CPU alert
        if system.cpu_percent > self.thresholds['cpu_percent']:
            alerts.append(PerformanceAlert(
                timestamp=datetime.now(),
                alert_type='high_cpu',
                severity='warning',
                message=f"CPU usage is high: {system.cpu_percent:.1f}%",
                metrics={'cpu_percent': system.cpu_percent},
                threshold=self.thresholds['cpu_percent']
            ))
        
        # Memory alert
        if system.memory_percent > self.thresholds['memory_percent']:
            alerts.append(PerformanceAlert(
                timestamp=datetime.now(),
                alert_type='high_memory',
                severity='warning',
                message=f"Memory usage is high: {system.memory_percent:.1f}%",
                metrics={'memory_percent': system.memory_percent},
                threshold=self.thresholds['memory_percent']
            ))
        
        # Disk alert
        if system.disk_usage_percent > self.thresholds['disk_usage_percent']:
            alerts.append(PerformanceAlert(
                timestamp=datetime.now(),
                alert_type='high_disk',
                severity='critical',
                message=f"Disk usage is high: {system.disk_usage_percent:.1f}%",
                metrics={'disk_usage_percent': system.disk_usage_percent},
                threshold=self.thresholds['disk_usage_percent']
            ))
        
        # Response time alert
        if app.response_time_avg > self.thresholds['response_time_ms']:
            alerts.append(PerformanceAlert(
                timestamp=datetime.now(),
                alert_type='slow_response',
                severity='warning',
                message=f"Response time is slow: {app.response_time_avg:.1f}ms",
                metrics={'response_time_avg': app.response_time_avg},
                threshold=self.thresholds['response_time_ms']
            ))
        
        # Error rate alert
        if app.error_rate > self.thresholds['error_rate_percent']:
            alerts.append(PerformanceAlert(
                timestamp=datetime.now(),
                alert_type='high_error_rate',
                severity='critical',
                message=f"Error rate is high: {app.error_rate:.1f}%",
                metrics={'error_rate': app.error_rate},
                threshold=self.thresholds['error_rate_percent']
            ))
        
        # Store alerts
        for alert in alerts:
            self.alerts.append(alert)
            await self._trigger_alert_callbacks(alert)
    
    async def _trigger_alert_callbacks(self, alert: PerformanceAlert):
        """Trigger alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    async def _store_metrics_redis(self, system: SystemMetrics, app: ApplicationMetrics, db: DatabaseMetrics):
        """Store metrics in Redis for persistence"""
        try:
            timestamp = datetime.now().isoformat()
            
            # Store system metrics
            await self.redis_client.setex(
                f"metrics:system:{timestamp}",
                86400,  # 24 hours TTL
                json.dumps(asdict(system))
            )
            
            # Store application metrics
            await self.redis_client.setex(
                f"metrics:app:{timestamp}",
                86400,
                json.dumps(asdict(app))
            )
            
            # Store database metrics
            await self.redis_client.setex(
                f"metrics:db:{timestamp}",
                86400,
                json.dumps(asdict(db))
            )
            
        except Exception as e:
            logger.error(f"Failed to store metrics in Redis: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """Add alert callback function"""
        self.alert_callbacks.append(callback)
    
    async def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Filter metrics by time
            recent_system = [m for m in self.system_metrics if m.timestamp > cutoff_time]
            recent_app = [m for m in self.application_metrics if m.timestamp > cutoff_time]
            recent_db = [m for m in self.database_metrics if m.timestamp > cutoff_time]
            
            if not recent_system or not recent_app or not recent_db:
                return {'error': 'No metrics available for the specified time range'}
            
            # Calculate averages
            avg_cpu = sum(m.cpu_percent for m in recent_system) / len(recent_system)
            avg_memory = sum(m.memory_percent for m in recent_system) / len(recent_system)
            avg_response_time = sum(m.response_time_avg for m in recent_app) / len(recent_app)
            avg_error_rate = sum(m.error_rate for m in recent_app) / len(recent_app)
            avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_db) / len(recent_db)
            
            # Get peak values
            peak_cpu = max(m.cpu_percent for m in recent_system)
            peak_memory = max(m.memory_percent for m in recent_system)
            peak_response_time = max(m.response_time_avg for m in recent_app)
            
            return {
                'time_range_hours': hours,
                'metrics_count': {
                    'system': len(recent_system),
                    'application': len(recent_app),
                    'database': len(recent_db)
                },
                'averages': {
                    'cpu_percent': round(avg_cpu, 2),
                    'memory_percent': round(avg_memory, 2),
                    'response_time_ms': round(avg_response_time, 2),
                    'error_rate_percent': round(avg_error_rate, 2),
                    'cache_hit_rate_percent': round(avg_cache_hit_rate, 2)
                },
                'peaks': {
                    'cpu_percent': round(peak_cpu, 2),
                    'memory_percent': round(peak_memory, 2),
                    'response_time_ms': round(peak_response_time, 2)
                },
                'alerts_count': len([a for a in self.alerts if a.timestamp > cutoff_time])
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {'error': str(e)}
    
    async def identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        try:
            # Get recent metrics
            recent_system = list(self.system_metrics)[-10:]  # Last 10 measurements
            recent_app = list(self.application_metrics)[-10:]
            recent_db = list(self.database_metrics)[-10:]
            
            if not recent_system or not recent_app or not recent_db:
                return bottlenecks
            
            # Check CPU bottleneck
            avg_cpu = sum(m.cpu_percent for m in recent_system) / len(recent_system)
            if avg_cpu > 70:
                bottlenecks.append({
                    'type': 'cpu',
                    'severity': 'high' if avg_cpu > 85 else 'medium',
                    'description': f'High CPU usage: {avg_cpu:.1f}%',
                    'recommendation': 'Consider scaling up CPU resources or optimizing CPU-intensive operations'
                })
            
            # Check memory bottleneck
            avg_memory = sum(m.memory_percent for m in recent_system) / len(recent_system)
            if avg_memory > 80:
                bottlenecks.append({
                    'type': 'memory',
                    'severity': 'high' if avg_memory > 90 else 'medium',
                    'description': f'High memory usage: {avg_memory:.1f}%',
                    'recommendation': 'Consider increasing memory or optimizing memory usage'
                })
            
            # Check response time bottleneck
            avg_response_time = sum(m.response_time_avg for m in recent_app) / len(recent_app)
            if avg_response_time > 500:
                bottlenecks.append({
                    'type': 'response_time',
                    'severity': 'high' if avg_response_time > 1000 else 'medium',
                    'description': f'Slow response time: {avg_response_time:.1f}ms',
                    'recommendation': 'Optimize database queries, add caching, or scale application servers'
                })
            
            # Check cache hit rate bottleneck
            avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_db) / len(recent_db)
            if avg_cache_hit_rate < 70:
                bottlenecks.append({
                    'type': 'cache',
                    'severity': 'medium',
                    'description': f'Low cache hit rate: {avg_cache_hit_rate:.1f}%',
                    'recommendation': 'Optimize cache strategy and increase cache size'
                })
            
            # Check error rate bottleneck
            avg_error_rate = sum(m.error_rate for m in recent_app) / len(recent_app)
            if avg_error_rate > 2:
                bottlenecks.append({
                    'type': 'error_rate',
                    'severity': 'high' if avg_error_rate > 5 else 'medium',
                    'description': f'High error rate: {avg_error_rate:.1f}%',
                    'recommendation': 'Investigate and fix application errors'
                })
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"Failed to identify bottlenecks: {e}")
            return []
    
    async def get_historical_metrics(self, metric_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical metrics from Redis"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            metrics = []
            
            # Get keys from Redis
            pattern = f"metrics:{metric_type}:*"
            keys = await self.redis_client.keys(pattern)
            
            for key in keys:
                try:
                    data = await self.redis_client.get(key)
                    if data:
                        metric_data = json.loads(data)
                        metric_time = datetime.fromisoformat(metric_data['timestamp'])
                        
                        if metric_time > cutoff_time:
                            metrics.append(metric_data)
                except Exception as e:
                    logger.error(f"Failed to parse metric data: {e}")
            
            # Sort by timestamp
            metrics.sort(key=lambda x: x['timestamp'])
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get historical metrics: {e}")
            return []
    
    async def cleanup_old_metrics(self, days: int = 7):
        """Clean up old metrics data"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # Clean up in-memory metrics
            self.system_metrics = deque(
                [m for m in self.system_metrics if m.timestamp > cutoff_time],
                maxlen=1000
            )
            self.application_metrics = deque(
                [m for m in self.application_metrics if m.timestamp > cutoff_time],
                maxlen=1000
            )
            self.database_metrics = deque(
                [m for m in self.database_metrics if m.timestamp > cutoff_time],
                maxlen=1000
            )
            
            # Clean up alerts
            self.alerts = deque(
                [a for a in self.alerts if a.timestamp > cutoff_time],
                maxlen=100
            )
            
            logger.info(f"Cleaned up metrics older than {days} days")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
    
    async def cleanup(self):
        """Cleanup monitoring resources"""
        try:
            await self.stop_monitoring()
            logger.info("Performance monitor cleanup completed")
        except Exception as e:
            logger.error(f"Failed to cleanup performance monitor: {e}")








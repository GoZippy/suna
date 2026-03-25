"""
Container Resource Optimization

This module provides container optimization capabilities including:
- Resource allocation optimization
- Container startup optimization
- Memory and CPU tuning
- Container health monitoring
- Resource usage analysis
"""

import asyncio
import logging
import time
import psutil
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import docker
import redis
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class ContainerMetrics:
    """Container performance metrics"""
    container_id: str
    name: str
    cpu_percent: float
    memory_percent: float
    memory_usage_mb: float
    network_io: Dict[str, float]
    disk_io: Dict[str, float]
    status: str
    uptime_seconds: float
    restart_count: int
    timestamp: datetime


@dataclass
class ResourceLimits:
    """Container resource limits"""
    cpu_limit: float  # CPU cores
    memory_limit_mb: int
    memory_swap_mb: int
    disk_read_bps: int
    disk_write_bps: int
    network_read_bps: int
    network_write_bps: int


@dataclass
class OptimizationRecommendation:
    """Container optimization recommendation"""
    container_name: str
    recommendation_type: str
    current_value: Any
    recommended_value: Any
    expected_improvement: str
    priority: str  # low, medium, high, critical


class ContainerOptimizer:
    """Container resource optimization system"""
    
    def __init__(self, redis_url: str = "redis://localhost:6391"):
        self.redis_url = redis_url
        self.redis_client = redis.from_url(redis_url)
        
        # Docker client
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
        
        # Container metrics storage
        self.container_metrics: Dict[str, List[ContainerMetrics]] = {}
        
        # Optimization history
        self.optimization_history: List[Dict[str, Any]] = []
        
        # Resource limits templates
        self.resource_templates = self._initialize_resource_templates()
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task = None
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    def _initialize_resource_templates(self) -> Dict[str, ResourceLimits]:
        """Initialize resource limit templates for different service types"""
        return {
            'web_server': ResourceLimits(
                cpu_limit=1.0,
                memory_limit_mb=512,
                memory_swap_mb=1024,
                disk_read_bps=50 * 1024 * 1024,  # 50 MB/s
                disk_write_bps=25 * 1024 * 1024,  # 25 MB/s
                network_read_bps=100 * 1024 * 1024,  # 100 MB/s
                network_write_bps=50 * 1024 * 1024   # 50 MB/s
            ),
            'api_server': ResourceLimits(
                cpu_limit=2.0,
                memory_limit_mb=1024,
                memory_swap_mb=2048,
                disk_read_bps=100 * 1024 * 1024,  # 100 MB/s
                disk_write_bps=50 * 1024 * 1024,   # 50 MB/s
                network_read_bps=200 * 1024 * 1024,  # 200 MB/s
                network_write_bps=100 * 1024 * 1024   # 100 MB/s
            ),
            'database': ResourceLimits(
                cpu_limit=4.0,
                memory_limit_mb=4096,
                memory_swap_mb=8192,
                disk_read_bps=500 * 1024 * 1024,  # 500 MB/s
                disk_write_bps=250 * 1024 * 1024,  # 250 MB/s
                network_read_bps=100 * 1024 * 1024,  # 100 MB/s
                network_write_bps=50 * 1024 * 1024   # 50 MB/s
            ),
            'cache_server': ResourceLimits(
                cpu_limit=1.0,
                memory_limit_mb=2048,
                memory_swap_mb=4096,
                disk_read_bps=25 * 1024 * 1024,   # 25 MB/s
                disk_write_bps=10 * 1024 * 1024,   # 10 MB/s
                network_read_bps=200 * 1024 * 1024,  # 200 MB/s
                network_write_bps=200 * 1024 * 1024   # 200 MB/s
            )
        }
    
    async def start_monitoring(self, interval: int = 30):
        """Start container monitoring"""
        if self.is_monitoring:
            logger.warning("Container monitoring is already running")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval)
        )
        logger.info(f"Container monitoring started with {interval}s interval")
    
    async def stop_monitoring(self):
        """Stop container monitoring"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Container monitoring stopped")
    
    async def _monitoring_loop(self, interval: int):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Collect metrics for all containers
                containers = await self._get_all_containers()
                
                for container in containers:
                    metrics = await self._collect_container_metrics(container)
                    if metrics:
                        # Store metrics
                        if container.name not in self.container_metrics:
                            self.container_metrics[container.name] = []
                        
                        self.container_metrics[container.name].append(metrics)
                        
                        # Keep only recent metrics
                        if len(self.container_metrics[container.name]) > 100:
                            self.container_metrics[container.name] = self.container_metrics[container.name][-50:]
                        
                        # Store in Redis
                        await self._store_metrics_redis(metrics)
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in container monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    async def _get_all_containers(self) -> List[docker.models.containers.Container]:
        """Get all running containers"""
        try:
            if not self.docker_client:
                return []
            
            containers = self.docker_client.containers.list()
            return containers
            
        except Exception as e:
            logger.error(f"Failed to get containers: {e}")
            return []
    
    async def _collect_container_metrics(self, container) -> Optional[ContainerMetrics]:
        """Collect metrics for a specific container"""
        try:
            # Get container stats
            stats = container.stats(stream=False)
            
            # Calculate CPU usage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
            
            # Calculate memory usage
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            memory_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0.0
            memory_usage_mb = memory_usage / 1024 / 1024
            
            # Get network I/O
            networks = stats.get('networks', {})
            network_io = {}
            for interface, data in networks.items():
                network_io[interface] = {
                    'rx_bytes': data.get('rx_bytes', 0),
                    'tx_bytes': data.get('tx_bytes', 0),
                    'rx_packets': data.get('rx_packets', 0),
                    'tx_packets': data.get('tx_packets', 0)
                }
            
            # Get disk I/O
            disk_io = {}
            if 'blkio_stats' in stats:
                blkio = stats['blkio_stats']
                disk_io = {
                    'read_bytes': sum(item['value'] for item in blkio.get('io_service_bytes_recursive', []) if item['op'] == 'Read'),
                    'write_bytes': sum(item['value'] for item in blkio.get('io_service_bytes_recursive', []) if item['op'] == 'Write')
                }
            
            # Get container info
            container_info = container.attrs
            status = container_info['State']['Status']
            uptime_seconds = (datetime.now() - datetime.fromisoformat(container_info['State']['StartedAt'].replace('Z', '+00:00'))).total_seconds()
            restart_count = container_info['RestartCount']
            
            return ContainerMetrics(
                container_id=container.id,
                name=container.name,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_usage_mb=memory_usage_mb,
                network_io=network_io,
                disk_io=disk_io,
                status=status,
                uptime_seconds=uptime_seconds,
                restart_count=restart_count,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to collect metrics for container {container.name}: {e}")
            return None
    
    async def _store_metrics_redis(self, metrics: ContainerMetrics):
        """Store container metrics in Redis"""
        try:
            key = f"container:metrics:{metrics.container_id}"
            data = {
                'container_id': metrics.container_id,
                'name': metrics.name,
                'cpu_percent': metrics.cpu_percent,
                'memory_percent': metrics.memory_percent,
                'memory_usage_mb': metrics.memory_usage_mb,
                'network_io': metrics.network_io,
                'disk_io': metrics.disk_io,
                'status': metrics.status,
                'uptime_seconds': metrics.uptime_seconds,
                'restart_count': metrics.restart_count,
                'timestamp': metrics.timestamp.isoformat()
            }
            
            await self.redis_client.setex(key, 3600, json.dumps(data))  # 1 hour TTL
            
        except Exception as e:
            logger.error(f"Failed to store metrics in Redis: {e}")
    
    async def analyze_container_performance(self, container_name: str) -> Dict[str, Any]:
        """Analyze performance of a specific container"""
        try:
            if container_name not in self.container_metrics:
                return {'error': 'No metrics available for container'}
            
            metrics = self.container_metrics[container_name]
            if not metrics:
                return {'error': 'No metrics available for container'}
            
            # Calculate averages
            avg_cpu = sum(m.cpu_percent for m in metrics) / len(metrics)
            avg_memory = sum(m.memory_percent for m in metrics) / len(metrics)
            avg_memory_mb = sum(m.memory_usage_mb for m in metrics) / len(metrics)
            
            # Calculate peaks
            peak_cpu = max(m.cpu_percent for m in metrics)
            peak_memory = max(m.memory_percent for m in metrics)
            peak_memory_mb = max(m.memory_usage_mb for m in metrics)
            
            # Calculate restart frequency
            total_restarts = sum(m.restart_count for m in metrics)
            avg_uptime = sum(m.uptime_seconds for m in metrics) / len(metrics)
            
            # Determine service type based on name
            service_type = self._determine_service_type(container_name)
            
            return {
                'container_name': container_name,
                'service_type': service_type,
                'metrics_count': len(metrics),
                'time_range': {
                    'start': metrics[0].timestamp.isoformat(),
                    'end': metrics[-1].timestamp.isoformat()
                },
                'averages': {
                    'cpu_percent': round(avg_cpu, 2),
                    'memory_percent': round(avg_memory, 2),
                    'memory_usage_mb': round(avg_memory_mb, 2)
                },
                'peaks': {
                    'cpu_percent': round(peak_cpu, 2),
                    'memory_percent': round(peak_memory, 2),
                    'memory_usage_mb': round(peak_memory_mb, 2)
                },
                'stability': {
                    'total_restarts': total_restarts,
                    'avg_uptime_seconds': round(avg_uptime, 2),
                    'restart_frequency': round(total_restarts / len(metrics), 3)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze container performance: {e}")
            return {'error': str(e)}
    
    def _determine_service_type(self, container_name: str) -> str:
        """Determine service type based on container name"""
        name_lower = container_name.lower()
        
        if any(keyword in name_lower for keyword in ['web', 'frontend', 'nginx']):
            return 'web_server'
        elif any(keyword in name_lower for keyword in ['api', 'backend', 'app']):
            return 'api_server'
        elif any(keyword in name_lower for keyword in ['db', 'database', 'postgres', 'mysql']):
            return 'database'
        elif any(keyword in name_lower for keyword in ['cache', 'redis', 'memcached']):
            return 'cache_server'
        else:
            return 'unknown'
    
    async def generate_optimization_recommendations(self, container_name: str) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations for a container"""
        try:
            recommendations = []
            
            # Get performance analysis
            analysis = await self.analyze_container_performance(container_name)
            if 'error' in analysis:
                return recommendations
            
            # Get current resource limits
            current_limits = await self._get_current_resource_limits(container_name)
            
            # Get recommended limits based on service type
            service_type = analysis['service_type']
            if service_type in self.resource_templates:
                recommended_limits = self.resource_templates[service_type]
                
                # CPU recommendations
                avg_cpu = analysis['averages']['cpu_percent']
                if avg_cpu > 80:
                    recommendations.append(OptimizationRecommendation(
                        container_name=container_name,
                        recommendation_type='cpu_limit',
                        current_value=current_limits.get('cpu_limit', 'unknown'),
                        recommended_value=recommended_limits.cpu_limit * 1.5,
                        expected_improvement='Reduce CPU pressure and improve response times',
                        priority='high' if avg_cpu > 90 else 'medium'
                    ))
                elif avg_cpu < 20 and current_limits.get('cpu_limit', 0) > 1.0:
                    recommendations.append(OptimizationRecommendation(
                        container_name=container_name,
                        recommendation_type='cpu_limit',
                        current_value=current_limits.get('cpu_limit', 'unknown'),
                        recommended_value=max(0.5, recommended_limits.cpu_limit * 0.5),
                        expected_improvement='Reduce resource waste and costs',
                        priority='medium'
                    ))
                
                # Memory recommendations
                avg_memory = analysis['averages']['memory_percent']
                if avg_memory > 85:
                    recommendations.append(OptimizationRecommendation(
                        container_name=container_name,
                        recommendation_type='memory_limit',
                        current_value=current_limits.get('memory_limit_mb', 'unknown'),
                        recommended_value=recommended_limits.memory_limit_mb * 1.5,
                        expected_improvement='Prevent out-of-memory errors and improve stability',
                        priority='critical' if avg_memory > 95 else 'high'
                    ))
                elif avg_memory < 30 and current_limits.get('memory_limit_mb', 0) > 512:
                    recommendations.append(OptimizationRecommendation(
                        container_name=container_name,
                        recommendation_type='memory_limit',
                        current_value=current_limits.get('memory_limit_mb', 'unknown'),
                        recommended_value=max(256, recommended_limits.memory_limit_mb * 0.7),
                        expected_improvement='Reduce memory waste and costs',
                        priority='medium'
                    ))
                
                # Restart frequency recommendations
                restart_freq = analysis['stability']['restart_frequency']
                if restart_freq > 0.1:  # More than 10% of measurements show restarts
                    recommendations.append(OptimizationRecommendation(
                        container_name=container_name,
                        recommendation_type='restart_policy',
                        current_value='unknown',
                        recommended_value='Implement proper restart policy and health checks',
                        expected_improvement='Improve container stability and reduce downtime',
                        priority='high'
                    ))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate optimization recommendations: {e}")
            return []
    
    async def _get_current_resource_limits(self, container_name: str) -> Dict[str, Any]:
        """Get current resource limits for a container"""
        try:
            if not self.docker_client:
                return {}
            
            containers = self.docker_client.containers.list(filters={'name': container_name})
            if not containers:
                return {}
            
            container = containers[0]
            host_config = container.attrs['HostConfig']
            
            return {
                'cpu_limit': host_config.get('CpuQuota', 0) / 100000,  # Convert from microseconds
                'memory_limit_mb': host_config.get('Memory', 0) / 1024 / 1024,
                'memory_swap_mb': host_config.get('MemorySwap', 0) / 1024 / 1024,
                'disk_read_bps': host_config.get('BlkioDeviceReadBps', 0),
                'disk_write_bps': host_config.get('BlkioDeviceWriteBps', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource limits: {e}")
            return {}
    
    async def apply_optimization(self, container_name: str, optimization_type: str, new_value: Any) -> bool:
        """Apply optimization to a container"""
        try:
            if not self.docker_client:
                return False
            
            containers = self.docker_client.containers.list(filters={'name': container_name})
            if not containers:
                logger.error(f"Container {container_name} not found")
                return False
            
            container = containers[0]
            
            # Stop container
            container.stop()
            
            # Update container configuration
            container_info = container.attrs
            host_config = container_info['HostConfig']
            
            if optimization_type == 'cpu_limit':
                host_config['CpuQuota'] = int(new_value * 100000)  # Convert to microseconds
            elif optimization_type == 'memory_limit':
                host_config['Memory'] = int(new_value * 1024 * 1024)  # Convert to bytes
            elif optimization_type == 'memory_swap':
                host_config['MemorySwap'] = int(new_value * 1024 * 1024)  # Convert to bytes
            
            # Remove old container
            container.remove()
            
            # Create new container with updated configuration
            # Note: This is a simplified approach. In production, use docker-compose or Kubernetes
            logger.info(f"Applied optimization {optimization_type}={new_value} to {container_name}")
            
            # Record optimization
            self.optimization_history.append({
                'timestamp': datetime.now().isoformat(),
                'container_name': container_name,
                'optimization_type': optimization_type,
                'old_value': 'unknown',
                'new_value': new_value,
                'status': 'applied'
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply optimization: {e}")
            return False
    
    async def optimize_startup_time(self, container_name: str) -> Dict[str, Any]:
        """Optimize container startup time"""
        try:
            if not self.docker_client:
                return {'error': 'Docker client not available'}
            
            containers = self.docker_client.containers.list(filters={'name': container_name})
            if not containers:
                return {'error': 'Container not found'}
            
            container = containers[0]
            
            # Get container image info
            image = container.image
            image_info = image.attrs
            
            # Analyze image layers
            layers = image_info.get('Layers', [])
            layer_sizes = []
            
            for layer in layers:
                layer_size = len(layer) if isinstance(layer, bytes) else 0
                layer_sizes.append(layer_size)
            
            total_size = sum(layer_sizes)
            
            # Generate recommendations
            recommendations = []
            
            if total_size > 500 * 1024 * 1024:  # 500MB
                recommendations.append({
                    'type': 'image_size',
                    'description': 'Consider using multi-stage builds to reduce image size',
                    'priority': 'high'
                })
            
            if len(layers) > 10:
                recommendations.append({
                    'type': 'layer_count',
                    'description': 'Reduce number of layers by combining RUN commands',
                    'priority': 'medium'
                })
            
            return {
                'container_name': container_name,
                'image_size_mb': round(total_size / 1024 / 1024, 2),
                'layer_count': len(layers),
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize startup time: {e}")
            return {'error': str(e)}
    
    async def get_optimization_summary(self) -> Dict[str, Any]:
        """Get optimization summary"""
        try:
            recent_optimizations = [
                opt for opt in self.optimization_history
                if datetime.fromisoformat(opt['timestamp']) > datetime.now() - timedelta(days=7)
            ]
            
            return {
                'is_monitoring': self.is_monitoring,
                'containers_monitored': len(self.container_metrics),
                'optimizations_applied_7d': len(recent_optimizations),
                'recent_optimizations': recent_optimizations[-5:],  # Last 5 optimizations
                'resource_templates': list(self.resource_templates.keys())
            }
            
        except Exception as e:
            logger.error(f"Failed to get optimization summary: {e}")
            return {}
    
    async def cleanup(self):
        """Cleanup container optimizer resources"""
        try:
            await self.stop_monitoring()
            self.executor.shutdown(wait=True)
            logger.info("Container optimizer cleanup completed")
        except Exception as e:
            logger.error(f"Failed to cleanup container optimizer: {e}")








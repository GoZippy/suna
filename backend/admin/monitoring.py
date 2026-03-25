"""
System monitoring and health check service
"""

import asyncio
import aiohttp
import psutil
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from .models import (
    SystemMetrics, ServiceHealth, ApplicationMetrics, DatabaseMetrics,
    SystemHealth, ServiceStatus, Alert, AlertLevel
)
from . import SERVICE_CONFIG, ADMIN_CONFIG
from ..database import get_db


class SystemMonitor:
    """System monitoring service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.metrics_cache = {}
        self.last_check = {}
    
    async def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        # Network I/O
        network = psutil.net_io_counters()
        
        # Load average
        load_avg = psutil.getloadavg()
        
        # Uptime
        uptime = time.time() - psutil.boot_time()
        
        return SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_usage_percent=cpu_percent,
            memory_usage_percent=memory_percent,
            disk_usage_percent=disk_percent,
            network_rx_bytes=network.bytes_recv,
            network_tx_bytes=network.bytes_sent,
            load_average_1m=load_avg[0],
            load_average_5m=load_avg[1],
            load_average_15m=load_avg[2],
            uptime_seconds=int(uptime)
        )
    
    async def check_service_health(self, service_id: str) -> ServiceHealth:
        """Check health of a specific service"""
        
        service_config = SERVICE_CONFIG['services'].get(service_id)
        if not service_config:
            return ServiceHealth(
                service_name="Unknown",
                service_id=service_id,
                status=ServiceStatus.UNKNOWN,
                port=0,
                last_check=datetime.utcnow(),
                error_message="Service not configured"
            )
        
        start_time = time.time()
        status = ServiceStatus.UNKNOWN
        error_message = None
        response_time_ms = None
        version = None
        
        try:
            # Check if port is listening
            if not self._is_port_listening(service_config['port']):
                status = ServiceStatus.DOWN
                error_message = f"Port {service_config['port']} not listening"
            else:
                # Check health endpoint if available
                if service_config['health_endpoint']:
                    health_url = f"http://localhost:{service_config['port']}{service_config['health_endpoint']}"
                    
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                        async with session.get(health_url) as response:
                            if response.status == 200:
                                status = ServiceStatus.HEALTHY
                                response_time_ms = (time.time() - start_time) * 1000
                                
                                # Try to get version from response
                                try:
                                    data = await response.json()
                                    version = data.get('version')
                                except:
                                    pass
                            else:
                                status = ServiceStatus.DEGRADED
                                error_message = f"Health check returned {response.status}"
                else:
                    # No health endpoint, just check if port is listening
                    status = ServiceStatus.HEALTHY
                    response_time_ms = (time.time() - start_time) * 1000
                
        except Exception as e:
            status = ServiceStatus.DOWN
            error_message = str(e)
        
        return ServiceHealth(
            service_name=service_config['name'],
            service_id=service_id,
            status=status,
            port=service_config['port'],
            health_endpoint=service_config['health_endpoint'],
            response_time_ms=response_time_ms,
            last_check=datetime.utcnow(),
            version=version,
            error_message=error_message
        )
    
    async def check_all_services(self) -> List[ServiceHealth]:
        """Check health of all services"""
        
        tasks = []
        for service_id in SERVICE_CONFIG['services'].keys():
            tasks.append(self.check_service_health(service_id))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        services = []
        for result in results:
            if isinstance(result, ServiceHealth):
                services.append(result)
            else:
                # Handle exception
                services.append(ServiceHealth(
                    service_name="Error",
                    service_id="error",
                    status=ServiceStatus.UNKNOWN,
                    port=0,
                    last_check=datetime.utcnow(),
                    error_message=str(result)
                ))
        
        return services
    
    def _is_port_listening(self, port: int) -> bool:
        """Check if a port is listening"""
        
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    async def get_application_metrics(self) -> ApplicationMetrics:
        """Get application-level metrics"""
        
        # This would typically come from Prometheus or application metrics
        # For now, we'll return basic metrics
        
        return ApplicationMetrics(
            timestamp=datetime.utcnow(),
            request_rate_per_second=0.0,  # Would come from metrics
            response_time_avg_ms=0.0,
            response_time_p95_ms=0.0,
            response_time_p99_ms=0.0,
            error_rate_percent=0.0,
            active_users=0,
            total_requests=0,
            total_errors=0
        )
    
    async def get_database_metrics(self) -> DatabaseMetrics:
        """Get database metrics"""
        
        try:
            # Get connection count
            result = self.db.execute(text("SELECT count(*) FROM pg_stat_activity"))
            connection_count = result.scalar()
            
            # Get active connections
            result = self.db.execute(text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"))
            active_connections = result.scalar()
            
            # Get idle connections
            result = self.db.execute(text("SELECT count(*) FROM pg_stat_activity WHERE state = 'idle'"))
            idle_connections = result.scalar()
            
            # Get database size
            result = self.db.execute(text("SELECT pg_database_size(current_database())"))
            database_size_bytes = result.scalar()
            
            # Get table count
            result = self.db.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"))
            table_count = result.scalar()
            
            return DatabaseMetrics(
                timestamp=datetime.utcnow(),
                connection_count=connection_count,
                active_connections=active_connections,
                idle_connections=idle_connections,
                query_performance_avg_ms=0.0,  # Would need more complex query
                slow_queries_count=0,
                cache_hit_rate_percent=0.0,
                database_size_bytes=database_size_bytes,
                table_count=table_count
            )
            
        except Exception as e:
            return DatabaseMetrics(
                timestamp=datetime.utcnow(),
                connection_count=0,
                active_connections=0,
                idle_connections=0,
                query_performance_avg_ms=0.0,
                slow_queries_count=0,
                cache_hit_rate_percent=0.0,
                database_size_bytes=0,
                table_count=0
            )
    
    async def get_system_health(self) -> SystemHealth:
        """Get overall system health"""
        
        services = await self.check_all_services()
        
        healthy_count = sum(1 for s in services if s.status == ServiceStatus.HEALTHY)
        degraded_count = sum(1 for s in services if s.status == ServiceStatus.DEGRADED)
        down_count = sum(1 for s in services if s.status == ServiceStatus.DOWN)
        total_count = len(services)
        
        # Determine overall status
        if down_count > 0:
            overall_status = ServiceStatus.DOWN
        elif degraded_count > 0:
            overall_status = ServiceStatus.DEGRADED
        else:
            overall_status = ServiceStatus.HEALTHY
        
        return SystemHealth(
            overall_status=overall_status,
            healthy_services=healthy_count,
            degraded_services=degraded_count,
            down_services=down_count,
            total_services=total_count,
            last_updated=datetime.utcnow(),
            critical_alerts=0,  # Would come from alert system
            warning_alerts=0,
            info_alerts=0
        )
    
    async def create_alert(self, level: AlertLevel, service: str, title: str, message: str) -> Alert:
        """Create a new alert"""
        
        alert = Alert(
            level=level,
            service=service,
            title=title,
            message=message
        )
        
        # In a real implementation, this would be stored in the database
        # For now, we'll just return the alert object
        
        return alert
    
    async def check_system_alerts(self) -> List[Alert]:
        """Check for system alerts based on current metrics"""
        
        alerts = []
        
        # Get system metrics
        system_metrics = await self.get_system_metrics()
        
        # Check CPU usage
        if system_metrics.cpu_usage_percent > 90:
            alerts.append(await self.create_alert(
                AlertLevel.CRITICAL,
                "system",
                "High CPU Usage",
                f"CPU usage is {system_metrics.cpu_usage_percent:.1f}%"
            ))
        elif system_metrics.cpu_usage_percent > 80:
            alerts.append(await self.create_alert(
                AlertLevel.WARNING,
                "system",
                "Elevated CPU Usage",
                f"CPU usage is {system_metrics.cpu_usage_percent:.1f}%"
            ))
        
        # Check memory usage
        if system_metrics.memory_usage_percent > 90:
            alerts.append(await self.create_alert(
                AlertLevel.CRITICAL,
                "system",
                "High Memory Usage",
                f"Memory usage is {system_metrics.memory_usage_percent:.1f}%"
            ))
        elif system_metrics.memory_usage_percent > 80:
            alerts.append(await self.create_alert(
                AlertLevel.WARNING,
                "system",
                "Elevated Memory Usage",
                f"Memory usage is {system_metrics.memory_usage_percent:.1f}%"
            ))
        
        # Check disk usage
        if system_metrics.disk_usage_percent > 95:
            alerts.append(await self.create_alert(
                AlertLevel.CRITICAL,
                "system",
                "Disk Space Critical",
                f"Disk usage is {system_metrics.disk_usage_percent:.1f}%"
            ))
        elif system_metrics.disk_usage_percent > 85:
            alerts.append(await self.create_alert(
                AlertLevel.WARNING,
                "system",
                "Low Disk Space",
                f"Disk usage is {system_metrics.disk_usage_percent:.1f}%"
            ))
        
        # Check service health
        services = await self.check_all_services()
        for service in services:
            if service.status == ServiceStatus.DOWN:
                alerts.append(await self.create_alert(
                    AlertLevel.CRITICAL,
                    service.service_id,
                    f"Service Down: {service.service_name}",
                    f"Service {service.service_name} is not responding"
                ))
            elif service.status == ServiceStatus.DEGRADED:
                alerts.append(await self.create_alert(
                    AlertLevel.WARNING,
                    service.service_id,
                    f"Service Degraded: {service.service_name}",
                    f"Service {service.service_name} is experiencing issues"
                ))
        
        return alerts
    
    async def get_metrics_history(self, metric_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical metrics data"""
        
        # In a real implementation, this would query a time-series database
        # For now, we'll return empty data
        
        return []
    
    async def cleanup_old_metrics(self, days: int = 30):
        """Clean up old metrics data"""
        
        # In a real implementation, this would delete old metrics from storage
        # For now, we'll just log the action
        
        print(f"Cleaning up metrics older than {days} days")


class MonitoringService:
    """Monitoring service that runs background tasks"""
    
    def __init__(self, db: Session):
        self.db = db
        self.monitor = SystemMonitor(db)
        self.running = False
        self.check_interval = ADMIN_CONFIG['health_check_interval']
    
    async def start_monitoring(self):
        """Start the monitoring service"""
        
        self.running = True
        
        while self.running:
            try:
                # Check system health
                await self.monitor.check_all_services()
                
                # Check for alerts
                await self.monitor.check_system_alerts()
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def stop_monitoring(self):
        """Stop the monitoring service"""
        
        self.running = False
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all data needed for the admin dashboard"""
        
        # Get all metrics concurrently
        system_metrics, services, system_health, alerts = await asyncio.gather(
            self.monitor.get_system_metrics(),
            self.monitor.check_all_services(),
            self.monitor.get_system_health(),
            self.monitor.check_system_alerts(),
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(system_metrics, Exception):
            system_metrics = SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_usage_percent=0.0,
                memory_usage_percent=0.0,
                disk_usage_percent=0.0,
                network_rx_bytes=0,
                network_tx_bytes=0,
                load_average_1m=0.0,
                load_average_5m=0.0,
                load_average_15m=0.0,
                uptime_seconds=0
            )
        
        if isinstance(services, Exception):
            services = []
        
        if isinstance(system_health, Exception):
            system_health = SystemHealth(
                overall_status=ServiceStatus.UNKNOWN,
                healthy_services=0,
                degraded_services=0,
                down_services=0,
                total_services=0,
                last_updated=datetime.utcnow(),
                critical_alerts=0,
                warning_alerts=0,
                info_alerts=0
            )
        
        if isinstance(alerts, Exception):
            alerts = []
        
        return {
            "system_metrics": system_metrics,
            "services": services,
            "system_health": system_health,
            "alerts": alerts,
            "timestamp": datetime.utcnow()
        }








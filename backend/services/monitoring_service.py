"""
Monitoring Service

This module provides comprehensive monitoring and observability for the Suna platform:
- Metrics collection and aggregation
- Health check management
- Performance monitoring
- Audit logging
- Alert management
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from uuid import UUID
import psutil
import aiohttp
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from database.connection import get_db
from database.models import User, Project, Thread, Message, FileStorage, WebSocketConnection
from utils.logger import logger
from utils.config import config
from services.redis_client import redis

class MonitoringService:
    """Centralized monitoring service for Suna platform"""
    
    def __init__(self):
        self.metrics = {}
        self.health_checks = {}
        self.alert_rules = {}
        self.audit_log = []
        self._initialized = False
        
    async def initialize(self):
        """Initialize the monitoring service"""
        if self._initialized:
            return
            
        # Register default health checks
        await self._register_default_health_checks()
        
        # Register default alert rules
        await self._register_default_alert_rules()
        
        # Start background tasks
        asyncio.create_task(self._metrics_collection_loop())
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._alert_evaluation_loop())
        
        self._initialized = True
        logger.info("Monitoring service initialized")
    
    async def _register_default_health_checks(self):
        """Register default health checks for all services"""
        self.health_checks = {
            "database": {
                "check": self._check_database_health,
                "interval": 30,
                "timeout": 10,
                "last_check": None,
                "status": "unknown"
            },
            "redis": {
                "check": self._check_redis_health,
                "interval": 30,
                "timeout": 10,
                "last_check": None,
                "status": "unknown"
            },
            "file_storage": {
                "check": self._check_file_storage_health,
                "interval": 60,
                "timeout": 15,
                "last_check": None,
                "status": "unknown"
            },
            "websocket": {
                "check": self._check_websocket_health,
                "interval": 30,
                "timeout": 10,
                "last_check": None,
                "status": "unknown"
            },
            "background_jobs": {
                "check": self._check_background_jobs_health,
                "interval": 60,
                "timeout": 15,
                "last_check": None,
                "status": "unknown"
            },
            "local_ai": {
                "check": self._check_local_ai_health,
                "interval": 120,
                "timeout": 30,
                "last_check": None,
                "status": "unknown"
            }
        }
    
    async def _register_default_alert_rules(self):
        """Register default alert rules"""
        self.alert_rules = {
            "high_cpu_usage": {
                "condition": lambda metrics: metrics.get("system_cpu_percent", 0) > 80,
                "message": "High CPU usage detected",
                "severity": "warning"
            },
            "high_memory_usage": {
                "condition": lambda metrics: metrics.get("system_memory_percent", 0) > 85,
                "message": "High memory usage detected",
                "severity": "warning"
            },
            "database_connection_issues": {
                "condition": lambda metrics: metrics.get("database_connections_failed", 0) > 5,
                "message": "Database connection issues detected",
                "severity": "critical"
            },
            "redis_connection_issues": {
                "condition": lambda metrics: metrics.get("redis_connection_failed", 0) > 3,
                "message": "Redis connection issues detected",
                "severity": "critical"
            },
            "high_error_rate": {
                "condition": lambda metrics: metrics.get("error_rate_percent", 0) > 10,
                "message": "High error rate detected",
                "severity": "critical"
            }
        }
    
    async def _metrics_collection_loop(self):
        """Background task for collecting metrics"""
        while True:
            try:
                await self._collect_system_metrics()
                await self._collect_application_metrics()
                await self._collect_business_metrics()
                await asyncio.sleep(60)  # Collect metrics every minute
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(60)
    
    async def _health_check_loop(self):
        """Background task for running health checks"""
        while True:
            try:
                await self._run_health_checks()
                await asyncio.sleep(30)  # Run health checks every 30 seconds
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)
    
    async def _alert_evaluation_loop(self):
        """Background task for evaluating alerts"""
        while True:
            try:
                await self._evaluate_alerts()
                await asyncio.sleep(60)  # Evaluate alerts every minute
            except Exception as e:
                logger.error(f"Error in alert evaluation loop: {e}")
                await asyncio.sleep(60)
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available / (1024 * 1024 * 1024)  # GB
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free = disk.free / (1024 * 1024 * 1024)  # GB
            
            # Network metrics
            network = psutil.net_io_counters()
            
            self.metrics.update({
                "system_cpu_percent": cpu_percent,
                "system_cpu_count": cpu_count,
                "system_memory_percent": memory_percent,
                "system_memory_available_gb": memory_available,
                "system_disk_percent": disk_percent,
                "system_disk_free_gb": disk_free,
                "system_network_bytes_sent": network.bytes_sent,
                "system_network_bytes_recv": network.bytes_recv,
                "system_network_packets_sent": network.packets_sent,
                "system_network_packets_recv": network.packets_recv,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _collect_application_metrics(self):
        """Collect application-level metrics"""
        try:
            # Database metrics
            db_metrics = await self._get_database_metrics()
            
            # Redis metrics
            redis_metrics = await self._get_redis_metrics()
            
            # WebSocket metrics
            websocket_metrics = await self._get_websocket_metrics()
            
            # File storage metrics
            file_storage_metrics = await self._get_file_storage_metrics()
            
            self.metrics.update({
                **db_metrics,
                **redis_metrics,
                **websocket_metrics,
                **file_storage_metrics
            })
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
    
    async def _collect_business_metrics(self):
        """Collect business-level metrics"""
        try:
            db = next(get_db())
            
            # User metrics
            total_users = db.query(User).count()
            active_users_24h = db.query(User).filter(
                User.last_login >= datetime.now(timezone.utc) - timedelta(hours=24)
            ).count()
            
            # Project metrics
            total_projects = db.query(Project).count()
            active_projects_24h = db.query(Project).filter(
                Project.updated_at >= datetime.now(timezone.utc) - timedelta(hours=24)
            ).count()
            
            # Message metrics
            total_messages = db.query(Message).count()
            messages_24h = db.query(Message).filter(
                Message.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)
            ).count()
            
            # File metrics
            total_files = db.query(FileStorage).count()
            total_file_size = db.query(func.sum(FileStorage.file_size)).scalar() or 0
            
            self.metrics.update({
                "business_total_users": total_users,
                "business_active_users_24h": active_users_24h,
                "business_total_projects": total_projects,
                "business_active_projects_24h": active_projects_24h,
                "business_total_messages": total_messages,
                "business_messages_24h": messages_24h,
                "business_total_files": total_files,
                "business_total_file_size_bytes": total_file_size
            })
            
        except Exception as e:
            logger.error(f"Error collecting business metrics: {e}")
    
    async def _get_database_metrics(self) -> Dict[str, Any]:
        """Get database metrics"""
        try:
            db = next(get_db())
            
            # Test connection
            start_time = time.time()
            db.execute("SELECT 1")
            db_latency = (time.time() - start_time) * 1000
            
            # Get connection pool info
            pool_size = db.bind.pool.size()
            checked_in = db.bind.pool.checkedin()
            checked_out = db.bind.pool.checkedout()
            
            return {
                "database_latency_ms": db_latency,
                "database_pool_size": pool_size,
                "database_connections_checked_in": checked_in,
                "database_connections_checked_out": checked_out,
                "database_connections_failed": 0  # Would need to track this
            }
        except Exception as e:
            logger.error(f"Error getting database metrics: {e}")
            return {
                "database_latency_ms": -1,
                "database_pool_size": 0,
                "database_connections_checked_in": 0,
                "database_connections_checked_out": 0,
                "database_connections_failed": 1
            }
    
    async def _get_redis_metrics(self) -> Dict[str, Any]:
        """Get Redis metrics"""
        try:
            redis_client = await redis.get_client()
            
            # Test connection
            start_time = time.time()
            await redis_client.ping()
            redis_latency = (time.time() - start_time) * 1000
            
            # Get Redis info
            info = await redis_client.info()
            
            return {
                "redis_latency_ms": redis_latency,
                "redis_connected_clients": info.get("connected_clients", 0),
                "redis_used_memory_bytes": info.get("used_memory", 0),
                "redis_keyspace_hits": info.get("keyspace_hits", 0),
                "redis_keyspace_misses": info.get("keyspace_misses", 0),
                "redis_connection_failed": 0
            }
        except Exception as e:
            logger.error(f"Error getting Redis metrics: {e}")
            return {
                "redis_latency_ms": -1,
                "redis_connected_clients": 0,
                "redis_used_memory_bytes": 0,
                "redis_keyspace_hits": 0,
                "redis_keyspace_misses": 0,
                "redis_connection_failed": 1
            }
    
    async def _get_websocket_metrics(self) -> Dict[str, Any]:
        """Get WebSocket metrics"""
        try:
            db = next(get_db())
            
            # Count active connections
            active_connections = db.query(WebSocketConnection).filter(
                WebSocketConnection.status == "connected"
            ).count()
            
            # Count connections by user
            connections_by_user = db.query(
                WebSocketConnection.user_id,
                func.count(WebSocketConnection.id)
            ).filter(
                WebSocketConnection.status == "connected"
            ).group_by(WebSocketConnection.user_id).all()
            
            return {
                "websocket_active_connections": active_connections,
                "websocket_connected_users": len(connections_by_user),
                "websocket_avg_connections_per_user": sum(count for _, count in connections_by_user) / max(len(connections_by_user), 1)
            }
        except Exception as e:
            logger.error(f"Error getting WebSocket metrics: {e}")
            return {
                "websocket_active_connections": 0,
                "websocket_connected_users": 0,
                "websocket_avg_connections_per_user": 0
            }
    
    async def _get_file_storage_metrics(self) -> Dict[str, Any]:
        """Get file storage metrics"""
        try:
            db = next(get_db())
            
            # File storage stats
            total_files = db.query(FileStorage).count()
            total_size = db.query(func.sum(FileStorage.file_size)).scalar() or 0
            active_files = db.query(FileStorage).filter(
                FileStorage.status == "active"
            ).count()
            
            # Files by type
            files_by_type = db.query(
                FileStorage.content_type,
                func.count(FileStorage.id)
            ).group_by(FileStorage.content_type).all()
            
            return {
                "file_storage_total_files": total_files,
                "file_storage_total_size_bytes": total_size,
                "file_storage_active_files": active_files,
                "file_storage_files_by_type": dict(files_by_type)
            }
        except Exception as e:
            logger.error(f"Error getting file storage metrics: {e}")
            return {
                "file_storage_total_files": 0,
                "file_storage_total_size_bytes": 0,
                "file_storage_active_files": 0,
                "file_storage_files_by_type": {}
            }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            db = next(get_db())
            start_time = time.time()
            db.execute("SELECT 1")
            latency = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "latency_ms": latency,
                "error": None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "latency_ms": -1,
                "error": str(e)
            }
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            redis_client = await redis.get_client()
            start_time = time.time()
            await redis_client.ping()
            latency = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "latency_ms": latency,
                "error": None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "latency_ms": -1,
                "error": str(e)
            }
    
    async def _check_file_storage_health(self) -> Dict[str, Any]:
        """Check file storage health"""
        try:
            # Check if storage directory exists and is writable
            import os
            storage_path = config.FILE_STORAGE_PATH
            
            if not os.path.exists(storage_path):
                os.makedirs(storage_path, exist_ok=True)
            
            # Test write access
            test_file = os.path.join(storage_path, ".health_check")
            with open(test_file, 'w') as f:
                f.write("health_check")
            os.remove(test_file)
            
            return {
                "status": "healthy",
                "storage_path": storage_path,
                "error": None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "storage_path": config.FILE_STORAGE_PATH,
                "error": str(e)
            }
    
    async def _check_websocket_health(self) -> Dict[str, Any]:
        """Check WebSocket health"""
        try:
            db = next(get_db())
            
            # Check if WebSocket service is accessible
            active_connections = db.query(WebSocketConnection).filter(
                WebSocketConnection.status == "connected"
            ).count()
            
            return {
                "status": "healthy",
                "active_connections": active_connections,
                "error": None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "active_connections": 0,
                "error": str(e)
            }
    
    async def _check_background_jobs_health(self) -> Dict[str, Any]:
        """Check background jobs health"""
        try:
            # This would need to be implemented based on the background job service
            # For now, return a basic health check
            return {
                "status": "healthy",
                "error": None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _check_local_ai_health(self) -> Dict[str, Any]:
        """Check local AI services health"""
        try:
            # This would need to be implemented based on the local AI service
            # For now, return a basic health check
            return {
                "status": "healthy",
                "error": None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _run_health_checks(self):
        """Run all registered health checks"""
        for service_name, health_check in self.health_checks.items():
            try:
                # Check if it's time to run this health check
                now = datetime.now(timezone.utc)
                if (health_check["last_check"] is None or 
                    (now - health_check["last_check"]).total_seconds() >= health_check["interval"]):
                    
                    # Run the health check
                    result = await health_check["check"]()
                    health_check["status"] = result["status"]
                    health_check["last_check"] = now
                    health_check["last_result"] = result
                    
                    logger.debug(f"Health check for {service_name}: {result['status']}")
                    
            except Exception as e:
                logger.error(f"Error running health check for {service_name}: {e}")
                health_check["status"] = "error"
                health_check["last_check"] = datetime.now(timezone.utc)
                health_check["last_result"] = {"status": "error", "error": str(e)}
    
    async def _evaluate_alerts(self):
        """Evaluate all alert rules"""
        try:
            for alert_name, alert_rule in self.alert_rules.items():
                if alert_rule["condition"](self.metrics):
                    await self._trigger_alert(alert_name, alert_rule)
        except Exception as e:
            logger.error(f"Error evaluating alerts: {e}")
    
    async def _trigger_alert(self, alert_name: str, alert_rule: Dict[str, Any]):
        """Trigger an alert"""
        try:
            alert = {
                "name": alert_name,
                "message": alert_rule["message"],
                "severity": alert_rule["severity"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": self.metrics.copy()
            }
            
            # Log the alert
            logger.warning(f"Alert triggered: {alert_name} - {alert_rule['message']}")
            
            # Store alert in Redis for persistence
            redis_client = await redis.get_client()
            await redis_client.lpush("alerts", json.dumps(alert))
            await redis_client.ltrim("alerts", 0, 999)  # Keep last 1000 alerts
            
            # TODO: Send alert to notification service
            # await notification_service.send_alert(alert)
            
        except Exception as e:
            logger.error(f"Error triggering alert {alert_name}: {e}")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics.copy()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all services"""
        return {
            "overall_status": self._get_overall_health_status(),
            "services": {
                name: {
                    "status": check["status"],
                    "last_check": check["last_check"].isoformat() if check["last_check"] else None,
                    "last_result": check.get("last_result", {})
                }
                for name, check in self.health_checks.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_overall_health_status(self) -> str:
        """Get overall health status"""
        statuses = [check["status"] for check in self.health_checks.values()]
        
        if "unhealthy" in statuses or "error" in statuses:
            return "unhealthy"
        elif "unknown" in statuses:
            return "degraded"
        else:
            return "healthy"
    
    async def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        try:
            redis_client = await redis.get_client()
            alerts = await redis_client.lrange("alerts", 0, limit - 1)
            return [json.loads(alert) for alert in alerts]
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []
    
    async def log_audit_event(self, event_type: str, user_id: Optional[UUID], 
                            resource_type: str, resource_id: str, 
                            action: str, details: Dict[str, Any]):
        """Log an audit event"""
        try:
            audit_event = {
                "event_type": event_type,
                "user_id": str(user_id) if user_id else None,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ip_address": None,  # Would need to be passed from request context
                "user_agent": None   # Would need to be passed from request context
            }
            
            # Log to structured logger
            logger.info("Audit event", extra=audit_event)
            
            # Store in Redis for persistence
            redis_client = await redis.get_client()
            await redis_client.lpush("audit_log", json.dumps(audit_event))
            await redis_client.ltrim("audit_log", 0, 9999)  # Keep last 10000 events
            
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
    
    async def get_audit_log(self, limit: int = 100, 
                          event_type: Optional[str] = None,
                          user_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
        """Get audit log entries"""
        try:
            redis_client = await redis.get_client()
            events = await redis_client.lrange("audit_log", 0, limit - 1)
            
            audit_events = []
            for event in events:
                event_data = json.loads(event)
                
                # Apply filters
                if event_type and event_data.get("event_type") != event_type:
                    continue
                if user_id and event_data.get("user_id") != str(user_id):
                    continue
                
                audit_events.append(event_data)
            
            return audit_events
            
        except Exception as e:
            logger.error(f"Error getting audit log: {e}")
            return []

    async def update_monitoring_settings(self, settings: Dict[str, Any]) -> bool:
        """Update monitoring settings (admin only)"""
        try:
            # Update configuration based on settings
            if 'metrics_collection_interval' in settings:
                config.METRICS_COLLECTION_INTERVAL = settings['metrics_collection_interval']
            if 'health_check_interval' in settings:
                config.HEALTH_CHECK_INTERVAL = settings['health_check_interval']
            if 'alert_evaluation_interval' in settings:
                config.ALERT_EVALUATION_INTERVAL = settings['alert_evaluation_interval']
            
            logger.info(f"Monitoring settings updated: {settings}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating monitoring settings: {e}")
            return False

    async def update_alert_thresholds(self, thresholds: Dict[str, Any]) -> bool:
        """Update alert thresholds (admin only)"""
        try:
            # Update alert thresholds based on settings
            if 'cpu_usage_threshold' in thresholds:
                config.CPU_USAGE_THRESHOLD = thresholds['cpu_usage_threshold']
            if 'memory_usage_threshold' in thresholds:
                config.MEMORY_USAGE_THRESHOLD = thresholds['memory_usage_threshold']
            if 'disk_usage_threshold' in thresholds:
                config.DISK_USAGE_THRESHOLD = thresholds['disk_usage_threshold']
            
            # Update alert rules with new thresholds
            self.alert_rules["high_cpu_usage"]["condition"] = lambda metrics: metrics.get("system_cpu_percent", 0) > config.CPU_USAGE_THRESHOLD
            self.alert_rules["high_memory_usage"]["condition"] = lambda metrics: metrics.get("system_memory_percent", 0) > config.MEMORY_USAGE_THRESHOLD
            
            logger.info(f"Alert thresholds updated: {thresholds}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating alert thresholds: {e}")
            return False

# Global monitoring service instance
monitoring_service = MonitoringService()

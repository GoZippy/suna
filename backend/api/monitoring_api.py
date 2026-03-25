"""
Monitoring API

FastAPI endpoints for monitoring and observability including:
- Metrics collection and exposure
- Health check endpoints
- Alert management
- Audit logging
- Prometheus metrics format
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from services.monitoring_service import monitoring_service
from auth.jwt_auth import get_current_user_id_from_jwt, get_current_active_user
from database.models import User
from utils.logger import logger

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

# Pydantic models for responses
class HealthCheckResponse(BaseModel):
    overall_status: str
    services: Dict[str, Dict[str, Any]]
    timestamp: str

class MetricsResponse(BaseModel):
    metrics: Dict[str, Any]
    timestamp: str

class AlertResponse(BaseModel):
    name: str
    message: str
    severity: str
    timestamp: str
    metrics: Dict[str, Any]

class AuditEventResponse(BaseModel):
    event_type: str
    user_id: Optional[str]
    resource_type: str
    resource_id: str
    action: str
    details: Dict[str, Any]
    timestamp: str

class SystemStatusResponse(BaseModel):
    status: str
    version: str
    uptime: str
    services: Dict[str, str]
    timestamp: str

@router.get("/health", response_model=HealthCheckResponse)
async def get_health_status():
    """Get comprehensive health status of all services"""
    try:
        # Initialize monitoring service if not already done
        await monitoring_service.initialize()
        
        health_status = await monitoring_service.get_health_status()
        return HealthCheckResponse(**health_status)
        
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get current system and application metrics"""
    try:
        # Initialize monitoring service if not already done
        await monitoring_service.initialize()
        
        metrics = await monitoring_service.get_metrics()
        return MetricsResponse(
            metrics=metrics,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Get metrics in Prometheus format"""
    try:
        # Initialize monitoring service if not already done
        await monitoring_service.initialize()
        
        metrics = await monitoring_service.get_metrics()
        
        # Convert to Prometheus format
        prometheus_lines = []
        
        # System metrics
        if "system_cpu_percent" in metrics:
            prometheus_lines.append(f"suna_system_cpu_percent {metrics['system_cpu_percent']}")
        if "system_memory_percent" in metrics:
            prometheus_lines.append(f"suna_system_memory_percent {metrics['system_memory_percent']}")
        if "system_disk_percent" in metrics:
            prometheus_lines.append(f"suna_system_disk_percent {metrics['system_disk_percent']}")
        
        # Database metrics
        if "database_latency_ms" in metrics:
            prometheus_lines.append(f"suna_database_latency_ms {metrics['database_latency_ms']}")
        if "database_pool_size" in metrics:
            prometheus_lines.append(f"suna_database_pool_size {metrics['database_pool_size']}")
        
        # Redis metrics
        if "redis_latency_ms" in metrics:
            prometheus_lines.append(f"suna_redis_latency_ms {metrics['redis_latency_ms']}")
        if "redis_connected_clients" in metrics:
            prometheus_lines.append(f"suna_redis_connected_clients {metrics['redis_connected_clients']}")
        
        # WebSocket metrics
        if "websocket_active_connections" in metrics:
            prometheus_lines.append(f"suna_websocket_active_connections {metrics['websocket_active_connections']}")
        
        # Business metrics
        if "business_total_users" in metrics:
            prometheus_lines.append(f"suna_business_total_users {metrics['business_total_users']}")
        if "business_total_projects" in metrics:
            prometheus_lines.append(f"suna_business_total_projects {metrics['business_total_projects']}")
        if "business_total_messages" in metrics:
            prometheus_lines.append(f"suna_business_total_messages {metrics['business_total_messages']}")
        
        # File storage metrics
        if "file_storage_total_files" in metrics:
            prometheus_lines.append(f"suna_file_storage_total_files {metrics['file_storage_total_files']}")
        if "file_storage_total_size_bytes" in metrics:
            prometheus_lines.append(f"suna_file_storage_total_size_bytes {metrics['file_storage_total_size_bytes']}")
        
        return "\n".join(prometheus_lines)
        
    except Exception as e:
        logger.error(f"Error getting Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get Prometheus metrics: {str(e)}")

@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    limit: int = Query(100, le=1000, description="Maximum number of alerts to return"),
    current_user: User = Depends(get_current_active_user)
):
    """Get recent alerts (admin only)"""
    try:
        # Check if user is admin (you might want to add proper admin role checking)
        
        alerts = await monitoring_service.get_alerts(limit=limit)
        return [AlertResponse(**alert) for alert in alerts]
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")

@router.get("/audit-log", response_model=List[AuditEventResponse])
async def get_audit_log(
    limit: int = Query(100, le=1000, description="Maximum number of audit events to return"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    current_user: User = Depends(get_current_active_user)
):
    """Get audit log entries (admin only)"""
    try:
        # Check if user is admin (you might want to add proper admin role checking)
        
        audit_events = await monitoring_service.get_audit_log(
            limit=limit,
            event_type=event_type,
            user_id=user_id
        )
        return [AuditEventResponse(**event) for event in audit_events]
        
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit log: {str(e)}")

@router.post("/audit-log")
async def log_audit_event(
    event_type: str,
    resource_type: str,
    resource_id: str,
    action: str,
    details: Dict[str, Any],
    user_id: Optional[UUID] = Depends(get_current_user_id_from_jwt)
):
    """Log an audit event"""
    try:
        await monitoring_service.log_audit_event(
            event_type=event_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details
        )
        return {"status": "logged"}
        
    except Exception as e:
        logger.error(f"Error logging audit event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log audit event: {str(e)}")

@router.get("/system-status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get overall system status and version information"""
    try:
        # Initialize monitoring service if not already done
        await monitoring_service.initialize()
        
        health_status = await monitoring_service.get_health_status()
        
        # Get service statuses
        services = {}
        for service_name, service_info in health_status["services"].items():
            services[service_name] = service_info["status"]
        
        return SystemStatusResponse(
            status=health_status["overall_status"],
            version="1.0.0",  # You might want to get this from config or version file
            uptime="0",  # You might want to track actual uptime
            services=services,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")

@router.get("/health/database")
async def get_database_health():
    """Get database health status"""
    try:
        # Initialize monitoring service if not already done
        await monitoring_service.initialize()
        
        health_status = await monitoring_service.get_health_status()
        db_health = health_status["services"].get("database", {})
        
        return {
            "status": db_health.get("status", "unknown"),
            "last_check": db_health.get("last_check"),
            "details": db_health.get("last_result", {})
        }
        
    except Exception as e:
        logger.error(f"Error getting database health: {e}")
        raise HTTPException(status_code=500, detail=f"Database health check failed: {str(e)}")

@router.get("/health/redis")
async def get_redis_health():
    """Get Redis health status"""
    try:
        # Initialize monitoring service if not already done
        await monitoring_service.initialize()
        
        health_status = await monitoring_service.get_health_status()
        redis_health = health_status["services"].get("redis", {})
        
        return {
            "status": redis_health.get("status", "unknown"),
            "last_check": redis_health.get("last_check"),
            "details": redis_health.get("last_result", {})
        }
        
    except Exception as e:
        logger.error(f"Error getting Redis health: {e}")
        raise HTTPException(status_code=500, detail=f"Redis health check failed: {str(e)}")

@router.get("/health/websocket")
async def get_websocket_health():
    """Get WebSocket health status"""
    try:
        # Initialize monitoring service if not already done
        await monitoring_service.initialize()
        
        health_status = await monitoring_service.get_health_status()
        websocket_health = health_status["services"].get("websocket", {})
        
        return {
            "status": websocket_health.get("status", "unknown"),
            "last_check": websocket_health.get("last_check"),
            "details": websocket_health.get("last_result", {})
        }
        
    except Exception as e:
        logger.error(f"Error getting WebSocket health: {e}")
        raise HTTPException(status_code=500, detail=f"WebSocket health check failed: {str(e)}")

@router.get("/health/file-storage")
async def get_file_storage_health():
    """Get file storage health status"""
    try:
        # Initialize monitoring service if not already done
        await monitoring_service.initialize()
        
        health_status = await monitoring_service.get_health_status()
        file_storage_health = health_status["services"].get("file_storage", {})
        
        return {
            "status": file_storage_health.get("status", "unknown"),
            "last_check": file_storage_health.get("last_check"),
            "details": file_storage_health.get("last_result", {})
        }
        
    except Exception as e:
        logger.error(f"Error getting file storage health: {e}")
        raise HTTPException(status_code=500, detail=f"File storage health check failed: {str(e)}")

@router.get("/health/background-jobs")
async def get_background_jobs_health():
    """Get background jobs health status"""
    try:
        # Initialize monitoring service if not already done
        await monitoring_service.initialize()
        
        health_status = await monitoring_service.get_health_status()
        background_jobs_health = health_status["services"].get("background_jobs", {})
        
        return {
            "status": background_jobs_health.get("status", "unknown"),
            "last_check": background_jobs_health.get("last_check"),
            "details": background_jobs_health.get("last_result", {})
        }
        
    except Exception as e:
        logger.error(f"Error getting background jobs health: {e}")
        raise HTTPException(status_code=500, detail=f"Background jobs health check failed: {str(e)}")

@router.get("/health/local-ai")
async def get_local_ai_health():
    """Get local AI services health status"""
    try:
        # Initialize monitoring service if not already done
        await monitoring_service.initialize()
        
        health_status = await monitoring_service.get_health_status()
        local_ai_health = health_status["services"].get("local_ai", {})
        
        return {
            "status": local_ai_health.get("status", "unknown"),
            "last_check": local_ai_health.get("last_check"),
            "details": local_ai_health.get("last_result", {})
        }
        
    except Exception as e:
        logger.error(f"Error getting local AI health: {e}")
        raise HTTPException(status_code=500, detail=f"Local AI health check failed: {str(e)}")

# Admin endpoints for monitoring management
@router.post("/admin/initialize")
async def initialize_monitoring(
    current_user: User = Depends(get_current_active_user)
):
    """Initialize the monitoring service (admin only)"""
    try:
        # Check if user is admin (you might want to add proper admin role checking)
        
        await monitoring_service.initialize()
        return {"status": "initialized", "message": "Monitoring service initialized successfully"}
        
    except Exception as e:
        logger.error(f"Error initializing monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize monitoring: {str(e)}")

@router.get("/admin/status")
async def get_monitoring_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get monitoring service status (admin only)"""
    try:
        # Check if user is admin (you might want to add proper admin role checking)
        
        return {
            "initialized": monitoring_service._initialized,
            "health_checks_count": len(monitoring_service.health_checks),
            "alert_rules_count": len(monitoring_service.alert_rules),
            "metrics_count": len(monitoring_service.metrics)
        }
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get monitoring status: {str(e)}")

@router.post("/admin/settings")
async def update_monitoring_settings(
    settings: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Update monitoring settings (admin only)"""
    try:
        # Check if user is admin (you might want to add proper admin role checking)
        
        # Update monitoring service settings
        success = await monitoring_service.update_monitoring_settings(settings)
        
        if success:
            return {"status": "updated", "message": "Monitoring settings updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update monitoring settings")
        
    except Exception as e:
        logger.error(f"Error updating monitoring settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update monitoring settings: {str(e)}")

@router.post("/admin/thresholds")
async def update_alert_thresholds(
    thresholds: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Update alert thresholds (admin only)"""
    try:
        # Check if user is admin (you might want to add proper admin role checking)
        
        # Update alert thresholds
        success = await monitoring_service.update_alert_thresholds(thresholds)
        
        if success:
            return {"status": "updated", "message": "Alert thresholds updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update alert thresholds")
        
    except Exception as e:
        logger.error(f"Error updating alert thresholds: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update alert thresholds: {str(e)}")

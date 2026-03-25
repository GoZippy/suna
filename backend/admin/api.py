"""
Admin API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from .models import (
    AdminUserCreate, AdminUserUpdate, AdminUserResponse, AdminLogin,
    AdminSession, SystemMetrics, ServiceHealth, SystemHealth, Alert,
    ServiceControl, SystemConfig, UserManagementStats, AdminAuditLog
)
from .auth import AdminAuthService, get_current_admin_session, get_current_admin_user
from .monitoring import SystemMonitor, MonitoringService
from . import ADMIN_CONFIG, ADMIN_ROLES, SERVICE_CONFIG
from ..database import get_db

# Create router
router = APIRouter(prefix="/admin", tags=["admin"])

# Security scheme
security = HTTPBearer()


# Authentication endpoints
@router.post("/login", response_model=Dict[str, Any])
async def admin_login(
    login_data: AdminLogin,
    request: Request,
    db: Session = Depends(get_db())
):
    """Admin login endpoint"""
    
    auth_service = AdminAuthService(db)
    
    try:
        # Authenticate user
        session = auth_service.authenticate_admin(login_data, request)
        
        # Create JWT token
        token = auth_service.create_jwt_token(session)
        
        # Log audit event
        audit_log = AdminAuditLog(
            admin_user_id=session.user_id,
            admin_username=session.username,
            action="login",
            resource_type="admin_session",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent'),
            success=True
        )
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": session.expires_at.isoformat(),
            "user": {
                "id": session.user_id,
                "username": session.username,
                "role": session.role.value,
                "permissions": session.permissions
            }
        }
        
    except HTTPException:
        # Log failed login attempt
        audit_log = AdminAuditLog(
            admin_user_id="unknown",
            admin_username=login_data.username,
            action="login_failed",
            resource_type="admin_session",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent'),
            success=False,
            error_message="Invalid credentials"
        )
        raise


@router.post("/logout")
async def admin_logout(
    request: Request,
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Admin logout endpoint"""
    
    # Log audit event
    audit_log = AdminAuditLog(
        admin_user_id=session.user_id,
        admin_username=session.username,
        action="logout",
        resource_type="admin_session",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get('user-agent'),
        success=True
    )
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=AdminUserResponse)
async def get_current_admin(
    current_user: AdminUserResponse = Depends(get_current_admin_user)
):
    """Get current admin user information"""
    
    return current_user


# Dashboard endpoints
@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data(
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Get dashboard data"""
    
    monitor = SystemMonitor(db)
    
    # Get all metrics concurrently
    system_metrics, services, system_health, alerts = await asyncio.gather(
        monitor.get_system_metrics(),
        monitor.check_all_services(),
        monitor.get_system_health(),
        monitor.check_system_alerts(),
        return_exceptions=True
    )
    
    # Handle exceptions
    if isinstance(system_metrics, Exception):
        system_metrics = None
    if isinstance(services, Exception):
        services = []
    if isinstance(system_health, Exception):
        system_health = None
    if isinstance(alerts, Exception):
        alerts = []
    
    return {
        "system_metrics": system_metrics,
        "services": services,
        "system_health": system_health,
        "alerts": alerts,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/dashboard/system-metrics", response_model=SystemMetrics)
async def get_system_metrics(
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Get system metrics"""
    
    monitor = SystemMonitor(db)
    return await monitor.get_system_metrics()


@router.get("/dashboard/services", response_model=List[ServiceHealth])
async def get_services_health(
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Get services health status"""
    
    monitor = SystemMonitor(db)
    return await monitor.check_all_services()


@router.get("/dashboard/system-health", response_model=SystemHealth)
async def get_system_health(
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Get overall system health"""
    
    monitor = SystemMonitor(db)
    return await monitor.get_system_health()


@router.get("/dashboard/alerts", response_model=List[Alert])
async def get_system_alerts(
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Get system alerts"""
    
    monitor = SystemMonitor(db)
    return await monitor.check_system_alerts()


# User management endpoints
@router.post("/users", response_model=AdminUserResponse)
async def create_admin_user(
    user_data: AdminUserCreate,
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Create a new admin user"""
    
    # Check permission
    auth_service = AdminAuthService(db)
    permission_check = auth_service.check_permission(session, "user_management")
    
    if not permission_check.has_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    auth_service = AdminAuthService(db)
    return auth_service.create_admin_user(user_data)


@router.get("/users", response_model=List[AdminUserResponse])
async def list_admin_users(
    skip: int = 0,
    limit: int = 100,
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """List admin users"""
    
    # Check permission
    auth_service = AdminAuthService(db)
    permission_check = auth_service.check_permission(session, "user_management")
    
    if not permission_check.has_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    auth_service = AdminAuthService(db)
    return auth_service.list_admin_users(skip=skip, limit=limit)


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_admin_user(
    user_id: str,
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Get admin user by ID"""
    
    # Check permission
    auth_service = AdminAuthService(db)
    permission_check = auth_service.check_permission(session, "user_management")
    
    if not permission_check.has_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    auth_service = AdminAuthService(db)
    user = auth_service.get_admin_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_admin_user(
    user_id: str,
    update_data: AdminUserUpdate,
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Update admin user"""
    
    # Check permission
    auth_service = AdminAuthService(db)
    permission_check = auth_service.check_permission(session, "user_management")
    
    if not permission_check.has_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    auth_service = AdminAuthService(db)
    user = auth_service.update_admin_user(user_id, update_data)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.delete("/users/{user_id}")
async def delete_admin_user(
    user_id: str,
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Delete admin user"""
    
    # Check permission
    auth_service = AdminAuthService(db)
    permission_check = auth_service.check_permission(session, "user_management")
    
    if not permission_check.has_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Prevent self-deletion
    if user_id == session.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    auth_service = AdminAuthService(db)
    success = auth_service.delete_admin_user(user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted successfully"}


@router.get("/users/stats", response_model=UserManagementStats)
async def get_user_management_stats(
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Get user management statistics"""
    
    # Check permission
    auth_service = AdminAuthService(db)
    permission_check = auth_service.check_permission(session, "user_management")
    
    if not permission_check.has_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # This would typically query the database for statistics
    # For now, return mock data
    
    return UserManagementStats(
        total_users=0,
        active_users=0,
        inactive_users=0,
        users_created_today=0,
        users_created_this_week=0,
        users_created_this_month=0,
        top_user_roles={},
        recent_registrations=[]
    )


# Service control endpoints
@router.post("/services/{service_id}/control")
async def control_service(
    service_id: str,
    control_data: ServiceControl,
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Control a service (start, stop, restart, reload)"""
    
    # Check permission
    auth_service = AdminAuthService(db)
    permission_check = auth_service.check_permission(session, "service_control")
    
    if not permission_check.has_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Check if service exists
    service_config = SERVICE_CONFIG['services'].get(service_id)
    if not service_config:
        raise HTTPException(status_code=404, detail="Service not found")
    
    try:
        # Execute service control command
        import subprocess
        
        command = service_config['restart_command']
        if control_data.action == "stop":
            command = command.replace("restart", "stop")
        elif control_data.action == "start":
            command = command.replace("restart", "start")
        
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Service control failed: {result.stderr}"
            )
        
        return {
            "message": f"Service {service_id} {control_data.action} successful",
            "command": command,
            "output": result.stdout
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Service control timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service control error: {str(e)}")


@router.get("/services/{service_id}/logs")
async def get_service_logs(
    service_id: str,
    lines: int = 100,
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Get service logs"""
    
    # Check permission
    auth_service = AdminAuthService(db)
    permission_check = auth_service.check_permission(session, "log_analysis")
    
    if not permission_check.has_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Check if service exists
    service_config = SERVICE_CONFIG['services'].get(service_id)
    if not service_config:
        raise HTTPException(status_code=404, detail="Service not found")
    
    try:
        import subprocess
        
        # Get last N lines from log file
        result = subprocess.run(
            ["tail", "-n", str(lines), service_config['log_file']],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to read logs: {result.stderr}"
            )
        
        return {
            "service_id": service_id,
            "log_file": service_config['log_file'],
            "lines": lines,
            "content": result.stdout
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Log retrieval timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Log retrieval error: {str(e)}")


# System configuration endpoints
@router.get("/config", response_model=List[SystemConfig])
async def get_system_config(
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Get system configuration"""
    
    # Check permission
    auth_service = AdminAuthService(db)
    permission_check = auth_service.check_permission(session, "system_configuration")
    
    if not permission_check.has_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # This would typically query the database for configuration
    # For now, return mock data
    
    return [
        SystemConfig(
            key="admin_port",
            value=ADMIN_CONFIG['admin_port'],
            description="Admin panel port",
            category="network"
        ),
        SystemConfig(
            key="session_timeout",
            value=ADMIN_CONFIG['session_timeout'],
            description="Admin session timeout in seconds",
            category="security"
        )
    ]


@router.put("/config/{key}")
async def update_system_config(
    key: str,
    config_data: SystemConfig,
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Update system configuration"""
    
    # Check permission
    auth_service = AdminAuthService(db)
    permission_check = auth_service.check_permission(session, "system_configuration")
    
    if not permission_check.has_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # This would typically update the database
    # For now, just return success
    
    return {
        "message": f"Configuration {key} updated successfully",
        "key": key,
        "value": config_data.value
    }


# Audit log endpoints
@router.get("/audit-logs", response_model=List[AdminAuditLog])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
):
    """Get admin audit logs"""
    
    # Check permission
    auth_service = AdminAuthService(db)
    permission_check = auth_service.check_permission(session, "log_analysis")
    
    if not permission_check.has_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # This would typically query the database for audit logs
    # For now, return empty list
    
    return []


# Health check endpoint
@router.get("/health")
async def admin_health_check():
    """Admin health check endpoint"""
    
    return {
        "status": "healthy",
        "service": "admin",
        "timestamp": datetime.utcnow().isoformat()
    }


# Import missing modules
import asyncio
from datetime import datetime 
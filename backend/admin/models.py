"""
Admin system data models
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


class AdminRole(str, Enum):
    """Admin user roles"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATOR = "operator"


class ServiceStatus(str, Enum):
    """Service status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class AlertLevel(str, Enum):
    """Alert level enumeration"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AdminUserCreate(BaseModel):
    """Model for creating admin users"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8)
    role: AdminRole = Field(default=AdminRole.OPERATOR)
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: bool = Field(default=True)


class AdminUserUpdate(BaseModel):
    """Model for updating admin users"""
    email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$')
    role: Optional[AdminRole] = None
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class AdminUserResponse(BaseModel):
    """Model for admin user responses"""
    id: str
    username: str
    email: str
    role: AdminRole
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    login_attempts: int = 0
    locked_until: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminLogin(BaseModel):
    """Model for admin login"""
    username: str
    password: str


class AdminSession(BaseModel):
    """Model for admin session"""
    session_id: str
    user_id: str
    username: str
    role: AdminRole
    permissions: List[str]
    created_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class SystemMetrics(BaseModel):
    """Model for system metrics"""
    timestamp: datetime
    cpu_usage_percent: float = Field(..., ge=0, le=100)
    memory_usage_percent: float = Field(..., ge=0, le=100)
    disk_usage_percent: float = Field(..., ge=0, le=100)
    network_rx_bytes: int = Field(..., ge=0)
    network_tx_bytes: int = Field(..., ge=0)
    load_average_1m: float = Field(..., ge=0)
    load_average_5m: float = Field(..., ge=0)
    load_average_15m: float = Field(..., ge=0)
    uptime_seconds: int = Field(..., ge=0)


class ServiceHealth(BaseModel):
    """Model for service health status"""
    service_name: str
    service_id: str
    status: ServiceStatus
    port: int
    health_endpoint: Optional[str] = None
    response_time_ms: Optional[float] = None
    last_check: datetime
    uptime_seconds: Optional[int] = None
    version: Optional[str] = None
    error_message: Optional[str] = None


class ApplicationMetrics(BaseModel):
    """Model for application metrics"""
    timestamp: datetime
    request_rate_per_second: float = Field(..., ge=0)
    response_time_avg_ms: float = Field(..., ge=0)
    response_time_p95_ms: float = Field(..., ge=0)
    response_time_p99_ms: float = Field(..., ge=0)
    error_rate_percent: float = Field(..., ge=0, le=100)
    active_users: int = Field(..., ge=0)
    total_requests: int = Field(..., ge=0)
    total_errors: int = Field(..., ge=0)


class DatabaseMetrics(BaseModel):
    """Model for database metrics"""
    timestamp: datetime
    connection_count: int = Field(..., ge=0)
    active_connections: int = Field(..., ge=0)
    idle_connections: int = Field(..., ge=0)
    query_performance_avg_ms: float = Field(..., ge=0)
    slow_queries_count: int = Field(..., ge=0)
    cache_hit_rate_percent: float = Field(..., ge=0, le=100)
    database_size_bytes: int = Field(..., ge=0)
    table_count: int = Field(..., ge=0)


class Alert(BaseModel):
    """Model for system alerts"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    level: AlertLevel
    service: Optional[str] = None
    title: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = Field(default=False)
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = Field(default=False)
    resolved_at: Optional[datetime] = None


class LogEntry(BaseModel):
    """Model for log entries"""
    timestamp: datetime
    level: str
    service: str
    message: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BackupInfo(BaseModel):
    """Model for backup information"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    backup_type: str  # 'database', 'files', 'full'
    size_bytes: int
    created_at: datetime
    expires_at: datetime
    status: str  # 'completed', 'failed', 'in_progress'
    checksum: Optional[str] = None
    error_message: Optional[str] = None


class ServiceControl(BaseModel):
    """Model for service control actions"""
    service_id: str
    action: str  # 'start', 'stop', 'restart', 'reload'
    force: bool = Field(default=False)


class SystemConfig(BaseModel):
    """Model for system configuration"""
    key: str
    value: Any
    description: Optional[str] = None
    category: str = Field(default="general")
    is_secret: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None


class DashboardData(BaseModel):
    """Model for dashboard data"""
    system_metrics: SystemMetrics
    application_metrics: ApplicationMetrics
    database_metrics: DatabaseMetrics
    service_health: List[ServiceHealth]
    recent_alerts: List[Alert]
    recent_logs: List[LogEntry]


class UserManagementStats(BaseModel):
    """Model for user management statistics"""
    total_users: int
    active_users: int
    inactive_users: int
    users_created_today: int
    users_created_this_week: int
    users_created_this_month: int
    top_user_roles: Dict[str, int]
    recent_registrations: List[Dict[str, Any]]


class SystemHealth(BaseModel):
    """Model for overall system health"""
    overall_status: ServiceStatus
    healthy_services: int
    degraded_services: int
    down_services: int
    total_services: int
    last_updated: datetime
    critical_alerts: int
    warning_alerts: int
    info_alerts: int


class AdminAuditLog(BaseModel):
    """Model for admin audit logs"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    admin_user_id: str
    admin_username: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = Field(default=True)
    error_message: Optional[str] = None


class PermissionCheck(BaseModel):
    """Model for permission checking"""
    user_id: str
    permission: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None


class PermissionResponse(BaseModel):
    """Model for permission response"""
    has_permission: bool
    reason: Optional[str] = None
    required_role: Optional[str] = None








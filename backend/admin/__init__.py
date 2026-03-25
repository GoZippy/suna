"""
Suna Administration and Management System

This package provides comprehensive administration and management interfaces for the Suna self-hosted system:
- Web-based admin panel for user and system management
- CLI tools for system administration and maintenance
- System health monitoring and diagnostic tools
- User management interface for account administration
- Configuration management and service control interfaces
- Log viewing and analysis tools
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Admin configuration
ADMIN_CONFIG = {
    'admin_port': int(os.getenv('ADMIN_PORT', '9091')),
    'admin_host': os.getenv('ADMIN_HOST', '0.0.0.0'),
    'admin_secret': os.getenv('ADMIN_SECRET', 'admin-secret-key-change-in-production'),
    'session_timeout': int(os.getenv('ADMIN_SESSION_TIMEOUT', '3600')),  # 1 hour
    'max_login_attempts': int(os.getenv('ADMIN_MAX_LOGIN_ATTEMPTS', '5')),
    'log_retention_days': int(os.getenv('ADMIN_LOG_RETENTION_DAYS', '30')),
    'backup_retention_days': int(os.getenv('ADMIN_BACKUP_RETENTION_DAYS', '7')),
    'health_check_interval': int(os.getenv('ADMIN_HEALTH_CHECK_INTERVAL', '60')),  # seconds
    'dashboard_refresh_interval': int(os.getenv('ADMIN_DASHBOARD_REFRESH', '30')),  # seconds
}

# Admin user roles and permissions
ADMIN_ROLES = {
    'super_admin': {
        'description': 'Full system access',
        'permissions': [
            'user_management',
            'system_configuration',
            'service_control',
            'log_analysis',
            'backup_restore',
            'security_management',
            'performance_monitoring',
            'database_management'
        ]
    },
    'admin': {
        'description': 'System administration access',
        'permissions': [
            'user_management',
            'service_control',
            'log_analysis',
            'performance_monitoring'
        ]
    },
    'operator': {
        'description': 'Basic operational access',
        'permissions': [
            'log_analysis',
            'performance_monitoring'
        ]
    }
}

# Service management configuration
SERVICE_CONFIG = {
    'services': {
        'frontend': {
            'name': 'Frontend',
            'port': 3091,
            'health_endpoint': '/health',
            'restart_command': 'docker-compose restart frontend',
            'log_file': '/var/log/suna/frontend.log'
        },
        'backend': {
            'name': 'Backend API',
            'port': 8091,
            'health_endpoint': '/health',
            'restart_command': 'docker-compose restart backend',
            'log_file': '/var/log/suna/backend.log'
        },
        'postgres': {
            'name': 'PostgreSQL Database',
            'port': 5491,
            'health_endpoint': None,
            'restart_command': 'docker-compose restart postgres',
            'log_file': '/var/log/suna/postgres.log'
        },
        'redis': {
            'name': 'Redis Cache',
            'port': 6391,
            'health_endpoint': None,
            'restart_command': 'docker-compose restart redis',
            'log_file': '/var/log/suna/redis.log'
        },
        'ollama': {
            'name': 'Ollama LLM Service',
            'port': 11434,
            'health_endpoint': '/api/tags',
            'restart_command': 'docker-compose restart ollama',
            'log_file': '/var/log/suna/ollama.log'
        },
        'prometheus': {
            'name': 'Prometheus Monitoring',
            'port': 9090,
            'health_endpoint': '/-/healthy',
            'restart_command': 'docker-compose restart prometheus',
            'log_file': '/var/log/suna/prometheus.log'
        },
        'grafana': {
            'name': 'Grafana Dashboard',
            'port': 3000,
            'health_endpoint': '/api/health',
            'restart_command': 'docker-compose restart grafana',
            'log_file': '/var/log/suna/grafana.log'
        },
        'nginx': {
            'name': 'Nginx Reverse Proxy',
            'port': 80,
            'health_endpoint': '/health',
            'restart_command': 'docker-compose restart nginx',
            'log_file': '/var/log/suna/nginx.log'
        }
    }
}

# Dashboard configuration
DASHBOARD_CONFIG = {
    'metrics': {
        'system': ['cpu_usage', 'memory_usage', 'disk_usage', 'network_io'],
        'application': ['request_rate', 'response_time', 'error_rate', 'active_users'],
        'database': ['connection_count', 'query_performance', 'cache_hit_rate'],
        'services': ['service_status', 'service_health', 'service_uptime']
    },
    'alerts': {
        'critical': ['service_down', 'high_cpu', 'high_memory', 'disk_full'],
        'warning': ['service_degraded', 'high_latency', 'low_disk_space'],
        'info': ['service_restart', 'backup_completed', 'update_available']
    }
}

__all__ = [
    'ADMIN_CONFIG',
    'ADMIN_ROLES', 
    'SERVICE_CONFIG',
    'DASHBOARD_CONFIG'
] 
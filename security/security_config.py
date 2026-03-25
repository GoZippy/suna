"""
Security configuration for Suna self-hosted deployment
Defines security policies, settings, and validation rules
"""

import os
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class SecurityLevel(Enum):
    """Security levels for different environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class PasswordPolicy:
    """Password policy configuration"""
    min_length: int = 12
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special: bool = True
    max_age_days: int = 90
    prevent_reuse: int = 5  # Number of previous passwords to prevent reuse


@dataclass
class SessionPolicy:
    """Session management policy"""
    max_session_duration_hours: int = 24
    idle_timeout_minutes: int = 30
    max_concurrent_sessions: int = 5
    require_reauthentication_for_admin: bool = True


@dataclass
class RateLimitPolicy:
    """Rate limiting policy"""
    api_default_limit: int = 100
    api_default_window: int = 60
    auth_login_limit: int = 5
    auth_login_window: int = 300
    auth_register_limit: int = 3
    auth_register_window: int = 3600
    admin_limit: int = 50
    admin_window: int = 60


@dataclass
class SecurityHeaders:
    """Security headers configuration"""
    content_security_policy: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none';"
    )
    x_frame_options: str = "DENY"
    x_content_type_options: str = "nosniff"
    x_xss_protection: str = "1; mode=block"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "geolocation=(), microphone=(), camera=()"


@dataclass
class SSLPolicy:
    """SSL/TLS configuration"""
    min_tls_version: str = "1.2"
    preferred_ciphers: List[str] = None
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False


@dataclass
class InputValidationPolicy:
    """Input validation policy"""
    max_body_size_mb: int = 10
    allowed_file_types: List[str] = None
    max_file_size_mb: int = 50
    suspicious_patterns: List[str] = None
    sql_injection_patterns: List[str] = None
    xss_patterns: List[str] = None


@dataclass
class AuditPolicy:
    """Audit logging policy"""
    log_all_requests: bool = True
    log_sensitive_operations: bool = True
    log_failed_attempts: bool = True
    retention_days: int = 90
    sensitive_endpoints: List[str] = None


class SecurityConfig:
    """Main security configuration class"""
    
    def __init__(self, environment: str = "development"):
        self.environment = SecurityLevel(environment)
        self.password_policy = self._get_password_policy()
        self.session_policy = self._get_session_policy()
        self.rate_limit_policy = self._get_rate_limit_policy()
        self.security_headers = self._get_security_headers()
        self.ssl_policy = self._get_ssl_policy()
        self.input_validation_policy = self._get_input_validation_policy()
        self.audit_policy = self._get_audit_policy()
    
    def _get_password_policy(self) -> PasswordPolicy:
        """Get password policy based on environment"""
        if self.environment == SecurityLevel.PRODUCTION:
            return PasswordPolicy(
                min_length=16,
                require_uppercase=True,
                require_lowercase=True,
                require_digits=True,
                require_special=True,
                max_age_days=60,
                prevent_reuse=10
            )
        elif self.environment == SecurityLevel.STAGING:
            return PasswordPolicy(
                min_length=14,
                require_uppercase=True,
                require_lowercase=True,
                require_digits=True,
                require_special=True,
                max_age_days=90,
                prevent_reuse=5
            )
        else:  # Development
            return PasswordPolicy(
                min_length=8,
                require_uppercase=False,
                require_lowercase=True,
                require_digits=True,
                require_special=False,
                max_age_days=365,
                prevent_reuse=0
            )
    
    def _get_session_policy(self) -> SessionPolicy:
        """Get session policy based on environment"""
        if self.environment == SecurityLevel.PRODUCTION:
            return SessionPolicy(
                max_session_duration_hours=8,
                idle_timeout_minutes=15,
                max_concurrent_sessions=3,
                require_reauthentication_for_admin=True
            )
        else:
            return SessionPolicy(
                max_session_duration_hours=24,
                idle_timeout_minutes=60,
                max_concurrent_sessions=10,
                require_reauthentication_for_admin=False
            )
    
    def _get_rate_limit_policy(self) -> RateLimitPolicy:
        """Get rate limiting policy based on environment"""
        if self.environment == SecurityLevel.PRODUCTION:
            return RateLimitPolicy(
                api_default_limit=50,
                api_default_window=60,
                auth_login_limit=3,
                auth_login_window=300,
                auth_register_limit=1,
                auth_register_window=3600,
                admin_limit=20,
                admin_window=60
            )
        else:
            return RateLimitPolicy()
    
    def _get_security_headers(self) -> SecurityHeaders:
        """Get security headers based on environment"""
        if self.environment == SecurityLevel.PRODUCTION:
            return SecurityHeaders(
                content_security_policy=(
                    "default-src 'self'; "
                    "script-src 'self'; "
                    "style-src 'self'; "
                    "img-src 'self' data:; "
                    "font-src 'self'; "
                    "connect-src 'self'; "
                    "frame-ancestors 'none';"
                ),
                x_frame_options="DENY",
                x_content_type_options="nosniff",
                x_xss_protection="1; mode=block",
                referrer_policy="strict-origin-when-cross-origin",
                permissions_policy="geolocation=(), microphone=(), camera=()"
            )
        else:
            return SecurityHeaders()
    
    def _get_ssl_policy(self) -> SSLPolicy:
        """Get SSL policy based on environment"""
        if self.environment == SecurityLevel.PRODUCTION:
            return SSLPolicy(
                min_tls_version="1.3",
                preferred_ciphers=[
                    "ECDHE-ECDSA-AES256-GCM-SHA384",
                    "ECDHE-RSA-AES256-GCM-SHA384",
                    "ECDHE-ECDSA-CHACHA20-POLY1305",
                    "ECDHE-RSA-CHACHA20-POLY1305"
                ],
                hsts_max_age=31536000,
                hsts_include_subdomains=True,
                hsts_preload=True
            )
        else:
            return SSLPolicy()
    
    def _get_input_validation_policy(self) -> InputValidationPolicy:
        """Get input validation policy based on environment"""
        return InputValidationPolicy(
            max_body_size_mb=10,
            allowed_file_types=[
                ".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
                ".json", ".xml", ".csv", ".pdf", ".doc", ".docx",
                ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico"
            ],
            max_file_size_mb=50,
            suspicious_patterns=[
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"vbscript:",
                r"onload=",
                r"onerror=",
                r"onclick=",
                r"<iframe[^>]*>",
                r"<object[^>]*>",
                r"<embed[^>]*>"
            ],
            sql_injection_patterns=[
                r"union\s+select",
                r"drop\s+table",
                r"delete\s+from",
                r"insert\s+into",
                r"update\s+set",
                r"exec\s*\(",
                r"eval\s*\("
            ],
            xss_patterns=[
                r"<script[^>]*>",
                r"javascript:",
                r"vbscript:",
                r"on\w+\s*=",
                r"<iframe[^>]*>",
                r"<object[^>]*>",
                r"<embed[^>]*>"
            ]
        )
    
    def _get_audit_policy(self) -> AuditPolicy:
        """Get audit policy based on environment"""
        return AuditPolicy(
            log_all_requests=True,
            log_sensitive_operations=True,
            log_failed_attempts=True,
            retention_days=90 if self.environment == SecurityLevel.PRODUCTION else 30,
            sensitive_endpoints=[
                "/api/auth/login",
                "/api/auth/register",
                "/api/admin",
                "/api/users",
                "/api/settings"
            ]
        )
    
    def get_rate_limits(self) -> Dict[str, Dict[str, int]]:
        """Get rate limiting configuration for middleware"""
        return {
            "/api/auth/login": {
                "limit": self.rate_limit_policy.auth_login_limit,
                "window": self.rate_limit_policy.auth_login_window
            },
            "/api/auth/register": {
                "limit": self.rate_limit_policy.auth_register_limit,
                "window": self.rate_limit_policy.auth_register_window
            },
            "/api/admin": {
                "limit": self.rate_limit_policy.admin_limit,
                "window": self.rate_limit_policy.admin_window
            },
            "/api/": {
                "limit": self.rate_limit_policy.api_default_limit,
                "window": self.rate_limit_policy.api_default_window
            }
        }
    
    def validate_password(self, password: str) -> Dict[str, Any]:
        """Validate password against policy"""
        errors = []
        
        if len(password) < self.password_policy.min_length:
            errors.append(f"Password must be at least {self.password_policy.min_length} characters long")
        
        if self.password_policy.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.password_policy.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.password_policy.require_digits and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if self.password_policy.require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def is_sensitive_endpoint(self, path: str) -> bool:
        """Check if endpoint is considered sensitive"""
        return any(sensitive in path for sensitive in self.audit_policy.sensitive_endpoints)


# Global security configuration instance
security_config = SecurityConfig(os.getenv("ENVIRONMENT", "development"))








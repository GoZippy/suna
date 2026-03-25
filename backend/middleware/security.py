"""
Security middleware for FastAPI application
Provides rate limiting, CORS, input validation, and security headers
"""

import time
import hashlib
import json
from typing import Dict, List, Optional, Callable
from collections import defaultdict
import re

from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

import structlog

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with configurable limits per endpoint"""
    
    def __init__(
        self,
        app: ASGIApp,
        default_limit: int = 100,
        default_window: int = 60,
        limits: Optional[Dict[str, Dict[str, int]]] = None
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.limits = limits or {}
        self.requests: Dict[str, List[float]] = defaultdict(list)
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Get client identifier (IP address or API key)
        client_id = self._get_client_id(request)
        
        # Get rate limit for this endpoint
        endpoint = request.url.path
        limit_config = self.limits.get(endpoint, {
            'limit': self.default_limit,
            'window': self.default_window
        })
        
        limit = limit_config['limit']
        window = limit_config['window']
        
        # Check rate limit
        current_time = time.time()
        client_requests = self.requests[client_id]
        
        # Remove old requests outside the window
        client_requests[:] = [req_time for req_time in client_requests 
                            if current_time - req_time < window]
        
        # Check if limit exceeded
        if len(client_requests) >= limit:
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                endpoint=endpoint,
                limit=limit,
                window=window
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": int(window - (current_time - client_requests[0]))
                }
            )
        
        # Add current request
        client_requests.append(current_time)
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(limit - len(client_requests))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + window))
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize input data"""
    
    def __init__(self, app: ASGIApp, max_body_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_body_size = max_body_size
        self.suspicious_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"onload=",
            r"onerror=",
            r"onclick=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"union\s+select",
            r"drop\s+table",
            r"delete\s+from",
            r"insert\s+into",
            r"update\s+set",
            r"exec\s*\(",
            r"eval\s*\(",
        ]
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request body too large"
            )
        
        # Validate request body for suspicious content
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8', errors='ignore')
                    if self._contains_suspicious_content(body_str):
                        logger.warning(
                            "Suspicious content detected in request",
                            client_ip=request.client.host,
                            path=request.url.path,
                            method=request.method
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid request content"
                        )
            except Exception as e:
                logger.error("Error validating request body", error=str(e))
        
        # Validate query parameters
        for param_name, param_value in request.query_params.items():
            if self._contains_suspicious_content(str(param_value)):
                logger.warning(
                    "Suspicious content in query parameter",
                    param_name=param_name,
                    client_ip=request.client.host
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid query parameter"
                )
        
        return await call_next(request)
    
    def _contains_suspicious_content(self, content: str) -> bool:
        """Check if content contains suspicious patterns"""
        content_lower = content.lower()
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        return False


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Log all requests for audit purposes"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host,
            user_agent=request.headers.get("user-agent"),
            content_length=request.headers.get("content-length")
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            duration = time.time() - start_time
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2)
            )
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_ms=round(duration * 1000, 2)
            )
            raise


def setup_security_middleware(app: ASGIApp) -> None:
    """Setup all security middleware for the FastAPI application"""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3091", "https://localhost:3091"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Rate limiting configuration
    rate_limits = {
        "/api/auth/login": {"limit": 5, "window": 300},  # 5 attempts per 5 minutes
        "/api/auth/register": {"limit": 3, "window": 3600},  # 3 attempts per hour
        "/api/admin": {"limit": 50, "window": 60},  # 50 requests per minute
        "/api/": {"limit": 100, "window": 60},  # 100 requests per minute
    }
    
    # Add security middleware in order
    app.add_middleware(AuditLogMiddleware)
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(RateLimitMiddleware, limits=rate_limits)
    app.add_middleware(SecurityHeadersMiddleware)








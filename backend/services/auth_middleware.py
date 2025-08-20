"""
Authentication middleware for FastAPI routes.
Provides JWT token validation and user context injection.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Callable
from services.auth import AuthService, User
from services.supabase import DBConnection
from utils.logger import logger
import functools

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)

# Global auth service instance
_auth_service: Optional[AuthService] = None

def get_auth_service() -> AuthService:
    """Get or create auth service instance"""
    global _auth_service
    if _auth_service is None:
        db = DBConnection()
        _auth_service = AuthService(db)
    return _auth_service

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get current user from JWT token.
    Returns None if no token or invalid token (for optional authentication).
    """
    if not credentials:
        return None
    
    try:
        auth_service = get_auth_service()
        payload = auth_service.verify_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if not user_id:
            return None
        
        user = await auth_service.get_user_by_id(user_id)
        return user
        
    except HTTPException:
        return None
    except Exception as e:
        logger.warning(f"Error getting current user: {e}")
        return None

async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """
    Get current active user from JWT token.
    Raises HTTPException if no user or user is inactive.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    return current_user

def require_role(required_role: str):
    """
    Decorator factory for role-based access control.
    
    Usage:
        @require_role("admin")
        async def admin_only_endpoint(user: User = Depends(get_current_active_user)):
            pass
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (should be injected by dependency)
            user = None
            for key, value in kwargs.items():
                if isinstance(value, User):
                    user = value
                    break
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            auth_service = get_auth_service()
            if not auth_service.has_permission(user, required_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class RoleChecker:
    """
    Dependency class for role-based access control.
    
    Usage:
        @app.get("/admin")
        async def admin_endpoint(user: User = Depends(RoleChecker("admin"))):
            pass
    """
    
    def __init__(self, required_role: str):
        self.required_role = required_role
    
    async def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        auth_service = get_auth_service()
        
        if not auth_service.has_permission(current_user, self.required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user

# Convenience dependency instances
require_admin = RoleChecker("admin")
require_moderator = RoleChecker("moderator")
require_user = RoleChecker("user")

async def extract_user_from_token(request: Request) -> Optional[User]:
    """
    Extract user from Authorization header without raising exceptions.
    Useful for middleware that needs optional user context.
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        auth_service = get_auth_service()
        payload = auth_service.verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            return None
        
        user = await auth_service.get_user_by_id(user_id)
        return user
        
    except Exception as e:
        logger.debug(f"Could not extract user from token: {e}")
        return None

def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user ID from JWT token without database lookup.
    Useful for quick user identification.
    """
    try:
        auth_service = get_auth_service()
        payload = auth_service.verify_token(token)
        return payload.get("sub")
    except Exception:
        return None

async def validate_api_key(request: Request) -> Optional[str]:
    """
    Validate API key from X-API-Key header.
    Returns user_id if valid, None otherwise.
    """
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    
    try:
        # TODO: Implement API key validation against database
        # This would check the api_keys table for valid keys
        # For now, return None to indicate API key auth is not implemented
        return None
    except Exception as e:
        logger.warning(f"Error validating API key: {e}")
        return None

class AuthenticationMiddleware:
    """
    Custom authentication middleware for request context.
    Adds user information to request state if available.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Try to extract user from token
            user = await extract_user_from_token(request)
            if user:
                scope["state"] = getattr(scope, "state", {})
                scope["state"]["user"] = user
                scope["state"]["user_id"] = user.id
            
            # Try to validate API key if no user token
            elif not user:
                user_id = await validate_api_key(request)
                if user_id:
                    scope["state"] = getattr(scope, "state", {})
                    scope["state"]["user_id"] = user_id
                    scope["state"]["auth_method"] = "api_key"
        
        await self.app(scope, receive, send)
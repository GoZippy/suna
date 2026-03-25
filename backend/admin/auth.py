"""
Admin authentication and authorization system
"""

import os
import jwt
import bcrypt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .models import (
    AdminUserCreate, AdminUserUpdate, AdminUserResponse, AdminLogin,
    AdminSession, AdminRole, PermissionCheck, PermissionResponse
)
from . import ADMIN_CONFIG, ADMIN_ROLES
from ..database import get_db
from ..database.models import User


# JWT configuration
JWT_SECRET = ADMIN_CONFIG['admin_secret']
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security scheme
security = HTTPBearer()


class AdminAuthService:
    """Admin authentication service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_admin_user(self, user_data: AdminUserCreate) -> AdminUserResponse:
        """Create a new admin user"""
        
        # Check if username already exists
        existing_user = self.db.query(User).filter(
            User.username == user_data.username
        ).first()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Check if email already exists
        existing_email = self.db.query(User).filter(
            User.email == user_data.email
        ).first()
        
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Hash password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(user_data.password.encode('utf-8'), salt)
        
        # Create user
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password.decode('utf-8'),
            full_name=user_data.full_name,
            is_active=user_data.is_active,
            role=user_data.role.value,
            is_admin=True
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return AdminUserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=AdminRole(user.role),
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login,
            login_attempts=0,
            locked_until=None
        )
    
    def authenticate_admin(self, login_data: AdminLogin, request: Request) -> AdminSession:
        """Authenticate admin user and create session"""
        
        # Find user
        user = self.db.query(User).filter(
            and_(
                User.username == login_data.username,
                User.is_admin == True
            )
        ).first()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=423, 
                detail=f"Account locked until {user.locked_until}"
            )
        
        # Check if account is active
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Account is inactive")
        
        # Verify password
        if not bcrypt.checkpw(login_data.password.encode('utf-8'), user.hashed_password.encode('utf-8')):
            # Increment login attempts
            user.login_attempts += 1
            
            # Lock account if max attempts exceeded
            if user.login_attempts >= ADMIN_CONFIG['max_login_attempts']:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            
            self.db.commit()
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Reset login attempts on successful login
        user.login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        # Create session
        session_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        
        # Get user permissions
        permissions = ADMIN_ROLES.get(user.role, {}).get('permissions', [])
        
        session = AdminSession(
            session_id=session_id,
            user_id=str(user.id),
            username=user.username,
            role=AdminRole(user.role),
            permissions=permissions,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        
        return session
    
    def create_jwt_token(self, session: AdminSession) -> str:
        """Create JWT token from session"""
        
        payload = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "username": session.username,
            "role": session.role.value,
            "permissions": session.permissions,
            "exp": session.expires_at,
            "iat": session.created_at
        }
        
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def verify_jwt_token(self, token: str) -> Optional[AdminSession]:
        """Verify JWT token and return session"""
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            # Check if token is expired
            exp_timestamp = payload.get("exp")
            if exp_timestamp and datetime.fromtimestamp(exp_timestamp) < datetime.utcnow():
                return None
            
            return AdminSession(
                session_id=payload["session_id"],
                user_id=payload["user_id"],
                username=payload["username"],
                role=AdminRole(payload["role"]),
                permissions=payload["permissions"],
                created_at=datetime.fromtimestamp(payload["iat"]),
                expires_at=datetime.fromtimestamp(exp_timestamp)
            )
            
        except jwt.PyJWTError:
            return None
    
    def get_admin_user(self, user_id: str) -> Optional[AdminUserResponse]:
        """Get admin user by ID"""
        
        user = self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.is_admin == True
            )
        ).first()
        
        if not user:
            return None
        
        return AdminUserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=AdminRole(user.role),
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login,
            login_attempts=user.login_attempts or 0,
            locked_until=user.locked_until
        )
    
    def update_admin_user(self, user_id: str, update_data: AdminUserUpdate) -> Optional[AdminUserResponse]:
        """Update admin user"""
        
        user = self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.is_admin == True
            )
        ).first()
        
        if not user:
            return None
        
        # Update fields
        if update_data.email is not None:
            # Check if email is already taken by another user
            existing_email = self.db.query(User).filter(
                and_(
                    User.email == update_data.email,
                    User.id != user_id
                )
            ).first()
            
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already exists")
            
            user.email = update_data.email
        
        if update_data.role is not None:
            user.role = update_data.role.value
        
        if update_data.full_name is not None:
            user.full_name = update_data.full_name
        
        if update_data.is_active is not None:
            user.is_active = update_data.is_active
        
        self.db.commit()
        self.db.refresh(user)
        
        return AdminUserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=AdminRole(user.role),
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login,
            login_attempts=user.login_attempts or 0,
            locked_until=user.locked_until
        )
    
    def delete_admin_user(self, user_id: str) -> bool:
        """Delete admin user"""
        
        user = self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.is_admin == True
            )
        ).first()
        
        if not user:
            return False
        
        self.db.delete(user)
        self.db.commit()
        
        return True
    
    def list_admin_users(self, skip: int = 0, limit: int = 100) -> List[AdminUserResponse]:
        """List admin users"""
        
        users = self.db.query(User).filter(
            User.is_admin == True
        ).offset(skip).limit(limit).all()
        
        return [
            AdminUserResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                role=AdminRole(user.role),
                full_name=user.full_name,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login,
                login_attempts=user.login_attempts or 0,
                locked_until=user.locked_until
            )
            for user in users
        ]
    
    def check_permission(self, session: AdminSession, permission: str) -> PermissionResponse:
        """Check if user has specific permission"""
        
        if permission in session.permissions:
            return PermissionResponse(has_permission=True)
        
        # Check if user has super admin role
        if session.role == AdminRole.SUPER_ADMIN:
            return PermissionResponse(has_permission=True)
        
        return PermissionResponse(
            has_permission=False,
            reason=f"Permission '{permission}' not granted",
            required_role="super_admin"
        )
    
    def require_permission(self, permission: str):
        """Dependency to require specific permission"""
        
        def permission_dependency(session: AdminSession = Depends(get_current_admin_session)):
            auth_service = AdminAuthService(next(get_db()))
            permission_check = auth_service.check_permission(session, permission)
            
            if not permission_check.has_permission:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission_check.reason}"
                )
            
            return session
        
        return permission_dependency


def get_current_admin_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db())
) -> AdminSession:
    """Get current admin session from JWT token"""
    
    auth_service = AdminAuthService(db)
    session = auth_service.verify_jwt_token(credentials.credentials)
    
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
    
    return session


def get_current_admin_user(
    session: AdminSession = Depends(get_current_admin_session),
    db: Session = Depends(get_db())
) -> AdminUserResponse:
    """Get current admin user"""
    
    auth_service = AdminAuthService(db)
    user = auth_service.get_admin_user(session.user_id)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )
    
    return user


# Permission decorators
def require_super_admin():
    """Require super admin role"""
    return AdminAuthService(next(get_db())).require_permission("system_configuration")


def require_admin():
    """Require admin role"""
    return AdminAuthService(next(get_db())).require_permission("user_management")


def require_operator():
    """Require operator role"""
    return AdminAuthService(next(get_db())).require_permission("log_analysis")








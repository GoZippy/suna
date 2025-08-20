"""
Authentication API endpoints for local authentication system.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer
from typing import List, Optional
from services.auth import (
    AuthService, User, UserCreate, UserLogin, UserUpdate, TokenData,
    UserRole, UserTier
)
from services.auth_middleware import (
    get_current_active_user, get_current_user, require_admin, 
    get_auth_service, RoleChecker
)
from services.supabase import DBConnection
from pydantic import BaseModel, EmailStr
from utils.logger import logger
import uuid

router = APIRouter(prefix="/auth", tags=["authentication"])

class RefreshTokenRequest(BaseModel):
    """Request model for token refresh"""
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    """Request model for password change"""
    current_password: str
    new_password: str

class UserResponse(BaseModel):
    """User response model (without sensitive data)"""
    id: str
    email: str
    role: str
    tier: str
    created_at: str
    updated_at: str
    is_active: bool

class UserListResponse(BaseModel):
    """User list response model"""
    users: List[UserResponse]
    total: int
    limit: int
    offset: int

def user_to_response(user: User) -> UserResponse:
    """Convert User model to UserResponse"""
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        tier=user.tier,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
        is_active=user.is_active
    )

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user.
    Only admins can create users with admin or moderator roles.
    """
    try:
        # For now, allow anyone to register as a regular user
        # In production, you might want to restrict this
        if user_data.role in [UserRole.ADMIN, UserRole.MODERATOR]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot register with elevated privileges"
            )
        
        user = await auth_service.create_user(user_data)
        return user_to_response(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=TokenData)
async def login_user(
    login_data: UserLogin,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login user and return access and refresh tokens.
    """
    try:
        token_data = await auth_service.login_user(login_data)
        
        # Set refresh token as httpOnly cookie for security
        response.set_cookie(
            key="refresh_token",
            value=token_data.refresh_token,
            httponly=True,
            secure=True,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        
        return token_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh", response_model=TokenData)
async def refresh_token(
    request: Request,
    refresh_request: Optional[RefreshTokenRequest] = None,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token.
    Accepts refresh token from request body or cookie.
    """
    try:
        # Try to get refresh token from request body first, then from cookie
        refresh_token = None
        if refresh_request and refresh_request.refresh_token:
            refresh_token = refresh_request.refresh_token
        else:
            refresh_token = request.cookies.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not provided"
            )
        
        token_data = await auth_service.refresh_access_token(refresh_token)
        return token_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout_user(
    request: Request,
    response: Response,
    refresh_request: Optional[RefreshTokenRequest] = None,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout user by invalidating refresh token.
    """
    try:
        # Try to get refresh token from request body first, then from cookie
        refresh_token = None
        if refresh_request and refresh_request.refresh_token:
            refresh_token = refresh_request.refresh_token
        else:
            refresh_token = request.cookies.get("refresh_token")
        
        if refresh_token:
            await auth_service.logout_user(refresh_token)
        
        # Clear refresh token cookie
        response.delete_cookie(key="refresh_token")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Don't raise exception for logout errors
        response.delete_cookie(key="refresh_token")
        return {"message": "Logged out"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.
    """
    return user_to_response(current_user)

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Update current user information.
    Users can only update their own email and password.
    """
    try:
        # Users cannot change their own role or tier
        if update_data.role is not None or update_data.tier is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify role or tier"
            )
        
        updated_user = await auth_service.update_user(current_user.id, update_data)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user_to_response(updated_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed"
        )

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Change user password.
    """
    try:
        # Verify current password
        authenticated_user = await auth_service.authenticate_user(
            current_user.email, 
            password_data.current_password
        )
        
        if not authenticated_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        update_data = UserUpdate(password=password_data.new_password)
        updated_user = await auth_service.update_user(current_user.id, update_data)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password change failed"
            )
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

# Admin endpoints
@router.get("/users", response_model=UserListResponse)
async def list_users(
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    List all users (admin only).
    """
    try:
        users = await auth_service.list_users(limit=limit, offset=offset)
        user_responses = [user_to_response(user) for user in users]
        
        return UserListResponse(
            users=user_responses,
            total=len(user_responses),  # TODO: Implement proper total count
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    user_data: UserCreate,
    admin_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Create a new user (admin only).
    Admins can create users with any role.
    """
    try:
        user = await auth_service.create_user(user_data)
        return user_to_response(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User creation failed"
        )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_admin(
    user_id: str,
    admin_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Get user by ID (admin only).
    """
    try:
        user = await auth_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user_to_response(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        )

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_admin(
    user_id: str,
    update_data: UserUpdate,
    admin_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Update user by ID (admin only).
    Admins can update any user field including role and tier.
    """
    try:
        updated_user = await auth_service.update_user(user_id, update_data)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user_to_response(updated_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed"
        )

@router.delete("/users/{user_id}")
async def delete_user_admin(
    user_id: str,
    admin_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Delete user by ID (admin only).
    This performs a soft delete by setting is_active to False.
    """
    try:
        # Prevent admin from deleting themselves
        if user_id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        success = await auth_service.delete_user(user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User deletion failed"
        )

@router.get("/validate-token")
async def validate_token(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Validate current token and return user info if valid.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return {
        "valid": True,
        "user": user_to_response(current_user)
    }
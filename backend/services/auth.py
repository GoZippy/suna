"""
Local authentication service for self-hosted Suna deployment.
Replaces Supabase Auth with JWT-based authentication.
"""

import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, validator
from fastapi import HTTPException, status
from passlib.context import CryptContext
from jose import JWTError, jwt as jose_jwt
import secrets
import uuid
from utils.logger import logger
from utils.config import config
import re

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
JWT_SECRET_KEY = config.JWT_SECRET_KEY or secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

class UserRole:
    """User role constants"""
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"

class UserTier:
    """User tier constants"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class UserCreate(BaseModel):
    """User creation model"""
    email: EmailStr
    password: str
    role: str = UserRole.USER
    tier: str = UserTier.FREE
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('role')
    def validate_role(cls, v):
        """Validate user role"""
        valid_roles = [UserRole.ADMIN, UserRole.USER, UserRole.MODERATOR]
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v
    
    @validator('tier')
    def validate_tier(cls, v):
        """Validate user tier"""
        valid_tiers = [UserTier.FREE, UserTier.PRO, UserTier.ENTERPRISE]
        if v not in valid_tiers:
            raise ValueError(f'Tier must be one of: {", ".join(valid_tiers)}')
        return v

class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    """User update model"""
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    tier: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength if provided"""
        if v is not None:
            if len(v) < 8:
                raise ValueError('Password must be at least 8 characters long')
            if not re.search(r'[A-Z]', v):
                raise ValueError('Password must contain at least one uppercase letter')
            if not re.search(r'[a-z]', v):
                raise ValueError('Password must contain at least one lowercase letter')
            if not re.search(r'\d', v):
                raise ValueError('Password must contain at least one digit')
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
                raise ValueError('Password must contain at least one special character')
        return v

class TokenData(BaseModel):
    """Token data model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class User(BaseModel):
    """User model"""
    id: str
    email: str
    role: str
    tier: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

class AuthService:
    """Local authentication service"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jose_jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jose_jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jose_jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != token_type:
                raise JWTError("Invalid token type")
            return payload
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        try:
            client = await self.db.client
            
            # Check if user already exists
            existing_user = await client.table("users").select("*").eq("email", user_data.email).execute()
            if existing_user.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
            
            # Hash password
            hashed_password = self.hash_password(user_data.password)
            
            # Create user record
            user_record = {
                "id": str(uuid.uuid4()),
                "email": user_data.email,
                "password_hash": hashed_password,
                "role": user_data.role,
                "tier": user_data.tier,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
            
            result = await client.table("users").insert(user_record).execute()
            
            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user"
                )
            
            created_user = result.data[0]
            logger.info(f"User created successfully: {created_user['email']}")
            
            return User(
                id=created_user["id"],
                email=created_user["email"],
                role=created_user["role"],
                tier=created_user["tier"],
                created_at=datetime.fromisoformat(created_user["created_at"].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(created_user["updated_at"].replace('Z', '+00:00')),
                is_active=created_user["is_active"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        try:
            client = await self.db.client
            
            # Get user by email
            result = await client.table("users").select("*").eq("email", email).execute()
            
            if not result.data:
                return None
            
            user_data = result.data[0]
            
            # Check if user is active
            if not user_data.get("is_active", True):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is disabled"
                )
            
            # Verify password
            if not self.verify_password(password, user_data["password_hash"]):
                return None
            
            return User(
                id=user_data["id"],
                email=user_data["email"],
                role=user_data["role"],
                tier=user_data["tier"],
                created_at=datetime.fromisoformat(user_data["created_at"].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(user_data["updated_at"].replace('Z', '+00:00')),
                is_active=user_data["is_active"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None
    
    async def login_user(self, login_data: UserLogin) -> TokenData:
        """Login user and return tokens"""
        user = await self.authenticate_user(login_data.email, login_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create tokens
        access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": user.id, "email": user.email, "role": user.role, "tier": user.tier},
            expires_delta=access_token_expires
        )
        
        refresh_token = self.create_refresh_token(
            data={"sub": user.id, "email": user.email}
        )
        
        # Store refresh token in database
        await self.store_refresh_token(user.id, refresh_token)
        
        logger.info(f"User logged in successfully: {user.email}")
        
        return TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    async def refresh_access_token(self, refresh_token: str) -> TokenData:
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            payload = self.verify_token(refresh_token, "refresh")
            user_id = payload.get("sub")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            # Check if refresh token exists in database
            client = await self.db.client
            token_result = await client.table("user_sessions").select("*").eq("user_id", user_id).eq("token_hash", self.hash_token(refresh_token)).execute()
            
            if not token_result.data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            # Get user data
            user_result = await client.table("users").select("*").eq("id", user_id).execute()
            
            if not user_result.data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            user_data = user_result.data[0]
            
            # Create new access token
            access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = self.create_access_token(
                data={"sub": user_data["id"], "email": user_data["email"], "role": user_data["role"], "tier": user_data["tier"]},
                expires_delta=access_token_expires
            )
            
            return TokenData(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not refresh token"
            )
    
    def hash_token(self, token: str) -> str:
        """Hash token for storage"""
        return bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    async def store_refresh_token(self, user_id: str, refresh_token: str):
        """Store refresh token in database"""
        try:
            client = await self.db.client
            
            # Clean up expired tokens for this user
            await self.cleanup_expired_tokens(user_id)
            
            # Store new refresh token
            token_record = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "token_hash": self.hash_token(refresh_token),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await client.table("user_sessions").insert(token_record).execute()
            
        except Exception as e:
            logger.error(f"Error storing refresh token: {e}")
            # Don't raise exception as this is not critical for login
    
    async def cleanup_expired_tokens(self, user_id: str):
        """Clean up expired refresh tokens for a user"""
        try:
            client = await self.db.client
            current_time = datetime.now(timezone.utc).isoformat()
            
            await client.table("user_sessions").delete().eq("user_id", user_id).lt("expires_at", current_time).execute()
            
        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {e}")
    
    async def logout_user(self, refresh_token: str):
        """Logout user by invalidating refresh token"""
        try:
            client = await self.db.client
            token_hash = self.hash_token(refresh_token)
            
            await client.table("user_sessions").delete().eq("token_hash", token_hash).execute()
            
        except Exception as e:
            logger.error(f"Error logging out user: {e}")
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            client = await self.db.client
            result = await client.table("users").select("*").eq("id", user_id).execute()
            
            if not result.data:
                return None
            
            user_data = result.data[0]
            
            return User(
                id=user_data["id"],
                email=user_data["email"],
                role=user_data["role"],
                tier=user_data["tier"],
                created_at=datetime.fromisoformat(user_data["created_at"].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(user_data["updated_at"].replace('Z', '+00:00')),
                is_active=user_data["is_active"]
            )
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    async def update_user(self, user_id: str, update_data: UserUpdate) -> Optional[User]:
        """Update user information"""
        try:
            client = await self.db.client
            
            # Prepare update data
            update_fields = {"updated_at": datetime.now(timezone.utc).isoformat()}
            
            if update_data.email is not None:
                # Check if email is already taken by another user
                existing_user = await client.table("users").select("*").eq("email", update_data.email).neq("id", user_id).execute()
                if existing_user.data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already taken by another user"
                    )
                update_fields["email"] = update_data.email
            
            if update_data.password is not None:
                update_fields["password_hash"] = self.hash_password(update_data.password)
            
            if update_data.role is not None:
                update_fields["role"] = update_data.role
            
            if update_data.tier is not None:
                update_fields["tier"] = update_data.tier
            
            # Update user
            result = await client.table("users").update(update_fields).eq("id", user_id).execute()
            
            if not result.data:
                return None
            
            updated_user = result.data[0]
            logger.info(f"User updated successfully: {updated_user['email']}")
            
            return User(
                id=updated_user["id"],
                email=updated_user["email"],
                role=updated_user["role"],
                tier=updated_user["tier"],
                created_at=datetime.fromisoformat(updated_user["created_at"].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(updated_user["updated_at"].replace('Z', '+00:00')),
                is_active=updated_user["is_active"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete by setting is_active to False)"""
        try:
            client = await self.db.client
            
            # Soft delete user
            result = await client.table("users").update({
                "is_active": False,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", user_id).execute()
            
            if result.data:
                # Clean up user sessions
                await client.table("user_sessions").delete().eq("user_id", user_id).execute()
                logger.info(f"User deleted successfully: {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    async def list_users(self, limit: int = 50, offset: int = 0) -> List[User]:
        """List all users with pagination"""
        try:
            client = await self.db.client
            
            result = await client.table("users").select("*").eq("is_active", True).range(offset, offset + limit - 1).execute()
            
            users = []
            for user_data in result.data:
                users.append(User(
                    id=user_data["id"],
                    email=user_data["email"],
                    role=user_data["role"],
                    tier=user_data["tier"],
                    created_at=datetime.fromisoformat(user_data["created_at"].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(user_data["updated_at"].replace('Z', '+00:00')),
                    is_active=user_data["is_active"]
                ))
            
            return users
            
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    def has_permission(self, user: User, required_role: str) -> bool:
        """Check if user has required role permission"""
        role_hierarchy = {
            UserRole.USER: 1,
            UserRole.MODERATOR: 2,
            UserRole.ADMIN: 3
        }
        
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
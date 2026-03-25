"""
Unit tests for authentication system
"""

import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from auth.models import User, UserCreate, UserLogin
from auth.password import hash_password, verify_password
from auth.jwt import create_access_token, verify_token, get_current_user
from auth.exceptions import AuthenticationError, InvalidCredentialsError


class TestPasswordHashing:
    """Test password hashing and verification"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > len(password)
        assert hashed.startswith("$2b$")
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_hash_password_different_salts(self):
        """Test that same password produces different hashes"""
        password = "testpassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTToken:
    """Test JWT token creation and validation"""
    
    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "test@example.com", "user_id": 1}
        token = create_access_token(data=data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode token to verify content
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["sub"] == "test@example.com"
        assert decoded["user_id"] == 1
        assert "exp" in decoded
    
    def test_create_access_token_with_expiry(self):
        """Test JWT token creation with custom expiry"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data=data, expires_delta=expires_delta)
        
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
        exp_time = datetime.fromtimestamp(decoded["exp"])
        now = datetime.now()
        
        # Token should expire in approximately 30 minutes
        assert (exp_time - now).total_seconds() > 29 * 60  # 29 minutes
        assert (exp_time - now).total_seconds() < 31 * 60  # 31 minutes
    
    def test_verify_token_valid(self):
        """Test valid token verification"""
        data = {"sub": "test@example.com", "user_id": 1}
        token = create_access_token(data=data)
        
        payload = verify_token(token)
        assert payload["sub"] == "test@example.com"
        assert payload["user_id"] == 1
    
    def test_verify_token_invalid(self):
        """Test invalid token verification"""
        with pytest.raises(AuthenticationError):
            verify_token("invalid-token")
    
    def test_verify_token_expired(self):
        """Test expired token verification"""
        data = {"sub": "test@example.com"}
        # Create token with past expiry
        token = jwt.encode(
            {
                **data,
                "exp": datetime.utcnow() - timedelta(hours=1)
            },
            "test-secret",
            algorithm="HS256"
        )
        
        with pytest.raises(AuthenticationError):
            verify_token(token)


class TestUserModels:
    """Test user model validation"""
    
    def test_user_create_valid(self):
        """Test valid user creation"""
        user_data = UserCreate(
            email="test@example.com",
            password="testpassword123",
            username="testuser",
            full_name="Test User"
        )
        
        assert user_data.email == "test@example.com"
        assert user_data.password == "testpassword123"
        assert user_data.username == "testuser"
        assert user_data.full_name == "Test User"
    
    def test_user_create_invalid_email(self):
        """Test user creation with invalid email"""
        with pytest.raises(ValueError):
            UserCreate(
                email="invalid-email",
                password="testpassword123",
                username="testuser",
                full_name="Test User"
            )
    
    def test_user_create_weak_password(self):
        """Test user creation with weak password"""
        with pytest.raises(ValueError):
            UserCreate(
                email="test@example.com",
                password="123",  # Too short
                username="testuser",
                full_name="Test User"
            )
    
    def test_user_login_valid(self):
        """Test valid user login"""
        login_data = UserLogin(
            email="test@example.com",
            password="testpassword123"
        )
        
        assert login_data.email == "test@example.com"
        assert login_data.password == "testpassword123"


class TestAuthenticationService:
    """Test authentication service functions"""
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, database_pool, test_user):
        """Test successful user authentication"""
        from auth.service import authenticate_user
        
        # Test with correct credentials
        user = await authenticate_user(
            database_pool, "test@example.com", "testpassword123"
        )
        
        assert user is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_email(self, database_pool):
        """Test authentication with invalid email"""
        from auth.service import authenticate_user
        
        # Test with non-existent email
        user = await authenticate_user(
            database_pool, "nonexistent@example.com", "testpassword123"
        )
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self, database_pool, test_user):
        """Test authentication with invalid password"""
        from auth.service import authenticate_user
        
        # Test with wrong password
        user = await authenticate_user(
            database_pool, "test@example.com", "wrongpassword"
        )
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, database_pool, clean_database):
        """Test successful user creation"""
        from auth.service import create_user
        
        user_data = UserCreate(
            email="newuser@example.com",
            password="newpassword123",
            username="newuser",
            full_name="New User"
        )
        
        user = await create_user(database_pool, user_data)
        
        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.full_name == "New User"
        assert user.is_active is True
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, database_pool, test_user):
        """Test user creation with duplicate email"""
        from auth.service import create_user
        
        user_data = UserCreate(
            email="test@example.com",  # Same as test_user
            password="newpassword123",
            username="newuser",
            full_name="New User"
        )
        
        with pytest.raises(ValueError):
            await create_user(database_pool, user_data)
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, database_pool, test_user):
        """Test user creation with duplicate username"""
        from auth.service import create_user
        
        user_data = UserCreate(
            email="newuser@example.com",
            password="newpassword123",
            username="testuser",  # Same as test_user
            full_name="New User"
        )
        
        with pytest.raises(ValueError):
            await create_user(database_pool, user_data)


class TestCurrentUserDependency:
    """Test get_current_user dependency"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, database_pool, test_user):
        """Test getting current user with valid token"""
        token = create_access_token(data={"sub": test_user.email})
        
        user = await get_current_user(database_pool, token)
        
        assert user is not None
        assert user.email == test_user.email
        assert user.id == test_user.id
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, database_pool):
        """Test getting current user with invalid token"""
        with pytest.raises(AuthenticationError):
            await get_current_user(database_pool, "invalid-token")
    
    @pytest.mark.asyncio
    async def test_get_current_user_nonexistent_user(self, database_pool):
        """Test getting current user with token for non-existent user"""
        token = create_access_token(data={"sub": "nonexistent@example.com"})
        
        with pytest.raises(AuthenticationError):
            await get_current_user(database_pool, token)
    
    @pytest.mark.asyncio
    async def test_get_current_user_inactive_user(self, database_pool, test_user):
        """Test getting current user with inactive user"""
        # Deactivate user
        async with database_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_active = false WHERE id = $1",
                test_user.id
            )
        
        token = create_access_token(data={"sub": test_user.email})
        
        with pytest.raises(AuthenticationError):
            await get_current_user(database_pool, token)


class TestPasswordValidation:
    """Test password validation rules"""
    
    def test_password_validation_minimum_length(self):
        """Test password minimum length validation"""
        from auth.password import validate_password
        
        # Too short password
        with pytest.raises(ValueError):
            validate_password("123")
        
        # Valid password
        validate_password("testpassword123")
    
    def test_password_validation_complexity(self):
        """Test password complexity requirements"""
        from auth.password import validate_password
        
        # Password without numbers
        with pytest.raises(ValueError):
            validate_password("testpassword")
        
        # Password without letters
        with pytest.raises(ValueError):
            validate_password("123456789")
        
        # Valid password
        validate_password("testpassword123")
    
    def test_password_validation_common_passwords(self):
        """Test password against common password list"""
        from auth.password import validate_password
        
        # Common password
        with pytest.raises(ValueError):
            validate_password("password123")
        
        # Valid password
        validate_password("MySecurePassword123!")








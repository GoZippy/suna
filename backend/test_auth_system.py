"""
Test script for the local authentication system.
This script tests the core authentication functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from services.auth import AuthService, UserCreate, UserLogin, UserRole, UserTier
from services.supabase import DBConnection
from utils.logger import logger

async def test_auth_system():
    """Test the authentication system functionality."""
    try:
        # Initialize database connection
        db = DBConnection()
        await db.initialize()
        auth_service = AuthService(db)
        
        logger.info("Testing authentication system...")
        
        # Test 1: Create a test user
        logger.info("Test 1: Creating test user...")
        test_user_data = UserCreate(
            email="test@example.com",
            password="TestPass123!",
            role=UserRole.USER,
            tier=UserTier.FREE
        )
        
        try:
            test_user = await auth_service.create_user(test_user_data)
            logger.info(f"✓ User created successfully: {test_user.email}")
        except Exception as e:
            logger.error(f"✗ Failed to create user: {e}")
            return False
        
        # Test 2: Login with the test user
        logger.info("Test 2: Testing user login...")
        login_data = UserLogin(
            email="test@example.com",
            password="TestPass123!"
        )
        
        try:
            token_data = await auth_service.login_user(login_data)
            logger.info(f"✓ Login successful, access token generated")
            logger.info(f"  Token type: {token_data.token_type}")
            logger.info(f"  Expires in: {token_data.expires_in} seconds")
        except Exception as e:
            logger.error(f"✗ Login failed: {e}")
            return False
        
        # Test 3: Verify token
        logger.info("Test 3: Testing token verification...")
        try:
            payload = auth_service.verify_token(token_data.access_token)
            logger.info(f"✓ Token verified successfully")
            logger.info(f"  User ID: {payload.get('sub')}")
            logger.info(f"  Email: {payload.get('email')}")
            logger.info(f"  Role: {payload.get('role')}")
        except Exception as e:
            logger.error(f"✗ Token verification failed: {e}")
            return False
        
        # Test 4: Get user by ID
        logger.info("Test 4: Testing get user by ID...")
        try:
            user_id = payload.get('sub')
            retrieved_user = await auth_service.get_user_by_id(user_id)
            if retrieved_user:
                logger.info(f"✓ User retrieved successfully: {retrieved_user.email}")
            else:
                logger.error("✗ User not found")
                return False
        except Exception as e:
            logger.error(f"✗ Failed to get user: {e}")
            return False
        
        # Test 5: Refresh token
        logger.info("Test 5: Testing token refresh...")
        try:
            new_token_data = await auth_service.refresh_access_token(token_data.refresh_token)
            logger.info(f"✓ Token refreshed successfully")
        except Exception as e:
            logger.error(f"✗ Token refresh failed: {e}")
            return False
        
        # Test 6: Password hashing
        logger.info("Test 6: Testing password hashing...")
        try:
            password = "TestPassword123!"
            hashed = auth_service.hash_password(password)
            is_valid = auth_service.verify_password(password, hashed)
            if is_valid:
                logger.info("✓ Password hashing and verification working")
            else:
                logger.error("✗ Password verification failed")
                return False
        except Exception as e:
            logger.error(f"✗ Password hashing test failed: {e}")
            return False
        
        # Test 7: Role-based permissions
        logger.info("Test 7: Testing role-based permissions...")
        try:
            # Test user should not have admin permissions
            has_admin_perm = auth_service.has_permission(retrieved_user, UserRole.ADMIN)
            has_user_perm = auth_service.has_permission(retrieved_user, UserRole.USER)
            
            if not has_admin_perm and has_user_perm:
                logger.info("✓ Role-based permissions working correctly")
            else:
                logger.error("✗ Role-based permissions not working correctly")
                return False
        except Exception as e:
            logger.error(f"✗ Role permission test failed: {e}")
            return False
        
        # Cleanup: Delete test user
        logger.info("Cleanup: Deleting test user...")
        try:
            success = await auth_service.delete_user(test_user.id)
            if success:
                logger.info("✓ Test user deleted successfully")
            else:
                logger.warning("⚠ Failed to delete test user")
        except Exception as e:
            logger.warning(f"⚠ Cleanup failed: {e}")
        
        logger.info("🎉 All authentication tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Authentication test failed: {e}")
        return False
    finally:
        await db.disconnect()

async def main():
    """Main test function."""
    logger.info("Starting authentication system tests...")
    
    success = await test_auth_system()
    
    if success:
        logger.info("✅ Authentication system is working correctly!")
        sys.exit(0)
    else:
        logger.error("❌ Authentication system tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
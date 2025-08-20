"""
Database initialization script for authentication tables.
Run this script to set up the local authentication system.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.supabase import DBConnection
from utils.logger import logger
from utils.config import config

async def run_migration():
    """Run the authentication tables migration."""
    try:
        # Initialize database connection
        db = DBConnection()
        await db.initialize()
        client = await db.client
        
        # Read the migration SQL file
        migration_file = Path(__file__).parent / "migrations" / "001_create_auth_tables.sql"
        
        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        logger.info("Running authentication tables migration...")
        
        # Execute the migration
        # Note: Supabase client doesn't support raw SQL execution directly
        # This would need to be run manually in the database or via a different method
        logger.warning("This migration needs to be run manually in your PostgreSQL database.")
        logger.info("Please execute the SQL in: backend/database/migrations/001_create_auth_tables.sql")
        
        # For now, just check if the users table exists
        try:
            result = await client.table("users").select("id").limit(1).execute()
            logger.info("Users table exists - migration appears to be complete")
            return True
        except Exception as e:
            logger.error(f"Users table does not exist. Please run the migration SQL manually: {e}")
            return False
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
    finally:
        await db.disconnect()

async def create_default_admin():
    """Create default admin user if it doesn't exist."""
    try:
        from services.auth import AuthService, UserCreate, UserRole, UserTier
        
        db = DBConnection()
        await db.initialize()
        auth_service = AuthService(db)
        
        # Check if admin user already exists
        admin_email = "admin@localhost"
        
        try:
            client = await db.client
            existing_admin = await client.table("users").select("*").eq("email", admin_email).execute()
            
            if existing_admin.data:
                logger.info(f"Admin user already exists: {admin_email}")
                return True
        except Exception:
            # Table might not exist yet
            pass
        
        # Create admin user
        admin_data = UserCreate(
            email=admin_email,
            password="Admin123!",  # This should be changed immediately
            role=UserRole.ADMIN,
            tier=UserTier.ENTERPRISE
        )
        
        try:
            admin_user = await auth_service.create_user(admin_data)
            logger.info(f"Default admin user created: {admin_user.email}")
            logger.warning("IMPORTANT: Change the default admin password immediately!")
            logger.info("Default credentials - Email: admin@localhost, Password: Admin123!")
            return True
        except Exception as e:
            logger.error(f"Failed to create admin user: {e}")
            return False
        
    except Exception as e:
        logger.error(f"Error creating default admin: {e}")
        return False
    finally:
        await db.disconnect()

async def main():
    """Main initialization function."""
    logger.info("Initializing authentication system...")
    
    # Run migration
    migration_success = await run_migration()
    
    if migration_success:
        # Create default admin user
        admin_success = await create_default_admin()
        
        if admin_success:
            logger.info("Authentication system initialization complete!")
            logger.info("You can now:")
            logger.info("1. Login with admin@localhost / Admin123!")
            logger.info("2. Access admin interface at /api/admin/")
            logger.info("3. Create additional users via API or admin interface")
        else:
            logger.error("Failed to create default admin user")
    else:
        logger.error("Migration failed - please run the SQL migration manually")

if __name__ == "__main__":
    asyncio.run(main())
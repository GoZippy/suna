#!/usr/bin/env python3
"""
Test script to verify database connection and setup
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from database.connection import db_manager
from database.models import User, Project, Thread

async def test_database_connection():
    """Test database connection and basic operations"""
    
    print("Testing database connection...")
    
    try:
        # Initialize database manager
        await db_manager.initialize()
        print("✓ Database connection initialized")
        
        # Test raw connection
        async with db_manager.get_connection() as conn:
            result = await conn.fetchval('SELECT version()')
            print(f"✓ PostgreSQL version: {result}")
            
            # Test pgvector extension
            extensions = await conn.fetch("""
                SELECT extname FROM pg_extension 
                WHERE extname IN ('uuid-ossp', 'vector', 'pg_trgm')
            """)
            print(f"✓ Extensions installed: {[ext['extname'] for ext in extensions]}")
        
        # Test Redis connection
        async with db_manager.get_redis() as redis:
            await redis.ping()
            print("✓ Redis connection successful")
        
        # Test SQLAlchemy session
        async with db_manager.get_session() as session:
            # Test basic query
            from sqlalchemy import text
            result = await session.execute(text('SELECT 1 as test'))
            test_value = result.scalar()
            print(f"✓ SQLAlchemy session test: {test_value}")
        
        print("\n✓ All database tests passed!")
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        raise
    
    finally:
        await db_manager.close()

async def test_table_creation():
    """Test that all tables exist"""
    
    print("\nTesting table structure...")
    
    try:
        await db_manager.initialize()
        
        async with db_manager.get_connection() as conn:
            # Get list of tables
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            table_names = [table['table_name'] for table in tables]
            print(f"✓ Found {len(table_names)} tables:")
            for table in table_names:
                print(f"  - {table}")
            
            # Check specific important tables
            expected_tables = [
                'users', 'user_sessions', 'user_tiers',
                'projects', 'threads', 'messages',
                'knowledge_base', 'usage_logs'
            ]
            
            missing_tables = [t for t in expected_tables if t not in table_names]
            if missing_tables:
                print(f"✗ Missing tables: {missing_tables}")
            else:
                print("✓ All expected tables found")
        
    except Exception as e:
        print(f"✗ Table test failed: {e}")
        raise
    
    finally:
        await db_manager.close()

async def main():
    """Run all tests"""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    print("Suna Database Connection Test")
    print("=" * 40)
    
    await test_database_connection()
    await test_table_creation()
    
    print("\n" + "=" * 40)
    print("Database setup verification complete!")

if __name__ == '__main__':
    asyncio.run(main())
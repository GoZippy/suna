"""
Initialize vector database with pgvector extension and tables
"""

import asyncio
import os
from pathlib import Path
from database.connection import db_manager
from utils.logger import logger

async def run_migration_file(file_path: Path):
    """Run a SQL migration file"""
    try:
        with open(file_path, 'r') as f:
            sql_content = f.read()
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        async with db_manager.get_connection() as conn:
            for statement in statements:
                if statement:
                    try:
                        await conn.execute(statement)
                        logger.debug(f"Executed: {statement[:100]}...")
                    except Exception as e:
                        # Log but continue with other statements
                        logger.warning(f"Statement failed (continuing): {e}")
                        logger.debug(f"Failed statement: {statement}")
        
        logger.info(f"Successfully ran migration: {file_path.name}")
        
    except Exception as e:
        logger.error(f"Error running migration {file_path.name}: {e}")
        raise

async def initialize_vector_database():
    """Initialize the vector database with all required tables and extensions"""
    try:
        await db_manager.initialize()
        
        # Get migrations directory
        migrations_dir = Path(__file__).parent / "migrations"
        
        # Run migrations in order
        migration_files = [
            "001_create_auth_tables.sql",
            "002_create_vector_tables.sql"
        ]
        
        for migration_file in migration_files:
            migration_path = migrations_dir / migration_file
            if migration_path.exists():
                await run_migration_file(migration_path)
            else:
                logger.warning(f"Migration file not found: {migration_file}")
        
        # Verify pgvector extension is working
        async with db_manager.get_connection() as conn:
            result = await conn.fetchval("SELECT vector_dims(ARRAY[1,2,3]::vector)")
            if result == 3:
                logger.info("pgvector extension is working correctly")
            else:
                logger.error("pgvector extension test failed")
        
        logger.info("Vector database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Vector database initialization failed: {e}")
        raise

async def create_sample_data():
    """Create some sample data for testing"""
    try:
        from services.vector_database import vector_db_service
        from uuid import uuid4
        
        await vector_db_service.initialize()
        
        # Sample documents
        sample_docs = [
            {
                "title": "Python Programming Basics",
                "content": "Python is a high-level programming language known for its simplicity and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
                "content_type": "text",
                "source_type": "manual"
            },
            {
                "title": "Machine Learning Introduction",
                "content": "Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed for every task.",
                "content_type": "text",
                "source_type": "manual"
            },
            {
                "title": "Vector Databases",
                "content": "Vector databases are specialized databases designed to store and query high-dimensional vectors efficiently. They are essential for similarity search and AI applications.",
                "content_type": "text",
                "source_type": "manual"
            }
        ]
        
        # Create a sample user and project (you may need to adjust this based on your auth system)
        sample_user_id = uuid4()
        sample_project_id = uuid4()
        
        # Add sample documents
        for doc in sample_docs:
            await vector_db_service.add_document(
                content=doc["content"],
                user_id=sample_user_id,
                project_id=sample_project_id,
                title=doc["title"],
                content_type=doc["content_type"],
                source_type=doc["source_type"]
            )
        
        logger.info("Sample data created successfully")
        
    except Exception as e:
        logger.error(f"Error creating sample data: {e}")

async def test_vector_functionality():
    """Test vector database functionality"""
    try:
        from services.vector_database import vector_db_service
        from services.embedding_service import embedding_service
        
        # Initialize services
        await vector_db_service.initialize()
        
        # Test embedding generation
        test_text = "This is a test document for vector search."
        embedding = await embedding_service.encode_text(test_text)
        logger.info(f"Generated embedding with dimension: {len(embedding)}")
        
        # Test similarity search
        results = await vector_db_service.similarity_search(
            query="programming language",
            max_results=5,
            similarity_threshold=0.1  # Low threshold for testing
        )
        logger.info(f"Similarity search returned {len(results)} results")
        
        # Test hybrid search
        hybrid_results = await vector_db_service.hybrid_search(
            query="machine learning",
            max_results=5,
            similarity_threshold=0.1
        )
        logger.info(f"Hybrid search returned {len(hybrid_results)} results")
        
        # Get statistics
        stats = await vector_db_service.get_statistics()
        logger.info(f"Database stats: {stats}")
        
        logger.info("Vector functionality test completed successfully")
        
    except Exception as e:
        logger.error(f"Vector functionality test failed: {e}")

if __name__ == "__main__":
    import sys
    
    async def main():
        command = sys.argv[1] if len(sys.argv) > 1 else "init"
        
        if command == "init":
            await initialize_vector_database()
        elif command == "sample":
            await initialize_vector_database()
            await create_sample_data()
        elif command == "test":
            await test_vector_functionality()
        else:
            print("Usage: python init_vector_db.py [init|sample|test]")
    
    asyncio.run(main())
#!/usr/bin/env python3
"""
Test script for vector database functionality
"""

import asyncio
import sys
import os
from uuid import uuid4

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.vector_database import vector_db_service
from services.embedding_service import embedding_service
from database.init_vector_db import initialize_vector_database
from utils.logger import logger

async def test_embedding_service():
    """Test the embedding service"""
    print("\n=== Testing Embedding Service ===")
    
    try:
        await embedding_service.initialize()
        
        # Test single text encoding
        text = "This is a test sentence for embedding."
        embedding = await embedding_service.encode_text(text)
        print(f"✓ Single text embedding: dimension {len(embedding)}")
        
        # Test batch encoding
        texts = [
            "Python is a programming language.",
            "Machine learning uses algorithms to learn from data.",
            "Vector databases store high-dimensional vectors."
        ]
        embeddings = await embedding_service.encode_text(texts)
        print(f"✓ Batch encoding: {len(embeddings)} embeddings generated")
        
        # Test similarity computation
        similarity = await embedding_service.compute_similarity(embeddings[0], embeddings[1])
        print(f"✓ Similarity computation: {similarity:.4f}")
        
        # Health check
        health = await embedding_service.health_check()
        print(f"✓ Health check: {health['status']}")
        print(f"  Model: {health['model_name']}")
        print(f"  Device: {health['device']}")
        print(f"  Embedding dimension: {health['embedding_dimension']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Embedding service test failed: {e}")
        return False

async def test_vector_database():
    """Test the vector database service"""
    print("\n=== Testing Vector Database Service ===")
    
    try:
        await vector_db_service.initialize()
        
        # Create test user and project
        test_user_id = uuid4()
        test_project_id = uuid4()
        
        print(f"Using test user: {test_user_id}")
        print(f"Using test project: {test_project_id}")
        
        # Test document addition
        doc_id = await vector_db_service.add_document(
            content="Python is a versatile programming language used for web development, data science, and artificial intelligence.",
            user_id=test_user_id,
            project_id=test_project_id,
            title="Python Programming",
            content_type="text",
            source_type="manual",
            metadata={"category": "programming", "difficulty": "beginner"}
        )
        print(f"✓ Document added with ID: {doc_id}")
        
        # Test batch document addition
        batch_docs = [
            {
                "content": "Machine learning algorithms can automatically learn patterns from data without explicit programming.",
                "user_id": test_user_id,
                "project_id": test_project_id,
                "title": "Machine Learning Basics",
                "content_type": "text",
                "source_type": "manual",
                "metadata": {"category": "ai", "difficulty": "intermediate"}
            },
            {
                "content": "Vector databases are optimized for storing and querying high-dimensional vectors used in AI applications.",
                "user_id": test_user_id,
                "project_id": test_project_id,
                "title": "Vector Databases",
                "content_type": "text",
                "source_type": "manual",
                "metadata": {"category": "database", "difficulty": "advanced"}
            }
        ]
        
        batch_ids = await vector_db_service.add_documents_batch(batch_docs)
        print(f"✓ Batch documents added: {len(batch_ids)} documents")
        
        # Test similarity search
        search_results = await vector_db_service.similarity_search(
            query="programming languages and development",
            similarity_threshold=0.1,
            max_results=10,
            user_id=test_user_id,
            project_id=test_project_id
        )
        print(f"✓ Similarity search: {len(search_results)} results")
        for i, result in enumerate(search_results[:3]):
            print(f"  {i+1}. {result['title']} (similarity: {result['similarity']:.4f})")
        
        # Test hybrid search
        hybrid_results = await vector_db_service.hybrid_search(
            query="machine learning algorithms",
            similarity_threshold=0.1,
            max_results=10,
            user_id=test_user_id,
            project_id=test_project_id,
            text_weight=0.4,
            vector_weight=0.6
        )
        print(f"✓ Hybrid search: {len(hybrid_results)} results")
        for i, result in enumerate(hybrid_results[:3]):
            print(f"  {i+1}. {result['title']} (combined: {result['combined_score']:.4f})")
        
        # Test statistics
        stats = await vector_db_service.get_statistics(
            user_id=test_user_id,
            project_id=test_project_id
        )
        print(f"✓ Statistics retrieved:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Entries with embeddings: {stats['entries_with_embeddings']}")
        print(f"  Embedding coverage: {stats['embedding_coverage']:.2%}")
        
        # Test document update
        success = await vector_db_service.update_document_embedding(
            doc_id,
            content="Python is an excellent programming language for beginners and experts alike.",
            title="Python Programming - Updated"
        )
        print(f"✓ Document embedding updated: {success}")
        
        # Test document deletion
        success = await vector_db_service.delete_document(doc_id)
        print(f"✓ Document deleted: {success}")
        
        # Clean up batch documents
        for batch_id in batch_ids:
            await vector_db_service.delete_document(batch_id)
        print(f"✓ Cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"✗ Vector database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_health_checks():
    """Test health check endpoints"""
    print("\n=== Testing Health Checks ===")
    
    try:
        # Embedding service health
        embedding_health = await embedding_service.health_check()
        print(f"✓ Embedding service: {embedding_health['status']}")
        
        # Vector database health
        vector_health = await vector_db_service.health_check()
        print(f"✓ Vector database: {vector_health['status']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    print("Starting Vector Database Tests...")
    
    # Initialize database first
    try:
        print("\n=== Initializing Database ===")
        await initialize_vector_database()
        print("✓ Database initialized")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False
    
    # Run tests
    tests = [
        ("Embedding Service", test_embedding_service),
        ("Vector Database", test_vector_database),
        ("Health Checks", test_health_checks)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n=== Test Summary ===")
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    return passed == len(results)

async def interactive_test():
    """Interactive test mode"""
    print("Interactive Vector Database Test")
    print("Commands: search, add, stats, health, quit")
    
    await vector_db_service.initialize()
    test_user_id = uuid4()
    test_project_id = uuid4()
    
    while True:
        try:
            command = input("\n> ").strip().lower()
            
            if command == "quit":
                break
            elif command == "search":
                query = input("Enter search query: ")
                results = await vector_db_service.similarity_search(
                    query=query,
                    user_id=test_user_id,
                    project_id=test_project_id,
                    max_results=5
                )
                print(f"Found {len(results)} results:")
                for i, result in enumerate(results):
                    print(f"{i+1}. {result['title']} ({result['similarity']:.4f})")
                    print(f"   {result['content'][:100]}...")
            
            elif command == "add":
                title = input("Enter title: ")
                content = input("Enter content: ")
                doc_id = await vector_db_service.add_document(
                    content=content,
                    title=title,
                    user_id=test_user_id,
                    project_id=test_project_id
                )
                print(f"Added document: {doc_id}")
            
            elif command == "stats":
                stats = await vector_db_service.get_statistics(
                    user_id=test_user_id,
                    project_id=test_project_id
                )
                print(f"Statistics: {stats}")
            
            elif command == "health":
                health = await vector_db_service.health_check()
                print(f"Health: {health}")
            
            else:
                print("Unknown command. Available: search, add, stats, health, quit")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "test"
    
    if command == "test":
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    elif command == "interactive":
        asyncio.run(interactive_test())
    else:
        print("Usage: python test_vector_db.py [test|interactive]")
        sys.exit(1)
# Vector Database Implementation

This document describes the vector database functionality implemented using pgvector for the Suna self-hosted migration.

## Overview

The vector database implementation provides:
- Local vector storage using PostgreSQL with pgvector extension
- Embedding generation using sentence-transformers
- Similarity search and hybrid search capabilities
- Knowledge base management with vector indexing
- Batch processing and optimization for large datasets

## Architecture

### Components

1. **pgvector Extension**: PostgreSQL extension for vector operations
2. **Embedding Service**: Local sentence-transformers for generating embeddings
3. **Vector Database Service**: High-level API for vector operations
4. **Knowledge Base API**: REST endpoints for managing documents and search
5. **Database Models**: SQLAlchemy models with vector support

### Database Schema

The main tables for vector functionality:

- `knowledge_base`: Stores documents with vector embeddings
- `projects`: Organizes documents by project
- `users`: User management and access control

Key vector-specific columns:
- `embedding`: vector(1536) - Stores document embeddings
- Vector indexes for fast similarity search

## Installation and Setup

### Prerequisites

1. PostgreSQL 16+ with pgvector extension
2. Python 3.11+ with required dependencies
3. Redis for caching (optional)

### Dependencies

Add to `pyproject.toml`:
```toml
"pgvector>=0.3.6",
"sentence-transformers>=3.3.1",
"torch>=2.5.1",
"numpy>=1.24.0",
"scikit-learn>=1.3.0",
```

### Database Setup

1. **Start PostgreSQL with pgvector**:
```bash
docker-compose -f docker-compose.vector-test.yml up -d
```

2. **Initialize the database**:
```bash
python database/init_vector_db.py init
```

3. **Create sample data** (optional):
```bash
python database/init_vector_db.py sample
```

### Configuration

Set environment variables in `.env`:
```bash
DATABASE_URL=postgresql://suna_user:suna_password@localhost:5433/suna_vector_test
REDIS_URL=redis://localhost:6380
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu
```

## Usage

### Embedding Service

```python
from services.embedding_service import embedding_service

# Initialize
await embedding_service.initialize()

# Generate embeddings
embedding = await embedding_service.encode_text("Your text here")
embeddings = await embedding_service.encode_text(["Text 1", "Text 2"])

# Compute similarity
similarity = await embedding_service.compute_similarity(embedding1, embedding2)
```

### Vector Database Service

```python
from services.vector_database import vector_db_service

# Initialize
await vector_db_service.initialize()

# Add document
doc_id = await vector_db_service.add_document(
    content="Document content",
    title="Document title",
    user_id=user_id,
    project_id=project_id
)

# Similarity search
results = await vector_db_service.similarity_search(
    query="search query",
    similarity_threshold=0.7,
    max_results=10
)

# Hybrid search (text + vector)
results = await vector_db_service.hybrid_search(
    query="search query",
    text_weight=0.3,
    vector_weight=0.7
)
```

### REST API Endpoints

#### Knowledge Base Management

- `GET /api/vector-kb/projects/{project_id}` - List documents
- `POST /api/vector-kb/projects/{project_id}` - Create document
- `PUT /api/vector-kb/{entry_id}` - Update document
- `DELETE /api/vector-kb/{entry_id}` - Delete document

#### Search Endpoints

- `POST /api/vector-kb/search/similarity` - Vector similarity search
- `POST /api/vector-kb/search/hybrid` - Hybrid text+vector search

#### Management Endpoints

- `GET /api/vector-kb/stats` - Get statistics
- `POST /api/vector-kb/reindex` - Reindex embeddings
- `GET /api/vector-kb/health` - Health check

### Example API Usage

#### Create a Document
```bash
curl -X POST "http://localhost:8000/api/vector-kb/projects/{project_id}" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Programming Guide",
    "content": "Python is a versatile programming language...",
    "content_type": "text",
    "source_type": "manual"
  }'
```

#### Similarity Search
```bash
curl -X POST "http://localhost:8000/api/vector-kb/search/similarity" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "programming languages",
    "similarity_threshold": 0.7,
    "max_results": 10
  }'
```

#### Hybrid Search
```bash
curl -X POST "http://localhost:8000/api/vector-kb/search/hybrid" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning algorithms",
    "similarity_threshold": 0.7,
    "max_results": 10,
    "text_weight": 0.3,
    "vector_weight": 0.7
  }'
```

## Testing

### Automated Tests

Run the comprehensive test suite:
```bash
python test_vector_db.py test
```

### Interactive Testing

Start interactive test mode:
```bash
python test_vector_db.py interactive
```

### Individual Component Tests

Test specific components:
```bash
# Test database initialization
python database/init_vector_db.py init

# Test with sample data
python database/init_vector_db.py sample

# Test functionality
python database/init_vector_db.py test
```

## Performance Optimization

### Vector Indexes

The implementation uses HNSW (Hierarchical Navigable Small World) indexes for fast similarity search:

```sql
CREATE INDEX idx_knowledge_base_embedding_hnsw ON knowledge_base 
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

### Batch Processing

For large datasets, use batch operations:

```python
# Batch document addition
documents = [{"content": "...", "title": "..."}, ...]
doc_ids = await vector_db_service.add_documents_batch(documents, batch_size=32)

# Batch embedding generation
embeddings = await embedding_service.encode_text(texts, batch_size=32)
```

### Configuration Tuning

Optimize for your hardware:

```python
# GPU acceleration (if available)
EMBEDDING_DEVICE=cuda

# Larger batch sizes for better GPU utilization
EMBEDDING_BATCH_SIZE=64

# Adjust vector index parameters
HNSW_M=16              # Number of connections
HNSW_EF_CONSTRUCTION=64  # Search width during construction
```

## Monitoring and Maintenance

### Health Checks

Monitor service health:
```bash
curl http://localhost:8000/api/vector-kb/health
```

### Statistics

Get database statistics:
```bash
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/vector-kb/stats
```

### Reindexing

Reindex embeddings for documents without them:
```bash
curl -X POST -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/vector-kb/reindex
```

## Troubleshooting

### Common Issues

1. **pgvector extension not found**
   - Ensure PostgreSQL has pgvector extension installed
   - Check with: `SELECT * FROM pg_extension WHERE extname = 'vector';`

2. **Embedding model download fails**
   - Check internet connection
   - Verify model name in sentence-transformers hub
   - Check disk space for model cache

3. **Slow similarity search**
   - Ensure vector indexes are created
   - Check index usage with EXPLAIN ANALYZE
   - Consider adjusting HNSW parameters

4. **Out of memory errors**
   - Reduce batch size for embedding generation
   - Use CPU instead of GPU if GPU memory is limited
   - Implement pagination for large result sets

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG
DB_ECHO=true
```

### Performance Monitoring

Monitor key metrics:
- Embedding generation time
- Search query performance
- Index size and memory usage
- Database connection pool status

## Migration from External Services

### From Pinecone/Weaviate

1. Export existing vectors and metadata
2. Transform to knowledge_base schema
3. Batch import using `add_documents_batch`
4. Verify with similarity searches

### From OpenAI Embeddings

1. Update embedding dimension if needed (default: 1536)
2. Migrate existing embeddings directly
3. Switch to local sentence-transformers for new content

## Security Considerations

### Access Control

- User-based access control through project ownership
- API authentication required for all endpoints
- Input validation and sanitization

### Data Protection

- Embeddings stored locally (no external API calls)
- Configurable data retention policies
- Audit logging for document operations

## Future Enhancements

### Planned Features

1. **Multi-modal embeddings**: Support for image and code embeddings
2. **Distributed search**: Scale across multiple PostgreSQL instances
3. **Advanced indexing**: Support for IVFFlat and other index types
4. **Real-time updates**: WebSocket notifications for search results
5. **Analytics**: Search analytics and usage metrics

### Performance Improvements

1. **Caching**: Redis caching for frequent searches
2. **Compression**: Vector compression for storage efficiency
3. **Parallel processing**: Multi-threaded embedding generation
4. **Query optimization**: Advanced query planning and optimization

## Contributing

When contributing to vector database functionality:

1. Follow the existing code structure
2. Add comprehensive tests for new features
3. Update documentation and examples
4. Consider performance implications
5. Maintain backward compatibility

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review test outputs for error details
3. Enable debug logging for detailed information
4. Check PostgreSQL and Redis logs
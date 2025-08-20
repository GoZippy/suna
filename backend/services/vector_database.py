"""
Vector database service using pgvector
Handles vector storage, similarity search, and hybrid search functionality
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from uuid import UUID
import numpy as np
from sqlalchemy import text, select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import db_manager
from database.models import KnowledgeBase, User, Project
from services.embedding_service import embedding_service
from utils.logger import logger

class VectorDatabaseService:
    """Service for vector database operations using pgvector"""
    
    def __init__(self):
        self.embedding_service = embedding_service
    
    async def initialize(self):
        """Initialize the vector database service"""
        await self.embedding_service.initialize()
        logger.info("Vector database service initialized")
    
    async def add_document(
        self,
        content: str,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        title: Optional[str] = None,
        content_type: str = 'text',
        source_type: str = 'manual',
        source_url: Optional[str] = None,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        file_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_index: int = 0,
        total_chunks: int = 1
    ) -> UUID:
        """
        Add a document to the vector database with embedding
        
        Args:
            content: Text content to embed and store
            user_id: Optional user ID for access control
            project_id: Optional project ID for organization
            title: Optional document title
            content_type: Type of content (text, code, markdown, etc.)
            source_type: Source of the document (manual, file, url, etc.)
            source_url: Optional source URL
            file_path: Optional file path
            file_size: Optional file size in bytes
            file_hash: Optional file hash for deduplication
            metadata: Optional additional metadata
            chunk_index: Index of this chunk if document is split
            total_chunks: Total number of chunks for this document
            
        Returns:
            UUID of the created knowledge base entry
        """
        try:
            # Generate embedding for the content
            text_to_embed = f"{title}\n\n{content}" if title else content
            embedding = await self.embedding_service.encode_text(text_to_embed)
            
            # Convert numpy array to list for PostgreSQL
            embedding_list = embedding.tolist()
            
            async with db_manager.get_session() as session:
                # Create knowledge base entry
                kb_entry = KnowledgeBase(
                    user_id=user_id,
                    project_id=project_id,
                    title=title,
                    content=content,
                    content_type=content_type,
                    source_type=source_type,
                    source_url=source_url,
                    embedding=embedding_list,
                    chunk_index=chunk_index,
                    total_chunks=total_chunks,
                    file_path=file_path,
                    file_size=file_size,
                    file_hash=file_hash,
                    metadata=metadata or {}
                )
                
                session.add(kb_entry)
                await session.flush()  # Get the ID
                
                entry_id = kb_entry.id
                logger.debug(f"Added document to vector database: {entry_id}")
                
                return entry_id
                
        except Exception as e:
            logger.error(f"Error adding document to vector database: {e}")
            raise
    
    async def add_documents_batch(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 32
    ) -> List[UUID]:
        """
        Add multiple documents to the vector database in batches
        
        Args:
            documents: List of document dictionaries with required fields
            batch_size: Batch size for embedding generation
            
        Returns:
            List of UUIDs for created entries
        """
        try:
            if not documents:
                return []
            
            # Prepare texts for batch embedding
            texts = []
            for doc in documents:
                content = doc.get('content', '')
                title = doc.get('title', '')
                text_to_embed = f"{title}\n\n{content}" if title else content
                texts.append(text_to_embed)
            
            # Generate embeddings in batches
            embeddings = await self.embedding_service.encode_text(
                texts, 
                batch_size=batch_size
            )
            
            # Store documents with embeddings
            entry_ids = []
            async with db_manager.get_session() as session:
                for i, doc in enumerate(documents):
                    embedding_list = embeddings[i].tolist()
                    
                    kb_entry = KnowledgeBase(
                        user_id=doc.get('user_id'),
                        project_id=doc.get('project_id'),
                        title=doc.get('title'),
                        content=doc.get('content', ''),
                        content_type=doc.get('content_type', 'text'),
                        source_type=doc.get('source_type', 'manual'),
                        source_url=doc.get('source_url'),
                        embedding=embedding_list,
                        chunk_index=doc.get('chunk_index', 0),
                        total_chunks=doc.get('total_chunks', 1),
                        file_path=doc.get('file_path'),
                        file_size=doc.get('file_size'),
                        file_hash=doc.get('file_hash'),
                        metadata=doc.get('metadata', {})
                    )
                    
                    session.add(kb_entry)
                    await session.flush()
                    entry_ids.append(kb_entry.id)
            
            logger.info(f"Added {len(documents)} documents to vector database")
            return entry_ids
            
        except Exception as e:
            logger.error(f"Error adding documents batch to vector database: {e}")
            raise
    
    async def similarity_search(
        self,
        query: str,
        similarity_threshold: float = 0.7,
        max_results: int = 10,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        content_types: Optional[List[str]] = None,
        source_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search
        
        Args:
            query: Search query text
            similarity_threshold: Minimum similarity score (0-1)
            max_results: Maximum number of results
            user_id: Optional user ID filter
            project_id: Optional project ID filter
            content_types: Optional content type filters
            source_types: Optional source type filters
            
        Returns:
            List of search results with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.encode_text(query)
            query_embedding_list = query_embedding.tolist()
            
            async with db_manager.get_session() as session:
                # Use the PostgreSQL function for similarity search
                query_sql = text("""
                    SELECT * FROM search_knowledge_base_by_similarity(
                        :query_embedding::vector,
                        :similarity_threshold,
                        :max_results,
                        :target_user_id,
                        :target_project_id
                    )
                """)
                
                result = await session.execute(query_sql, {
                    'query_embedding': query_embedding_list,
                    'similarity_threshold': similarity_threshold,
                    'max_results': max_results,
                    'target_user_id': user_id,
                    'target_project_id': project_id
                })
                
                results = []
                for row in result.fetchall():
                    # Apply additional filters if specified
                    if content_types and row.content_type not in content_types:
                        continue
                    if source_types and row.source_type not in source_types:
                        continue
                    
                    results.append({
                        'id': row.id,
                        'title': row.title,
                        'content': row.content,
                        'content_type': row.content_type,
                        'source_type': row.source_type,
                        'similarity': row.similarity,
                        'metadata': row.metadata,
                        'created_at': row.created_at
                    })
                
                logger.debug(f"Vector similarity search returned {len(results)} results")
                return results
                
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            raise
    
    async def hybrid_search(
        self,
        query: str,
        similarity_threshold: float = 0.7,
        max_results: int = 10,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        text_weight: float = 0.3,
        vector_weight: float = 0.7,
        content_types: Optional[List[str]] = None,
        source_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining text and vector similarity
        
        Args:
            query: Search query text
            similarity_threshold: Minimum similarity score (0-1)
            max_results: Maximum number of results
            user_id: Optional user ID filter
            project_id: Optional project ID filter
            text_weight: Weight for text search score (0-1)
            vector_weight: Weight for vector search score (0-1)
            content_types: Optional content type filters
            source_types: Optional source type filters
            
        Returns:
            List of search results with combined scores
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.encode_text(query)
            query_embedding_list = query_embedding.tolist()
            
            async with db_manager.get_session() as session:
                # Use the PostgreSQL function for hybrid search
                query_sql = text("""
                    SELECT * FROM hybrid_search_knowledge_base(
                        :query_text,
                        :query_embedding::vector,
                        :similarity_threshold,
                        :max_results,
                        :target_user_id,
                        :target_project_id,
                        :text_weight,
                        :vector_weight
                    )
                """)
                
                result = await session.execute(query_sql, {
                    'query_text': query,
                    'query_embedding': query_embedding_list,
                    'similarity_threshold': similarity_threshold,
                    'max_results': max_results,
                    'target_user_id': user_id,
                    'target_project_id': project_id,
                    'text_weight': text_weight,
                    'vector_weight': vector_weight
                })
                
                results = []
                for row in result.fetchall():
                    # Apply additional filters if specified
                    if content_types and row.content_type not in content_types:
                        continue
                    if source_types and row.source_type not in source_types:
                        continue
                    
                    results.append({
                        'id': row.id,
                        'title': row.title,
                        'content': row.content,
                        'content_type': row.content_type,
                        'source_type': row.source_type,
                        'text_score': float(row.text_score),
                        'vector_score': float(row.vector_score),
                        'combined_score': float(row.combined_score),
                        'metadata': row.metadata,
                        'created_at': row.created_at
                    })
                
                logger.debug(f"Hybrid search returned {len(results)} results")
                return results
                
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            raise
    
    async def update_document_embedding(
        self,
        document_id: UUID,
        content: Optional[str] = None,
        title: Optional[str] = None
    ) -> bool:
        """
        Update the embedding for an existing document
        
        Args:
            document_id: ID of the document to update
            content: New content (if None, uses existing content)
            title: New title (if None, uses existing title)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with db_manager.get_session() as session:
                # Get existing document
                result = await session.execute(
                    select(KnowledgeBase).where(KnowledgeBase.id == document_id)
                )
                kb_entry = result.scalar_one_or_none()
                
                if not kb_entry:
                    logger.warning(f"Document {document_id} not found")
                    return False
                
                # Use provided content/title or existing ones
                update_content = content if content is not None else kb_entry.content
                update_title = title if title is not None else kb_entry.title
                
                # Generate new embedding
                text_to_embed = f"{update_title}\n\n{update_content}" if update_title else update_content
                embedding = await self.embedding_service.encode_text(text_to_embed)
                embedding_list = embedding.tolist()
                
                # Update the document
                kb_entry.embedding = embedding_list
                if content is not None:
                    kb_entry.content = content
                if title is not None:
                    kb_entry.title = title
                
                logger.debug(f"Updated embedding for document {document_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating document embedding: {e}")
            return False
    
    async def delete_document(self, document_id: UUID) -> bool:
        """
        Delete a document from the vector database
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(
                    select(KnowledgeBase).where(KnowledgeBase.id == document_id)
                )
                kb_entry = result.scalar_one_or_none()
                
                if not kb_entry:
                    logger.warning(f"Document {document_id} not found")
                    return False
                
                await session.delete(kb_entry)
                logger.debug(f"Deleted document {document_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    async def get_statistics(
        self,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get vector database statistics
        
        Args:
            user_id: Optional user ID filter
            project_id: Optional project ID filter
            
        Returns:
            Dictionary with statistics
        """
        try:
            async with db_manager.get_session() as session:
                # Use the PostgreSQL function for statistics
                query_sql = text("""
                    SELECT * FROM get_knowledge_base_stats(
                        :target_user_id,
                        :target_project_id
                    )
                """)
                
                result = await session.execute(query_sql, {
                    'target_user_id': user_id,
                    'target_project_id': project_id
                })
                
                row = result.fetchone()
                if row:
                    return {
                        'total_entries': int(row.total_entries),
                        'entries_with_embeddings': int(row.entries_with_embeddings),
                        'total_content_length': int(row.total_content_length or 0),
                        'avg_content_length': float(row.avg_content_length or 0),
                        'content_types': row.content_types or {},
                        'source_types': row.source_types or {},
                        'embedding_coverage': (
                            float(row.entries_with_embeddings) / float(row.total_entries)
                            if row.total_entries > 0 else 0.0
                        )
                    }
                
                return {
                    'total_entries': 0,
                    'entries_with_embeddings': 0,
                    'total_content_length': 0,
                    'avg_content_length': 0,
                    'content_types': {},
                    'source_types': {},
                    'embedding_coverage': 0.0
                }
                
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    async def reindex_embeddings(
        self,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        batch_size: int = 32
    ) -> Dict[str, Any]:
        """
        Reindex embeddings for documents that don't have them
        
        Args:
            user_id: Optional user ID filter
            project_id: Optional project ID filter
            batch_size: Batch size for processing
            
        Returns:
            Dictionary with reindexing results
        """
        try:
            async with db_manager.get_session() as session:
                # Find documents without embeddings
                query = select(KnowledgeBase).where(KnowledgeBase.embedding.is_(None))
                
                if user_id:
                    query = query.where(KnowledgeBase.user_id == user_id)
                if project_id:
                    query = query.where(KnowledgeBase.project_id == project_id)
                
                result = await session.execute(query)
                documents = result.scalars().all()
                
                if not documents:
                    return {
                        'total_processed': 0,
                        'successful': 0,
                        'failed': 0,
                        'errors': []
                    }
                
                # Process in batches
                successful = 0
                failed = 0
                errors = []
                
                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i + batch_size]
                    
                    # Prepare texts for batch embedding
                    texts = []
                    for doc in batch:
                        text_to_embed = f"{doc.title}\n\n{doc.content}" if doc.title else doc.content
                        texts.append(text_to_embed)
                    
                    try:
                        # Generate embeddings for batch
                        embeddings = await self.embedding_service.encode_text(
                            texts, 
                            batch_size=batch_size
                        )
                        
                        # Update documents with embeddings
                        for j, doc in enumerate(batch):
                            try:
                                doc.embedding = embeddings[j].tolist()
                                successful += 1
                            except Exception as e:
                                failed += 1
                                errors.append(f"Document {doc.id}: {str(e)}")
                        
                        await session.commit()
                        
                    except Exception as e:
                        failed += len(batch)
                        errors.append(f"Batch {i//batch_size}: {str(e)}")
                        await session.rollback()
                
                logger.info(f"Reindexing completed: {successful} successful, {failed} failed")
                
                return {
                    'total_processed': len(documents),
                    'successful': successful,
                    'failed': failed,
                    'errors': errors
                }
                
        except Exception as e:
            logger.error(f"Error reindexing embeddings: {e}")
            return {
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
                'errors': [str(e)]
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the vector database service"""
        try:
            # Check embedding service
            embedding_health = await self.embedding_service.health_check()
            
            # Check database connection and vector extension
            async with db_manager.get_session() as session:
                # Test vector extension
                result = await session.execute(text("SELECT vector_dims(ARRAY[1,2,3]::vector)"))
                vector_test = result.scalar()
                
                # Get basic statistics
                stats = await self.get_statistics()
                
                return {
                    'status': 'healthy',
                    'embedding_service': embedding_health,
                    'vector_extension': 'available' if vector_test == 3 else 'unavailable',
                    'database_stats': stats
                }
                
        except Exception as e:
            logger.error(f"Vector database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

# Global vector database service instance
vector_db_service = VectorDatabaseService()

# Convenience functions
async def add_document(content: str, **kwargs) -> UUID:
    """Convenience function for adding a document"""
    return await vector_db_service.add_document(content, **kwargs)

async def similarity_search(query: str, **kwargs) -> List[Dict[str, Any]]:
    """Convenience function for similarity search"""
    return await vector_db_service.similarity_search(query, **kwargs)

async def hybrid_search(query: str, **kwargs) -> List[Dict[str, Any]]:
    """Convenience function for hybrid search"""
    return await vector_db_service.hybrid_search(query, **kwargs)
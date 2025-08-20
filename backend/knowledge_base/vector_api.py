"""
Vector-enabled Knowledge Base API
Provides endpoints for vector database operations with pgvector
"""

import json
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from database.connection import db_manager
from database.models import KnowledgeBase, Project
from services.vector_database import vector_db_service
from services.embedding_service import embedding_service
from knowledge_base.file_processor import FileProcessor
from utils.auth_utils import get_current_user_id_from_jwt
from utils.logger import logger
from flags.flags import is_enabled

router = APIRouter(prefix="/vector-kb", tags=["vector-knowledge-base"])

# Pydantic models
class KnowledgeBaseEntryResponse(BaseModel):
    id: UUID
    title: Optional[str]
    content: str
    content_type: str
    source_type: str
    source_url: Optional[str]
    file_path: Optional[str]
    file_size: Optional[int]
    file_hash: Optional[str]
    chunk_index: int
    total_chunks: int
    metadata: dict
    created_at: str
    updated_at: str
    has_embedding: bool

class KnowledgeBaseListResponse(BaseModel):
    entries: List[KnowledgeBaseEntryResponse]
    total_count: int
    embedding_coverage: float

class CreateKnowledgeBaseEntryRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=1)
    content_type: str = Field(default="text")
    source_type: str = Field(default="manual")
    source_url: Optional[str] = None
    metadata: Optional[dict] = Field(default_factory=dict)

class UpdateKnowledgeBaseEntryRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    content_type: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    metadata: Optional[dict] = None

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_results: int = Field(default=10, ge=1, le=100)
    content_types: Optional[List[str]] = None
    source_types: Optional[List[str]] = None

class SearchResult(BaseModel):
    id: UUID
    title: Optional[str]
    content: str
    content_type: str
    source_type: str
    similarity: Optional[float] = None
    text_score: Optional[float] = None
    vector_score: Optional[float] = None
    combined_score: Optional[float] = None
    metadata: dict
    created_at: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int
    query: str
    search_type: str

class HybridSearchRequest(SearchRequest):
    text_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0)

class VectorStatsResponse(BaseModel):
    total_entries: int
    entries_with_embeddings: int
    embedding_coverage: float
    total_content_length: int
    avg_content_length: float
    content_types: dict
    source_types: dict

class ReindexResponse(BaseModel):
    total_processed: int
    successful: int
    failed: int
    errors: List[str]

# API Endpoints

@router.get("/projects/{project_id}", response_model=KnowledgeBaseListResponse)
async def get_project_knowledge_base(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Get all knowledge base entries for a project"""
    if not await is_enabled("knowledge_base"):
        raise HTTPException(status_code=403, detail="Knowledge base feature is not available")
    
    try:
        async with db_manager.get_session() as session:
            # Verify project access
            project_result = await session.execute(
                select(Project).where(
                    and_(Project.project_id == project_id, Project.user_id == user_id)
                )
            )
            project = project_result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            
            # Get knowledge base entries
            kb_result = await session.execute(
                select(KnowledgeBase).where(KnowledgeBase.project_id == project_id)
                .order_by(KnowledgeBase.created_at.desc())
            )
            entries = kb_result.scalars().all()
            
            # Convert to response format
            entry_responses = []
            entries_with_embeddings = 0
            
            for entry in entries:
                has_embedding = entry.embedding is not None
                if has_embedding:
                    entries_with_embeddings += 1
                
                entry_responses.append(KnowledgeBaseEntryResponse(
                    id=entry.id,
                    title=entry.title,
                    content=entry.content,
                    content_type=entry.content_type,
                    source_type=entry.source_type,
                    source_url=entry.source_url,
                    file_path=entry.file_path,
                    file_size=entry.file_size,
                    file_hash=entry.file_hash,
                    chunk_index=entry.chunk_index,
                    total_chunks=entry.total_chunks,
                    metadata=entry.metadata,
                    created_at=entry.created_at.isoformat(),
                    updated_at=entry.updated_at.isoformat(),
                    has_embedding=has_embedding
                ))
            
            embedding_coverage = (
                entries_with_embeddings / len(entries) if entries else 0.0
            )
            
            return KnowledgeBaseListResponse(
                entries=entry_responses,
                total_count=len(entries),
                embedding_coverage=embedding_coverage
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project knowledge base: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve knowledge base")

@router.post("/projects/{project_id}", response_model=KnowledgeBaseEntryResponse)
async def create_knowledge_base_entry(
    project_id: UUID,
    entry_data: CreateKnowledgeBaseEntryRequest,
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Create a new knowledge base entry with vector embedding"""
    if not await is_enabled("knowledge_base"):
        raise HTTPException(status_code=403, detail="Knowledge base feature is not available")
    
    try:
        async with db_manager.get_session() as session:
            # Verify project access
            project_result = await session.execute(
                select(Project).where(
                    and_(Project.project_id == project_id, Project.user_id == user_id)
                )
            )
            project = project_result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
        
        # Create entry with embedding
        entry_id = await vector_db_service.add_document(
            content=entry_data.content,
            user_id=user_id,
            project_id=project_id,
            title=entry_data.title,
            content_type=entry_data.content_type,
            source_type=entry_data.source_type,
            source_url=entry_data.source_url,
            metadata=entry_data.metadata
        )
        
        # Retrieve the created entry
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == entry_id)
            )
            entry = result.scalar_one()
            
            return KnowledgeBaseEntryResponse(
                id=entry.id,
                title=entry.title,
                content=entry.content,
                content_type=entry.content_type,
                source_type=entry.source_type,
                source_url=entry.source_url,
                file_path=entry.file_path,
                file_size=entry.file_size,
                file_hash=entry.file_hash,
                chunk_index=entry.chunk_index,
                total_chunks=entry.total_chunks,
                metadata=entry.metadata,
                created_at=entry.created_at.isoformat(),
                updated_at=entry.updated_at.isoformat(),
                has_embedding=entry.embedding is not None
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating knowledge base entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to create knowledge base entry")

@router.put("/{entry_id}", response_model=KnowledgeBaseEntryResponse)
async def update_knowledge_base_entry(
    entry_id: UUID,
    entry_data: UpdateKnowledgeBaseEntryRequest,
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Update a knowledge base entry and regenerate embedding if content changed"""
    if not await is_enabled("knowledge_base"):
        raise HTTPException(status_code=403, detail="Knowledge base feature is not available")
    
    try:
        async with db_manager.get_session() as session:
            # Get existing entry and verify access
            result = await session.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == entry_id)
            )
            entry = result.scalar_one_or_none()
            
            if not entry:
                raise HTTPException(status_code=404, detail="Knowledge base entry not found")
            
            # Verify user has access to the project
            if entry.project_id:
                project_result = await session.execute(
                    select(Project).where(
                        and_(Project.project_id == entry.project_id, Project.user_id == user_id)
                    )
                )
                if not project_result.scalar_one_or_none():
                    raise HTTPException(status_code=403, detail="Access denied")
            elif entry.user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Update fields
            content_changed = False
            title_changed = False
            
            if entry_data.title is not None:
                entry.title = entry_data.title
                title_changed = True
            if entry_data.content is not None:
                entry.content = entry_data.content
                content_changed = True
            if entry_data.content_type is not None:
                entry.content_type = entry_data.content_type
            if entry_data.source_type is not None:
                entry.source_type = entry_data.source_type
            if entry_data.source_url is not None:
                entry.source_url = entry_data.source_url
            if entry_data.metadata is not None:
                entry.metadata = entry_data.metadata
            
            await session.commit()
            
            # Update embedding if content or title changed
            if content_changed or title_changed:
                await vector_db_service.update_document_embedding(
                    entry_id,
                    content=entry.content,
                    title=entry.title
                )
            
            # Refresh entry to get updated data
            await session.refresh(entry)
            
            return KnowledgeBaseEntryResponse(
                id=entry.id,
                title=entry.title,
                content=entry.content,
                content_type=entry.content_type,
                source_type=entry.source_type,
                source_url=entry.source_url,
                file_path=entry.file_path,
                file_size=entry.file_size,
                file_hash=entry.file_hash,
                chunk_index=entry.chunk_index,
                total_chunks=entry.total_chunks,
                metadata=entry.metadata,
                created_at=entry.created_at.isoformat(),
                updated_at=entry.updated_at.isoformat(),
                has_embedding=entry.embedding is not None
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating knowledge base entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to update knowledge base entry")

@router.delete("/{entry_id}")
async def delete_knowledge_base_entry(
    entry_id: UUID,
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Delete a knowledge base entry"""
    if not await is_enabled("knowledge_base"):
        raise HTTPException(status_code=403, detail="Knowledge base feature is not available")
    
    try:
        async with db_manager.get_session() as session:
            # Get entry and verify access
            result = await session.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == entry_id)
            )
            entry = result.scalar_one_or_none()
            
            if not entry:
                raise HTTPException(status_code=404, detail="Knowledge base entry not found")
            
            # Verify user has access
            if entry.project_id:
                project_result = await session.execute(
                    select(Project).where(
                        and_(Project.project_id == entry.project_id, Project.user_id == user_id)
                    )
                )
                if not project_result.scalar_one_or_none():
                    raise HTTPException(status_code=403, detail="Access denied")
            elif entry.user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete the entry
        success = await vector_db_service.delete_document(entry_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete entry")
        
        return {"message": "Knowledge base entry deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting knowledge base entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete knowledge base entry")

@router.post("/search/similarity", response_model=SearchResponse)
async def similarity_search(
    search_request: SearchRequest,
    project_id: Optional[UUID] = Query(None),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Perform vector similarity search"""
    if not await is_enabled("knowledge_base"):
        raise HTTPException(status_code=403, detail="Knowledge base feature is not available")
    
    try:
        # Verify project access if specified
        if project_id:
            async with db_manager.get_session() as session:
                project_result = await session.execute(
                    select(Project).where(
                        and_(Project.project_id == project_id, Project.user_id == user_id)
                    )
                )
                if not project_result.scalar_one_or_none():
                    raise HTTPException(status_code=404, detail="Project not found")
        
        # Perform similarity search
        results = await vector_db_service.similarity_search(
            query=search_request.query,
            similarity_threshold=search_request.similarity_threshold,
            max_results=search_request.max_results,
            user_id=user_id,
            project_id=project_id,
            content_types=search_request.content_types,
            source_types=search_request.source_types
        )
        
        # Convert to response format
        search_results = []
        for result in results:
            search_results.append(SearchResult(
                id=result['id'],
                title=result['title'],
                content=result['content'],
                content_type=result['content_type'],
                source_type=result['source_type'],
                similarity=result['similarity'],
                metadata=result['metadata'],
                created_at=result['created_at'].isoformat()
            ))
        
        return SearchResponse(
            results=search_results,
            total_results=len(search_results),
            query=search_request.query,
            search_type="similarity"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in similarity search: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.post("/search/hybrid", response_model=SearchResponse)
async def hybrid_search(
    search_request: HybridSearchRequest,
    project_id: Optional[UUID] = Query(None),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Perform hybrid search combining text and vector similarity"""
    if not await is_enabled("knowledge_base"):
        raise HTTPException(status_code=403, detail="Knowledge base feature is not available")
    
    try:
        # Verify project access if specified
        if project_id:
            async with db_manager.get_session() as session:
                project_result = await session.execute(
                    select(Project).where(
                        and_(Project.project_id == project_id, Project.user_id == user_id)
                    )
                )
                if not project_result.scalar_one_or_none():
                    raise HTTPException(status_code=404, detail="Project not found")
        
        # Perform hybrid search
        results = await vector_db_service.hybrid_search(
            query=search_request.query,
            similarity_threshold=search_request.similarity_threshold,
            max_results=search_request.max_results,
            user_id=user_id,
            project_id=project_id,
            text_weight=search_request.text_weight,
            vector_weight=search_request.vector_weight,
            content_types=search_request.content_types,
            source_types=search_request.source_types
        )
        
        # Convert to response format
        search_results = []
        for result in results:
            search_results.append(SearchResult(
                id=result['id'],
                title=result['title'],
                content=result['content'],
                content_type=result['content_type'],
                source_type=result['source_type'],
                text_score=result['text_score'],
                vector_score=result['vector_score'],
                combined_score=result['combined_score'],
                metadata=result['metadata'],
                created_at=result['created_at'].isoformat()
            ))
        
        return SearchResponse(
            results=search_results,
            total_results=len(search_results),
            query=search_request.query,
            search_type="hybrid"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in hybrid search: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.get("/stats", response_model=VectorStatsResponse)
async def get_vector_stats(
    project_id: Optional[UUID] = Query(None),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Get vector database statistics"""
    if not await is_enabled("knowledge_base"):
        raise HTTPException(status_code=403, detail="Knowledge base feature is not available")
    
    try:
        # Verify project access if specified
        if project_id:
            async with db_manager.get_session() as session:
                project_result = await session.execute(
                    select(Project).where(
                        and_(Project.project_id == project_id, Project.user_id == user_id)
                    )
                )
                if not project_result.scalar_one_or_none():
                    raise HTTPException(status_code=404, detail="Project not found")
        
        # Get statistics
        stats = await vector_db_service.get_statistics(
            user_id=user_id,
            project_id=project_id
        )
        
        return VectorStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vector stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

@router.post("/reindex", response_model=ReindexResponse)
async def reindex_embeddings(
    project_id: Optional[UUID] = Query(None),
    batch_size: int = Query(32, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Reindex embeddings for documents that don't have them"""
    if not await is_enabled("knowledge_base"):
        raise HTTPException(status_code=403, detail="Knowledge base feature is not available")
    
    try:
        # Verify project access if specified
        if project_id:
            async with db_manager.get_session() as session:
                project_result = await session.execute(
                    select(Project).where(
                        and_(Project.project_id == project_id, Project.user_id == user_id)
                    )
                )
                if not project_result.scalar_one_or_none():
                    raise HTTPException(status_code=404, detail="Project not found")
        
        # Reindex embeddings
        result = await vector_db_service.reindex_embeddings(
            user_id=user_id,
            project_id=project_id,
            batch_size=batch_size
        )
        
        return ReindexResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reindexing embeddings: {e}")
        raise HTTPException(status_code=500, detail="Reindexing failed")

@router.post("/projects/{project_id}/upload-file")
async def upload_file_to_project_kb(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Upload and process a file for project knowledge base"""
    if not await is_enabled("knowledge_base"):
        raise HTTPException(status_code=403, detail="Knowledge base feature is not available")
    
    try:
        async with db_manager.get_session() as session:
            # Verify project access
            project_result = await session.execute(
                select(Project).where(
                    and_(Project.project_id == project_id, Project.user_id == user_id)
                )
            )
            project = project_result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
        
        # Read file content
        file_content = await file.read()
        
        # Process file in background
        background_tasks.add_task(
            process_file_background,
            project_id,
            user_id,
            file_content,
            file.filename,
            file.content_type or 'application/octet-stream'
        )
        
        return {
            "message": "File upload started. Processing in background.",
            "filename": file.filename,
            "project_id": project_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")

@router.get("/health")
async def health_check():
    """Health check for vector database service"""
    try:
        health = await vector_db_service.health_check()
        return health
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

# Background task functions
async def process_file_background(
    project_id: UUID,
    user_id: UUID,
    file_content: bytes,
    filename: str,
    mime_type: str
):
    """Background task to process uploaded files"""
    processor = FileProcessor()
    
    try:
        # Process the file
        result = await processor.process_file_upload(
            str(project_id),  # FileProcessor expects string
            str(user_id),     # FileProcessor expects string
            file_content,
            filename,
            mime_type
        )
        
        if result['success']:
            logger.info(f"Successfully processed file {filename} for project {project_id}")
        else:
            logger.error(f"Failed to process file {filename}: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error in background file processing: {e}")
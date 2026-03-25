"""
FastAPI endpoints for background job processing management.

This module provides REST API endpoints for managing background jobs,
scheduling, monitoring, and worker management.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from utils.config import config
from utils.logger import logger
from database.connection import get_db
from services.background_jobs import background_job_service

router = APIRouter(prefix="/api/background-jobs", tags=["background-jobs"])

# Pydantic models for request/response
class JobRequest(BaseModel):
    job_type: str = Field(..., description="Type of job to execute")
    function_name: str = Field(..., description="Function name to execute")
    arguments: Optional[Dict[str, Any]] = Field(default={}, description="Function arguments")
    keyword_arguments: Optional[Dict[str, Any]] = Field(default={}, description="Function keyword arguments")
    priority: int = Field(default=0, description="Job priority (higher = more important)")
    scheduled_at: Optional[str] = Field(None, description="ISO datetime for scheduled execution")

class JobResponse(BaseModel):
    id: str
    job_type: str
    job_name: str
    status: str
    priority: int
    retry_count: int
    max_retries: int
    scheduled_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    worker_id: Optional[str]
    error_message: Optional[str]
    metadata: Dict[str, Any]

class ScheduledJobRequest(BaseModel):
    name: str = Field(..., description="Unique name for the scheduled job")
    description: str = Field(..., description="Description of the job")
    job_type: str = Field(..., description="Type of job to execute")
    function_name: str = Field(..., description="Function name to execute")
    arguments: Optional[Dict[str, Any]] = Field(default={}, description="Function arguments")
    keyword_arguments: Optional[Dict[str, Any]] = Field(default={}, description="Function keyword arguments")
    cron_expression: Optional[str] = Field(None, description="Cron expression for scheduling")
    interval_seconds: Optional[int] = Field(None, description="Interval in seconds for scheduling")
    max_instances: int = Field(default=1, description="Maximum concurrent instances")
    timeout_seconds: int = Field(default=3600, description="Job timeout in seconds")
    priority: int = Field(default=0, description="Job priority")

class ScheduledJobResponse(BaseModel):
    id: str
    name: str
    description: str
    job_type: str
    function_name: str
    arguments: Dict[str, Any]
    keyword_arguments: Dict[str, Any]
    cron_expression: Optional[str]
    interval_seconds: Optional[int]
    next_run_at: str
    last_run_at: Optional[str]
    is_active: bool
    max_instances: int
    timeout_seconds: int
    priority: int
    metadata: Dict[str, Any]

class WorkerStatsResponse(BaseModel):
    active_workers: int
    total_workers: int
    job_stats: Dict[str, int]
    workers: List[Dict[str, Any]]

class HealthResponse(BaseModel):
    status: str
    message: str
    timestamp: str
    services: Dict[str, Any]

@router.post("/jobs", response_model=JobResponse)
async def create_job(
    request: JobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create and enqueue a new background job."""
    try:
        if not config.ENABLE_BACKGROUND_JOBS:
            raise HTTPException(status_code=503, detail="Background job processing is disabled")
        
        # Parse scheduled_at if provided
        scheduled_at = None
        if request.scheduled_at:
            try:
                scheduled_at = datetime.fromisoformat(request.scheduled_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid scheduled_at format. Use ISO 8601 format.")
        
        job_id = await background_job_service.enqueue_job(
            job_type=request.job_type,
            function_name=request.function_name,
            arguments=request.arguments,
            keyword_arguments=request.keyword_arguments,
            priority=request.priority,
            scheduled_at=scheduled_at
        )
        
        # Get job status
        job_status = await background_job_service.get_job_status(job_id)
        if not job_status:
            raise HTTPException(status_code=500, detail="Failed to create job")
        
        return JobResponse(**job_status)
        
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs", response_model=List[JobResponse])
async def get_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    limit: int = Query(100, ge=1, le=1000, description="Number of jobs to return"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
    db: Session = Depends(get_db)
):
    """Get jobs from the queue with optional filtering."""
    try:
        if not config.ENABLE_BACKGROUND_JOBS:
            raise HTTPException(status_code=503, detail="Background job processing is disabled")
        
        jobs = await background_job_service.get_job_queue(
            status=status,
            job_type=job_type,
            limit=limit,
            offset=offset
        )
        
        return [JobResponse(**job) for job in jobs if job]
        
    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get the status of a specific job."""
    try:
        if not config.ENABLE_BACKGROUND_JOBS:
            raise HTTPException(status_code=503, detail="Background job processing is disabled")
        
        job_status = await background_job_service.get_job_status(job_id)
        if not job_status:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobResponse(**job_status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Cancel a pending or running job."""
    try:
        if not config.ENABLE_BACKGROUND_JOBS:
            raise HTTPException(status_code=503, detail="Background job processing is disabled")
        
        success = await background_job_service.cancel_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
        
        return {"message": "Job cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Retry a failed job."""
    try:
        if not config.ENABLE_BACKGROUND_JOBS:
            raise HTTPException(status_code=503, detail="Background job processing is disabled")
        
        success = await background_job_service.retry_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or cannot be retried")
        
        return {"message": "Job queued for retry"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scheduled-jobs", response_model=ScheduledJobResponse)
async def create_scheduled_job(
    request: ScheduledJobRequest,
    db: Session = Depends(get_db)
):
    """Create a new scheduled job."""
    try:
        if not config.ENABLE_JOB_SCHEDULING:
            raise HTTPException(status_code=503, detail="Job scheduling is disabled")
        
        if not request.cron_expression and not request.interval_seconds:
            raise HTTPException(status_code=400, detail="Either cron_expression or interval_seconds must be provided")
        
        job_id = await background_job_service.create_scheduled_job(
            name=request.name,
            description=request.description,
            job_type=request.job_type,
            function_name=request.function_name,
            arguments=request.arguments,
            keyword_arguments=request.keyword_arguments,
            cron_expression=request.cron_expression,
            interval_seconds=request.interval_seconds,
            max_instances=request.max_instances,
            timeout_seconds=request.timeout_seconds,
            priority=request.priority
        )
        
        # Get the created job
        from database.models import ScheduledJob
        scheduled_job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
        if not scheduled_job:
            raise HTTPException(status_code=500, detail="Failed to create scheduled job")
        
        return ScheduledJobResponse(
            id=str(scheduled_job.id),
            name=scheduled_job.name,
            description=scheduled_job.description,
            job_type=scheduled_job.job_type,
            function_name=scheduled_job.function_name,
            arguments=scheduled_job.arguments,
            keyword_arguments=scheduled_job.keyword_arguments,
            cron_expression=scheduled_job.cron_expression,
            interval_seconds=scheduled_job.interval_seconds,
            next_run_at=scheduled_job.next_run_at.isoformat(),
            last_run_at=scheduled_job.last_run_at.isoformat() if scheduled_job.last_run_at else None,
            is_active=scheduled_job.is_active,
            max_instances=scheduled_job.max_instances,
            timeout_seconds=scheduled_job.timeout_seconds,
            priority=scheduled_job.priority,
            metadata=scheduled_job.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create scheduled job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scheduled-jobs", response_model=List[ScheduledJobResponse])
async def get_scheduled_jobs(
    active_only: bool = Query(False, description="Show only active jobs"),
    db: Session = Depends(get_db)
):
    """Get all scheduled jobs."""
    try:
        if not config.ENABLE_JOB_SCHEDULING:
            raise HTTPException(status_code=503, detail="Job scheduling is disabled")
        
        from database.models import ScheduledJob
        query = db.query(ScheduledJob)
        
        if active_only:
            query = query.filter(ScheduledJob.is_active == True)
        
        scheduled_jobs = query.all()
        
        return [
            ScheduledJobResponse(
                id=str(job.id),
                name=job.name,
                description=job.description,
                job_type=job.job_type,
                function_name=job.function_name,
                arguments=job.arguments,
                keyword_arguments=job.keyword_arguments,
                cron_expression=job.cron_expression,
                interval_seconds=job.interval_seconds,
                next_run_at=job.next_run_at.isoformat(),
                last_run_at=job.last_run_at.isoformat() if job.last_run_at else None,
                is_active=job.is_active,
                max_instances=job.max_instances,
                timeout_seconds=job.timeout_seconds,
                priority=job.priority,
                metadata=job.metadata
            )
            for job in scheduled_jobs
        ]
        
    except Exception as e:
        logger.error(f"Failed to get scheduled jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=WorkerStatsResponse)
async def get_worker_stats(
    db: Session = Depends(get_db)
):
    """Get worker and job statistics."""
    try:
        if not config.ENABLE_JOB_MONITORING:
            raise HTTPException(status_code=503, detail="Job monitoring is disabled")
        
        stats = await background_job_service.get_worker_stats()
        return WorkerStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get worker stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health", response_model=HealthResponse)
async def get_health(
    db: Session = Depends(get_db)
):
    """Get health status of the background job processing system."""
    try:
        # Check if services are enabled
        services = {
            "background_jobs": config.ENABLE_BACKGROUND_JOBS,
            "job_scheduling": config.ENABLE_JOB_SCHEDULING,
            "job_monitoring": config.ENABLE_JOB_MONITORING,
            "worker_scaling": config.ENABLE_WORKER_SCALING,
            "job_persistence": config.ENABLE_JOB_PERSISTENCE
        }
        
        # Check if background job service is initialized
        if config.ENABLE_BACKGROUND_JOBS:
            services["service_initialized"] = background_job_service._initialized
        
        # Determine overall status
        if not config.ENABLE_BACKGROUND_JOBS:
            status = "disabled"
            message = "Background job processing is disabled"
        elif not background_job_service._initialized:
            status = "error"
            message = "Background job service not initialized"
        else:
            status = "healthy"
            message = "Background job processing system is healthy"
        
        return HealthResponse(
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
            services=services
        )
        
    except Exception as e:
        logger.error(f"Failed to get health status: {e}")
        return HealthResponse(
            status="error",
            message=f"Health check failed: {str(e)}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            services={}
        )

@router.post("/cleanup")
async def cleanup_old_jobs(
    days: int = Query(7, ge=1, le=365, description="Number of days to keep jobs"),
    db: Session = Depends(get_db)
):
    """Clean up old completed/failed jobs."""
    try:
        if not config.ENABLE_BACKGROUND_JOBS:
            raise HTTPException(status_code=503, detail="Background job processing is disabled")
        
        deleted_count = await background_job_service.cleanup_old_jobs(days)
        
        return {
            "message": f"Cleaned up {deleted_count} old jobs",
            "deleted_count": deleted_count,
            "days": days
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-job")
async def create_test_job(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a test job for debugging purposes."""
    try:
        if not config.ENABLE_BACKGROUND_JOBS:
            raise HTTPException(status_code=503, detail="Background job processing is disabled")
        
        job_id = await background_job_service.enqueue_job(
            job_type="test",
            function_name="test_function",
            arguments={"test_param": "test_value"},
            keyword_arguments={"test_kwarg": "test_kwvalue"},
            priority=0
        )
        
        return {
            "message": "Test job created successfully",
            "job_id": job_id,
            "job_type": "test",
            "function_name": "test_function"
        }
        
    except Exception as e:
        logger.error(f"Failed to create test job: {e}")
        raise HTTPException(status_code=500, detail=str(e))




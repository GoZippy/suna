"""
Background job processing service for Suna.

This module provides a comprehensive background job processing system using
Dramatiq for job queuing, APScheduler for scheduling, and PostgreSQL for
persistence. It includes job monitoring, worker management, and failure recovery.
"""

import asyncio
import json
import time
import traceback
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from uuid import UUID

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from utils.config import config
from utils.logger import logger
from database.connection import get_db
from database.models import JobQueue, JobResult, ScheduledJob, WorkerNode

# Global broker instance
broker = None
scheduler = None
worker_nodes = {}

class BackgroundJobService:
    """Service for managing background jobs and scheduling."""
    
    def __init__(self):
        self.broker = None
        self.scheduler = None
        self.worker_id = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the background job service."""
        if self._initialized:
            return
        
        try:
            # Initialize Redis broker
            self.broker = RedisBroker(
                host=config.REDIS_BROKER_HOST,
                port=config.REDIS_BROKER_PORT,
                password=config.REDIS_BROKER_PASSWORD,
                ssl=config.REDIS_BROKER_SSL,
                db=config.REDIS_BROKER_DB,
                middleware=[AsyncIO()]
            )
            
            # Set the broker globally for Dramatiq
            dramatiq.set_broker(self.broker)
            
            # Initialize scheduler if enabled
            if config.ENABLE_JOB_SCHEDULING:
                self.scheduler = AsyncIOScheduler(
                    timezone=config.SCHEDULER_TIMEZONE,
                    job_defaults={
                        'max_instances': config.SCHEDULER_MAX_INSTANCES,
                        'coalesce': config.SCHEDULER_COALESCE,
                        'misfire_grace_time': config.SCHEDULER_MISFIRE_GRACE_TIME
                    }
                )
                await self._load_scheduled_jobs()
                self.scheduler.start()
                logger.info("Background job scheduler started")
            
            # Register worker node
            self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
            await self._register_worker_node()
            
            self._initialized = True
            logger.info(f"Background job service initialized with worker ID: {self.worker_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize background job service: {e}")
            raise
    
    async def _register_worker_node(self):
        """Register this worker node in the database."""
        try:
            db = next(get_db())
            worker_node = WorkerNode(
                worker_id=self.worker_id,
                hostname=config.REDIS_BROKER_HOST,
                status='active',
                process_count=config.WORKER_PROCESSES,
                thread_count=config.WORKER_THREADS,
                last_heartbeat=datetime.now(timezone.utc)
            )
            db.add(worker_node)
            db.commit()
            logger.info(f"Registered worker node: {self.worker_id}")
        except Exception as e:
            logger.error(f"Failed to register worker node: {e}")
    
    async def _load_scheduled_jobs(self):
        """Load scheduled jobs from database into scheduler."""
        try:
            db = next(get_db())
            scheduled_jobs = db.query(ScheduledJob).filter(
                ScheduledJob.is_active == True
            ).all()
            
            for job in scheduled_jobs:
                await self._add_scheduled_job_to_scheduler(job)
            
            logger.info(f"Loaded {len(scheduled_jobs)} scheduled jobs")
        except Exception as e:
            logger.error(f"Failed to load scheduled jobs: {e}")
    
    async def _add_scheduled_job_to_scheduler(self, scheduled_job: ScheduledJob):
        """Add a scheduled job to the APScheduler."""
        try:
            if scheduled_job.cron_expression:
                trigger = CronTrigger.from_crontab(scheduled_job.cron_expression)
            elif scheduled_job.interval_seconds:
                trigger = IntervalTrigger(seconds=scheduled_job.interval_seconds)
            else:
                logger.warning(f"Scheduled job {scheduled_job.name} has no trigger")
                return
            
            self.scheduler.add_job(
                func=self._execute_scheduled_job,
                trigger=trigger,
                args=[scheduled_job.id],
                id=str(scheduled_job.id),
                name=scheduled_job.name,
                max_instances=scheduled_job.max_instances,
                replace_existing=True
            )
            
            logger.debug(f"Added scheduled job to scheduler: {scheduled_job.name}")
        except Exception as e:
            logger.error(f"Failed to add scheduled job to scheduler: {e}")
    
    async def _execute_scheduled_job(self, scheduled_job_id: UUID):
        """Execute a scheduled job."""
        try:
            db = next(get_db())
            scheduled_job = db.query(ScheduledJob).filter(
                ScheduledJob.id == scheduled_job_id
            ).first()
            
            if not scheduled_job or not scheduled_job.is_active:
                return
            
            # Create job queue entry
            job_queue = JobQueue(
                job_type=scheduled_job.job_type,
                job_name=scheduled_job.name,
                function_name=scheduled_job.function_name,
                arguments=scheduled_job.arguments,
                keyword_arguments=scheduled_job.keyword_arguments,
                priority=scheduled_job.priority,
                max_retries=config.JOB_QUEUE_MAX_RETRIES,
                scheduled_at=datetime.now(timezone.utc)
            )
            db.add(job_queue)
            db.commit()
            
            # Update scheduled job last run
            scheduled_job.last_run_at = datetime.now(timezone.utc)
            scheduled_job.next_run_at = self._calculate_next_run(scheduled_job)
            db.commit()
            
            # Enqueue the job
            await self.enqueue_job(
                job_type=scheduled_job.job_type,
                function_name=scheduled_job.function_name,
                arguments=scheduled_job.arguments,
                keyword_arguments=scheduled_job.keyword_arguments,
                priority=scheduled_job.priority,
                job_id=str(job_queue.id)
            )
            
            logger.info(f"Executed scheduled job: {scheduled_job.name}")
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled job {scheduled_job_id}: {e}")
    
    def _calculate_next_run(self, scheduled_job: ScheduledJob) -> datetime:
        """Calculate the next run time for a scheduled job."""
        now = datetime.now(timezone.utc)
        
        if scheduled_job.cron_expression:
            trigger = CronTrigger.from_crontab(scheduled_job.cron_expression)
            return trigger.next_fire_time(None, now)
        elif scheduled_job.interval_seconds:
            return now + timedelta(seconds=scheduled_job.interval_seconds)
        else:
            return now + timedelta(hours=1)  # Default fallback
    
    async def enqueue_job(
        self,
        job_type: str,
        function_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        keyword_arguments: Optional[Dict[str, Any]] = None,
        priority: int = None,
        scheduled_at: Optional[datetime] = None,
        job_id: Optional[str] = None
    ) -> str:
        """Enqueue a job for execution."""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Create job queue entry
            db = next(get_db())
            job_queue = JobQueue(
                id=UUID(job_id) if job_id else uuid4(),
                job_type=job_type,
                job_name=f"{job_type}_{function_name}",
                function_name=function_name,
                arguments=arguments or {},
                keyword_arguments=keyword_arguments or {},
                priority=priority or config.JOB_QUEUE_DEFAULT_PRIORITY,
                scheduled_at=scheduled_at or datetime.now(timezone.utc)
            )
            db.add(job_queue)
            db.commit()
            
            # Send to Dramatiq broker
            message = self.broker.enqueue(
                execute_job,
                job_id=str(job_queue.id),
                job_type=job_type,
                function_name=function_name,
                arguments=arguments or {},
                keyword_arguments=keyword_arguments or {},
                priority=priority or config.JOB_QUEUE_DEFAULT_PRIORITY
            )
            
            logger.info(f"Enqueued job {job_queue.id} of type {job_type}")
            return str(job_queue.id)
            
        except Exception as e:
            logger.error(f"Failed to enqueue job: {e}")
            raise
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a job."""
        try:
            db = next(get_db())
            job = db.query(JobQueue).filter(JobQueue.id == job_id).first()
            
            if not job:
                return None
            
            result = {
                'id': str(job.id),
                'job_type': job.job_type,
                'job_name': job.job_name,
                'status': job.status,
                'priority': job.priority,
                'retry_count': job.retry_count,
                'max_retries': job.max_retries,
                'scheduled_at': job.scheduled_at.isoformat() if job.scheduled_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'worker_id': job.worker_id,
                'error_message': job.error_message,
                'metadata': job.metadata
            }
            
            if job.result:
                result['result'] = {
                    'result_type': job.result.result_type,
                    'execution_time': float(job.result.execution_time) if job.result.execution_time else None,
                    'memory_usage': job.result.memory_usage,
                    'cpu_usage': float(job.result.cpu_usage) if job.result.cpu_usage else None
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return None
    
    async def get_job_queue(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get jobs from the queue with optional filtering."""
        try:
            db = next(get_db())
            query = db.query(JobQueue)
            
            if status:
                query = query.filter(JobQueue.status == status)
            if job_type:
                query = query.filter(JobQueue.job_type == job_type)
            
            jobs = query.order_by(desc(JobQueue.scheduled_at)).offset(offset).limit(limit).all()
            
            return [await self.get_job_status(str(job.id)) for job in jobs]
            
        except Exception as e:
            logger.error(f"Failed to get job queue: {e}")
            return []
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        try:
            db = next(get_db())
            job = db.query(JobQueue).filter(
                and_(
                    JobQueue.id == job_id,
                    JobQueue.status.in_(['pending', 'running'])
                )
            ).first()
            
            if not job:
                return False
            
            job.status = 'cancelled'
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            
            logger.info(f"Cancelled job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job: {e}")
            return False
    
    async def retry_job(self, job_id: str) -> bool:
        """Retry a failed job."""
        try:
            db = next(get_db())
            job = db.query(JobQueue).filter(
                and_(
                    JobQueue.id == job_id,
                    JobQueue.status == 'failed',
                    JobQueue.retry_count < JobQueue.max_retries
                )
            ).first()
            
            if not job:
                return False
            
            # Reset job for retry
            job.status = 'pending'
            job.retry_count += 1
            job.started_at = None
            job.completed_at = None
            job.worker_id = None
            job.error_message = None
            job.scheduled_at = datetime.now(timezone.utc)
            db.commit()
            
            # Re-enqueue
            await self.enqueue_job(
                job_type=job.job_type,
                function_name=job.function_name,
                arguments=job.arguments,
                keyword_arguments=job.keyword_arguments,
                priority=job.priority,
                job_id=str(job.id)
            )
            
            logger.info(f"Retried job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry job: {e}")
            return False
    
    async def create_scheduled_job(
        self,
        name: str,
        description: str,
        job_type: str,
        function_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        keyword_arguments: Optional[Dict[str, Any]] = None,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        max_instances: int = 1,
        timeout_seconds: int = 3600,
        priority: int = 0
    ) -> str:
        """Create a new scheduled job."""
        try:
            if not cron_expression and not interval_seconds:
                raise ValueError("Either cron_expression or interval_seconds must be provided")
            
            db = next(get_db())
            scheduled_job = ScheduledJob(
                name=name,
                description=description,
                job_type=job_type,
                function_name=function_name,
                arguments=arguments or {},
                keyword_arguments=keyword_arguments or {},
                cron_expression=cron_expression,
                interval_seconds=interval_seconds,
                next_run_at=self._calculate_next_run_time(cron_expression, interval_seconds),
                max_instances=max_instances,
                timeout_seconds=timeout_seconds,
                priority=priority
            )
            db.add(scheduled_job)
            db.commit()
            
            # Add to scheduler if active
            if self.scheduler and scheduled_job.is_active:
                await self._add_scheduled_job_to_scheduler(scheduled_job)
            
            logger.info(f"Created scheduled job: {name}")
            return str(scheduled_job.id)
            
        except Exception as e:
            logger.error(f"Failed to create scheduled job: {e}")
            raise
    
    def _calculate_next_run_time(
        self,
        cron_expression: Optional[str],
        interval_seconds: Optional[int]
    ) -> datetime:
        """Calculate the next run time for a new scheduled job."""
        now = datetime.now(timezone.utc)
        
        if cron_expression:
            trigger = CronTrigger.from_crontab(cron_expression)
            return trigger.next_fire_time(None, now)
        elif interval_seconds:
            return now + timedelta(seconds=interval_seconds)
        else:
            return now + timedelta(hours=1)
    
    async def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        try:
            db = next(get_db())
            
            # Get active workers
            active_workers = db.query(WorkerNode).filter(
                WorkerNode.status == 'active'
            ).all()
            
            # Get job statistics
            job_stats = db.query(
                JobQueue.status,
                func.count(JobQueue.id).label('count')
            ).group_by(JobQueue.status).all()
            
            stats = {
                'active_workers': len(active_workers),
                'total_workers': db.query(WorkerNode).count(),
                'job_stats': {stat.status: stat.count for stat in job_stats},
                'workers': [
                    {
                        'worker_id': worker.worker_id,
                        'hostname': worker.hostname,
                        'status': worker.status,
                        'process_count': worker.process_count,
                        'thread_count': worker.thread_count,
                        'current_load': float(worker.current_load),
                        'last_heartbeat': worker.last_heartbeat.isoformat(),
                        'uptime': (datetime.now(timezone.utc) - worker.started_at).total_seconds()
                    }
                    for worker in active_workers
                ]
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get worker stats: {e}")
            return {}
    
    async def cleanup_old_jobs(self, days: int = 7) -> int:
        """Clean up old completed/failed jobs."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            db = next(get_db())
            deleted_count = db.query(JobQueue).filter(
                and_(
                    JobQueue.status.in_(['completed', 'failed', 'cancelled']),
                    JobQueue.completed_at < cutoff_date
                )
            ).delete()
            
            db.commit()
            logger.info(f"Cleaned up {deleted_count} old jobs")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
            return 0

# Global service instance
background_job_service = BackgroundJobService()

@dramatiq.actor
async def execute_job(
    job_id: str,
    job_type: str,
    function_name: str,
    arguments: Dict[str, Any],
    keyword_arguments: Dict[str, Any],
    priority: int = 0
):
    """Execute a background job."""
    start_time = time.time()
    job_result = None
    
    try:
        # Update job status to running
        db = next(get_db())
        job = db.query(JobQueue).filter(JobQueue.id == job_id).first()
        
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        job.status = 'running'
        job.started_at = datetime.now(timezone.utc)
        job.worker_id = background_job_service.worker_id
        db.commit()
        
        # Execute the job function
        logger.info(f"Executing job {job_id}: {function_name}")
        
        # Here you would dynamically call the function
        # For now, we'll just simulate execution
        result_data = {
            'job_type': job_type,
            'function_name': function_name,
            'arguments': arguments,
            'keyword_arguments': keyword_arguments,
            'execution_time': time.time() - start_time
        }
        
        # Update job status to completed
        job.status = 'completed'
        job.completed_at = datetime.now(timezone.utc)
        
        # Create job result
        job_result = JobResult(
            job_id=job.id,
            result_data=result_data,
            result_type='success',
            execution_time=time.time() - start_time
        )
        db.add(job_result)
        db.commit()
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        error_message = f"Job execution failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"Job {job_id} failed: {error_message}")
        
        try:
            # Update job status to failed
            db = next(get_db())
            job = db.query(JobQueue).filter(JobQueue.id == job_id).first()
            if job:
                job.status = 'failed'
                job.completed_at = datetime.now(timezone.utc)
                job.error_message = error_message
                
                # Create job result for failure
                job_result = JobResult(
                    job_id=job.id,
                    result_data={'error': error_message},
                    result_type='error',
                    execution_time=time.time() - start_time
                )
                db.add(job_result)
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")

async def initialize_background_jobs():
    """Initialize the background job processing system."""
    try:
        await background_job_service.initialize()
        logger.info("Background job processing system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize background job processing: {e}")
        raise




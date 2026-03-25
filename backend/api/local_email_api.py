"""
Local Email and Notification API

Provides endpoints for managing local email delivery and system notifications.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import logging

from database.connection import get_db
from services.local_email import LocalEmailService, NotificationService
from utils.config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/local-email", tags=["local-email"])

# Pydantic models for API requests/responses
class EmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    template_name: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    priority: int = 0
    scheduled_at: Optional[str] = None

class EmailResponse(BaseModel):
    id: str
    status: str
    message: str

class EmailQueueItem(BaseModel):
    id: str
    to_email: str
    subject: str
    status: str
    priority: int
    scheduled_at: str
    sent_at: Optional[str] = None
    retry_count: int
    error_message: Optional[str] = None

class NotificationRequest(BaseModel):
    user_id: str
    notification_type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    priority: int = 0

class NotificationResponse(BaseModel):
    id: str
    message: str

class NotificationItem(BaseModel):
    id: str
    notification_type: str
    title: str
    message: str
    priority: int
    read_at: Optional[str] = None
    created_at: str

# Initialize services
email_service = LocalEmailService()
notification_service = NotificationService()

@router.post("/send", response_model=EmailResponse)
async def send_email(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send an email immediately or add to queue"""
    try:
        if not config.ENABLE_LOCAL_EMAIL:
            raise HTTPException(status_code=503, detail="Local email service is disabled")
        
        email_id = await email_service.send_email(
            to_email=request.to_email,
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html,
            template_name=request.template_name,
            template_data=request.template_data or {},
            priority=request.priority,
            scheduled_at=request.scheduled_at,
            db=db
        )
        
        return EmailResponse(
            id=str(email_id),
            status="queued",
            message="Email added to queue successfully"
        )
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue", response_model=List[EmailQueueItem])
async def get_email_queue(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get email queue items with optional filtering"""
    try:
        if not config.ENABLE_LOCAL_EMAIL:
            raise HTTPException(status_code=503, detail="Local email service is disabled")
        
        items = await email_service.get_queue_items(
            status=status,
            limit=limit,
            db=db
        )
        
        return [
            EmailQueueItem(
                id=str(item.id),
                to_email=item.to_email,
                subject=item.subject,
                status=item.status,
                priority=item.priority,
                scheduled_at=item.scheduled_at.isoformat(),
                sent_at=item.sent_at.isoformat() if item.sent_at else None,
                retry_count=item.retry_count,
                error_message=item.error_message
            )
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get email queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/queue/{email_id}/retry")
async def retry_email(
    email_id: str,
    db: Session = Depends(get_db)
):
    """Retry sending a failed email"""
    try:
        if not config.ENABLE_LOCAL_EMAIL:
            raise HTTPException(status_code=503, detail="Local email service is disabled")
        
        success = await email_service.retry_email(email_id, db)
        if not success:
            raise HTTPException(status_code=404, detail="Email not found or cannot be retried")
        
        return {"message": "Email queued for retry"}
    except Exception as e:
        logger.error(f"Failed to retry email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/queue/{email_id}")
async def cancel_email(
    email_id: str,
    db: Session = Depends(get_db)
):
    """Cancel a pending email"""
    try:
        if not config.ENABLE_LOCAL_EMAIL:
            raise HTTPException(status_code=503, detail="Local email service is disabled")
        
        success = await email_service.cancel_email(email_id, db)
        if not success:
            raise HTTPException(status_code=404, detail="Email not found or cannot be cancelled")
        
        return {"message": "Email cancelled successfully"}
    except Exception as e:
        logger.error(f"Failed to cancel email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/send", response_model=NotificationResponse)
async def send_notification(
    request: NotificationRequest,
    db: Session = Depends(get_db)
):
    """Send a system notification to a user"""
    try:
        if not config.ENABLE_EMAIL_NOTIFICATIONS:
            raise HTTPException(status_code=503, detail="Notification service is disabled")
        
        notification_id = await notification_service.send_notification(
            user_id=request.user_id,
            notification_type=request.notification_type,
            title=request.title,
            message=request.message,
            data=request.data or {},
            priority=request.priority,
            db=db
        )
        
        return NotificationResponse(
            id=str(notification_id),
            message="Notification sent successfully"
        )
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notifications/{user_id}", response_model=List[NotificationItem])
async def get_user_notifications(
    user_id: str,
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get notifications for a specific user"""
    try:
        if not config.ENABLE_EMAIL_NOTIFICATIONS:
            raise HTTPException(status_code=503, detail="Notification service is disabled")
        
        notifications = await notification_service.get_user_notifications(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit,
            db=db
        )
        
        return [
            NotificationItem(
                id=str(notification.id),
                notification_type=notification.notification_type,
                title=notification.title,
                message=notification.message,
                priority=notification.priority,
                read_at=notification.read_at.isoformat() if notification.read_at else None,
                created_at=notification.created_at.isoformat()
            )
            for notification in notifications
        ]
    except Exception as e:
        logger.error(f"Failed to get notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    try:
        if not config.ENABLE_EMAIL_NOTIFICATIONS:
            raise HTTPException(status_code=503, detail="Notification service is disabled")
        
        success = await notification_service.mark_read(notification_id, db)
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {"message": "Notification marked as read"}
    except Exception as e:
        logger.error(f"Failed to mark notification as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/{user_id}/read-all")
async def mark_all_notifications_read(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Mark all notifications for a user as read"""
    try:
        if not config.ENABLE_EMAIL_NOTIFICATIONS:
            raise HTTPException(status_code=503, detail="Notification service is disabled")
        
        count = await notification_service.mark_all_read(user_id, db)
        return {"message": f"Marked {count} notifications as read"}
    except Exception as e:
        logger.error(f"Failed to mark all notifications as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Check the health of the local email and notification services"""
    try:
        email_health = await email_service.health_check()
        notification_health = await notification_service.health_check()
        
        return {
            "email_service": email_health,
            "notification_service": notification_health,
            "enabled": {
                "email": config.ENABLE_LOCAL_EMAIL,
                "notifications": config.ENABLE_EMAIL_NOTIFICATIONS,
                "queue": config.ENABLE_EMAIL_QUEUE
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))




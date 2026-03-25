"""
Local Email and Notification Service

This module provides a comprehensive local email system that replaces external
email service dependencies. It includes SMTP configuration, email templates,
queue management, retry logic, and delivery tracking.
"""

import os
import smtplib
import ssl
import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from utils.config import config
from utils.logger import logger
from database.connection import get_db_session
from database.models import EmailQueue, NotificationLog

class EmailStatus(Enum):
    """Email delivery status enumeration."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BOUNCED = "bounced"

class NotificationType(Enum):
    """Notification type enumeration."""
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    SYSTEM_ALERT = "system_alert"
    USAGE_WARNING = "usage_warning"
    CREDIT_LOW = "credit_low"
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"

@dataclass
class EmailTemplate:
    """Email template configuration."""
    name: str
    subject: str
    html_template: str
    text_template: str
    variables: List[str]

@dataclass
class EmailRequest:
    """Email request data structure."""
    to_email: str
    to_name: Optional[str] = None
    subject: str = ""
    html_content: str = ""
    text_content: str = ""
    template_name: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    priority: int = 0
    scheduled_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class LocalEmailService:
    """Local email service using SMTP."""
    
    def __init__(self):
        self.smtp_host = config.SMTP_HOST or "localhost"
        self.smtp_port = config.SMTP_PORT or 1025
        self.smtp_user = config.SMTP_USER
        self.smtp_password = config.SMTP_PASSWORD
        self.sender_email = config.SENDER_EMAIL or "noreply@suna.local"
        self.sender_name = config.SENDER_NAME or "Suna System"
        self.use_tls = config.SMTP_USE_TLS or False
        self.use_ssl = config.SMTP_USE_SSL or False
        
        # Load email templates
        self.templates = self._load_email_templates()
        
        # Initialize SMTP connection
        self.smtp_connection = None
        self._connection_initialized = False
        
    def _load_email_templates(self) -> Dict[str, EmailTemplate]:
        """Load email templates from configuration."""
        templates = {
            "welcome": EmailTemplate(
                name="welcome",
                subject="🎉 Welcome to Suna — Let's Get Started",
                html_template=self._get_welcome_html_template(),
                text_template=self._get_welcome_text_template(),
                variables=["user_name", "app_name", "login_url"]
            ),
            "password_reset": EmailTemplate(
                name="password_reset",
                subject="🔐 Reset Your Suna Password",
                html_template=self._get_password_reset_html_template(),
                text_template=self._get_password_reset_text_template(),
                variables=["user_name", "reset_url", "expiry_hours"]
            ),
            "email_verification": EmailTemplate(
                name="email_verification",
                subject="✅ Verify Your Email Address",
                html_template=self._get_verification_html_template(),
                text_template=self._get_verification_text_template(),
                variables=["user_name", "verification_url", "expiry_hours"]
            ),
            "system_alert": EmailTemplate(
                name="system_alert",
                subject="⚠️ System Alert: {alert_type}",
                html_template=self._get_system_alert_html_template(),
                text_template=self._get_system_alert_text_template(),
                variables=["alert_type", "alert_message", "timestamp", "severity"]
            ),
            "usage_warning": EmailTemplate(
                name="usage_warning",
                subject="📊 Usage Warning: {usage_type}",
                html_template=self._get_usage_warning_html_template(),
                text_template=self._get_usage_warning_text_template(),
                variables=["user_name", "usage_type", "current_usage", "limit", "percentage"]
            ),
            "credit_low": EmailTemplate(
                name="credit_low",
                subject="💳 Low Credit Balance Alert",
                html_template=self._get_credit_low_html_template(),
                text_template=self._get_credit_low_text_template(),
                variables=["user_name", "current_credits", "threshold", "recharge_url"]
            ),
            "agent_complete": EmailTemplate(
                name="agent_complete",
                subject="✅ Agent Task Completed",
                html_template=self._get_agent_complete_html_template(),
                text_template=self._get_agent_complete_text_template(),
                variables=["user_name", "agent_name", "task_description", "result_summary", "view_url"]
            ),
            "agent_error": EmailTemplate(
                name="agent_error",
                subject="❌ Agent Task Failed",
                html_template=self._get_agent_error_html_template(),
                text_template=self._get_agent_error_text_template(),
                variables=["user_name", "agent_name", "task_description", "error_message", "view_url"]
            )
        }
        return templates
    
    async def initialize(self):
        """Initialize the email service."""
        try:
            # Test SMTP connection
            await self._test_smtp_connection()
            self._connection_initialized = True
            logger.info(f"Local email service initialized with SMTP: {self.smtp_host}:{self.smtp_port}")
        except Exception as e:
            logger.warning(f"Failed to initialize SMTP connection: {e}")
            self._connection_initialized = False
    
    async def _test_smtp_connection(self):
        """Test SMTP connection."""
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                if self.use_tls:
                    server.starttls()
            
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            
            server.quit()
            logger.debug("SMTP connection test successful")
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            raise
    
    async def send_email(self, email_request: EmailRequest) -> bool:
        """Send an email immediately."""
        try:
            # Prepare email content
            if email_request.template_name and email_request.template_data:
                html_content, text_content, subject = self._render_template(
                    email_request.template_name,
                    email_request.template_data
                )
            else:
                html_content = email_request.html_content
                text_content = email_request.text_content
                subject = email_request.subject
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = email_request.to_email
            
            # Add content
            if html_content:
                message.attach(MIMEText(html_content, "html"))
            if text_content:
                message.attach(MIMEText(text_content, "plain"))
            
            # Send email
            return await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending email to {email_request.to_email}: {e}")
            return False
    
    async def queue_email(self, email_request: EmailRequest) -> str:
        """Queue an email for later sending."""
        try:
            db = next(get_db_session())
            
            # Prepare email content
            if email_request.template_name and email_request.template_data:
                html_content, text_content, subject = self._render_template(
                    email_request.template_name,
                    email_request.template_data
                )
            else:
                html_content = email_request.html_content
                text_content = email_request.text_content
                subject = email_request.subject
            
            # Create email queue entry
            queue_entry = EmailQueue(
                to_email=email_request.to_email,
                from_email=self.sender_email,
                subject=subject,
                body_text=text_content,
                body_html=html_content,
                template_name=email_request.template_name,
                template_data=email_request.template_data or {},
                status=EmailStatus.PENDING.value,
                priority=email_request.priority,
                max_retries=3,
                retry_count=0,
                scheduled_at=email_request.scheduled_at or datetime.now(timezone.utc),
                metadata=email_request.metadata or {}
            )
            
            db.add(queue_entry)
            db.commit()
            db.refresh(queue_entry)
            
            logger.info(f"Email queued for {email_request.to_email}: {queue_entry.id}")
            return str(queue_entry.id)
            
        except Exception as e:
            logger.error(f"Error queuing email for {email_request.to_email}: {e}")
            raise
        finally:
            db.close()
    
    async def process_email_queue(self, batch_size: int = 10) -> Dict[str, int]:
        """Process queued emails."""
        stats = {"processed": 0, "sent": 0, "failed": 0}
        
        try:
            db = next(get_db_session())
            
            # Get pending emails
            pending_emails = db.query(EmailQueue).filter(
                and_(
                    EmailQueue.status == EmailStatus.PENDING.value,
                    EmailQueue.scheduled_at <= datetime.now(timezone.utc),
                    EmailQueue.retry_count < EmailQueue.max_retries
                )
            ).order_by(EmailQueue.priority.desc(), EmailQueue.scheduled_at.asc()).limit(batch_size).all()
            
            for email in pending_emails:
                stats["processed"] += 1
                
                try:
                    # Create message
                    message = MIMEMultipart("alternative")
                    message["Subject"] = email.subject
                    message["From"] = f"{self.sender_name} <{email.from_email}>"
                    message["To"] = email.to_email
                    
                    if email.body_html:
                        message.attach(MIMEText(email.body_html, "html"))
                    if email.body_text:
                        message.attach(MIMEText(email.body_text, "plain"))
                    
                    # Send email
                    success = await self._send_message(message)
                    
                    if success:
                        email.status = EmailStatus.SENT.value
                        email.sent_at = datetime.now(timezone.utc)
                        stats["sent"] += 1
                        logger.info(f"Email sent successfully: {email.id}")
                    else:
                        email.retry_count += 1
                        if email.retry_count >= email.max_retries:
                            email.status = EmailStatus.FAILED.value
                            email.error_message = "Max retries exceeded"
                            stats["failed"] += 1
                            logger.error(f"Email failed after max retries: {email.id}")
                        else:
                            # Schedule retry with exponential backoff
                            backoff_minutes = 2 ** email.retry_count
                            email.scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
                            logger.warning(f"Email retry scheduled: {email.id} (attempt {email.retry_count})")
                    
                    db.commit()
                    
                except Exception as e:
                    email.retry_count += 1
                    email.error_message = str(e)
                    if email.retry_count >= email.max_retries:
                        email.status = EmailStatus.FAILED.value
                        stats["failed"] += 1
                    db.commit()
                    logger.error(f"Error processing email {email.id}: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error processing email queue: {e}")
            return stats
        finally:
            db.close()
    
    async def _send_message(self, message: MIMEMultipart) -> bool:
        """Send a message via SMTP."""
        try:
            if not self._connection_initialized:
                await self.initialize()
            
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                if self.use_tls:
                    server.starttls()
            
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            
            server.send_message(message)
            server.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"SMTP send error: {e}")
            return False
    
    def _render_template(self, template_name: str, data: Dict[str, Any]) -> tuple[str, str, str]:
        """Render an email template with data."""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        
        # Render subject
        subject = template.subject.format(**data)
        
        # Render HTML content
        html_content = template.html_template
        for var in template.variables:
            if var in data:
                html_content = html_content.replace(f"{{{var}}}", str(data[var]))
        
        # Render text content
        text_content = template.text_template
        for var in template.variables:
            if var in data:
                text_content = text_content.replace(f"{{{var}}}", str(data[var]))
        
        return html_content, text_content, subject
    
    async def send_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: int = 0
    ) -> str:
        """Send a system notification."""
        try:
            db = next(get_db_session())
            
            # Create notification log entry
            notification = NotificationLog(
                user_id=user_id,
                notification_type=notification_type.value,
                title=title,
                message=message,
                data=data or {},
                priority=priority,
                read_at=None,
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            logger.info(f"Notification created: {notification.id} for user {user_id}")
            return str(notification.id)
            
        except Exception as e:
            logger.error(f"Error creating notification for user {user_id}: {e}")
            raise
        finally:
            db.close()
    
    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get notifications for a user."""
        try:
            db = next(get_db_session())
            
            query = db.query(NotificationLog).filter(NotificationLog.user_id == user_id)
            
            if unread_only:
                query = query.filter(NotificationLog.read_at.is_(None))
            
            notifications = query.order_by(
                NotificationLog.created_at.desc()
            ).limit(limit).all()
            
            return [asdict(notification) for notification in notifications]
            
        except Exception as e:
            logger.error(f"Error getting notifications for user {user_id}: {e}")
            return []
        finally:
            db.close()
    
    async def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read."""
        try:
            db = next(get_db_session())
            
            notification = db.query(NotificationLog).filter(
                and_(
                    NotificationLog.id == notification_id,
                    NotificationLog.user_id == user_id
                )
            ).first()
            
            if notification:
                notification.read_at = datetime.now(timezone.utc)
                db.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error marking notification {notification_id} as read: {e}")
            return False
        finally:
            db.close()
    
    # Template methods
    def _get_welcome_html_template(self) -> str:
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to {app_name}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .button { display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Welcome to {app_name}!</h1>
        </div>
        
        <p>Hi {user_name},</p>
        
        <p>Welcome to {app_name} — we're excited to have you on board!</p>
        
        <p>To get started, please visit our platform:</p>
        
        <p style="text-align: center;">
            <a href="{login_url}" class="button">Get Started</a>
        </p>
        
        <p>If you have any questions or need help getting started, don't hesitate to reach out to our support team.</p>
        
        <p>Best regards,<br>The {app_name} Team</p>
        
        <div class="footer">
            <p>This email was sent to you because you signed up for a {app_name} account.</p>
        </div>
    </div>
</body>
</html>"""
    
    def _get_welcome_text_template(self) -> str:
        return """Hi {user_name},

Welcome to {app_name} — we're excited to have you on board!

To get started, please visit our platform: {login_url}

If you have any questions or need help getting started, don't hesitate to reach out to our support team.

Best regards,
The {app_name} Team

---
This email was sent to you because you signed up for a {app_name} account."""
    
    def _get_password_reset_html_template(self) -> str:
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .button { display: inline-block; padding: 12px 24px; background-color: #dc3545; color: white; text-decoration: none; border-radius: 5px; }
        .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Reset Your Password</h1>
        </div>
        
        <p>Hi {user_name},</p>
        
        <p>We received a request to reset your password. Click the button below to create a new password:</p>
        
        <p style="text-align: center;">
            <a href="{reset_url}" class="button">Reset Password</a>
        </p>
        
        <div class="warning">
            <strong>Important:</strong> This link will expire in {expiry_hours} hours. If you didn't request this password reset, please ignore this email.
        </div>
        
        <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
        <p>{reset_url}</p>
        
        <p>Best regards,<br>The Suna Team</p>
    </div>
</body>
</html>"""
    
    def _get_password_reset_text_template(self) -> str:
        return """Hi {user_name},

We received a request to reset your password. Click the link below to create a new password:

{reset_url}

Important: This link will expire in {expiry_hours} hours. If you didn't request this password reset, please ignore this email.

Best regards,
The Suna Team"""
    
    def _get_verification_html_template(self) -> str:
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .button { display: inline-block; padding: 12px 24px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Verify Your Email Address</h1>
        </div>
        
        <p>Hi {user_name},</p>
        
        <p>Please verify your email address by clicking the button below:</p>
        
        <p style="text-align: center;">
            <a href="{verification_url}" class="button">Verify Email</a>
        </p>
        
        <p>This link will expire in {expiry_hours} hours.</p>
        
        <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
        <p>{verification_url}</p>
        
        <p>Best regards,<br>The Suna Team</p>
    </div>
</body>
</html>"""
    
    def _get_verification_text_template(self) -> str:
        return """Hi {user_name},

Please verify your email address by clicking the link below:

{verification_url}

This link will expire in {expiry_hours} hours.

Best regards,
The Suna Team"""
    
    def _get_system_alert_html_template(self) -> str:
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Alert</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .alert { background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .timestamp { font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚠️ System Alert: {alert_type}</h1>
        
        <div class="alert">
            <strong>Severity:</strong> {severity}<br>
            <strong>Time:</strong> {timestamp}
        </div>
        
        <p>{alert_message}</p>
        
        <p class="timestamp">This alert was generated automatically by the Suna system.</p>
    </div>
</body>
</html>"""
    
    def _get_system_alert_text_template(self) -> str:
        return """System Alert: {alert_type}

Severity: {severity}
Time: {timestamp}

{alert_message}

This alert was generated automatically by the Suna system."""
    
    def _get_usage_warning_html_template(self) -> str:
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Usage Warning</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .progress { background-color: #e9ecef; border-radius: 5px; height: 20px; margin: 10px 0; }
        .progress-bar { background-color: #ffc107; height: 100%; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Usage Warning: {usage_type}</h1>
        
        <p>Hi {user_name},</p>
        
        <div class="warning">
            <strong>Warning:</strong> You are approaching your usage limit for {usage_type}.
        </div>
        
        <p><strong>Current Usage:</strong> {current_usage}</p>
        <p><strong>Limit:</strong> {limit}</p>
        <p><strong>Percentage Used:</strong> {percentage}%</p>
        
        <div class="progress">
            <div class="progress-bar" style="width: {percentage}%"></div>
        </div>
        
        <p>Please consider upgrading your plan or reducing usage to avoid service interruptions.</p>
        
        <p>Best regards,<br>The Suna Team</p>
    </div>
</body>
</html>"""
    
    def _get_usage_warning_text_template(self) -> str:
        return """Usage Warning: {usage_type}

Hi {user_name},

Warning: You are approaching your usage limit for {usage_type}.

Current Usage: {current_usage}
Limit: {limit}
Percentage Used: {percentage}%

Please consider upgrading your plan or reducing usage to avoid service interruptions.

Best regards,
The Suna Team"""
    
    def _get_credit_low_html_template(self) -> str:
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Low Credit Balance</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .button { display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>💳 Low Credit Balance Alert</h1>
        
        <p>Hi {user_name},</p>
        
        <div class="warning">
            <strong>Warning:</strong> Your credit balance is running low.
        </div>
        
        <p><strong>Current Credits:</strong> {current_credits}</p>
        <p><strong>Threshold:</strong> {threshold}</p>
        
        <p>To continue using our services without interruption, please recharge your account:</p>
        
        <p style="text-align: center;">
            <a href="{recharge_url}" class="button">Recharge Credits</a>
        </p>
        
        <p>Best regards,<br>The Suna Team</p>
    </div>
</body>
</html>"""
    
    def _get_credit_low_text_template(self) -> str:
        return """Low Credit Balance Alert

Hi {user_name},

Warning: Your credit balance is running low.

Current Credits: {current_credits}
Threshold: {threshold}

To continue using our services without interruption, please recharge your account: {recharge_url}

Best regards,
The Suna Team"""
    
    def _get_agent_complete_html_template(self) -> str:
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Task Completed</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .success { background-color: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .button { display: inline-block; padding: 12px 24px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Agent Task Completed</h1>
        
        <p>Hi {user_name},</p>
        
        <div class="success">
            <strong>Success!</strong> Your agent "{agent_name}" has completed its task.
        </div>
        
        <p><strong>Task:</strong> {task_description}</p>
        <p><strong>Result:</strong> {result_summary}</p>
        
        <p style="text-align: center;">
            <a href="{view_url}" class="button">View Results</a>
        </p>
        
        <p>Best regards,<br>The Suna Team</p>
    </div>
</body>
</html>"""
    
    def _get_agent_complete_text_template(self) -> str:
        return """Agent Task Completed

Hi {user_name},

Success! Your agent "{agent_name}" has completed its task.

Task: {task_description}
Result: {result_summary}

View results: {view_url}

Best regards,
The Suna Team"""
    
    def _get_agent_error_html_template(self) -> str:
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Task Failed</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .error { background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .button { display: inline-block; padding: 12px 24px; background-color: #dc3545; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>❌ Agent Task Failed</h1>
        
        <p>Hi {user_name},</p>
        
        <div class="error">
            <strong>Error:</strong> Your agent "{agent_name}" encountered an error while processing its task.
        </div>
        
        <p><strong>Task:</strong> {task_description}</p>
        <p><strong>Error:</strong> {error_message}</p>
        
        <p style="text-align: center;">
            <a href="{view_url}" class="button">View Details</a>
        </p>
        
        <p>Please review the error details and try again if needed.</p>
        
        <p>Best regards,<br>The Suna Team</p>
    </div>
</body>
</html>"""
    
    def _get_agent_error_text_template(self) -> str:
        return """Agent Task Failed

Hi {user_name},

Error: Your agent "{agent_name}" encountered an error while processing its task.

Task: {task_description}
Error: {error_message}

View details: {view_url}

Please review the error details and try again if needed.

Best regards,
The Suna Team"""

# Global instance
local_email_service = LocalEmailService()

async def initialize_local_email():
    """Initialize the local email service"""
    try:
        await local_email_service.initialize()
        logger.info("Local email service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize local email service: {e}")
        raise

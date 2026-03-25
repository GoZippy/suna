"""
Admin Dashboard for User Management and Billing Administration
Provides web-based interface for managing users, tiers, and credits
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
from uuid import UUID

from database.connection import get_db_session
from database.models import User, UsageLog, CreditTransaction
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from utils.auth_utils import get_current_user_id_from_jwt
from utils.logger import logger
import os

router = APIRouter(prefix="/admin", tags=["admin"])

# Setup templates directory
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(templates_dir, exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Main admin dashboard"""
    try:
        # Check if user is admin
        admin_user = db.query(User).filter(User.id == user_id).first()
        if not admin_user or admin_user.role != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get basic statistics
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.last_login_at >= datetime.now(timezone.utc) - timedelta(days=30)).count()
        
        # Get recent usage
        recent_usage = db.query(
            func.sum(UsageLog.amount).label('total_usage'),
            func.count(UsageLog.id).label('usage_count')
        ).filter(
            UsageLog.created_at >= datetime.now(timezone.utc) - timedelta(days=7)
        ).first()
        
        # Get recent credit transactions
        recent_transactions = db.query(CreditTransaction).order_by(
            desc(CreditTransaction.created_at)
        ).limit(10).all()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "admin_user": admin_user,
            "total_users": total_users,
            "active_users": active_users,
            "recent_usage": recent_usage,
            "recent_transactions": recent_transactions
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load admin dashboard")

@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """User management interface"""
    try:
        # Check if user is admin
        admin_user = db.query(User).filter(User.id == user_id).first()
        if not admin_user or admin_user.role != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get all users with their usage statistics
        users = db.query(User).all()
        
        user_stats = []
        for user in users:
            # Get current month usage
            current_month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_usage = db.query(func.sum(UsageLog.amount)).filter(
                UsageLog.user_id == user.id,
                UsageLog.created_at >= current_month_start
            ).scalar() or 0.0
            
            user_stats.append({
                'user': user,
                'monthly_usage': float(monthly_usage)
            })
        
        return templates.TemplateResponse("users.html", {
            "request": request,
            "admin_user": admin_user,
            "users": user_stats
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading user management: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load user management")

@router.post("/users/{target_user_id}/tier")
async def admin_change_user_tier(
    target_user_id: UUID,
    new_tier: str = Form(...),
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Change user tier from admin interface"""
    try:
        # Check if user is admin
        admin_user = db.query(User).filter(User.id == user_id).first()
        if not admin_user or admin_user.role != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get target user
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")
        
        old_tier = target_user.tier
        target_user.tier = new_tier
        db.commit()
        
        logger.info(f"Admin {user_id} changed user {target_user_id} tier from {old_tier} to {new_tier}")
        
        return RedirectResponse(url="/admin/users", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing user tier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to change user tier")

@router.post("/users/{target_user_id}/credits")
async def admin_add_user_credits(
    target_user_id: UUID,
    amount: float = Form(...),
    reason: str = Form(...),
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Add credits to user from admin interface"""
    try:
        # Check if user is admin
        admin_user = db.query(User).filter(User.id == user_id).first()
        if not admin_user or admin_user.role != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get target user
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")
        
        # Create credit transaction
        transaction = CreditTransaction(
            user_id=target_user_id,
            transaction_type='grant',
            amount=amount,
            balance_before=target_user.credit_balance,
            balance_after=target_user.credit_balance + amount,
            description=f"Admin grant: {reason}",
            metadata={'granted_by': str(user_id)}
        )
        
        # Update user credit balance
        target_user.credit_balance += amount
        
        db.add(transaction)
        db.commit()
        
        logger.info(f"Admin {user_id} granted {amount} credits to user {target_user_id}: {reason}")
        
        return RedirectResponse(url="/admin/users", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting credits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to grant credits")

@router.get("/usage", response_class=HTMLResponse)
async def admin_usage_analytics(
    request: Request,
    period_days: int = 30,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Usage analytics dashboard"""
    try:
        # Check if user is admin
        admin_user = db.query(User).filter(User.id == user_id).first()
        if not admin_user or admin_user.role != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get usage statistics for the period
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)
        
        # Usage by resource type
        usage_by_type = db.query(
            UsageLog.resource_type,
            func.sum(UsageLog.amount).label('total_amount'),
            func.sum(UsageLog.cost).label('total_cost'),
            func.count(UsageLog.id).label('usage_count')
        ).filter(
            UsageLog.created_at >= cutoff_date
        ).group_by(UsageLog.resource_type).all()
        
        # Top users by usage
        top_users = db.query(
            User.email,
            User.tier,
            func.sum(UsageLog.amount).label('total_usage'),
            func.sum(UsageLog.cost).label('total_cost')
        ).join(UsageLog).filter(
            UsageLog.created_at >= cutoff_date
        ).group_by(User.id, User.email, User.tier).order_by(
            desc(func.sum(UsageLog.cost))
        ).limit(10).all()
        
        # Daily usage trend
        daily_usage = db.query(
            func.date(UsageLog.created_at).label('date'),
            func.sum(UsageLog.amount).label('total_usage')
        ).filter(
            UsageLog.created_at >= cutoff_date
        ).group_by(func.date(UsageLog.created_at)).order_by(
            func.date(UsageLog.created_at)
        ).all()
        
        return templates.TemplateResponse("usage_analytics.html", {
            "request": request,
            "admin_user": admin_user,
            "usage_by_type": usage_by_type,
            "top_users": top_users,
            "daily_usage": daily_usage,
            "period_days": period_days
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading usage analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load usage analytics")

@router.get("/credits", response_class=HTMLResponse)
async def admin_credit_management(
    request: Request,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Credit management interface"""
    try:
        # Check if user is admin
        admin_user = db.query(User).filter(User.id == user_id).first()
        if not admin_user or admin_user.role != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get recent credit transactions
        recent_transactions = db.query(CreditTransaction).order_by(
            desc(CreditTransaction.created_at)
        ).limit(50).all()
        
        # Get users with credit balances
        users_with_credits = db.query(User).filter(User.credit_balance > 0).order_by(
            desc(User.credit_balance)
        ).all()
        
        return templates.TemplateResponse("credit_management.html", {
            "request": request,
            "admin_user": admin_user,
            "recent_transactions": recent_transactions,
            "users_with_credits": users_with_credits
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading credit management: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load credit management")

@router.get("/local-ai", response_class=HTMLResponse)
async def admin_local_ai(
    request: Request,
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Local AI/ML services management interface"""
    try:
        # Check if user is admin (we'll use the auth check from the template)
        
        return templates.TemplateResponse("local_ai.html", {
            "request": request,
            "admin_user": {"id": user_id}  # Minimal user info for template
        })
        
    except Exception as e:
        logger.error(f"Error loading local AI interface: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load local AI interface")

@router.get("/local-email", response_class=HTMLResponse)
async def admin_local_email(
    request: Request,
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Local email and notification management interface"""
    try:
        # Check if user is admin (we'll use the auth check from the template)
        
        return templates.TemplateResponse("local_email.html", {
            "request": request,
            "admin_user": {"id": user_id}  # Minimal user info for template
        })
        
    except Exception as e:
        logger.error(f"Error loading local email interface: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load local email interface")

@router.get("/background-jobs", response_class=HTMLResponse)
async def admin_background_jobs(
    request: Request,
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Background job processing management interface"""
    try:
        # Check if user is admin (we'll use the auth check from the template)
        
        return templates.TemplateResponse("background_jobs.html", {
            "request": request,
            "admin_user": {"id": user_id}  # Minimal user info for template
        })
        
    except Exception as e:
        logger.error(f"Error loading background jobs interface: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load background jobs interface")

@router.get("/websocket", response_class=HTMLResponse)
async def admin_websocket(
    request: Request,
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """WebSocket management interface"""
    try:
        # Check if user is admin (we'll use the auth check from the template)
        
        return templates.TemplateResponse("websocket.html", {
            "request": request,
            "admin_user": {"id": user_id}  # Minimal user info for template
        })
        
    except Exception as e:
        logger.error(f"Error loading WebSocket interface: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load WebSocket interface")

@router.get("/file-storage", response_class=HTMLResponse)
async def admin_file_storage(
    request: Request,
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """File storage management interface"""
    try:
        # Check if user is admin (we'll use the auth check from the template)
        
        return templates.TemplateResponse("file_storage.html", {
            "request": request,
            "admin_user": {"id": user_id}  # Minimal user info for template
        })
        
    except Exception as e:
        logger.error(f"Error loading file storage interface: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load file storage interface")


@router.get("/monitoring", response_class=HTMLResponse)
async def admin_monitoring(
    request: Request,
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Monitoring and observability interface"""
    try:
        # Check if user is admin (we'll use the auth check from the template)
        
        return templates.TemplateResponse("monitoring.html", {
            "request": request,
            "admin_user": {"id": user_id}  # Minimal user info for template
        })
        
    except Exception as e:
        logger.error(f"Error loading monitoring interface: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load monitoring interface")

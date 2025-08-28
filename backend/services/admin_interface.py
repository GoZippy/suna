"""
Simple web-based admin interface for user management.
Provides basic HTML interface for local user administration.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
from services.auth import AuthService, User, UserCreate, UserUpdate, UserRole, UserTier
from services.auth_middleware import require_admin, get_auth_service
from services.billing_local import BillingService, get_billing_service
from utils.logger import logger
import os

router = APIRouter(prefix="/admin", tags=["admin"])

# Setup templates directory
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "admin")
os.makedirs(templates_dir, exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin_user: User = Depends(require_admin)
):
    """
    Admin dashboard - main page for user management.
    """
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "admin_user": admin_user,
        "title": "Admin Dashboard"
    })

@router.get("/users", response_class=HTMLResponse)
async def admin_users_list(
    request: Request,
    page: int = 1,
    limit: int = 20,
    admin_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    List all users with pagination.
    """
    try:
        offset = (page - 1) * limit
        users = await auth_service.list_users(limit=limit, offset=offset)
        
        return templates.TemplateResponse("users_list.html", {
            "request": request,
            "admin_user": admin_user,
            "users": users,
            "page": page,
            "limit": limit,
            "has_next": len(users) == limit,
            "has_prev": page > 1,
            "title": "User Management"
        })
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Failed to load users")

@router.get("/users/create", response_class=HTMLResponse)
async def admin_create_user_form(
    request: Request,
    admin_user: User = Depends(require_admin)
):
    """
    Show create user form.
    """
    return templates.TemplateResponse("create_user.html", {
        "request": request,
        "admin_user": admin_user,
        "roles": [UserRole.USER, UserRole.MODERATOR, UserRole.ADMIN],
        "tiers": [UserTier.FREE, UserTier.PRO, UserTier.ENTERPRISE],
        "title": "Create User"
    })

@router.post("/users/create")
async def admin_create_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    tier: str = Form(...),
    admin_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Create a new user via form submission.
    """
    try:
        user_data = UserCreate(
            email=email,
            password=password,
            role=role,
            tier=tier
        )
        
        await auth_service.create_user(user_data)
        return RedirectResponse(url="/api/admin/users", status_code=303)
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return templates.TemplateResponse("create_user.html", {
            "request": request,
            "admin_user": admin_user,
            "roles": [UserRole.USER, UserRole.MODERATOR, UserRole.ADMIN],
            "tiers": [UserTier.FREE, UserTier.PRO, UserTier.ENTERPRISE],
            "error": str(e),
            "title": "Create User"
        })

@router.get("/users/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(
    request: Request,
    user_id: str,
    admin_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Show user details and edit form.
    """
    try:
        user = await auth_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return templates.TemplateResponse("user_detail.html", {
            "request": request,
            "admin_user": admin_user,
            "user": user,
            "roles": [UserRole.USER, UserRole.MODERATOR, UserRole.ADMIN],
            "tiers": [UserTier.FREE, UserTier.PRO, UserTier.ENTERPRISE],
            "title": f"User: {user.email}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail="Failed to load user")

@router.post("/users/{user_id}/update")
async def admin_update_user(
    request: Request,
    user_id: str,
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    tier: Optional[str] = Form(None),
    admin_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Update user via form submission.
    """
    try:
        # Prepare update data
        update_data = UserUpdate()
        
        if email and email.strip():
            update_data.email = email.strip()
        
        if password and password.strip():
            update_data.password = password.strip()
        
        if role and role.strip():
            update_data.role = role.strip()
        
        if tier and tier.strip():
            update_data.tier = tier.strip()
        
        await auth_service.update_user(user_id, update_data)
        return RedirectResponse(url=f"/api/admin/users/{user_id}", status_code=303)
        
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        user = await auth_service.get_user_by_id(user_id)
        return templates.TemplateResponse("user_detail.html", {
            "request": request,
            "admin_user": admin_user,
            "user": user,
            "roles": [UserRole.USER, UserRole.MODERATOR, UserRole.ADMIN],
            "tiers": [UserTier.FREE, UserTier.PRO, UserTier.ENTERPRISE],
            "error": str(e),
            "title": f"User: {user.email if user else 'Unknown'}"
        })

@router.post("/users/{user_id}/delete")
async def admin_delete_user(
    user_id: str,
    admin_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Delete user (soft delete).
    """
    try:
        # Prevent admin from deleting themselves
        if user_id == admin_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        success = await auth_service.delete_user(user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        return RedirectResponse(url="/api/admin/users", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")

@router.get("/billing", response_class=HTMLResponse)
async def admin_billing_dashboard(
    request: Request,
    period_days: int = 30,
    admin_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
    billing_service: BillingService = Depends(get_billing_service)
):
    """
    Admin billing dashboard with usage analytics and credit management.
    """
    try:
        from database.connection import get_db_session
        from database.models import UsageLog, User
        from sqlalchemy import func, desc
        from datetime import datetime, timezone, timedelta

        db = await get_db_session()

        # Get overall usage statistics
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Total usage by resource type
        usage_by_type = db.query(
            UsageLog.resource_type,
            func.sum(UsageLog.amount).label('total_amount'),
            func.sum(UsageLog.cost).label('total_cost')
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

        # Revenue statistics
        total_revenue = sum(float(log.total_cost) for log in usage_by_type) if usage_by_type else 0

        # Get all users for tier distribution
        users = await auth_service.list_users(limit=1000)
        tier_distribution = {}
        for user in users:
            tier_distribution[user.tier] = tier_distribution.get(user.tier, 0) + 1

        return templates.TemplateResponse("billing_dashboard.html", {
            "request": request,
            "admin_user": admin_user,
            "usage_by_type": usage_by_type,
            "top_users": top_users,
            "tier_distribution": tier_distribution,
            "total_revenue": total_revenue,
            "period_days": period_days,
            "title": f"Billing Dashboard ({period_days} days)"
        })

    except Exception as e:
        logger.error(f"Error getting billing stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to load billing statistics")

@router.get("/stats", response_class=HTMLResponse)
async def admin_stats(
    request: Request,
    admin_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Show system statistics.
    """
    try:
        # Get basic user statistics
        users = await auth_service.list_users(limit=1000)  # Get all users for stats

        stats = {
            "total_users": len(users),
            "active_users": len([u for u in users if u.is_active]),
            "users_by_role": {},
            "users_by_tier": {}
        }

        # Calculate role distribution
        for user in users:
            stats["users_by_role"][user.role] = stats["users_by_role"].get(user.role, 0) + 1
            stats["users_by_tier"][user.tier] = stats["users_by_tier"].get(user.tier, 0) + 1

        return templates.TemplateResponse("stats.html", {
            "request": request,
            "admin_user": admin_user,
            "stats": stats,
            "title": "System Statistics"
        })

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to load statistics")
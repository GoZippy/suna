"""
Local Billing Service for Self-Hosted Suna.
Replaces Stripe billing with local user management, usage tracking, and credit system.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Tuple, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
import os

from utils.cache import Cache
from utils.logger import logger
from utils.config import config, EnvMode
from services.supabase import DBConnection
from utils.auth_utils import get_current_user_id_from_jwt
from pydantic import BaseModel
from utils.constants import MODEL_ACCESS_TIERS, MODEL_NAME_ALIASES, HARDCODED_MODEL_PRICES
from litellm.cost_calculator import cost_per_token
from database.connection import get_db_session
from database.models import UsageLog, User, UserTier, CreditTransaction
from services.auth import User as AuthUser, AuthService, get_auth_service
from services.auth_middleware import require_admin
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
import time

# Token price multiplier for local credit calculation
TOKEN_PRICE_MULTIPLIER = 1.5

# Minimum credits required to allow a new request when over subscription limit
CREDIT_MIN_START_DOLLARS = 0.20

# Local credit packages (in dollars)
CREDIT_PACKAGES = {
    'credits_5': {'amount': 5, 'price': 5, 'description': '5 Credits'},
    'credits_10': {'amount': 10, 'price': 10, 'description': '10 Credits'},
    'credits_25': {'amount': 25, 'price': 25, 'description': '25 Credits'},
    'credits_50': {'amount': 50, 'price': 50, 'description': '50 Credits'},
    'credits_100': {'amount': 100, 'price': 100, 'description': '100 Credits'},
}

# Tier configurations with usage limits
TIER_CONFIGS = {
    'free': {
        'name': 'Free',
        'monthly_usage_limit': 60,  # minutes
        'max_concurrent_agents': 1,
        'max_projects': 3,
        'max_storage_gb': 1,
        'features': ['basic_agent_creation', 'web_search', 'file_upload']
    },
    'pro': {
        'name': 'Pro',
        'monthly_usage_limit': 300,  # minutes
        'max_concurrent_agents': 3,
        'max_projects': 10,
        'max_storage_gb': 10,
        'features': ['advanced_agent_creation', 'web_search', 'file_upload', 'api_access', 'priority_support']
    },
    'enterprise': {
        'name': 'Enterprise',
        'monthly_usage_limit': 1200,  # minutes
        'max_concurrent_agents': 10,
        'max_projects': 50,
        'max_storage_gb': 100,
        'features': ['all_features', 'custom_integrations', 'dedicated_support', 'sla_guarantee']
    }
}

router = APIRouter(prefix="/billing", tags=["billing"])

# Setup templates directory
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "billing")
os.makedirs(templates_dir, exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)

class BillingService:
    """Local billing service to replace Stripe functionality"""

    def __init__(self, db_connection):
        self.db = db_connection

    async def get_user_usage(self, user_id: str, period_days: int = 30) -> Dict:
        """Get user's usage statistics for the specified period"""
        try:
            db = await get_db_session()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)

            # Get usage logs for the period
            usage_logs = db.query(UsageLog).filter(
                and_(
                    UsageLog.user_id == user_id,
                    UsageLog.created_at >= cutoff_date
                )
            ).all()

            total_cost = sum(float(log.cost) for log in usage_logs)
            total_tokens = sum(int(log.amount) for log in usage_logs if log.unit == 'tokens')
            total_minutes = sum(float(log.amount) for log in usage_logs if log.unit == 'minutes')

            # Get user's tier info
            user = db.query(User).filter(User.id == user_id).first()
            tier_config = TIER_CONFIGS.get(user.tier, TIER_CONFIGS['free'])

            return {
                'total_cost': total_cost,
                'total_tokens': total_tokens,
                'total_minutes': total_minutes,
                'usage_logs': usage_logs,
                'tier_limit': tier_config['monthly_usage_limit'],
                'remaining_minutes': max(0, tier_config['monthly_usage_limit'] - total_minutes)
            }

        except Exception as e:
            logger.error(f"Error getting user usage: {e}")
            return {
                'total_cost': 0,
                'total_tokens': 0,
                'total_minutes': 0,
                'usage_logs': [],
                'tier_limit': 60,
                'remaining_minutes': 60
            }

    async def check_usage_limit(self, user_id: str, requested_minutes: float = 0) -> Tuple[bool, str]:
        """Check if user has exceeded their usage limit"""
        try:
            usage = await self.get_user_usage(user_id)

            if usage['total_minutes'] + requested_minutes > usage['tier_limit']:
                return False, f"Usage limit exceeded. You have {usage['remaining_minutes']:.1f} minutes remaining out of {usage['tier_limit']} minutes."

            return True, "Usage within limits"

        except Exception as e:
            logger.error(f"Error checking usage limit: {e}")
            return False, "Error checking usage limits"

    async def log_usage(self, user_id: str, resource_type: str, amount: float,
                       unit: str, cost: float = 0, project_id: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> bool:
        """Log usage for billing purposes"""
        try:
            db = await get_db_session()

            usage_log = UsageLog(
                user_id=user_id,
                project_id=project_id,
                resource_type=resource_type,
                amount=amount,
                unit=unit,
                cost=cost,
                metadata=metadata or {}
            )

            db.add(usage_log)
            db.commit()

            logger.info(f"Usage logged: user={user_id}, type={resource_type}, amount={amount}{unit}")
            return True

        except Exception as e:
            logger.error(f"Error logging usage: {e}")
            return False

    async def get_credit_balance(self, user_id: str) -> float:
        """Get user's credit balance from database"""
        try:
            db = await get_db_session()
            user = db.query(User).filter(User.id == user_id).first()
            return float(user.credit_balance) if user else 0.0
        except Exception as e:
            logger.error(f"Error getting credit balance: {e}")
            return 0.0

    async def add_credits(self, user_id: str, amount: float, transaction_type: str = 'purchase',
                         description: str = None, reference_id: str = None) -> bool:
        """Add credits to user's balance"""
        try:
            db = await get_db_session()

            # Get current balance
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            balance_before = float(user.credit_balance)
            balance_after = balance_before + amount

            # Update user balance
            user.credit_balance = balance_after
            db.commit()

            # Record transaction
            transaction = CreditTransaction(
                user_id=user_id,
                transaction_type=transaction_type,
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                description=description,
                reference_id=reference_id
            )
            db.add(transaction)
            db.commit()

            logger.info(f"Credits added: user={user_id}, amount={amount}, balance={balance_after}")
            return True

        except Exception as e:
            logger.error(f"Error adding credits: {e}")
            db.rollback()
            return False

    async def deduct_credits(self, user_id: str, amount: float, description: str = None,
                           reference_id: str = None) -> bool:
        """Deduct credits from user's balance"""
        try:
            db = await get_db_session()

            # Get current balance
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            balance_before = float(user.credit_balance)
            if balance_before < amount:
                return False

            balance_after = balance_before - amount

            # Update user balance
            user.credit_balance = balance_after
            db.commit()

            # Record transaction
            transaction = CreditTransaction(
                user_id=user_id,
                transaction_type='usage',
                amount=-amount,  # Negative amount for deduction
                balance_before=balance_before,
                balance_after=balance_after,
                description=description,
                reference_id=reference_id
            )
            db.add(transaction)
            db.commit()

            logger.info(f"Credits deducted: user={user_id}, amount={amount}, balance={balance_after}")
            return True

        except Exception as e:
            logger.error(f"Error deducting credits: {e}")
            db.rollback()
            return False

    def calculate_cost(self, model: str, input_tokens: int = 0, output_tokens: int = 0) -> float:
        """Calculate cost for model usage"""
        try:
            pricing = get_model_pricing(model)
            if not pricing:
                return 0

            input_cost_per_million, output_cost_per_million = pricing
            total_cost = (input_tokens * input_cost_per_million + output_tokens * output_cost_per_million) / 1_000_000
            return total_cost

        except Exception as e:
            logger.error(f"Error calculating cost: {e}")
            return 0

def get_model_pricing(model: str) -> tuple[float, float] | None:
    """Get pricing for a model. Returns (input_cost_per_million, output_cost_per_million) or None."""
    if model in HARDCODED_MODEL_PRICES:
        pricing = HARDCODED_MODEL_PRICES[model]
        return pricing["input_cost_per_million_tokens"], pricing["output_cost_per_million_tokens"]
    return None

# Dependency to get billing service
async def get_billing_service(db_connection=Depends(DBConnection)) -> BillingService:
    return BillingService(db_connection)

@router.get("/usage", response_model=Dict)
async def get_user_usage(
    user_id: str = Depends(get_current_user_id_from_jwt),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get user's current usage statistics"""
    return await billing_service.get_user_usage(user_id)

@router.get("/credits", response_model=float)
async def get_credit_balance(
    user_id: str = Depends(get_current_user_id_from_jwt),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get user's credit balance"""
    return await billing_service.get_credit_balance(user_id)

@router.post("/credits/purchase")
async def purchase_credits(
    package_id: str,
    user_id: str = Depends(get_current_user_id_from_jwt),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Purchase credits (would integrate with payment processor)"""
    if package_id not in CREDIT_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package ID")

    package = CREDIT_PACKAGES[package_id]

    # In a real implementation, this would integrate with a payment processor
    # For now, we'll simulate the purchase by adding credits directly
    success = await billing_service.add_credits(
        user_id=user_id,
        amount=package['amount'],
        transaction_type='purchase',
        description=f"Purchase of {package['description']}",
        reference_id=package_id
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to process credit purchase")

    logger.info(f"Credit purchase completed: user={user_id}, package={package_id}, amount={package['amount']}")

    return {"message": f"Successfully purchased {package['description']}", "credits_added": package['amount']}

@router.get("/packages", response_model=Dict)
async def get_credit_packages():
    """Get available credit packages"""
    return CREDIT_PACKAGES

@router.get("/tiers", response_model=Dict)
async def get_tier_configs():
    """Get available tier configurations"""
    return TIER_CONFIGS

@router.post("/usage/log")
async def log_usage(
    resource_type: str,
    amount: float,
    unit: str,
    cost: float = 0,
    project_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
    user_id: str = Depends(get_current_user_id_from_jwt),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Log usage (internal API)"""
    success = await billing_service.log_usage(
        user_id=user_id,
        resource_type=resource_type,
        amount=amount,
        unit=unit,
        cost=cost,
        project_id=project_id,
        metadata=metadata
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to log usage")

    return {"message": "Usage logged successfully"}

# Admin endpoints
@router.get("/admin/usage", response_class=HTMLResponse)
async def admin_usage_dashboard(
    request: Request,
    period_days: int = 30,
    admin_user: AuthUser = Depends(require_admin),
    billing_service: BillingService = Depends(get_billing_service),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Admin dashboard for usage analytics"""
    try:
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
            func.sum(UsageLog.amount).label('total_usage'),
            func.sum(UsageLog.cost).label('total_cost')
        ).join(UsageLog).filter(
            UsageLog.created_at >= cutoff_date
        ).group_by(User.id, User.email).order_by(
            desc(func.sum(UsageLog.cost))
        ).limit(10).all()

        return templates.TemplateResponse("usage_dashboard.html", {
            "request": request,
            "admin_user": admin_user,
            "usage_by_type": usage_by_type,
            "top_users": top_users,
            "period_days": period_days,
            "title": f"Usage Analytics ({period_days} days)"
        })

    except Exception as e:
        logger.error(f"Error loading usage dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to load usage dashboard")

@router.get("/admin/credits", response_class=HTMLResponse)
async def admin_credits_management(
    request: Request,
    admin_user: AuthUser = Depends(require_admin)
):
    """Admin interface for credit management"""
    return templates.TemplateResponse("credits_management.html", {
        "request": request,
        "admin_user": admin_user,
        "credit_packages": CREDIT_PACKAGES,
        "title": "Credit Management"
    })

@router.post("/admin/credits/grant")
async def admin_grant_credits(
    user_email: str = Form(...),
    amount: float = Form(...),
    reason: str = Form(...),
    admin_user: AuthUser = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Admin function to grant credits to a user"""
    try:
        # Find user by email
        db = await get_db_session()
        user = db.query(User).filter(User.email == user_email).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Grant credits using the billing service
        success = await billing_service.add_credits(
            user_id=str(user.id),
            amount=amount,
            transaction_type='grant',
            description=f"Admin grant: {reason}",
            reference_id=f"admin_{admin_user.id}"
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to grant credits")

        logger.info(f"Credits granted: admin={admin_user.id}, user={user.id}, amount={amount}, reason={reason}")

        return RedirectResponse(url="/api/billing/admin/credits", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting credits: {e}")
        raise HTTPException(status_code=500, detail="Failed to grant credits")

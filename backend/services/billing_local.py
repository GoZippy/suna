"""
Local Billing Service for Self-Hosted Suna.
Replaces Stripe billing with local user management, usage tracking, and credit system.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional, Dict, Tuple, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from utils.cache import Cache
from utils.logger import logger
from utils.config import config, EnvMode
from database.connection import get_db_session
from database.models import UsageLog, User, UserTier, CreditTransaction
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from utils.auth_utils import get_current_user_id_from_jwt
from pydantic import BaseModel
import time

router = APIRouter(prefix="/billing", tags=["billing"])

# Local user tier definitions (replacing Stripe price IDs)
LOCAL_TIERS = {
    'free': {
        'name': 'Free',
        'display_name': 'Free Tier',
        'max_monthly_usage': 60,  # 1 hour
        'max_concurrent_agents': 1,
        'max_projects': 3,
        'max_storage_gb': 1,
        'features': {
            'basic_models': True,
            'community_support': True,
            'basic_tools': True
        }
    },
    'pro': {
        'name': 'Pro',
        'display_name': 'Pro Tier',
        'max_monthly_usage': 120,  # 2 hours
        'max_concurrent_agents': 2,
        'max_projects': 10,
        'max_storage_gb': 10,
        'features': {
            'advanced_models': True,
            'priority_support': True,
            'all_tools': True,
            'custom_agents': True
        }
    },
    'business': {
        'name': 'Business',
        'display_name': 'Business Tier',
        'max_monthly_usage': 360,  # 6 hours
        'max_concurrent_agents': 5,
        'max_projects': 50,
        'max_storage_gb': 100,
        'features': {
            'enterprise_models': True,
            'dedicated_support': True,
            'all_tools': True,
            'custom_agents': True,
            'team_collaboration': True
        }
    },
    'enterprise': {
        'name': 'Enterprise',
        'display_name': 'Enterprise Tier',
        'max_monthly_usage': 720,  # 12 hours
        'max_concurrent_agents': 10,
        'max_projects': 100,
        'max_storage_gb': 500,
        'features': {
            'enterprise_models': True,
            'dedicated_support': True,
            'all_tools': True,
            'custom_agents': True,
            'team_collaboration': True,
            'custom_integrations': True,
            'sla_guarantee': True
        }
    }
}

# Credit packages for local purchase
CREDIT_PACKAGES = {
    'credits_5': {'amount': 5, 'price': 5, 'description': '5 Credits'},
    'credits_10': {'amount': 10, 'price': 10, 'description': '10 Credits'},
    'credits_25': {'amount': 25, 'price': 25, 'description': '25 Credits'},
    'credits_50': {'amount': 50, 'price': 50, 'description': '50 Credits'},
    'credits_100': {'amount': 100, 'price': 100, 'description': '100 Credits'},
}

# Pydantic models for API requests/responses
class UserTierResponse(BaseModel):
    tier: str
    display_name: str
    max_monthly_usage: float
    max_concurrent_agents: int
    max_projects: int
    max_storage_gb: int
    features: Dict[str, bool]

class UsageSummaryResponse(BaseModel):
    current_month_usage: float
    monthly_limit: float
    usage_percentage: float
    credit_balance: float
    tier: str

class CreditPurchaseRequest(BaseModel):
    package_id: str
    amount: float

class CreditTransactionResponse(BaseModel):
    id: UUID
    transaction_type: str
    amount: float
    balance_before: float
    balance_after: float
    description: Optional[str]
    created_at: datetime

class TierChangeRequest(BaseModel):
    new_tier: str

@router.get("/user/tier", response_model=UserTierResponse)
async def get_user_tier(
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db_session)
):
    """Get the current user's tier information"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        tier_info = LOCAL_TIERS.get(user.tier, LOCAL_TIERS['free'])
        
        return UserTierResponse(
            tier=user.tier,
            display_name=tier_info['display_name'],
            max_monthly_usage=tier_info['max_monthly_usage'],
            max_concurrent_agents=tier_info['max_concurrent_agents'],
            max_projects=tier_info['max_projects'],
            max_storage_gb=tier_info['max_storage_gb'],
            features=tier_info['features']
        )
    except Exception as e:
        logger.error(f"Error getting user tier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/user/usage", response_model=UsageSummaryResponse)
async def get_user_usage_summary(
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db_session)
):
    """Get the current user's usage summary for the current month"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get current month usage
        current_month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_usage = db.query(func.sum(UsageLog.amount)).filter(
            UsageLog.user_id == user_id,
            UsageLog.resource_type == 'agent_runtime',
            UsageLog.created_at >= current_month_start
        ).scalar() or 0.0
        
        tier_info = LOCAL_TIERS.get(user.tier, LOCAL_TIERS['free'])
        monthly_limit = tier_info['max_monthly_usage']
        usage_percentage = (monthly_usage / monthly_limit * 100) if monthly_limit > 0 else 0
        
        return UsageSummaryResponse(
            current_month_usage=float(monthly_usage),
            monthly_limit=monthly_limit,
            usage_percentage=float(usage_percentage),
            credit_balance=float(user.credit_balance),
            tier=user.tier
        )
    except Exception as e:
        logger.error(f"Error getting user usage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/user/tier/change")
async def change_user_tier(
    request: TierChangeRequest,
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db_session)
):
    """Change the user's tier (admin only for now)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if new tier exists
        if request.new_tier not in LOCAL_TIERS:
            raise HTTPException(status_code=400, detail="Invalid tier")
        
        # For now, only allow admins to change tiers
        if user.role != 'admin':
            raise HTTPException(status_code=403, detail="Only admins can change tiers")
        
        old_tier = user.tier
        user.tier = request.new_tier
        db.commit()
        
        logger.info(f"User {user_id} tier changed from {old_tier} to {request.new_tier}")
        
        return {"message": f"Tier changed from {old_tier} to {request.new_tier}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing user tier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/credits/packages")
async def get_credit_packages():
    """Get available credit packages"""
    return {"packages": CREDIT_PACKAGES}

@router.post("/credits/purchase")
async def purchase_credits(
    request: CreditPurchaseRequest,
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db_session)
):
    """Purchase credits (simulated - no actual payment processing)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate package
        if request.package_id not in CREDIT_PACKAGES:
            raise HTTPException(status_code=400, detail="Invalid credit package")
        
        package = CREDIT_PACKAGES[request.package_id]
        
        # Create credit transaction
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type='purchase',
            amount=package['amount'],
            balance_before=user.credit_balance,
            balance_after=user.credit_balance + package['amount'],
            description=f"Purchased {package['description']}",
            metadata={'package_id': request.package_id}
        )
        
        # Update user credit balance
        user.credit_balance += package['amount']
        
        db.add(transaction)
        db.commit()
        
        logger.info(f"User {user_id} purchased {package['amount']} credits")
        
        return {
            "message": f"Successfully purchased {package['amount']} credits",
            "new_balance": float(user.credit_balance),
            "transaction_id": str(transaction.id)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error purchasing credits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/credits/transactions", response_model=List[CreditTransactionResponse])
async def get_credit_transactions(
    user_id: UUID = Depends(get_current_user_id_from_jwt),
    db: Session = Depends(get_db_session),
    limit: int = 50,
    offset: int = 0
):
    """Get user's credit transaction history"""
    try:
        transactions = db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id
        ).order_by(
            desc(CreditTransaction.created_at)
        ).offset(offset).limit(limit).all()
        
        return [
            CreditTransactionResponse(
                id=t.id,
                transaction_type=t.transaction_type,
                amount=float(t.amount),
                balance_before=float(t.balance_before),
                balance_after=float(t.balance_after),
                description=t.description,
                created_at=t.created_at
            )
            for t in transactions
        ]
    except Exception as e:
        logger.error(f"Error getting credit transactions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/admin/users")
async def get_all_users(
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Get all users (admin only)"""
    try:
        # Check if user is admin
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.role != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        
        users = db.query(User).all()
        
        return {
            "users": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "tier": u.tier,
                    "role": u.role,
                    "credit_balance": float(u.credit_balance),
                    "created_at": u.created_at,
                    "last_login_at": u.last_login_at
                }
                for u in users
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin/users/{target_user_id}/tier")
async def admin_change_user_tier(
    target_user_id: UUID,
    request: TierChangeRequest,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Admin endpoint to change any user's tier"""
    try:
        # Check if current user is admin
        admin_user = db.query(User).filter(User.id == user_id).first()
        if not admin_user or admin_user.role != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get target user
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")
        
        # Check if new tier exists
        if request.new_tier not in LOCAL_TIERS:
            raise HTTPException(status_code=400, detail="Invalid tier")
        
        old_tier = target_user.tier
        target_user.tier = request.new_tier
        db.commit()
        
        logger.info(f"Admin {user_id} changed user {target_user_id} tier from {old_tier} to {request.new_tier}")
        
        return {"message": f"User tier changed from {old_tier} to {request.new_tier}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing user tier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin/users/{target_user_id}/credits")
async def admin_add_user_credits(
    target_user_id: UUID,
    request: CreditPurchaseRequest,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id_from_jwt)
):
    """Admin endpoint to add credits to any user"""
    try:
        # Check if current user is admin
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
            amount=request.amount,
            balance_before=target_user.credit_balance,
            balance_after=target_user.credit_balance + request.amount,
            description=f"Credits granted by admin",
            metadata={'granted_by': str(user_id)}
        )
        
        # Update user credit balance
        target_user.credit_balance += request.amount
        
        db.add(transaction)
        db.commit()
        
        logger.info(f"Admin {user_id} granted {request.amount} credits to user {target_user_id}")
        
        return {
            "message": f"Successfully granted {request.amount} credits",
            "new_balance": float(target_user.credit_balance),
            "transaction_id": str(transaction.id)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting credits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Usage tracking functions
async def log_usage(
    db: Session,
    user_id: UUID,
    resource_type: str,
    amount: float,
    unit: str = 'minutes',
    cost: float = 0.0,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    project_id: Optional[UUID] = None,
    metadata: Optional[Dict] = None
):
    """Log usage for a user"""
    try:
        usage_log = UsageLog(
            user_id=user_id,
            project_id=project_id,
            resource_type=resource_type,
            amount=amount,
            unit=unit,
            cost=cost,
            provider=provider,
            model=model,
            metadata=metadata or {}
        )
        
        db.add(usage_log)
        db.commit()
        
        logger.debug(f"Logged usage for user {user_id}: {amount} {unit} of {resource_type}")
        
    except Exception as e:
        logger.error(f"Error logging usage: {e}", exc_info=True)
        db.rollback()

async def check_usage_limits(
    db: Session,
    user_id: UUID,
    resource_type: str = 'agent_runtime'
) -> Tuple[bool, str]:
    """Check if user has exceeded their usage limits"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"
        
        tier_info = LOCAL_TIERS.get(user.tier, LOCAL_TIERS['free'])
        monthly_limit = tier_info['max_monthly_usage']
        
        # Get current month usage
        current_month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_usage = db.query(func.sum(UsageLog.amount)).filter(
            UsageLog.user_id == user_id,
            UsageLog.resource_type == resource_type,
            UsageLog.created_at >= current_month_start
        ).scalar() or 0.0
        
        if monthly_usage >= monthly_limit:
            return False, f"Monthly usage limit of {monthly_limit} minutes exceeded"
        
        return True, "Usage within limits"
        
    except Exception as e:
        logger.error(f"Error checking usage limits: {e}", exc_info=True)
        return False, "Error checking usage limits"

async def deduct_credits(
    db: Session,
    user_id: UUID,
    amount: float,
    description: str,
    reference_id: Optional[str] = None
) -> bool:
    """Deduct credits from user's balance"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        if user.credit_balance < amount:
            return False
        
        # Create credit transaction
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type='usage',
            amount=-amount,
            balance_before=user.credit_balance,
            balance_after=user.credit_balance - amount,
            description=description,
            reference_id=reference_id
        )
        
        # Update user credit balance
        user.credit_balance -= amount
        
        db.add(transaction)
        db.commit()
        
        logger.debug(f"Deducted {amount} credits from user {user_id}: {description}")
        return True
        
    except Exception as e:
        logger.error(f"Error deducting credits: {e}", exc_info=True)
        db.rollback()
        return False

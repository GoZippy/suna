"""
Zippy self-hosted billing façade.

Exposes the same function names as legacy Kortix `services.billing` so agent,
thread, and trigger code import paths stay stable. No Stripe: cloud billing is
disabled unless STRIPE_SECRET_KEY is set (unsupported in this fork).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from utils.logger import logger
from utils.config import config, EnvMode
from utils.constants import HARDCODED_MODEL_PRICES, MODEL_NAME_ALIASES

try:
    from litellm.cost_calculator import cost_per_token
except ImportError:
    cost_per_token = None


def _billing_bypass() -> bool:
    """Use local/self-hosted behaviour (no Stripe subscription checks)."""
    if config.ENV_MODE == EnvMode.LOCAL:
        return True
    key = getattr(config, "STRIPE_SECRET_KEY", None) or ""
    if not str(key).strip():
        return True
    return False


def get_model_pricing(model: str) -> Optional[Tuple[float, float]]:
    if model in HARDCODED_MODEL_PRICES:
        pricing = HARDCODED_MODEL_PRICES[model]
        return pricing["input_cost_per_million_tokens"], pricing["output_cost_per_million_tokens"]
    return None


def calculate_token_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    try:
        prompt_tokens = int(prompt_tokens) if prompt_tokens is not None else 0
        completion_tokens = int(completion_tokens) if completion_tokens is not None else 0
        resolved_model = MODEL_NAME_ALIASES.get(model, model)
        hardcoded_pricing = get_model_pricing(model) or get_model_pricing(resolved_model)
        if hardcoded_pricing:
            inp_m, out_m = hardcoded_pricing
            return (prompt_tokens / 1_000_000) * inp_m + (completion_tokens / 1_000_000) * out_m
        if cost_per_token:
            for m in [model, resolved_model]:
                try:
                    p = cost_per_token(m, prompt_tokens, completion_tokens)
                    if p is not None:
                        return float(p)
                except Exception:
                    continue
        return 0.0
    except Exception as e:
        logger.error(f"calculate_token_cost failed: {e}", exc_info=True)
        return 0.0


def _local_subscription_stub() -> Dict[str, Any]:
    return {
        "price_id": "zippy_selfhosted",
        "plan_name": "Self-hosted",
        "minutes_limit": "no limit",
    }


def _allowed_models_list() -> List[str]:
    try:
        free = list((MODEL_NAME_ALIASES or {}).keys())
        return free[:200] if free else ["*"]
    except Exception:
        return ["*"]


async def can_use_model(client, user_id: str, model_name: str):
    if _billing_bypass():
        return True, "Self-hosted billing: model access not gated by Stripe", _allowed_models_list()
    logger.warning("Stripe-backed can_use_model is not supported in Zippy; denying")
    return False, "Stripe billing is disabled in this build", []


async def check_billing_status(client, user_id: str) -> Tuple[bool, str, Optional[Dict]]:
    if _billing_bypass():
        return True, "Self-hosted billing: run limits use local tier/credits", _local_subscription_stub()
    logger.warning("Stripe-backed check_billing_status is not supported in Zippy; denying")
    return False, "Stripe billing is disabled in this build", None


async def get_subscription_tier(client, user_id: str) -> str:
    try:
        res = (
            await client.table("users")
            .select("tier")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        rows = getattr(res, "data", None) or []
        if rows and rows[0].get("tier"):
            return str(rows[0]["tier"])
    except Exception as e:
        logger.debug(f"get_subscription_tier fallback for {user_id}: {e}")
    return "free"


async def handle_usage_with_credits(
    client,
    user_id: str,
    token_cost: float,
    thread_id: str = None,
    message_id: str = None,
    model: str = None,
) -> Tuple[bool, str]:
    if _billing_bypass():
        return True, "Self-hosted: token usage not billed via Stripe"
    logger.warning("Stripe-backed handle_usage_with_credits is not supported in Zippy")
    return False, "Stripe billing is disabled in this build"

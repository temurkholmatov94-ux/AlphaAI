from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ModelPricing


class PricingUnavailable(Exception):
    """Raised when there is no current, verified price for a provider model."""


def _ceil_div(numerator: int, denominator: int) -> int:
    return (numerator + denominator - 1) // denominator


def estimate_max_cost_microusd(
    db: Session,
    *,
    provider: str,
    model_id: str,
    estimated_input_tokens: int,
    max_output_tokens: int,
    safety_margin_bps: int = 1500,
) -> int:
    """Return a conservative USD-micro estimate using verified, versioned pricing.

    Rates are stored in micro-USD per one million tokens. Token estimates must
    come from a trusted server-side tokenizer and max output is bounded by API
    validation. Missing/stale prices fail closed; never infer prices from names.
    """
    if not 0 <= estimated_input_tokens <= 10_000_000:
        raise ValueError("Estimated input token count is outside permitted limits")
    if not 1 <= max_output_tokens <= 1_000_000:
        raise ValueError("Maximum output token count is outside permitted limits")
    if not 0 <= safety_margin_bps <= 10_000:
        raise ValueError("Safety margin must be between 0 and 100 percent")

    now = datetime.now(timezone.utc)
    price = db.scalar(
        select(ModelPricing)
        .where(
            ModelPricing.provider == provider,
            ModelPricing.model_id == model_id,
            ModelPricing.active.is_(True),
        )
        .order_by(ModelPricing.effective_from.desc(), ModelPricing.id.desc())
        .limit(1)
    )

    if price is not None:
        verified_at = price.verified_at
        effective_from = price.effective_from
        effective_until = price.effective_until
        if verified_at.tzinfo is None:
            verified_at = verified_at.replace(tzinfo=timezone.utc)
        if effective_from.tzinfo is None:
            effective_from = effective_from.replace(tzinfo=timezone.utc)
        if effective_until is not None and effective_until.tzinfo is None:
            effective_until = effective_until.replace(tzinfo=timezone.utc)
        is_current = (
            verified_at <= now
            and verified_at >= now - timedelta(days=30)
            and effective_from <= now
            and (effective_until is None or effective_until > now)
        )
        if not is_current:
            price = None

    if price is None:
        raise PricingUnavailable("No current verified price is configured for this model")
    if price.input_microusd_per_million_tokens < 0 or price.output_microusd_per_million_tokens < 0:
        raise PricingUnavailable("Configured model pricing is invalid")

    input_cost = _ceil_div(
        estimated_input_tokens * price.input_microusd_per_million_tokens,
        1_000_000,
    )
    output_cost = _ceil_div(
        max_output_tokens * price.output_microusd_per_million_tokens,
        1_000_000,
    )
    subtotal = input_cost + output_cost
    return _ceil_div(subtotal * (10_000 + safety_margin_bps), 10_000)

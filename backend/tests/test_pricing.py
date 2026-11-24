from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models import ModelPricing
from app.pricing import PricingUnavailable, estimate_max_cost_microusd


def open_test_db():
    generator = app.dependency_overrides[get_db]()
    return generator, next(generator)


def test_cost_estimate_uses_verified_price_and_safety_margin(client):
    generator, db = open_test_db()
    try:
        now = datetime.now(timezone.utc)
        db.add(
            ModelPricing(
                provider="openai",
                model_id="gpt-test",
                input_microusd_per_million_tokens=1_000_000,
                output_microusd_per_million_tokens=2_000_000,
                source_url="https://provider.example/pricing",
                verified_at=now,
                effective_from=now - timedelta(minutes=1),
                active=True,
            )
        )
        db.commit()
        estimate = estimate_max_cost_microusd(
            db,
            provider="openai",
            model_id="gpt-test",
            estimated_input_tokens=1000,
            max_output_tokens=1000,
        )
        assert estimate == 3450
    finally:
        db.close()
        generator.close()


def test_missing_or_stale_pricing_fails_closed(client):
    generator, db = open_test_db()
    try:
        with pytest.raises(PricingUnavailable):
            estimate_max_cost_microusd(
                db,
                provider="anthropic",
                model_id="unpriced-model",
                estimated_input_tokens=100,
                max_output_tokens=100,
            )

        now = datetime.now(timezone.utc)
        db.add(
            ModelPricing(
                provider="anthropic",
                model_id="expired-model",
                input_microusd_per_million_tokens=100,
                output_microusd_per_million_tokens=200,
                source_url="https://provider.example/pricing",
                verified_at=now - timedelta(days=10),
                effective_from=now - timedelta(days=9),
                effective_until=now - timedelta(days=1),
                active=True,
            )
        )
        db.commit()
        with pytest.raises(PricingUnavailable):
            estimate_max_cost_microusd(
                db,
                provider="anthropic",
                model_id="expired-model",
                estimated_input_tokens=100,
                max_output_tokens=100,
            )
    finally:
        db.close()
        generator.close()


@pytest.mark.parametrize(
    "input_tokens,output_tokens",
    [(-1, 10), (10, 0), (10_000_001, 10), (10, 1_000_001)],
)
def test_pricing_estimator_rejects_unbounded_token_estimates(client, input_tokens, output_tokens):
    generator, db = open_test_db()
    try:
        with pytest.raises(ValueError):
            estimate_max_cost_microusd(
                db,
                provider="openai",
                model_id="gpt-test",
                estimated_input_tokens=input_tokens,
                max_output_tokens=output_tokens,
            )
    finally:
        db.close()
        generator.close()

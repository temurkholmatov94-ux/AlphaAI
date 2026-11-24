from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models import OrganizationMembership, UsageAccount, UsageEvent
from app.usage import (
    UsageBudgetExceeded,
    UsageIdempotencyConflict,
    UsageStateConflict,
    reserve_usage,
    release_usage,
    settle_usage,
)


def open_test_db():
    generator = app.dependency_overrides[get_db]()
    return generator, next(generator)


def verified_workspace(client):
    registered = client.post(
        "/v1/auth/register",
        json={"email": "budget-owner@example.com", "password": "LongPassphrase123!secure"},
    )
    assert registered.status_code == 201
    verified = client.post(
        "/v1/auth/verify-email",
        json={"token": registered.json()["development_verification_token"]},
    )
    assert verified.status_code == 200

    generator, db = open_test_db()
    try:
        membership = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == registered.json()["user_id"]
            )
        )
        account = db.scalar(
            select(UsageAccount).where(UsageAccount.organization_id == membership.organization_id)
        )
        account.enabled = True
        account.budget_limit_microusd = 1_000_000
        db.commit()
        return account.organization_id
    finally:
        db.close()
        generator.close()


def test_budget_reservation_settlement_and_idempotency(client):
    organization_id = verified_workspace(client)
    generator, db = open_test_db()
    try:
        reservation = reserve_usage(
            db,
            organization_id=organization_id,
            idempotency_key="request-000001",
            estimated_microusd=700_000,
            provider="openai",
            model_id="alpha-fast",
        )
        account = db.scalar(
            select(UsageAccount).where(UsageAccount.organization_id == organization_id)
        )
        assert account.reserved_microusd == 700_000
        assert account.spent_microusd == 0

        duplicate = reserve_usage(
            db,
            organization_id=organization_id,
            idempotency_key="request-000001",
            estimated_microusd=700_000,
            provider="openai",
            model_id="alpha-fast",
        )
        assert duplicate.id == reservation.id
        assert account.reserved_microusd == 700_000

        try:
            reserve_usage(
                db,
                organization_id=organization_id,
                idempotency_key="request-000002",
                estimated_microusd=400_000,
                provider="openai",
                model_id="alpha-fast",
            )
            assert False, "Expected budget admission to reject over-budget request"
        except UsageBudgetExceeded:
            pass

        event = settle_usage(
            db,
            reservation_id=reservation.id,
            actual_microusd=650_000,
            input_tokens=100,
            output_tokens=50,
        )
        assert event.cost_microusd == 650_000
        assert db.scalar(select(UsageAccount).where(UsageAccount.organization_id == organization_id)).reserved_microusd == 0
        assert db.scalar(select(UsageAccount).where(UsageAccount.organization_id == organization_id)).spent_microusd == 650_000

        same_event = settle_usage(
            db,
            reservation_id=reservation.id,
            actual_microusd=650_000,
            input_tokens=100,
            output_tokens=50,
        )
        assert same_event.id == event.id
        assert db.scalar(select(UsageEvent).where(UsageEvent.reservation_id == reservation.id)) is not None

        try:
            reserve_usage(
                db,
                organization_id=organization_id,
                idempotency_key="request-000001",
                estimated_microusd=600_000,
                provider="openai",
                model_id="alpha-fast",
            )
            assert False, "Expected idempotency mismatch to fail"
        except UsageIdempotencyConflict:
            pass
    finally:
        db.close()
        generator.close()


def test_release_is_idempotent_and_does_not_add_spend(client):
    organization_id = verified_workspace(client)
    generator, db = open_test_db()
    try:
        reservation = reserve_usage(
            db,
            organization_id=organization_id,
            idempotency_key="request-000003",
            estimated_microusd=250_000,
            provider="anthropic",
            model_id="alpha-reasoning",
        )
        release_usage(db, reservation_id=reservation.id)
        release_usage(db, reservation_id=reservation.id)
        account = db.scalar(
            select(UsageAccount).where(UsageAccount.organization_id == organization_id)
        )
        assert account.reserved_microusd == 0
        assert account.spent_microusd == 0
        assert reservation.status == "released"
        try:
            settle_usage(
                db,
                reservation_id=reservation.id,
                actual_microusd=10,
                input_tokens=1,
                output_tokens=1,
            )
            assert False, "Released reservation must not be settled"
        except UsageStateConflict:
            pass
    finally:
        db.close()
        generator.close()


def test_new_workspace_budget_is_disabled_by_default(client):
    registered = client.post(
        "/v1/auth/register",
        json={"email": "closed-budget@example.com", "password": "LongPassphrase123!secure"},
    )
    assert registered.status_code == 201
    client.post(
        "/v1/auth/verify-email",
        json={"token": registered.json()["development_verification_token"]},
    )
    generator, db = open_test_db()
    try:
        membership = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == registered.json()["user_id"]
            )
        )
        account = db.scalar(
            select(UsageAccount).where(UsageAccount.organization_id == membership.organization_id)
        )
        assert account.enabled is False
        assert account.budget_limit_microusd == 0
    finally:
        db.close()
        generator.close()

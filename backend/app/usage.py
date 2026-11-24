from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import UsageAccount, UsageEvent, UsageReservation


class UsageLimitError(Exception):
    """Base exception for fail-closed usage admission."""


class UsageAccountNotConfigured(UsageLimitError):
    pass


class UsageBudgetExceeded(UsageLimitError):
    pass


class UsageIdempotencyConflict(UsageLimitError):
    pass


class UsageStateConflict(UsageLimitError):
    pass


def reserve_usage(
    db: Session,
    *,
    organization_id: int,
    idempotency_key: str,
    estimated_microusd: int,
    provider: str,
    model_id: str,
) -> UsageReservation:
    """Atomically reserve estimated spend before a paid provider request.

    The caller supplies an estimate produced by trusted server-side pricing logic,
    never a client-provided amount. The transaction commits the reservation and
    account balance together. Missing/disabled budgets fail closed.
    """
    key = idempotency_key.strip()
    if not 8 <= len(key) <= 128:
        raise ValueError("Idempotency key must contain between 8 and 128 characters")
    if not 1 <= estimated_microusd <= 10**12:
        raise ValueError("Estimated spend is outside the permitted range")

    account = db.scalar(
        select(UsageAccount).where(UsageAccount.organization_id == organization_id)
    )
    if account is None:
        raise UsageAccountNotConfigured("Organization has no usage account")

    existing = db.scalar(
        select(UsageReservation).where(
            UsageReservation.usage_account_id == account.id,
            UsageReservation.idempotency_key == key,
        )
    )
    if existing is not None:
        if existing.estimated_microusd != estimated_microusd:
            raise UsageIdempotencyConflict("Idempotency key was already used with a different estimate")
        if existing.status not in {"reserved", "settled"}:
            raise UsageStateConflict("Idempotency key belongs to a completed reservation")
        return existing

    statement = (
        update(UsageAccount)
        .where(
            UsageAccount.id == account.id,
            UsageAccount.enabled.is_(True),
            UsageAccount.budget_limit_microusd
            >= UsageAccount.spent_microusd + UsageAccount.reserved_microusd + estimated_microusd,
        )
        .values(reserved_microusd=UsageAccount.reserved_microusd + estimated_microusd)
        .returning(UsageAccount.id)
    )
    reserved_account_id = db.scalar(statement)
    if reserved_account_id is None:
        db.rollback()
        account = db.scalar(
            select(UsageAccount).where(UsageAccount.organization_id == organization_id)
        )
        if account is None or not account.enabled or account.budget_limit_microusd <= 0:
            raise UsageAccountNotConfigured("Usage budget is not enabled")
        raise UsageBudgetExceeded("Organization usage budget is exhausted")

    reservation = UsageReservation(
        usage_account_id=account.id,
        idempotency_key=key,
        estimated_microusd=estimated_microusd,
        status="reserved",
        provider=provider,
        model_id=model_id,
    )
    db.add(reservation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(UsageReservation).where(
                UsageReservation.usage_account_id == account.id,
                UsageReservation.idempotency_key == key,
            )
        )
        if existing is not None and existing.estimated_microusd == estimated_microusd and existing.status in {"reserved", "settled"}:
            return existing
        raise UsageIdempotencyConflict("Concurrent request reused an idempotency key")
    db.refresh(reservation)
    return reservation


def settle_usage(
    db: Session,
    *,
    reservation_id: int,
    actual_microusd: int,
    input_tokens: int,
    output_tokens: int,
    metadata: dict | None = None,
) -> UsageEvent:
    """Settle a reservation once and write the immutable usage event.

    Actual cost may exceed the estimate if a provider's final usage differs; the
    overage is recorded, and subsequent reservations will be blocked by the budget.
    """
    if not 0 <= actual_microusd <= 10**12:
        raise ValueError("Actual spend is outside the permitted range")
    if not 0 <= input_tokens <= 10**12 or not 0 <= output_tokens <= 10**12:
        raise ValueError("Token counts are outside the permitted range")

    reservation = db.scalar(
        select(UsageReservation).where(UsageReservation.id == reservation_id).with_for_update()
    )
    if reservation is None:
        raise UsageStateConflict("Usage reservation does not exist")

    existing_event = db.scalar(
        select(UsageEvent).where(UsageEvent.reservation_id == reservation_id)
    )
    if reservation.status == "settled" and existing_event is not None:
        if reservation.actual_microusd != actual_microusd:
            raise UsageIdempotencyConflict("Reservation was already settled with a different cost")
        return existing_event
    if reservation.status != "reserved":
        raise UsageStateConflict("Only active reservations can be settled")

    account = db.scalar(
        select(UsageAccount).where(UsageAccount.id == reservation.usage_account_id).with_for_update()
    )
    if account is None or account.reserved_microusd < reservation.estimated_microusd:
        raise UsageStateConflict("Usage reservation/account balance invariant failed")

    account.reserved_microusd -= reservation.estimated_microusd
    account.spent_microusd += actual_microusd
    reservation.actual_microusd = actual_microusd
    reservation.status = "settled"
    reservation.completed_at = datetime.now(timezone.utc)

    event = UsageEvent(
        usage_account_id=account.id,
        reservation_id=reservation.id,
        provider=reservation.provider,
        model_id=reservation.model_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_microusd=actual_microusd,
        metadata_json=metadata or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def release_usage(db: Session, *, reservation_id: int) -> None:
    """Release reserved capacity when a provider request definitively did not run."""
    reservation = db.scalar(
        select(UsageReservation).where(UsageReservation.id == reservation_id).with_for_update()
    )
    if reservation is None:
        raise UsageStateConflict("Usage reservation does not exist")
    if reservation.status == "released":
        return
    if reservation.status != "reserved":
        raise UsageStateConflict("Only active reservations can be released")

    account = db.scalar(
        select(UsageAccount).where(UsageAccount.id == reservation.usage_account_id).with_for_update()
    )
    if account is None or account.reserved_microusd < reservation.estimated_microusd:
        raise UsageStateConflict("Usage reservation/account balance invariant failed")

    account.reserved_microusd -= reservation.estimated_microusd
    reservation.status = "released"
    reservation.completed_at = datetime.now(timezone.utc)
    db.commit()

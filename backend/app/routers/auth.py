import hmac
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AuditEvent, EmailVerification, Organization, OrganizationMembership, UsageAccount, User
from app.schemas import (
    EmailVerificationRequest,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserRead,
)
from app.security import (
    create_access_token,
    digest_secret,
    generate_verification_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/v1/auth", tags=["identity"])

class AdminBootstrapRequest(RegisterRequest):
    bootstrap_token: str = Field(min_length=32, max_length=256)


@router.post("/bootstrap-admin", status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: AdminBootstrapRequest, db: Session = Depends(get_db)):
    """One-time HTTPS bootstrap; disabled unless a temporary server token is configured."""
    configured_token = get_settings().alphaai_bootstrap_token
    if not configured_token or not hmac.compare_digest(payload.bootstrap_token, configured_token):
        raise HTTPException(status_code=404, detail="Not found")

    allowed = {
        address.strip().lower()
        for address in get_settings().alphaai_admin_emails
        if address.strip()
    }
    email = str(payload.email).strip().lower()
    if not allowed or email not in allowed:
        raise HTTPException(status_code=403, detail="This email is not configured as a platform administrator")

    existing_admin = db.scalar(select(User.id).where(User.email.in_(allowed)).limit(1))
    if existing_admin is not None:
        raise HTTPException(status_code=409, detail="Administrator bootstrap is already complete")

    user = User(email=email, password_hash=hash_password(payload.password), is_active=True, email_verified=True)
    db.add(user)
    db.flush()
    organization = Organization(
        name=f"{email.split('@', 1)[0]}'s workspace",
        slug=f"workspace-{uuid4().hex[:12]}",
        created_by_user_id=user.id,
    )
    db.add(organization)
    db.flush()
    db.add(OrganizationMembership(user_id=user.id, organization_id=organization.id, role="owner"))
    db.add(UsageAccount(organization_id=organization.id, budget_limit_microusd=0, enabled=False))
    db.add(AuditEvent(
        actor_user_id=user.id,
        action="identity.admin_bootstrapped",
        resource_type="user",
        resource_id=str(user.id),
        details={"organization_id": organization.id, "email_verified": True},
    ))
    db.commit()
    return {"status": "created", "email": email, "message": "Administrator account created. Remove ALPHAAI_BOOTSTRAP_TOKEN from Render now."}



@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    email = str(payload.email).strip().lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()

    organization = Organization(
        name=f"{email.split('@', 1)[0]}'s workspace",
        slug=f"workspace-{uuid4().hex[:12]}",
        created_by_user_id=user.id,
    )
    db.add(organization)
    db.flush()
    db.add(OrganizationMembership(user_id=user.id, organization_id=organization.id, role="owner"))
    # New workspaces start with inference spending disabled and a zero budget.
    db.add(UsageAccount(organization_id=organization.id, budget_limit_microusd=0, enabled=False))

    raw_token = generate_verification_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    db.add(
        EmailVerification(
            user_id=user.id,
            token_hash=digest_secret(raw_token),
            expires_at=expires_at,
        )
    )
    db.add(
        AuditEvent(
            actor_user_id=user.id,
            action="identity.registered",
            resource_type="user",
            resource_id=str(user.id),
            details={"organization_id": organization.id},
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    # Email delivery is not configured yet. This token is only exposed in explicit
    # local development/test environments and is never returned in production.
    environment = get_settings().app_env
    development_token = raw_token if environment in {"development", "test"} else None
    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        status="pending_email_verification",
        verification_required=True,
        development_verification_token=development_token,
    )


@router.post("/verify-email", response_model=UserRead)
def verify_email(payload: EmailVerificationRequest, db: Session = Depends(get_db)) -> UserRead:
    try:
        token_hash = digest_secret(payload.token)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Email verification is not configured")

    verification = db.scalar(
        select(EmailVerification).where(EmailVerification.token_hash == token_hash)
    )
    now = datetime.now(timezone.utc)
    if verification is None or verification.used_at is not None:
        raise HTTPException(status_code=400, detail="Verification token is invalid or already used")

    expires_at = verification.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(status_code=400, detail="Verification token has expired")

    user = db.get(User, verification.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Account cannot be verified")

    verification.used_at = now
    user.email_verified = True
    db.add(
        AuditEvent(
            actor_user_id=user.id,
            action="identity.email_verified",
            resource_type="user",
            resource_id=str(user.id),
            details={},
        )
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if not verify_password(payload.password, user.password_hash if user else None):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email verification is required")

    token, expires_at = create_access_token(user.id)
    db.add(
        AuditEvent(
            actor_user_id=user.id,
            action="identity.login",
            resource_type="user",
            resource_id=str(user.id),
            details={},
        )
    )
    db.commit()
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)

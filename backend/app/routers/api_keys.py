from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import APIKey, AuditEvent, User
from app.schemas import APIKeyCreate, APIKeyCreated, APIKeyRead
from app.security import generate_api_key

router = APIRouter(prefix="/v1/api-keys", tags=["api-keys"])


@router.post("", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: APIKeyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIKeyCreated:
    raw_key, prefix, key_hash = generate_api_key()
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
        if payload.expires_in_days is not None
        else None
    )
    api_key = APIKey(
        user_id=user.id,
        name=payload.name.strip(),
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=payload.scopes,
        expires_at=expires_at,
    )
    db.add(api_key)
    db.flush()
    db.add(
        AuditEvent(
            actor_user_id=user.id,
            action="api_key.created",
            resource_type="api_key",
            resource_id=str(api_key.id),
            details={"scopes": payload.scopes},
        )
    )
    db.commit()
    db.refresh(api_key)
    return APIKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        api_key=raw_key,
    )


@router.get("", response_model=list[APIKeyRead])
def list_api_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[APIKeyRead]:
    records = db.scalars(
        select(APIKey).where(APIKey.user_id == user.id).order_by(APIKey.created_at.desc())
    ).all()
    return [APIKeyRead.model_validate(record) for record in records]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    record = db.scalar(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="API key not found")
    if record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
        db.add(
            AuditEvent(
                actor_user_id=user.id,
                action="api_key.revoked",
                resource_type="api_key",
                resource_id=str(record.id),
                details={},
            )
        )
        db.commit()

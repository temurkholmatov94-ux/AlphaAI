from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin import require_platform_admin
from app.database import get_db
from app.models import AuditEvent, ModelRecord, User

router = APIRouter(prefix="/v1/admin/models", tags=["platform-admin", "model-universe"])

REVIEW_STATUSES = ("discovered", "review-required", "degraded", "retired", "available")
LICENSE_STATUSES = ("unknown", "verified", "not_applicable", "restricted", "rejected")
ACCESS_METHODS = ("unknown", "download", "gated_download", "hosted_api", "self_hosted")


class ModelReviewUpdate(BaseModel):
    license_status: str = Field(min_length=1, max_length=32)
    access_method: str = Field(min_length=1, max_length=32)
    availability_status: str = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def validate_review(self):
        if self.license_status not in LICENSE_STATUSES:
            raise ValueError("Unsupported license status")
        if self.access_method not in ACCESS_METHODS:
            raise ValueError("Unsupported access method")
        if self.availability_status not in REVIEW_STATUSES:
            raise ValueError("Unsupported availability status")
        if self.availability_status == "available":
            if self.license_status not in {"verified", "not_applicable"}:
                raise ValueError("A publicly available model requires an approved license status")
            if self.access_method == "unknown":
                raise ValueError("A publicly available model requires a verified access method")
        return self


@router.get("/review-queue")
def list_review_queue(
    _admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
):
    statement = select(ModelRecord).where(
        ModelRecord.availability_status.in_(("discovered", "review-required", "degraded"))
    )
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(ModelRecord.model_id.ilike(pattern) | ModelRecord.display_name.ilike(pattern))
    count_statement = select(func.count()).select_from(ModelRecord).where(\n        ModelRecord.availability_status.in_(("discovered", "review-required", "degraded"))\n    )\n    if q:\n        pattern = f"%{q.strip()}%"\n        count_statement = count_statement.where(\n            ModelRecord.model_id.ilike(pattern) | ModelRecord.display_name.ilike(pattern)\n        )\n    total = db.scalar(count_statement) or 0
    items = db.scalars(
        statement.order_by(ModelRecord.updated_at.desc(), ModelRecord.id.desc())
        .limit(limit).offset(offset)
    ).all()
    return {
        "items": [
            {
                "model_id": item.model_id,
                "display_name": item.display_name,
                "provider": item.provider,
                "source_url": item.source_url,
                "license_id": item.license_id,
                "license_status": item.license_status,
                "access_method": item.access_method,
                "availability_status": item.availability_status,
                "tasks": item.tasks,
                "weights_available": item.weights_available,
                "gated": item.gated,
                "upstream_revision": item.upstream_revision,
                "upstream_last_modified": item.upstream_last_modified,
                "last_verified_at": item.last_verified_at,
            }
            for item in items
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/{model_id:path}/review")
def review_model(
    model_id: str,
    payload: ModelReviewUpdate,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    item = db.scalar(select(ModelRecord).where(ModelRecord.model_id == model_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Model not found")

    before = {
        "license_status": item.license_status,
        "access_method": item.access_method,
        "availability_status": item.availability_status,
    }
    item.license_status = payload.license_status
    item.access_method = payload.access_method
    item.availability_status = payload.availability_status
    item.last_verified_at = datetime.now(timezone.utc)
    item.updated_at = datetime.now(timezone.utc)
    db.add(
        AuditEvent(
            actor_user_id=admin.id,
            action="model.reviewed",
            resource_type="model",
            resource_id=item.model_id,
            details={"before": before, "after": payload.model_dump()},
        )
    )
    db.commit()
    db.refresh(item)
    return {
        "model_id": item.model_id,
        "license_status": item.license_status,
        "access_method": item.access_method,
        "availability_status": item.availability_status,
        "last_verified_at": item.last_verified_at,
    }

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import ModelRecord

PUBLIC_STATUSES = ("available",)


def list_public_models(
    db: Session,
    *,
    q: str | None = None,
    provider: str | None = None,
    task: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[ModelRecord], int]:
    filters = [ModelRecord.availability_status.in_(PUBLIC_STATUSES)]

    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                ModelRecord.model_id.ilike(pattern),
                ModelRecord.display_name.ilike(pattern),
                ModelRecord.description.ilike(pattern),
            )
        )
    if provider:
        filters.append(ModelRecord.provider.ilike(provider.strip()))
    if task:
        filters.append(ModelRecord.tasks.contains([task.strip().lower()]))

    total = db.scalar(select(func.count()).select_from(ModelRecord).where(*filters)) or 0
    statement = (
        select(ModelRecord)
        .where(*filters)
        .order_by(ModelRecord.display_name.asc(), ModelRecord.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all()), total


def get_public_model(db: Session, model_id: str) -> ModelRecord | None:
    statement = select(ModelRecord).where(
        ModelRecord.model_id == model_id,
        ModelRecord.availability_status.in_(PUBLIC_STATUSES),
    )
    return db.scalar(statement)

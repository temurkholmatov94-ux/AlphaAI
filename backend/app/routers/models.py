from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.registry import get_public_model, list_public_models
from app.schemas import ModelListResponse, ModelRead

router = APIRouter(prefix="/v1/models", tags=["model-universe"])


@router.get("", response_model=ModelListResponse)
def list_models(
    q: str | None = Query(default=None, max_length=120),
    provider: str | None = Query(default=None, max_length=100),
    task: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: Session = Depends(get_db),
) -> ModelListResponse:
    items, total = list_public_models(
        db, q=q, provider=provider, task=task, limit=limit, offset=offset
    )
    return ModelListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{model_id:path}", response_model=ModelRead)
def read_model(model_id: str, db: Session = Depends(get_db)) -> ModelRead:
    model = get_public_model(db, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelRead.model_validate(model)

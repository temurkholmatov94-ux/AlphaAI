from __future__ import annotations

from datetime import datetime
from typing import Any

from huggingface_hub import HfApi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ModelRecord


_WEIGHT_SUFFIXES = (
    ".safetensors", ".bin", ".gguf", ".pt", ".pth", ".onnx",
    ".h5", ".msgpack", ".tflite",
)


def _weight_files(info: Any) -> tuple[bool, bool]:
    """Return (file listing was supplied, recognized weight file exists)."""
    siblings = getattr(info, "siblings", None)
    if siblings is None:
        return False, False
    for sibling in siblings:
        filename = sibling if isinstance(sibling, str) else getattr(sibling, "rfilename", "")
        if str(filename).lower().endswith(_WEIGHT_SUFFIXES):
            return True, True
    return True, False


def map_huggingface_model(info: Any) -> dict:
    """Map upstream metadata to an unapproved AlphaAI registry record.

    Discovery is never proof of license approval, downloadable weights,
    or runtime availability. All new records remain review-required.
    """
    model_id = str(getattr(info, "id", "") or "").strip()
    if not model_id:
        raise ValueError("Hugging Face model metadata is missing its model id")

    card_data = getattr(info, "card_data", None)
    license_id = getattr(card_data, "license", None) if card_data else None
    pipeline_tag = getattr(info, "pipeline_tag", None)
    last_modified = getattr(info, "last_modified", None)
    gated_value = getattr(info, "gated", False)
    gated = bool(gated_value) if gated_value is not None else None
    listing_supplied, has_weights = _weight_files(info)

    if has_weights and gated is True:
        weights_status = "gated"
    elif has_weights and gated is False:
        weights_status = "public"
    elif listing_supplied:
        weights_status = "not_listed"
    else:
        weights_status = "unknown"

    return {
        "model_id": model_id,
        "display_name": model_id.rsplit("/", 1)[-1],
        "provider": "Hugging Face",
        "source_url": f"https://huggingface.co/{model_id}",
        "description": None,
        "license_id": str(license_id) if license_id else None,
        "license_status": "unknown",
        "access_method": "gated_download" if gated else "download",
        "availability_status": "review-required",
        "tasks": [str(pipeline_tag).lower()] if pipeline_tag else [],
        "modalities": [],
        "context_window": None,
        "weights_available": bool(has_weights and gated is False),
        "weights_status": weights_status,
        "last_verified_at": None,
        "publisher": model_id.split("/", 1)[0] if "/" in model_id else None,
        "downloads": getattr(info, "downloads", None),
        "likes": getattr(info, "likes", None),
        "gated": gated,
        "library_name": getattr(info, "library_name", None),
        "upstream_revision": getattr(info, "sha", None),
        "upstream_last_modified": last_modified if isinstance(last_modified, datetime) else None,
    }


class HuggingFaceDiscovery:
    def __init__(self, api: HfApi | None = None):
        token = get_settings().huggingface_token or False
        self.api = api or HfApi(token=token)

    def fetch(self, *, limit: int = 50, search: str | None = None, pipeline_tag: str | None = None):
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return list(
            self.api.list_models(
                search=search,
                pipeline_tag=pipeline_tag,
                sort="downloads",
                limit=limit,
                full=True,
                cardData=True,
                token=False if not get_settings().huggingface_token else get_settings().huggingface_token,
            )
        )

    def ingest(self, db: Session, *, limit: int = 50, search: str | None = None,
               pipeline_tag: str | None = None) -> dict[str, int]:
        discovered = self.fetch(limit=limit, search=search, pipeline_tag=pipeline_tag)
        created = 0
        updated = 0

        for info in discovered:
            values = map_huggingface_model(info)
            existing = db.scalar(
                select(ModelRecord).where(ModelRecord.model_id == values["model_id"])
            )
            if existing is None:
                db.add(ModelRecord(**values))
                created += 1
                continue

            # Refresh upstream facts only. Never overwrite human license approval,
            # public availability, or runtime access decisions during discovery.
            for field in (
                "display_name", "source_url", "publisher", "downloads", "likes",
                "gated", "library_name", "upstream_revision", "upstream_last_modified",
                "tasks", "weights_available", "weights_status",
            ):
                setattr(existing, field, values[field])
            updated += 1

        db.commit()
        return {"fetched": len(discovered), "created": created, "updated": updated}

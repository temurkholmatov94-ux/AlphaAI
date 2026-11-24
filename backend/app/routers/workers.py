from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin import require_platform_admin
from app.database import get_db
from app.models import AuditEvent, ComputeWorker, User, WorkerBenchmark
from app.security import digest_secret

router = APIRouter(prefix="/v1", tags=["compute-workers"])
worker_bearer = HTTPBearer(auto_error=False)


class WorkerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class GPUReport(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    vendor: str | None = Field(default=None, max_length=40)
    vram_mb: int = Field(ge=0, le=2_000_000)


class HardwareHeartbeat(BaseModel):
    agent_version: str = Field(min_length=1, max_length=40)
    os: str = Field(min_length=1, max_length=80)
    architecture: str = Field(min_length=1, max_length=40)
    cpu_model: str | None = Field(default=None, max_length=160)
    cpu_logical_cores: int = Field(ge=1, le=4096)
    ram_total_mb: int = Field(ge=256, le=4_194_304)
    ram_available_mb: int = Field(ge=0, le=4_194_304)
    gpus: list[GPUReport] = Field(default_factory=list, max_length=32)

    @field_validator("gpus")
    @classmethod
    def validate_gpu_memory(cls, gpus):
        if sum(gpu.vram_mb for gpu in gpus) > 8_000_000:
            raise ValueError("Reported GPU memory exceeds the supported inventory bound")
        return gpus

    @field_validator("ram_available_mb")
    @classmethod
    def validate_available_ram(cls, value, info):
        total = info.data.get("ram_total_mb")
        if total is not None and value > total:
            raise ValueError("Available RAM cannot exceed total RAM")
        return value


class BenchmarkSubmission(BaseModel):
    benchmark_name: Literal["alphaai-fp32-matmul-v1"]
    benchmark_version: str = Field(min_length=1, max_length=40)
    device_name: str = Field(min_length=1, max_length=120)
    device_vram_bytes: int = Field(ge=1, le=2_000_000_000_000)
    matrix_size: int = Field(ge=256, le=2048)
    repetitions: int = Field(ge=1, le=100)
    average_latency_ms: float = Field(gt=0, le=600_000, allow_inf_nan=False)
    torch_version: str = Field(min_length=1, max_length=40)
    cuda_version: str = Field(min_length=1, max_length=40)
    driver_version: str | None = Field(default=None, max_length=40)


@router.post("/admin/workers", status_code=status.HTTP_201_CREATED)
def create_worker(
    payload: WorkerCreate,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    raw_token = "aai_worker_" + secrets.token_urlsafe(36)
    worker_id = "wkr_" + secrets.token_urlsafe(12)
    worker = ComputeWorker(
        worker_id=worker_id,
        name=payload.name.strip(),
        token_hash=digest_secret(raw_token),
        active=True,
        hardware_report={},
    )
    db.add(worker)
    db.flush()
    db.add(
        AuditEvent(
            actor_user_id=admin.id,
            action="compute_worker.created",
            resource_type="compute_worker",
            resource_id=worker_id,
            details={"name": worker.name},
        )
    )
    db.commit()
    return {
        "worker_id": worker_id,
        "name": worker.name,
        "worker_token": raw_token,
        "token_display": "shown-once",
        "message": "Store this token in the worker's secret store. It cannot be retrieved later.",
    }


def authenticate_worker(
    credentials: HTTPAuthorizationCredentials | None = Depends(worker_bearer),
    db: Session = Depends(get_db),
) -> ComputeWorker:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid worker credentials are required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    raw_token = credentials.credentials
    if not raw_token.startswith("aai_worker_"):
        raise unauthorized
    try:
        token_hash = digest_secret(raw_token)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Worker authentication is not configured")
    worker = db.scalar(select(ComputeWorker).where(ComputeWorker.token_hash == token_hash))
    if worker is None or not worker.active or worker.revoked_at is not None:
        raise unauthorized
    return worker


@router.post("/workers/heartbeat")
def worker_heartbeat(
    payload: HardwareHeartbeat,
    worker: ComputeWorker = Depends(authenticate_worker),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    worker.hardware_report = payload.model_dump()
    worker.last_seen_at = now
    db.commit()
    return {"worker_id": worker.worker_id, "accepted": True, "received_at": now}


@router.post("/workers/benchmarks", status_code=status.HTTP_201_CREATED)
def submit_worker_benchmark(
    payload: BenchmarkSubmission,
    worker: ComputeWorker = Depends(authenticate_worker),
    db: Session = Depends(get_db),
):
    # Derive the headline score on the server; never trust a client-supplied TFLOPS value.
    operations = 2 * (payload.matrix_size ** 3)
    tflops = (operations / (payload.average_latency_ms / 1000)) / 1_000_000_000_000
    if not 0 < tflops <= 100_000:
        raise HTTPException(status_code=422, detail="Benchmark result is outside supported bounds")
    result = WorkerBenchmark(
        worker_id=worker.id,
        benchmark_name=payload.benchmark_name,
        benchmark_version=payload.benchmark_version,
        device_name=payload.device_name,
        device_vram_bytes=payload.device_vram_bytes,
        matrix_size=payload.matrix_size,
        repetitions=payload.repetitions,
        average_latency_ms=payload.average_latency_ms,
        estimated_fp32_tflops=tflops,
        measurement_json={
            "torch_version": payload.torch_version,
            "cuda_version": payload.cuda_version,
            "driver_version": payload.driver_version,
            "provenance": "worker-reported; not independently attested",
        },
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return {
        "id": result.id,
        "benchmark_name": result.benchmark_name,
        "device_name": result.device_name,
        "average_latency_ms": result.average_latency_ms,
        "estimated_fp32_tflops": result.estimated_fp32_tflops,
        "trust_status": "unverified",
        "created_at": result.created_at,
    }


@router.get("/admin/workers/benchmarks")
def list_worker_benchmarks(
    _admin: User = Depends(require_platform_admin),
    limit: int =  Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(WorkerBenchmark)
        .order_by(WorkerBenchmark.created_at.desc())
        .limit(limit)
    ).all()
    workers = {
        worker.id: worker
        for worker in db.scalars(select(ComputeWorker)).all()
    }
    return {
        "items": [
            {
                "id": row.id,
                "worker_id": workers[row.worker_id].worker_id,
                "worker_name": workers[row.worker_id].name,
                "benchmark_name": row.benchmark_name,
                "device_name": row.device_name,
                "device_vram_bytes": row.device_vram_bytes,
                "matrix_size": row.matrix_size,
                "repetitions": row.repetitions,
                "average_latency_ms": row.average_latency_ms,
                "estimated_fp32_tflops": row.estimated_fp32_tflops,
                "measurement": row.measurement_json,
                "trust_status": "unverified",
                "created_at": row.created_at,
            }
            for row in rows if row.worker_id in workers
        ],
        "total_returned": len(rows),
        "limit": limit,
    }


@router.get("/admin/workers")
def list_workers(
    _admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    workers = db.scalars(select(ComputeWorker).order_by(ComputeWorker.created_at.desc())).all()
    items = []
    for worker in workers:
        last_seen = worker.last_seen_at
        if last_seen is not None and last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        online = bool(worker.active and worker.revoked_at is None and last_seen and last_seen >= now - timedelta(seconds=120))
        items.append(
            {
                "worker_id": worker.worker_id,
                "name": worker.name,
                "active": worker.active,
                "status": "online" if online else ("offline" if worker.active else "revoked"),
                "hardware": worker.hardware_report,
                "last_seen_at": worker.last_seen_at,
                "created_at": worker.created_at,
            }
        )
    return {"items": items, "total": len(items), "heartbeat_timeout_seconds": 120}


@router.post("/admin/workers/{worker_id}/revoke")
def revoke_worker(
    worker_id: str,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    worker = db.scalar(select(ComputeWorker).where(ComputeWorker.worker_id == worker_id))
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    if worker.active:
        worker.active = False
        worker.revoked_at = datetime.now(timezone.utc)
        db.add(
            AuditEvent(
                actor_user_id=admin.id,
                action="compute_worker.revoked",
                resource_type="compute_worker",
                resource_id=worker_id,
                details={"name": worker.name},
            )
        )
        db.commit()
    return {"worker_id": worker_id, "active": worker.active, "revoked": worker.revoked_at is not None}

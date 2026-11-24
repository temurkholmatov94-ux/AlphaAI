from fastapi import FastAPI

from app.config import get_settings
from app.routers.models import router as models_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Control plane for the AlphaAI multi-model intelligence platform.",
    version="0.2.0",
)

app.include_router(models_router)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "foundation",
        "docs": "/docs",
    }


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "alphaai-control-plane"}

from fastapi import APIRouter, Depends

from app.admin import require_platform_admin
from app.config import get_settings
from app.models import User
from app.providers.registry import build_provider_registry
from app.providers.service import ProviderGateway

router = APIRouter(prefix="/v1/admin/providers", tags=["platform-admin", "providers"])


@router.get("")
def list_provider_status(_admin: User = Depends(require_platform_admin)) -> dict:
    """Return configuration readiness, never secrets or live-health claims."""
    settings = get_settings()
    registry = build_provider_registry(settings)
    gateway = ProviderGateway(settings, registry=registry)
    descriptors = registry.descriptors()
    routes = gateway.route_descriptors
    route_counts = {
        descriptor.name: sum(1 for route in routes if route["provider"] == descriptor.name)
        for descriptor in descriptors
    }
    return {
        "providers": [
            {
                "name": descriptor.name,
                "protocol": descriptor.protocol,
                "credential_configured": descriptor.configured,
                "configured_route_count": route_counts[descriptor.name],
                "status": "configured" if descriptor.configured else "not-configured",
                "health_check": "not-run",
            }
            for descriptor in descriptors
        ],
        "routes": routes,
        "route_count": len(routes),
        "note": "Configuration status is not a live provider health check. No credentials are returned.",
    }

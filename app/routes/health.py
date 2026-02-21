from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import Settings
from app.services.ostium_adapter import OstiumAdapter



def build_health_router(settings: Settings, adapter: OstiumAdapter) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health():
        return {
            "status": "healthy",
            "service": "flowforge-ostium-service",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @router.get("/ready")
    async def ready():
        is_ready, reason = adapter.ready()
        if is_ready:
            return {
                "status": "ready",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "status": "not ready",
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return router

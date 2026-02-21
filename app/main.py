from __future__ import annotations

from fastapi import FastAPI

from app.config import load_settings
from app.logger import configure_logging
from app.middleware.hmac_auth import HmacAuthMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.routes.health import build_health_router
from app.routes.v1 import build_v1_router
from app.services.ostium_adapter import OstiumAdapter

settings = load_settings()
configure_logging(settings.log_level)

adapter = OstiumAdapter(settings)

app = FastAPI(title="FlowForge Ostium Service", version="0.1.0")
app.add_middleware(RequestContextMiddleware)
app.add_middleware(HmacAuthMiddleware, settings=settings)

app.include_router(build_health_router(settings, adapter))
app.include_router(build_v1_router(adapter))

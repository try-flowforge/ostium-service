from __future__ import annotations

import hmac
import logging
from hashlib import sha256
from time import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import Settings

LOGGER = logging.getLogger("ostium_service.hmac")

HMAC_HEADERS = {
    "timestamp": "x-timestamp",
    "signature": "x-signature",
}


class HmacAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/ready"}:
            return await call_next(request)

        if not request.url.path.startswith("/v1/"):
            return await call_next(request)

        if not self._settings.hmac_secret:
            return JSONResponse(
                status_code=500,
                content={"error": {"code": "SERVER_MISCONFIGURED", "message": "HMAC secret is not configured"}},
            )

        timestamp = request.headers.get(HMAC_HEADERS["timestamp"])
        signature = request.headers.get(HMAC_HEADERS["signature"])

        if not timestamp or not signature:
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "UNAUTHORIZED", "message": "Missing required authentication headers"}},
            )

        try:
            request_ts = int(timestamp)
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "UNAUTHORIZED", "message": "Invalid timestamp format"}},
            )

        now_ms = int(time() * 1000)
        if abs(now_ms - request_ts) > self._settings.hmac_timestamp_tolerance_ms:
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "UNAUTHORIZED", "message": "Request expired or timestamp too far in future"}},
            )

        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8") if body_bytes else ""
        payload = f"{timestamp}:{request.method.upper()}:{request.url.path}:{body_str}"

        expected = hmac.new(
            self._settings.hmac_secret.encode("utf-8"),
            payload.encode("utf-8"),
            sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            LOGGER.warning("HMAC verification failed", extra={"path": request.url.path})
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "UNAUTHORIZED", "message": "Invalid signature"}},
            )

        return await call_next(request)

from __future__ import annotations
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from app.schemas.common import ErrorBody, ErrorEnvelope, Meta, SuccessEnvelope
from app.services.ostium_adapter import OstiumServiceError

LOGGER = logging.getLogger("ostium_service.routes.v1")

def _meta(request: Request) -> Meta:
    return Meta(requestId=getattr(request.state, "request_id", "unknown"))

def _success(request: Request, data: dict) -> SuccessEnvelope:
    return SuccessEnvelope(success=True, data=data, meta=_meta(request))

def _error(request: Request, code: str, message: str, details: dict | None = None, retryable: bool | None = None) -> ErrorEnvelope:
    return ErrorEnvelope(
        success=False,
        error=ErrorBody(code=code, message=message, details=details, retryable=retryable),
        meta=_meta(request),
    )

def error_response(request: Request, exc: OstiumServiceError) -> JSONResponse:
    payload = _error(
        request,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        retryable=exc.retryable,
    ).model_dump()
    return JSONResponse(status_code=exc.status_code, content=payload)

def unexpected_error_response(request: Request, operation: str, exc: Exception) -> JSONResponse:
    LOGGER.exception("Unhandled exception in %s", operation)
    payload = _error(
        request,
        code="OSTIUM_INTERNAL_ERROR",
        message=f"Unexpected failure while processing {operation}",
        details={"error": str(exc), "type": type(exc).__name__, "operation": operation},
        retryable=False,
    ).model_dump()
    return JSONResponse(status_code=500, content=payload)

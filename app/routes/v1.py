from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorBody, ErrorEnvelope, Meta, SuccessEnvelope
from app.schemas.ostium import (
    BalanceRequest,
    MarketsListRequest,
    PositionCloseRequest,
    PositionOpenRequest,
    PositionsListRequest,
    PositionUpdateSlRequest,
    PositionUpdateTpRequest,
    PriceRequest,
)
from app.services.ostium_adapter import OstiumAdapter
from app.services.ostium_adapter import OstiumServiceError



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



def build_v1_router(adapter: OstiumAdapter) -> APIRouter:
    router = APIRouter(prefix="/v1")

    def error_response(request: Request, exc: OstiumServiceError) -> JSONResponse:
        payload = _error(
            request,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            retryable=exc.retryable,
        ).model_dump()
        return JSONResponse(status_code=exc.status_code, content=payload)

    @router.post("/markets/list")
    async def markets_list(payload: MarketsListRequest, request: Request):
        try:
            data = await adapter.list_markets(payload.network)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)

    @router.post("/prices/get")
    async def prices_get(payload: PriceRequest, request: Request):
        try:
            data = await adapter.get_price(payload.network, payload.base, payload.quote)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)

    @router.post("/accounts/balance")
    async def accounts_balance(payload: BalanceRequest, request: Request):
        try:
            data = await adapter.get_balance(payload.network, payload.address)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)

    @router.post("/positions/list")
    async def positions_list(payload: PositionsListRequest, request: Request):
        try:
            data = await adapter.list_positions(payload.network, payload.traderAddress)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)

    @router.post("/positions/open")
    async def positions_open(payload: PositionOpenRequest, request: Request):
        try:
            data = await adapter.open_position(payload.model_dump())
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)

    @router.post("/positions/close")
    async def positions_close(payload: PositionCloseRequest, request: Request):
        try:
            data = await adapter.close_position(payload.model_dump())
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)

    @router.post("/positions/update-sl")
    async def positions_update_sl(payload: PositionUpdateSlRequest, request: Request):
        try:
            data = await adapter.update_sl(payload.model_dump())
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)

    @router.post("/positions/update-tp")
    async def positions_update_tp(payload: PositionUpdateTpRequest, request: Request):
        try:
            data = await adapter.update_tp(payload.model_dump())
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)

    return router

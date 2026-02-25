from __future__ import annotations
from fastapi import APIRouter, Request
from app.schemas.ostium import (
    PositionOpenRequest, 
    PositionCloseRequest, 
    PositionUpdateSlRequest, 
    PositionUpdateTpRequest, 
    PositionMetricsRequest,
    PositionsListRequest
)
from app.services.ostium_adapter import OstiumAdapter, OstiumServiceError
from .common import _success, error_response, unexpected_error_response

def build_trading_router(adapter: OstiumAdapter) -> APIRouter:
    router = APIRouter()

    @router.post("/positions/list")
    async def positions_list(payload: PositionsListRequest, request: Request):
        try:
            data = await adapter.list_positions(payload.network, payload.traderAddress)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "positions/list", exc)

    @router.post("/positions/open")
    async def positions_open(payload: PositionOpenRequest, request: Request):
        try:
            data = await adapter.open_position(payload.model_dump())
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "positions/open", exc)

    @router.post("/positions/close")
    async def positions_close(payload: PositionCloseRequest, request: Request):
        try:
            data = await adapter.close_position(payload.model_dump())
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "positions/close", exc)

    @router.post("/positions/update-sl")
    async def positions_update_sl(payload: PositionUpdateSlRequest, request: Request):
        try:
            data = await adapter.update_sl(payload.model_dump())
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "positions/update-sl", exc)

    @router.post("/positions/update-tp")
    async def positions_update_tp(payload: PositionUpdateTpRequest, request: Request):
        try:
            data = await adapter.update_tp(payload.model_dump())
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "positions/update-tp", exc)

    @router.post("/positions/metrics")
    async def positions_metrics(payload: PositionMetricsRequest, request: Request):
        try:
            data = await adapter.get_position_metrics(payload.model_dump())
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "positions/metrics", exc)

    return router

from __future__ import annotations
from fastapi import APIRouter, Request
from app.schemas.ostium import OrderCancelRequest, OrderUpdateRequest, OrderTrackRequest, PositionsListRequest
from app.services.ostium_adapter import OstiumAdapter, OstiumServiceError
from .common import _success, error_response, unexpected_error_response

def build_orders_router(adapter: OstiumAdapter) -> APIRouter:
    router = APIRouter()

    @router.post("/orders/list")
    async def orders_list(payload: PositionsListRequest, request: Request):
        try:
            data = await adapter.list_orders(payload.network, payload.traderAddress)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "orders/list", exc)

    @router.post("/orders/cancel")
    async def orders_cancel(payload: OrderCancelRequest, request: Request):
        try:
            data = await adapter.cancel_order(payload.model_dump())
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "orders/cancel", exc)

    @router.post("/orders/update")
    async def orders_update(payload: OrderUpdateRequest, request: Request):
        try:
            data = await adapter.update_order(payload.model_dump())
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "orders/update", exc)

    @router.post("/orders/track")
    async def orders_track(payload: OrderTrackRequest, request: Request):
        try:
            data = await adapter.track_order(payload.network, payload.orderId)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "orders/track", exc)

    return router

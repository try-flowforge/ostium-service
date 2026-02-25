from __future__ import annotations
from fastapi import APIRouter, Request
from app.schemas.ostium import PriceRequest, MarketsListRequest, MarketFundingRequest, MarketDetailsRequest
from app.services.ostium_adapter import OstiumAdapter, OstiumServiceError
from .common import _success, error_response, unexpected_error_response

def build_market_router(adapter: OstiumAdapter) -> APIRouter:
    router = APIRouter()

    @router.post("/markets/list")
    async def markets_list(payload: MarketsListRequest, request: Request):
        try:
            data = await adapter.list_markets(payload.network)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "markets/list", exc)

    @router.post("/prices/get")
    async def prices_get(payload: PriceRequest, request: Request):
        try:
            data = await adapter.get_price(payload.network, payload.base, payload.quote)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "prices/get", exc)

    @router.post("/markets/funding-rate")
    async def markets_funding_rate(payload: MarketFundingRequest, request: Request):
        try:
            data = await adapter.get_funding_rate(payload.network, payload.pairId, payload.periodHours)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "markets/funding-rate", exc)

    @router.post("/markets/rollover-rate")
    async def markets_rollover_rate(payload: MarketFundingRequest, request: Request):
        try:
            data = await adapter.get_rollover_rate(payload.network, payload.pairId, payload.periodHours)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "markets/rollover-rate", exc)

    @router.post("/markets/details")
    async def markets_details(payload: MarketDetailsRequest, request: Request):
        try:
            data = await adapter.get_market_details(payload.network, payload.pairId)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "markets/details", exc)

    return router

from __future__ import annotations
from fastapi import APIRouter, Request
from app.schemas.ostium import BalanceRequest, PositionsListRequest, FaucetRequest
from app.services.ostium_adapter import OstiumAdapter, OstiumServiceError
from .common import _success, error_response, unexpected_error_response

def build_accounts_router(adapter: OstiumAdapter) -> APIRouter:
    router = APIRouter()

    @router.post("/accounts/balance")
    async def accounts_balance(payload: BalanceRequest, request: Request):
        try:
            data = await adapter.get_balance(payload.network, payload.address)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "accounts/balance", exc)

    @router.post("/accounts/history")
    async def accounts_history(payload: PositionsListRequest, request: Request):
        try:
            data = await adapter.get_history(payload.network, payload.traderAddress)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "accounts/history", exc)

    @router.post("/faucet/request")
    async def faucet_request(payload: FaucetRequest, request: Request):
        try:
            data = await adapter.request_faucet(payload.network, payload.traderAddress)
            return _success(request, data)
        except OstiumServiceError as exc:
            return error_response(request, exc)
        except Exception as exc:
            return unexpected_error_response(request, "faucet/request", exc)

    return router

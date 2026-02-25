from __future__ import annotations
from fastapi import APIRouter
from app.services.ostium_adapter import OstiumAdapter
from .trading import build_trading_router
from .orders import build_orders_router
from .market import build_market_router
from .accounts import build_accounts_router

def build_v1_router(adapter: OstiumAdapter) -> APIRouter:
    router = APIRouter(prefix="/v1")
    
    router.include_router(build_trading_router(adapter))
    router.include_router(build_orders_router(adapter))
    router.include_router(build_market_router(adapter))
    router.include_router(build_accounts_router(adapter))
    
    return router

from __future__ import annotations
from typing import Any
from app.config import Settings
from .ostium.base import OstiumServiceError
from .ostium.market_manager import MarketManager
from .ostium.trading_manager import TradingManager
from .ostium.order_manager import OrderManager
from .ostium.account_manager import AccountManager

class OstiumAdapter:
    def __init__(self, settings: Settings):
        self._settings = settings
        self.market = MarketManager(settings)
        self.trading = TradingManager(settings, self.market)
        self.orders = OrderManager(settings)
        self.accounts = AccountManager(settings)

    def ready(self) -> tuple[bool, str | None]:
        if not self._settings.ostium_enabled:
            return False, "OSTIUM_ENABLED is false"
        # Since we use sdk internal to managers, we just assume it's ready if managers can init
        return True, None

    # Redirect methods to domain managers
    async def list_markets(self, network: str) -> dict[str, Any]:
        return await self.market.list_markets(network)

    async def get_price(self, network: str, base: str, quote: str, detailed: bool = False) -> dict[str, Any]:
        return await self.market.get_price(network, base, quote, detailed)

    async def get_balance(self, network: str, address: str) -> dict[str, Any]:
        return await self.accounts.get_balance(network, address)

    async def list_positions(self, network: str, trader_address: str) -> dict[str, Any]:
        return await self.accounts.list_positions(network, trader_address)

    async def open_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.trading.open_position(payload)

    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.trading.close_position(payload)

    async def update_sl(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.trading.update_sl(payload)

    async def update_tp(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.trading.update_tp(payload)

    async def list_orders(self, network: str, trader_address: str) -> dict[str, Any]:
        return await self.orders.list_orders(network, trader_address)

    async def get_history(self, network: str, trader_address: str, limit: int = 20) -> dict[str, Any]:
        return await self.accounts.get_history(network, trader_address, limit)

    async def cancel_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.orders.cancel_order(payload)

    async def update_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.orders.update_order(payload)

    async def track_order(self, network: str, order_id: str) -> dict[str, Any]:
        return await self.orders.track_order(network, order_id)

    async def get_position_metrics(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.trading.get_position_metrics(payload)

    async def get_funding_rate(self, network: str, pair_id: int, period_hours: int = 24) -> dict[str, Any]:
        return await self.market.get_funding_rate(network, pair_id, period_hours)

    async def get_rollover_rate(self, network: str, pair_id: int, period_hours: int = 24) -> dict[str, Any]:
        return await self.market.get_rollover_rate(network, pair_id, period_hours)

    async def get_market_details(self, network: str, pair_id: int) -> dict[str, Any]:
        return await self.market.get_market_details(network, pair_id)

    async def request_faucet(self, network: str, trader_address: str | None = None) -> dict[str, Any]:
        return await self.accounts.request_faucet(network, trader_address)

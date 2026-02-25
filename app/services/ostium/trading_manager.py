from __future__ import annotations
import asyncio
from typing import Any
from .base import BaseManager, OstiumServiceError
from .market_manager import MarketManager

class TradingManager(BaseManager):
    def __init__(self, settings: Any, market_manager: MarketManager):
        super().__init__(settings)
        self._market_manager = market_manager

    async def open_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._idempotency_get(payload.get("idempotencyKey"))
        if existing: return existing

        network = payload["network"]
        trader_address = payload.get("traderAddress")
        pair_id = await self._market_manager.resolve_pair_id(network, payload["market"])
        side = str(payload["side"]).lower()
        order_type = str(payload.get("orderType", "market")).upper()
        trigger_price = payload.get("triggerPrice")
        slippage = float(payload.get("slippage", 2.0))

        delegate_key = self._ensure_delegate_key()
        sdk = self._build_sdk(network, private_key=delegate_key)

        try:
            max_leverage = await sdk.get_pair_max_leverage(pair_id)
            if float(payload["leverage"]) > max_leverage:
                raise OstiumServiceError(code="LEVERAGE_TOO_HIGH", message=f"Leverage exceeds maximum of {max_leverage}x", status_code=400)
        except Exception as exc:
            if isinstance(exc, OstiumServiceError): raise
        
        symbol = await self._market_manager.resolve_pair_symbol(network, pair_id)
        if not symbol: raise OstiumServiceError(code="INVALID_MARKET", message=f"Could not resolve symbol for pairId={pair_id}", status_code=400)

        if order_type == "MARKET":
            price_data = await self._market_manager.get_price(network, symbol, "USD")
            at_price = price_data.get("price")
            if at_price is None: raise OstiumServiceError(code="PRICE_FETCH_FAILED", message=f"Could not determine market price", status_code=502)
        else:
            if trigger_price is None: raise OstiumServiceError(code="TRIGGER_PRICE_REQUIRED", message=f"triggerPrice is required", status_code=400)
            at_price = trigger_price

        trade_params = {"asset_type": pair_id, "collateral": float(payload["collateral"]), "direction": side == "long", "leverage": float(payload["leverage"]), "order_type": order_type}
        if payload.get("slPrice") is not None: trade_params["sl"] = float(payload["slPrice"])
        if payload.get("tpPrice") is not None: trade_params["tp"] = float(payload["tpPrice"])
        if trader_address: trade_params["trader_address"] = trader_address

        try:
            if hasattr(sdk.ostium, "set_slippage_percentage"): sdk.ostium.set_slippage_percentage(slippage)
            result = await asyncio.to_thread(sdk.ostium.perform_trade, trade_params, float(at_price))
        except Exception as exc:
            raise self._normalize_sdk_error("open_position", "OPEN_POSITION_FAILED", "Failed to open position", exc) from exc

        response = {"network": network, "pairId": pair_id, "orderType": order_type, "triggerPrice": float(at_price), "status": "submitted", "result": self._to_json_safe(result)}
        self._idempotency_set(payload.get("idempotencyKey"), response)
        return response

    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._idempotency_get(payload.get("idempotencyKey"))
        if existing: return existing

        network = payload["network"]
        pair_id, trade_index = int(payload["pairId"]), int(payload["tradeIndex"])
        trader_address = payload.get("traderAddress")
        close_percentage, slippage = float(payload.get("closePercentage", 100.0)), float(payload.get("slippage", 2.0))

        delegate_key = self._ensure_delegate_key()
        sdk = self._build_sdk(network, private_key=delegate_key)

        symbol = await self._market_manager.resolve_pair_symbol(network, pair_id)
        if not symbol: raise OstiumServiceError(code="INVALID_MARKET", message="Could not resolve symbol", status_code=400)

        price_data = await self._market_manager.get_price(network, symbol, "USD")
        market_price = price_data.get("price")
        if market_price is None: raise OstiumServiceError(code="PRICE_FETCH_FAILED", message="Could not determine price", status_code=502)

        try:
            if hasattr(sdk.ostium, "set_slippage_percentage"): sdk.ostium.set_slippage_percentage(slippage)
            result = await asyncio.to_thread(sdk.ostium.close_trade, pair_id=pair_id, trade_index=trade_index, market_price=float(market_price), close_percentage=close_percentage, trader_address=trader_address)
        except Exception as exc:
            raise self._normalize_sdk_error("close_position", "CLOSE_POSITION_FAILED", "Failed to close position", exc) from exc

        response = {"network": network, "pairId": pair_id, "tradeIndex": trade_index, "status": "submitted", "result": self._to_json_safe(result)}
        self._idempotency_set(payload.get("idempotencyKey"), response)
        return response

    async def update_sl(self, payload: dict[str, Any]) -> dict[str, Any]:
        network, pair_id, trade_index, sl_price = payload["network"], int(payload["pairId"]), int(payload["tradeIndex"]), float(payload["slPrice"])
        trader_address = payload.get("traderAddress")
        sdk = self._build_sdk(network, private_key=self._ensure_delegate_key())
        try:
            result = await asyncio.to_thread(sdk.ostium.update_sl, pair_id=pair_id, trade_index=trade_index, sl_price=sl_price, trader_address=trader_address)
        except Exception as exc:
            raise self._normalize_sdk_error("update_sl", "UPDATE_SL_FAILED", "Failed to update SL", exc) from exc
        return {"network": network, "pairId": pair_id, "tradeIndex": trade_index, "slPrice": sl_price, "status": "submitted", "result": self._to_json_safe(result)}

    async def update_tp(self, payload: dict[str, Any]) -> dict[str, Any]:
        network, pair_id, trade_index, tp_price = payload["network"], int(payload["pairId"]), int(payload["tradeIndex"]), float(payload["tpPrice"])
        trader_address = payload.get("traderAddress")
        sdk = self._build_sdk(network, private_key=self._ensure_delegate_key())
        try:
            result = await asyncio.to_thread(sdk.ostium.update_tp, pair_id=pair_id, trade_index=trade_index, tp_price=tp_price, trader_address=trader_address)
        except Exception as exc:
            raise self._normalize_sdk_error("update_tp", "UPDATE_TP_FAILED", "Failed to update TP", exc) from exc
        return {"network": network, "pairId": pair_id, "tradeIndex": trade_index, "tpPrice": tp_price, "status": "submitted", "result": self._to_json_safe(result)}

    async def get_position_metrics(self, payload: dict[str, Any]) -> dict[str, Any]:
        network, pair_id, trade_index, trader_address = payload["network"], int(payload["pairId"]), int(payload["tradeIndex"]), payload.get("traderAddress")
        sdk = self._build_sdk(network, private_key=self._ensure_delegate_key())
        try:
            metrics = await sdk.get_open_trade_metrics(pair_id=pair_id, trade_index=trade_index, trader_address=trader_address)
        except Exception as exc:
            raise OstiumServiceError(code="METRICS_FETCH_FAILED", message="Failed to fetch metrics", status_code=502, details={"error": str(exc)}) from exc
        return {"network": network, "pairId": pair_id, "tradeIndex": trade_index, "metrics": self._to_json_safe(metrics)}

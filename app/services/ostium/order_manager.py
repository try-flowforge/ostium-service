from __future__ import annotations
import asyncio
from typing import Any
from .base import BaseManager, OstiumServiceError, Decimal

class OrderManager(BaseManager):
    async def list_orders(self, network: str, trader_address: str) -> dict[str, Any]:
        sdk = self._build_sdk(network)
        try:
            orders = await sdk.subgraph.get_orders(trader_address)
        except Exception as exc:
            raise OstiumServiceError(code="ORDERS_FETCH_FAILED", message="Failed to fetch orders", status_code=502, details={"error": str(exc)}) from exc
        return {"network": network, "traderAddress": trader_address, "orders": self._to_json_safe(orders if isinstance(orders, list) else [])}

    async def cancel_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._idempotency_get(payload.get("idempotencyKey"))
        if existing: return existing
        network, pair_id, trade_index, trader_address = payload["network"], int(payload["pairId"]), int(payload["tradeIndex"]), payload.get("traderAddress")
        sdk = self._build_sdk(network, private_key=self._ensure_delegate_key())
        try:
            result = await asyncio.to_thread(sdk.ostium.cancel_limit_order, pair_id=pair_id, trade_index=trade_index, trader_address=trader_address)
        except Exception as exc:
            raise self._normalize_sdk_error("cancel_order", "CANCEL_ORDER_FAILED", "Failed to cancel order", exc) from exc
        response = {"network": network, "pairId": pair_id, "tradeIndex": trade_index, "status": "submitted", "result": self._to_json_safe(result)}
        self._idempotency_set(payload.get("idempotencyKey"), response)
        return response

    async def update_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        network, pair_id, trade_index = payload["network"], int(payload["pairId"]), int(payload["tradeIndex"])
        price, tp, sl = payload.get("price"), payload.get("tpPrice"), payload.get("slPrice")
        delegate_key = self._ensure_delegate_key()
        sdk = self._build_sdk(network, private_key=delegate_key)
        try:
            result = await asyncio.to_thread(sdk.ostium.update_limit_order, pair_id=pair_id, index=trade_index, pvt_key=delegate_key, price=Decimal(str(price)) if price else None, tp=Decimal(str(tp)) if tp else None, sl=Decimal(str(sl)) if sl else None)
        except Exception as exc:
            raise self._normalize_sdk_error("update_order", "UPDATE_ORDER_FAILED", "Failed to update order", exc) from exc
        return {"network": network, "pairId": pair_id, "tradeIndex": trade_index, "status": "submitted", "result": self._to_json_safe(result)}

    async def track_order(self, network: str, order_id: str) -> dict[str, Any]:
        sdk = self._build_sdk(network)
        try:
            result = await asyncio.to_thread(sdk.ostium.track_order_and_trade, subgraph_client=sdk.subgraph, order_id=order_id)
        except Exception as exc:
            raise OstiumServiceError(code="ORDER_TRACKING_FAILED", message=f"Failed to track order {order_id}", status_code=502, details={"error": str(exc)}) from exc
        return {"network": network, "orderId": order_id, "result": self._to_json_safe(result)}

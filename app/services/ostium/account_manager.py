from __future__ import annotations
import asyncio
from typing import Any
from .base import BaseManager, OstiumServiceError

class AccountManager(BaseManager):
    async def get_balance(self, network: str, address: str) -> dict[str, Any]:
        sdk = self._build_sdk(network)
        try:
            usdc = await asyncio.to_thread(sdk.balance.get_usdc_balance, address)
            native = await asyncio.to_thread(sdk.balance.get_ether_balance, address)
        except Exception as exc:
            raise OstiumServiceError(code="BALANCE_FETCH_FAILED", message="Failed to fetch balances", status_code=502, details={"error": str(exc)}) from exc
        return {"network": network, "address": address, "balances": {"usdc": self._to_json_safe(usdc), "native": self._to_json_safe(native)}}

    async def list_positions(self, network: str, trader_address: str) -> dict[str, Any]:
        sdk = self._build_sdk(network)
        try:
            positions = await sdk.subgraph.get_open_trades(trader_address)
        except Exception as exc:
            raise OstiumServiceError(code="POSITIONS_FETCH_FAILED", message="Failed to fetch positions", status_code=502, details={"error": str(exc)}) from exc
        return {"network": network, "traderAddress": trader_address, "positions": self._to_json_safe(positions if isinstance(positions, list) else [])}

    async def get_history(self, network: str, trader_address: str, limit: int = 20) -> dict[str, Any]:
        sdk = self._build_sdk(network)
        try:
            history = await sdk.subgraph.get_recent_history(trader_address, last_n_orders=limit)
        except Exception as exc:
            raise OstiumServiceError(code="HISTORY_FETCH_FAILED", message="Failed to fetch history", status_code=502, details={"error": str(exc)}) from exc
        return {"network": network, "traderAddress": trader_address, "history": self._to_json_safe(history if isinstance(history, list) else [])}

    async def request_faucet(self, network: str, trader_address: str | None = None) -> dict[str, Any]:
        if network != "testnet": raise OstiumServiceError(code="FAUCET_NOT_AVAILABLE", message="Faucet is testnet only", status_code=400)
        sdk = self._build_sdk(network, private_key=self._ensure_delegate_key())
        if not sdk.faucet: raise OstiumServiceError(code="FAUCET_UNAVAILABLE", message="Faucet not initialized", status_code=503)
        target = trader_address or sdk.ostium.get_public_address()
        try:
            method = getattr(sdk.faucet, "get_tokens", getattr(sdk.faucet, "request_tokens", None))
            if not method: result = "Manual request required"
            else:
                try:
                    result = await asyncio.to_thread(method, target)
                except TypeError as e:
                    if "argument" in str(e):
                        result = await asyncio.to_thread(method)
                    else:
                        raise
            return {"network": network, "address": target, "status": "submitted", "result": self._to_json_safe(result)}
        except Exception as exc:
            raise self._normalize_sdk_error("request_faucet", "FAUCET_REQUEST_FAILED", "Failed to request faucet", exc) from exc

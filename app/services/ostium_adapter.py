from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.config import Settings

try:
    # Official package import path
    from ostium_python_sdk import OstiumSDK  # type: ignore
except Exception:  # pragma: no cover - import availability depends on env
    OstiumSDK = None  # type: ignore


LOGGER = logging.getLogger("ostium_service.adapter")

_DUMMY_PRIVATE_KEY = "0x" + ("1" * 64)


@dataclass(frozen=True)
class OstiumServiceError(Exception):
    code: str
    message: str
    status_code: int = 400
    retryable: bool | None = None
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


class OstiumAdapter:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._idempotency_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def ready(self) -> tuple[bool, str | None]:
        if not self._settings.ostium_enabled:
            return False, "OSTIUM_ENABLED is false"
        if OstiumSDK is None:
            return False, "ostium_python_sdk import failed"
        return True, None

    def _network_rpc(self, network: str) -> str:
        if network == "testnet":
            return self._settings.ostium_testnet_rpc_url
        if network == "mainnet":
            return self._settings.ostium_mainnet_rpc_url
        raise OstiumServiceError(
            code="INVALID_NETWORK",
            message="network must be testnet or mainnet",
            status_code=400,
            retryable=False,
        )

    def _build_sdk(self, network: str, private_key: str | None = None):
        if not self._settings.ostium_enabled:
            raise OstiumServiceError(
                code="OSTIUM_DISABLED",
                message="Ostium is disabled by configuration",
                status_code=503,
                retryable=False,
            )
        if OstiumSDK is None:
            raise OstiumServiceError(
                code="SDK_UNAVAILABLE",
                message="Ostium SDK is not available in runtime",
                status_code=503,
                retryable=False,
            )

        rpc_url = self._network_rpc(network)
        return OstiumSDK(
            network=network,
            private_key=private_key or _DUMMY_PRIVATE_KEY,
            rpc_url=rpc_url,
            use_delegation=bool(private_key and self._settings.ostium_delegate_private_key),
        )

    def _ensure_delegate_key(self) -> str:
        if not self._settings.ostium_delegate_private_key:
            raise OstiumServiceError(
                code="DELEGATE_KEY_MISSING",
                message="OSTIUM_DELEGATE_PRIVATE_KEY is not configured",
                status_code=503,
                retryable=False,
            )
        return self._settings.ostium_delegate_private_key

    def _idempotency_get(self, key: str | None) -> dict[str, Any] | None:
        if not key:
            return None
        item = self._idempotency_cache.get(key)
        if not item:
            return None
        created_at, payload = item
        if time.time() - created_at > 3600:
            self._idempotency_cache.pop(key, None)
            return None
        return payload

    def _idempotency_set(self, key: str | None, payload: dict[str, Any]) -> None:
        if not key:
            return
        self._idempotency_cache[key] = (time.time(), payload)

    async def _maybe_await(self, value: Any) -> Any:
        if asyncio.iscoroutine(value):
            return await value
        return await asyncio.to_thread(lambda: value)

    async def _fetch_pairs(self, network: str) -> list[dict[str, Any]]:
        sdk = self._build_sdk(network)
        try:
            pairs = await asyncio.to_thread(sdk.get_formatted_pairs_details)
            if isinstance(pairs, list):
                return pairs
        except Exception:
            LOGGER.debug("get_formatted_pairs_details failed, trying subgraph.get_pairs")

        try:
            pairs = await sdk.subgraph.get_pairs()
            if isinstance(pairs, list):
                return pairs
        except Exception as exc:
            raise OstiumServiceError(
                code="MARKETS_FETCH_FAILED",
                message="Failed to fetch markets from Ostium",
                status_code=502,
                retryable=True,
                details={"error": str(exc)},
            ) from exc
        return []

    async def _resolve_pair_id(self, network: str, market: str) -> int:
        if market.isdigit():
            return int(market)

        normalized = market.upper()
        pairs = await self._fetch_pairs(network)
        for pair in pairs:
            pair_from = str(pair.get("from", "")).upper()
            symbol = str(pair.get("symbol", "")).upper()
            name = str(pair.get("name", "")).upper()
            if normalized in {pair_from, symbol, name}:
                pair_id = pair.get("id") or pair.get("pairId")
                if pair_id is not None:
                    return int(pair_id)
        raise OstiumServiceError(
            code="INVALID_MARKET",
            message=f"Market '{market}' is not available on {network}",
            status_code=400,
            retryable=False,
        )

    async def _resolve_pair_symbol(self, network: str, pair_id: int) -> str | None:
        pairs = await self._fetch_pairs(network)
        for pair in pairs:
            current_id = pair.get("id") or pair.get("pairId")
            if current_id is None:
                continue
            if int(current_id) == pair_id:
                symbol = str(pair.get("from", "")).upper()
                return symbol or None
        return None

    @staticmethod
    def _decimal_to_str(value: Any) -> str:
        if isinstance(value, Decimal):
            return format(value, "f")
        return str(value)

    @classmethod
    def _to_json_safe(cls, value: Any) -> Any:
        if isinstance(value, Decimal):
            return format(value, "f")
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, bytes):
            return "0x" + value.hex()
        if isinstance(value, bytearray):
            return "0x" + bytes(value).hex()
        if isinstance(value, dict):
            return {str(key): cls._to_json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [cls._to_json_safe(item) for item in value]
        if hasattr(value, "hex"):
            try:
                hex_value = value.hex()
            except Exception:
                hex_value = None
            if isinstance(hex_value, str):
                return hex_value if hex_value.startswith("0x") else f"0x{hex_value}"
        if hasattr(value, "__dict__"):
            return cls._to_json_safe(vars(value))
        return str(value)

    async def list_markets(self, network: str) -> dict[str, Any]:
        pairs = await self._fetch_pairs(network)
        markets: list[dict[str, Any]] = []
        for pair in pairs:
            pair_id = pair.get("id") or pair.get("pairId")
            if pair_id is None:
                continue
            base = str(pair.get("from", "")).upper()
            quote = str(pair.get("to", "USD")).upper()
            status = "active"
            if pair.get("isPaused") is True:
                status = "paused"
            markets.append(
                {
                    "pairId": int(pair_id),
                    "symbol": base,
                    "pair": f"{base}/{quote}",
                    "status": status,
                }
            )
        return {"network": network, "markets": markets}

    async def get_price(self, network: str, base: str, quote: str) -> dict[str, Any]:
        sdk = self._build_sdk(network)
        try:
            result = await sdk.price.get_price(base.upper(), quote.upper())
            if isinstance(result, tuple):
                price = float(result[0]) if len(result) > 0 and result[0] is not None else None
                is_market_open = bool(result[1]) if len(result) > 1 else None
                is_day_trading_closed = bool(result[2]) if len(result) > 2 else None
            else:
                price = float(result) if result is not None else None
                is_market_open = None
                is_day_trading_closed = None
        except Exception as exc:
            raise OstiumServiceError(
                code="PRICE_FETCH_FAILED",
                message=f"Failed to fetch price for {base}/{quote}",
                status_code=502,
                retryable=True,
                details={"error": str(exc)},
            ) from exc

        return {
            "network": network,
            "base": base.upper(),
            "quote": quote.upper(),
            "price": price,
            "isMarketOpen": is_market_open,
            "isDayTradingClosed": is_day_trading_closed,
        }

    async def get_balance(self, network: str, address: str) -> dict[str, Any]:
        sdk = self._build_sdk(network)
        try:
            usdc_balance = await asyncio.to_thread(sdk.balance.get_usdc_balance, address)
            native_balance = await asyncio.to_thread(sdk.balance.get_ether_balance, address)
        except Exception as exc:
            raise OstiumServiceError(
                code="BALANCE_FETCH_FAILED",
                message=f"Failed to fetch balances for {address}",
                status_code=502,
                retryable=True,
                details={"error": str(exc)},
            ) from exc

        return {
            "network": network,
            "address": address,
            "balances": {
                "usdc": self._decimal_to_str(usdc_balance),
                "native": self._decimal_to_str(native_balance),
            },
        }

    async def list_positions(self, network: str, trader_address: str) -> dict[str, Any]:
        sdk = self._build_sdk(network)
        try:
            positions = await sdk.subgraph.get_open_trades(trader_address)
        except Exception as exc:
            raise OstiumServiceError(
                code="POSITIONS_FETCH_FAILED",
                message=f"Failed to fetch positions for {trader_address}",
                status_code=502,
                retryable=True,
                details={"error": str(exc)},
            ) from exc

        return {
            "network": network,
            "traderAddress": trader_address,
            "positions": self._to_json_safe(positions if isinstance(positions, list) else []),
        }

    async def open_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._idempotency_get(payload.get("idempotencyKey"))
        if existing:
            return existing

        network = payload["network"]
        trader_address = payload.get("traderAddress")
        pair_id = await self._resolve_pair_id(network, payload["market"])
        side = str(payload["side"]).lower()
        if side not in {"long", "short"}:
            raise OstiumServiceError(
                code="INVALID_SIDE",
                message="side must be long or short",
                status_code=400,
                retryable=False,
            )

        delegate_key = self._ensure_delegate_key()
        sdk = self._build_sdk(network, private_key=delegate_key)

        symbol = await self._resolve_pair_symbol(network, pair_id)
        if not symbol:
            raise OstiumServiceError(
                code="INVALID_MARKET",
                message=f"Could not resolve market symbol for pairId={pair_id}",
                status_code=400,
                retryable=False,
            )
        price_data = await self.get_price(network, symbol, "USD")
        at_price = price_data.get("price")
        if at_price is None:
            raise OstiumServiceError(
                code="PRICE_FETCH_FAILED",
                message=f"Could not determine market price for {symbol}",
                status_code=502,
                retryable=True,
            )

        trade_params: dict[str, Any] = {
            "asset_type": pair_id,
            "collateral": float(payload["collateral"]),
            "direction": side == "long",
            "leverage": float(payload["leverage"]),
        }
        if trader_address:
            trade_params["trader_address"] = trader_address

        try:
            result = await asyncio.to_thread(
                sdk.ostium.perform_trade,
                trade_params,
                at_price,
            )
        except Exception as exc:
            raise OstiumServiceError(
                code="OPEN_POSITION_FAILED",
                message="Failed to open position on Ostium",
                status_code=502,
                retryable=True,
                details={"error": str(exc)},
            ) from exc

        response = {
            "network": network,
            "pairId": pair_id,
            "status": "submitted",
            "result": self._to_json_safe(result),
        }
        self._idempotency_set(payload.get("idempotencyKey"), response)
        return response

    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._idempotency_get(payload.get("idempotencyKey"))
        if existing:
            return existing

        network = payload["network"]
        pair_id = int(payload["pairId"])
        trade_index = int(payload["tradeIndex"])
        trader_address = payload.get("traderAddress")

        delegate_key = self._ensure_delegate_key()
        sdk = self._build_sdk(network, private_key=delegate_key)

        symbol = await self._resolve_pair_symbol(network, pair_id)
        if not symbol:
            raise OstiumServiceError(
                code="INVALID_MARKET",
                message=f"Could not resolve market symbol for pairId={pair_id}",
                status_code=400,
                retryable=False,
            )

        price_data = await self.get_price(network, symbol, "USD")
        market_price = price_data.get("price")
        if market_price is None:
            raise OstiumServiceError(
                code="PRICE_FETCH_FAILED",
                message=f"Could not determine market price for pairId={pair_id}",
                status_code=502,
                retryable=True,
            )

        try:
            if trader_address:
                result = await asyncio.to_thread(
                    sdk.ostium.close_trade,
                    trade_index,
                    float(market_price),
                    pair_id,
                    trader_address,
                )
            else:
                result = await asyncio.to_thread(
                    sdk.ostium.close_trade,
                    trade_index,
                    float(market_price),
                    pair_id,
                )
        except Exception as exc:
            raise OstiumServiceError(
                code="CLOSE_POSITION_FAILED",
                message="Failed to close position on Ostium",
                status_code=502,
                retryable=True,
                details={"error": str(exc)},
            ) from exc

        response = {
            "network": network,
            "pairId": pair_id,
            "tradeIndex": trade_index,
            "status": "submitted",
            "result": self._to_json_safe(result),
        }
        self._idempotency_set(payload.get("idempotencyKey"), response)
        return response

    async def update_sl(self, payload: dict[str, Any]) -> dict[str, Any]:
        network = payload["network"]
        pair_id = int(payload["pairId"])
        trade_index = int(payload["tradeIndex"])
        sl_price = float(payload["slPrice"])
        trader_address = payload.get("traderAddress")

        delegate_key = self._ensure_delegate_key()
        sdk = self._build_sdk(network, private_key=delegate_key)

        try:
            if trader_address:
                result = await asyncio.to_thread(
                    sdk.ostium.update_sl,
                    pair_id,
                    trade_index,
                    sl_price,
                    trader_address,
                )
            else:
                result = await asyncio.to_thread(
                    sdk.ostium.update_sl,
                    pair_id,
                    trade_index,
                    sl_price,
                )
        except Exception as exc:
            raise OstiumServiceError(
                code="UPDATE_SL_FAILED",
                message="Failed to update stop-loss on Ostium",
                status_code=502,
                retryable=True,
                details={"error": str(exc)},
            ) from exc

        return {
            "network": network,
            "pairId": pair_id,
            "tradeIndex": trade_index,
            "slPrice": sl_price,
            "result": self._to_json_safe(result),
        }

    async def update_tp(self, payload: dict[str, Any]) -> dict[str, Any]:
        network = payload["network"]
        pair_id = int(payload["pairId"])
        trade_index = int(payload["tradeIndex"])
        tp_price = float(payload["tpPrice"])
        trader_address = payload.get("traderAddress")

        delegate_key = self._ensure_delegate_key()
        sdk = self._build_sdk(network, private_key=delegate_key)

        try:
            if trader_address:
                result = await asyncio.to_thread(
                    sdk.ostium.update_tp,
                    pair_id,
                    trade_index,
                    tp_price,
                    trader_address,
                )
            else:
                result = await asyncio.to_thread(
                    sdk.ostium.update_tp,
                    pair_id,
                    trade_index,
                    tp_price,
                )
        except Exception as exc:
            raise OstiumServiceError(
                code="UPDATE_TP_FAILED",
                message="Failed to update take-profit on Ostium",
                status_code=502,
                retryable=True,
                details={"error": str(exc)},
            ) from exc

        return {
            "network": network,
            "pairId": pair_id,
            "tradeIndex": trade_index,
            "tpPrice": tp_price,
            "result": self._to_json_safe(result),
        }

from __future__ import annotations
import asyncio
from typing import Any
from .base import BaseManager, OstiumServiceError, LOGGER

class MarketManager(BaseManager):
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

    async def resolve_pair_id(self, network: str, market: str) -> int:
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

    async def resolve_pair_symbol(self, network: str, pair_id: int) -> str | None:
        pairs = await self._fetch_pairs(network)
        for pair in pairs:
            current_id = pair.get("id") or pair.get("pairId")
            if current_id is None: continue
            if int(current_id) == pair_id:
                symbol = str(pair.get("from", "")).upper()
                return symbol or None
        return None

    async def list_markets(self, network: str) -> dict[str, Any]:
        pairs = await self._fetch_pairs(network)
        markets = []
        for pair in pairs:
            pair_id = pair.get("id") or pair.get("pairId")
            if pair_id is None: continue
            base = str(pair.get("from", "")).upper()
            quote = str(pair.get("to", "USD")).upper()
            status = "active"
            if pair.get("isPaused") is True: status = "paused"
            markets.append({"pairId": int(pair_id), "symbol": base, "pair": f"{base}/{quote}", "status": status})
        return {"network": network, "markets": markets}

    async def get_price(self, network: str, base: str, quote: str, detailed: bool = False) -> dict[str, Any]:
        sdk = self._build_sdk(network)
        try:
            if detailed:
                result = await sdk.price.get_latest_price_json(base.upper(), quote.upper())
                return {"network": network, "base": base.upper(), "quote": quote.upper(), "priceData": self._to_json_safe(result)}
            
            result = await sdk.price.get_price(base.upper(), quote.upper())
            if isinstance(result, tuple):
                price = float(result[0]) if len(result) > 0 and result[0] is not None else None
                is_market_open = bool(result[1]) if len(result) > 1 else None
                is_day_trading_closed = bool(result[2]) if len(result) > 2 else None
            else:
                price = float(result) if result is not None else None
                is_market_open = is_day_trading_closed = None
        except Exception as exc:
            raise OstiumServiceError(code="PRICE_FETCH_FAILED", message=f"Failed to fetch price for {base}/{quote}", status_code=502, retryable=True, details={"error": str(exc)}) from exc

        return {"network": network, "base": base.upper(), "quote": quote.upper(), "price": price, "isMarketOpen": is_market_open, "isDayTradingClosed": is_day_trading_closed}

    async def get_funding_rate(self, network: str, pair_id: int, period_hours: int = 24) -> dict[str, Any]:
        sdk = self._build_sdk(network)
        try:
            res = await sdk.get_funding_rate_for_pair_id(pair_id, period_hours=period_hours)
            return {"network": network, "pairId": pair_id, "periodHours": period_hours, "accFundingLong": str(res[0]), "accFundingShort": str(res[1]), "fundingRatePercent": float(res[2]), "targetFundingRatePercent": float(res[3])}
        except Exception as exc:
            raise OstiumServiceError(code="FUNDING_FETCH_FAILED", message=f"Failed to fetch funding rate for pairId={pair_id}", status_code=502, retryable=True, details={"error": str(exc)}) from exc

    async def get_rollover_rate(self, network: str, pair_id: int, period_hours: int = 24) -> dict[str, Any]:
        sdk = self._build_sdk(network)
        try:
            res = await sdk.get_rollover_rate_for_pair_id(pair_id, period_hours=period_hours)
            return {"network": network, "pairId": pair_id, "periodHours": period_hours, "rolloverRate": str(res)}
        except Exception as exc:
            raise OstiumServiceError(code="ROLLOVER_FETCH_FAILED", message=f"Failed to fetch rollover rate for pairId={pair_id}", status_code=502, retryable=True, details={"error": str(exc)}) from exc

    async def get_market_details(self, network: str, pair_id: int) -> dict[str, Any]:
        sdk = self._build_sdk(network)
        try:
            res = await sdk.subgraph.get_pair_details(pair_id)
            return {"network": network, "pairId": pair_id, "details": self._to_json_safe(res)}
        except Exception as exc:
            raise OstiumServiceError(code="MARKET_DETAILS_FAILED", message=f"Failed to fetch details for pairId={pair_id}", status_code=502, retryable=True, details={"error": str(exc)}) from exc

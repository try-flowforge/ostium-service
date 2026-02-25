from __future__ import annotations
from pydantic import field_validator
from .base import NetworkedRequest

class PositionOpenRequest(NetworkedRequest):
    market: str
    side: str
    collateral: float
    leverage: float
    orderType: str = "market"  # market, limit, stop
    triggerPrice: float | None = None
    slippage: float = 2.0
    slPrice: float | None = None
    tpPrice: float | None = None
    traderAddress: str | None = None
    idempotencyKey: str | None = None

    @field_validator("orderType")
    @classmethod
    def validate_order_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"market", "limit", "stop"}:
            raise ValueError("orderType must be market, limit, or stop")
        return normalized

    @field_validator("side")
    @classmethod
    def validate_side(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"long", "short"}:
            raise ValueError("side must be long or short")
        return normalized

    @field_validator("collateral", "leverage")
    @classmethod
    def validate_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("value must be greater than 0")
        return value

    @field_validator("slPrice", "tpPrice")
    @classmethod
    def validate_optional_positive(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value <= 0:
            raise ValueError("value must be greater than 0")
        return value

class PositionCloseRequest(NetworkedRequest):
    pairId: int
    tradeIndex: int
    closePercentage: float = 100.0
    slippage: float = 2.0
    traderAddress: str | None = None
    idempotencyKey: str | None = None

class PositionUpdateSlRequest(NetworkedRequest):
    pairId: int
    tradeIndex: int
    slPrice: float
    traderAddress: str | None = None

class PositionUpdateTpRequest(NetworkedRequest):
    pairId: int
    tradeIndex: int
    tpPrice: float
    traderAddress: str | None = None

class PositionMetricsRequest(NetworkedRequest):
    pairId: int
    tradeIndex: int
    traderAddress: str | None = None

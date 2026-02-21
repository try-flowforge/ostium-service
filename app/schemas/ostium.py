from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class NetworkedRequest(BaseModel):
    network: str = Field(description="testnet or mainnet")

    @field_validator("network")
    @classmethod
    def validate_network(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"testnet", "mainnet"}:
            raise ValueError("network must be testnet or mainnet")
        return normalized


class MarketsListRequest(NetworkedRequest):
    pass


class PriceRequest(NetworkedRequest):
    base: str
    quote: str = "USD"


class BalanceRequest(NetworkedRequest):
    address: str


class PositionsListRequest(NetworkedRequest):
    traderAddress: str


class PositionOpenRequest(NetworkedRequest):
    market: str
    side: str
    collateral: float
    leverage: float
    traderAddress: str | None = None
    idempotencyKey: str | None = None

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


class PositionCloseRequest(NetworkedRequest):
    pairId: int
    tradeIndex: int
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

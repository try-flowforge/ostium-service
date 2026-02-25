from __future__ import annotations
from .base import NetworkedRequest

class OrderCancelRequest(NetworkedRequest):
    pairId: int
    tradeIndex: int
    traderAddress: str | None = None
    idempotencyKey: str | None = None

class OrderUpdateRequest(NetworkedRequest):
    pairId: int
    tradeIndex: int
    price: float | None = None
    slPrice: float | None = None
    tpPrice: float | None = None
    traderAddress: str | None = None

class OrderTrackRequest(NetworkedRequest):
    orderId: str

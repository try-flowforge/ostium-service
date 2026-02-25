from __future__ import annotations
from .base import NetworkedRequest

class MarketsListRequest(NetworkedRequest):
    pass

class PriceRequest(NetworkedRequest):
    base: str
    quote: str = "USD"

class MarketFundingRequest(NetworkedRequest):
    pairId: int
    periodHours: int = 24

class MarketDetailsRequest(NetworkedRequest):
    pairId: int

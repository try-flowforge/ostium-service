from __future__ import annotations
from .base import NetworkedRequest

class BalanceRequest(NetworkedRequest):
    address: str

class PositionsListRequest(NetworkedRequest):
    traderAddress: str

class FaucetRequest(NetworkedRequest):
    traderAddress: str | None = None

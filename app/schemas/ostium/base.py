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

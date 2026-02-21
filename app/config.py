from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    log_level: str
    hmac_secret: str
    hmac_timestamp_tolerance_ms: int
    request_timeout_ms: int
    sdk_connect_timeout_ms: int
    ostium_enabled: bool
    ostium_testnet_rpc_url: str
    ostium_mainnet_rpc_url: str
    ostium_delegate_private_key: str | None



def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}



def load_settings() -> Settings:
    return Settings(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5002")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        hmac_secret=os.getenv("HMAC_SECRET", ""),
        hmac_timestamp_tolerance_ms=int(os.getenv("HMAC_TIMESTAMP_TOLERANCE_MS", "300000")),
        request_timeout_ms=int(os.getenv("REQUEST_TIMEOUT_MS", "30000")),
        sdk_connect_timeout_ms=int(os.getenv("SDK_CONNECT_TIMEOUT_MS", "10000")),
        ostium_enabled=_to_bool(os.getenv("OSTIUM_ENABLED"), True),
        ostium_testnet_rpc_url=os.getenv("OSTIUM_TESTNET_RPC_URL", "https://sepolia-rollup.arbitrum.io/rpc"),
        ostium_mainnet_rpc_url=os.getenv("OSTIUM_MAINNET_RPC_URL", "https://arb1.arbitrum.io/rpc"),
        ostium_delegate_private_key=os.getenv("OSTIUM_DELEGATE_PRIVATE_KEY") or None,
    )

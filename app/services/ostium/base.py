from __future__ import annotations
import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from app.config import Settings

try:
    from ostium_python_sdk import OstiumSDK  # type: ignore
except Exception:
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

class BaseManager:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._idempotency_cache: dict[str, tuple[float, dict[str, Any]]] = {}

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
                if isinstance(hex_value, str):
                    return hex_value if hex_value.startswith("0x") else f"0x{hex_value}"
            except Exception:
                pass
        if hasattr(value, "__dict__"):
            return cls._to_json_safe(vars(value))
        return str(value)

    def _normalize_sdk_error(
        self,
        operation: str,
        default_code: str,
        default_message: str,
        exc: Exception,
    ) -> OstiumServiceError:
        raw_error = str(exc)
        lower_error = raw_error.lower()
        details = {"error": raw_error, "operation": operation}

        if "sufficient allowance" in lower_error or "allowance for" in lower_error:
            return OstiumServiceError(
                code="ALLOWANCE_MISSING",
                message="Sufficient allowance not present. Approve the trading contract to spend USDC.",
                status_code=400,
                retryable=False,
                details=details,
            )
        if "delegation is not active" in lower_error or "delegation not active" in lower_error:
            return OstiumServiceError(
                code="DELEGATION_NOT_ACTIVE",
                message="Delegation is not active. Approve delegation before write actions.",
                status_code=400,
                retryable=False,
                details=details,
            )
        if "safe wallet not found" in lower_error:
            return OstiumServiceError(
                code="SAFE_WALLET_MISSING",
                message="Safe wallet not found for selected network.",
                status_code=400,
                retryable=False,
                details=details,
            )
        if "delegate wallet gas is low" in lower_error or "insufficient funds for gas" in lower_error:
            return OstiumServiceError(
                code="DELEGATE_GAS_LOW",
                message="Delegate wallet gas is low. Fund delegate wallet with ETH.",
                status_code=400,
                retryable=False,
                details=details,
            )
        if "timeout" in lower_error or "timed out" in lower_error:
            return OstiumServiceError(
                code="OSTIUM_SERVICE_TIMEOUT",
                message="Ostium service timed out.",
                status_code=504,
                retryable=True,
                details=details,
            )
        return OstiumServiceError(
            code=default_code,
            message=default_message,
            status_code=502,
            retryable=True,
            details=details,
        )

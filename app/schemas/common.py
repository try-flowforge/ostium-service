from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Meta(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    requestId: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    retryable: bool | None = None


class SuccessEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any]
    meta: Meta


class ErrorEnvelope(BaseModel):
    success: bool = False
    error: ErrorBody
    meta: Meta

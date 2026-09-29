from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class GuardrailStatus(str, Enum):
    PASS = "pass"
    BLOCKED = "blocked"
    FALLBACK = "fallback"
    SANITIZED = "sanitized"


class GuardrailResult(BaseModel):
    passed: bool = True
    guardrail_name: str
    action: str = "allow"  # "allow", "reject", "fallback", "sanitize"
    reason: str | None = None
    user_message: str | None = None
    sanitized_query: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "guardrail_name": self.guardrail_name,
            "action": self.action,
            "reason": self.reason,
            "user_message": self.user_message,
            "sanitized_query": self.sanitized_query,
            "metadata": self.metadata,
        }

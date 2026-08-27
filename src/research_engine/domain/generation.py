from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GenerationRequest:
    system_prompt: str
    user_prompt: str
    temperature: float = 0.7
    max_tokens: int = 4096
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    content: str
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

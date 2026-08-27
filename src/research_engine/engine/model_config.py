from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelConfig:
    name: str
    provider: str
    model: str
    endpoint: str
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "endpoint": self.endpoint,
            "api_key": self.api_key,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


@dataclass
class ModelRegistry:
    _models: dict[str, ModelConfig] = field(
        default_factory=dict
    )

    def register(self, config: ModelConfig) -> None:
        if config.name in self._models:
            raise ValueError(
                f"Model already registered: {config.name}"
            )

        self._models[config.name] = config

    def get(self, name: str) -> ModelConfig:
        try:
            return self._models[name]
        except KeyError as exc:
            raise KeyError(
                f"Model not found: {name}"
            ) from exc

    def has(self, name: str) -> bool:
        return name in self._models

    def list(self) -> list[ModelConfig]:
        return list(self._models.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "models": [
                model.to_dict()
                for model in self._models.values()
            ]
        }

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelConfig:
    """
    Immutable configuration of a generation model.

    `name`
        Stable configuration name referenced by Worker.model.

    `model`
        Actual model identifier sent to the provider.

    `generation_parameters`
        Canonical generation parameter dictionary.

    Legacy convenience fields `api_key`, `temperature`, and `max_tokens`
    remain supported because older tests/loaders use them directly.
    """

    name: str
    provider: str
    model: str
    endpoint: str

    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096

    generation_parameters: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Model name must not be empty")

        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("Model provider must not be empty")

        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Model identifier must not be empty")

        if not isinstance(self.endpoint, str) or not self.endpoint.strip():
            raise ValueError("Model endpoint must not be empty")

        if self.api_key is not None and not isinstance(self.api_key, str):
            raise ValueError("Model api_key must be a string or null")

        if not isinstance(self.temperature, (int, float)):
            raise ValueError("Model temperature must be numeric")

        if not isinstance(self.max_tokens, int):
            raise ValueError("Model max_tokens must be an integer")

        parameters = dict(self.generation_parameters)

        # Legacy constructor fields become defaults.
        parameters.setdefault("temperature", self.temperature)
        parameters.setdefault("max_tokens", self.max_tokens)

        object.__setattr__(
            self,
            "generation_parameters",
            parameters,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "endpoint": self.endpoint,
            "api_key": self.api_key,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "generation_parameters": dict(
                self.generation_parameters
            ),
        }


@dataclass
class ModelRegistry:
    """
    Registry of configured generation models.

    Models are addressed by their stable configuration name.
    """

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
                f"Unknown model: {name}"
            ) from exc

    def has(self, name: str) -> bool:
        return name in self._models

    def list(self) -> list[ModelConfig]:
        return list(self._models.values())

    def names(self) -> list[str]:
        return list(self._models.keys())

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {
            name: config.to_dict()
            for name, config in self._models.items()
        }

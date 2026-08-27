from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelConfig:
    """
    Immutable configuration of a generation model.

    The configuration describes how a worker should reach a model
    and which generation parameters should be used by default.
    """

    name: str
    provider: str
    model: str
    endpoint: str
    generation_parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Model name must not be empty")

        if not self.provider.strip():
            raise ValueError("Model provider must not be empty")

        if not self.model.strip():
            raise ValueError("Model identifier must not be empty")

        if not self.endpoint.strip():
            raise ValueError("Model endpoint must not be empty")

        # Make a defensive copy even though the dataclass itself is frozen.
        # This prevents the caller from changing the original dictionary
        # after construction.
        object.__setattr__(
            self,
            "generation_parameters",
            dict(self.generation_parameters),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the model configuration.

        A copy of generation_parameters is returned so callers cannot
        accidentally mutate the configuration through the returned dict.
        """
        return {
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "endpoint": self.endpoint,
            "generation_parameters": dict(self.generation_parameters),
        }


@dataclass
class ModelRegistry:
    """
    Registry of configured generation models.

    Models are addressed by their unique configuration name.
    """

    _models: dict[str, ModelConfig] = field(default_factory=dict)

    def register(self, config: ModelConfig) -> None:
        """
        Register a model configuration.

        Duplicate names are rejected because the model name is the
        stable identifier used by workers.
        """
        if config.name in self._models:
            raise ValueError(
                f"Model already registered: {config.name}"
            )

        self._models[config.name] = config

    def get(self, name: str) -> ModelConfig:
        """
        Return a registered model configuration.

        Raises:
            KeyError: if the model does not exist.
        """
        try:
            return self._models[name]
        except KeyError as exc:
            raise KeyError(
                f"Unknown model: {name}"
            ) from exc

    def has(self, name: str) -> bool:
        """Return True when a model with this name is registered."""
        return name in self._models

    def list(self) -> list[ModelConfig]:
        """
        Return all registered model configurations.

        The returned list is independent from the registry.
        """
        return list(self._models.values())

    def names(self) -> list[str]:
        """Return registered model names."""
        return list(self._models.keys())

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Serialize the complete registry."""
        return {
            name: config.to_dict()
            for name, config in self._models.items()
        }

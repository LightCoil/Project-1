from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelConfig:
    """
    Configuration of an external generation model.

    The model itself is not part of Project-1.
    Project-1 only stores the information required to access it.
    """

    name: str
    provider: str
    model: str
    endpoint: str
    api_key: str | None = None

    temperature: float = 0.7
    max_tokens: int = 4096

    capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "endpoint": self.endpoint,
            "api_key": self.api_key,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "capabilities": list(self.capabilities),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelConfig:
        return cls(
            name=str(data["name"]),
            provider=str(data["provider"]),
            model=str(data["model"]),
            endpoint=str(data["endpoint"]),
            api_key=data.get("api_key"),
            temperature=float(data.get("temperature", 0.7)),
            max_tokens=int(data.get("max_tokens", 4096)),
            capabilities=list(data.get("capabilities", [])),
        )


@dataclass
class ModelRegistry:
    """
    Registry of model configurations.

    Project-1 can work with any number of externally hosted models.
    The registry only maps a logical configuration name to ModelConfig.
    """

    _models: dict[str, ModelConfig] = field(default_factory=dict)

    def register(self, config: ModelConfig) -> None:
        """
        Add or replace a model configuration.
        """
        self._models[config.name] = config

    def get(self, name: str) -> ModelConfig:
        """
        Return a model configuration by name.

        Raises:
            KeyError: if the requested model does not exist.
        """
        try:
            return self._models[name]
        except KeyError as exc:
            raise KeyError(
                f"Unknown model: {name}"
            ) from exc

    def remove(self, name: str) -> None:
        """
        Remove a model configuration.
        """
        try:
            del self._models[name]
        except KeyError as exc:
            raise KeyError(
                f"Unknown model: {name}"
            ) from exc

    def has(self, name: str) -> bool:
        """
        Check whether a model configuration exists.
        """
        return name in self._models

    def list(self) -> list[ModelConfig]:
        """
        Return all registered model configurations.
        """
        return list(self._models.values())

    def names(self) -> list[str]:
        """
        Return names of all registered models.
        """
        return list(self._models.keys())

    def clear(self) -> None:
        """
        Remove all registered model configurations.
        """
        self._models.clear()

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """
        Serialize the complete registry.
        """
        return {
            name: config.to_dict()
            for name, config in self._models.items()
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, dict[str, Any]],
    ) -> ModelRegistry:
        """
        Restore a registry from serialized data.
        """
        registry = cls()

        for name, config_data in data.items():
            config = ModelConfig.from_dict(
                {
                    **config_data,
                    "name": config_data.get("name", name),
                }
            )
            registry.register(config)

        return registry

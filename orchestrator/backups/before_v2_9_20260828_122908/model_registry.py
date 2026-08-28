
"""PROJECT-1 model registry.

The registry describes which executors are available to the
strategic planner. It contains capabilities and limits, but
never contains API keys or secrets.
"""

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ModelInfo:
    name: str
    provider: str
    description: str
    capabilities: tuple[str, ...]
    context_window: int | None = None
    max_output_tokens: int | None = None
    supports_streaming: bool = False
    supports_reasoning: bool = False
    supports_code: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["capabilities"] = list(self.capabilities)
        return data


class ModelRegistry:

    def __init__(self):
        self._models: dict[str, ModelInfo] = {}

    def register(self, model: ModelInfo) -> None:
        if not model.name.strip():
            raise ValueError("Model name cannot be empty.")

        self._models[model.name] = model

    def unregister(self, name: str) -> None:
        self._models.pop(name, None)

    def get(self, name: str) -> ModelInfo:
        if name not in self._models:
            raise KeyError(
                f"Unknown model: {name}"
            )

        return self._models[name]

    def names(self) -> list[str]:
        return list(self._models.keys())

    def all(self) -> list[ModelInfo]:
        return list(self._models.values())

    def describe_for_planner(self) -> list[dict[str, Any]]:
        return [
            model.to_dict()
            for model in self._models.values()
        ]

    def __len__(self) -> int:
        return len(self._models)

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model_config import ModelConfig, ModelRegistry


class ModelConfigLoader:
    """
    Загружает конфигурацию моделей из JSON-файла.

    Формат:

    {
        "models": [
            {
                "name": "generator",
                "provider": "openai-compatible",
                "model": "some-model",
                "endpoint": "http://localhost:8000/v1",
                "api_key": "..."
            }
        ]
    }

    API-ключи можно не указывать в конфигурации.
    В этом случае значение будет None.
    """

    def load(self, path: str | Path) -> ModelRegistry:
        config_path = Path(path)

        if not config_path.exists():
            raise FileNotFoundError(
                f"Model configuration file not found: {config_path}"
            )

        if not config_path.is_file():
            raise ValueError(
                f"Model configuration path is not a file: {config_path}"
            )

        try:
            payload = json.loads(
                config_path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in model configuration: {config_path}"
            ) from exc

        return self.from_dict(payload)

    def from_dict(self, payload: dict[str, Any]) -> ModelRegistry:
        if not isinstance(payload, dict):
            raise ValueError(
                "Model configuration root must be an object"
            )

        models = payload.get("models")

        if models is None:
            raise ValueError(
                "Model configuration must contain 'models'"
            )

        if not isinstance(models, list):
            raise ValueError(
                "'models' must be a list"
            )

        registry = ModelRegistry()

        for index, item in enumerate(models):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Model entry #{index + 1} must be an object"
                )

            registry.register(
                self._build_config(item, index)
            )

        return registry

    def _build_config(
        self,
        payload: dict[str, Any],
        index: int,
    ) -> ModelConfig:
        required = (
            "name",
            "provider",
            "model",
            "endpoint",
        )

        for field in required:
            if field not in payload:
                raise ValueError(
                    f"Model entry #{index + 1} "
                    f"is missing required field '{field}'"
                )

        return ModelConfig(
            name=self._require_string(
                payload["name"],
                "name",
                index,
            ),
            provider=self._require_string(
                payload["provider"],
                "provider",
                index,
            ),
            model=self._require_string(
                payload["model"],
                "model",
                index,
            ),
            endpoint=self._require_string(
                payload["endpoint"],
                "endpoint",
                index,
            ),
            api_key=self._optional_string(
                payload.get("api_key"),
                "api_key",
                index,
            ),
            temperature=payload.get(
                "temperature",
                0.7,
            ),
            max_tokens=payload.get(
                "max_tokens",
                4096,
            ),
        )

    @staticmethod
    def _require_string(
        value: Any,
        field: str,
        index: int,
    ) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Model entry #{index + 1} field "
                f"'{field}' must be a non-empty string"
            )

        return value.strip()

    @staticmethod
    def _optional_string(
        value: Any,
        field: str,
        index: int,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(
                f"Model entry #{index + 1} field "
                f"'{field}' must be a string or null"
            )

        return value

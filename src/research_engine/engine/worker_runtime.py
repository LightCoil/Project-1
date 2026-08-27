from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from research_engine.domain.worker import Worker
from research_engine.engine.model_config import (
    ModelConfig,
    ModelRegistry,
)


@dataclass
class WorkerRuntime:
    """
    Runtime-слой между Worker, ModelRegistry
    и GenerationClient.

    Runtime не изменяет ModelConfig в Registry.
    """

    worker: Worker
    registry: ModelRegistry | None = None
    client: Any | None = None

    def resolve_model(self) -> ModelConfig:
        """
        Разрешает конфигурацию модели Worker'а.
        """

        model_name = getattr(
            self.worker,
            "model_name",
            None,
        )

        if not model_name:
            model_name = getattr(
                self.worker,
                "model",
                "",
            )

        if not model_name:
            raise ValueError(
                "Worker has no configured model"
            )

        if self.registry is None:
            raise ValueError(
                "Model registry is not configured"
            )

        return self.registry.get(model_name)

    def model_config(self) -> ModelConfig:
        """
        Совместимый alias.
        """
        return self.resolve_model()

    def generation_parameters(self) -> dict[str, Any]:
        """
        Возвращает независимую копию параметров генерации.

        Изменение результата не меняет Registry.
        """

        config = self.resolve_model()

        parameters = getattr(
            config,
            "generation_parameters",
            {},
        )

        return deepcopy(parameters)

    def get_generation_parameters(
        self,
    ) -> dict[str, Any]:
        return self.generation_parameters()

    def generate(
        self,
        request: Any,
    ) -> Any:
        """
        Передаёт generation request клиенту.

        Поддерживается Worker-aware API:
            client.generate(worker, request)
        """

        if self.client is None:
            raise ValueError(
                "Generation client is not configured"
            )

        # Проверяем конфигурацию до generation.
        config = self.resolve_model()

        # Не мутируем Worker или ModelConfig.
        _ = config

        return self.client.generate(
            self.worker,
            request,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Сериализуемая информация о runtime.
        """

        config = self.resolve_model()

        return {
            "worker_id": self.worker.id,
            "worker_name": self.worker.name,
            "model_name": getattr(
                self.worker,
                "model_name",
                self.worker.model,
            ),
            "model": getattr(
                config,
                "model",
                None,
            ),
            "provider": getattr(
                config,
                "provider",
                None,
            ),
            "endpoint": getattr(
                config,
                "endpoint",
                None,
            ),
            "generation_parameters": deepcopy(
                getattr(
                    config,
                    "generation_parameters",
                    {},
                )
            ),
        }

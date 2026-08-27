from __future__ import annotations

from dataclasses import dataclass

from research_engine.engine.generation_client import GenerationClient
from research_engine.engine.http_client import HttpGenerationClient
from research_engine.engine.model_config import ModelConfig, ModelRegistry
from research_engine.engine.worker_runtime import WorkerRuntime


@dataclass(frozen=True)
class RuntimeFactory:
    """
    Создаёт WorkerRuntime на основании конфигурации модели.

    Factory не управляет жизненным циклом WorkerRuntime и не хранит
    изменяемое состояние выполнения исследования.
    """

    registry: ModelRegistry

    def create(
        self,
        *,
        worker_model: str,
    ) -> WorkerRuntime:
        """
        Создать runtime для указанной модели.

        Parameters
        ----------
        worker_model:
            Имя модели, зарегистрированной в ModelRegistry.

        Returns
        -------
        WorkerRuntime
            Runtime, связанный с найденной конфигурацией модели.

        Raises
        ------
        KeyError
            Если модель не зарегистрирована.
        """
        config = self.registry.get(worker_model)

        client = self._create_client(config)

        return WorkerRuntime(
            model_config=config,
            client=client,
        )

    def _create_client(
        self,
        config: ModelConfig,
    ) -> GenerationClient:
        """
        Создать GenerationClient для конкретной конфигурации.

        На этом этапе поддерживаются:
        - fake
        - openai-compatible
        """
        provider = config.provider.strip().lower()

        if provider == "fake":
            return _FakeCompatibleClient(config)

        if provider in {"openai-compatible", "openai_compatible"}:
            return HttpGenerationClient(
                endpoint=config.endpoint,
            )

        raise ValueError(
            f"Unsupported model provider: {config.provider}"
        )


class _FakeCompatibleClient:
    """
    Минимальный placeholder для fake provider.

    Реальный FakeGenerationClient подключается на уровне тестов/локального
    runtime, поэтому factory не создаёт здесь скрытого глобального состояния.
    """

    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    def generate(self, worker, request):
        from research_engine.engine.fake_client import FakeGenerationClient

        client = FakeGenerationClient()
        return client.generate(worker, request)

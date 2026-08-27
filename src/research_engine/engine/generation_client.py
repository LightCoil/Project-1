from __future__ import annotations

from typing import Protocol

from research_engine.domain.generation import (
    GenerationRequest,
    GenerationResult,
)
from research_engine.domain.worker import Worker


class GenerationClient(Protocol):
    """
    Контракт клиента генерации.

    Scheduler зависит только от этого интерфейса.
    Конкретная реализация может работать через:

    - FakeGenerationClient;
    - HTTP API;
    - локальный inference server;
    - другой backend.

    Project-1 не должен зависеть от конкретной модели.
    """

    def generate(
        self,
        worker: Worker,
        request: GenerationRequest,
    ) -> GenerationResult:
        """
        Выполнить генерацию и вернуть GenerationResult.
        """
        ...

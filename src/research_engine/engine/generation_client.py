from __future__ import annotations

from typing import Protocol

from research_engine.domain.generation import (
    GenerationRequest,
    GenerationResult,
)
from research_engine.domain.worker import Worker


class GenerationClient(Protocol):
    """
    Абстрактный контракт клиента генерации.

    Scheduler работает только с этим интерфейсом.
    Конкретная реализация модели находится за его пределами.
    """

    def generate(
        self,
        worker: Worker,
        request: GenerationRequest,
    ) -> GenerationResult:
        """
        Выполнить генерацию через указанного Worker.
        """
        ...

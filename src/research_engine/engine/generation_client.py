from __future__ import annotations

from typing import Protocol

from research_engine.domain.generation import (
    GenerationRequest,
    GenerationResult,
)
from research_engine.domain.worker import Worker


class GenerationClient(Protocol):
    """
    Абстрактный интерфейс генерации.

    Scheduler работает с этим контрактом и не знает,
    каким образом фактически вызывается модель.

    Реализация может быть:
      - FakeGenerationClient для тестов;
      - HTTP-клиентом;
      - клиентом локального inference-сервера;
      - любым другим совместимым backend.
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

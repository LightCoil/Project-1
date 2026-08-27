from __future__ import annotations

from research_engine.domain.generation import (
    GenerationRequest,
    GenerationResult,
)
from research_engine.domain.worker import Worker
from research_engine.engine.generation_client import GenerationClient


class FakeGenerationClient:
    """
    Тестовая реализация GenerationClient.

    Используется для тестирования Project-1 без реальной модели.
    """

    def __init__(
        self,
        *,
        fail_on_step: str | None = None,
    ) -> None:
        self.fail_on_step = fail_on_step

    def generate(
        self,
        worker: Worker,
        request: GenerationRequest,
    ) -> GenerationResult:

        context = request.context

        step_name = context.get("step_name")

        if (
            self.fail_on_step is not None
            and step_name == self.fail_on_step
        ):
            raise RuntimeError(
                f"Fake generation failure on step {step_name}"
            )

        # ----------------------------------------------------
        # Определяем текущий этап.
        #
        # Реальный ContextBuilder уже формирует request.context.
        # Поэтому Fake client не должен самостоятельно строить
        # контекст исследования.
        # ----------------------------------------------------

        if step_name == "A":

            content = (
                f"[FAKE A by {worker.name}] "
                f"Thesis generated from the research objective.\n\n"
                f"{request.user_prompt}"
            )

        elif step_name == "B":

            content = (
                f"[FAKE B by {worker.name}] "
                f"Critique of the previous result.\n\n"
                f"{request.user_prompt}"
            )

        elif step_name == "C":

            content = (
                f"[FAKE C by {worker.name}] "
                f"Revision of the previous results.\n\n"
                f"{request.user_prompt}"
            )

        elif step_name == "D":

            content = (
                f"[FAKE D by {worker.name}] "
                f"Critique of the revised result.\n\n"
                f"{request.user_prompt}"
            )

        elif step_name == "E":

            content = (
                f"[FAKE E by {worker.name}] "
                f"Final result.\n\n"
                f"{request.user_prompt}"
            )

        else:

            content = (
                f"[FAKE by {worker.name}]\n\n"
                f"{request.user_prompt}"
            )

        return GenerationResult(
            content=content,
            metadata={
                "provider": "fake",
                "model": worker.model,
                "step": step_name,
            },
        )


# ------------------------------------------------------------
# Runtime contract check
# ------------------------------------------------------------
#
# Protocol не требует наследования, поэтому это просто
# документационная проверка для разработчика.
#

_: GenerationClient = FakeGenerationClient()

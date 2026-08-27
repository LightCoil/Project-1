from __future__ import annotations

from research_engine.domain.generation import (
    GenerationRequest,
    GenerationResult,
)
from research_engine.domain.worker import Worker
from research_engine.engine.generation_client import GenerationClient


class FakeGenerationClient:
    """
    Тестовый клиент генерации.

    Не обращается к внешней модели.
    Нужен для проверки Scheduler и всего pipeline.
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

        step = request.context.get("step")

        if (
            self.fail_on_step is not None
            and step == self.fail_on_step
        ):
            raise RuntimeError(
                f"Fake generation failure on step {step}"
            )

        if step == "A":
            content = (
                f"[FAKE A by {worker.name}] "
                f"Thesis for: "
                f"{request.context.get('objective', '')}"
            )

        elif step == "B":
            source = request.context.get("inputs", {}).get("A", "")

            content = (
                f"[FAKE B by {worker.name}] "
                f"Critique of A: {source}"
            )

        elif step == "C":
            inputs = request.context.get("inputs", {})

            content = (
                f"[FAKE C by {worker.name}] "
                f"Revision using A and B. "
                f"A={inputs.get('A', '')} | "
                f"B={inputs.get('B', '')}"
            )

        elif step == "D":
            source = request.context.get("inputs", {}).get("C", "")

            content = (
                f"[FAKE D by {worker.name}] "
                f"Critique of C: {source}"
            )

        elif step == "E":
            inputs = request.context.get("inputs", {})

            content = (
                f"[FAKE E by {worker.name}] "
                f"Final from C and D. "
                f"C={inputs.get('C', '')} | "
                f"D={inputs.get('D', '')}"
            )

        else:
            content = (
                f"[FAKE {step} by {worker.name}] "
                f"{request.user_prompt}"
            )

        return GenerationResult(
            content=content,
            metadata={
                "provider": "fake",
                "model": worker.model,
                "step": step,
            },
        )


# Проверяем совместимость реализации с контрактом.
_: GenerationClient = FakeGenerationClient()

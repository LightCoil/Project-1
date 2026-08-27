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

    Никаких сетевых запросов или настоящих моделей.
    Используется для проверки работы движка.
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
        """
        Создаёт детерминированный искусственный результат.
        """

        step_name = request.step_name

        if (
            self.fail_on_step is not None
            and step_name == self.fail_on_step
        ):
            raise RuntimeError(
                f"Fake generation failure on step {step_name}"
            )

        if step_name == "A":
            text = (
                f"[FAKE A by {worker.name}] "
                f"Thesis for: {request.objective}"
            )

        elif step_name == "B":
            source = request.inputs.get("A", "")

            text = (
                f"[FAKE B by {worker.name}] "
                f"Critique of A: {source}"
            )

        elif step_name == "C":
            source_a = request.inputs.get("A", "")
            source_b = request.inputs.get("B", "")

            text = (
                f"[FAKE C by {worker.name}] "
                f"Revision using A and B. "
                f"A={source_a} | B={source_b}"
            )

        elif step_name == "D":
            source_c = request.inputs.get("C", "")

            text = (
                f"[FAKE D by {worker.name}] "
                f"Critique of C: {source_c}"
            )

        elif step_name == "E":
            source_c = request.inputs.get("C", "")
            source_d = request.inputs.get("D", "")

            text = (
                f"[FAKE E by {worker.name}] "
                f"Final from C and D. "
                f"C={source_c} | D={source_d}"
            )

        else:
            text = (
                f"[FAKE {step_name} by {worker.name}] "
                f"Generated result."
            )

        return GenerationResult(
            text=text,
            model=worker.model,
        )

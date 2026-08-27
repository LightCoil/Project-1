from __future__ import annotations

from typing import Protocol

from research_engine.domain.generation import GenerationRequest, GenerationResult
from research_engine.domain.worker import Worker


class GenerationClient(Protocol):
    def generate(self, worker: Worker, request: GenerationRequest) -> GenerationResult:
        ...


class FakeGenerationClient:
    """Deterministic stand-in for a real model API."""

    def __init__(self, *, fail_on_step: str | None = None) -> None:
        self.fail_on_step = fail_on_step
        self.calls: list[tuple[str, str]] = []

    def generate(self, worker: Worker, request: GenerationRequest) -> GenerationResult:
        step = str(request.context.get("step", "?"))
        self.calls.append((worker.id, step))
        if self.fail_on_step == step:
            raise RuntimeError(f"fake worker failure on step {step}")

        inputs = request.context.get("inputs") or {}
        if step == "A":
            content = f"[FAKE A by {worker.name}] Thesis for: {request.context['objective']}"
        elif step == "B":
            content = f"[FAKE B by {worker.name}] Critique of A: {inputs.get('A', '')}"
        elif step == "C":
            content = (
                f"[FAKE C by {worker.name}] Revision using A and B. "
                f"A={inputs.get('A', '')} | B={inputs.get('B', '')}"
            )
        elif step == "D":
            content = f"[FAKE D by {worker.name}] Critique of C: {inputs.get('C', '')}"
        elif step == "E":
            content = (
                f"[FAKE E by {worker.name}] Final from C and D. "
                f"C={inputs.get('C', '')} | D={inputs.get('D', '')}"
            )
        elif step == "SUMMARY":
            content = (
                f"**Итог:**\nShort result of {worker.name}.\n\n"
                f"**Основная идея:**\n{inputs.get('E', '')}"
            )
        else:
            content = f"[FAKE {step} by {worker.name}]"

        return GenerationResult(
            content=content,
            finish_reason="stop",
            usage={"prompt_tokens": 1, "completion_tokens": 1},
            metadata={"worker_id": worker.id, "model": worker.model},
        )

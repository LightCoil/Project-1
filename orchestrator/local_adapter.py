
"""PROJECT-1 local model adapter v2.8."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class LocalModelAdapter:
    """
    Small universal adapter used by ModelExecutor.

    It deliberately does not assume a particular inference framework.

    A real callable can be injected through `runner`.

    runner(task: str) -> str

    This keeps the orchestrator independent from:
      - transformers
      - llama.cpp
      - vLLM
      - custom WebUI runtimes
      - future inference backends
    """

    name: str
    runner: Optional[Callable[[str], Any]] = None

    def __call__(self, task: str) -> str:
        return self.run(task)

    def run(self, task: str) -> str:
        if not isinstance(task, str):
            raise TypeError("task must be a string")

        task = task.strip()

        if not task:
            raise ValueError("task cannot be empty")

        if self.runner is None:
            raise RuntimeError(
                f"Local model '{self.name}' has no inference runner."
            )

        result = self.runner(task)

        if result is None:
            return ""

        if isinstance(result, str):
            return result

        return str(result)

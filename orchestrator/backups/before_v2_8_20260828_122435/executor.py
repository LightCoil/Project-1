
"""PROJECT-1 universal model execution layer v2.7."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ExecutionRecord:
    model: str
    task: str
    status: str
    result: str
    metadata: Dict[str, Any]


class ModelExecutor:
    """
    Universal execution boundary.

    The orchestrator knows WHAT should be done.
    ModelExecutor knows HOW to invoke a registered provider.

    Provider forms supported:
      - callable
      - object.run(task)
      - object.generate(task)
      - object.execute(task)
    """

    def __init__(self, model_registry=None, providers=None):
        self.model_registry = model_registry
        self.providers = providers or {}

    def available_models(self):
        registry = self.model_registry

        if registry is None:
            return []

        if hasattr(registry, "describe"):
            return list(registry.describe() or [])

        if hasattr(registry, "list_models"):
            return list(registry.list_models() or [])

        if isinstance(registry, dict):
            return list(registry.values())

        return []

    def is_registered(self, model_name: str) -> bool:
        for model in self.available_models():
            if isinstance(model, dict):
                if model.get("name") == model_name:
                    return True
            elif getattr(model, "name", None) == model_name:
                return True

        if isinstance(self.providers, dict):
            return model_name in self.providers

        return False

    def resolve_provider(self, model_name: str):
        providers = self.providers

        if providers is None:
            return None

        if hasattr(providers, "get"):
            return providers.get(model_name)

        return None

    def execute(self, model_name: str, task: str) -> ExecutionRecord:
        if not model_name:
            raise ValueError("Model name is required.")

        if not task or not str(task).strip():
            raise ValueError("Assignment task is required.")

        if not self.is_registered(model_name):
            raise ValueError(
                f"Model '{model_name}' is unavailable."
            )

        provider = self.resolve_provider(model_name)

        if provider is None:
            return ExecutionRecord(
                model=model_name,
                task=task,
                status="stub",
                result=(
                    f"[STUB:{model_name}] "
                    f"Executed assignment: {task}"
                ),
                metadata={
                    "execution_mode": "development_stub",
                },
            )

        try:
            if callable(provider):
                result = provider(task)

            elif hasattr(provider, "run"):
                result = provider.run(task)

            elif hasattr(provider, "generate"):
                result = provider.generate(task)

            elif hasattr(provider, "execute"):
                result = provider.execute(task)

            else:
                raise TypeError(
                    f"Provider for '{model_name}' "
                    "has no supported execution interface."
                )

            return ExecutionRecord(
                model=model_name,
                task=task,
                status="completed",
                result=str(result),
                metadata={
                    "execution_mode": "provider",
                },
            )

        except Exception as exc:
            return ExecutionRecord(
                model=model_name,
                task=task,
                status="error",
                result="",
                metadata={
                    "execution_mode": "provider",
                    "error": str(exc),
                },
            )

    def execute_assignment(self, assignment) -> ExecutionRecord:
        model = getattr(assignment, "model", None)
        task = getattr(assignment, "task", None)

        if model is None and isinstance(assignment, dict):
            model = assignment.get("model")

        if task is None and isinstance(assignment, dict):
            task = assignment.get("task")

        return self.execute(model, task)

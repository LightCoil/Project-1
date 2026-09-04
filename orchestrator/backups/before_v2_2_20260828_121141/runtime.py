
"""PROJECT-1 Orchestrator runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .protocol import Command, parse_command


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ExecutionResult:
    command: dict[str, Any]
    result: Any
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "result": self.result,
            "timestamp": self.timestamp,
        }


@dataclass
class OrchestrationContext:
    task: str
    history: list[ExecutionResult] = field(default_factory=list)
    finished: bool = False
    final_result: Any = None

    def add_result(
        self,
        command: Command,
        result: Any,
    ) -> None:
        self.history.append(
            ExecutionResult(
                command=command.to_dict(),
                result=result,
            )
        )

    def results_for_planner(self) -> list[dict[str, Any]]:
        return [
            item.to_dict()
            for item in self.history
        ]


class OrchestratorRuntime:
    """
    Execution engine.

    The runtime itself does not know how ChatGPT or local models
    communicate. Providers are injected as callables.
    """

    def __init__(
        self,
        *,
        planner: Callable[[dict[str, Any]], dict[str, Any]],
        models: dict[str, Callable[[str], Any]] | None = None,
    ):
        self.planner = planner
        self.models = models or {}

    def execute_model(
        self,
        model: str,
        task: str,
    ) -> Any:
        if model not in self.models:
            raise RuntimeError(
                f"Model provider not registered: {model}"
            )

        return self.models[model](task)

    def execute_command(
        self,
        context: OrchestrationContext,
        command: Command,
    ) -> Any:

        if command.type == "ASK_MODEL":
            model = command.payload["model"]
            task = command.payload["task"]

            result = self.execute_model(model, task)
            context.add_result(command, result)
            return result

        if command.type == "ASK_GPT":
            planner_request = {
                "mode": "follow_up",
                "task": context.task,
                "prompt": command.payload["prompt"],
                "history": context.results_for_planner(),
            }

            result = self.planner(planner_request)
            context.add_result(command, result)
            return result

        if command.type == "REVIEW_RESULTS":
            planner_request = {
                "mode": "review",
                "task": context.task,
                "history": context.results_for_planner(),
            }

            result = self.planner(planner_request)
            context.add_result(command, result)
            return result

        if command.type == "FINISH":
            planner_request = {
                "mode": "final",
                "task": context.task,
                "history": context.results_for_planner(),
            }

            result = self.planner(planner_request)

            context.add_result(command, result)
            context.finished = True
            context.final_result = result

            return result

        raise RuntimeError(
            f"Unhandled command: {command.type}"
        )

    def run(
        self,
        task: str,
        *,
        max_steps: int = 20,
    ) -> OrchestrationContext:

        context = OrchestrationContext(task=task)

        planner_request = {
            "mode": "initial",
            "task": task,
            "history": [],
        }

        for _ in range(max_steps):

            response = self.planner(planner_request)

            command_data = response.get("command")

            if not command_data:
                raise RuntimeError(
                    "Planner returned no command."
                )

            command = parse_command(command_data)

            self.execute_command(
                context,
                command,
            )

            if context.finished:
                return context

            planner_request = {
                "mode": "continue",
                "task": task,
                "history": context.results_for_planner(),
            }

        raise RuntimeError(
            f"Maximum orchestration steps exceeded: {max_steps}"
        )

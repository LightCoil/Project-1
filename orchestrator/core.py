from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .state import TaskState
from .providers import ModelProvider
from .prompts import (
    PLANNER_PROMPT,
    REVIEW_PROMPT,
    SYNTHESIS_PROMPT,
)


class Orchestrator:
    """
    PROJECT-1 high-level orchestration engine.

    The important architectural principle is:

        USER
          ↓
        ORCHESTRATOR
          ↓
        strategic consultation
          ↓
        task decomposition
          ↓
        model assignments
          ↓
        model results
          ↓
        critical review
          ↓
        additional assignments
          ↓
        possible second consultation
          ↓
        synthesis

    The orchestrator itself does not need to be the strongest
    model. Its purpose is to control the reasoning process.
    """

    def __init__(
        self,
        providers: dict[str, ModelProvider],
        storage_dir: Path | None = None,
    ):
        self.providers = providers

        self.storage_dir = (
            storage_dir
            or Path(__file__).resolve().parent / "state"
        )

        self.storage_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def create_task(self, task: str) -> TaskState:
        if not task or not task.strip():
            raise ValueError("Task cannot be empty")

        state = TaskState(
            task=task.strip()
        )

        state.add_message(
            role="user",
            content=task.strip(),
            source="user",
        )

        return state

    def consult_planner(
        self,
        state: TaskState,
        provider_name: str,
    ) -> dict[str, Any]:

        provider = self.providers[provider_name]

        prompt = PLANNER_PROMPT.format(
            task=state.task
        )

        response = provider.ask(prompt)

        state.add_message(
            role="assistant",
            content=response.content,
            source=provider_name,
        )

        state.add_knowledge(
            content=response.content,
            source=provider_name,
        )

        plan = {
            "provider": provider_name,
            "response": response.content,
            "success": response.success,
        }

        state.plan = plan

        return plan

    def assign(
        self,
        state: TaskState,
        model_name: str,
        instruction: str,
        reason: str = "",
    ) -> dict[str, Any]:

        if model_name not in self.providers:
            raise KeyError(
                f"Unknown provider: {model_name}"
            )

        state.add_assignment(
            model=model_name,
            instruction=instruction,
            reason=reason,
        )

        provider = self.providers[model_name]

        response = provider.ask(instruction)

        state.add_result(
            model=model_name,
            instruction=instruction,
            result=response.content,
        )

        state.add_knowledge(
            content=response.content,
            source=model_name,
        )

        return {
            "model": model_name,
            "success": response.success,
            "result": response.content,
        }

    def review(
        self,
        state: TaskState,
        provider_name: str,
    ) -> str:

        provider = self.providers[provider_name]

        knowledge = "\n\n".join(
            item["content"]
            for item in state.knowledge
        )

        assignments = "\n".join(
            str(item)
            for item in state.assignments
        )

        results = "\n\n".join(
            item["result"]
            for item in state.results
        )

        prompt = REVIEW_PROMPT.format(
            task=state.task,
            knowledge=knowledge,
            assignments=assignments,
            results=results,
        )

        response = provider.ask(prompt)

        state.add_message(
            role="assistant",
            content=response.content,
            source=provider_name,
        )

        state.add_knowledge(
            content=response.content,
            source=provider_name,
        )

        return response.content

    def synthesize(
        self,
        state: TaskState,
        provider_name: str,
    ) -> str:

        provider = self.providers[provider_name]

        knowledge = "\n\n".join(
            item["content"]
            for item in state.knowledge
        )

        results = "\n\n".join(
            item["result"]
            for item in state.results
        )

        prompt = SYNTHESIS_PROMPT.format(
            task=state.task,
            knowledge=knowledge,
            results=results,
        )

        response = provider.ask(prompt)

        state.final_result = response.content

        state.add_message(
            role="assistant",
            content=response.content,
            source=provider_name,
        )

        return response.content

    def save_state(
        self,
        state: TaskState,
        name: str = "task.json",
    ) -> Path:

        path = self.storage_dir / name

        path.write_text(
            __import__("json").dumps(
                asdict(state),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return path

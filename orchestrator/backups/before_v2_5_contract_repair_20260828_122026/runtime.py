
"""PROJECT-1 Orchestrator runtime v2.5."""

from typing import Any, Dict, List, Optional

from .planner_context import (
    build_v25_planner_prompt,
)
from .protocol import (
    Assignment,
    ModelExecutionResult,
    PlannerDecision,
)
from .routing import (
    build_zero_model_decision,
    normalize_decision,
)


class OrchestratorRuntime:

    def __init__(
        self,
        planner=None,
        model_registry=None,
        providers=None,
        chatgpt=None,
        max_context_items=12,
    ):
        self.planner = planner
        self.model_registry = model_registry
        self.providers = providers
        self.chatgpt = chatgpt
        self.max_context_items = (
            max_context_items
        )

        self.history = []
        self.planner_calls = 0
        self.steps = 0

    # ------------------------------------------------------------
    # MODELS
    # ------------------------------------------------------------

    def available_models(self):
        registry = self.model_registry

        if registry is None:
            return []

        if hasattr(
            registry,
            "describe",
        ):
            return list(
                registry.describe() or []
            )

        if hasattr(
            registry,
            "list_models",
        ):
            return list(
                registry.list_models() or []
            )

        if isinstance(
            registry,
            dict,
        ):
            return list(
                registry.values()
            )

        return []

    # ------------------------------------------------------------
    # PROMPT
    # ------------------------------------------------------------

    def make_planner_request(
        self,
        task: str,
        history: Optional[List[Dict[str, Any]]] = None,
        previous_answer: str = "",
    ):

        if history is None:
            history = self.history

        return build_v25_planner_prompt(
            task,
            self.available_models(),
            history,
            previous_answer,
        )

    # ------------------------------------------------------------
    # PLANNER
    # ------------------------------------------------------------

    def ask_planner(
        self,
        task: str,
        history: Optional[List[Dict[str, Any]]] = None,
        previous_answer: str = "",
    ):

        if history is None:
            history = self.history

        models = self.available_models()

        if not models:
            return build_zero_model_decision(
                task
            )

        if self.planner is None:
            raise RuntimeError(
                "Planner is required when "
                "models are available."
            )

        prompt = self.make_planner_request(
            task,
            history,
            previous_answer,
        )

        self.planner_calls += 1

        raw = self.planner(
            prompt
        )

        return normalize_decision(
            raw,
            models,
        )

    # ------------------------------------------------------------
    # CHATGPT
    # ------------------------------------------------------------

    def ask_chatgpt(
        self,
        task: str,
    ):

        if self.chatgpt is None:
            return (
                "[CHATGPT STUB]\n"
                f"{task}"
            )

        if callable(self.chatgpt):
            return self.chatgpt(
                task
            )

        if hasattr(
            self.chatgpt,
            "run",
        ):
            return self.chatgpt.run(
                task
            )

        if hasattr(
            self.chatgpt,
            "ask",
        ):
            return self.chatgpt.ask(
                task
            )

        raise TypeError(
            "Invalid ChatGPT provider."
        )

    # ------------------------------------------------------------
    # PROVIDER
    # ------------------------------------------------------------

    def resolve_provider(
        self,
        model_name: str,
    ):

        providers = self.providers

        if providers is None:
            return None

        if hasattr(
            providers,
            "get",
        ):
            return providers.get(
                model_name
            )

        if isinstance(
            providers,
            dict,
        ):
            return providers.get(
                model_name
            )

        return None

    # ------------------------------------------------------------
    # EXECUTE
    # ------------------------------------------------------------

    def execute_assignment(
        self,
        assignment: Assignment,
    ):

        provider = self.resolve_provider(
            assignment.model
        )

        if provider is None:
            return ModelExecutionResult(
                model=assignment.model,
                task=assignment.task,
                status="stub",
                result=(
                    f"[STUB:{assignment.model}] "
                    f"{assignment.task}"
                ),
            )

        if callable(provider):
            result = provider(
                assignment.task
            )

        elif hasattr(
            provider,
            "run",
        ):
            result = provider.run(
                assignment.task
            )

        elif hasattr(
            provider,
            "generate",
        ):
            result = provider.generate(
                assignment.task
            )

        else:
            raise TypeError(
                f"Unsupported provider "
                f"for {assignment.model}"
            )

        return ModelExecutionResult(
            model=assignment.model,
            task=assignment.task,
            status="completed",
            result=str(result),
        )

    # ------------------------------------------------------------
    # HISTORY
    # ------------------------------------------------------------

    def result_to_history(
        self,
        result: ModelExecutionResult,
    ):

        return {
            "type": "model_result",
            "model": result.model,
            "task": result.task,
            "status": result.status,
            "result": result.result,
        }

    # ------------------------------------------------------------
    # STEP
    # ------------------------------------------------------------

    def step(
        self,
        task: str,
        previous_answer: str = "",
    ):

        decision = self.ask_planner(
            task,
            self.history,
            previous_answer,
        )

        self.steps += 1

        if decision.mode == "chatgpt_only":

            result = self.ask_chatgpt(
                decision.chatgpt_task
                or task
            )

            entry = {
                "type": "chatgpt_result",
                "task": (
                    decision.chatgpt_task
                    or task
                ),
                "result": str(result),
            }

            self.history.append(entry)

            return {
                "status": "chatgpt_only",
                "decision": decision,
                "results": [entry],
                "final": str(result),
            }

        if decision.mode == "assignments":

            results = []

            for assignment in (
                decision.assignments
            ):

                result = (
                    self.execute_assignment(
                        assignment
                    )
                )

                self.history.append(
                    self.result_to_history(
                        result
                    )
                )

                results.append(result)

            return {
                "status": "assignments",
                "decision": decision,
                "results": results,
                "final": "",
            }

        if decision.mode == "review":

            review_task = (
                decision.review_task
                or task
            )

            result = self.ask_chatgpt(
                review_task
            )

            entry = {
                "type": "chatgpt_review",
                "task": review_task,
                "result": str(result),
            }

            self.history.append(entry)

            return {
                "status": "review",
                "decision": decision,
                "results": [entry],
                "final": str(result),
            }

        if decision.mode == "finish":

            final = (
                decision.final_answer
                or previous_answer
            )

            return {
                "status": "finish",
                "decision": decision,
                "results": [],
                "final": final,
            }

        raise RuntimeError(
            f"Unhandled planner mode: "
            f"{decision.mode}"
        )

    # ------------------------------------------------------------
    # ITERATIVE RUN
    # ------------------------------------------------------------

    def run(
        self,
        task: str,
        max_steps: int = 8,
    ):

        self.history = []
        self.planner_calls = 0
        self.steps = 0

        previous_answer = ""

        for _ in range(
            max_steps
        ):

            result = self.step(
                task,
                previous_answer,
            )

            if result["final"]:
                return {
                    "status": "completed",
                    "steps": self.steps,
                    "planner_calls": (
                        self.planner_calls
                    ),
                    "history": self.history,
                    "final": result["final"],
                }

            previous_answer = (
                result["final"]
                or previous_answer
            )

            if result["status"] == "chatgpt_only":
                return {
                    "status": "completed",
                    "steps": self.steps,
                    "planner_calls": (
                        self.planner_calls
                    ),
                    "history": self.history,
                    "final": result["final"],
                }

        raise RuntimeError(
            "Maximum orchestration steps exceeded: "
            f"{max_steps}"
        )

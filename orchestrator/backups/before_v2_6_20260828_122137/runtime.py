
"""PROJECT-1 Orchestrator runtime v2.5."""

from typing import Any, Dict, List

from .planner_context import (
    build_human_readable_prompt,
)
from .protocol import (
    ModelExecutionResult,
    PlannerDecision,
)
from .routing import (
    build_zero_model_decision,
    validate_raw_decision,
)


class OrchestratorRuntime:

    def __init__(
        self,
        planner=None,
        model_registry=None,
        providers=None,
        max_context_items=12,
    ):
        self.planner = planner
        self.model_registry = model_registry
        self.providers = providers
        self.max_context_items = max_context_items

    # ------------------------------------------------------------
    # MODELS
    # ------------------------------------------------------------

    def available_models(self) -> List[Dict[str, Any]]:
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

    # ------------------------------------------------------------
    # PLANNER PROMPT
    # ------------------------------------------------------------

    def make_planner_request(
        self,
        task: str,
        history: List[Dict[str, Any]],
    ) -> str:

        return build_human_readable_prompt(
            task,
            self.available_models(),
            history,
        )

    # ------------------------------------------------------------
    # PLANNER
    # ------------------------------------------------------------

    def ask_planner(
        self,
        task: str,
        history: List[Dict[str, Any]],
    ) -> PlannerDecision:

        models = self.available_models()

        # ZERO-MODEL MODE:
        # ChatGPT itself does the work.
        if not models:
            decision = build_zero_model_decision(task)

            decision.raw["task"] = task

            return decision

        if self.planner is None:
            raise RuntimeError(
                "Planner is required when executable "
                "models are registered."
            )

        prompt = self.make_planner_request(
            task,
            history,
        )

        raw = self.planner(prompt)

        if isinstance(raw, PlannerDecision):
            raw_decision = raw.raw
        else:
            raw_decision = raw

        if raw_decision is None:
            raise ValueError(
                "Planner returned no decision."
            )

        raw_decision = dict(raw_decision)

        raw_decision["task"] = task

        return validate_raw_decision(
            raw_decision,
            models,
        )

    # ------------------------------------------------------------
    # PROVIDER
    # ------------------------------------------------------------

    def resolve_provider(self, model_name: str):

        providers = self.providers

        if providers is None:
            return None

        if isinstance(providers, dict):
            return providers.get(model_name)

        if hasattr(providers, "get"):
            return providers.get(model_name)

        return None

    # ------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------

    def execute_assignment(
        self,
        assignment,
    ) -> ModelExecutionResult:

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

        try:

            if callable(provider):
                result = provider(
                    assignment.task
                )

            elif hasattr(provider, "run"):
                result = provider.run(
                    assignment.task
                )

            else:
                raise TypeError(
                    "Provider is neither callable "
                    "nor exposes run()."
                )

            return ModelExecutionResult(
                model=assignment.model,
                task=assignment.task,
                status="completed",
                result=str(result),
            )

        except Exception as exc:

            return ModelExecutionResult(
                model=assignment.model,
                task=assignment.task,
                status="error",
                result=str(exc),
            )

    # ------------------------------------------------------------
    # HISTORY
    # ------------------------------------------------------------

    @staticmethod
    def result_to_history(result):

        return {
            "model": result.model,
            "task": result.task,
            "result": result.result,
            "status": result.status,
        }

    # ------------------------------------------------------------
    # ONE STEP
    # ------------------------------------------------------------

    def step(
        self,
        task: str,
        history=None,
    ):

        if history is None:
            history = []

        decision = self.ask_planner(
            task,
            history,
        )

        # ChatGPT-only branch.
        if decision.mode == "chatgpt_only":
            return {
                "mode": "chatgpt_only",
                "decision": decision,
                "results": [],
                "history": list(history),
                "planner_prompt": self.make_planner_request(
                    task,
                    history,
                ),
                "next_action": "chatgpt_execute",
            }

        results = []

        for assignment in decision.assignments:

            result = self.execute_assignment(
                assignment
            )

            results.append(result)

        new_history = list(history)

        for result in results:
            new_history.append(
                self.result_to_history(result)
            )

        if self.max_context_items > 0:
            new_history = new_history[
                -self.max_context_items:
            ]

        return {
            "mode": decision.mode,
            "decision": decision,
            "results": results,
            "history": new_history,
            "planner_prompt": self.make_planner_request(
                task,
                new_history,
            ),
            "next_action": (
                "review_results"
                if results
                else "chatgpt_execute"
            ),
        }

    # ------------------------------------------------------------
    # RUN
    # ------------------------------------------------------------

    def run(
        self,
        task: str,
        max_steps=10,
    ):

        history = []
        steps = []

        for _ in range(max_steps):

            result = self.step(
                task,
                history,
            )

            steps.append(result)

            history = result.get(
                "history",
                history,
            )

            if result.get(
                "next_action"
            ) == "chatgpt_execute":

                return {
                    "task": task,
                    "steps": steps,
                    "history": history,
                    "mode": result.get(
                        "mode"
                    ),
                    "status": "ready_for_chatgpt",
                }

            if not result.get("results"):
                return {
                    "task": task,
                    "steps": steps,
                    "history": history,
                    "mode": result.get(
                        "mode"
                    ),
                    "status": "complete",
                }

            # Foundation behavior:
            # one model-distribution step followed by review.
            return {
                "task": task,
                "steps": steps,
                "history": history,
                "mode": result.get(
                    "mode"
                ),
                "status": "awaiting_review",
            }

        raise RuntimeError(
            f"Maximum orchestration steps exceeded: "
            f"{max_steps}"
        )

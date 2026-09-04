
"""PROJECT-1 Orchestrator runtime v2.2."""

from typing import Any, Dict, List, Optional

from .planner_context import (
    build_human_readable_prompt,
    build_planner_context,
)
from .protocol import PlannerDecision
from .routing import (
    build_zero_model_decision,
    validate_raw_decision,
)


class OrchestratorRuntime:
    """
    Execution engine.

    ChatGPT is treated as a strategic advisor.
    Local models are workers.
    """

    def __init__(
        self,
        planner=None,
        model_registry=None,
        providers=None,
    ):
        self.planner = planner
        self.model_registry = model_registry
        self.providers = providers

    # ------------------------------------------------------------
    # REGISTRY
    # ------------------------------------------------------------

    def available_models(self) -> List[Dict[str, Any]]:
        registry = self.model_registry

        if registry is None:
            return []

        if hasattr(registry, "describe"):
            result = registry.describe()
            return list(result or [])

        if hasattr(registry, "list_models"):
            result = registry.list_models()
            return list(result or [])

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
    # PLANNER CALL
    # ------------------------------------------------------------

    def ask_planner(
        self,
        task: str,
        history: List[Dict[str, Any]],
    ) -> PlannerDecision:

        models = self.available_models()

        if not models:
            return build_zero_model_decision(
                task,
                history,
            )

        if self.planner is None:
            raise RuntimeError(
                "Planner is required when executable models exist."
            )

        prompt = self.make_planner_request(
            task,
            history,
        )

        raw = self.planner(prompt)

        if isinstance(raw, PlannerDecision):
            return validate_raw_decision(
                raw.raw,
                models,
            )

        if not isinstance(raw, dict):
            raise TypeError(
                "Planner must return a dict or PlannerDecision."
            )

        return validate_raw_decision(
            raw,
            models,
        )

    # ------------------------------------------------------------
    # MODEL EXECUTION
    # ------------------------------------------------------------

    def execute_assignment(
        self,
        assignment,
    ) -> Dict[str, Any]:

        if self.providers is None:
            return {
                "model": assignment.model,
                "task": assignment.task,
                "result": (
                    f"[STUB:{assignment.model}] "
                    f"{assignment.task}"
                ),
            }

        provider = None

        if hasattr(self.providers, "get"):
            provider = self.providers.get(
                assignment.model
            )

        if provider is None:
            return {
                "model": assignment.model,
                "task": assignment.task,
                "result": (
                    f"[STUB:{assignment.model}] "
                    f"{assignment.task}"
                ),
            }

        if callable(provider):
            result = provider(assignment.task)
        elif hasattr(provider, "run"):
            result = provider.run(assignment.task)
        else:
            raise TypeError(
                f"Unsupported provider for "
                f"{assignment.model}"
            )

        return {
            "model": assignment.model,
            "task": assignment.task,
            "result": str(result),
        }

    # ------------------------------------------------------------
    # MAIN STEP
    # ------------------------------------------------------------

    def step(
        self,
        task: str,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:

        history = list(history or [])

        decision = self.ask_planner(
            task,
            history,
        )

        if decision.mode == "finish":
            return {
                "status": "finished",
                "decision": decision,
                "results": [],
            }

        if decision.mode == "chatgpt_only":
            return {
                "status": "chatgpt_only",
                "decision": decision,
                "results": [],
            }

        results = []

        for assignment in decision.assignments:
            results.append(
                self.execute_assignment(
                    assignment
                )
            )

        return {
            "status": "executed",
            "decision": decision,
            "results": results,
        }

    # ------------------------------------------------------------
    # SAFE SMOKE RUN
    # ------------------------------------------------------------

    def run(
        self,
        task: str,
        max_steps: int = 10,
    ) -> Dict[str, Any]:

        history = []
        planner_calls = 0

        for step_number in range(1, max_steps + 1):

            result = self.step(
                task,
                history,
            )

            planner_calls += 1

            status = result["status"]

            if status == "chatgpt_only":
                return {
                    "status": "chatgpt_only",
                    "steps": step_number,
                    "planner_calls": planner_calls,
                    "history": history,
                    "decision": result["decision"],
                    "chatgpt_task": (
                        result["decision"].chatgpt_task
                    ),
                }

            if status == "finished":
                return {
                    "status": "finished",
                    "steps": step_number,
                    "planner_calls": planner_calls,
                    "history": history,
                    "decision": result["decision"],
                }

            for item in result["results"]:
                history.append(item)

            decision = result["decision"]

            if not decision.continue_needed:
                return {
                    "status": "finished",
                    "steps": step_number,
                    "planner_calls": planner_calls,
                    "history": history,
                    "decision": decision,
                }

        raise RuntimeError(
            f"Maximum orchestration steps exceeded: "
            f"{max_steps}"
        )

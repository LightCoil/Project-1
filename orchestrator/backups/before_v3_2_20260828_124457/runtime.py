
"""PROJECT-1 Orchestrator runtime v3.1."""

from typing import Any, Dict, List

from .planner_context import (
    build_human_readable_prompt,
    build_review_prompt,
    build_zero_model_prompt,
)

from .routing import normalize_plan, normalize_review

from .protocol import (
    ExecutionRecord,
)


class OrchestratorRuntime:

    def __init__(
        self,
        planner=None,
        model_registry=None,
        providers=None,
        executor=None,
        max_context_items=12,
    ):

        self.planner = planner
        self.model_registry = model_registry
        self.providers = providers
        self.executor = executor
        self.max_context_items = max_context_items

    # ------------------------------------------------------------
    # MODELS
    # ------------------------------------------------------------

    def available_models(self):
        registry = self.model_registry

        if registry is None:
            return []

        if hasattr(registry, "describe"):
            return list(registry.describe() or [])

        if hasattr(registry, "list_models"):
            return list(registry.list_models() or [])

        if isinstance(registry, dict):
            result = []

            for value in registry.values():
                if isinstance(value, dict):
                    result.append(value)
                else:
                    result.append(
                        {
                            "name": getattr(
                                value,
                                "name",
                                str(value),
                            ),
                            "provider": "local",
                            "capabilities": [],
                        }
                    )

            return result

        return []

    # ------------------------------------------------------------
    # PROMPT
    # ------------------------------------------------------------

    def planner_prompt(
        self,
        task: str,
        history: List[Dict[str, Any]],
    ):

        models = self.available_models()

        if not models:
            return build_zero_model_prompt(
                task,
                history,
            )

        return build_human_readable_prompt(
            task,
            models,
            history,
        )

    # ------------------------------------------------------------
    # PLANNER
    # ------------------------------------------------------------

    def ask_planner(
        self,
        task: str,
        history: List[Dict[str, Any]],
    ):

        models = self.available_models()

        if self.planner is None:
            raise RuntimeError(
                "Planner is required for orchestration."
            )

        prompt = self.planner_prompt(
            task,
            history,
        )

        raw = self.planner(prompt)

        if not isinstance(raw, dict):
            raise ValueError(
                "Planner must return a dictionary."
            )

        return normalize_plan(
            raw,
            models,
        )

    # ------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------

    def execute_assignment(
        self,
        assignment: Dict[str, Any],
    ):

        model = assignment["model"]
        task = assignment["task"]

        if self.executor is None:
            raise RuntimeError(
                "ModelExecutor is required."
            )

        result = self.executor.execute(
            model,
            task,
        )

        if isinstance(result, ExecutionRecord):
            return result

        if isinstance(result, dict):
            return ExecutionRecord(
                model=model,
                task=task,
                status=str(
                    result.get(
                        "status",
                        "completed",
                    )
                ),
                result=str(
                    result.get(
                        "result",
                        "",
                    )
                ),
                metadata=dict(
                    result.get(
                        "metadata",
                        {},
                    )
                ),
            )

        return ExecutionRecord(
            model=model,
            task=task,
            status="completed",
            result=str(result),
            metadata={
                "execution_mode": "provider"
            },
        )

    # ------------------------------------------------------------
    # HISTORY
    # ------------------------------------------------------------

    def result_to_history(self, result):

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

        history = list(history or [])

        decision = self.ask_planner(
            task,
            history,
        )

        action = decision.get(
            "action",
            "finish",
        )

        if action == "finish":
            return {
                "action": "finish",
                "planner_decision": decision,
                "results": [],
                "history": history,
            }

        results = []

        for assignment in decision["assignments"]:

            result = self.execute_assignment(
                assignment
            )

            results.append(result)

            history.append(
                self.result_to_history(result)
            )

            history = history[
                -self.max_context_items:
            ]

        return {
            "action": "execute",
            "planner_decision": decision,
            "results": results,
            "history": history,
        }

    # ------------------------------------------------------------
    # REVIEW
    # ------------------------------------------------------------

    def review(
        self,
        task: str,
        history,
    ):

        models = self.available_models()

        prompt = build_review_prompt(
            task,
            models,
            history,
        )

        if self.planner is None:
            raise RuntimeError(
                "Planner is required for review."
            )

        raw = self.planner(prompt)

        return normalize_review(
            raw,
            models,
        )

    # ------------------------------------------------------------
    # FULL LOOP
    # ------------------------------------------------------------

    def run(
        self,
        task: str,
        max_steps=8,
    ):

        history = []
        planner_calls = 0
        execution_results = []

        for step_index in range(
            max_steps
        ):

            result = self.step(
                task,
                history,
            )

            planner_calls += 1

            history = result["history"]

            execution_results.extend(
                result["results"]
            )

            if result["action"] == "finish":
                return {
                    "status": "completed",
                    "steps": step_index + 1,
                    "planner_calls": planner_calls,
                    "results": execution_results,
                    "history": history,
                    "final_decision": result[
                        "planner_decision"
                    ],
                }

            review = self.review(
                task,
                history,
            )

            planner_calls += 1

            if review["action"] == "finish":
                return {
                    "status": "completed",
                    "steps": step_index + 1,
                    "planner_calls": planner_calls,
                    "results": execution_results,
                    "history": history,
                    "final_decision": review,
                }

        raise RuntimeError(
            f"Maximum orchestration steps exceeded: "
            f"{max_steps}"
        )

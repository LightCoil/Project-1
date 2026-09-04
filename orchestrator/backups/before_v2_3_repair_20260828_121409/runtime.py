
"""PROJECT-1 Orchestrator runtime v2.3."""

from typing import Any, Dict, List, Optional

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
        self.max_context_items = (
            max_context_items
        )

    # ------------------------------------------------------------
    # MODEL REGISTRY
    # ------------------------------------------------------------

    def available_models(
        self
    ) -> List[Dict[str, Any]]:

        registry = self.model_registry

        if registry is None:
            return []

        if hasattr(
            registry,
            "describe",
        ):

            return list(
                registry.describe()
                or []
            )

        if hasattr(
            registry,
            "list_models",
        ):

            return list(
                registry.list_models()
                or []
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

        if not models:

            return build_zero_model_decision(
                task
            )

        if self.planner is None:

            raise RuntimeError(
                "Planner is required when "
                "models are registered."
            )

        prompt = self.make_planner_request(
            task,
            history,
        )

        raw = self.planner(
            prompt
        )

        if isinstance(
            raw,
            PlannerDecision,
        ):

            raw = raw.raw

        return validate_raw_decision(
            raw,
            models,
        )

    # ------------------------------------------------------------
    # MODEL PROVIDER RESOLUTION
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
    # EXECUTE ONE ASSIGNMENT
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

            elif hasattr(
                provider,
                "run",
            ):

                result = provider.run(
                    assignment.task
                )

            else:

                raise TypeError(
                    "Unsupported provider."
                )

            return ModelExecutionResult(
                model=assignment.model,
                task=assignment.task,
                status="completed",
                result=str(
                    result
                ),
            )

        except Exception as exc:

            return ModelExecutionResult(
                model=assignment.model,
                task=assignment.task,
                status="failed",
                error=str(
                    exc
                ),
            )

    # ------------------------------------------------------------
    # SERIALIZE RESULT
    # ------------------------------------------------------------

    @staticmethod
    def result_to_history(
        result: ModelExecutionResult,
    ) -> Dict[str, Any]:

        return {
            "model": result.model,
            "task": result.task,
            "status": result.status,
            "result": result.result,
            "error": result.error,
        }

    # ------------------------------------------------------------
    # SINGLE ORCHESTRATION STEP
    # ------------------------------------------------------------

    def step(
        self,
        task: str,
        history: Optional[
            List[Dict[str, Any]]
        ] = None,
    ) -> Dict[str, Any]:

        history = list(
            history or []
        )

        decision = self.ask_planner(
            task,
            history,
        )

        if decision.mode == "chatgpt_only":

            return {
                "status": "chatgpt_only",
                "decision": decision,
                "results": [],
            }

        if decision.mode == "finish":

            return {
                "status": "finished",
                "decision": decision,
                "results": [],
            }

        results = []

        for assignment in (
            decision.assignments
        ):

            result = (
                self.execute_assignment(
                    assignment
                )
            )

            results.append(
                result
            )

        return {
            "status": "executed",
            "decision": decision,
            "results": results,
        }

    # ------------------------------------------------------------
    # FULL ORCHESTRATION LOOP
    # ------------------------------------------------------------

    def run(
        self,
        task: str,
        max_steps: int = 10,
    ) -> Dict[str, Any]:

        history = []
        planner_calls = 0

        for step_number in range(
            1,
            max_steps + 1,
        ):

            result = self.step(
                task,
                history,
            )

            planner_calls += 1

            status = result[
                "status"
            ]

            decision = result[
                "decision"
            ]

            if status == "chatgpt_only":

                return {
                    "status": "chatgpt_only",
                    "steps": step_number,
                    "planner_calls": planner_calls,
                    "history": history,
                    "decision": decision,
                    "chatgpt_task": (
                        decision.chatgpt_task
                    ),
                }

            if status == "finished":

                return {
                    "status": "finished",
                    "steps": step_number,
                    "planner_calls": planner_calls,
                    "history": history,
                    "decision": decision,
                }

            for execution in (
                result["results"]
            ):

                history.append(
                    self.result_to_history(
                        execution
                    )
                )

            if not decision.continue_needed:

                return {
                    "status": "finished",
                    "steps": step_number,
                    "planner_calls": planner_calls,
                    "history": history,
                    "decision": decision,
                }

        raise RuntimeError(
            "Maximum orchestration steps "
            f"exceeded: {max_steps}"
        )

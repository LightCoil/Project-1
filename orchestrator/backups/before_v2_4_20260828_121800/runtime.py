
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


# ================================================================
# PROJECT1_V23_ZERO_MODEL_FALLBACK
# ================================================================

def _project1_v23_executable_models(self):
    """
    Return only models that can actually be executed.

    Registry entries that merely describe capabilities are not
    considered executable unless their provider exposes an
    execution path.
    """
    registry = getattr(self, "model_registry", None)

    if registry is None:
        registry = getattr(self, "registry", None)

    if registry is None:
        return []

    try:
        if hasattr(registry, "list_executable_models"):
            return list(registry.list_executable_models())
    except Exception:
        pass

    try:
        if hasattr(registry, "executable_models"):
            value = registry.executable_models
            return list(value() if callable(value) else value)
    except Exception:
        pass

    try:
        if hasattr(registry, "list_models"):
            models = list(registry.list_models())
            result = []

            for model in models:
                executable = getattr(model, "executable", None)

                if executable is False:
                    continue

                provider = getattr(model, "provider", None)

                if provider is None:
                    continue

                result.append(model)

            return result
    except Exception:
        pass

    return []


def _project1_v23_force_chatgpt_only(self, task, reason):
    """
    Construct a deterministic ChatGPT-only continuation.

    This method does not perform an external request itself.
    The actual provider invocation remains under the existing
    provider abstraction.
    """

    return {
        "mode": "chatgpt_only",
        "reason": reason,
        "task": task,
        "assignments": [],
        "requires_external_planner": True,
        "instruction": (
            "Дополнительных исполняемых моделей нет. "
            "Выполни необходимую работу сам. "
            "Не пытайся распределять задачу между отсутствующими моделями."
        ),
    }


def _project1_v23_validate_plan(self, task, plan):
    """
    Validate planner routing against the currently executable
    model set.

    If there are no executable models, distribution is converted
    into an explicit ChatGPT-only route.
    """

    models = _project1_v23_executable_models(self)

    if not models:
        return _project1_v23_force_chatgpt_only(
            self,
            task,
            "No executable local/external models are currently available."
        )

    assignments = []

    raw_assignments = []

    if isinstance(plan, dict):
        raw_assignments = (
            plan.get("assignments")
            or plan.get("model_assignments")
            or plan.get("distribution")
            or []
        )

    available_names = set()

    for model in models:
        if isinstance(model, dict):
            name = model.get("name")
        else:
            name = getattr(model, "name", None)

        if name:
            available_names.add(name)

    for item in raw_assignments:
        if not isinstance(item, dict):
            continue

        model_name = (
            item.get("model")
            or item.get("model_name")
            or item.get("name")
        )

        if model_name not in available_names:
            continue

        assignments.append(item)

    validated = dict(plan) if isinstance(plan, dict) else {}

    validated["assignments"] = assignments
    validated["available_executable_models"] = sorted(
        available_names
    )

    return validated


# Attach helpers without replacing the existing orchestration loop.
try:
    Runtime
except NameError:
    Runtime = None

if Runtime is not None:
    Runtime._project1_v23_executable_models = (
        _project1_v23_executable_models
    )
    Runtime._project1_v23_force_chatgpt_only = (
        _project1_v23_force_chatgpt_only
    )
    Runtime._project1_v23_validate_plan = (
        _project1_v23_validate_plan
    )

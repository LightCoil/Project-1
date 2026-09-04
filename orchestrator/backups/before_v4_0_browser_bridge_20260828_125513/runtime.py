
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

    def available_models(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Return executable models visible to the runtime.

        Visibility is normalized across Registry, Executor,
        and provider storage.

        The runtime must never report zero models when the
        attached executor has an executable provider.
        """

        # --------------------------------------------------------
        # 1. Executor is the primary execution authority.
        # --------------------------------------------------------

        executor = getattr(
            self,
            "executor",
            None,
        )

        if executor is not None:

            # Try public executor APIs.
            for method_name in [
                "available_models",
                "models",
                "list_models",
                "names",
            ]:

                method = getattr(
                    executor,
                    method_name,
                    None,
                )

                if callable(method):

                    try:
                        values = list(
                            method()
                            or []
                        )

                    except Exception:
                        values = []

                    if values:

                        normalized = []

                        for item in values:

                            if isinstance(
                                item,
                                dict,
                            ):
                                normalized.append(
                                    dict(item)
                                )

                            else:
                                normalized.append(
                                    {
                                        "name": str(item),
                                        "provider": (
                                            "local_api"
                                        ),
                                        "executable": True,
                                    }
                                )

                        if normalized:
                            return normalized

        # --------------------------------------------------------
        # 2. Registry fallback.
        # --------------------------------------------------------

        registry = getattr(
            self,
            "model_registry",
            None,
        )

        if registry is not None:

            for method_name in [
                "describe_for_planner",
                "describe",
                "all",
                "list_models",
            ]:

                method = getattr(
                    registry,
                    method_name,
                    None,
                )

                if callable(method):

                    try:
                        values = list(
                            method()
                            or []
                        )

                    except Exception:
                        values = []

                    if values:

                        normalized = []

                        for item in values:

                            if isinstance(
                                item,
                                dict,
                            ):
                                normalized.append(
                                    dict(item)
                                )

                            else:
                                name = getattr(
                                    item,
                                    "name",
                                    str(item),
                                )

                                normalized.append(
                                    {
                                        "name": name,
                                        "provider": (
                                            getattr(
                                                item,
                                                "provider",
                                                "local",
                                            )
                                        ),
                                        "executable": (
                                            getattr(
                                                item,
                                                "executable",
                                                True,
                                            )
                                        ),
                                    }
                                )

                        if normalized:
                            return normalized

            # Direct registry storage fallback.
            models = getattr(
                registry,
                "_models",
                None,
            )

            if isinstance(
                models,
                dict,
            ):

                result = []

                for name, value in models.items():

                    if isinstance(
                        value,
                        dict,
                    ):
                        item = dict(value)
                        item.setdefault(
                            "name",
                            name,
                        )
                        item.setdefault(
                            "executable",
                            True,
                        )
                        result.append(item)

                    else:
                        result.append(
                            {
                                "name": str(name),
                                "provider": "local",
                                "executable": True,
                            }
                        )

                if result:
                    return result

        # --------------------------------------------------------
        # 3. Provider-map fallback.
        # --------------------------------------------------------

        providers = getattr(
            self,
            "providers",
            None,
        )

        if isinstance(
            providers,
            dict,
        ):

            result = []

            for name, provider in providers.items():

                if provider is None:
                    continue

                result.append(
                    {
                        "name": str(name),
                        "provider": "local_api",
                        "executable": True,
                    }
                )

            if result:
                return result

        return []
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
        assignment,
    ):
        """
        Execute one model assignment.

        Assignment compatibility:
          1. mapping/dict:
             {"model": "...", "task": "..."}

          2. object:
             assignment.model
             assignment.task

        The runtime normalizes both representations before
        delegating execution to ModelExecutor.
        """

        # --------------------------------------------------------
        # Normalize assignment
        # --------------------------------------------------------

        if isinstance(assignment, dict):
            model_name = assignment.get("model")
            task = assignment.get("task")

        else:
            model_name = getattr(
                assignment,
                "model",
                None,
            )

            task = getattr(
                assignment,
                "task",
                None,
            )

        if not model_name:
            raise ValueError(
                "Assignment is missing required model."
            )

        if task is None:
            raise ValueError(
                "Assignment is missing required task."
            )

        # --------------------------------------------------------
        # Executor boundary
        # --------------------------------------------------------

        executor = getattr(
            self,
            "executor",
            None,
        )

        if executor is not None:
            return executor.execute(
                model_name,
                task,
            )

        # --------------------------------------------------------
        # Legacy provider fallback
        # --------------------------------------------------------

        provider = self.resolve_provider(
            model_name
        )

        if provider is None:
            return ModelExecutionResult(
                model=model_name,
                task=task,
                status="stub",
                result=(
                    f"[STUB:{model_name}] "
                    f"{task}"
                ),
            )

        try:

            if callable(provider):
                result = provider(task)

            elif hasattr(provider, "run"):
                result = provider.run(task)

            elif hasattr(provider, "generate"):
                result = provider.generate(task)

            else:
                raise TypeError(
                    "Provider is neither callable nor "
                    "supports run()/generate()."
                )

            return ModelExecutionResult(
                model=model_name,
                task=task,
                status="completed",
                result=str(result),
            )

        except Exception as exc:

            return ModelExecutionResult(
                model=model_name,
                task=task,
                status="error",
                result=str(exc),
            )
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

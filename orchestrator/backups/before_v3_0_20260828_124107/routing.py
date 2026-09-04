
"""PROJECT-1 orchestration routing."""

from typing import Any, Dict, List

from .protocol import PlannerDecision


def build_zero_model_decision(task: str) -> PlannerDecision:
    """Create a ChatGPT-only decision."""

    return PlannerDecision(
        mode="chatgpt_only",
        assignments=[],
        raw={
            "mode": "chatgpt_only",
            "assignments": [],
            "instruction": (
                "Дополнительных моделей нет. "
                "Выполни необходимую работу сам."
            ),
        },
    )


def validate_raw_decision(
    raw: Any,
    available_models: List[Dict[str, Any]],
) -> PlannerDecision:
    """Validate planner output against available models."""

    if isinstance(raw, PlannerDecision):
        decision = raw
    else:
        data = dict(raw or {})

        decision = PlannerDecision(
            mode=data.get("mode", "distributed"),
            assignments=data.get("assignments", []),
            raw=data,
        )

    available = {
        item.get("name")
        for item in available_models
        if item.get("name")
    }

    if not available:
        return build_zero_model_decision(
            decision.raw.get("task", "")
        )

    for assignment in decision.assignments:
        model_name = getattr(
            assignment,
            "model",
            None,
        )

        if model_name not in available:
            raise ValueError(
                f"unavailable model selected: {model_name}"
            )

    return decision

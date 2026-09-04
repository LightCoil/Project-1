
"""PROJECT-1 Orchestrator routing v2.4."""

from typing import Any, Dict, List


def _name(model: Any) -> str:
    if isinstance(model, dict):
        return str(
            model.get("name")
            or model.get("model")
            or ""
        )

    return str(
        getattr(model, "name", "")
        or getattr(model, "model", "")
        or ""
    )


def executable_model_names(
    models: List[Any],
) -> List[str]:

    names = []

    for model in models:
        name = _name(model)

        if name:
            names.append(name)

    return names


def build_zero_model_decision(
    task: str,
) -> Dict[str, Any]:

    return {
        "mode": "chatgpt_only",
        "assignments": [],
        "final_action": "execute_directly",
        "reason": (
            "No executable models are available."
        ),
        "task": str(task),
    }


def validate_raw_decision(
    raw: Any,
    available_models: List[Any],
) -> Dict[str, Any]:

    allowed = set(
        executable_model_names(
            available_models
        )
    )

    if raw is None:
        raw = {}

    if not isinstance(raw, dict):
        raw = {
            "mode": "chatgpt_only",
            "assignments": [],
            "final_action": "execute_directly",
            "reason": "Planner returned no structured plan.",
        }

    assignments = raw.get(
        "assignments",
        [],
    )

    if assignments is None:
        assignments = []

    if not isinstance(assignments, list):
        assignments = []

    normalized = []

    for item in assignments:

        if not isinstance(item, dict):
            continue

        model = str(
            item.get("model")
            or ""
        ).strip()

        task = str(
            item.get("task")
            or ""
        ).strip()

        if not model or not task:
            continue

        if model not in allowed:
            raise ValueError(
                "Planner selected unavailable model: "
                f"{model}"
            )

        normalized.append({
            "model": model,
            "task": task,
            "expected_output": str(
                item.get("expected_output")
                or ""
            ),
        })

    if not available_models:
        return build_zero_model_decision(
            str(raw.get("task") or "")
        )

    return {
        "mode": (
            "distributed"
            if normalized
            else "chatgpt_only"
        ),
        "assignments": normalized,
        "final_action": str(
            raw.get("final_action")
            or (
                "execute_models"
                if normalized
                else "execute_directly"
            )
        ),
        "reason": str(
            raw.get("reason")
            or ""
        ),
    }

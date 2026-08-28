
"""PROJECT-1 routing v3.1."""

from typing import Any, Dict, List


def _names(models: List[Dict[str, Any]]) -> set:
    return {
        str(model.get("name"))
        for model in models
        if model.get("name")
    }


def normalize_plan(
    raw: Dict[str, Any],
    models: List[Dict[str, Any]],
) -> Dict[str, Any]:

    if not isinstance(raw, dict):
        raise ValueError("Planner response must be a dictionary.")

    available = _names(models)

    action = str(
        raw.get("action", raw.get("mode", "finish"))
    ).lower()

    if action in {
        "finish",
        "finished",
        "done",
        "complete",
    }:
        return {
            "action": "finish",
            "assignments": [],
            "instruction": str(
                raw.get("instruction", "")
            ),
        }

    assignments = raw.get("assignments", [])

    if not isinstance(assignments, list):
        raise ValueError(
            "Planner assignments must be a list."
        )

    normalized = []

    for item in assignments:
        if not isinstance(item, dict):
            raise ValueError(
                "Each planner assignment must be an object."
            )

        model = item.get("model")
        task = item.get("task")

        if not model or not task:
            raise ValueError(
                "Every assignment requires model and task."
            )

        if model not in available:
            raise ValueError(
                f"Planner selected unavailable model: {model}"
            )

        normalized.append(
            {
                "model": str(model),
                "task": str(task),
            }
        )

    if not normalized:
        return {
            "action": "finish",
            "assignments": [],
            "instruction": str(
                raw.get("instruction", "")
            ),
        }

    return {
        "action": "execute",
        "assignments": normalized,
        "instruction": str(
            raw.get("instruction", "")
        ),
    }


def normalize_review(
    raw: Dict[str, Any],
    models: List[Dict[str, Any]],
) -> Dict[str, Any]:

    return normalize_plan(raw, models)

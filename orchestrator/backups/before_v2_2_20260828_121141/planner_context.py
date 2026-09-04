
"""Context supplied to the strategic planner."""

from typing import Any


def build_planner_context(
    *,
    task: str,
    available_models: list[dict[str, Any]],
    history: list[dict[str, Any]],
    phase: str,
) -> dict[str, Any]:

    return {
        "protocol_version": "2.1",
        "phase": phase,
        "user_task": task,

        "available_models": available_models,

        "execution_history": history,

        "planner_instruction": (
            "Choose only models from available_models. "
            "Distribute subtasks according to capabilities. "
            "Do not assume unavailable models exist. "
            "When the available evidence is sufficient, "
            "request final synthesis instead of creating "
            "unnecessary additional work."
        ),
    }


"""Routing rules for PROJECT-1 Orchestrator v2.2."""

from typing import Any, Dict, List

from .protocol import PlannerDecision, normalize_planner_decision


def validate_assignments(
    decision: PlannerDecision,
    available_models: List[Dict[str, Any]],
) -> PlannerDecision:

    registry = {
        str(model.get("name", "")): model
        for model in available_models
    }

    if decision.mode == "chatgpt_only":
        return decision

    if decision.mode == "finish":
        return decision

    if not registry:
        raise ValueError(
            "Planner attempted model distribution while "
            "no models are available."
        )

    valid = []

    for assignment in decision.assignments:
        if assignment.model not in registry:
            raise ValueError(
                "Planner selected unavailable model: "
                f"{assignment.model}"
            )

        valid.append(assignment)

    decision.assignments = valid

    if not decision.assignments:
        raise ValueError(
            "Planner selected distribute mode "
            "but produced no valid assignments."
        )

    return decision


def validate_raw_decision(
    raw: Dict[str, Any],
    available_models: List[Dict[str, Any]],
) -> PlannerDecision:

    decision = normalize_planner_decision(raw)

    return validate_assignments(
        decision,
        available_models,
    )


def build_zero_model_decision(
    user_task: str,
    history: List[Dict[str, Any]],
) -> PlannerDecision:

    return PlannerDecision(
        mode="chatgpt_only",
        chatgpt_task=(
            "Выполни задачу самостоятельно. "
            "Дополнительных моделей нет.\n\n"
            f"Задача пользователя:\n{user_task}"
        ),
        continue_needed=False,
        reason=(
            "No executable models are available; "
            "model distribution would be unnecessary."
        ),
    )

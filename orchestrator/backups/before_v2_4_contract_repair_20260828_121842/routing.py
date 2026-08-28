
"""Routing and model availability rules."""

from typing import Any, Dict, List

from .protocol import (
    PlannerDecision,
    normalize_planner_decision,
)


def model_name_map(
    models: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:

    return {
        str(
            model.get("name", "")
        ): model
        for model in models or []
    }


def executable_models(
    models: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    result = []

    for model in models or []:

        availability = str(
            model.get(
                "availability",
                "unknown"
            )
        ).lower()

        if availability in {
            "available",
            "ready",
            "online",
        }:

            result.append(model)

    return result


def validate_assignments(
    decision: PlannerDecision,
    available_models: List[Dict[str, Any]],
) -> PlannerDecision:

    registry = model_name_map(
        available_models
    )

    executable = {
        model["name"]
        for model in executable_models(
            available_models
        )
    }

    if decision.mode == "chatgpt_only":
        return decision

    if decision.mode == "finish":
        return decision

    if not executable:

        raise ValueError(
            "Planner selected model distribution, "
            "but no executable models are available."
        )

    valid = []

    for assignment in decision.assignments:

        if assignment.model not in registry:

            raise ValueError(
                "Planner selected unknown model: "
                f"{assignment.model}"
            )

        if assignment.model not in executable:

            raise ValueError(
                "Planner selected unavailable model: "
                f"{assignment.model}"
            )

        valid.append(
            assignment
        )

    if not valid:

        raise ValueError(
            "Distribution mode requires "
            "at least one valid assignment."
        )

    decision.assignments = valid

    return decision


def validate_raw_decision(
    raw: Dict[str, Any],
    available_models: List[Dict[str, Any]],
) -> PlannerDecision:

    decision = normalize_planner_decision(
        raw
    )

    return validate_assignments(
        decision,
        available_models,
    )


def build_zero_model_decision(
    user_task: str,
) -> PlannerDecision:

    return PlannerDecision(
        mode="chatgpt_only",
        chatgpt_task=(
            "Выполни задачу самостоятельно.\n\n"
            "Дополнительных моделей нет.\n\n"
            f"Задача пользователя:\n"
            f"{user_task}"
        ),
        continue_needed=False,
        reason=(
            "No executable models are available."
        ),
    )

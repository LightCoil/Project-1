
"""PROJECT-1 routing and planner decision normalization v2.5."""

from typing import Any, Dict, List

from .protocol import (
    Assignment,
    PlannerDecision,
)


VALID_MODES = {
    "assignments",
    "chatgpt_only",
    "review",
    "finish",
}


def build_zero_model_decision(
    task: str,
) -> PlannerDecision:

    return PlannerDecision(
        mode="chatgpt_only",
        assignments=[],
        chatgpt_task=(
            "Выполни необходимую работу самостоятельно "
            "по пользовательской задаче."
        ),
        rationale=(
            "Исполняемых дополнительных моделей нет."
        ),
    )


def normalize_decision(
    raw: Any,
    available_models: List[Dict[str, Any]],
) -> PlannerDecision:

    if isinstance(raw, PlannerDecision):
        return raw

    if not isinstance(raw, dict):
        raise ValueError(
            "Planner must return a dictionary."
        )

    mode = str(
        raw.get("mode", "")
    ).strip()

    if mode not in VALID_MODES:
        raise ValueError(
            f"Invalid planner mode: {mode!r}"
        )

    known_models = {
        str(item.get("name"))
        for item in available_models
    }

    assignments = []

    for item in raw.get(
        "assignments",
        [],
    ) or []:

        assignment = Assignment.from_dict(
            item
        )

        if not assignment.model:
            raise ValueError(
                "Planner produced an assignment "
                "without a model."
            )

        if assignment.model not in known_models:
            raise ValueError(
                "Planner selected unavailable model: "
                f"{assignment.model}"
            )

        if not assignment.task:
            raise ValueError(
                "Planner produced an assignment "
                "without a task."
            )

        assignments.append(
            assignment
        )

    if not available_models:

        if mode == "assignments":
            return build_zero_model_decision(
                str(raw.get("chatgpt_task") or "")
            )

        if assignments:
            return build_zero_model_decision(
                str(raw.get("chatgpt_task") or "")
            )

        if mode not in {
            "chatgpt_only",
            "finish",
            "review",
        }:
            return build_zero_model_decision(
                str(raw.get("chatgpt_task") or "")
            )

    if mode == "assignments" and not assignments:
        raise ValueError(
            "Planner selected assignments mode "
            "but produced no assignments."
        )

    return PlannerDecision(
        mode=mode,
        assignments=assignments,
        chatgpt_task=str(
            raw.get("chatgpt_task", "")
        ),
        review_task=str(
            raw.get("review_task", "")
        ),
        final_answer=str(
            raw.get("final_answer", "")
        ),
        rationale=str(
            raw.get("rationale", "")
        ),
        raw=raw,
    )


def validate_raw_decision(
    raw: Any,
    available_models: List[Dict[str, Any]],
):
    return normalize_decision(
        raw,
        available_models,
    )

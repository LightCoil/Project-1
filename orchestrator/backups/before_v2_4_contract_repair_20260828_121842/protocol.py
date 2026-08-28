
"""PROJECT-1 Orchestrator protocol v2.3."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ModelAssignment:
    model: str
    task: str
    expected_output: str = ""


@dataclass
class PlannerDecision:
    mode: str
    assignments: List[ModelAssignment] = field(default_factory=list)
    chatgpt_task: str = ""
    continue_needed: bool = False
    reason: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelExecutionResult:
    model: str
    task: str
    status: str
    result: str = ""
    error: str = ""


def normalize_planner_decision(
    data: Dict[str, Any]
) -> PlannerDecision:

    if not isinstance(data, dict):
        raise TypeError(
            "Planner response must be a dictionary."
        )

    mode = str(
        data.get("mode", "")
    ).strip().lower()

    if mode not in {
        "distribute",
        "chatgpt_only",
        "finish",
    }:
        raise ValueError(
            f"Unsupported planner mode: {mode!r}"
        )

    assignments = []

    for item in data.get(
        "assignments",
        []
    ) or []:

        if not isinstance(item, dict):
            continue

        model = str(
            item.get("model", "")
        ).strip()

        task = str(
            item.get("task", "")
        ).strip()

        if not model or not task:
            continue

        assignments.append(
            ModelAssignment(
                model=model,
                task=task,
                expected_output=str(
                    item.get(
                        "expected_output",
                        ""
                    )
                ).strip(),
            )
        )

    return PlannerDecision(
        mode=mode,
        assignments=assignments,
        chatgpt_task=str(
            data.get(
                "chatgpt_task",
                ""
            )
        ).strip(),
        continue_needed=bool(
            data.get(
                "continue_needed",
                False
            )
        ),
        reason=str(
            data.get(
                "reason",
                ""
            )
        ).strip(),
        raw=data,
    )

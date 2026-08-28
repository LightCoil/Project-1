
"""PROJECT-1 task routing protocol."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskAssignment:

    task: str
    model: str
    priority: int = 0
    expected_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "model": self.model,
            "priority": self.priority,
            "expected_output": self.expected_output,
        }


@dataclass
class ExecutionPlan:

    assignments: list[TaskAssignment] = field(
        default_factory=list
    )
    rationale: str = ""

    def validate(
        self,
        available_models: set[str],
    ) -> None:

        for assignment in self.assignments:

            if assignment.model not in available_models:
                raise ValueError(
                    "Planner selected unavailable model: "
                    f"{assignment.model}"
                )

            if not assignment.task.strip():
                raise ValueError(
                    "Task assignment cannot be empty."
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignments": [
                item.to_dict()
                for item in self.assignments
            ],
            "rationale": self.rationale,
        }


def parse_execution_plan(
    data: dict[str, Any],
    available_models: set[str],
) -> ExecutionPlan:

    assignments = []

    for item in data.get("assignments", []):

        assignment = TaskAssignment(
            task=str(item.get("task", "")).strip(),
            model=str(item.get("model", "")).strip(),
            priority=int(item.get("priority", 0)),
            expected_output=str(
                item.get("expected_output", "")
            ),
        )

        assignments.append(assignment)

    plan = ExecutionPlan(
        assignments=assignments,
        rationale=str(
            data.get("rationale", "")
        ),
    )

    plan.validate(available_models)

    return plan

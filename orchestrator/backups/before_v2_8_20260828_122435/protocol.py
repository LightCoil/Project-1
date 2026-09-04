
"""PROJECT-1 Orchestrator protocol v2.5."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelExecutionResult:
    model: str
    task: str
    status: str
    result: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Assignment:
    model: str
    task: str
    expected_output: str = ""
    priority: str = "normal"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            model=str(data.get("model", "")),
            task=str(data.get("task", "")),
            expected_output=str(
                data.get("expected_output", "")
            ),
            priority=str(
                data.get("priority", "normal")
            ),
        )

    def to_dict(self):
        return {
            "model": self.model,
            "task": self.task,
            "expected_output": self.expected_output,
            "priority": self.priority,
        }


@dataclass
class PlannerDecision:
    mode: str
    assignments: List[Assignment] = field(
        default_factory=list
    )
    chatgpt_task: str = ""
    review_task: str = ""
    final_answer: str = ""
    rationale: str = ""
    raw: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self):
        return {
            "mode": self.mode,
            "assignments": [
                item.to_dict()
                for item in self.assignments
            ],
            "chatgpt_task": self.chatgpt_task,
            "review_task": self.review_task,
            "final_answer": self.final_answer,
            "rationale": self.rationale,
        }

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TaskState:
    """
    Persistent state of one orchestration task.
    """

    task: str
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    plan: dict[str, Any] | None = None

    knowledge: list[dict[str, Any]] = field(
        default_factory=list
    )

    assignments: list[dict[str, Any]] = field(
        default_factory=list
    )

    results: list[dict[str, Any]] = field(
        default_factory=list
    )

    messages: list[dict[str, Any]] = field(
        default_factory=list
    )

    final_result: str | None = None

    def add_message(
        self,
        role: str,
        content: str,
        source: str = "unknown",
    ) -> None:
        self.messages.append(
            {
                "role": role,
                "content": content,
                "source": source,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_knowledge(
        self,
        content: str,
        source: str,
    ) -> None:
        self.knowledge.append(
            {
                "content": content,
                "source": source,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_assignment(
        self,
        model: str,
        instruction: str,
        reason: str = "",
    ) -> None:
        self.assignments.append(
            {
                "model": model,
                "instruction": instruction,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_result(
        self,
        model: str,
        instruction: str,
        result: str,
    ) -> None:
        self.results.append(
            {
                "model": model,
                "instruction": instruction,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
        )

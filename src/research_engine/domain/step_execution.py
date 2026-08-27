from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from research_engine.domain.enums import StepStatus
from research_engine.domain.ids import new_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class StepExecution:
    id: str
    research_id: str
    workflow_step_id: str
    status: StepStatus = StepStatus.PENDING
    worker_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    input_snapshot: dict[str, Any] = field(default_factory=dict)
    output_artifact_id: str | None = None
    error: str | None = None

    @classmethod
    def create(cls, *, research_id: str, workflow_step_id: str) -> StepExecution:
        return cls(
            id=new_id("exec"),
            research_id=research_id,
            workflow_step_id=workflow_step_id,
        )

    def start(self, worker_id: str, input_snapshot: dict[str, Any]) -> None:
        self.status = StepStatus.RUNNING
        self.worker_id = worker_id
        self.input_snapshot = input_snapshot
        self.started_at = _now()
        self.error = None

    def complete(self, output_artifact_id: str) -> None:
        self.status = StepStatus.COMPLETED
        self.output_artifact_id = output_artifact_id
        self.completed_at = _now()
        self.error = None

    def fail(self, message: str) -> None:
        self.status = StepStatus.FAILED
        self.error = message
        self.completed_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "research_id": self.research_id,
            "workflow_step_id": self.workflow_step_id,
            "status": self.status.value,
            "worker_id": self.worker_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "input_snapshot": dict(self.input_snapshot),
            "output_artifact_id": self.output_artifact_id,
            "error": self.error,
        }

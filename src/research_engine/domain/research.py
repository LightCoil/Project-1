from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from research_engine.domain.enums import ResearchStatus
from research_engine.domain.ids import new_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Research:
    id: str
    experiment_id: str
    number: int
    status: ResearchStatus = ResearchStatus.PENDING
    current_step: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    final_artifact_id: str | None = None
    error: str | None = None

    @classmethod
    def create(cls, *, experiment_id: str, number: int) -> Research:
        if number < 1:
            raise ValueError("research number must be at least 1")
        return cls(
            id=new_id("res"),
            experiment_id=experiment_id,
            number=number,
        )

    def start(self, step_name: str) -> None:
        now = _now()
        if self.started_at is None:
            self.started_at = now
        self.status = ResearchStatus.RUNNING
        self.current_step = step_name
        self.error = None

    def fail(self, message: str) -> None:
        self.status = ResearchStatus.FAILED
        self.error = message

    def interrupt(self) -> None:
        if self.status == ResearchStatus.RUNNING:
            self.status = ResearchStatus.INTERRUPTED

    def complete(self, final_artifact_id: str) -> None:
        self.status = ResearchStatus.COMPLETED
        self.final_artifact_id = final_artifact_id
        self.completed_at = _now()
        self.error = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "number": self.number,
            "status": self.status.value,
            "current_step": self.current_step,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "final_artifact_id": self.final_artifact_id,
            "error": self.error,
        }

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from research_engine.domain.enums import ExperimentStatus
from research_engine.domain.ids import new_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Experiment:
    id: str
    name: str
    objective: str
    workflow_id: str
    research_count: int
    status: ExperimentStatus = ExperimentStatus.DRAFT
    description: str | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        *,
        name: str,
        objective: str,
        workflow_id: str,
        research_count: int,
        description: str | None = None,
    ) -> Experiment:
        if research_count < 1:
            raise ValueError("research_count must be at least 1")
        stamp = _now()
        return cls(
            id=new_id("exp"),
            name=name,
            description=description,
            objective=objective,
            workflow_id=workflow_id,
            research_count=research_count,
            status=ExperimentStatus.DRAFT,
            created_at=stamp,
            updated_at=stamp,
        )

    def mark_queued(self) -> None:
        self.status = ExperimentStatus.QUEUED
        self.updated_at = _now()

    def mark_running(self) -> None:
        self.status = ExperimentStatus.RUNNING
        self.updated_at = _now()

    def mark_completed(self) -> None:
        self.status = ExperimentStatus.COMPLETED
        self.updated_at = _now()

    def mark_failed(self) -> None:
        self.status = ExperimentStatus.FAILED
        self.updated_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "objective": self.objective,
            "workflow_id": self.workflow_id,
            "research_count": self.research_count,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

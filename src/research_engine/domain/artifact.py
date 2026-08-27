from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from research_engine.domain.enums import ArtifactType
from research_engine.domain.ids import new_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Artifact:
    id: str
    research_id: str
    step_execution_id: str
    type: ArtifactType
    content: str
    created_at: datetime = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        research_id: str,
        step_execution_id: str,
        type: ArtifactType,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        return cls(
            id=new_id("art"),
            research_id=research_id,
            step_execution_id=step_execution_id,
            type=type,
            content=content,
            metadata=metadata or {},
        )

    def to_dict(self, *, include_content: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "research_id": self.research_id,
            "step_execution_id": self.step_execution_id,
            "type": self.type.value,
            "created_at": self.created_at.isoformat(),
            "metadata": dict(self.metadata),
        }
        if include_content:
            data["content"] = self.content
        return data

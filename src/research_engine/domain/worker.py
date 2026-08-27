from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from research_engine.domain.enums import WorkerRole, WorkerStatus
from research_engine.domain.ids import new_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Worker:
    id: str
    name: str
    role: WorkerRole
    provider: str
    model: str
    endpoint: str
    status: WorkerStatus = WorkerStatus.ONLINE
    capabilities: list[str] = field(default_factory=list)
    last_seen: datetime = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        *,
        name: str,
        role: WorkerRole,
        model: str,
        endpoint: str = "fake://local",
        provider: str = "openai-compatible",
        capabilities: list[str] | None = None,
    ) -> Worker:
        return cls(
            id=new_id("worker"),
            name=name,
            role=role,
            provider=provider,
            model=model,
            endpoint=endpoint,
            capabilities=capabilities or [role.value],
        )

    def is_free(self) -> bool:
        return self.status == WorkerStatus.ONLINE

    def can_run(self, role: WorkerRole) -> bool:
        return self.is_free() and (self.role == role or role.value in self.capabilities)

    def mark_busy(self) -> None:
        self.status = WorkerStatus.BUSY
        self.last_seen = _now()

    def mark_online(self) -> None:
        self.status = WorkerStatus.ONLINE
        self.last_seen = _now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "provider": self.provider,
            "model": self.model,
            "endpoint": self.endpoint,
            "status": self.status.value,
            "capabilities": list(self.capabilities),
            "last_seen": self.last_seen.isoformat(),
        }

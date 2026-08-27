from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import WorkerRole, WorkerStatus
from .ids import new_id


@dataclass
class Worker:
    id: str
    name: str
    role: WorkerRole
    model: str
    endpoint: str = "fake://local"
    provider: str = "openai-compatible"
    capabilities: list[str] = field(default_factory=list)
    status: WorkerStatus = WorkerStatus.OFFLINE

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
            model=model,
            endpoint=endpoint,
            provider=provider,
            capabilities=list(capabilities or []),
        )

    def can_run(self, role: WorkerRole) -> bool:
        return (
            self.status == WorkerStatus.ONLINE
            and self.role == role
        )

    def is_free(self) -> bool:
        return self.status == WorkerStatus.ONLINE

    def mark_online(self) -> None:
        self.status = WorkerStatus.ONLINE

    def mark_busy(self) -> None:
        self.status = WorkerStatus.BUSY

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "model": self.model,
            "endpoint": self.endpoint,
            "provider": self.provider,
            "capabilities": list(self.capabilities),
            "status": self.status.value,
        }

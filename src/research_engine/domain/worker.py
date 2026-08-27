from __future__ import annotations

from dataclasses import dataclass, field

from research_engine.domain.enums import WorkerRole, WorkerStatus
from research_engine.domain.ids import new_id


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
        role: WorkerRole | str,
        provider: str = "fake",
        model: str | None = None,
        endpoint: str | None = None,
        model_name: str | None = None,
        capabilities: list[str] | None = None,
        id: str | None = None,
    ) -> "Worker":
        """
        Создаёт Worker.

        Поддерживаются оба имени параметра модели:

            model="..."
            model_name="..."

        Если переданы оба, model_name имеет приоритет.

        Пустая модель разрешена на уровне Worker.
        Проверка наличия модели выполняется WorkerRuntime.
        """

        if isinstance(role, str):
            try:
                role = WorkerRole(role)
            except ValueError:
                try:
                    role = WorkerRole[role.upper()]
                except KeyError as exc:
                    raise ValueError(
                        f"Unknown worker role: {role}"
                    ) from exc

        resolved_model = (
            model_name
            if model_name is not None
            else (model if model is not None else "")
        )

        resolved_endpoint = (
            endpoint
            if endpoint is not None
            else "fake://local"
        )

        return cls(
            id=id or new_id(),
            name=name,
            role=role,
            model=resolved_model,
            endpoint=resolved_endpoint,
            provider=provider,
            capabilities=list(capabilities or []),
        )

    @property
    def model_name(self) -> str:
        """
        Совместимый alias для model.
        """
        return self.model

    @model_name.setter
    def model_name(self, value: str) -> None:
        self.model = value

    def can_run(
        self,
        role: WorkerRole | str | None,
    ) -> bool:
        """
        Проверяет, может ли Worker выполнить работу указанной роли.
        """

        if self.status is not WorkerStatus.ONLINE:
            return False

        if role is None:
            return True

        if isinstance(role, str):
            try:
                role = WorkerRole(role)
            except ValueError:
                try:
                    role = WorkerRole[role.upper()]
                except KeyError:
                    return False

        return self.role is role

    def mark_online(self) -> None:
        self.status = WorkerStatus.ONLINE

    def mark_offline(self) -> None:
        self.status = WorkerStatus.OFFLINE

    def mark_busy(self) -> None:
        self.status = WorkerStatus.BUSY

    def mark_idle(self) -> None:
        self.status = WorkerStatus.ONLINE

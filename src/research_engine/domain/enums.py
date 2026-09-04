from __future__ import annotations

from enum import Enum


class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkerStatus(str, Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"


class WorkerRole(str, Enum):
    GENERATOR = "generator"
    CRITIC = "critic"
    RESEARCHER = "researcher"
    ANALYST = "analyst"


class ArtifactType(str, Enum):
    THESIS = "thesis"
    CRITIQUE = "critique"
    REVISION = "revision"
    FINAL = "final"
    SUMMARY = "summary"

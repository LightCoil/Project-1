from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from research_engine.domain.enums import ArtifactType, WorkerRole
from research_engine.domain.ids import new_id

OBJECTIVE_INPUT = "objective"


@dataclass
class WorkflowStep:
    id: str
    position: int
    name: str
    role: WorkerRole
    input_artifacts: list[str]
    artifact_type: ArtifactType
    title: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "position": self.position,
            "name": self.name,
            "role": self.role.value,
            "input_artifacts": list(self.input_artifacts),
            "artifact_type": self.artifact_type.value,
            "title": self.title,
        }


@dataclass
class Workflow:
    id: str
    name: str
    description: str
    steps: list[WorkflowStep] = field(default_factory=list)

    def step_by_name(self, name: str) -> WorkflowStep:
        for step in self.steps:
            if step.name == name:
                return step
        raise KeyError(f"unknown workflow step: {name}")

    def next_step(self, completed_name: str | None) -> WorkflowStep | None:
        if completed_name is None:
            return self.steps[0] if self.steps else None
        current = self.step_by_name(completed_name)
        nxt = current.position + 1
        for step in self.steps:
            if step.position == nxt:
                return step
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def abcde(cls) -> Workflow:
        """Default v0.1 workflow: A generator, B critic, C revision, D critic, E final."""
        return cls(
            id=new_id("wf"),
            name="A-B-C-D-E",
            description="Generator → Critic → Revision → Critic → Final",
            steps=[
                WorkflowStep(
                    id=new_id("wfs"),
                    position=1,
                    name="A",
                    role=WorkerRole.GENERATOR,
                    input_artifacts=[OBJECTIVE_INPUT],
                    artifact_type=ArtifactType.THESIS,
                    title="GENERATOR",
                ),
                WorkflowStep(
                    id=new_id("wfs"),
                    position=2,
                    name="B",
                    role=WorkerRole.CRITIC,
                    input_artifacts=["A"],
                    artifact_type=ArtifactType.CRITIQUE,
                    title="CRITIC",
                ),
                WorkflowStep(
                    id=new_id("wfs"),
                    position=3,
                    name="C",
                    role=WorkerRole.GENERATOR,
                    input_artifacts=["A", "B"],
                    artifact_type=ArtifactType.REVISION,
                    title="REVISION",
                ),
                WorkflowStep(
                    id=new_id("wfs"),
                    position=4,
                    name="D",
                    role=WorkerRole.CRITIC,
                    input_artifacts=["C"],
                    artifact_type=ArtifactType.CRITIQUE,
                    title="CRITIC",
                ),
                WorkflowStep(
                    id=new_id("wfs"),
                    position=5,
                    name="E",
                    role=WorkerRole.GENERATOR,
                    input_artifacts=["C", "D"],
                    artifact_type=ArtifactType.FINAL,
                    title="FINAL",
                ),
            ],
        )

from __future__ import annotations

from datetime import datetime, timezone

from research_engine.domain.artifact import Artifact
from research_engine.domain.enums import ResearchStatus, StepStatus, WorkerRole
from research_engine.domain.experiment import Experiment
from research_engine.domain.research import Research
from research_engine.domain.step_execution import StepExecution
from research_engine.domain.worker import Worker
from research_engine.domain.workflow import Workflow
from research_engine.persistence.files import ExperimentFiles


class ExperimentStore:
    """In-memory technical state. Artifact bodies live on disk via ExperimentFiles."""

    def __init__(
        self,
        *,
        experiment: Experiment,
        workflow: Workflow,
        files: ExperimentFiles,
    ) -> None:
        self.experiment = experiment
        self.workflow = workflow
        self.files = files
        self._researches: dict[str, Research] = {}
        self._executions: dict[str, StepExecution] = {}
        self._artifacts: dict[str, Artifact] = {}
        self._step_name_by_artifact: dict[str, str] = {}
        self._workers: dict[str, Worker] = {}

    def save_experiment(self, experiment: Experiment) -> None:
        self.experiment = experiment

    def add_research(self, research: Research) -> None:
        self._researches[research.id] = research

    def create_researches(self) -> list[Research]:
        created: list[Research] = []
        for number in range(1, self.experiment.research_count + 1):
            research = Research.create(experiment_id=self.experiment.id, number=number)
            self.add_research(research)
            created.append(research)
        return created

    def save_research(self, research: Research) -> None:
        self._researches[research.id] = research

    def get_research(self, research_id: str) -> Research:
        return self._researches[research_id]

    def list_researches(self) -> list[Research]:
        return sorted(self._researches.values(), key=lambda item: item.number)

    def save_execution(self, execution: StepExecution) -> None:
        self._executions[execution.id] = execution

    def executions_for(self, research_id: str) -> list[StepExecution]:
        return [item for item in self._executions.values() if item.research_id == research_id]

    def latest_failed_execution(self, research_id: str) -> StepExecution | None:
        failed = [
            item
            for item in self.executions_for(research_id)
            if item.status == StepStatus.FAILED
        ]
        if not failed:
            return None
        epoch = datetime.min.replace(tzinfo=timezone.utc)
        return max(failed, key=lambda item: item.started_at or item.completed_at or epoch)

    def save_artifact(self, artifact: Artifact, *, step_name: str) -> None:
        self._artifacts[artifact.id] = artifact
        self._step_name_by_artifact[artifact.id] = step_name
        self.files.write_artifact_file(artifact.id, artifact.content)

    def artifacts_by_step_name(self, research_id: str) -> dict[str, Artifact]:
        mapping: dict[str, Artifact] = {}
        for artifact in self._artifacts.values():
            if artifact.research_id != research_id:
                continue
            mapping[self._step_name_by_artifact[artifact.id]] = artifact
        return mapping

    def add_worker(self, worker: Worker) -> None:
        self._workers[worker.id] = worker

    def save_worker(self, worker: Worker) -> None:
        self._workers[worker.id] = worker

    def find_free_worker(self, role: WorkerRole | None) -> Worker | None:
        if role is None:
            return self.find_free_worker_named_role()
        for worker in self._workers.values():
            if worker.can_run(role):
                return worker
        return None

    def find_free_worker_named_role(self) -> Worker | None:
        for worker in self._workers.values():
            if worker.can_run(WorkerRole.GENERATOR):
                return worker
        return None

    def snapshot(self) -> dict:
        return {
            "id": self.experiment.id,
            "status": self.experiment.status.value,
            "created_at": self.experiment.created_at.isoformat(),
            "updated_at": self.experiment.updated_at.isoformat(),
            "workflow": self.workflow.name,
            "branch_count": self.experiment.research_count,
            "experiment": self.experiment.to_dict(),
            "workflow_detail": self.workflow.to_dict(),
            "researches": [item.to_dict() for item in self.list_researches()],
            "step_executions": [item.to_dict() for item in self._executions.values()],
            "artifacts": [item.to_dict() for item in self._artifacts.values()],
            "workers": [item.to_dict() for item in self._workers.values()],
            "completed_count": sum(
                1 for item in self._researches.values() if item.status == ResearchStatus.COMPLETED
            ),
        }

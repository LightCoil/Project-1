from __future__ import annotations

from dataclasses import dataclass

from research_engine.domain.artifact import Artifact
from research_engine.domain.enums import ArtifactType, ResearchStatus, StepStatus, WorkerRole
from research_engine.domain.ids import format_research_number
from research_engine.domain.research import Research
from research_engine.domain.step_execution import StepExecution
from research_engine.domain.worker import Worker
from research_engine.domain.workflow import Workflow, WorkflowStep
from research_engine.engine.context_builder import ContextBuilder
from research_engine.engine.worker_executor import WorkerExecutor
from research_engine.engine.fake_client import GenerationClient
from research_engine.persistence.experiment_store import ExperimentStore
from research_engine.persistence.files import ExperimentFiles


@dataclass
class ReadyWork:
    research: Research
    step: WorkflowStep


class Scheduler:
    """Picks the next ready A–E operation and a free worker of the matching role."""

    def __init__(
        self,
        *,
        store: ExperimentStore,
        client: GenerationClient,
        files: ExperimentFiles,
        context_builder: ContextBuilder | None = None,
        worker_executor: WorkerExecutor | None = None,
    ) -> None:
        self.store = store
        self.client = client
        self.files = files
        self.context_builder = context_builder or ContextBuilder()
        self.worker_executor = worker_executor or self._build_worker_executor()

    def _build_worker_executor(self) -> WorkerExecutor:
        """Create the default WorkerExecutor used by the Scheduler."""
        from research_engine.engine.worker_runtime import WorkerRuntime
        from research_engine.engine.model_config import ModelRegistry

        registry = ModelRegistry()

        for worker in self.store.workers:
            try:
                config = WorkerRuntime.create(
                    worker=worker,
                    registry=registry,
                    client=self.client,
                )
            except Exception:
                continue

            model_config = config.model_config
            if model_config is not None:
                registry.register(model_config)

        workers = self.store.workers
        if not workers:
            raise RuntimeError(
                "Cannot build WorkerExecutor: no workers are registered."
            )

        runtime = WorkerRuntime.create(
            worker=workers[0],
            registry=registry,
            client=self.client,
        )

        return WorkerExecutor(
            runtime=runtime,
            client=self.client,
        )

    def next_work(self) -> ReadyWork | None:
        for research in self.store.list_researches():
            if research.status in {ResearchStatus.COMPLETED, ResearchStatus.FAILED}:
                continue
            workflow = self.store.workflow
            artifacts = self.store.artifacts_by_step_name(research.id)
            completed_name = self._last_completed_step_name(research, workflow)
            nxt = workflow.next_step(completed_name)
            if nxt is None:
                continue
            missing = [
                ref
                for ref in nxt.input_artifacts
                if ref != "objective" and ref not in artifacts
            ]
            if missing:
                continue
            return ReadyWork(research=research, step=nxt)
        return None

    def tick(self) -> bool:
        work = self.next_work()
        if work is None:
            return False
        worker = self.store.find_free_worker(work.step.role)
        if worker is None:
            return False
        self._run(work, worker)
        return True

    def run_until_idle(self, *, max_ticks: int = 10_000) -> None:
        for _ in range(max_ticks):
            if not self.tick():
                return
        raise RuntimeError("scheduler exceeded max_ticks")

    def retry(self, research_id: str) -> None:
        research = self.store.get_research(research_id)
        failed = self.store.latest_failed_execution(research_id)
        if failed is None:
            raise ValueError("no failed step to retry")
        research.status = ResearchStatus.PENDING
        research.error = None
        self.store.save_research(research)

    def _run(self, work: ReadyWork, worker: Worker) -> None:
        experiment = self.store.experiment
        research = work.research
        step = work.step
        execution = StepExecution.create(
            research_id=research.id,
            workflow_step_id=step.id,
        )
        artifacts = self.store.artifacts_by_step_name(research.id)
        request = self.context_builder.build(
            experiment=experiment,
            step=step,
            artifacts_by_step=artifacts,
        )
        worker.mark_busy()
        research.start(step.name)
        execution.start(
            worker.id,
            {
                "system_prompt": request.system_prompt,
                "user_prompt": request.user_prompt,
                "input_steps": request.context.get("input_steps", []),
            },
        )
        self.store.save_worker(worker)
        self.store.save_research(research)
        self.store.save_execution(execution)
        experiment.mark_running()
        self.store.save_experiment(experiment)

        try:
            execution_result = self.worker_executor.execute(
                worker=worker,
                request=request,
            )
            result = execution_result.result
            artifact = Artifact.create(
                research_id=research.id,
                step_execution_id=execution.id,
                type=step.artifact_type,
                content=result.content,
                metadata={
                    "step": step.name,
                    "worker_id": worker.id,
                    "model": worker.model,
                    "finish_reason": result.finish_reason,
                    "usage": result.usage,
                },
            )
            execution.complete(artifact.id)
            self.store.save_artifact(artifact, step_name=step.name)
            self.store.save_execution(execution)
            self.files.append_step(
                research_number=self._number(research),
                step=step,
                content=artifact.content,
                experiment=experiment,
            )
            if step.name == "E":
                self._finish_research(research, artifact)
        except Exception as exc:
            execution.fail(str(exc))
            research.fail(str(exc))
            self.store.save_execution(execution)
            self.store.save_research(research)
        finally:
            worker.mark_online()
            self.store.save_worker(worker)
            self.files.write_experiment_json(self.store.snapshot())

    def _finish_research(self, research: Research, final_artifact: Artifact) -> None:
        experiment = self.store.experiment
        number = self._number(research)
        request = self.context_builder.build_summary(
            experiment=experiment,
            research_number=number,
            final_artifact=final_artifact,
        )
        summary_worker = self.store.find_free_worker(WorkerRole.GENERATOR)
        if summary_worker is None:
            summary_content = f"**Итог:**\n{final_artifact.content}"
            summary_meta: dict = {"step": "SUMMARY", "worker_id": None}
        else:
            summary_execution = self.worker_executor.execute(
                worker=summary_worker,
                request=request,
            )
            summary_result = summary_execution.result
            summary_content = summary_result.content
            summary_meta = {
                "step": "SUMMARY",
                "worker_id": summary_worker.id,
                "model": summary_worker.model,
            }
        summary = Artifact.create(
            research_id=research.id,
            step_execution_id=final_artifact.step_execution_id,
            type=ArtifactType.SUMMARY,
            content=summary_content,
            metadata=summary_meta,
        )
        self.store.save_artifact(summary, step_name="SUMMARY")
        research.complete(final_artifact.id)
        research.current_step = "E"
        self.store.save_research(research)
        self.files.append_summary(research_number=number, content=summary.content)
        self.files.append_results(
            research_number=number,
            experiment_name=experiment.name,
            summary=summary.content,
        )
        if all(item.status == ResearchStatus.COMPLETED for item in self.store.list_researches()):
            experiment.mark_completed()
            self.store.save_experiment(experiment)

    def _number(self, research: Research) -> str:
        return format_research_number(research.number, self.store.experiment.research_count)

    def _last_completed_step_name(self, research: Research, workflow: Workflow) -> str | None:
        completed = {
            exec_.workflow_step_id
            for exec_ in self.store.executions_for(research.id)
            if exec_.status == StepStatus.COMPLETED
        }
        last: str | None = None
        for step in sorted(workflow.steps, key=lambda item: item.position):
            if step.id in completed:
                last = step.name
            else:
                break
        return last

from __future__ import annotations

from pathlib import Path

from research_engine.domain.experiment import Experiment
from research_engine.domain.ids import format_research_number
from research_engine.domain.workflow import WorkflowStep


class ExperimentFiles:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.research_dir = root / "research"
        self.research_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir = root / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def research_path(self, research_number: str) -> Path:
        return self.research_dir / f"{research_number}.txt"

    def write_artifact_file(self, artifact_id: str, content: str) -> Path:
        path = self.artifacts_dir / f"{artifact_id}.txt"
        path.write_text(content, encoding="utf-8")
        return path

    def append_step(
        self,
        *,
        research_number: str,
        step: WorkflowStep,
        content: str,
        experiment: Experiment,
    ) -> None:
        path = self.research_path(research_number)
        if not path.exists():
            header = (
                f"RESEARCH №{research_number}\n"
                f"\n"
                f"EXPERIMENT:\n"
                f"{experiment.name}\n"
                f"\n"
                f"OBJECTIVE:\n"
                f"{experiment.objective}\n"
            )
            path.write_text(header, encoding="utf-8")
        block = (
            f"\n"
            f"==================================================\n"
            f"{step.name} — {step.title}\n"
            f"==================================================\n"
            f"\n"
            f"{content}\n"
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(block)

    def append_summary(self, *, research_number: str, content: str) -> None:
        path = self.research_path(research_number)
        block = (
            f"\n"
            f"==================================================\n"
            f"SUMMARY\n"
            f"==================================================\n"
            f"\n"
            f"{content}\n"
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(block)

    def append_results(
        self,
        *,
        research_number: str,
        experiment_name: str,
        summary: str,
    ) -> None:
        path = self.root / "results.md"
        if not path.exists():
            path.write_text(
                "# Research Results\n"
                f"\n"
                f"Experiment: {experiment_name}\n",
                encoding="utf-8",
            )
        block = (
            f"\n"
            f"---\n"
            f"\n"
            f"## №{research_number}\n"
            f"\n"
            f"{summary}\n"
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(block)

    def write_experiment_json(self, payload: dict) -> None:
        import json

        path = self.root / "experiment.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def experiment_dir(data_root: Path, experiment_id: str) -> Path:
    path = data_root / "experiments" / experiment_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def numbered(experiment_count_or_number: int, total: int) -> str:
    return format_research_number(experiment_count_or_number, total)

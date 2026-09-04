from __future__ import annotations

from research_engine.domain.artifact import Artifact
from research_engine.domain.enums import ArtifactType, WorkerRole
from research_engine.domain.experiment import Experiment
from research_engine.domain.generation import GenerationRequest
from research_engine.domain.workflow import OBJECTIVE_INPUT, WorkflowStep

ROLE_INSTRUCTIONS = {
    WorkerRole.GENERATOR: (
        "You are a generator. Produce a complete, self-contained result "
        "for the assigned step. Do not summarize previous steps unless asked."
    ),
    WorkerRole.CRITIC: (
        "You are a critic. Analyze the provided result rigorously. "
        "Point out contradictions, missing pieces, and weak claims."
    ),
}

STEP_TASKS = {
    "A": "Create the initial thesis for the research objective.",
    "B": "Critically analyze result A.",
    "C": "Revise result A using the critique in B. Produce a corrected version.",
    "D": "Critically analyze the revised result C. Do not use A or B.",
    "E": "Produce the final result using the revised version C and critique D.",
    "SUMMARY": "Write a short catalog entry for the completed research.",
}


class ContextBuilder:
    def build(
        self,
        *,
        experiment: Experiment,
        step: WorkflowStep,
        artifacts_by_step: dict[str, Artifact],
    ) -> GenerationRequest:
        parts: list[str] = [
            f"EXPERIMENT: {experiment.name}",
            "",
            "OBJECTIVE:",
            experiment.objective,
            "",
            f"CURRENT STEP: {step.name} — {step.title}",
            f"YOUR TASK: {STEP_TASKS.get(step.name, step.title)}",
        ]
        included: dict[str, str] = {}
        for ref in step.input_artifacts:
            if ref == OBJECTIVE_INPUT:
                continue
            artifact = artifacts_by_step.get(ref)
            if artifact is None:
                raise KeyError(f"missing input artifact for step {step.name}: {ref}")
            parts.extend(["", f"RESULT {ref}:", artifact.content])
            included[ref] = artifact.content

        return GenerationRequest(
            system_prompt=ROLE_INSTRUCTIONS[step.role],
            user_prompt="\n".join(parts),
            context={
                "step": step.name,
                "role": step.role.value,
                "input_steps": [ref for ref in step.input_artifacts if ref != OBJECTIVE_INPUT],
                "inputs": included,
                "objective": experiment.objective,
            },
        )

    def build_summary(
        self,
        *,
        experiment: Experiment,
        research_number: str,
        final_artifact: Artifact,
    ) -> GenerationRequest:
        prompt = "\n".join(
            [
                f"EXPERIMENT: {experiment.name}",
                "",
                "OBJECTIVE:",
                experiment.objective,
                "",
                f"RESEARCH: №{research_number}",
                "",
                "FINAL RESULT E:",
                final_artifact.content,
                "",
                "Write a brief catalog entry with:",
                "Итог:",
                "Основная идея:",
            ]
        )
        return GenerationRequest(
            system_prompt=ROLE_INSTRUCTIONS[WorkerRole.GENERATOR],
            user_prompt=prompt,
            context={
                "step": "SUMMARY",
                "role": WorkerRole.GENERATOR.value,
                "input_steps": ["E"],
                "inputs": {"E": final_artifact.content},
                "objective": experiment.objective,
            },
        )

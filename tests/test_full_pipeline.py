from pathlib import Path

from research_engine.domain.experiment import Experiment
from research_engine.domain.enums import WorkerRole, WorkerStatus
from research_engine.domain.worker import Worker
from research_engine.domain.workflow import Workflow
from research_engine.engine.fake_client import FakeGenerationClient
from research_engine.engine.scheduler import Scheduler
from research_engine.persistence.experiment_store import ExperimentStore
from research_engine.persistence.files import ExperimentFiles


def test_full_research_pipeline():
    """
    Проверяет полный pipeline:

        Experiment
            ↓
        3 Research
            ↓
        A → B → C → D → E
            ↓
        SUMMARY
            ↓
        research/*.txt
        results.md
    """

    # --------------------------------------------------------
    # Temporary output
    # --------------------------------------------------------

    root = Path("test_output")

    if root.exists():
        import shutil
        shutil.rmtree(root)

    root.mkdir()

    # --------------------------------------------------------
    # Workflow
    # --------------------------------------------------------

    workflow = Workflow.abcde()

    assert [
        step.name
        for step in workflow.steps
    ] == ["A", "B", "C", "D", "E"]

    # --------------------------------------------------------
    # Experiment
    # --------------------------------------------------------

    experiment = Experiment.create(
        name="Integration Test",
        objective="Проверить полный цикл исследования A→B→C→D→E",
        workflow_id=workflow.id,
        research_count=3,
    )

    # --------------------------------------------------------
    # Persistence
    # --------------------------------------------------------

    files = ExperimentFiles(root)

    store = ExperimentStore(
        experiment=experiment,
        workflow=workflow,
        files=files,
    )

    store.save_experiment(experiment)

    # --------------------------------------------------------
    # Workers
    # --------------------------------------------------------

    generator = Worker.create(
        name="Fake Generator",
        role=WorkerRole.GENERATOR,
        provider="fake",
        model="fake-generator",
        endpoint="fake://generator",
    )

    critic = Worker.create(
        name="Fake Critic",
        role=WorkerRole.CRITIC,
        provider="fake",
        model="fake-critic",
        endpoint="fake://critic",
    )

    generator.status = WorkerStatus.ONLINE
    critic.status = WorkerStatus.ONLINE

    store.add_worker(generator)
    store.add_worker(critic)

    # --------------------------------------------------------
    # Researches
    # --------------------------------------------------------

    researches = store.create_researches()

    assert len(researches) == 3

    assert [
        research.number
        for research in researches
    ] == [1, 2, 3]

    # --------------------------------------------------------
    # Fake model
    # --------------------------------------------------------

    client = FakeGenerationClient()

    # --------------------------------------------------------
    # Scheduler
    # --------------------------------------------------------

    scheduler = Scheduler(
        store=store,
        client=client,
        files=files,
    )

    # --------------------------------------------------------
    # Execute
    # --------------------------------------------------------

    scheduler.run_until_idle()

    # --------------------------------------------------------
    # Verify Research
    # --------------------------------------------------------

    for research in researches:

        saved = store.get_research(research.id)

        assert saved.status.value == "completed"

        executions = store.executions_for(
            research.id
        )

        assert len(executions) == 5

        artifacts = store.artifacts_by_step_name(
            research.id
        )

        assert set(artifacts.keys()) == {
            "A",
            "B",
            "C",
            "D",
            "E",
            "SUMMARY",
        }

        # ----------------------------------------------------
        # Research file
        # ----------------------------------------------------

        research_file = (
            root
            / "research"
            / f"{research.number:03d}.txt"
        )

        assert research_file.exists()

        text = research_file.read_text(
            encoding="utf-8"
        )

        for step in ["A", "B", "C", "D", "E"]:
            assert step in text

    # --------------------------------------------------------
    # results.md
    # --------------------------------------------------------

    results_file = root / "results.md"

    assert results_file.exists()

    results = results_file.read_text(
        encoding="utf-8"
    )

    for number in range(1, 4):
        assert f"№{number:03d}" in results

    # --------------------------------------------------------
    # Final verification
    # --------------------------------------------------------

    print()
    print("✅ Research #001 — A→B→C→D→E→SUMMARY")
    print("✅ Research #002 — A→B→C→D→E→SUMMARY")
    print("✅ Research #003 — A→B→C→D→E→SUMMARY")
    print("✅ Все исследования завершены")
    print("✅ Все executions созданы")
    print("✅ Все artifacts созданы")
    print("✅ Все TXT-файлы созданы")
    print("✅ results.md создан")
    print("✅ Результаты исследований не смешались")

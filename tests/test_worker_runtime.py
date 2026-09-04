from research_engine.domain.generation import GenerationRequest
from research_engine.domain.worker import Worker
from research_engine.domain.enums import WorkerRole
from research_engine.engine.fake_client import FakeGenerationClient
from research_engine.engine.model_config import ModelConfig, ModelRegistry
from research_engine.engine.worker_runtime import WorkerRuntime


def make_registry() -> ModelRegistry:
    registry = ModelRegistry()

    registry.register(
        ModelConfig(
            name="test-generator",
            provider="fake",
            model="fake-generator",
            endpoint="fake://generator",
            generation_parameters={
                "temperature": 0.4,
                "max_tokens": 1024,
            },
        )
    )

    return registry


def make_worker() -> Worker:
    return Worker.create(
        name="Generator",
        role=WorkerRole.GENERATOR,
        model="test-generator",
        endpoint="fake://generator",
        provider="fake",
    )


def test_worker_runtime_resolves_model():
    registry = make_registry()
    worker = make_worker()
    client = FakeGenerationClient()

    runtime = WorkerRuntime.create(
        worker=worker,
        registry=registry,
        client=client,
    )

    assert runtime.worker.id == worker.id
    assert runtime.model.name == "test-generator"
    assert runtime.model_name() == "fake-generator"
    assert runtime.provider() == "fake"
    assert runtime.endpoint() == "fake://generator"


def test_worker_runtime_uses_generation_client():
    registry = make_registry()
    worker = make_worker()
    client = FakeGenerationClient()

    runtime = WorkerRuntime.create(
        worker=worker,
        registry=registry,
        client=client,
    )

    request = GenerationRequest(
        system_prompt="You are a generator.",
        user_prompt="Create a thesis.",
    )

    result = runtime.generate(request)

    assert result.content
    assert result.finish_reason == "stop"


def test_worker_runtime_exposes_generation_parameters():
    registry = make_registry()
    worker = make_worker()
    client = FakeGenerationClient()

    runtime = WorkerRuntime.create(
        worker=worker,
        registry=registry,
        client=client,
    )

    parameters = runtime.generation_parameters()

    assert parameters == {
        "temperature": 0.4,
        "max_tokens": 1024,
    }


def test_worker_runtime_does_not_expose_mutable_model_parameters():
    registry = make_registry()
    worker = make_worker()
    client = FakeGenerationClient()

    runtime = WorkerRuntime.create(
        worker=worker,
        registry=registry,
        client=client,
    )

    parameters = runtime.generation_parameters()
    parameters["temperature"] = 1.0

    assert runtime.generation_parameters()["temperature"] == 0.4


def test_worker_runtime_rejects_unknown_model():
    registry = ModelRegistry()

    worker = Worker.create(
        name="Generator",
        role=WorkerRole.GENERATOR,
        model="missing-model",
        endpoint="fake://generator",
        provider="fake",
    )

    client = FakeGenerationClient()

    try:
        WorkerRuntime.create(
            worker=worker,
            registry=registry,
            client=client,
        )
    except KeyError as exc:
        assert "Unknown model" in str(exc)
    else:
        raise AssertionError(
            "Unknown worker model must fail"
        )


def test_worker_runtime_rejects_worker_without_model():
    registry = ModelRegistry()

    worker = Worker.create(
        name="Generator",
        role=WorkerRole.GENERATOR,
        model="",
        endpoint="fake://generator",
        provider="fake",
    )

    client = FakeGenerationClient()

    try:
        WorkerRuntime.create(
            worker=worker,
            registry=registry,
            client=client,
        )
    except ValueError as exc:
        assert "does not reference a model" in str(exc)
    else:
        raise AssertionError(
            "Worker without model must fail"
        )


def test_worker_runtime_to_dict():
    registry = make_registry()
    worker = make_worker()
    client = FakeGenerationClient()

    runtime = WorkerRuntime.create(
        worker=worker,
        registry=registry,
        client=client,
    )

    payload = runtime.to_dict()

    assert "worker" in payload
    assert "model" in payload
    assert payload["model"]["name"] == "test-generator"
    assert payload["model"]["model"] == "fake-generator"

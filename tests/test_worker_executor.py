from __future__ import annotations

from research_engine.domain.generation import GenerationRequest
from research_engine.domain.worker import Worker
from research_engine.engine.fake_client import FakeGenerationClient
from research_engine.engine.model_config import ModelConfig, ModelRegistry
from research_engine.engine.worker_executor import WorkerExecutor
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
        role="generator",
        model_name="test-generator",
    )


def make_request() -> GenerationRequest:
    return GenerationRequest(
        system_prompt="You are a generator.",
        user_prompt="Produce a thesis.",
        temperature=0.7,
        max_tokens=256,
        context={
            "step": "A",
            "objective": "Test execution",
        },
    )


def test_worker_executor_executes_generation():
    registry = make_registry()
    runtime = WorkerRuntime(registry=registry)
    client = FakeGenerationClient()

    executor = WorkerExecutor(
        runtime=runtime,
        client=client,
    )

    worker = make_worker()
    request = make_request()

    execution = executor.execute(
        worker=worker,
        request=request,
    )

    assert execution.worker.id == worker.id
    assert execution.model_name == "test-generator"
    assert execution.result.content
    assert execution.result.finish_reason == "stop"


def test_worker_executor_uses_runtime_model():
    registry = make_registry()
    runtime = WorkerRuntime(registry=registry)
    client = FakeGenerationClient()

    executor = WorkerExecutor(
        runtime=runtime,
        client=client,
    )

    worker = make_worker()
    request = make_request()

    execution = executor.execute(
        worker=worker,
        request=request,
    )

    assert execution.model_name == "test-generator"


def test_worker_executor_preserves_request():
    registry = make_registry()
    runtime = WorkerRuntime(registry=registry)
    client = FakeGenerationClient()

    executor = WorkerExecutor(
        runtime=runtime,
        client=client,
    )

    worker = make_worker()
    request = make_request()

    execution = executor.execute(
        worker=worker,
        request=request,
    )

    assert execution.request.system_prompt == request.system_prompt
    assert execution.request.user_prompt == request.user_prompt
    assert execution.request.temperature == request.temperature
    assert execution.request.max_tokens == request.max_tokens
    assert execution.request.context == request.context


def test_worker_executor_returns_serializable_result():
    registry = make_registry()
    runtime = WorkerRuntime(registry=registry)
    client = FakeGenerationClient()

    executor = WorkerExecutor(
        runtime=runtime,
        client=client,
    )

    worker = make_worker()
    request = make_request()

    execution = executor.execute(
        worker=worker,
        request=request,
    )

    payload = execution.to_dict()

    assert payload["worker_id"] == worker.id
    assert payload["worker_name"] == worker.name
    assert payload["model_name"] == "test-generator"

    assert payload["request"]["temperature"] == 0.7
    assert payload["request"]["max_tokens"] == 256
    assert payload["request"]["context"]["step"] == "A"

    assert payload["result"]["content"]
    assert payload["result"]["finish_reason"] == "stop"


def test_worker_executor_propagates_generation_failure():
    registry = make_registry()
    runtime = WorkerRuntime(registry=registry)

    client = FakeGenerationClient(
        fail_on_step="A",
    )

    executor = WorkerExecutor(
        runtime=runtime,
        client=client,
    )

    worker = make_worker()
    request = make_request()

    try:
        executor.execute(
            worker=worker,
            request=request,
        )
    except Exception as exc:
        assert "A" in str(exc)
    else:
        raise AssertionError(
            "Generation failure must be propagated"
        )

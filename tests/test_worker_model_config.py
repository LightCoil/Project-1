from research_engine.domain.enums import WorkerRole, WorkerStatus
from research_engine.domain.worker import Worker
from research_engine.engine.model_config import (
    ModelConfig,
    ModelRegistry,
)


def test_model_registry_returns_registered_model():
    registry = ModelRegistry()

    config = ModelConfig(
        name="generator",
        provider="openai-compatible",
        model="test-generator",
        endpoint="http://localhost:8000/v1",
    )

    registry.register(config)

    assert registry.has("generator")
    assert registry.get("generator") is config


def test_model_registry_rejects_duplicate_model():
    registry = ModelRegistry()

    config = ModelConfig(
        name="generator",
        provider="openai-compatible",
        model="test-generator",
        endpoint="http://localhost:8000/v1",
    )

    registry.register(config)

    try:
        registry.register(config)
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError(
            "Duplicate model registration should fail"
        )


def test_worker_can_reference_configured_model():
    registry = ModelRegistry()

    config = ModelConfig(
        name="generator",
        provider="openai-compatible",
        model="test-generator",
        endpoint="http://localhost:8000/v1",
    )

    registry.register(config)

    model = registry.get("generator")

    worker = Worker.create(
        name="Generator Worker",
        role=WorkerRole.GENERATOR,
        model=model.model,
        endpoint=model.endpoint,
        provider=model.provider,
    )

    worker.mark_online()

    assert worker.status == WorkerStatus.ONLINE
    assert worker.model == "test-generator"
    assert worker.endpoint == "http://localhost:8000/v1"
    assert worker.provider == "openai-compatible"


def test_model_config_preserves_generation_parameters():
    config = ModelConfig(
        name="generator",
        provider="openai-compatible",
        model="test-generator",
        endpoint="http://localhost:8000/v1",
        temperature=0.2,
        max_tokens=8192,
    )

    assert config.temperature == 0.2
    assert config.max_tokens == 8192


def test_registry_lists_models():
    registry = ModelRegistry()

    registry.register(
        ModelConfig(
            name="generator",
            provider="openai-compatible",
            model="generator-model",
            endpoint="http://generator/v1",
        )
    )

    registry.register(
        ModelConfig(
            name="critic",
            provider="openai-compatible",
            model="critic-model",
            endpoint="http://critic/v1",
        )
    )

    models = registry.list()

    assert len(models) == 2
    assert models[0].name == "generator"
    assert models[1].name == "critic"

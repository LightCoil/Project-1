from __future__ import annotations

import pytest

from research_engine.domain.generation import GenerationRequest
from research_engine.domain.worker import Worker
from research_engine.engine.model_config import ModelConfig, ModelRegistry
from research_engine.engine.runtime_factory import RuntimeFactory


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

    registry.register(
        ModelConfig(
            name="test-http",
            provider="openai-compatible",
            model="test-model",
            endpoint="http://localhost:8000/v1",
            generation_parameters={
                "temperature": 0.7,
                "max_tokens": 2048,
            },
        )
    )

    return registry


def make_worker(model_name: str) -> Worker:
    return Worker.create(
        name="Test Worker",
        role="generator",
        model=model_name,
    )


def test_runtime_factory_resolves_registered_model():
    registry = make_registry()

    factory = RuntimeFactory(registry=registry)

    runtime = factory.create(
        worker_model="test-generator",
    )

    assert runtime is not None
    assert runtime.model_config.name == "test-generator"
    assert runtime.model_config.model == "fake-generator"


def test_runtime_factory_rejects_unknown_model():
    registry = make_registry()

    factory = RuntimeFactory(registry=registry)

    with pytest.raises(KeyError, match="Unknown model"):
        factory.create(
            worker_model="missing",
        )


def test_runtime_factory_rejects_unknown_provider():
    registry = ModelRegistry()

    registry.register(
        ModelConfig(
            name="unknown",
            provider="something-unknown",
            model="test-model",
            endpoint="http://localhost:8000/v1",
        )
    )

    factory = RuntimeFactory(registry=registry)

    with pytest.raises(
        ValueError,
        match="Unsupported model provider",
    ):
        factory.create(
            worker_model="unknown",
        )


def test_runtime_factory_creates_fake_runtime():
    registry = make_registry()

    factory = RuntimeFactory(registry=registry)

    runtime = factory.create(
        worker_model="test-generator",
    )

    worker = make_worker("test-generator")

    request = GenerationRequest(
        system_prompt="You are a generator.",
        user_prompt="Test generation.",
    )

    result = runtime.client.generate(
        worker,
        request,
    )

    assert result.content
    assert "FAKE" in result.content


def test_runtime_factory_creates_http_runtime():
    registry = make_registry()

    factory = RuntimeFactory(registry=registry)

    runtime = factory.create(
        worker_model="test-http",
    )

    assert runtime is not None
    assert runtime.model_config.name == "test-http"
    assert runtime.model_config.provider == "openai-compatible"

    assert isinstance(
        runtime.client,
        object,
    )


def test_runtime_uses_exact_registered_configuration():
    registry = make_registry()

    factory = RuntimeFactory(registry=registry)

    runtime = factory.create(
        worker_model="test-generator",
    )

    assert runtime.model_config.endpoint == "fake://generator"
    assert runtime.model_config.generation_parameters == {
        "temperature": 0.4,
        "max_tokens": 1024,
    }

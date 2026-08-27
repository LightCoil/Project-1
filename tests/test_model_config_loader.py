import json

import pytest

from research_engine.engine.model_config_loader import (
    ModelConfigLoader,
)


def test_load_json_configuration(tmp_path):
    config_file = tmp_path / "models.json"

    config_file.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "name": "generator",
                        "provider": "openai-compatible",
                        "model": "test-generator",
                        "endpoint": "http://localhost:8000/v1",
                        "api_key": "test-key",
                        "temperature": 0.5,
                        "max_tokens": 2048,
                    },
                    {
                        "name": "critic",
                        "provider": "openai-compatible",
                        "model": "test-critic",
                        "endpoint": "http://localhost:9000/v1",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    registry = ModelConfigLoader().load(config_file)

    generator = registry.get("generator")
    critic = registry.get("critic")

    assert generator.name == "generator"
    assert generator.provider == "openai-compatible"
    assert generator.model == "test-generator"
    assert generator.endpoint == "http://localhost:8000/v1"
    assert generator.api_key == "test-key"
    assert generator.temperature == 0.5
    assert generator.max_tokens == 2048

    assert critic.name == "critic"
    assert critic.model == "test-critic"
    assert critic.api_key is None


def test_load_from_dict():
    payload = {
        "models": [
            {
                "name": "local",
                "provider": "openai-compatible",
                "model": "local-model",
                "endpoint": "http://127.0.0.1:8000/v1",
            }
        ]
    }

    registry = ModelConfigLoader().from_dict(payload)

    model = registry.get("local")

    assert model.name == "local"
    assert model.model == "local-model"


def test_missing_file(tmp_path):
    path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        ModelConfigLoader().load(path)


def test_invalid_json(tmp_path):
    path = tmp_path / "models.json"

    path.write_text(
        "{ invalid json",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid JSON"):
        ModelConfigLoader().load(path)


def test_missing_models_field():
    with pytest.raises(
        ValueError,
        match="must contain 'models'",
    ):
        ModelConfigLoader().from_dict({})


def test_models_must_be_list():
    with pytest.raises(
        ValueError,
        match="'models' must be a list",
    ):
        ModelConfigLoader().from_dict(
            {"models": {}}
        )


def test_missing_required_field():
    payload = {
        "models": [
            {
                "name": "generator",
                "provider": "openai-compatible",
                "model": "test-model",
            }
        ]
    }

    with pytest.raises(
        ValueError,
        match="missing required field 'endpoint'",
    ):
        ModelConfigLoader().from_dict(payload)


def test_invalid_model_entry():
    with pytest.raises(
        ValueError,
        match="Model entry #1 must be an object",
    ):
        ModelConfigLoader().from_dict(
            {"models": ["invalid"]}
        )


def test_empty_required_string():
    payload = {
        "models": [
            {
                "name": "",
                "provider": "openai-compatible",
                "model": "test-model",
                "endpoint": "http://localhost:8000/v1",
            }
        ]
    }

    with pytest.raises(
        ValueError,
        match="field 'name'",
    ):
        ModelConfigLoader().from_dict(payload)


def test_multiple_models_are_loaded():
    payload = {
        "models": [
            {
                "name": "generator",
                "provider": "openai-compatible",
                "model": "generator-model",
                "endpoint": "http://generator/v1",
            },
            {
                "name": "critic",
                "provider": "openai-compatible",
                "model": "critic-model",
                "endpoint": "http://critic/v1",
            },
            {
                "name": "final",
                "provider": "openai-compatible",
                "model": "final-model",
                "endpoint": "http://final/v1",
            },
        ]
    }

    registry = ModelConfigLoader().from_dict(payload)

    assert registry.get("generator").model == "generator-model"
    assert registry.get("critic").model == "critic-model"
    assert registry.get("final").model == "final-model"

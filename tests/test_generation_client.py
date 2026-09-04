from research_engine.domain.generation import GenerationRequest
from research_engine.domain.worker import Worker
from research_engine.domain.enums import WorkerRole

from research_engine.engine.fake_client import FakeGenerationClient


def make_worker() -> Worker:
    return Worker.create(
        name="Test Generator",
        role=WorkerRole.GENERATOR,
        model="fake-model",
        endpoint="fake://local",
        provider="fake",
    )


def make_request(
    step: str,
    *,
    inputs: dict[str, str] | None = None,
) -> GenerationRequest:

    inputs = inputs or {}

    return GenerationRequest(
        system_prompt="test",
        user_prompt="test",
        context={
            "step": step,
            "role": "generator",
            "input_steps": list(inputs.keys()),
            "inputs": inputs,
            "objective": "Test objective",
        },
    )


def test_fake_client_implements_generation_contract():
    client = FakeGenerationClient()
    worker = make_worker()

    request = make_request("A")

    result = client.generate(
        worker,
        request,
    )

    assert result.content
    assert result.metadata["provider"] == "fake"
    assert result.metadata["model"] == "fake-model"
    assert result.metadata["step"] == "A"


def test_fake_client_generates_all_steps():
    client = FakeGenerationClient()
    worker = make_worker()

    requests = [
        make_request("A"),
        make_request("B", inputs={"A": "thesis"}),
        make_request(
            "C",
            inputs={
                "A": "thesis",
                "B": "critique",
            },
        ),
        make_request("D", inputs={"C": "revision"}),
        make_request(
            "E",
            inputs={
                "C": "revision",
                "D": "critique",
            },
        ),
    ]

    for request in requests:
        result = client.generate(
            worker,
            request,
        )

        assert result.content
        assert request.context["step"] in result.content


def test_fake_client_can_simulate_failure():
    client = FakeGenerationClient(
        fail_on_step="C"
    )

    worker = make_worker()

    request = make_request(
        "C",
        inputs={
            "A": "thesis",
            "B": "critique",
        },
    )

    try:
        client.generate(
            worker,
            request,
        )
    except RuntimeError as exc:
        assert "C" in str(exc)
    else:
        raise AssertionError(
            "FakeGenerationClient должен был "
            "сгенерировать ошибку на шаге C"
        )

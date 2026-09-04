from research_engine.domain.generation import GenerationRequest
from research_engine.domain.worker import Worker
from research_engine.engine.http_client import HttpGenerationClient
from research_engine.engine.model_config import ModelConfig, ModelRegistry
from research_engine.engine.worker_executor import WorkerExecutor
from research_engine.engine.worker_runtime import WorkerRuntime


class FakeGenerationClient(HttpGenerationClient):
    """
    Capture the request passed through WorkerExecutor.

    No network request is performed.
    """

    def __init__(self):
        super().__init__(
            endpoint="http://example.test/v1"
        )
        self.last_worker = None
        self.last_request = None

    def generate(self, worker, request):
        self.last_worker = worker
        self.last_request = request

        return type(
            "FakeGenerationResult",
            (),
            {
                "content": "test response",
                "finish_reason": "stop",
                "usage": {},
                "metadata": {},
            },
        )()


def test_model_generation_parameters_reach_http_payload():
    """
    Verify the complete generation-parameter flow:

        ModelConfig
            ↓
        WorkerRuntime
            ↓
        WorkerExecutor
            ↓
        GenerationRequest
            ↓
        HttpGenerationClient
            ↓
        HTTP payload

    No real HTTP request is performed.
    """

    config = ModelConfig(
        name="test-generator",
        provider="openai-compatible",
        model="test-model",
        endpoint="http://example.test/v1",
        temperature=0.4,
        max_tokens=1024,
        generation_parameters={
            "top_p": 0.85,
            "top_k": 40,
            "repetition_penalty": 1.1,
            "seed": 123,
        },
    )

    registry = ModelRegistry()
    registry.register(config)

    worker = Worker(
        id="worker-1",
        name="Test Worker",
        role="generator",
        provider="openai-compatible",
        model="test-generator",
        endpoint="http://example.test/v1",
        capabilities=[],
    )

    client = FakeGenerationClient()

    runtime = WorkerRuntime.create(
        worker=worker,
        registry=registry,
        client=client,
    )

    # ---------------------------------------------------------------
    # A. Runtime must expose the complete parameter set
    # ---------------------------------------------------------------

    parameters = runtime.generation_parameters()

    assert parameters["temperature"] == 0.4
    assert parameters["max_tokens"] == 1024
    assert parameters["top_p"] == 0.85
    assert parameters["top_k"] == 40
    assert parameters["repetition_penalty"] == 1.1
    assert parameters["seed"] == 123

    # ---------------------------------------------------------------
    # B. Executor must inject those parameters into a new request
    # ---------------------------------------------------------------

    request = GenerationRequest(
        system_prompt="system",
        user_prompt="user",
        temperature=0.4,
        max_tokens=1024,
    )

    executor = WorkerExecutor(
        runtime=runtime,
        client=client,
    )

    execution = executor.execute(
        worker=worker,
        request=request,
    )

    forwarded_request = client.last_request

    assert forwarded_request is not None

    assert forwarded_request.temperature == 0.4
    assert forwarded_request.max_tokens == 1024

    assert (
        forwarded_request.generation_parameters["temperature"]
        == 0.4
    )

    assert (
        forwarded_request.generation_parameters["max_tokens"]
        == 1024
    )

    assert (
        forwarded_request.generation_parameters["top_p"]
        == 0.85
    )

    assert (
        forwarded_request.generation_parameters["top_k"]
        == 40
    )

    assert (
        forwarded_request.generation_parameters[
            "repetition_penalty"
        ]
        == 1.1
    )

    assert (
        forwarded_request.generation_parameters["seed"]
        == 123
    )

    # ---------------------------------------------------------------
    # C. Original request must not be mutated
    # ---------------------------------------------------------------

    assert request.generation_parameters == {}

    # ---------------------------------------------------------------
    # D. Executor must return the forwarded request
    # ---------------------------------------------------------------

    assert (
        execution.request.generation_parameters
        == forwarded_request.generation_parameters
    )

    # ---------------------------------------------------------------
    # E. HTTP client must translate the request into payload
    # ---------------------------------------------------------------

    payload = client._build_payload(
        worker=worker,
        request=forwarded_request,
    )

    assert payload["model"] == "test-generator"

    assert payload["temperature"] == 0.4
    assert payload["max_tokens"] == 1024

    assert payload["top_p"] == 0.85
    assert payload["top_k"] == 40
    assert payload["repetition_penalty"] == 1.1
    assert payload["seed"] == 123

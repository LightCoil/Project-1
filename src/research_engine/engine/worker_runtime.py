from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from research_engine.domain.generation import GenerationRequest, GenerationResult
from research_engine.domain.worker import Worker
from research_engine.engine.generation_client import GenerationClient
from research_engine.engine.model_config import ModelConfig, ModelRegistry


@dataclass(frozen=True)
class WorkerRuntime:
    """
    Connects a domain Worker with the configured model and
    a GenerationClient.

    Worker remains a domain object.
    ModelRegistry remains the source of model configuration.
    GenerationClient remains responsible for actual generation.
    """

    worker: Worker
    model: ModelConfig
    client: GenerationClient

    @classmethod
    def create(
        cls,
        *,
        worker: Worker,
        registry: ModelRegistry,
        client: GenerationClient,
    ) -> "WorkerRuntime":
        """
        Build a runtime worker from the worker's configured model.

        The Worker must reference a model by name. The registry resolves
        that name into the complete ModelConfig.
        """
        model_name = worker.model

        if not model_name:
            raise ValueError(
                f"Worker {worker.id} does not reference a model"
            )

        model = registry.get(model_name)

        return cls(
            worker=worker,
            model=model,
            client=client,
        )

    def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        """
        Execute one generation using this worker's configured model.

        The current GenerationClient contract accepts a Worker, while
        model-specific configuration belongs to the runtime layer.
        The client therefore receives the domain Worker and the runtime
        validates that the selected model is the one configured for it.
        """
        return self.client.generate(
            self.worker,
            request,
        )

    def model_name(self) -> str:
        """Return the configured model identifier."""
        return self.model.model

    def endpoint(self) -> str:
        """Return the configured model endpoint."""
        return self.model.endpoint

    def provider(self) -> str:
        """Return the configured provider."""
        return self.model.provider

    def generation_parameters(self) -> dict[str, Any]:
        """
        Return generation parameters defined by ModelConfig.

        A copy is returned so callers cannot mutate the configuration
        stored in the registry through this method.
        """
        return dict(self.model.generation_parameters)

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable runtime description."""
        return {
            "worker": self.worker.to_dict(),
            "model": self.model.to_dict(),
        }

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from research_engine.domain.worker import Worker
from research_engine.engine.model_config import (
    ModelConfig,
    ModelRegistry,
)


@dataclass
class WorkerRuntime:
    """
    Runtime binding between a Worker, its registered ModelConfig,
    and a generation client.

    Supports both compatibility construction modes:

        WorkerRuntime(
            worker=worker,
            registry=registry,
            client=client,
        )

    and:

        WorkerRuntime(
            model_config=config,
            client=client,
        )
    """

    worker: Worker | None = None
    model_config: ModelConfig | None = None
    client: Any | None = None
    registry: ModelRegistry | None = None

    @classmethod
    def create(
        cls,
        *,
        worker: Worker,
        registry: ModelRegistry,
        client: Any | None = None,
    ) -> "WorkerRuntime":
        """
        Create a worker-bound runtime.

        The worker must reference a model registered in the
        supplied ModelRegistry.
        """

        runtime = cls(
            worker=worker,
            registry=registry,
            client=client,
        )

        runtime.resolve_model()

        return runtime

    def resolve_model(
        self,
        worker: Worker | None = None,
    ) -> ModelConfig:
        """
        Resolve the ModelConfig associated with the active worker.

        Resolution order:

        1. explicitly supplied worker;
        2. runtime-bound worker;
        3. explicitly supplied model_config.
        """

        if self.model_config is not None:
            return self.model_config

        active_worker = (
            worker
            if worker is not None
            else self.worker
        )

        if active_worker is None:
            raise ValueError(
                "Worker is not configured"
            )

        model_name = getattr(
            active_worker,
            "model_name",
            None,
        )

        if callable(model_name):
            model_name = model_name()

        if not model_name:
            model_name = getattr(
                active_worker,
                "model",
                "",
            )

        if not model_name:
            raise ValueError(
                "Worker does not reference a model"
            )

        if self.registry is None:
            raise ValueError(
                "Model registry is not configured"
            )

        return self.registry.get(model_name)

    @property
    def model(self) -> ModelConfig:
        """
        Compatibility alias for the resolved ModelConfig.
        """

        return self.resolve_model()

    def model_name(self) -> str:
        """
        Return the actual provider model identifier.
        """

        return self.resolve_model().model

    def provider(self) -> str:
        """
        Return the provider identifier.
        """

        return self.resolve_model().provider

    def endpoint(self) -> str:
        """
        Return the configured model endpoint.
        """

        return self.resolve_model().endpoint

    def generation_parameters(self, worker: Worker | None = None) -> dict[str, Any]:
        """
        Return an independent copy of all generation parameters
        exposed by the active ModelConfig.

        Standard parameters are normalized into the resulting
        dictionary, while custom parameters are preserved.
        """

        config = self.resolve_model(worker)

        parameters: dict[str, Any] = {}

        temperature = getattr(
            config,
            "temperature",
            None,
        )

        if temperature is not None:
            parameters["temperature"] = temperature

        max_tokens = getattr(
            config,
            "max_tokens",
            None,
        )

        if max_tokens is not None:
            parameters["max_tokens"] = max_tokens

        extra = getattr(
            config,
            "generation_parameters",
            None,
        )

        if isinstance(extra, dict):
            parameters.update(extra)

        return deepcopy(parameters)

    def generate(
        self,
        request: Any,
    ) -> Any:
        """
        Execute a generation request through the configured client.
        """

        if self.client is None:
            raise RuntimeError(
                "WorkerRuntime has no generation client"
            )

        if self.worker is None:
            raise RuntimeError(
                "WorkerRuntime has no worker"
            )

        return self.client.generate(
            self.worker,
            request,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the runtime configuration.

        Mutable generation parameters are copied so callers cannot
        mutate the underlying ModelConfig.
        """

        worker_payload = None

        if self.worker is not None:
            role = getattr(
                self.worker,
                "role",
                None,
            )

            if hasattr(role, "value"):
                role = role.value

            worker_payload = {
                "id": getattr(
                    self.worker,
                    "id",
                    None,
                ),
                "name": getattr(
                    self.worker,
                    "name",
                    None,
                ),
                "role": role,
                "provider": getattr(
                    self.worker,
                    "provider",
                    None,
                ),
                "model": getattr(
                    self.worker,
                    "model",
                    None,
                ),
                "endpoint": getattr(
                    self.worker,
                    "endpoint",
                    None,
                ),
                "capabilities": list(
                    getattr(
                        self.worker,
                        "capabilities",
                        [],
                    )
                    or []
                ),
            }

        config = self.resolve_model()

        model_payload = {
            "name": config.name,
            "provider": config.provider,
            "model": config.model,
            "endpoint": config.endpoint,
            "api_key": getattr(
                config,
                "api_key",
                None,
            ),
            "temperature": getattr(
                config,
                "temperature",
                0.7,
            ),
            "max_tokens": getattr(
                config,
                "max_tokens",
                4096,
            ),
            "generation_parameters": deepcopy(
                getattr(
                    config,
                    "generation_parameters",
                    {},
                )
                or {}
            ),
        }

        return {
            "worker": worker_payload,
            "model": model_payload,
            "model_config": model_payload,
            "generation_parameters": (
                self.generation_parameters()
            ),
        }

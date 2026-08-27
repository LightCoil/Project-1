from __future__ import annotations

from dataclasses import dataclass

from research_engine.domain.worker import Worker
from research_engine.engine.fake_client import FakeGenerationClient
from research_engine.engine.generation_client import GenerationClient
from research_engine.engine.http_client import HttpGenerationClient
from research_engine.engine.model_config import (
    ModelConfig,
    ModelRegistry,
)
from research_engine.engine.worker_runtime import WorkerRuntime


@dataclass(frozen=True)
class RuntimeFactory:
    """
    Creates WorkerRuntime instances from registered ModelConfig
    objects.

    Supported construction paths:

        factory.create(worker=worker)

    and:

        factory.create(worker_model="config-name")

    The worker-bound path preserves the Worker instance inside
    WorkerRuntime.

    The worker_model path creates a model-config-bound runtime
    without a Worker.
    """

    registry: ModelRegistry

    def create(
        self,
        worker: Worker | str | None = None,
        *,
        worker_model: str | None = None,
    ) -> WorkerRuntime:
        """
        Create a WorkerRuntime.

        Supported forms:

            create(worker=worker)

            create(worker_model="config-name")

            create("config-name")

        For worker-bound creation, the worker.model / worker.model_name
        value identifies the registered ModelConfig.
        """

        if worker is not None and worker_model is not None:
            raise ValueError(
                "Specify either worker or worker_model, not both"
            )

        # --------------------------------------------------------------
        # Positional string compatibility:
        #
        # factory.create("audit-config")
        #
        # is treated as worker_model.
        # --------------------------------------------------------------

        if isinstance(worker, str):
            if worker_model is not None:
                raise ValueError(
                    "Specify either worker or worker_model, not both"
                )

            worker_model = worker
            worker = None

        # --------------------------------------------------------------
        # Worker-bound path
        # --------------------------------------------------------------

        if worker is not None:
            model_name = getattr(
                worker,
                "model_name",
                None,
            )

            if callable(model_name):
                model_name = model_name()

            if not model_name:
                model_name = getattr(
                    worker,
                    "model",
                    None,
                )

            if not model_name:
                raise ValueError(
                    "Worker does not reference a model"
                )

            config = self.registry.get(model_name)

            client = self._create_client(config)

            return WorkerRuntime(
                worker=worker,
                model_config=config,
                client=client,
                registry=self.registry,
            )

        # --------------------------------------------------------------
        # Model-only compatibility path
        # --------------------------------------------------------------

        if worker_model is not None:
            config = self.registry.get(worker_model)

            client = self._create_client(config)

            return WorkerRuntime(
                model_config=config,
                client=client,
                registry=self.registry,
            )

        raise ValueError(
            "RuntimeFactory.create() requires worker or worker_model"
        )

    def _create_client(
        self,
        config: ModelConfig,
    ) -> GenerationClient:
        """
        Create the generation client for a ModelConfig.

        FakeGenerationClient intentionally does not need the config
        object in its constructor. It already implements the required
        generate(worker, request) protocol used by the runtime tests.
        """

        provider = config.provider.strip().lower()

        if provider == "fake":
            return FakeGenerationClient()

        if provider in {
            "openai-compatible",
            "openai_compatible",
        }:
            return HttpGenerationClient(
                endpoint=config.endpoint,
                api_key=config.api_key,
            )

        raise ValueError(
            f"Unsupported model provider: {config.provider}"
        )

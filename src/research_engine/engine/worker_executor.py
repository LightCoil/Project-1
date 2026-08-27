from __future__ import annotations
from copy import deepcopy

from dataclasses import dataclass, replace
from typing import Any

from research_engine.domain.generation import (
    GenerationRequest,
    GenerationResult,
)
from research_engine.domain.worker import Worker
from research_engine.engine.generation_client import GenerationClient
from research_engine.engine.worker_runtime import WorkerRuntime


@dataclass(frozen=True)
class WorkerExecutionResult:
    """
    Результат выполнения одного worker.

    Содержит:
    - worker;
    - generation request;
    - generation result;
    - имя модели.
    """

    worker: Worker
    request: GenerationRequest
    result: GenerationResult
    model_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker.id,
            "worker_name": self.worker.name,
            "model_name": self.model_name,
            "request": {
                "system_prompt": self.request.system_prompt,
                "user_prompt": self.request.user_prompt,
                "temperature": self.request.temperature,
                "max_tokens": self.request.max_tokens,
                "context": dict(self.request.context),
                "generation_parameters": dict(
                    self.request.generation_parameters
                ),
            },
            "result": {
                "content": self.result.content,
                "finish_reason": self.result.finish_reason,
                "usage": dict(self.result.usage),
                "metadata": dict(self.result.metadata),
            },
        }


class WorkerExecutor:
    """
    Выполняет GenerationRequest через GenerationClient.

    Ответственности:
    1. Получить runtime-конфигурацию worker.
    2. Передать request клиенту генерации.
    3. Вернуть типизированный результат выполнения.

    WorkerExecutor не:
    - выбирает worker;
    - управляет scheduler;
    - сохраняет artifacts;
    - изменяет состояние Research.
    """

    def __init__(
        self,
        *,
        runtime: WorkerRuntime,
        client: GenerationClient,
    ) -> None:
        self._runtime = runtime
        self._client = client

    @property
    def runtime(self) -> WorkerRuntime:
        return self._runtime

    @property
    def client(self) -> GenerationClient:
        return self._client

    def execute(
        self,
        *,
        worker: Worker,
        request: GenerationRequest,
    ) -> WorkerExecutionResult:
        """
        Выполнить генерацию для worker.

        Параметры модели разрешаются через WorkerRuntime и
        передаются дальше в отдельную копию GenerationRequest.

        Исходный request не изменяется.
        """

        model = self._runtime.resolve_model(worker)

        parameters = self._runtime.generation_parameters(worker=worker)

        forwarded_request = replace(
            request,
            temperature=parameters.get(
                "temperature",
                request.temperature,
            ),
            max_tokens=parameters.get(
                "max_tokens",
                request.max_tokens,
            ),
            generation_parameters=deepcopy(parameters),
        )

        result = self._client.generate(
            worker,
            forwarded_request,
        )

        execution_request = replace(
            request,
            generation_parameters=deepcopy(
                forwarded_request.generation_parameters
            ),
        )

        return WorkerExecutionResult(
            worker=worker,
            request=execution_request,
            result=result,
            model_name=model.name,
        )

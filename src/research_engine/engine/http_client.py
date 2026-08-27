from __future__ import annotations

from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json

from research_engine.domain.generation import (
    GenerationRequest,
    GenerationResult,
)
from research_engine.domain.worker import Worker


class HttpGenerationClient:
    """
    HTTP implementation of GenerationClient.

    Project-1 knows nothing about the model provider.
    A Worker only supplies an HTTP endpoint.
    """

    def __init__(
        self,
        *,
        timeout: float = 120.0,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be greater than 0")

        self.timeout = timeout

    def generate(
        self,
        worker: Worker,
        request: GenerationRequest,
    ) -> GenerationResult:

        if not worker.endpoint:
            raise ValueError(
                f"Worker {worker.id} has no endpoint"
            )

        payload = {
            "system_prompt": request.system_prompt,
            "user_prompt": request.user_prompt,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "context": request.context,
        }

        body = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        http_request = Request(
            worker.endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(
                http_request,
                timeout=self.timeout,
            ) as response:

                raw = response.read()

        except HTTPError as exc:
            raise RuntimeError(
                f"Generation endpoint returned HTTP "
                f"{exc.code}: {exc.reason}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"Generation endpoint is unreachable: "
                f"{exc.reason}"
            ) from exc

        except TimeoutError as exc:
            raise RuntimeError(
                "Generation endpoint timed out"
            ) from exc

        try:
            result: dict[str, Any] = json.loads(
                raw.decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "Generation endpoint returned invalid JSON"
            ) from exc

        content = result.get("content")

        if not isinstance(content, str):
            raise RuntimeError(
                "Generation endpoint response must contain "
                "a string field 'content'"
            )

        finish_reason = result.get(
            "finish_reason",
            "stop",
        )

        if not isinstance(finish_reason, str):
            finish_reason = str(finish_reason)

        usage = result.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}

        metadata = result.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        return GenerationResult(
            content=content,
            finish_reason=finish_reason,
            usage=usage,
            metadata=metadata,
        )

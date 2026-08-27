from __future__ import annotations
from copy import deepcopy

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any

from research_engine.domain.generation import GenerationResult


class HttpGenerationClient:
    """
    HTTP client for OpenAI-compatible generation endpoints.

    Supported constructors:

        HttpGenerationClient(endpoint="http://...")
        HttpGenerationClient(timeout=5)

    Supported generate() APIs:

        generate(request)
        generate(worker, request)

    The client always returns GenerationResult.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout

    def generate(
        self,
        worker_or_request: Any,
        request: Any | None = None,
    ) -> GenerationResult:
        if request is None:
            worker = None
            generation_request = worker_or_request
        else:
            worker = worker_or_request
            generation_request = request

        endpoint = self._resolve_endpoint(worker)

        payload = self._build_payload(
            worker=worker,
            request=generation_request,
        )

        url = self._generation_url(endpoint)

        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

        http_request = Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urlopen(
                http_request,
                timeout=self.timeout,
            ) as response:
                raw = response.read().decode(
                    "utf-8"
                )

        except HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                "HTTP generation failed: "
                f"{exc.code} {exc.reason}: {body}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"HTTP generation connection failed: {exc}"
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "HTTP generation returned invalid JSON"
            ) from exc

        return self._parse_response(
            data,
            worker=worker,
        )

    # ------------------------------------------------------------------
    # Endpoint
    # ------------------------------------------------------------------

    def _resolve_endpoint(
        self,
        worker: Any | None,
    ) -> str:
        if worker is not None:
            worker_endpoint = getattr(
                worker,
                "endpoint",
                None,
            )

            if worker_endpoint:
                return str(worker_endpoint)

        if self.endpoint:
            return self.endpoint

        raise ValueError(
            "HTTP generation endpoint is not configured"
        )

    def _generation_url(
        self,
        endpoint: str,
    ) -> str:
        endpoint = endpoint.rstrip("/")

        if endpoint.endswith("/chat/completions"):
            return endpoint

        if endpoint.endswith("/v1"):
            return (
                f"{endpoint}/chat/completions"
            )

        # Legacy mock-server behaviour:
        # use endpoint directly.
        return endpoint

    # ------------------------------------------------------------------
    # Payload
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        *,
        worker: Any | None,
        request: Any,
    ) -> dict[str, Any]:
        system_prompt = getattr(
            request,
            "system_prompt",
            "",
        )

        user_prompt = getattr(
            request,
            "user_prompt",
            "",
        )

        temperature = getattr(
            request,
            "temperature",
            None,
        )

        max_tokens = getattr(
            request,
            "max_tokens",
            None,
        )

        context = getattr(
            request,
            "context",
            None,
        )

        generation_parameters = getattr(
            request,
            "generation_parameters",
            None,
        )

        model = None

        if worker is not None:
            model = getattr(
                worker,
                "model",
                None,
            )

        payload: dict[str, Any] = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        }

        if model:
            payload["model"] = model

        if temperature is not None:
            payload["temperature"] = temperature

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if context:
            payload["context"] = context

        if isinstance(generation_parameters, dict):
            for key, value in deepcopy(
                generation_parameters
            ).items():
                if key in {
                    "system_prompt",
                    "user_prompt",
                    "messages",
                    "model",
                    "context",
                }:
                    continue

                payload[key] = value

        return payload

    # ------------------------------------------------------------------
    # Response
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        data: dict[str, Any],
        *,
        worker: Any | None = None,
    ) -> GenerationResult:

        content: str = ""
        finish_reason: str = "stop"
        usage: dict[str, Any] = {}
        metadata: dict[str, Any] = {}

        choices = data.get("choices")

        if isinstance(choices, list) and choices:
            first = choices[0]

            if isinstance(first, dict):
                finish_reason = (
                    first.get("finish_reason")
                    or "stop"
                )

                message = first.get("message")

                if isinstance(message, dict):
                    value = message.get("content")

                    if value is not None:
                        content = str(value)

                if not content and "text" in first:
                    value = first.get("text")

                    if value is not None:
                        content = str(value)

        # Simple mock API:
        if not content and "text" in data:
            value = data.get("text")

            if value is not None:
                content = str(value)

        # Another simple mock API:
        if not content and "content" in data:
            value = data.get("content")

            if value is not None:
                content = str(value)

        if isinstance(data.get("usage"), dict):
            usage = dict(data["usage"])

        if isinstance(data.get("metadata"), dict):
            metadata.update(data["metadata"])

        if "model" in data:
            metadata.setdefault(
                "model",
                data["model"],
            )

        metadata.setdefault(
            "provider",
            "openai-compatible",
        )

        if worker is not None:
            worker_model = getattr(
                worker,
                "model",
                None,
            )

            if worker_model:
                metadata.setdefault(
                    "model",
                    worker_model,
                )

        # Preserve unknown top-level response information
        # without replacing the typed result contract.
        if not content and not choices:
            metadata.setdefault(
                "raw_response",
                data,
            )

        return GenerationResult(
            content=content,
            finish_reason=finish_reason,
            usage=usage,
            metadata=metadata,
        )

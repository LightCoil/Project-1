from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any


class HttpGenerationClient:
    """
    HTTP-клиент для OpenAI-compatible generation endpoint.

    Поддерживает оба варианта:

        HttpGenerationClient(endpoint="http://...")
        HttpGenerationClient(timeout=5)

    и оба варианта generate():

        generate(request)
        generate(worker, request)
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
    ) -> Any:
        """
        Выполняет generation.

        Старый API:
            generate(request)

        Worker-aware API:
            generate(worker, request)
        """

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
                raw = response.read().decode("utf-8")

        except HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                f"HTTP generation failed: "
                f"{exc.code} {exc.reason}: {body}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"HTTP generation connection failed: {exc}"
            ) from exc

        data = json.loads(raw)

        return self._parse_response(data)

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

        # Уже полный OpenAI-compatible endpoint.
        if endpoint.endswith("/chat/completions"):
            return endpoint

        # Если endpoint заканчивается на /v1,
        # добавляем chat/completions.
        if endpoint.endswith("/v1"):
            return f"{endpoint}/chat/completions"

        # Для тестовых HTTP-серверов старого проекта
        # endpoint используется непосредственно.
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

        model = None

        if worker is not None:
            model = getattr(
                worker,
                "model",
                None,
            )

        payload: dict[str, Any] = {
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

        return payload

    # ------------------------------------------------------------------
    # Response
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        data: dict[str, Any],
    ) -> Any:

        # OpenAI-compatible response.
        choices = data.get("choices")

        if choices:
            first = choices[0]

            message = first.get("message")

            if isinstance(message, dict):
                if "content" in message:
                    return message["content"]

            if "text" in first:
                return first["text"]

        # Некоторые простые mock-серверы проекта
        # возвращают {"text": "..."}.
        if "text" in data:
            return data["text"]

        # Ещё один удобный вариант mock API.
        if "content" in data:
            return data["content"]

        # Если сервер вернул неизвестный JSON,
        # не теряем данные.
        return data

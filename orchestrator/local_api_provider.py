"""PROJECT-1 OpenAI-compatible local model provider."""

from __future__ import annotations

from typing import Any, Dict, Optional
import json
import urllib.error
import urllib.request


class LocalOpenAICompatibleProvider:
    """
    Minimal OpenAI-compatible HTTP provider.

    Secrets are supplied at runtime and are never persisted by this
    class.
    """

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        timeout: int = 120,
        max_output_tokens: int = 25,
    ):
        # api_url is the canonical constructor argument.
        # base_url is accepted as a compatibility alias.
        if api_url is None:
            api_url = base_url

        if not api_url:
            raise ValueError(
                "api_url or base_url is required"
            )

        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens

        # Normalize full endpoints to a base URL.
        for suffix in (
            "/v1/chat/completions",
            "/chat/completions",
            "/v1/models",
            "/models",
        ):
            if self.api_url.endswith(suffix):
                self.api_url = self.api_url[
                    :-len(suffix)
                ].rstrip("/")
                break

        self.base_url = self.api_url
        self.models_url = (
            f"{self.base_url}/v1/models"
        )
        self.chat_url = (
            f"{self.base_url}/v1/chat/completions"
        )

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

        return headers

    def discover_model(self) -> str:
        request = urllib.request.Request(
            self.models_url,
            headers=self._headers(),
            method="GET",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )
            raise RuntimeError(
                f"Model discovery HTTP {exc.code}: {body}"
            ) from exc

        candidates = []

        if isinstance(payload, dict):
            if isinstance(payload.get("data"), list):
                candidates = payload["data"]

            elif isinstance(payload.get("models"), list):
                candidates = payload["models"]

        for item in candidates:
            if isinstance(item, dict):
                value = (
                    item.get("id")
                    or item.get("name")
                    or item.get("model")
                )

                if value:
                    self.model_name = str(value)
                    return self.model_name

            elif isinstance(item, str):
                self.model_name = item
                return self.model_name

        raise RuntimeError(
            "No model was returned by /v1/models."
        )

    def chat(
        self,
        prompt: str,
        max_output_tokens: Optional[int] = None,
    ) -> str:

        if not self.model_name:
            self.discover_model()

        limit = (
            max_output_tokens
            if max_output_tokens is not None
            else self.max_output_tokens
        )

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "max_tokens": limit,
            "temperature": 0.2,
            "stream": False,
        }

        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            self.chat_url,
            data=data,
            headers=self._headers(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                f"Chat API HTTP {exc.code}: {body}"
            ) from exc

        if isinstance(result, dict):
            choices = result.get("choices")

            if isinstance(choices, list) and choices:
                first = choices[0]

                if isinstance(first, dict):
                    message = first.get("message")

                    if isinstance(message, dict):
                        content = message.get(
                            "content"
                        )

                        if content is not None:
                            return str(content)

                    text = first.get("text")

                    if text is not None:
                        return str(text)

            # Some compatible servers return generated text
            # directly.
            for key in (
                "response",
                "content",
                "text",
            ):
                if result.get(key) is not None:
                    return str(result[key])

        raise RuntimeError(
            "Chat API returned no usable text."
        )

    def run(self, task: str) -> str:
        return self.chat(task)

    def __call__(self, task: str) -> str:
        return self.chat(task)

    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.model_name,
            "provider": "local_api",
            "description": (
                "OpenAI-compatible local model."
            ),
            "capabilities": [
                "general",
                "reasoning",
                "analysis",
                "code",
            ],
            "context_window": None,
            "max_output_tokens": (
                self.max_output_tokens
            ),
            "supports_streaming": True,
            "supports_reasoning": True,
            "supports_code": True,
        }

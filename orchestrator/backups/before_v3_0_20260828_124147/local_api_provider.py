
"""PROJECT-1 OpenAI-compatible local API provider v3.0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import requests


@dataclass
class LocalOpenAICompatibleProvider:
    base_url: str
    api_key: str = ""
    model: str = "auto"
    timeout: int = 120
    max_output_tokens: int = 25

    @property
    def models_url(self) -> str:
        return self.base_url.rstrip("/") + "/v1/models"

    @property
    def chat_url(self) -> str:
        return self.base_url.rstrip("/") + "/v1/chat/completions"

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

        return headers

    def discover_model(self) -> Optional[str]:
        response = requests.get(
            self.models_url,
            headers=self._headers(),
            timeout=20,
        )

        response.raise_for_status()

        payload = response.json()

        data = payload.get("data", [])

        if not isinstance(data, list):
            return None

        for item in data:
            if isinstance(item, dict):
                model_id = item.get("id")

                if model_id:
                    self.model = str(model_id)
                    return self.model

        return None

    def run(self, task: str) -> str:
        model_name = self.model

        if not model_name or model_name == "auto":
            discovered = self.discover_model()

            if not discovered:
                raise RuntimeError(
                    "Local API does not expose a model name "
                    "through /v1/models."
                )

            model_name = discovered

        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": task,
                }
            ],
            "max_tokens": self.max_output_tokens,
            "stream": False,
        }

        response = requests.post(
            self.chat_url,
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                "Local model API HTTP "
                f"{response.status_code}: "
                f"{response.text[:1000]}"
            )

        result = response.json()

        choices = result.get("choices", [])

        if not choices:
            raise RuntimeError(
                "Local API returned no choices."
            )

        message = choices[0].get("message", {})

        content = message.get("content")

        if content is None:
            content = choices[0].get("text")

        if content is None:
            raise RuntimeError(
                "Local API response contains no text content."
            )

        return str(content)

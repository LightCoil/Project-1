
"""PROJECT-1 OpenAI-compatible local API provider v2.9."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Optional


class LocalOpenAICompatibleProvider:
    """
    Minimal OpenAI-compatible HTTP provider.

    The provider expects:

        POST /v1/chat/completions

    with:

        {
            "model": "...",
            "messages": [
                {
                    "role": "user",
                    "content": "..."
                }
            ]
        }

    Secrets are supplied at runtime and are never persisted.
    """

    def __init__(
        self,
        name: str,
        api_url: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120,
        max_tokens: int = 25,
    ):
        self.name = name
        self.api_url = api_url
        self.api_key = api_key or ""
        self.model = model or name
        self.timeout = timeout
        self.max_tokens = max_tokens

    def run(self, task: str) -> str:
        if not isinstance(task, str):
            raise TypeError(
                "task must be a string"
            )

        task = task.strip()

        if not task:
            raise ValueError(
                "task cannot be empty"
            )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": task,
                }
            ],
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        data = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        request = urllib.request.Request(
            self.api_url,
            data=data,
            method="POST",
        )

        request.add_header(
            "Content-Type",
            "application/json",
        )

        if self.api_key:
            request.add_header(
                "Authorization",
                f"Bearer {self.api_key}",
            )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                raw = response.read()

        except urllib.error.HTTPError as exc:
            body = ""

            try:
                body = exc.read().decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                pass

            raise RuntimeError(
                f"Local model API HTTP {exc.code}: "
                f"{body[:1000]}"
            ) from exc

        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Local model API connection failed: "
                f"{exc.reason}"
            ) from exc

        except TimeoutError as exc:
            raise RuntimeError(
                "Local model API request timed out."
            ) from exc

        try:
            result = json.loads(
                raw.decode(
                    "utf-8",
                    errors="replace",
                )
            )
        except Exception as exc:
            raise RuntimeError(
                "Local model API returned invalid JSON."
            ) from exc

        return self._extract_text(result)

    @staticmethod
    def _extract_text(result: Any) -> str:

        if isinstance(result, str):
            return result

        if not isinstance(result, dict):
            return str(result)

        choices = result.get(
            "choices"
        )

        if isinstance(
            choices,
            list,
        ) and choices:

            first = choices[0]

            if isinstance(
                first,
                dict,
            ):

                message = first.get(
                    "message"
                )

                if isinstance(
                    message,
                    dict,
                ):

                    content = message.get(
                        "content"
                    )

                    if content is not None:
                        return str(content)

                text = first.get(
                    "text"
                )

                if text is not None:
                    return str(text)

        output = result.get(
            "output"
        )

        if output is not None:
            return str(output)

        response = result.get(
            "response"
        )

        if response is not None:
            return str(response)

        raise RuntimeError(
            "Could not extract model text "
            "from API response."
        )

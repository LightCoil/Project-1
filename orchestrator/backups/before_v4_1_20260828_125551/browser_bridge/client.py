"""PROJECT-1 Browser Chat Client v4.0."""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Dict, Optional


class BrowserChatClient:

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: float = 180.0,
        poll_interval: float = 0.5,
    ):

        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.poll_interval = poll_interval

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
    ):

        body = None

        if payload is not None:
            body = json.dumps(
                payload,
                ensure_ascii=False,
            ).encode("utf-8")

        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={
                "Content-Type":
                    "application/json",
                "X-Bridge-Token":
                    self.token,
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=15,
        ) as response:

            raw = response.read()

        return json.loads(
            raw.decode("utf-8")
        )

    def health(self) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/health",
        )

    def request_chatgpt(
        self,
        prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:

        created = self._request(
            "POST",
            "/orchestrator/request",
            {
                "prompt": prompt,
                "metadata": metadata or {},
            },
        )

        if not created.get("ok"):
            raise RuntimeError(
                created.get(
                    "error",
                    "bridge request failed",
                )
            )

        request_id = created["request_id"]

        deadline = time.time() + self.timeout

        while time.time() < deadline:

            result = self._request(
                "GET",
                "/orchestrator/result",
            )

            if result.get("available"):

                item = result["result"]

                if item["id"] != request_id:
                    continue

                return item["payload"]["response"]

            time.sleep(
                self.poll_interval
            )

        raise TimeoutError(
            "ChatGPT browser response timeout."
        )


__all__ = [
    "BrowserChatClient",
]

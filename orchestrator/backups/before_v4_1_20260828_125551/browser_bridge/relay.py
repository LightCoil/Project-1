"""PROJECT-1 Browser Chat Relay v4.0.

Transport boundary between the orchestrator and the user's browser.

This module intentionally does NOT communicate with ChatGPT directly.
The browser extension is responsible for interacting with the visible
ChatGPT web page.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional


@dataclass
class BridgeMessage:
    id: str
    kind: str
    payload: Dict[str, Any]
    created_at: float = field(default_factory=time.time)


class BridgeState:
    def __init__(self, token: Optional[str] = None):
        self.token = token or secrets.token_urlsafe(32)
        self.lock = threading.Lock()

        self.pending_request: Optional[BridgeMessage] = None
        self.response: Optional[BridgeMessage] = None

        self.browser_connected = False
        self.last_browser_seen = 0.0

    def browser_touch(self) -> None:
        with self.lock:
            self.browser_connected = True
            self.last_browser_seen = time.time()

    def browser_is_alive(self) -> bool:
        with self.lock:
            if not self.browser_connected:
                return False

            return (time.time() - self.last_browser_seen) < 30

    def create_request(
        self,
        prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        request_id = secrets.token_urlsafe(16)

        message = BridgeMessage(
            id=request_id,
            kind="chatgpt_request",
            payload={
                "prompt": prompt,
                "metadata": metadata or {},
            },
        )

        with self.lock:
            self.pending_request = message
            self.response = None

        return request_id

    def consume_request(self) -> Optional[BridgeMessage]:
        with self.lock:
            message = self.pending_request
            self.pending_request = None
            return message

    def set_response(
        self,
        request_id: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self.lock:
            self.response = BridgeMessage(
                id=request_id,
                kind="chatgpt_response",
                payload={
                    "response": response,
                    "metadata": metadata or {},
                },
            )

    def consume_response(self) -> Optional[BridgeMessage]:
        with self.lock:
            message = self.response
            self.response = None
            return message


class RelayHandler(BaseHTTPRequestHandler):

    state: BridgeState = None

    def _send_json(
        self,
        status: int,
        payload: Dict[str, Any],
    ) -> None:

        body = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*",
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, X-Bridge-Token",
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS",
        )

        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        token = self.headers.get("X-Bridge-Token", "")
        return secrets.compare_digest(
            token,
            self.state.token,
        )

    def do_OPTIONS(self):
        self._send_json(
            200,
            {"ok": True},
        )

    def do_GET(self):

        if self.path == "/health":
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "project1-browser-bridge",
                    "version": "4.0",
                    "browser_connected":
                        self.state.browser_is_alive(),
                },
            )
            return

        if not self._authorized():
            self._send_json(
                401,
                {"ok": False, "error": "unauthorized"},
            )
            return

        if self.path == "/browser/poll":

            self.state.browser_touch()

            message = self.state.consume_request()

            if message is None:
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "pending": False,
                    },
                )
                return

            self._send_json(
                200,
                {
                    "ok": True,
                    "pending": True,
                    "request": {
                        "id": message.id,
                        "kind": message.kind,
                        "payload": message.payload,
                    },
                },
            )
            return

        if self.path == "/orchestrator/result":

            result = self.state.consume_response()

            if result is None:
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "available": False,
                    },
                )
                return

            self._send_json(
                200,
                {
                    "ok": True,
                    "available": True,
                    "result": {
                        "id": result.id,
                        "kind": result.kind,
                        "payload": result.payload,
                    },
                },
            )
            return

        self._send_json(
            404,
            {"ok": False, "error": "not_found"},
        )

    def do_POST(self):

        if not self._authorized():
            self._send_json(
                401,
                {"ok": False, "error": "unauthorized"},
            )
            return

        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            raw = self.rfile.read(length)

            data = json.loads(
                raw.decode("utf-8")
            )

        except Exception as exc:
            self._send_json(
                400,
                {
                    "ok": False,
                    "error": f"invalid_json: {exc}",
                },
            )
            return

        if self.path == "/orchestrator/request":

            prompt = str(
                data.get("prompt", "")
            ).strip()

            if not prompt:
                self._send_json(
                    400,
                    {
                        "ok": False,
                        "error": "prompt_required",
                    },
                )
                return

            request_id = self.state.create_request(
                prompt=prompt,
                metadata=data.get(
                    "metadata",
                    {},
                ),
            )

            self._send_json(
                200,
                {
                    "ok": True,
                    "request_id": request_id,
                },
            )
            return

        if self.path == "/browser/response":

            request_id = str(
                data.get("request_id", "")
            ).strip()

            response = str(
                data.get("response", "")
            )

            if not request_id:
                self._send_json(
                    400,
                    {
                        "ok": False,
                        "error": "request_id_required",
                    },
                )
                return

            self.state.set_response(
                request_id=request_id,
                response=response,
                metadata=data.get(
                    "metadata",
                    {},
                ),
            )

            self.state.browser_touch()

            self._send_json(
                200,
                {"ok": True},
            )
            return

        self._send_json(
            404,
            {"ok": False, "error": "not_found"},
        )

    def log_message(self, format, *args):
        # Keep Colab output clean.
        return


class BrowserChatRelay:

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        token: Optional[str] = None,
    ):

        self.host = host
        self.port = port

        self.state = BridgeState(token)

        RelayHandler.state = self.state

        self.server = ThreadingHTTPServer(
            (self.host, self.port),
            RelayHandler,
        )

        self.thread = None

    @property
    def token(self) -> str:
        return self.state.token

    def start(self) -> None:

        if self.thread is not None:
            return

        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )

        self.thread.start()

    def stop(self) -> None:

        self.server.shutdown()
        self.server.server_close()

        self.thread = None


__all__ = [
    "BridgeMessage",
    "BridgeState",
    "BrowserChatRelay",
]

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from research_engine.domain.generation import GenerationRequest
from research_engine.domain.worker import Worker
from research_engine.domain.enums import WorkerRole
from research_engine.engine.http_client import HttpGenerationClient


class TestHandler(BaseHTTPRequestHandler):

    received = None

    def do_POST(self):
        length = int(
            self.headers["Content-Length"]
        )

        body = self.rfile.read(length)

        TestHandler.received = json.loads(
            body.decode("utf-8")
        )

        response = {
            "content": "HTTP generated result",
            "finish_reason": "stop",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
            },
            "metadata": {
                "test": True,
            },
        }

        encoded = json.dumps(
            response
        ).encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "application/json",
        )
        self.send_header(
            "Content-Length",
            str(len(encoded)),
        )
        self.end_headers()

        self.wfile.write(encoded)

    def log_message(self, *args):
        pass


def test_http_generation_client():

    server = HTTPServer(
        ("127.0.0.1", 0),
        TestHandler,
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )

    thread.start()

    try:

        port = server.server_address[1]

        worker = Worker.create(
            name="HTTP Test Worker",
            role=WorkerRole.GENERATOR,
            model="test-model",
            endpoint=f"http://127.0.0.1:{port}",
        )

        request = GenerationRequest(
            system_prompt="System",
            user_prompt="User",
            temperature=0.7,
            max_tokens=100,
            context={
                "step": "A",
                "objective": "Test",
            },
        )

        client = HttpGenerationClient(
            timeout=5,
        )

        result = client.generate(
            worker,
            request,
        )

        assert result.content == (
            "HTTP generated result"
        )

        assert result.finish_reason == "stop"

        assert result.usage["prompt_tokens"] == 10

        assert result.metadata["test"] is True

        assert TestHandler.received is not None

        assert (
            TestHandler.received["system_prompt"]
            == "System"
        )

        assert (
            TestHandler.received["user_prompt"]
            == "User"
        )

        assert (
            TestHandler.received["context"]["step"]
            == "A"
        )

    finally:
        server.shutdown()
        server.server_close()

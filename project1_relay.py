
import json
import time
import threading
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

ROOT = Path("/content/Project-1")
TOKEN_FILE = ROOT / "bridge_token.txt"
TOKEN = TOKEN_FILE.read_text().strip()

app = FastAPI()

state = {
    "browser_connected": False,
    "last_heartbeat": 0.0,
    "pending_request": None,
    "last_response": None,
    "request_counter": 0
}

lock = threading.Lock()

def authorized(request):
    token = request.headers.get("X-Bridge-Token", "")
    return token == TOKEN

@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "project1-browser-bridge",
        "version": "5.0",
        "browser_connected": state["browser_connected"]
    }

@app.get("/browser/heartbeat")
async def heartbeat(request: Request):

    if not authorized(request):
        return JSONResponse(
            {"ok": False, "error": "unauthorized"},
            status_code=401
        )

    with lock:
        state["browser_connected"] = True
        state["last_heartbeat"] = time.time()

    return {
        "ok": True,
        "browser_connected": True
    }

@app.get("/browser/poll")
async def poll(request: Request):

    if not authorized(request):
        return JSONResponse(
            {"ok": False, "error": "unauthorized"},
            status_code=401
        )

    with lock:

        req = state["pending_request"]

        if req is None:
            return {
                "ok": True,
                "pending": False
            }

        return {
            "ok": True,
            "pending": True,
            "request": req
        }

@app.post("/browser/response")
async def response(request: Request):

    if not authorized(request):
        return JSONResponse(
            {"ok": False, "error": "unauthorized"},
            status_code=401
        )

    data = await request.json()

    with lock:

        state["last_response"] = {
            **data,
            "received_at": time.time()
        }

        state["pending_request"] = None

    return {
        "ok": True
    }

@app.post("/request")
async def create_request(request: Request):

    if not authorized(request):
        return JSONResponse(
            {"ok": False, "error": "unauthorized"},
            status_code=401
        )

    data = await request.json()

    text = str(
        data.get("text", "")
    ).strip()

    if not text:
        return JSONResponse(
            {
                "ok": False,
                "error": "text is empty"
            },
            status_code=400
        )

    with lock:

        state["request_counter"] += 1

        request_id = (
            f"project1-{int(time.time()*1000)}-"
            f"{state['request_counter']}"
        )

        state["pending_request"] = {
            "id": request_id,
            "type": "chat",
            "text": text,
            "timeout_ms": int(
                data.get(
                    "timeout_ms",
                    180000
                )
            ),
            "created_at": time.time()
        }

        state["last_response"] = None

    return {
        "ok": True,
        "request_id": request_id
    }

@app.get("/request/{request_id}")
async def request_status(
    request_id: str,
    request: Request
):

    if not authorized(request):
        return JSONResponse(
            {"ok": False, "error": "unauthorized"},
            status_code=401
        )

    with lock:

        response = state["last_response"]

        if (
            response and
            response.get("id") == request_id
        ):
            return {
                "ok": True,
                "done": True,
                "response": response
            }

    return {
        "ok": True,
        "done": False
    }

@app.get("/status")
async def status(request: Request):

    if not authorized(request):
        return JSONResponse(
            {"ok": False, "error": "unauthorized"},
            status_code=401
        )

    with lock:
        age = (
            time.time() -
            state["last_heartbeat"]
        )

        connected = (
            state["browser_connected"] and
            age < 10
        )

        return {
            "ok": True,
            "browser_connected": connected,
            "last_heartbeat_age": age,
            "pending": (
                state["pending_request"]
                is not None
            ),
            "last_response": state["last_response"]
        }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8767,
        log_level="warning"
    )

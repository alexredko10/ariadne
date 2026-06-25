"""Task Intake HTTP server — minimal stdlib ASGI application.

Exposes the Task Intake service via HTTP endpoints.
This is intake-only.  It does not invoke the runner, orchestrate agents,
create run records, or write to ``.ariadne/**``.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs

from task_intake.app import accept_task
from task_intake.doctor import doctor
from task_intake.models import TaskIntakeRequest
from task_intake.normalize import normalize_task_intake
from task_intake.context_preview import generate_context_preview
from task_intake.runs import create_mock_run
from task_intake.mock_loop import run_mock_loop

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONTENT_TYPE_JSON = "application/json"

# ---------------------------------------------------------------------------
# ASGI app
# ---------------------------------------------------------------------------


async def app(scope: dict, receive: callable, send: callable) -> None:
    """Minimal ASGI application for Task Intake HTTP.

    Parameters
    ----------
    scope
        ASGI connection scope.
    receive
        ASGI receive callable.
    send
        ASGI send callable.
    """
    if scope["type"] != "http":
        return

    method = scope["method"]
    path = scope["path"]

    # --- Route matching ---
    if method == "GET" and path == "/health":
        body = json.dumps(dict(doctor()), ensure_ascii=False).encode("utf-8")
        await _send_json(send, 200, body)
        return

    if method == "POST" and path in ("/submit", "/task-intake/submit"):
        # Read body
        body_bytes = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] == "http.request":
                body_bytes += event.get("body", b"")
                more_body = event.get("more_body", False)

        # Parse JSON
        try:
            data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            await _send_json(
                send, 400,
                json.dumps({
                    "status": "rejected",
                    "reason": "Invalid JSON body.",
                    "error_code": "unsupported_request",
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        prompt = data.get("prompt") if isinstance(data, dict) else None
        if not isinstance(prompt, str):
            await _send_json(
                send, 400,
                json.dumps({
                    "status": "rejected",
                    "reason": "prompt is required and must be a string.",
                    "error_code": "unsupported_request",
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        result = accept_task(TaskIntakeRequest(prompt=prompt))

        if result.status.value == "accepted":
            body = json.dumps({
                "status": "accepted",
                "task_id": result.task_id,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps({
                "status": "rejected",
                "reason": result.reason,
                "error_code": result.error_code.value if result.error_code else "",
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        return

    if method == "POST" and path == "/task-intake/normalize":
        # Read body
        body_bytes = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] == "http.request":
                body_bytes += event.get("body", b"")
                more_body = event.get("more_body", False)

        # Parse JSON
        try:
            data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            await _send_json(
                send, 400,
                json.dumps({
                    "ok": False,
                    "validation": {
                        "valid": False,
                        "errors": ["Invalid JSON body."],
                        "warnings": [],
                    },
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        result = normalize_task_intake(data)

        if result.get("ok") is True:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 400, body)
        return

    if method == "POST" and path == "/context/preview":
        # Read body
        body_bytes = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] == "http.request":
                body_bytes += event.get("body", b"")
                more_body = event.get("more_body", False)

        # Parse JSON
        try:
            data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            await _send_json(
                send, 400,
                json.dumps({
                    "ok": False,
                    "validation": {
                        "valid": False,
                        "errors": ["Invalid JSON body."],
                        "warnings": [],
                    },
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        result = generate_context_preview(data)

        if result.get("ok") is True:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 400, body)
        return

    if method == "POST" and path == "/runs":
        # Read body
        body_bytes = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] == "http.request":
                body_bytes += event.get("body", b"")
                more_body = event.get("more_body", False)

        # Parse JSON
        try:
            data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            await _send_json(
                send, 400,
                json.dumps({
                    "ok": False,
                    "status": {
                        "state": "validation_failed",
                        "phase": "mock_run",
                        "message": "Invalid JSON body.",
                        "is_terminal": True,
                        "progress": 0,
                        "updated_by": "task-intake-api",
                    },
                    "validation": {
                        "valid": False,
                        "errors": ["Invalid JSON body."],
                        "warnings": [],
                    },
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        result = create_mock_run(data)

        if result.get("ok") is True:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 400, body)
        return

    if method == "POST" and path == "/mock-loop":
        # Read body
        body_bytes = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] == "http.request":
                body_bytes += event.get("body", b"")
                more_body = event.get("more_body", False)

        # Parse JSON
        try:
            data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            await _send_json(
                send, 400,
                json.dumps({
                    "ok": False,
                    "validation": {
                        "valid": False,
                        "errors": ["Invalid JSON body."],
                        "warnings": [],
                    },
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        result = run_mock_loop(data)

        if result.get("ok") is True:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 400, body)
        return

    # --- 404 ---
    body = json.dumps({"error": "Not Found"}, ensure_ascii=False).encode("utf-8")
    await _send_json(send, 404, body)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _send_json(send: callable, status: int, body: bytes) -> None:
    """Send a JSON response."""
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            (b"content-type", _CONTENT_TYPE_JSON.encode("utf-8")),
            (b"content-length", str(len(body)).encode("utf-8")),
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })


# ---------------------------------------------------------------------------
# Expose app title for PLAN import check
# ---------------------------------------------------------------------------

title = "Task Intake API"

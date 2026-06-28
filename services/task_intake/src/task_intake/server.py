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
from task_intake.execution_handoff import run_mock_execution_handoff

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

    if method == "POST" and path == "/runs/execute":
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
                    "errors": [{"code": "invalid_json", "message": "Invalid JSON body."}],
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        # Map "task" field to "raw_task" if raw_task is not set
        if isinstance(data, dict) and "task" in data and not data.get("raw_task"):
            data = dict(data)
            data["raw_task"] = data.pop("task")

        result = run_mock_execution_handoff(data)

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

    if method == "GET" and path == "/":
        html = _HTML_PAGE.encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/html; charset=utf-8"),
                (b"content-length", str(len(html)).encode("utf-8")),
            ],
        })
        await send({"type": "http.response.body", "body": html})
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
# HTML page for local interaction at GET /
# ---------------------------------------------------------------------------

_HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ariadne — Local Interaction</title>
<style>
body { font-family: sans-serif; margin: 2rem; }
pre { background: #f5f5f5; padding: 1rem; overflow-x: auto; }
.status-completed { color: #0a0; }
.status-requires_review, .status-blocked { color: #a50; }
.status-failed, .status-error { color: #a00; }
</style>
</head>
<body>
<h1>Ariadne — Local Interaction</h1>
<label for="task">Task:</label>
<textarea id="task" rows="4" cols="60" placeholder="Describe your task…">Implement JWT authentication middleware</textarea>
<br>
<button id="submit">Submit</button>
<div id="result">
<h2>Result</h2>
<div id="status"></div>
<pre id="json"></pre>
</div>
<script>
document.getElementById("submit").addEventListener("click", async function () {
    var task = document.getElementById("task").value;
    if (!task) { alert("Task text is required."); return; }
    document.getElementById("status").textContent = "Running…";
    try {
        var resp = await fetch("/runs/execute", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({task: task}),
        });
        var data = await resp.json();
        var status = data.runtime_status || "unknown";
        document.getElementById("status").innerHTML =
            "<span class=\"status-" + status + "\">" + status + "</span>";
        document.getElementById("json").textContent =
            JSON.stringify(data, null, 2);
    } catch (e) {
        document.getElementById("status").textContent = "Error: " + e.message;
    }
});
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Expose app title for PLAN import check
# ---------------------------------------------------------------------------

title = "Task Intake API"

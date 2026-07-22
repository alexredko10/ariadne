"""Tests for the local user-facing interaction page."""

from __future__ import annotations

import asyncio
import json

from task_intake.server import app


# ---------------------------------------------------------------------------
# ASGI test harness
# ---------------------------------------------------------------------------


async def _asgi_request(
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, dict | str, dict]:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "http_version": "1.1",
        "scheme": "http",
        "client": ("127.0.0.1", 8001),
        "server": ("127.0.0.1", 8001),
    }

    response_status = 500
    response_headers: list = []
    response_body = b""

    async def receive() -> dict:
        if body is not None:
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict) -> None:
        nonlocal response_status, response_headers, response_body
        if event["type"] == "http.response.start":
            response_status = event["status"]
            response_headers = event.get("headers", [])
        elif event["type"] == "http.response.body":
            response_body += event.get("body", b"")

    await app(scope, receive, send)

    return response_status, response_body.decode("utf-8", errors="replace"), dict(response_headers)


def _request(
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, str, dict]:
    return asyncio.run(_asgi_request(method, path, body=body))


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------


class TestGetRoot:
    def test_returns_200(self):
        status, _, _ = _request("GET", "/")
        assert status == 200

    def test_response_is_html(self):
        _, _, headers = _request("GET", "/")
        ct = dict(headers).get(b"content-type", b"").decode("utf-8")
        assert "text/html" in ct

    def test_contains_task_input(self):
        _, body, _ = _request("GET", "/")
        assert "textarea" in body or "<input" in body

    def test_contains_submit_button(self):
        _, body, _ = _request("GET", "/")
        assert "button" in body

    def test_references_runs_execute(self):
        _, body, _ = _request("GET", "/")
        assert "/runs/execute" in body

    def test_external_assets_are_only_bulma_cdn(self):
        _, body, _ = _request("GET", "/")
        import re
        # Extract every external href/src URL from the HTML
        urls = set()
        for m in re.finditer(r'(?:href|src)="([^"]+)"', body):
            u = m.group(1)
            if u.startswith("http") or u.startswith("//"):
                urls.add(u)
        # The only external URL must be the Bulma CDN stylesheet
        assert urls == {"https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.4/css/bulma.min.css"}, f"unexpected external URLs: {urls}"
        # Continue rejecting unpkg and jsdelivr at any level
        assert "unpkg" not in body.lower()
        assert "jsdelivr" not in body.lower()


# ---------------------------------------------------------------------------
# POST /runs/execute preserved
# ---------------------------------------------------------------------------


class TestRunsExecutePreserved:
    def test_returns_runtime_status(self):
        body = json.dumps({"task": "Add JWT auth middleware"}).encode("utf-8")
        status, raw, _ = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert status == 200
        assert "runtime_status" in data
        assert data["runtime_status"] == "completed"

    def test_returns_execution_request(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        _, raw, _ = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert "execution_request" in data

    def test_returns_execution_result(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        _, raw, _ = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert "execution_result" in data
        assert data["execution_result"]["status"] == "completed"

    def test_returns_execution_envelope(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        _, raw, _ = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert "execution_envelope" in data
        assert data["execution_envelope"]["envelope_id"].startswith("env_")

    def test_returns_review_boundary(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        _, raw, _ = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert "review_boundary" in data
        assert "decision" in data["review_boundary"]

    def test_deterministic(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        _, r1r, _ = _request("POST", "/runs/execute", body=body)
        _, r2r, _ = _request("POST", "/runs/execute", body=body)
        d1 = json.loads(r1r)
        d2 = json.loads(r2r)
        assert d1 == d2

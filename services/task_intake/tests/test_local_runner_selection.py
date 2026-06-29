"""Tests for explicit local runner selection on the interaction page."""

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
) -> tuple[int, str]:
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
    response_body = b""

    async def receive() -> dict:
        if body is not None:
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict) -> None:
        nonlocal response_status, response_body
        if event["type"] == "http.response.start":
            response_status = event["status"]
        elif event["type"] == "http.response.body":
            response_body += event.get("body", b"")

    await app(scope, receive, send)

    return response_status, response_body.decode("utf-8", errors="replace")


def _request(method: str, path: str, body: bytes | None = None) -> tuple[int, str]:
    return asyncio.run(_asgi_request(method, path, body=body))


# ---------------------------------------------------------------------------
# GET / page content
# ---------------------------------------------------------------------------


class TestExplanationPanel:
    def test_page_contains_explanation_panel(self):
        _, html = _request("GET", "/")
        assert "Ariadne turns your task" in html

    def test_explains_default_mode(self):
        _, html = _request("GET", "/")
        assert "default" in html.lower()
        assert "deterministic" in html.lower()

    def test_explains_docker_opt_in(self):
        _, html = _request("GET", "/")
        assert "opt-in" in html.lower()
        assert "Docker" in html


class TestRunnerSelection:
    def test_has_noop_runner_option(self):
        _, html = _request("GET", "/")
        assert 'value="noop"' in html

    def test_has_docker_agent_option(self):
        _, html = _request("GET", "/")
        assert 'value="docker-agent"' in html

    def test_noop_is_default(self):
        _, html = _request("GET", "/")
        assert 'checked' in html
        # The checked radio should be the noop one
        import re
        noop_pos = html.find('value="noop"')
        docker_pos = html.find('value="docker-agent"')
        # Find 'checked' closest to noop
        after_noop = html[noop_pos:noop_pos + 50]
        assert 'checked' in after_noop

    def test_page_submits_requested_adapter(self):
        _, html = _request("GET", "/")
        assert "requested_adapter" in html
        assert "/runs/execute" in html

    def test_page_has_no_external_assets(self):
        _, html = _request("GET", "/")
        assert "cdn" not in html.lower()
        assert "unpkg" not in html.lower()
        assert "jsdelivr" not in html.lower()
        assert "react" not in html.lower()
        assert "vue" not in html.lower()
        assert "src=\"" not in html


# ---------------------------------------------------------------------------
# POST /runs/execute with explicit runner
# ---------------------------------------------------------------------------


class TestRunsExecuteWithNoop:
    def test_returns_completed(self):
        body = json.dumps({"task": "Add JWT auth", "requested_adapter": "noop"}).encode("utf-8")
        status, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert status == 200
        assert data["runtime_status"] == "completed"
        assert data["execution_result"]["adapter"] == "noop-v1"
        assert data["execution_request"]["requested_adapter"] == "noop"


class TestRunsExecuteWithDocker:
    def test_returns_blocked_without_allow_docker(self):
        body = json.dumps({"task": "Add JWT auth", "requested_adapter": "docker-agent"}).encode("utf-8")
        status, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert status == 200
        # Docker adapter returns blocked when allow_docker=False
        assert data["execution_result"]["status"] == "blocked"
        assert data["execution_result"]["adapter"] == "docker-agent-v1"

    def test_returns_execution_envelope(self):
        body = json.dumps({"task": "Add JWT auth", "requested_adapter": "docker-agent"}).encode("utf-8")
        _, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert "execution_envelope" in data

    def test_returns_review_boundary(self):
        body = json.dumps({"task": "Add JWT auth", "requested_adapter": "docker-agent"}).encode("utf-8")
        _, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert "review_boundary" in data

    def test_runtime_status_matches(self):
        body = json.dumps({"task": "Add JWT auth", "requested_adapter": "docker-agent"}).encode("utf-8")
        _, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        # Docker adapter without allow_docker returns blocked
        assert data["runtime_status"] == data["review_boundary"]["decision"]
        assert data["runtime_status"] == "blocked"

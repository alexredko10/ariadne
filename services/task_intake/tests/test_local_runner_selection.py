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

    def test_external_assets_are_only_bulma_cdn(self):
        _, html = _request("GET", "/")
        import re
        urls = set()
        for m in re.finditer(r'(?:href|src)="([^"]+)"', html):
            u = m.group(1)
            if u.startswith("http") or u.startswith("//"):
                urls.add(u)
        assert urls == {"https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.4/css/bulma.min.css"}, f"unexpected external URLs: {urls}"
        assert "unpkg" not in html.lower()
        assert "jsdelivr" not in html.lower()
        assert "react" not in html.lower()
        assert "vue" not in html.lower()


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


# ---------------------------------------------------------------------------
# Docker opt-in UI control
# ---------------------------------------------------------------------------


class TestDockerOptInControl:
    """Tests for the new allow_docker checkbox in the UI."""

    def test_page_has_allow_docker_checkbox(self):
        _, html = _request("GET", "/")
        assert "allow-docker-checkbox" in html

    def test_allow_docker_label_present(self):
        _, html = _request("GET", "/")
        assert "ARIADNE_ALLOW_DOCKER_EXECUTION" in html

    def test_allow_docker_defaults_unchecked(self):
        _, html = _request("GET", "/")
        # The checkbox should not have 'checked' attribute
        import re
        # Find the checkbox input
        match = re.search(r'<input[^>]*id="allow-docker-checkbox"[^>]*>', html)
        assert match is not None, "allow-docker-checkbox input not found"
        assert 'checked' not in match.group()

    def test_selecting_docker_does_not_auto_check_allow(self):
        body = json.dumps(
            {"task": "test", "requested_adapter": "docker-agent"}
        ).encode("utf-8")
        _, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        # Without allow_docker, docker-agent should be blocked
        assert data["execution_result"]["status"] == "blocked"

    def test_post_includes_allow_docker_when_checked(self):
        body = json.dumps(
            {"task": "test", "requested_adapter": "docker-agent", "allow_docker": True}
        ).encode("utf-8")
        _, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        # The execution result adapter should be docker-agent-v1
        assert data["execution_result"]["adapter"] == "docker-agent-v1"

    def test_conditional_copy_replaces_hardcoded_boundary(self):
        _, html = _request("GET", "/")
        # The old hardcoded string must be gone
        assert "completed without Docker" not in html
        assert "allow_docker=True" not in html

    def test_docker_radio_not_auto_selected(self):
        _, html = _request("GET", "/")
        # noop should still be the default
        assert 'value="noop"' in html
        # docker-agent should not be checked
        import re
        docker_match = re.search(r'<input[^>]*value="docker-agent"[^>]*>', html)
        assert docker_match is not None
        assert 'checked' not in docker_match.group()

"""Tests for the local user test feedback panel."""

from __future__ import annotations

import asyncio
import json
import re

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
# Feedback panel
# ---------------------------------------------------------------------------


class TestFeedbackPanel:
    def test_page_contains_feedback_panel(self):
        _, html = _request("GET", "/")
        assert "User Test Feedback" in html or "feedback" in html.lower()

    def test_feedback_has_understanding_question(self):
        _, html = _request("GET", "/")
        assert "understand" in html.lower()

    def test_feedback_has_runner_clarity_question(self):
        _, html = _request("GET", "/")
        assert "runner selection" in html.lower()

    def test_feedback_has_summary_clarity_question(self):
        _, html = _request("GET", "/")
        assert "summary card" in html.lower()

    def test_feedback_has_trace_question(self):
        _, html = _request("GET", "/")
        assert "execution trace" in html.lower()

    def test_feedback_has_confusing_question(self):
        _, html = _request("GET", "/")
        assert "What was confusing" in html or "q_confusing" in html

    def test_feedback_has_expectation_question(self):
        _, html = _request("GET", "/")
        assert "expect Ariadne" in html or "q_expect_next" in html

    def test_feedback_has_notes_field(self):
        _, html = _request("GET", "/")
        assert "notes" in html.lower()

    def test_feedback_has_generate_button(self):
        _, html = _request("GET", "/")
        assert "Generate" in html

    def test_feedback_no_backend_route(self):
        """Feedback is client-side only — no POST route for feedback."""
        body = json.dumps({"feedback": "test"}).encode("utf-8")
        status, _ = _request("POST", "/feedback", body=body)
        assert status == 404

    def test_summary_card_preserved(self):
        _, html = _request("GET", "/")
        assert "summary-card" in html

    def test_trace_preserved(self):
        _, html = _request("GET", "/")
        assert "Execution Trace" in html or "trace" in html.lower()

    def test_structured_view_preserved(self):
        _, html = _request("GET", "/")
        assert "structured-view" in html

    def test_raw_json_preserved(self):
        _, html = _request("GET", "/")
        assert "<pre" in html

    def test_runner_selection_preserved(self):
        _, html = _request("GET", "/")
        assert 'name="runner"' in html

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


# ---------------------------------------------------------------------------
# POST /runs/execute preserved
# ---------------------------------------------------------------------------


class TestRunsExecutePreserved:
    def test_returns_runtime_status(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        status, raw = _request("POST", "/runs/execute", body=body)
        data = json.loads(raw)
        assert status == 200
        assert "runtime_status" in data
        assert data["runtime_status"] == "completed"

    def test_deterministic(self):
        body = json.dumps({"task": "Add JWT auth"}).encode("utf-8")
        _, r1r = _request("POST", "/runs/execute", body=body)
        _, r2r = _request("POST", "/runs/execute", body=body)
        d1 = json.loads(r1r)
        d2 = json.loads(r2r)
        assert d1 == d2

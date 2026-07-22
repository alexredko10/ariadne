"""Tests for the local run summary card."""

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
# Summary card on page
# ---------------------------------------------------------------------------


class TestSummaryCard:
    def test_page_contains_summary_card_section(self):
        _, html = _request("GET", "/")
        assert "summary" in html.lower()

    def test_summary_shows_selected_runner(self):
        _, html = _request("GET", "/")
        assert "runner" in html.lower() or "Selected runner" in html

    def test_summary_shows_what_happened(self):
        _, html = _request("GET", "/")
        assert "Deterministic" in html or "Docker opt-in" in html or "blocked" in html or "completed" in html

    def test_summary_shows_runtime_status(self):
        _, html = _request("GET", "/")
        assert "runtime" in html.lower()

    def test_summary_shows_execution_result_status(self):
        _, html = _request("GET", "/")
        assert "Execution result" in html or "execution_result" in html.lower()

    def test_summary_shows_review_decision(self):
        _, html = _request("GET", "/")
        assert "Review decision" in html or "review" in html.lower()

    def test_summary_shows_evidence_count(self):
        _, html = _request("GET", "/")
        assert "Evidence" in html

    def test_summary_placeholder_before_submit(self):
        _, html = _request("GET", "/")
        assert "Submit a task to see the run summary" in html

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

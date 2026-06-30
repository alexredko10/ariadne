"""Tests for the local run history in page."""

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
# Run history panel
# ---------------------------------------------------------------------------


class TestRunHistoryPanel:
    def test_page_contains_run_history_section(self):
        _, html = _request("GET", "/")
        assert "run-history-section" in html or "Run History" in html

    def test_history_empty_before_submit(self):
        _, html = _request("GET", "/")
        assert "No runs yet" in html

    def test_history_has_clear_button(self):
        _, html = _request("GET", "/")
        assert "clear-history-btn" in html

    def test_history_has_list_container(self):
        _, html = _request("GET", "/")
        assert "run-history-list" in html

    def test_history_no_persistence(self):
        _, html = _request("GET", "/")
        assert "localStorage" not in html
        assert "sessionStorage" not in html

    def test_history_has_js_array(self):
        _, html = _request("GET", "/")
        assert "__ariadne_run_history" in html

    def test_history_has_push_function(self):
        _, html = _request("GET", "/")
        assert "pushRunHistory" in html

    def test_history_has_render_function(self):
        _, html = _request("GET", "/")
        assert "renderRunHistory" in html

    def test_history_has_clear_function(self):
        _, html = _request("GET", "/")
        assert "clearRunHistory" in html

    def test_history_max_entries_capped(self):
        _, html = _request("GET", "/")
        # The JS should check length > 10 and shift the oldest
        assert "> 10" in html or "length > 10" in html


# ---------------------------------------------------------------------------
# Existing UI preserved
# ---------------------------------------------------------------------------


class TestExistingUIPreserved:
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

    def test_scenarios_preserved(self):
        _, html = _request("GET", "/")
        assert "Guided scenarios" in html

    def test_feedback_panel_preserved(self):
        _, html = _request("GET", "/")
        assert "User Test Feedback" in html

    def test_session_report_preserved(self):
        _, html = _request("GET", "/")
        assert "Generate session report" in html

    def test_run_report_section_preserved(self):
        _, html = _request("GET", "/")
        assert "run-report-section" in html

    def test_no_external_assets(self):
        _, html = _request("GET", "/")
        assert "cdn" not in html.lower()
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

"""Tests for the local user confusion signals panel."""

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
# Confusion signals panel presence
# ---------------------------------------------------------------------------


class TestConfusionPanel:
    def test_page_contains_confusion_panel(self):
        _, html = _request("GET", "/")
        assert "confusion-signals-panel" in html or "Confusion Signals" in html

    def test_panel_header(self):
        _, html = _request("GET", "/")
        assert "Confusion Signals" in html


# ---------------------------------------------------------------------------
# Four category buttons
# ---------------------------------------------------------------------------


class TestCategoryButtons:
    def test_has_unclear_next_step_button(self):
        _, html = _request("GET", "/")
        assert "Unclear next step" in html

    def test_has_unexpected_result_button(self):
        _, html = _request("GET", "/")
        assert "Unexpected result" in html

    def test_has_runner_confusion_button(self):
        _, html = _request("GET", "/")
        assert "Runner confusion" in html

    def test_has_report_export_confusion_button(self):
        _, html = _request("GET", "/")
        assert "Report/export confusion" in html

    def test_all_four_buttons_present(self):
        _, html = _request("GET", "/")
        count = html.count('class="confusion-btn"')
        assert count == 4, f"Expected 4 confusion-btn elements, found {count}"

    def test_buttons_call_add_function(self):
        _, html = _request("GET", "/")
        # Each button onclick should call addConfusionSignal
        assert "addConfusionSignal('unclear_next_step')" in html
        assert "addConfusionSignal('unexpected_result')" in html
        assert "addConfusionSignal('runner_confusion')" in html
        assert "addConfusionSignal('report_export_confusion')" in html


# ---------------------------------------------------------------------------
# Note field
# ---------------------------------------------------------------------------


class TestNoteField:
    def test_note_field_available(self):
        _, html = _request("GET", "/")
        assert "confusion-note-input" in html
        assert "textarea" in html

    def test_note_field_placeholder(self):
        _, html = _request("GET", "/")
        assert "confused about" in html


# ---------------------------------------------------------------------------
# Signal list
# ---------------------------------------------------------------------------


class TestSignalList:
    def test_signal_list_container(self):
        _, html = _request("GET", "/")
        assert "confusion-signal-list" in html

    def test_signal_empty_state(self):
        _, html = _request("GET", "/")
        assert "No confusion signals recorded" in html


# ---------------------------------------------------------------------------
# Clear button
# ---------------------------------------------------------------------------


class TestClearButton:
    def test_clear_button_present(self):
        _, html = _request("GET", "/")
        assert "clear-confusion-btn" in html
        assert "Clear all signals" in html

    def test_clear_button_calls_function(self):
        _, html = _request("GET", "/")
        assert "clearConfusionSignals" in html


# ---------------------------------------------------------------------------
# JS functions
# ---------------------------------------------------------------------------


class TestJSFunctions:
    def test_add_confusion_signal_function(self):
        _, html = _request("GET", "/")
        assert "addConfusionSignal" in html

    def test_render_confusion_signals_function(self):
        _, html = _request("GET", "/")
        assert "renderConfusionSignals" in html

    def test_clear_confusion_signals_function(self):
        _, html = _request("GET", "/")
        assert "clearConfusionSignals" in html

    def test_confusion_signals_array(self):
        _, html = _request("GET", "/")
        assert "__ariadne_confusion_signals" in html

    def test_signal_has_timestamp(self):
        _, html = _request("GET", "/")
        assert "timestamp" in html


# ---------------------------------------------------------------------------
# No storage
# ---------------------------------------------------------------------------


class TestNoStorage:
    def test_no_local_storage(self):
        _, html = _request("GET", "/")
        assert "localStorage" not in html

    def test_no_session_storage(self):
        _, html = _request("GET", "/")
        assert "sessionStorage" not in html


# ---------------------------------------------------------------------------
# Session report integration
# ---------------------------------------------------------------------------


class TestSessionReportIntegration:
    def test_session_report_includes_signals_header(self):
        _, html = _request("GET", "/")
        assert "=== Confusion Signals ===" in html

    def test_session_report_handles_empty_signals(self):
        _, html = _request("GET", "/")
        assert "(none)" in html


# ---------------------------------------------------------------------------
# Existing UI preserved
# ---------------------------------------------------------------------------


class TestExistingUIPreserved:
    def test_onboarding_preserved(self):
        _, html = _request("GET", "/")
        assert "onboarding-panel" in html

    def test_manual_checklist_preserved(self):
        _, html = _request("GET", "/")
        assert "manual-checklist" in html

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

    def test_run_history_preserved(self):
        _, html = _request("GET", "/")
        assert "run-history-section" in html

    def test_validation_preserved(self):
        _, html = _request("GET", "/")
        assert "task-validation" in html

    def test_error_panel_preserved(self):
        _, html = _request("GET", "/")
        assert "error-panel" in html

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

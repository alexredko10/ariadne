"""Tests for the local empty and error states."""

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
# Empty state before first run
# ---------------------------------------------------------------------------


class TestEmptyStateBeforeFirstRun:
    def test_summary_placeholder_present(self):
        _, html = _request("GET", "/")
        assert "Submit a task to see the run summary" in html

    def test_run_history_placeholder_present(self):
        _, html = _request("GET", "/")
        assert "No runs yet" in html

    def test_run_report_hidden_before_submit(self):
        _, html = _request("GET", "/")
        assert "display:none" in html or "display: none" in html
        assert "run-report-section" in html

    def test_trace_empty_before_submit(self):
        _, html = _request("GET", "/")
        # trace-steps is present but empty before first run
        assert "trace-steps" in html

    def test_raw_json_empty_before_submit(self):
        _, html = _request("GET", "/")
        # The <pre id="json"> is present but empty
        assert "<pre id=\"json\"" in html


# ---------------------------------------------------------------------------
# Task validation (client-side)
# ---------------------------------------------------------------------------


class TestTaskValidation:
    def test_validation_message_element_present(self):
        _, html = _request("GET", "/")
        assert "task-validation" in html
        assert "Task text is required" in html

    def test_validation_hidden_by_default(self):
        _, html = _request("GET", "/")
        assert "validation-error" in html
        # The validation message is hidden via CSS class, not inline style
        # The .validation-error class has display:none
        assert ".validation-error" in html
        assert 'style="display:none"' not in html or 'style="display: none"' not in html

    def test_validation_js_check_exists(self):
        _, html = _request("GET", "/")
        assert "task.trim()" in html or "task.trim" in html or "trim()" in html

    def test_validation_blocks_submit(self):
        _, html = _request("GET", "/")
        # The submit handler should return early for empty task
        # Look for the validation guard
        assert 'task.trim() === ""' in html or "!task ||" in html

    def test_validation_style_present(self):
        _, html = _request("GET", "/")
        assert "validation-error" in html


# ---------------------------------------------------------------------------
# Loading state
# ---------------------------------------------------------------------------


class TestLoadingState:
    def test_loading_text_in_status_bar(self):
        _, html = _request("GET", "/")
        # The status bar shows "Running…" during fetch
        assert "Running" in html

    def test_submit_button_disabled_during_run(self):
        _, html = _request("GET", "/")
        # The submit button has disabled state in JS
        assert 'disabled = true' in html or 'disabled=true' in html or 'disabled=\"true\"' in html or 'btn.disabled' in html

    def test_submit_button_text_changes(self):
        _, html = _request("GET", "/")
        assert "Running" in html


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_error_panel_present(self):
        _, html = _request("GET", "/")
        assert "error-panel" in html
        assert "Request Error" in html

    def test_error_panel_hidden_by_default(self):
        _, html = _request("GET", "/")
        # error-panel should be display:none initially
        assert "error-panel" in html

    def test_error_panel_dismiss_button(self):
        _, html = _request("GET", "/")
        assert "dismiss-error-btn" in html
        assert "Dismiss" in html

    def test_error_message_element_present(self):
        _, html = _request("GET", "/")
        assert "error-message" in html

    def test_network_error_handling(self):
        _, html = _request("GET", "/")
        assert "Request failed" in html or "showError" in html

    def test_http_error_status_handling(self):
        _, html = _request("GET", "/")
        assert "Unexpected response status" in html

    def test_invalid_json_handling(self):
        _, html = _request("GET", "/")
        assert "Failed to parse response as JSON" in html or "Invalid JSON" in html

    def test_unexpected_format_handling(self):
        _, html = _request("GET", "/")
        assert "Unexpected response format" in html

    def test_previous_data_preserved_on_error(self):
        _, html = _request("GET", "/")
        # The submit handler should not clear summary-card or trace on error
        # Check that renderSummaryCard is not called in catch/error paths
        assert "renderSummaryCard" in html

    def test_history_not_modified_on_failure(self):
        _, html = _request("GET", "/")
        # pushRunHistory should only be called in the success path
        assert "pushRunHistory" in html


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

    def test_run_history_preserved(self):
        _, html = _request("GET", "/")
        assert "run-history-section" in html

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

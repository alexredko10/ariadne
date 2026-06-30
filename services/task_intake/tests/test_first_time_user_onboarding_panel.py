"""Tests for the first-time user onboarding panel."""

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
# Onboarding panel presence and content
# ---------------------------------------------------------------------------


class TestOnboardingPanel:
    def test_page_contains_onboarding_panel(self):
        _, html = _request("GET", "/")
        assert "onboarding-panel" in html or "Welcome to Ariadne" in html

    def test_onboarding_header(self):
        _, html = _request("GET", "/")
        assert "Welcome to Ariadne" in html

    def test_onboarding_explains_local_noop(self):
        _, html = _request("GET", "/")
        assert "Local/no-op" in html or "local/no" in html.lower()

    def test_onboarding_explains_docker_opt_in(self):
        _, html = _request("GET", "/")
        assert "Docker agent" in html
        assert "opt-in" in html.lower()

    def test_onboarding_has_step_by_step(self):
        _, html = _request("GET", "/")
        assert "Step-by-step" in html or "Step-by-step" in html
        # At least a few steps mentioned
        assert "Select a guided scenario" in html
        assert "Choose a runner" in html
        assert "Click Submit" in html

    def test_onboarding_has_dismiss_button(self):
        _, html = _request("GET", "/")
        assert "dismiss-onboarding-btn" in html
        assert "Dismiss" in html

    def test_dismiss_in_memory_only(self):
        _, html = _request("GET", "/")
        # No localStorage or sessionStorage
        assert "localStorage" not in html
        assert "sessionStorage" not in html

    def test_dismiss_js_flag_exists(self):
        _, html = _request("GET", "/")
        assert "__onboarding_dismissed" in html

    def test_dismiss_js_function_exists(self):
        _, html = _request("GET", "/")
        assert "dismissOnboarding" in html


# ---------------------------------------------------------------------------
# Existing explanation panel preserved
# ---------------------------------------------------------------------------


class TestExplanationPanelPreserved:
    def test_explanation_panel_present(self):
        _, html = _request("GET", "/")
        assert "explanation" in html

    def test_explanation_content_present(self):
        _, html = _request("GET", "/")
        assert "local harness" in html or "execution request" in html

    def test_onboarding_above_explanation(self):
        _, html = _request("GET", "/")
        # Look for the HTML element IDs, not just substring matches
        # Find the opening tag elements in the HTML body
        onb_tag = '<div id="onboarding-panel"'
        exp_tag = '<div id="explanation"'
        onb_idx = html.index(onb_tag) if onb_tag in html else -1
        exp_idx = html.index(exp_tag) if exp_tag in html else -1
        assert onb_idx >= 0, "onboarding-panel element not found"
        assert exp_idx >= 0, "explanation element not found"
        assert onb_idx < exp_idx, "onboarding panel must appear above explanation"


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

    def test_validation_preserved(self):
        _, html = _request("GET", "/")
        assert "task-validation" in html

    def test_error_panel_preserved(self):
        _, html = _request("GET", "/")
        assert "error-panel" in html

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

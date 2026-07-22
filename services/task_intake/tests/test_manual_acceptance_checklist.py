"""Tests for the manual acceptance checklist."""

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
# Checklist panel presence
# ---------------------------------------------------------------------------


class TestChecklistPanel:
    def test_page_contains_checklist(self):
        _, html = _request("GET", "/")
        assert "Manual Acceptance Checklist" in html

    def test_checklist_has_header(self):
        _, html = _request("GET", "/")
        assert "Manual Acceptance Checklist" in html

    def test_checklist_has_counter(self):
        _, html = _request("GET", "/")
        assert "checklist-counter" in html

    def test_checklist_counter_starts_at_0(self):
        _, html = _request("GET", "/")
        assert "0/15" in html

    def test_checklist_has_reset_button(self):
        _, html = _request("GET", "/")
        assert "reset-checklist-btn" in html
        assert "Reset all" in html


# ---------------------------------------------------------------------------
# 15 checklist items
# ---------------------------------------------------------------------------


class TestChecklistItems:
    def test_checklist_has_15_items(self):
        _, html = _request("GET", "/")
        # Count only checkbox input elements with the class, not JS references
        count = html.count('class="checklist-cb"')
        assert count == 15, f"Expected 15 checkbox inputs, found {count}"

    def test_item_1_onboarding(self):
        _, html = _request("GET", "/")
        assert "First-time onboarding" in html

    def test_item_2_scenario(self):
        _, html = _request("GET", "/")
        assert "Scenario can be selected" in html

    def test_item_3_submit(self):
        _, html = _request("GET", "/")
        assert "Task can be submitted" in html

    def test_item_4_local_noop_default(self):
        _, html = _request("GET", "/")
        assert "Local/no-op remains default" in html

    def test_item_5_docker_opt_in(self):
        _, html = _request("GET", "/")
        assert "Docker-agent remains opt-in" in html

    def test_item_6_summary_card(self):
        _, html = _request("GET", "/")
        assert "Summary card is visible" in html

    def test_item_7_trace(self):
        _, html = _request("GET", "/")
        assert "Execution trace is visible" in html

    def test_item_8_structured(self):
        _, html = _request("GET", "/")
        assert "Structured result is visible" in html

    def test_item_9_raw_json(self):
        _, html = _request("GET", "/")
        assert "Raw JSON remains available" in html

    def test_item_10_feedback(self):
        _, html = _request("GET", "/")
        assert "Feedback can be captured" in html

    def test_item_11_session_report(self):
        _, html = _request("GET", "/")
        assert "Session report can be generated" in html

    def test_item_12_run_report(self):
        _, html = _request("GET", "/")
        assert "Run report can be copied" in html or "Run report can be copied/exported" in html

    def test_item_13_history(self):
        _, html = _request("GET", "/")
        assert "Local run history updates" in html

    def test_item_14_empty_validation(self):
        _, html = _request("GET", "/")
        assert "Empty task validation" in html

    def test_item_15_error_preserves(self):
        _, html = _request("GET", "/")
        assert "Error state preserves" in html


# ---------------------------------------------------------------------------
# Progress counter behavior
# ---------------------------------------------------------------------------


class TestProgressCounter:
    def test_counter_updates_function(self):
        _, html = _request("GET", "/")
        assert "updateChecklistCounter" in html

    def test_counter_all_passed_text(self):
        _, html = _request("GET", "/")
        assert "All checks passed" in html

    def test_counter_uses_query_selector(self):
        _, html = _request("GET", "/")
        assert "checklist-cb" in html


# ---------------------------------------------------------------------------
# Reset behavior
# ---------------------------------------------------------------------------


class TestResetBehavior:
    def test_reset_function_checks_all(self):
        _, html = _request("GET", "/")
        assert "reset-checklist-btn" in html
        # The reset handler iterates over all checkboxes and unchecks them
        assert 'checked = false' in html or 'checked=false' in html


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
# Existing UI preserved
# ---------------------------------------------------------------------------


class TestExistingUIPreserved:
    def test_onboarding_preserved(self):
        _, html = _request("GET", "/")
        assert "onboarding-panel" in html

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

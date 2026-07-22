"""Tests for the copy/export local run report."""

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
# Run report panel
# ---------------------------------------------------------------------------


class TestRunReportPanel:
    def test_page_contains_run_report_section(self):
        _, html = _request("GET", "/")
        assert "run-report-section" in html or "Run Report" in html

    def test_run_report_has_generate_button(self):
        _, html = _request("GET", "/")
        assert "Generate run report" in html or "generate-run-report-btn" in html

    def test_run_report_has_copy_button(self):
        _, html = _request("GET", "/")
        assert "Copy report" in html or "copy-run-report-btn" in html

    def test_run_report_has_download_button(self):
        _, html = _request("GET", "/")
        assert "Download report" in html or "download-run-report-btn" in html

    def test_run_report_has_output_textarea(self):
        _, html = _request("GET", "/")
        assert "run-report-output" in html

    def test_run_report_hidden_before_submit(self):
        _, html = _request("GET", "/")
        # run-report-section should have display:none by default
        assert 'id="run-report-section"' in html
        assert "display:none" in html or "display: none" in html

    def test_run_report_has_generate_function(self):
        _, html = _request("GET", "/")
        assert "generateRunReport" in html

    def test_run_report_has_blob_download(self):
        _, html = _request("GET", "/")
        assert "Blob" in html and "createObjectURL" in html

    def test_run_report_no_backend_route(self):
        body = json.dumps({"report": "test"}).encode("utf-8")
        status, _ = _request("POST", "/run-report", body=body)
        assert status == 404


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

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
    query_string: str = "",
) -> tuple[int, str]:
    # Parse query string from path if not explicitly provided
    if not query_string and "?" in path:
        path_part, qs_part = path.split("?", 1)
        path = path_part
        query_string = qs_part
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string.encode("utf-8"),
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


def _request(
    method: str,
    path: str,
    body: bytes | None = None,
    query_string: str = "",
) -> tuple[int, str]:
    return asyncio.run(_asgi_request(method, path, body=body, query_string=query_string))


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
# GET /runs evidence-backed run list
# ---------------------------------------------------------------------------


class TestGetRunsRoute:
    """Tests for the GET /runs evidence-backed run list route."""

    def test_empty_runs_root_returns_ok_true(self):
        """Empty runs directory returns ok=true with count=0."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is True
        assert data["count"] == 0
        assert data["runs"] == []

    def test_missing_runs_root_returns_ok_false(self):
        """Missing runs root returns ok=false with error."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        # Do not create the directory
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False
        assert "error" in data

    def test_complete_run_appears_in_list(self):
        """Complete run appears in list with status completed."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "test-run-001")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1",
            "run_id": "test-run-001",
            "status": "completed",
            "pipeline_status": "completed",
            "pipeline_final_action": "continue",
            "git_boundary_status": "approved",
            "reason_codes": ["completed"],
            "execution_attempted": True,
            "execution_results_summary": [],
            "finished_at": "2026-07-10T12:05:00Z",
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        manifest = {
            "schema_version": "1",
            "run_id": "test-run-001",
            "run_json_hash": "abc123",
            "files": ["run.json"],
        }
        with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is True
        assert data["count"] == 1
        assert data["runs"][0]["run_id"] == "test-run-001"
        assert data["runs"][0]["status"] == "completed"

    def test_blocked_run_appears_in_list(self):
        """Blocked run appears in list."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "blocked-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1",
            "run_id": "blocked-run",
            "status": "blocked",
            "pipeline_status": "completed",
            "git_boundary_status": "approved",
            "reason_codes": ["approval_required"],
            "execution_attempted": False,
            "execution_results_summary": [],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["count"] == 1
        assert data["runs"][0]["status"] == "blocked"

    def test_failed_run_appears_in_list(self):
        """Failed run appears in list."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "failed-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1",
            "run_id": "failed-run",
            "status": "failed",
            "pipeline_status": "completed",
            "git_boundary_status": "failed",
            "reason_codes": ["execution_failed"],
            "execution_attempted": True,
            "execution_results_summary": [],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["count"] == 1
        assert data["runs"][0]["status"] == "failed"

    def test_missing_manifest_indicator(self):
        """Missing manifest indicator is visible."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "test-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1",
            "run_id": "test-run",
            "status": "completed",
            "reason_codes": ["completed"],
            "execution_attempted": True,
            "execution_results_summary": [],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        # No manifest.json created
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["runs"][0]["manifest_available"] is False
        assert "manifest.json" in data["runs"][0]["missing_evidence"]

    def test_missing_run_report_indicator(self):
        """Missing run-report indicator is visible."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "test-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1",
            "run_id": "test-run",
            "status": "completed",
            "reason_codes": ["completed"],
            "execution_attempted": True,
            "execution_results_summary": [],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        manifest = {"schema_version": "1", "run_id": "test-run", "run_json_hash": "abc", "files": ["run.json"]}
        with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, sort_keys=True, ensure_ascii=False, indent=2)
        # No run-report.txt created
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["runs"][0]["run_report_available"] is False
        assert "run-report.txt" in data["runs"][0]["missing_evidence"]

    def test_malformed_run_json_indicator(self):
        """Malformed run.json indicator is visible."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "malformed-run")
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            f.write("{invalid json")
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert "run.json" in data["runs"][0]["malformed_evidence"]

    def test_pr_url_appears_when_present(self):
        """PR URL appears only when present."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "pr-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1",
            "run_id": "pr-run",
            "status": "completed",
            "reason_codes": ["completed"],
            "execution_attempted": True,
            "execution_results_summary": [
                {"operation": "gh_pr_create", "exit_code": "0", "pr_url": "https://github.com/owner/repo/pull/42"},
            ],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["runs"][0]["pr_url"] == "https://github.com/owner/repo/pull/42"

    def test_no_pr_url_fabricated(self):
        """No PR URL is fabricated when absent."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "no-pr-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1",
            "run_id": "no-pr-run",
            "status": "completed",
            "reason_codes": ["completed"],
            "execution_attempted": True,
            "execution_results_summary": [],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["runs"][0]["pr_url"] is None

    def test_reason_codes_serialized(self):
        """reason_codes are serialized in response."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "rc-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1",
            "run_id": "rc-run",
            "status": "completed",
            "reason_codes": ["completed", "some_warning"],
            "execution_attempted": True,
            "execution_results_summary": [],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["runs"][0]["reason_codes"] == ["completed", "some_warning"]

    def test_execution_attempted_serialized(self):
        """execution_attempted is serialized in response."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "ea-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1",
            "run_id": "ea-run",
            "status": "completed",
            "reason_codes": ["completed"],
            "execution_attempted": True,
            "execution_results_summary": [],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["runs"][0]["execution_attempted"] is True

    def test_deterministic_ordering(self):
        """Deterministic ordering is preserved (newest first)."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        for run_id in ["run-003", "run-001", "run-002"]:
            run_dir = os.path.join(runs_root, run_id)
            os.makedirs(run_dir, exist_ok=True)
            run_json = {
                "schema_version": "1",
                "run_id": run_id,
                "status": "completed",
                "reason_codes": ["completed"],
                "execution_attempted": True,
                "execution_results_summary": [],
            }
            with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
                json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["count"] == 3
        assert data["runs"][0]["run_id"] == "run-003"
        assert data["runs"][1]["run_id"] == "run-002"
        assert data["runs"][2]["run_id"] == "run-001"

    def test_payload_cleanliness_indicator(self):
        """Payload cleanliness available indicator is present."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "pc-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1",
            "run_id": "pc-run",
            "status": "completed",
            "reason_codes": ["completed"],
            "execution_attempted": True,
            "execution_results_summary": [],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert "payload_cleanliness_available" in data["runs"][0]
        assert data["runs"][0]["payload_cleanliness_available"] is False

    def test_readiness_indicator(self):
        """Readiness available indicator is present."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "rd-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1",
            "run_id": "rd-run",
            "status": "completed",
            "reason_codes": ["completed"],
            "execution_attempted": True,
            "execution_results_summary": [],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert "readiness_available" in data["runs"][0]
        assert data["runs"][0]["readiness_available"] is False

    def test_tests_use_temporary_fixtures(self):
        """Tests use temporary/local fixtures only."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        # Verify no real project .ariadne was accessed
        real_ariadne = os.path.join(os.getcwd(), ".ariadne", "runs")
        assert not os.path.exists(real_ariadne)

    def test_route_does_not_shell_out(self):
        """Route does not shell out."""
        import inspect
        from task_intake.server import app
        source = inspect.getsource(app)
        assert "subprocess" not in source
        assert "os.system" not in source
        assert "shell=True" not in source

    def test_route_does_not_run_agents(self):
        """Route does not run agents."""
        import inspect
        from task_intake.server import app
        source = inspect.getsource(app)
        assert "run_ariadne_task" not in source

    def test_route_does_not_mutate_runtime_state(self):
        """Route does not mutate runtime state."""
        import tempfile
        import os
        import json
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "test-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1",
            "run_id": "test-run",
            "status": "completed",
            "reason_codes": ["completed"],
            "execution_attempted": True,
            "execution_results_summary": [],
        }
        run_json_path = os.path.join(run_dir, "run.json")
        with open(run_json_path, "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        import hashlib
        with open(run_json_path, "rb") as f:
            hash_before = hashlib.sha256(f.read()).hexdigest()
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        with open(run_json_path, "rb") as f:
            hash_after = hashlib.sha256(f.read()).hexdigest()
        assert hash_before == hash_after


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

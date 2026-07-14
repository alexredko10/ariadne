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
        # Contract version present in error state
        assert data["ev_contract_version"] == "1"
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
        # Contract version present
        assert data["ev_contract_version"] == "1"
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


# ---------------------------------------------------------------------------
# Helper: create a complete run directory for detail tests
# ---------------------------------------------------------------------------


def _create_detail_run(tmp_dir: str, run_id: str, **kwargs) -> dict:
    """Create a run directory with run.json and optional evidence files."""
    import os
    import json

    runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)

    include_manifest = kwargs.get("include_manifest", True)
    include_report = kwargs.get("include_report", True)
    include_pr_url = kwargs.get("include_pr_url", False)
    malformed_manifest = kwargs.get("malformed_manifest", False)

    execution_results = [
        {"operation": "git_status", "exit_code": "0", "stdout": "ok", "stderr": ""},
        {"operation": "git_commit", "exit_code": "0", "stdout": "ok", "stderr": ""},
    ]
    if include_pr_url:
        execution_results.append({
            "operation": "gh_pr_create",
            "exit_code": "0",
            "stdout": "https://github.com/owner/repo/pull/99\n",
            "stderr": "",
            "pr_url": "https://github.com/owner/repo/pull/99",
        })

    run_json = {
        "schema_version": "1",
        "run_id": run_id,
        "status": kwargs.get("status", "completed"),
        "pipeline_status": kwargs.get("pipeline_status", "completed"),
        "git_boundary_status": kwargs.get("git_boundary_status", "approved"),
        "reason_codes": kwargs.get("reason_codes", ["completed"]),
        "execution_attempted": kwargs.get("execution_attempted", True),
        "execution_results_summary": execution_results,
        "started_at": "2026-07-10T12:00:00Z",
        "finished_at": "2026-07-10T12:05:00Z",
    }
    run_json_path = os.path.join(run_dir, "run.json")
    with open(run_json_path, "w", encoding="utf-8") as f:
        json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)

    manifest_path = os.path.join(run_dir, "manifest.json")
    if include_manifest:
        manifest = {
            "schema_version": "1",
            "run_id": run_id,
            "run_json_hash": "abc123def456",
            "files": ["run.json", "run-report.txt"],
        }
        if malformed_manifest:
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write("{bad manifest")
        else:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, sort_keys=True, ensure_ascii=False, indent=2)

    report_path = os.path.join(run_dir, "run-report.txt")
    if include_report:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("Ariadne Run Report\nRun ID: " + run_id + "\nStatus: completed\n")

    return {
        "runs_root": runs_root,
        "run_dir": run_dir,
        "run_json_path": run_json_path,
        "manifest_path": manifest_path,
        "report_path": report_path,
    }


# ---------------------------------------------------------------------------
# GET /runs/<run_id> detail endpoint tests
# ---------------------------------------------------------------------------


class TestRunDetailEndpoint:
    """Tests for the GET /runs/<run_id> detail endpoint."""

    def test_complete_run_detail_response(self, tmp_path):
        """Complete run detail returns ok=true with summary, detail, and evidence."""
        import os
        paths = _create_detail_run(str(tmp_path), "run-001")
        status, raw = _request("GET", "/runs/run-001?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        # Contract version present
        assert data["ev_contract_version"] == "1"
        assert data["ok"] is True
        assert data["summary"] is not None
        assert data["summary"]["run_id"] == "run-001"
        assert data["summary"]["status"] == "completed"
        assert data["detail"] is not None
        assert len(data["detail"]["execution_results"]) > 0
        assert "manifest_files" in data["detail"]
        assert data["detail"]["report_preview"] is not None
        assert "Ariadne Run Report" in data["detail"]["report_preview"]
        assert len(data["detail"]["evidence_paths"]) > 0

    def test_blocked_run_detail_response(self):
        """Blocked run detail reflects correct status."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _create_detail_run(tmp_dir, "blocked-run",
                                   status="blocked",
                                   reason_codes=["approval_required"],
                                   execution_attempted=False)
        status, raw = _request("GET", "/runs/blocked-run?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["summary"]["status"] == "blocked"
        assert data["summary"]["execution_attempted"] is False

    def test_unknown_run_id(self):
        """Unknown run_id returns ok=false with error."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        status, raw = _request("GET", "/runs/nonexistent-run?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        # Contract version present in error state
        assert data["ev_contract_version"] == "1"
        assert data["ok"] is False
        assert data["error"] is not None

    def test_missing_run_json(self):
        """Missing run.json returns ok=false with missing notice."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "no-json-run")
        os.makedirs(run_dir, exist_ok=True)
        status, raw = _request("GET", "/runs/no-json-run?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False
        assert len(data["missing"]) > 0
        assert any("run.json" in n["expected_path"] for n in data["missing"])

    def test_missing_manifest(self):
        """Missing manifest returns ok=false with missing notice for manifest."""
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _create_detail_run(tmp_dir, "no-manifest-run", include_manifest=False)
        status, raw = _request("GET", "/runs/no-manifest-run?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False
        assert len(data["missing"]) > 0
        assert any("manifest.json" in n["expected_path"] for n in data["missing"])

    def test_malformed_manifest(self):
        """Malformed manifest returns ok=false with malformed notice."""
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _create_detail_run(tmp_dir, "bad-manifest-run", malformed_manifest=True)
        status, raw = _request("GET", "/runs/bad-manifest-run?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False
        assert len(data["malformed"]) > 0
        assert any("manifest.json" in n["expected_path"] for n in data["malformed"])

    def test_missing_run_report(self):
        """Missing run-report returns ok=false with missing notice."""
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _create_detail_run(tmp_dir, "no-report-run", include_report=False)
        status, raw = _request("GET", "/runs/no-report-run?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False
        assert len(data["missing"]) > 0
        assert any("run-report.txt" in n["expected_path"] for n in data["missing"])

    def test_execution_results_serialization(self):
        """Execution results are serialized with operation and exit_code."""
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _create_detail_run(tmp_dir, "exec-run")
        status, raw = _request("GET", "/runs/exec-run?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        er = data["detail"]["execution_results"]
        assert len(er) >= 2
        ops = [r.get("operation") for r in er]
        assert "git_status" in ops
        assert "git_commit" in ops

    def test_manifest_files_serialization(self):
        """Manifest files array is present."""
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _create_detail_run(tmp_dir, "mf-run")
        status, raw = _request("GET", "/runs/mf-run?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert isinstance(data["detail"]["manifest_files"], list)
        assert "run.json" in data["detail"]["manifest_files"]

    def test_pr_url_present_when_persisted(self):
        """PR URL is present only when in persisted evidence."""
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _create_detail_run(tmp_dir, "pr-run", include_pr_url=True)
        status, raw = _request("GET", "/runs/pr-run?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["summary"]["pr_url"] == "https://github.com/owner/repo/pull/99"

    def test_pr_url_absent_when_not_persisted(self):
        """PR URL is absent when not in persisted evidence."""
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _create_detail_run(tmp_dir, "no-pr-run", include_pr_url=False)
        status, raw = _request("GET", "/runs/no-pr-run?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["summary"]["pr_url"] is None

    def test_payload_cleanliness_null(self):
        """payload_cleanliness is null when unavailable."""
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _create_detail_run(tmp_dir, "pc-run")
        status, raw = _request("GET", "/runs/pc-run?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["payload_cleanliness"] is None

    def test_readiness_null(self):
        """readiness is null when unavailable."""
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _create_detail_run(tmp_dir, "rd-run")
        status, raw = _request("GET", "/runs/rd-run?runs_root=" + paths["runs_root"])
        assert status == 200
        data = json.loads(raw)
        assert data["readiness"] is None

    def test_traversal_run_id_rejected(self):
        """Traversal-like run_id returns ok=false, error."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        status, raw = _request("GET", "/runs/../etc?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False
        assert "error" in data

    def test_slash_in_run_id_rejected(self):
        """Run_id with slash returns ok=false."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        status, raw = _request("GET", "/runs/bad/run?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False

    def test_empty_run_id_rejected(self):
        """Empty run_id returns ok=false."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        # /runs/ with no run_id after the slash
        status, raw = _request("GET", "/runs/?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False

    def test_endpoint_read_only_no_mutation(self):
        """Detail endpoint does not mutate persisted artifacts."""
        import tempfile
        import os
        import hashlib
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        paths = _create_detail_run(tmp_dir, "mut-test")
        # Record hash before
        with open(paths["run_json_path"], "rb") as f:
            hash_before = hashlib.sha256(f.read()).hexdigest()
        status, raw = _request("GET", "/runs/mut-test?runs_root=" + paths["runs_root"])
        with open(paths["run_json_path"], "rb") as f:
            hash_after = hashlib.sha256(f.read()).hexdigest()
        assert hash_before == hash_after


# ---------------------------------------------------------------------------
# Detail panel page tests
# ---------------------------------------------------------------------------


class TestDetailPanel:
    """Tests for the run detail panel in the page."""

    def test_get_only_boundary(self):
        """Only GET method is handled for detail routes."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            status, raw = _request(method, "/runs/some-run?runs_root=" + runs_root)
            # Non-GET methods on /runs/<id> fall through to the catch-all (404)
            assert status == 404

    def test_existing_runs_list_still_works(self):
        """Existing GET /runs regression - list route still works."""
        import tempfile
        import os
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is True
        assert "count" in data
        assert "runs" in data

    def test_existing_page_renders(self):
        """Page at GET / still renders with all existing sections."""
        _, html = _request("GET", "/")
        assert "Ariadne" in html
        assert "summary-card" in html
        assert "Execution Trace" in html
        assert "structured-view" in html

    def test_page_contains_detail_panel(self):
        """Page contains #run-detail-panel div."""
        _, html = _request("GET", "/")
        assert "run-detail-panel" in html

    def test_page_contains_detail_js_functions(self):
        """Page contains fetchRunDetail and renderRunDetail JS functions."""
        _, html = _request("GET", "/")
        assert "fetchRunDetail" in html
        assert "renderRunDetail" in html

    def test_run_list_entries_are_clickable(self):
        """Run-list entries have clickable View buttons."""
        _, html = _request("GET", "/")
        # Verify fetchRunDetail onclick exists in the page JS
        assert "fetchRunDetail(" in html
        assert "View</button>" in html

    def test_selection_fetches_detail_route(self):
        """Selection uses fetch to the exact detail route."""
        _, html = _request("GET", "/")
        assert 'fetch("/runs/"' in html or "fetch(\"/runs/\"" in html

    def test_detail_panel_sections(self):
        """Required detail sections are rendered in JS."""
        _, html = _request("GET", "/")
        assert "Execution Results" in html
        assert "Manifest Files" in html
        assert "Report Preview" in html
        assert "Evidence Paths" in html
        assert "Missing Evidence" in html
        assert "Malformed Evidence" in html

    def test_missing_evidence_rendered(self):
        """Missing evidence notice rendering exists."""
        _, html = _request("GET", "/")
        assert 'data.missing' in html

    def test_malformed_evidence_rendered(self):
        """Malformed evidence notice rendering exists."""
        _, html = _request("GET", "/")
        assert 'data.malformed' in html

    def test_no_localstorage_persistence(self):
        """No localStorage or sessionStorage addition."""
        _, html = _request("GET", "/")
        # The existing PR 0139 test already checks for this; we verify no new ones
        assert "localStorage" not in html
        assert "sessionStorage" not in html

    def test_no_ariadne_writes(self):
        """No .ariadne write paths in the server code."""
        import inspect
        from task_intake.server import app
        source = inspect.getsource(app)
        # The detail route should not create directories or write files
        assert "os.makedirs" not in source
        assert 'open(' not in source or 'open(path, "r"' in source or 'open(path, "rb"' in source

    def test_no_shell_out_in_implementation(self):
        """No real git, gh, Docker, subprocess, or agent execution."""
        import inspect
        from task_intake.server import app
        source = inspect.getsource(app)
        assert "subprocess" not in source
        assert "os.system" not in source
        assert "shell=True" not in source
        assert "docker" not in source.lower()
        assert "run_ariadne_task" not in source

    def test_unavailable_values_rendered(self):
        """Unavailable values (payload_cleanliness, readiness) are rendered."""
        _, html = _request("GET", "/")
        assert "Payload cleanliness" in html
        assert "Readiness" in html

    def test_reason_codes_section_exists(self):
        """Reason codes section exists in the detail panel JS."""
        _, html = _request("GET", "/")
        assert "Reason codes" in html

"""Tests for the Artifact Workspace Shell — PR 0143 + PR 0144."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile


# ---------------------------------------------------------------------------
# ASGI test harness (matching existing _request pattern)
# ---------------------------------------------------------------------------


async def _asgi_request(
    method: str,
    path: str,
    body: bytes | None = None,
    query_string: str = "",
) -> tuple[int, str]:
    from task_intake.server import app

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
# Workspace Route Tests
# ---------------------------------------------------------------------------


class TestWorkspaceRoute:
    """Tests for the GET /workspace route."""

    def test_get_workspace_returns_200(self):
        """GET /workspace returns HTTP 200."""
        status, _ = _request("GET", "/workspace")
        assert status == 200

    def test_get_workspace_content_type_html(self):
        """GET /workspace returns text/html content type."""
        status, html = _request("GET", "/workspace")
        assert status == 200
        assert "<!DOCTYPE html>" in html
        assert "<html" in html

    def test_workspace_root_exists(self):
        """Response contains #artifact-workspace root element."""
        _, html = _request("GET", "/workspace")
        assert 'id="artifact-workspace"' in html

    def test_workspace_has_page_title(self):
        """Document has correct title."""
        _, html = _request("GET", "/workspace")
        assert "<title>Ariadne — Artifact Workspace</title>" in html

    def test_workspace_has_h1_heading(self):
        """Page has h1 heading with Artifact Workspace."""
        _, html = _request("GET", "/workspace")
        assert "<h1>Artifact Workspace</h1>" in html


class TestFourZoneStructure:
    """Tests for the four semantic zones."""

    def test_zone_timeline_exists(self):
        """Left timeline zone exists."""
        _, html = _request("GET", "/workspace")
        assert 'id="zone-timeline"' in html

    def test_zone_timeline_heading(self):
        """Timeline zone has h2 heading 'Timeline'."""
        _, html = _request("GET", "/workspace")
        assert 'id="zone-timeline-heading"' in html
        assert "<h2 id=\"zone-timeline-heading\">Timeline</h2>" in html

    def test_zone_canvas_exists(self):
        """Center artifact canvas zone exists."""
        _, html = _request("GET", "/workspace")
        assert 'id="zone-canvas"' in html

    def test_zone_canvas_heading(self):
        """Canvas zone has h2 heading 'Artifact Canvas'."""
        _, html = _request("GET", "/workspace")
        assert 'id="zone-canvas-heading"' in html
        assert "<h2 id=\"zone-canvas-heading\">Artifact Canvas</h2>" in html

    def test_zone_gates_proofs_exists(self):
        """Right gates and proofs zone exists."""
        _, html = _request("GET", "/workspace")
        assert 'id="zone-gates-proofs"' in html

    def test_zone_gates_proofs_heading(self):
        """Gates zone has h2 heading 'Gates & Proofs'."""
        _, html = _request("GET", "/workspace")
        assert 'id="zone-gates-proofs-heading"' in html
        assert "Gates &amp; Proofs" in html

    def test_zone_logs_captures_exists(self):
        """Bottom logs and captures zone exists."""
        _, html = _request("GET", "/workspace")
        assert 'id="zone-logs-captures"' in html

    def test_zone_logs_captures_heading(self):
        """Logs zone has h2 heading 'Logs & Captures'."""
        _, html = _request("GET", "/workspace")
        assert 'id="zone-logs-captures-heading"' in html
        assert "Logs &amp; Captures" in html


class TestPlaceholderStates:
    """Tests that placeholder states do not fabricate evidence."""

    def test_canvas_has_placeholder(self):
        """Canvas zone shows placeholder text."""
        _, html = _request("GET", "/workspace")
        assert "Select a run from the timeline to view artifacts" in html

    def test_gates_has_placeholder(self):
        """Gates zone shows placeholder text."""
        _, html = _request("GET", "/workspace")
        assert "No gate checks available" in html

    def test_logs_has_placeholder(self):
        """Logs zone shows placeholder text."""
        _, html = _request("GET", "/workspace")
        assert "No logs available" in html

    def test_no_fabricated_evidence_in_canvas(self):
        """Canvas does not claim to have real evidence."""
        _, html = _request("GET", "/workspace")
        assert "accepted" not in html.lower() or "No artifact loaded" in html

    def test_no_fabricated_evidence_in_gates(self):
        """Gates zone does not claim to have real gate results."""
        _, html = _request("GET", "/workspace")
        assert "Gates and proofs will appear after" in html

    def test_no_fabricated_evidence_in_logs(self):
        """Logs zone does not claim to have real logs."""
        _, html = _request("GET", "/workspace")
        assert "Captured execution output will appear here" in html


class TestProductionFixtureRemoval:
    """PR 0144: Tests that production mock entries are no longer the data source."""

    def test_production_fixture_notice_absent(self):
        """Fixture notice div is no longer present in the HTML."""
        _, html = _request("GET", "/workspace")
        assert "fixture-notice" not in html
        assert "Fixture data" not in html

    def test_no_production_mock_run_ids(self):
        """Production mock run IDs are not embedded in the static HTML."""
        _, html = _request("GET", "/workspace")
        assert "mock-run-001" not in html
        assert "mock-run-002" not in html

    def test_workspace_module_has_no_fixture_constant(self):
        """The _WORKSPACE_FIXTURE constant is removed from the module."""
        import inspect
        from task_intake import artifact_workspace
        members = set(dir(artifact_workspace))
        assert "_WORKSPACE_FIXTURE" not in members
        assert "_WORKSPACE_FIXTURE_JSON" not in members

    def test_live_fetch_present(self):
        """The page includes fetch('/runs') for live data loading."""
        _, html = _request("GET", "/workspace")
        assert 'fetch("/runs")' in html

    def test_render_is_deterministic_and_live(self):
        """Workspace render no longer embeds fixture data; it's live-driven."""
        from task_intake.artifact_workspace import render_artifact_workspace
        html1 = render_artifact_workspace()
        html2 = render_artifact_workspace()
        assert html1 == html2
        # The render output should contain the fetchRuns call, not fixture entries
        assert "function fetchRuns" in html1
        assert "fetchRuns();" in html1


class TestLiveRunListStates:
    """PR 0144: Tests for live run list state behavior in the page structure."""

    def test_loading_state_text_present(self):
        """Loading state text exists in the JS."""
        _, html = _request("GET", "/workspace")
        assert "Loading runs..." in html

    def test_empty_state_text_present(self):
        """Empty state text exists."""
        _, html = _request("GET", "/workspace")
        assert "No runs available. Submit a task to see timeline entries." in html

    def test_root_error_state_text_present(self):
        """Missing/unreadable root state text exists."""
        _, html = _request("GET", "/workspace")
        assert "Runs directory not available. Run a task to create run evidence." in html

    def test_version_mismatch_state_text_present(self):
        """Version mismatch state text exists."""
        _, html = _request("GET", "/workspace")
        assert "Contract version mismatch" in html

    def test_invalid_payload_state_text_present(self):
        """Invalid payload state text exists."""
        _, html = _request("GET", "/workspace")
        assert "Unexpected response format. Could not parse run list." in html

    def test_fetch_failure_state_text_present(self):
        """Fetch failure state text exists."""
        _, html = _request("GET", "/workspace")
        assert "Failed to load run data. Check that the server is running." in html

    def test_malformed_entry_text_present(self):
        """Malformed entry handling exists."""
        _, html = _request("GET", "/workspace")
        assert "(incomplete)" in html

    def test_ev_contract_version_validation_present(self):
        """ev_contract_version '1' validation is present."""
        _, html = _request("GET", "/workspace")
        assert "ev_contract_version" in html
        assert '!== "1"' in html

    def test_envelope_validation_present(self):
        """Envelope validation (ok, runs) is present."""
        _, html = _request("GET", "/workspace")
        assert "typeof data.ok" in html
        assert "Array.isArray(data.runs)" in html

    def test_show_timeline_state_function_exists(self):
        """showTimelineState function exists for state management."""
        _, html = _request("GET", "/workspace")
        assert "function showTimelineState" in html

    def test_entry_has_click_and_keydown_handlers(self):
        """Each entry has click and keydown event listeners (not inline handlers)."""
        _, html = _request("GET", "/workspace")
        assert "addEventListener" in html


class TestLiveRunListRender:
    """PR 0144: Tests for live run list rendering fields."""

    def test_run_id_rendering_present(self):
        """run_id is rendered."""
        _, html = _request("GET", "/workspace")
        assert "timeline-run-id" in html

    def test_status_rendering_present(self):
        """status is rendered as visible text."""
        _, html = _request("GET", "/workspace")
        assert "timeline-status" in html

    def test_status_is_text_not_color_only(self):
        """Status text is explicitly set via textContent, not only color class."""
        _, html = _request("GET", "/workspace")
        assert 'className = "timeline-status status-"' in html  # status snippet

    def test_branch_unavailable_rendering_present(self):
        """branch: not available text is rendered."""
        _, html = _request("GET", "/workspace")
        assert "branch: not available" in html

    def test_readiness_unavailable_rendering_present(self):
        """readiness: not available text is rendered."""
        _, html = _request("GET", "/workspace")
        assert "readiness: not available" in html

    def test_created_at_semantics_present(self):
        """Created at label is used (not generated_at)."""
        _, html = _request("GET", "/workspace")
        assert "Created at:" in html
        assert "generated_at" not in html

    def test_reason_codes_rendering_present(self):
        """Reason codes rendering exists."""
        _, html = _request("GET", "/workspace")
        assert "timeline-reason-codes" in html

    def test_missing_evidence_rendering_present(self):
        """Missing evidence indicator exists."""
        _, html = _request("GET", "/workspace")
        assert "timeline-evidence-missing" in html
        assert "Missing:" in html

    def test_malformed_evidence_rendering_present(self):
        """Malformed evidence indicator exists."""
        _, html = _request("GET", "/workspace")
        assert "timeline-evidence-malformed" in html
        assert "Malformed:" in html

    def test_safe_pr_url_rendering_present(self):
        """Safe PR URL rendering exists with isSafeUrl check."""
        _, html = _request("GET", "/workspace")
        assert "function isSafeUrl" in html
        assert ".rel = " in html

    def test_semantic_list_structure(self):
        """Semantic list structure uses role='list' and accessible label."""
        _, html = _request("GET", "/workspace")
        assert 'role="list"' in html
        assert 'aria-label="Local run list"' in html


class TestLiveSafeRendering:
    """PR 0144: Tests for safe rendering of live data."""

    def test_textcontent_used_for_untrusted_values(self):
        """textContent is used for all untrusted value rendering."""
        _, html = _request("GET", "/workspace")
        # Multiple textContent usages for different fields
        assert "textContent" in html

    def test_no_inline_onclick_from_data(self):
        """No inline onclick built from run data values."""
        _, html = _request("GET", "/workspace")
        assert "onclick=" not in html

    def test_no_inline_onkeydown_from_data(self):
        """No inline onkeydown built from run data values."""
        _, html = _request("GET", "/workspace")
        assert "onkeydown=" not in html

    def test_no_innerHTML_concatenation_of_run_values(self):
        """No innerHTML concatenation with run field values."""
        _, html = _request("GET", "/workspace")
        # The innerHTML in escHtml is for escaping. The state-clear pattern
        # (entriesDiv.innerHTML = "") is for clearing the container.
        # Verify that innerHTML is not used for inserting run data content.
        # Count innerHTML occurrences — should only be in escHtml and clearing.
        inner_count = html.count(".innerHTML")
        # escHtml: "return div.innerHTML" + showTimelineState clearing: "entriesDiv.innerHTML = """
        # ": renderRunList clearing: "entriesDiv.innerHTML = """
        # Both are safe clearing/escaping patterns.
        assert inner_count == 3, f"Expected 3 innerHTML occurrences, got {inner_count}"
        # No innerHTML used to set content from run values
        assert ".innerHTML = html" not in html

    def test_safe_url_validation_present(self):
        """isSafeUrl validates http/https prefix."""
        _, html = _request("GET", "/workspace")
        assert 'http://"' in html or 'https://"' in html or 'indexOf("http://")' in html


class TestLiveAccessibility:
    """PR 0144: Tests for accessibility of live run list."""

    def test_list_has_accessible_label(self):
        """The timeline entries container has accessible label."""
        _, html = _request("GET", "/workspace")
        assert 'aria-label="Local run list"' in html

    def test_entries_have_aria_label(self):
        """Each entry has aria-label with run_id and status."""
        _, html = _request("GET", "/workspace")
        assert "aria-label" in html
        assert "Run " in html

    def test_loading_state_uses_role_status(self):
        """Loading state sets role=status on the entries container."""
        _, html = _request("GET", "/workspace")
        assert 'role", "status"' in html

    def test_status_color_class_used(self):
        """Status color classes exist for visual distinction."""
        _, html = _request("GET", "/workspace")
        assert "status-completed" in html
        assert "status-blocked" in html
        assert "status-failed" in html


class TestLiveZoneBoundaries:
    """PR 0144: Tests that other zones remain deferred."""

    def test_canvas_still_placeholder(self):
        """Canvas zone remains a PR 0145 placeholder."""
        _, html = _request("GET", "/workspace")
        assert "PR 0145" in html
        assert "Select a run from the timeline" in html

    def test_gates_still_deferred(self):
        """Gates & Proofs zone remains deferred."""
        _, html = _request("GET", "/workspace")
        assert "No gate checks available" in html

    def test_logs_still_deferred(self):
        """Logs & Captures zone remains deferred."""
        _, html = _request("GET", "/workspace")
        assert "No logs available" in html

    def test_no_mutation_controls(self):
        """No mutation, agent launch, or git/PR controls."""
        _, html = _request("GET", "/workspace")
        assert "retry" not in html.lower()
        assert "rerun" not in html.lower()
        assert "git commit" not in html.lower()
        assert "git push" not in html.lower()


class TestLiveHostileStrings:
    """PR 0144: Tests that hostile strings cannot break rendering."""

    def test_eschtml_still_present(self):
        """escHtml function is still present for safe HTML escaping."""
        _, html = _request("GET", "/workspace")
        assert "function escHtml" in html

    def test_safetext_function_present(self):
        """safeText function provides safe string rendering."""
        _, html = _request("GET", "/workspace")
        assert "function safeText" in html

    def test_no_eval_in_live_code(self):
        """No eval in the live run list code."""
        _, html = _request("GET", "/workspace")
        assert "eval(" not in html

    def test_no_document_write(self):
        """No document.write in live code."""
        _, html = _request("GET", "/workspace")
        assert "document.write" not in html

    def test_no_function_constructor(self):
        """No Function constructor."""
        _, html = _request("GET", "/workspace")
        assert "new Function" not in html

    def test_no_external_assets_in_live_code(self):
        """No external assets introduced."""
        _, html = _request("GET", "/workspace")
        assert 'src="http' not in html
        assert 'href="http' not in html
        assert "cdn." not in html.lower()


class TestLiveCompatibility:
    """PR 0144: Tests that existing routes remain compatible."""

    def test_get_runs_ev_contract_version_unchanged(self):
        """GET /runs ev_contract_version remains '1'."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_get_runs_detail_ev_contract_version_unchanged(self):
        """GET /runs/<run_id> ev_contract_version remains '1'."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "compat-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1", "run_id": "compat-run",
            "status": "completed", "reason_codes": ["completed"],
            "execution_attempted": True, "execution_results_summary": [],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs/compat-run?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_get_root_unchanged(self):
        """GET / remains unchanged."""
        status, html = _request("GET", "/")
        assert status == 200
        assert "Ariadne — Local Interaction" in html

    def test_get_workspace_still_returns_200(self):
        """GET /workspace still returns 200."""
        status, _ = _request("GET", "/workspace")
        assert status == 200

    def test_all_zones_still_present(self):
        """All four zones remain present."""
        _, html = _request("GET", "/workspace")
        assert 'id="zone-timeline"' in html
        assert 'id="zone-canvas"' in html
        assert 'id="zone-gates-proofs"' in html
        assert 'id="zone-logs-captures"' in html


class TestSafeRendering:
    """Tests for safe rendering behavior."""

    def test_eschtml_function_exists(self):
        """escHtml safe-rendering function exists in page JS."""
        _, html = _request("GET", "/workspace")
        assert "function escHtml" in html

    def test_textcontent_based_escaping(self):
        """escHtml uses textContent-based escaping."""
        _, html = _request("GET", "/workspace")
        assert "textContent" in html
        assert "createElement" in html

    def test_no_eval(self):
        """No eval() in workspace JS."""
        _, html = _request("GET", "/workspace")
        assert "eval(" not in html and "eval (" not in html

    def test_no_document_write(self):
        """No document.write in workspace JS."""
        _, html = _request("GET", "/workspace")
        assert "document.write" not in html

    def test_no_function_constructor(self):
        """No Function constructor in workspace JS."""
        _, html = _request("GET", "/workspace")
        assert "new Function" not in html


class TestNoMutationControls:
    """Tests that no mutation controls exist in the workspace."""

    def test_no_accept_reject_approve_buttons(self):
        """No accept/reject/approve buttons."""
        _, html = _request("GET", "/workspace")
        assert "accept" not in html.lower() or "No artifact loaded" in html

    def test_no_retry_rerun_buttons(self):
        """No retry/rerun buttons."""
        _, html = _request("GET", "/workspace")
        assert "retry" not in html.lower()
        assert "rerun" not in html.lower()

    def test_no_git_commit_push_controls(self):
        """No git commit/push controls."""
        _, html = _request("GET", "/workspace")
        assert "git commit" not in html.lower()
        assert "git push" not in html.lower()

    def test_no_gh_pr_controls(self):
        """No gh pr controls."""
        _, html = _request("GET", "/workspace")
        assert "gh pr" not in html.lower()

    def test_no_agent_launch_controls(self):
        """No agent launch controls."""
        _, html = _request("GET", "/workspace")
        assert "launch agent" not in html.lower()
        assert "run agent" not in html.lower()

    def test_no_arbitrary_file_path_input(self):
        """No file path or directory input fields."""
        _, html = _request("GET", "/workspace")
        assert '<input type="file"' not in html


class TestNoExternalAssets:
    """Tests that no external assets are loaded."""

    def test_no_external_scripts(self):
        """No external script src in workspace."""
        _, html = _request("GET", "/workspace")
        assert 'src="http' not in html and "src='http" not in html

    def test_no_external_stylesheets(self):
        """No external stylesheet links."""
        _, html = _request("GET", "/workspace")
        assert 'href="http' not in html and "href='http" not in html

    def test_no_cdn_references(self):
        """No CDN references."""
        _, html = _request("GET", "/workspace")
        assert "cdn." not in html.lower()
        assert "unpkg" not in html.lower()
        assert "jsdelivr" not in html.lower()

    def test_no_font_imports(self):
        """No external font imports."""
        _, html = _request("GET", "/workspace")
        assert "@import" not in html


class TestResponsiveStructure:
    """Tests for responsive layout structure."""

    def test_media_query_present(self):
        """CSS media query for responsive behavior exists."""
        _, html = _request("GET", "/workspace")
        assert "@media" in html

    def test_all_zones_still_present_in_html(self):
        """All four zones are structurally present regardless of layout."""
        _, html = _request("GET", "/workspace")
        assert 'id="zone-timeline"' in html
        assert 'id="zone-canvas"' in html
        assert 'id="zone-gates-proofs"' in html
        assert 'id="zone-logs-captures"' in html


class TestUnsupportedMethods:
    """Tests for unsupported HTTP methods on /workspace."""

    def test_post_workspace_returns_404(self):
        """POST /workspace returns 404."""
        status, _ = _request("POST", "/workspace")
        assert status == 404

    def test_put_workspace_returns_404(self):
        """PUT /workspace returns 404."""
        status, _ = _request("PUT", "/workspace")
        assert status == 404

    def test_patch_workspace_returns_404(self):
        """PATCH /workspace returns 404."""
        status, _ = _request("PATCH", "/workspace")
        assert status == 404

    def test_delete_workspace_returns_404(self):
        """DELETE /workspace returns 404."""
        status, _ = _request("DELETE", "/workspace")
        assert status == 404


class TestExistingPagePreserved:
    """Tests that existing GET /, GET /runs, and GET /runs/<run_id> are unchanged."""

    def test_get_root_still_accessible(self):
        """GET / still returns the Local Interaction page."""
        status, html = _request("GET", "/")
        assert status == 200
        assert "Ariadne — Local Interaction" in html

    def test_get_root_has_run_history_section(self):
        """GET / still has run-history-section."""
        _, html = _request("GET", "/")
        assert "run-history-section" in html

    def test_get_root_has_run_detail_panel(self):
        """GET / still has run-detail-panel."""
        _, html = _request("GET", "/")
        assert "run-detail-panel" in html

    def test_get_runs_still_works(self):
        """GET /runs still returns versioned JSON."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_get_runs_detail_still_works(self):
        """GET /runs/<run_id> still returns versioned JSON."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "test-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1", "run_id": "test-run",
            "status": "completed", "reason_codes": ["completed"],
            "execution_attempted": True, "execution_results_summary": [],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs/test-run?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_get_root_no_workspace_pollution(self):
        """GET / does not contain workspace identifiers."""
        _, html = _request("GET", "/")
        assert 'id="artifact-workspace"' not in html
        assert 'id="zone-timeline"' not in html


class TestWorkspacePurity:
    """Tests that the workspace module has no prohibited authority."""

    def test_no_filesystem_access(self):
        """Workspace module does not perform filesystem access."""
        import inspect
        from task_intake.artifact_workspace import render_artifact_workspace
        source = inspect.getsource(render_artifact_workspace)
        # The render function only returns a pre-built HTML string
        assert "open(" not in source
        assert "os.path" not in source
        assert "os.listdir" not in source

    def test_no_asgi_routing(self):
        """Workspace render function has no ASGI routing."""
        import inspect
        from task_intake.artifact_workspace import render_artifact_workspace
        source = inspect.getsource(render_artifact_workspace)
        assert "scope" not in source
        assert "receive" not in source
        assert "send" not in source

    def test_no_deterministic(self):
        """Workspace render is deterministic — same output every call."""
        from task_intake.artifact_workspace import render_artifact_workspace
        html1 = render_artifact_workspace()
        html2 = render_artifact_workspace()
        assert html1 == html2


class TestAccessibility:
    """Tests for accessibility landmarks and semantics."""

    def test_main_landmark_present(self):
        """Workspace root has role main."""
        _, html = _request("GET", "/workspace")
        assert 'role="main"' in html

    def test_zone_regions_present(self):
        """All zones have role region."""
        _, html = _request("GET", "/workspace")
        assert 'role="region"' in html

    def test_zones_aria_labelledby(self):
        """All zones use aria-labelledby referencing their headings."""
        _, html = _request("GET", "/workspace")
        assert 'aria-labelledby="zone-timeline-heading"' in html
        assert 'aria-labelledby="zone-canvas-heading"' in html
        assert 'aria-labelledby="zone-gates-proofs-heading"' in html
        assert 'aria-labelledby="zone-logs-captures-heading"' in html

    def test_timeline_entries_are_keyboard_accessible(self):
        """Timeline entries have keyboard handlers via addEventListener."""
        _, html = _request("GET", "/workspace")
        assert "addEventListener" in html
        assert "keydown" in html


class TestNoRepositoryWrites:
    """Tests that no repository-local state is written."""

    def test_no_ariadne_writes(self):
        """Workspace does not write to .ariadne."""
        import inspect
        from task_intake.artifact_workspace import render_artifact_workspace
        source = inspect.getsource(render_artifact_workspace)
        assert ".ariadne" not in source
        assert "os.makedirs" not in source

    def test_no_subprocess_shell_outs(self):
        """Workspace module has no subprocess, os.system, or shell outs."""
        import os as _os
        serializer_path = _os.path.join(
            _os.path.dirname(__file__),
            "..", "src", "task_intake", "artifact_workspace.py",
        )
        with open(serializer_path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "subprocess" not in source
        assert "os.system" not in source
        assert "Popen" not in source

    def test_no_docker_references(self):
        """Workspace module has no Docker references."""
        import os as _os
        serializer_path = _os.path.join(
            _os.path.dirname(__file__),
            "..", "src", "task_intake", "artifact_workspace.py",
        )
        with open(serializer_path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "docker" not in source.lower()

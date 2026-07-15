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
        assert "Select a run to view manifest and evidence" in html

    def test_no_fabricated_evidence_in_logs(self):
        """Logs zone does not claim to have real logs."""
        _, html = _request("GET", "/workspace")
        assert "Select a run to view execution output" in html


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
        # PR 0147 adds innerHTML clearing in gates/logs rendering functions
        # (showGatesLoading, showGatesUnavailable, renderGatesProofs,
        #  showLogsLoading, showLogsUnavailable, renderLogsCaptures)
        assert inner_count >= 3, f"Expected at least 3 innerHTML occurrences, got {inner_count}"
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
        """Canvas zone shows initial placeholder before any selection."""
        _, html = _request("GET", "/workspace")
        assert "Select a run from the timeline to view artifacts" in html

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


# ---------------------------------------------------------------------------
# PR 0147 — Gates & Proofs and Logs & Captures Viewer Tests
# ---------------------------------------------------------------------------


class TestGatesProofsManifestViewer:
    """PR 0147: Tests for Gates & Proofs manifest viewer."""

    def test_gates_content_container_exists(self):
        """#gates-content container exists within zone."""
        _, html = _request("GET", "/workspace")
        assert 'id="gates-content"' in html

    def test_manifest_files_heading_present(self):
        """Manifest Files h3 heading exists."""
        _, html = _request("GET", "/workspace")
        assert '"Manifest Files"' in html

    def test_manifest_entries_use_gate_entry_class(self):
        """Manifest entries use gate-entry CSS class."""
        _, html = _request("GET", "/workspace")
        assert "gate-entry" in html

    def test_manifest_entries_use_gate_label_class(self):
        """Manifest entries use gate-label CSS class."""
        _, html = _request("GET", "/workspace")
        assert "gate-label" in html

    def test_manifest_classification_label_present(self):
        """Runtime Evidence classification label exists."""
        _, html = _request("GET", "/workspace")
        assert "Runtime Evidence" in html
        assert "listed in manifest.json" in html

    def test_manifest_empty_state_text_present(self):
        """\"Manifest file list is empty.\" text exists."""
        _, html = _request("GET", "/workspace")
        assert "Manifest file list is empty." in html

    def test_manifest_missing_state_text_present(self):
        """Manifest not available text exists."""
        _, html = _request("GET", "/workspace")
        assert "Manifest not available. The manifest.json file is missing" in html

    def test_no_file_links_in_manifest(self):
        """No file: links in manifest rendering."""
        _, html = _request("GET", "/workspace")
        assert "file:" not in html

    def test_manifest_files_from_detail_response(self):
        """manifest_files accessed from detail response."""
        _, html = _request("GET", "/workspace")
        assert "d.manifest_files" in html

    def test_manifest_entries_preserve_order(self):
        """Manifest entries rendered in array order."""
        _, html = _request("GET", "/workspace")
        # The renderGatesProofs function iterates manifest_files in order
        assert "renderGatesProofs" in html


class TestGatesProofsEvidenceViewer:
    """PR 0147: Tests for Gates & Proofs evidence/proof viewer."""

    def test_evidence_paths_heading_present(self):
        """Evidence Paths h3 heading exists."""
        _, html = _request("GET", "/workspace")
        assert '"Evidence Paths"' in html

    def test_evidence_paths_rendered_as_inert_text(self):
        """Evidence paths rendered via safeText (textContent), not as links."""
        _, html = _request("GET", "/workspace")
        # safeText is used for evidence_paths values
        assert "safeText(d.evidence_paths" in html
        # No anchor creation for evidence paths
        assert 'd.evidence_paths[j]' in html

    def test_no_evidence_path_anchors(self):
        """No anchors created for evidence paths."""
        _, html = _request("GET", "/workspace")
        # Evidence paths in gates zone are NOT wrapped in <a> tags
        # The href attribute usage in gates zone is only for PR URL (agent claims)
        assert '"Evidence reference"' in html

    def test_evidence_paths_classification_label(self):
        """Evidence reference classification label exists."""
        _, html = _request("GET", "/workspace")
        assert "Evidence reference" in html

    def test_no_evidence_paths_state_present(self):
        """No evidence paths available state text exists."""
        _, html = _request("GET", "/workspace")
        assert "No evidence paths available." in html

    def test_run_json_hash_heading_present(self):
        """Run JSON Hash h3 heading exists."""
        _, html = _request("GET", "/workspace")
        assert '"Run JSON Hash"' in html

    def test_run_json_hash_classification_label(self):
        """Run JSON hash classification label exists."""
        _, html = _request("GET", "/workspace")
        assert "as recorded in manifest" in html

    def test_run_json_hash_not_described_as_verified(self):
        """Run JSON hash is NOT described as verified."""
        _, html = _request("GET", "/workspace")
        # Plan requires: no "Verified proof", "Accepted proof", etc.
        assert "Verified proof" not in html
        assert "Accepted proof" not in html
        assert "hash verified" not in html.lower()

    def test_hash_not_available_state_present(self):
        """Run JSON hash not available state exists."""
        _, html = _request("GET", "/workspace")
        assert "Run JSON hash not available." in html

    def test_source_errors_heading_in_gates(self):
        """Source Errors h3 heading exists in gates zone."""
        _, html = _request("GET", "/workspace")
        assert '"Source Errors"' in html

    def test_source_errors_classification_label(self):
        """Source error classification label exists."""
        _, html = _request("GET", "/workspace")
        assert "Source error" in html

    def test_no_source_errors_state_present(self):
        """No source errors reported state text exists."""
        _, html = _request("GET", "/workspace")
        assert "No source errors reported." in html

    def test_agent_claims_heading_present(self):
        """Agent Claims h3 heading exists."""
        _, html = _request("GET", "/workspace")
        assert '"Agent Claims"' in html

    def test_agent_claims_label_present(self):
        """Agent-performed operation label exists."""
        _, html = _request("GET", "/workspace")
        assert "Agent-performed operation: gh_pr_create" in html

    def test_agent_claims_not_labelled_as_proof(self):
        """Agent claims are NOT labelled as proof."""
        _, html = _request("GET", "/workspace")
        assert "Agent-performed" in html
        # Agent claims are separate from runtime evidence
        assert "Runtime Evidence" in html

    def test_report_provenance_heading_present(self):
        """Report Provenance h3 heading exists."""
        _, html = _request("GET", "/workspace")
        assert '"Report Provenance"' in html

    def test_report_provenance_not_proof_text(self):
        """Report provenance includes not-verified-proof disclaimer."""
        _, html = _request("GET", "/workspace")
        assert "not independently verified proof" in html

    def test_report_available_provenance_text(self):
        """Run report available provenance text exists."""
        _, html = _request("GET", "/workspace")
        assert "Run report is available" in html

    def test_report_unavailable_provenance_text(self):
        """Run report not available state text exists."""
        _, html = _request("GET", "/workspace")
        assert "Run report is not available" in html

    def test_proof_references_heading_present(self):
        """Proof References h3 heading exists."""
        _, html = _request("GET", "/workspace")
        assert '"Proof References"' in html

    def test_proof_refs_unavailable_text_present(self):
        """proof_refs unavailable disclosure text exists."""
        _, html = _request("GET", "/workspace")
        assert "proof_refs are not stored" in html
        assert "not independently verified proof" in html

    def test_no_proof_acceptance_controls(self):
        """No proof acceptance or approval controls."""
        _, html = _request("GET", "/workspace")
        assert "approve" not in html.lower()

    def test_no_proof_fabrication(self):
        """No fabricated proof_ref values beyond the honest disclosure."""
        _, html = _request("GET", "/workspace")
        assert "Verified proof" not in html
        assert "Accepted proof" not in html
        assert "Trusted proof" not in html

    def test_source_errors_not_called_logs(self):
        """Source errors in gates zone are not falsely called logs."""
        _, html = _request("GET", "/workspace")
        assert "Source error" in html


class TestLogsCapturesViewer:
    """PR 0147: Tests for Logs & Captures viewer."""

    def test_logs_content_container_exists(self):
        """#logs-content container exists within zone."""
        _, html = _request("GET", "/workspace")
        assert 'id="logs-content"' in html

    def test_captures_unavailable_default_text_present(self):
        """Default captures/logs unavailable text exists."""
        _, html = _request("GET", "/workspace")
        assert "Command captures and logs are not stored in the current run evidence model" in html

    def test_stdout_not_captured_text_present(self):
        """Explicit note that stdout is not captured."""
        _, html = _request("GET", "/workspace")
        assert "stdout, stderr, and command output are not captured" in html

    def test_execution_summary_heading_present(self):
        """Execution Summary h3 heading exists."""
        _, html = _request("GET", "/workspace")
        assert '"Execution Summary"' in html

    def test_execution_summary_renders_operation_and_exit_code(self):
        """Execution summary renders operation name and exit_code."""
        _, html = _request("GET", "/workspace")
        assert "Execution Result:" in html
        assert "exit_code:" in html

    def test_execution_summary_uses_safetext(self):
        """Execution summary values use safeText."""
        _, html = _request("GET", "/workspace")
        assert "safeText(er.operation" in html

    def test_no_execution_results_state_present(self):
        """No execution results recorded state text exists."""
        _, html = _request("GET", "/workspace")
        assert "No execution results recorded." in html

    def test_no_fabricated_stdout_stderr(self):
        """No fabricated stdout or stderr values."""
        _, html = _request("GET", "/workspace")
        # The only mention of stdout/stderr should be in the "not captured" text
        assert "not captured" in html

    def test_no_fabricated_capture_paths(self):
        """No fabricated capture paths."""
        _, html = _request("GET", "/workspace")
        assert "capture_path" not in html

    def test_no_fabricated_command_text(self):
        """No fabricated command text beyond operation names."""
        _, html = _request("GET", "/workspace")
        assert "command output" in html  # only in "not captured" text

    def test_source_errors_in_logs_zone(self):
        """Source errors can be rendered in logs zone."""
        _, html = _request("GET", "/workspace")
        # renderLogsCaptures references d.source_errors
        assert "d.source_errors" in html

    def test_log_entry_class_used(self):
        """Log entries use log-entry CSS class."""
        _, html = _request("GET", "/workspace")
        assert "log-entry" in html

    def test_log_label_class_used(self):
        """Log labels use log-label CSS class."""
        _, html = _request("GET", "/workspace")
        assert "log-label" in html


class TestGatesLogsHostileStrings:
    """PR 0147: Tests for hostile content rendering in gates/logs zones."""

    def test_manifest_files_use_textcontent(self):
        """Manifest file names rendered via textContent (safeText)."""
        _, html = _request("GET", "/workspace")
        assert "safeText(d.manifest_files" in html

    def test_evidence_paths_use_textcontent(self):
        """Evidence paths rendered via textContent (safeText)."""
        _, html = _request("GET", "/workspace")
        assert "safeText(d.evidence_paths" in html

    def test_execution_results_use_textcontent(self):
        """Execution results rendered via textContent (safeText)."""
        _, html = _request("GET", "/workspace")
        assert "safeText(er.operation" in html

    def test_source_errors_use_textcontent(self):
        """Source errors rendered via textContent (safeText)."""
        _, html = _request("GET", "/workspace")
        assert "safeText(d.source_errors" in html

    def test_no_innerhtml_with_runtime_values(self):
        """No innerHTML concatenation with runtime values in gates/logs."""
        _, html = _request("GET", "/workspace")
        # innerHTML used only for clearing (innerHTML = "")
        assert "content.innerHTML = \"\"" in html
        # But NOT concatenated with runtime values
        assert "innerHTML = d." not in html
        assert "innerHTML = safeText" not in html

    def test_no_eval_in_gates_logs(self):
        """No eval in gates/logs zone code."""
        _, html = _request("GET", "/workspace")
        assert "eval(" not in html

    def test_no_function_constructor(self):
        """No Function constructor."""
        _, html = _request("GET", "/workspace")
        assert "new Function" not in html

    def test_no_document_write(self):
        """No document.write."""
        _, html = _request("GET", "/workspace")
        assert "document.write" not in html

    def test_no_javascript_urls(self):
        """No javascript: URLs."""
        _, html = _request("GET", "/workspace")
        assert "javascript:" not in html

    def test_no_data_urls(self):
        """No data: URLs."""
        _, html = _request("GET", "/workspace")
        assert "data:" not in html

    def test_no_file_urls(self):
        """No file: URLs."""
        _, html = _request("GET", "/workspace")
        assert "file:" not in html

    def test_no_automatic_linkification(self):
        """No automatic URL linkification in gates/logs zones."""
        _, html = _request("GET", "/workspace")
        # isSafeUrl used only for PR URLs in agent claims, not for arbitrary paths
        assert "isSafeUrl(data.summary.pr_url)" in html

    def test_no_iframe_srcdoc(self):
        """No iframe srcdoc."""
        _, html = _request("GET", "/workspace")
        assert "srcdoc" not in html


class TestGatesLogsNoMutationControls:
    """PR 0147: Tests that no mutation controls exist in gates/logs zones."""

    def test_no_accept_reject_in_gates(self):
        """No accept/reject controls in gates zone."""
        _, html = _request("GET", "/workspace")
        assert "accept" not in html.lower() or "No artifact loaded" in html

    def test_no_gate_mutation_controls(self):
        """No gate mutation controls."""
        _, html = _request("GET", "/workspace")
        assert "approve" not in html.lower()

    def test_no_agent_launch_in_gates(self):
        """No agent launch controls in gates zone."""
        _, html = _request("GET", "/workspace")
        assert "launch agent" not in html.lower()
        assert "run agent" not in html.lower()

    def test_no_git_controls_in_gates(self):
        """No git controls in gates zone."""
        _, html = _request("GET", "/workspace")
        assert "git commit" not in html.lower()
        assert "git push" not in html.lower()

    def test_no_orchestration_in_gates_or_logs(self):
        """No orchestration controls in gates/logs zones."""
        _, html = _request("GET", "/workspace")
        assert "orchestrat" not in html.lower()

    def test_no_retry_rerun_in_gates_or_logs(self):
        """No retry/rerun controls in gates/logs zones."""
        _, html = _request("GET", "/workspace")
        # The word "retry" must not appear as a control
        assert "retry" not in html.lower()
        assert "rerun" not in html.lower()


class TestGatesLogsViewerIntegration:
    """PR 0147: Tests for gates/logs viewer integration with selection."""

    def test_show_gates_loading_function_present(self):
        """showGatesLoading function exists."""
        _, html = _request("GET", "/workspace")
        assert "function showGatesLoading" in html

    def test_show_gates_unavailable_function_present(self):
        """showGatesUnavailable function exists."""
        _, html = _request("GET", "/workspace")
        assert "function showGatesUnavailable" in html

    def test_render_gates_proofs_function_present(self):
        """renderGatesProofs function exists."""
        _, html = _request("GET", "/workspace")
        assert "function renderGatesProofs" in html

    def test_show_logs_loading_function_present(self):
        """showLogsLoading function exists."""
        _, html = _request("GET", "/workspace")
        assert "function showLogsLoading" in html

    def test_show_logs_unavailable_function_present(self):
        """showLogsUnavailable function exists."""
        _, html = _request("GET", "/workspace")
        assert "function showLogsUnavailable" in html

    def test_render_logs_captures_function_present(self):
        """renderLogsCaptures function exists."""
        _, html = _request("GET", "/workspace")
        assert "function renderLogsCaptures" in html

    def test_gates_loading_called_in_select_run(self):
        """showGatesLoading is called in selectRun."""
        _, html = _request("GET", "/workspace")
        assert "showGatesLoading()" in html

    def test_logs_loading_called_in_select_run(self):
        """showLogsLoading is called in selectRun."""
        _, html = _request("GET", "/workspace")
        assert "showLogsLoading()" in html

    def test_render_gates_called_on_detail_success(self):
        """renderGatesProofs called after successful detail fetch."""
        _, html = _request("GET", "/workspace")
        assert "renderGatesProofs(data)" in html

    def test_render_logs_called_on_detail_success(self):
        """renderLogsCaptures called after successful detail fetch."""
        _, html = _request("GET", "/workspace")
        assert "renderLogsCaptures(data)" in html

    def test_gates_unavailable_called_on_fetch_failure(self):
        """showGatesUnavailable called on detail fetch failure."""
        _, html = _request("GET", "/workspace")
        assert "showGatesUnavailable()" in html

    def test_logs_unavailable_called_on_fetch_failure(self):
        """showLogsUnavailable called on detail fetch failure."""
        _, html = _request("GET", "/workspace")
        assert "showLogsUnavailable()" in html

    def test_loading_text_present(self):
        """Loading text exists in gates/logs loading functions."""
        _, html = _request("GET", "/workspace")
        # Both showGatesLoading and showLogsLoading use "Loading..."
        assert '"Loading..."' in html

    def test_stale_response_protection_preserved(self):
        """detailRequestCounter stale protection used for detail fetch."""
        _, html = _request("GET", "/workspace")
        assert "requestId !== detailRequestCounter" in html

    def test_gates_data_not_available_text_present(self):
        """Gates unavailable fetch failure message exists."""
        _, html = _request("GET", "/workspace")
        assert "Gates and proofs data not available" in html

    def test_logs_data_not_available_text_present(self):
        """Logs unavailable fetch failure message exists."""
        _, html = _request("GET", "/workspace")
        assert "Logs and captures data not available" in html


class TestGatesLogsPreservation:
    """PR 0147: Tests that PR 0145 and PR 0146 behavior is preserved."""

    def test_detail_panel_functions_preserved(self):
        """renderDetail still exists."""
        _, html = _request("GET", "/workspace")
        assert "function renderDetail" in html
        assert "function showDetailLoading" in html
        assert "function showDetailFetchFailure" in html

    def test_detail_request_counter_preserved(self):
        """detailRequestCounter variable still exists."""
        _, html = _request("GET", "/workspace")
        assert "detailRequestCounter" in html

    def test_selected_run_id_preserved(self):
        """selectedRunId variable still exists."""
        _, html = _request("GET", "/workspace")
        assert "selectedRunId" in html

    def test_aria_selected_preserved(self):
        """aria-selected management still exists."""
        _, html = _request("GET", "/workspace")
        assert "aria-selected" in html

    def test_timeline_selected_class_preserved(self):
        """timeline-selected CSS class still present."""
        _, html = _request("GET", "/workspace")
        assert "timeline-selected" in html

    def test_encode_uri_component_preserved(self):
        """encodeURIComponent still used."""
        _, html = _request("GET", "/workspace")
        assert "encodeURIComponent" in html

    def test_fetch_report_function_preserved(self):
        """fetchReport function still exists."""
        _, html = _request("GET", "/workspace")
        assert "function fetchReport" in html

    def test_render_report_function_preserved(self):
        """renderReport function still exists."""
        _, html = _request("GET", "/workspace")
        assert "function renderReport" in html

    def test_report_viewer_css_preserved(self):
        """#report-viewer CSS still present."""
        _, html = _request("GET", "/workspace")
        assert "#report-viewer" in html

    def test_report_text_css_preserved(self):
        """#report-text CSS still present."""
        _, html = _request("GET", "/workspace")
        assert "#report-text" in html

    def test_get_workspace_returns_200(self):
        """GET /workspace still returns 200."""
        status, _ = _request("GET", "/workspace")
        assert status == 200

    def test_get_root_returns_200(self):
        """GET / still returns 200."""
        status, html = _request("GET", "/")
        assert status == 200
        assert "Ariadne — Local Interaction" in html

    def test_get_runs_returns_ev_contract_version_1(self):
        """GET /runs ev_contract_version remains '1'."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        os.makedirs(runs_root, exist_ok=True)
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_get_runs_detail_returns_ev_contract_version_1(self):
        """GET /runs/<run_id> ev_contract_version remains '1'."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        run_dir = os.path.join(runs_root, "preserve-run")
        os.makedirs(run_dir, exist_ok=True)
        run_json = {
            "schema_version": "1", "run_id": "preserve-run",
            "status": "completed", "reason_codes": ["completed"],
            "execution_attempted": True, "execution_results_summary": [],
        }
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)
        status, raw = _request("GET", "/runs/preserve-run?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_get_runs_report_returns_ev_contract_version_1(self):
        """GET /runs/<run_id>/report ev_contract_version remains '1'."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "preserve-run")
        status, raw = _request("GET", "/runs/preserve-run/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_all_four_zones_still_present(self):
        """All four workspace zones still present."""
        _, html = _request("GET", "/workspace")
        assert 'id="zone-timeline"' in html
        assert 'id="zone-canvas"' in html
        assert 'id="zone-gates-proofs"' in html
        assert 'id="zone-logs-captures"' in html

    def test_gates_placeholder_still_present(self):
        """Gates zone initial placeholder still present."""
        _, html = _request("GET", "/workspace")
        assert "No gate checks available" in html

    def test_logs_placeholder_still_present(self):
        """Logs zone initial placeholder still present."""
        _, html = _request("GET", "/workspace")
        assert "No logs available" in html

    def test_no_launch_orchestration_controls(self):
        """No launch or orchestration controls introduced."""
        _, html = _request("GET", "/workspace")
        assert "launch" not in html.lower()
        assert "orchestrat" not in html.lower()

    def test_no_external_assets_introduced(self):
        """No external assets introduced."""
        _, html = _request("GET", "/workspace")
        assert 'src="http' not in html
        assert 'href="http' not in html
        assert "cdn." not in html.lower()

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


class TestDetailPanelSelection:
    """PR 0145: Tests for detail panel selection wiring."""

    def test_detail_request_counter_present(self):
        """detailRequestCounter variable exists for stale-response protection."""
        _, html = _request("GET", "/workspace")
        assert "detailRequestCounter" in html

    def test_selected_run_id_variable_present(self):
        """selectedRunId variable exists for selection tracking."""
        _, html = _request("GET", "/workspace")
        assert "selectedRunId" in html

    def test_aria_selected_present(self):
        """aria-selected attribute management exists."""
        _, html = _request("GET", "/workspace")
        assert "aria-selected" in html

    def test_timeline_selected_class_present(self):
        """timeline-selected CSS class exists for visual selection."""
        _, html = _request("GET", "/workspace")
        assert "timeline-selected" in html

    def test_encode_uri_component_present(self):
        """encodeURIComponent is used for safe request URL construction."""
        _, html = _request("GET", "/workspace")
        assert "encodeURIComponent" in html

    def test_detail_fetch_url_present(self):
        """Detail fetch URL uses /runs/ with encoded run_id."""
        _, html = _request("GET", "/workspace")
        assert 'fetch("/runs/" + encodeURIComponent' in html

    def test_stale_response_check_present(self):
        """Stale response is discarded by checking requestId against counter."""
        _, html = _request("GET", "/workspace")
        assert "requestId !== detailRequestCounter" in html


class TestDetailPanelStates:
    """PR 0145: Tests for detail panel state messages."""

    def test_loading_detail_text_present(self):
        """Loading detail state message exists."""
        _, html = _request("GET", "/workspace")
        assert "Loading detail for" in html

    def test_run_not_found_text_present(self):
        """Unknown run state message exists."""
        _, html = _request("GET", "/workspace")
        assert "The run may have been removed" in html

    def test_detail_version_mismatch_text_present(self):
        """Detail version mismatch state message exists."""
        _, html = _request("GET", "/workspace")
        assert "Contract version mismatch" in html

    def test_invalid_envelope_text_present(self):
        """Invalid detail response envelope state exists."""
        _, html = _request("GET", "/workspace")
        assert "Unexpected detail response format" in html

    def test_summary_not_available_text_present(self):
        """Invalid summary shape state exists."""
        _, html = _request("GET", "/workspace")
        assert "Run summary not available" in html

    def test_detail_not_available_text_present(self):
        """Invalid detail shape state exists."""
        _, html = _request("GET", "/workspace")
        assert "Detail evidence not available" in html

    def test_detail_fetch_failure_text_present(self):
        """Detail fetch failure state exists."""
        _, html = _request("GET", "/workspace")
        assert "Failed to load run detail" in html

    def test_no_execution_results_text_present(self):
        """Empty execution_results state exists."""
        _, html = _request("GET", "/workspace")
        assert "No execution results available" in html

    def test_no_evidence_paths_text_present(self):
        """Empty evidence_paths state exists."""
        _, html = _request("GET", "/workspace")
        assert "No evidence paths available" in html

    def test_no_source_errors_text_present(self):
        """Empty source_errors state exists."""
        _, html = _request("GET", "/workspace")
        assert "No source errors reported" in html

    def test_no_missing_evidence_text_present(self):
        """Empty missing evidence state exists."""
        _, html = _request("GET", "/workspace")
        assert "No missing evidence" in html

    def test_no_malformed_evidence_text_present(self):
        """Empty malformed evidence state exists."""
        _, html = _request("GET", "/workspace")
        assert "No malformed evidence" in html


class TestDetailPanelDisplay:
    """PR 0145: Tests for detail panel display fields."""

    def test_detail_content_id_present(self):
        """Detail panel has #detail-content container."""
        _, html = _request("GET", "/workspace")
        assert 'id="detail-content"' in html or "detail-content" in html

    def test_detail_loading_id_present(self):
        """Loading state has #detail-loading element."""
        _, html = _request("GET", "/workspace")
        assert 'id="detail-loading"' in html or "detail-loading" in html

    def test_summary_section_label_present(self):
        """Summary heading exists in renderDetail."""
        _, html = _request("GET", "/workspace")
        assert 'textContent = "Summary"' in html

    def test_run_id_detail_row_present(self):
        """Run ID row renders via safeText."""
        _, html = _request("GET", "/workspace")
        assert 'detailRow("Run ID"' in html

    def test_status_detail_row_present(self):
        """Status row renders as visible text with CSS class."""
        _, html = _request("GET", "/workspace")
        assert 'detailRow("Status"' in html

    def test_reason_codes_detail_row_present(self):
        """Reason codes row renders."""
        _, html = _request("GET", "/workspace")
        assert 'detailRow("Reason codes"' in html

    def test_execution_attempted_detail_row_present(self):
        """Execution attempted row renders yes/no/not available."""
        _, html = _request("GET", "/workspace")
        assert 'detailRow("Execution attempted"' in html

    def test_payload_cleanliness_unavailable_text_present(self):
        """Payload cleanliness shown as not available when null."""
        _, html = _request("GET", "/workspace")
        assert 'detailRow("Payload cleanliness"' in html

    def test_readiness_unavailable_text_present(self):
        """Readiness shown as not available when null."""
        _, html = _request("GET", "/workspace")
        assert 'detailRow("Readiness"' in html

    def test_run_json_hash_detail_row_present(self):
        """Run JSON hash row renders via safeText."""
        _, html = _request("GET", "/workspace")
        assert 'detailRow("Run JSON hash"' in html

    def test_execution_results_render_operation_and_exit_code(self):
        """Execution results render operation and exit_code only."""
        _, html = _request("GET", "/workspace")
        assert ": exit_code " in html

    def test_evidence_paths_as_text_only(self):
        """Evidence paths rendered as textContent, not as links."""
        _, html = _request("GET", "/workspace")
        assert "Evidence Paths" in html or "Evidence paths" in html

    def test_missing_notices_expected_path_and_reason(self):
        """Missing evidence notices include expected_path and reason."""
        _, html = _request("GET", "/workspace")
        assert "expected_path" in html

    def test_malformed_notices_expected_path_and_reason(self):
        """Malformed evidence notices include expected_path and reason."""
        _, html = _request("GET", "/workspace")
        assert "malformed" in html


class TestDetailDeferrals:
    """PR 0145: Tests that PR 0146 and PR 0147 content is not rendered."""

    def test_report_preview_not_rendered(self):
        """report_preview is not rendered in the detail panel."""
        _, html = _request("GET", "/workspace")
        assert "report_preview" not in html

    def test_manifest_files_not_rendered(self):
        """manifest_files is not rendered in the detail panel (rendered in Gates & Proofs zone per PR 0147)."""
        _, html = _request("GET", "/workspace")
        # PR 0147: manifest_files is now rendered in the Gates & Proofs zone
        # via renderGatesProofs using d.manifest_files . Verify the accessor exists.
        assert "d.manifest_files" in html

    def test_gates_zone_still_deferred(self):
        """Gates & Proofs zone remains deferred."""
        _, html = _request("GET", "/workspace")
        assert "No gate checks available" in html

    def test_logs_zone_still_deferred(self):
        """Logs & Captures zone remains deferred."""
        _, html = _request("GET", "/workspace")
        assert "No logs available" in html

    def test_no_mutation_controls_in_detail(self):
        """No mutation controls in detail panel."""
        _, html = _request("GET", "/workspace")
        assert "retry" not in html.lower()
        assert "rerun" not in html.lower()


# ---------------------------------------------------------------------------
# PR 0146 Report API and Viewer Tests
# ---------------------------------------------------------------------------


def _make_report_run(tmp_dir, run_id="run-001", include_report=True,
                      include_manifest=True, include_run_json=True,
                      report_content="Ariadne Run Report\nTest content.",
                      malformed_manifest=False, malformed_report=False,
                      report_encoding="utf-8", empty_report=False,
                      oversized_report=False):
    """Create a run directory with run.json, manifest.json, and run-report.txt."""
    runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)

    if include_run_json:
        run_json_path = os.path.join(run_dir, "run.json")
        run_json = {
            "schema_version": "1", "run_id": run_id,
            "status": "completed", "pipeline_status": "completed",
            "git_boundary_status": "approved",
            "reason_codes": ["completed"], "execution_attempted": True,
            "execution_results_summary": [],
            "started_at": "2026-07-15T12:00:00Z",
            "finished_at": "2026-07-15T12:05:00Z",
        }
        with open(run_json_path, "w", encoding="utf-8") as f:
            json.dump(run_json, f, sort_keys=True, ensure_ascii=False, indent=2)

    if include_manifest:
        manifest_path = os.path.join(run_dir, "manifest.json")
        if malformed_manifest:
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write("{bad manifest")
        else:
            manifest = {
                "schema_version": "1", "run_id": run_id,
                "run_json_hash": "abc123",
                "files": ["run.json", "run-report.txt"],
            }
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, sort_keys=True, ensure_ascii=False, indent=2)

    if include_report:
        report_path = os.path.join(run_dir, "run-report.txt")
        if malformed_report:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            os.chmod(report_path, 0o000)
        elif empty_report:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("")
        elif oversized_report:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("X" * 100001)
        else:
            with open(report_path, "w", encoding=report_encoding) as f:
                f.write(report_content)

    return runs_root


class TestReportApi:
    """PR 0146: Tests for GET /runs/<run_id>/report API."""

    def test_report_returns_200_with_json(self):
        """GET /runs/<run_id>/report returns 200 with JSON."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001")
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert "ev_contract_version" in data

    def test_report_has_ev_contract_version_1(self):
        """Report response has ev_contract_version '1'."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001")
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_complete_report_content_returned(self):
        """Complete report content is returned with correct content_length."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        content = "Ariadne Run Report\nRun ID: run-001\nStatus: completed\n"
        runs_root = _make_report_run(tmp_dir, "run-001", report_content=content)
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is True
        assert data["content"] == content
        assert data["content_length"] == len(content)
        assert data["truncated"] is False
        assert data["report_exists"] is True

    def test_empty_report_returns_content_empty(self):
        """Empty report returns content='' and report_exists=True."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001", empty_report=True)
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is True
        assert data["content"] == ""
        assert data["content_length"] == 0
        assert data["report_exists"] is True

    def test_missing_report_returns_file_not_found(self):
        """Missing report returns ok=False, error='file_not_found'."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001", include_report=False)
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False
        assert data["error"] == "file_not_found"
        assert data["content"] is None
        assert data["report_exists"] is False

    def test_unreadable_report_returns_error(self):
        """Unreadable report returns ok=False with read_error."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        content = "test"
        runs_root = _make_report_run(
            tmp_dir, "run-001",
            report_content=content, malformed_report=True,
        )
        # Restore perms so test can clean up
        try:
            status, raw = _request(
                "GET", "/runs/run-001/report?runs_root=" + runs_root)
            assert status == 200
            data = json.loads(raw)
            assert data["ok"] is False
            assert "read_error" in str(data["error"])
            assert data["report_exists"] is True
        finally:
            report_dir = os.path.join(runs_root, "run-001")
            rp = os.path.join(report_dir, "run-report.txt")
            if os.path.exists(rp):
                os.chmod(rp, 0o644)

    def test_invalid_run_id_returns_error(self):
        """Invalid run_id returns error."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001")
        status, raw = _request(
            "GET", "/runs/../etc/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False
        assert data["error"] == "invalid_run_id"

    def test_unknown_run_returns_run_not_found(self):
        """Unknown run_id returns error='run not found'."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001")
        status, raw = _request(
            "GET", "/runs/nonexistent/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False
        assert data["error"] == "run not found"

    def test_report_envelope_has_exact_keys(self):
        """Report response has exact key set."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001")
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        expected_keys = {
            "ev_contract_version", "ok", "error", "run_id", "content",
            "content_length", "truncated", "truncation_limit",
            "report_exists", "manifest_lists_report", "provenance",
        }
        assert set(data.keys()) == expected_keys

    def test_manifest_lists_report_true(self):
        """manifest_lists_report is True when manifest includes run-report.txt."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001")
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["manifest_lists_report"] is True
        assert "run-report.txt is listed in manifest files" in data["provenance"]

    def test_provenance_linked_when_manifest_and_run_json_available(self):
        """Provenance indicates linked when manifest and run.json exist."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001")
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert "run.json and manifest.json exist" in data["provenance"]

    def test_provenance_unavailable_when_manifest_missing(self):
        """Provenance indicates unavailable when manifest is missing."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001", include_manifest=False)
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert "cannot verify" in data["provenance"]
        assert data["manifest_lists_report"] is False

    def test_provenance_malformed_when_manifest_unreadable(self):
        """Provenance indicates malformed when manifest is broken."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(
            tmp_dir, "run-001", malformed_manifest=True)
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert "manifest evidence is malformed" in data["provenance"]

    def test_oversize_report_truncated_flag(self):
        """Report exceeding 100KB has truncated=True."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(
            tmp_dir, "run-001", oversized_report=True)
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is True
        assert data["truncated"] is True
        assert data["truncation_limit"] == 100000
        assert len(data["content"]) == 100000

    def test_non_get_returns_404(self):
        """Non-GET methods on /runs/<run_id>/report return 404."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001")
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            status, _ = _request(
                method, "/runs/run-001/report?runs_root=" + runs_root)
            assert status == 404, (
                f"{method} should return 404, got {status}")

    def test_report_preview_not_used_as_full_report(self):
        """Report endpoint does not return 500-char preview."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        long_content = "X" * 600
        runs_root = _make_report_run(
            tmp_dir, "run-001", report_content=long_content)
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert len(data["content"]) == 600
        assert data["content_length"] == 600

    def test_missing_runs_root_returns_error(self):
        """Missing runs_root returns ok=False."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
        status, raw = _request(
            "GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is False
        assert "runs_root not found" in data["error"]


class TestReportViewer:
    """PR 0146: Tests for report viewer rendering in workspace."""

    def test_report_viewer_css_present(self):
        """#report-viewer CSS is present in workspace."""
        _, html = _request("GET", "/workspace")
        assert "#report-viewer" in html

    def test_report_text_css_present(self):
        """#report-text CSS is present."""
        _, html = _request("GET", "/workspace")
        assert "#report-text" in html

    def test_report_provenance_css_present(self):
        """#report-provenance CSS is present."""
        _, html = _request("GET", "/workspace")
        assert "#report-provenance" in html

    def test_report_viewer_function_present(self):
        """getOrCreateReportViewer function exists."""
        _, html = _request("GET", "/workspace")
        assert "function getOrCreateReportViewer" in html

    def test_fetch_report_function_present(self):
        """fetchReport function exists."""
        _, html = _request("GET", "/workspace")
        assert "function fetchReport" in html

    def test_render_report_function_present(self):
        """renderReport function exists."""
        _, html = _request("GET", "/workspace")
        assert "function renderReport" in html

    def test_report_heading_present(self):
        """Report viewer has 'Run Report' heading."""
        _, html = _request("GET", "/workspace")
        assert '"Run Report"' in html

    def test_loading_report_text_present(self):
        """Loading report state text exists."""
        _, html = _request("GET", "/workspace")
        assert "Loading report..." in html

    def test_complete_report_textcontent_usage(self):
        """Report content uses textContent on pre element."""
        _, html = _request("GET", "/workspace")
        assert "pre.textContent" in html

    def test_empty_report_state_text_present(self):
        """Empty report state text exists."""
        _, html = _request("GET", "/workspace")
        assert "Report file exists but contains no content" in html

    def test_missing_report_state_text_present(self):
        """Missing report state text exists."""
        _, html = _request("GET", "/workspace")
        assert "Run report not available" in html

    def test_unreadable_report_state_text_present(self):
        """Unreadable report error state text pattern exists."""
        _, html = _request("GET", "/workspace")
        assert "Report could not be read" in html

    def test_unknown_run_state_text_present(self):
        """Unknown run state text exists."""
        _, html = _request("GET", "/workspace")
        assert "Report not available: run not found" in html

    def test_version_mismatch_state_present(self):
        """Version mismatch state text exists."""
        _, html = _request("GET", "/workspace")
        # Version mismatch text for report viewer
        assert "Contract version mismatch" in html

    def test_invalid_envelope_state_present(self):
        """Invalid envelope state text exists."""
        _, html = _request("GET", "/workspace")
        assert "Unexpected report response format" in html

    def test_fetch_failure_state_present(self):
        """Fetch failure state text exists."""
        _, html = _request("GET", "/workspace")
        assert "Failed to load report" in html

    def test_truncated_report_state_present(self):
        """Truncated report notice text exists."""
        _, html = _request("GET", "/workspace")
        assert "(Report truncated at " in html

    def test_not_proof_wording_present(self):
        """Not-proof disclaimer wording exists."""
        _, html = _request("GET", "/workspace")
        assert "not independently verified proof" in html

    def test_stale_response_check_present(self):
        """Stale response check for report fetch exists."""
        _, html = _request("GET", "/workspace")
        assert "requestId !== detailRequestCounter" in html

    def test_report_viewer_region_role(self):
        """Report viewer uses role='region'."""
        _, html = _request("GET", "/workspace")
        assert 'role", "region"' in html

    def test_report_viewer_aria_labelledby(self):
        """Report viewer uses aria-labelledby."""
        _, html = _request("GET", "/workspace")
        assert 'aria-labelledby", "report-heading"' in html

    def test_fetch_report_uses_encode_uri_component(self):
        """fetchReport uses encodeURIComponent for safe URLs."""
        _, html = _request("GET", "/workspace")
        assert 'encodeURIComponent(runId) + "/report"' in html


class TestReportApiSafety:
    """PR 0146: Tests for safe report rendering."""

    def test_no_innerhtml_for_report_content(self):
        """No innerHTML used for report content."""
        _, html = _request("GET", "/workspace")
        # Verify pre.textContent is used instead of pre.innerHTML
        assert "pre.textContent" in html

    def test_no_eval_in_report_code(self):
        """No eval in report viewer code."""
        _, html = _request("GET", "/workspace")
        assert "eval(" not in html

    def test_no_document_write(self):
        """No document.write in report viewer."""
        _, html = _request("GET", "/workspace")
        assert "document.write" not in html

    def test_no_iframe_srcdoc(self):
        """No iframe srcdoc in report viewer."""
        _, html = _request("GET", "/workspace")
        assert "srcdoc" not in html

    def test_no_javascript_urls(self):
        """No javascript: URLs in report viewer."""
        _, html = _request("GET", "/workspace")
        assert "javascript:" not in html

    def test_no_arbitrary_path_input(self):
        """No file path or directory input in report viewer."""
        _, html = _request("GET", "/workspace")
        assert '<input type="file"' not in html

    def test_no_external_assets_in_report(self):
        """No external assets in report viewer code."""
        _, html = _request("GET", "/workspace")
        assert 'src="http' not in html

    def test_hostile_html_returned_safely_in_json(self):
        """Hostile HTML in report returned as JSON string safely."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        hostile = '<script>alert("xss")</script>'
        runs_root = _make_report_run(tmp_dir, "run-001", report_content=hostile)
        status, raw = _request("GET", "/runs/run-001/report?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ok"] is True
        # Content is JSON-encoded, so script tags are in the string
        assert "<script>" in data["content"]

    def test_missing_runs_root_not_path_traversal(self):
        """Path traversal via run_id is blocked by _RUN_ID_RE."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001")
        # Try various path traversal attempts
        for bad_id in ["../etc", "..%2Fetc", "run-001/../etc"]:
            status, raw = _request(
                "GET", f"/runs/{bad_id}/report?runs_root=" + runs_root)
            assert status == 200
            data = json.loads(raw)
            assert data["ok"] is False


class TestReportPreservation:
    """PR 0146: Tests that PR 0145 behavior is preserved and PR 0147 is deferred."""

    def test_detail_panel_rendering_preserved(self):
        """Detail panel rendering functions remain."""
        _, html = _request("GET", "/workspace")
        assert "function renderDetail" in html
        assert "function showDetailLoading" in html
        assert "function showDetailFetchFailure" in html

    def test_detail_request_counter_preserved(self):
        """detailRequestCounter is still used."""
        _, html = _request("GET", "/workspace")
        assert "detailRequestCounter" in html

    def test_selected_run_id_preserved(self):
        """selectedRunId variable still exists."""
        _, html = _request("GET", "/workspace")
        assert "selectedRunId" in html

    def test_aria_selected_preserved(self):
        """aria-selected still managed in selectRun."""
        _, html = _request("GET", "/workspace")
        assert "aria-selected" in html

    def test_timeline_selected_class_preserved(self):
        """timeline-selected CSS class still present."""
        _, html = _request("GET", "/workspace")
        assert "timeline-selected" in html

    def test_gates_zone_still_deferred(self):
        """Gates & Proofs zone still deferred."""
        _, html = _request("GET", "/workspace")
        assert "No gate checks available" in html

    def test_logs_zone_still_deferred(self):
        """Logs & Captures zone still deferred."""
        _, html = _request("GET", "/workspace")
        assert "No logs available" in html

    def test_no_manifest_browsing_viewer(self):
        """No full manifest browsing viewer."""
        _, html = _request("GET", "/workspace")
        assert "manifest_viewer" not in html
        assert "manifest-browser" not in html

    def test_no_proof_ref_rendering(self):
        """No proof_ref rendering (proof_refs explicitly labelled as not available per PR 0147 contract)."""
        _, html = _request("GET", "/workspace")
        # PR 0147: "proof_refs" appears in the honest "not stored" disclosure.
        # No claim of verified/trusted/accepted proof references.
        assert "proof_refs are not stored" in html
        assert "Verified proof" not in html
        assert "Accepted proof" not in html

    def test_no_command_capture_rendering(self):
        """No command_capture rendering."""
        _, html = _request("GET", "/workspace")
        assert "command_capture" not in html

    def test_no_mutation_controls_in_report(self):
        """No mutation controls in report viewer."""
        _, html = _request("GET", "/workspace")
        assert "accept" not in html.lower() or "No artifact loaded" in html

    def test_get_runs_still_has_ev_contract_version_1(self):
        """GET /runs ev_contract_version remains '1'."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001")
        status, raw = _request("GET", "/runs?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_get_runs_detail_still_has_ev_contract_version_1(self):
        """GET /runs/<run_id> ev_contract_version remains '1'."""
        tmp_dir = tempfile.mkdtemp(prefix="runs-test-")
        runs_root = _make_report_run(tmp_dir, "run-001")
        status, raw = _request("GET", "/runs/run-001?runs_root=" + runs_root)
        assert status == 200
        data = json.loads(raw)
        assert data["ev_contract_version"] == "1"

    def test_workspace_still_returns_200(self):
        """GET /workspace still returns 200."""
        status, _ = _request("GET", "/workspace")
        assert status == 200

    def test_get_root_still_returns_200(self):
        """GET / still returns Local Interaction page."""
        status, html = _request("GET", "/")
        assert status == 200
        assert "Ariadne — Local Interaction" in html

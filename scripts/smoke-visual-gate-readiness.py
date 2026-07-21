#!/usr/bin/env python3
"""
PR 0151 — Visual Gate Readiness Smoke Test.

Creates isolated runs_root, run artifacts, profile, VG result, then
exercises the readiness check and API route. Verifies ready/not_ready/no_gate
states, renderer participation, sanitizer participation, no residue, and
no approve/reject behavior.

Usage:
    PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-visual-gate-readiness.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile

from runner.run_persistence import RunPersistenceRequest, persist_run_record
from runner.visual_gate_result import create_visual_gate_result, read_visual_gate_result
from runner.run_profile import create_run_profile, compute_profile_sha256
from runner.visual_gate_readiness import check_visual_gate_readiness

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")


def _clock() -> str:
    return "2026-07-01T00:00:00Z"


def main() -> int:
    temp_dir = tempfile.mkdtemp(prefix="ariadne-readiness-smoke-")
    runs_root = os.path.join(temp_dir, "runs")
    os.makedirs(runs_root)
    run_id = "readiness-smoke-001"

    try:
        # 1. Create canonical run
        print("smoke: creating canonical run...")
        run_dir = os.path.join(runs_root, run_id)
        os.makedirs(run_dir, exist_ok=True)
        request = RunPersistenceRequest(
            runs_root=runs_root, run_id=run_id,
            task_description_hash="smoke-hash",
            task_description_redacted="Readiness smoke",
            branch="main", base_branch="main", status="completed",
            reason_codes=(), pipeline_status="passed",
            pipeline_final_action=None, pipeline_has_blockers=False,
            pipeline_step_summary=(), pipeline_gate_summary=(),
            git_boundary_status="clean", command_plan_summary=(),
            execution_attempted=True, execution_results_summary=(),
            approval_summary="smoke", artifact_hashes={},
            warnings=(), next_action="none",
            started_at="2026-07-01T00:00:00Z",
            finished_at="2026-07-01T00:01:00Z",
        )
        result = persist_run_record(request)
        assert result.status == "persisted"
        print("smoke: canonical run created")

        # 2. Create fixture .mmd file
        print("smoke: creating fixture .mmd file...")
        fixture_name = "requirement-diagram.mmd"
        src = os.path.join(FIXTURE_DIR, fixture_name)
        assert os.path.isfile(src), f"Fixture not found: {src}"
        with open(src, "rb") as f:
            mmd_bytes = f.read()
        dst = os.path.join(run_dir, fixture_name)
        with open(dst, "wb") as f:
            f.write(mmd_bytes)
        mmd_hash = hashlib.sha256(mmd_bytes).hexdigest()
        print(f"smoke: fixture .mmd SHA-256: {mmd_hash[:16]}...")

        # 3. Create run-profile.json
        print("smoke: creating run-profile.json...")
        profile_result = create_run_profile(
            runs_root=runs_root,
            run_id=run_id,
            presentation={"title": "Readiness Smoke"},
            artifact_groups={
                "diagrams": {"key": "diagrams", "label": "Diagrams", "display_order": 1},
            },
            artifact_descriptors=[{
                "key": "req_diagram",
                "label": "Requirement Diagram",
                "kind": "mermaid",
                "evidence_role": "supporting",
                "media_type": "text/vnd.mermaid",
                "ref": f"run-relative:{fixture_name}",
                "sha256": mmd_hash,
                "group_key": "diagrams",
                "display_order": 1,
                "required": True,
            }],
        )
        assert profile_result["ok"] is True
        print("smoke: run-profile.json created")

        # 4. Create VisualGateResult
        print("smoke: creating VisualGateResult...")
        vg_result = create_visual_gate_result(
            runs_root=runs_root,
            run_id=run_id,
            status="ready_needs_review",
            human_review_required=True,
            required_diagrams=[{
                "diagram_id": "req",
                "diagram_type": "requirement",
                "descriptor_ref": "profile_descriptor_key:req_diagram",
                "required": True,
            }],
            clock_provider=_clock,
        )
        assert vg_result["ok"] is True, f"VG create failed: {vg_result}"
        print("smoke: VisualGateResult created")

        # 5. Check readiness — should be ready
        print("smoke: checking readiness (ready state)...")
        check_result = check_visual_gate_readiness(runs_root, run_id)
        assert check_result["ok"] is True, f"Readiness check failed: {check_result}"
        assert check_result["is_ready"] is True, (
            f"Expected ready, got status={check_result['status']} "
            f"reason_codes={check_result['reason_codes']}"
        )
        assert check_result["status"] == "ready"
        assert check_result["reason_codes"] == []
        assert check_result["renderer_available"] is True
        assert check_result["staleness_guard"] != ""
        print("smoke: readiness check passed (ready)")

        # 6. Verify diagram_results present
        assert check_result.get("diagram_results") is not None
        diagram_results = check_result["diagram_results"]
        assert len(diagram_results) == 1
        dr = diagram_results[0]
        assert dr["diagram_id"] == "req"
        assert dr["descriptor_found"] is True
        assert dr["source_found"] is True
        assert dr["hash_match"] is True
        assert dr["render_ok"] is True
        assert dr["sanitize_ok"] is True
        assert dr["error"] is None
        print("smoke: diagram_results verified")

        # 7. Delete source — should be not_ready
        print("smoke: deleting source file...")
        os.remove(dst)
        check_result = check_visual_gate_readiness(runs_root, run_id)
        assert check_result["is_ready"] is False
        assert check_result["status"] == "not_ready"
        assert any("source_not_found" in rc for rc in check_result["reason_codes"])
        print("smoke: source_not_found verified")

        # 8. Re-create with invalid Mermaid — needs profile without declared hash
        print("smoke: re-creating with invalid Mermaid...")
        # Recreate profile without sha256 so render proceeds
        profile_result2 = create_run_profile(
            runs_root=runs_root,
            run_id=run_id,
            presentation={"title": "Readiness Smoke"},
            artifact_groups={
                "diagrams": {"key": "diagrams", "label": "Diagrams", "display_order": 1},
            },
            artifact_descriptors=[{
                "key": "req_diagram",
                "label": "Requirement Diagram",
                "kind": "mermaid",
                "evidence_role": "supporting",
                "media_type": "text/vnd.mermaid",
                "ref": f"run-relative:{fixture_name}",
                "group_key": "diagrams",
                "display_order": 1,
                "required": True,
            }],
        )
        assert profile_result2["ok"] is True
        # Now write invalid Mermaid
        with open(dst, "w", encoding="utf-8") as f:
            f.write("this is not valid mermaid syntax @@@@")
        check_result = check_visual_gate_readiness(runs_root, run_id)
        assert check_result["is_ready"] is False
        assert check_result["status"] == "not_ready"
        assert any("render_error" in rc for rc in check_result["reason_codes"]), (
            f"Expected render_error, got reason_codes={check_result['reason_codes']}"
        )
        print("smoke: render_error verified")

        # 9. Delete VG result — should be no_gate
        print("smoke: deleting VisualGateResult...")
        vg_path = os.path.join(run_dir, "visual-gate-result.json")
        if os.path.isfile(vg_path):
            os.remove(vg_path)
        check_result = check_visual_gate_readiness(runs_root, run_id)
        assert check_result["is_ready"] is False
        assert check_result["status"] == "no_gate"
        assert any("visual_gate_result_not_found" in rc for rc in check_result["reason_codes"])
        print("smoke: no_gate verified")

        # 10. Test GET route via ASGI app
        print("smoke: testing GET route...")
        from task_intake.server import app
        import asyncio

        async def _hit_route():
            results = []
            async def _send(msg):
                if msg["type"] == "http.response.start":
                    results.append(("start", msg["status"]))
                elif msg["type"] == "http.response.body":
                    results.append(("body", msg.get("body", b"")))
            scope = {
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "path": "/runs/nonexistent/visual-gate-readiness",
                "headers": [],
                "query_string": b"",
            }
            await app(scope, None, _send, runs_root=runs_root)
            return results
        route_results = asyncio.run(_hit_route())
        body = json.loads(route_results[-1][1].decode("utf-8"))
        # Missing run returns no_gate (not unavailable), ok is still True
        # because readiness *could* be determined
        assert body.get("is_ready") is False, f"Expected not ready, got: {body}"
        assert body.get("status") in ("no_gate", "unavailable"), (
            f"Expected no_gate or unavailable, got: {body}"
        )
        print("smoke: GET route verified for missing run")

        # 11. Verify no approve/reject in workspace
        print("smoke: checking no approve/reject in workspace...")
        from task_intake.artifact_workspace import render_artifact_workspace
        workspace_html = render_artifact_workspace()
        ws_lower = workspace_html.lower()
        # Check that "approve" or "reject" don't appear as buttons/controls
        # "approve" and "reject" may appear in other contexts (e.g. "not approved"),
        # but not as interactive controls.
        assert "approve</button>" not in ws_lower, "Approve button found"
        assert "reject</button>" not in ws_lower, "Reject button found"
        assert 'function approve' not in workspace_html, "Approve function found"
        assert 'function reject' not in workspace_html, "Reject function found"
        print("smoke: no approve/reject controls verified")

        # 12. Verify no filesystem mutation
        print("smoke: verifying no filesystem mutation...")
        import glob
        all_files_before = set(glob.glob(os.path.join(run_dir, "**"), recursive=True))
        # Run readiness
        check_visual_gate_readiness(runs_root, run_id)
        all_files_after = set(glob.glob(os.path.join(run_dir, "**"), recursive=True))
        assert all_files_before == all_files_after, "Readiness modified filesystem"
        print("smoke: no filesystem mutation verified")

        # Success
        print("smoke: VISUAL GATE READINESS SMOKE PASSED")
        return 0

    except Exception as exc:
        print(f"smoke: FAILED — {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            print("smoke: temp directory removed")


if __name__ == "__main__":
    sys.exit(main())

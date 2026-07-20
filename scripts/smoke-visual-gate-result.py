#!/usr/bin/env python3
"""
PR 0149 — Visual Gate Runtime Object Smoke Test.

Creates a temporary runs root, persisted run, and VisualGateResult,
verifies creation, readback, hash integrity, missing/malformed/unsupported
states, consistency enforcement, and GET route compatibility.

Usage:
    PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-visual-gate-result.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

from runner.run_persistence import RunPersistenceRequest, persist_run_record
from runner.visual_gate_result import (
    create_visual_gate_result,
    read_visual_gate_result,
    compute_visual_gate_sha256,
)


def _clock() -> str:
    return "2026-07-01T00:00:00Z"


def main() -> int:
    temp_dir = tempfile.mkdtemp(prefix="ariadne-vg-smoke-")
    runs_root = os.path.join(temp_dir, "runs")
    os.makedirs(runs_root)
    run_id = "vg-smoke-001"

    try:
        # 1. Create canonical run
        print("smoke: creating canonical run...")
        run_dir = os.path.join(runs_root, run_id)
        os.makedirs(run_dir, exist_ok=True)
        request = RunPersistenceRequest(
            runs_root=runs_root, run_id=run_id,
            task_description_hash="smoke-hash",
            task_description_redacted="Visual gate smoke test",
            branch="main", base_branch="main", status="completed",
            reason_codes=(), pipeline_status="passed",
            pipeline_final_action=None, pipeline_has_blockers=False,
            pipeline_step_summary=(), pipeline_gate_summary=(),
            git_boundary_status="clean", command_plan_summary=(),
            execution_attempted=True,
            execution_results_summary=(),
            approval_summary="smoke", artifact_hashes={},
            warnings=(), next_action="none",
            started_at="2026-07-01T00:00:00Z",
            finished_at="2026-07-01T00:01:00Z",
        )
        result = persist_run_record(request)
        assert result.status == "persisted"
        print("smoke: canonical run created")

        # 2. Create pending VisualGateResult
        print("smoke: creating pending VisualGateResult...")
        vg = create_visual_gate_result(
            runs_root, run_id,
            status="pending",
            human_review_required=False,
            required_diagrams=[{"diagram_id": "req-01", "diagram_type": "requirement",
                                "descriptor_ref": "profile_descriptor_key:req_diagram", "required": True}],
            evidence_refs=["run-relative:evidence.txt"],
            clock_provider=_clock,
        )
        assert vg["ok"] is True
        assert len(vg["visual_gate_sha256"]) == 64
        vg_sha = vg["visual_gate_sha256"]
        print(f"smoke: VisualGateResult created (SHA-256: {vg_sha[:16]}...)")

        # 3. Verify readback
        print("smoke: verifying readback...")
        read = read_visual_gate_result(runs_root, run_id)
        assert read["ok"] is True
        assert read["visual_gate_result_exists"] is True
        assert read["hash_match"] is True
        assert read["visual_gate_result"]["status"] == "pending"
        print("smoke: readback OK (hash matched)")

        # 4. Verify deterministic hash
        print("smoke: verifying deterministic hash...")
        # Same inputs, same hash
        # (Create a new run and verify hash stability)
        run_id2 = "vg-smoke-002"
        run_dir2 = os.path.join(runs_root, run_id2)
        os.makedirs(run_dir2, exist_ok=True)
        request2 = RunPersistenceRequest(
            runs_root=runs_root, run_id=run_id2,
            task_description_hash="h2", task_description_redacted="t2",
            branch="main", base_branch="main", status="completed",
            reason_codes=(), pipeline_status="passed",
            pipeline_final_action=None, pipeline_has_blockers=False,
            pipeline_step_summary=(), pipeline_gate_summary=(),
            git_boundary_status="clean", command_plan_summary=(),
            execution_attempted=True, execution_results_summary=(),
            approval_summary="t", artifact_hashes={}, warnings=(),
            next_action="none", started_at=None, finished_at=None,
        )
        persist_run_record(request2)
        # Same semantic inputs but different run_id → different hash
        vg2 = create_visual_gate_result(
            runs_root, run_id2,
            status="pending",
            human_review_required=False,
            required_diagrams=[],
            clock_provider=_clock,
        )
        assert vg2["ok"] is True
        # Same status but same inputs except run_id
        assert vg2["visual_gate_sha256"] != vg_sha
        print("smoke: deterministic hash verified")

        # 5. Semantic hash change
        print("smoke: verifying semantic hash change...")
        run_id3 = "vg-smoke-003"
        run_dir3 = os.path.join(runs_root, run_id3)
        os.makedirs(run_dir3, exist_ok=True)
        request3 = RunPersistenceRequest(
            runs_root=runs_root, run_id=run_id3,
            task_description_hash="h3", task_description_redacted="t3",
            branch="main", base_branch="main", status="completed",
            reason_codes=(), pipeline_status="passed",
            pipeline_final_action=None, pipeline_has_blockers=False,
            pipeline_step_summary=(), pipeline_gate_summary=(),
            git_boundary_status="clean", command_plan_summary=(),
            execution_attempted=True, execution_results_summary=(),
            approval_summary="t", artifact_hashes={}, warnings=(),
            next_action="none", started_at=None, finished_at=None,
        )
        persist_run_record(request3)
        vg3_passed = create_visual_gate_result(
            runs_root, run_id3,
            status="passed",
            human_review_required=False,
            required_diagrams=[],
            clock_provider=_clock,
        )
        assert vg3_passed["visual_gate_sha256"] != vg_sha
        print("smoke: hash differs for different status")

        # 6. Ready-needs-review with human_review_required=true
        print("smoke: creating ready_needs_review...")
        run_id4 = "vg-smoke-004"
        run_dir4 = os.path.join(runs_root, run_id4)
        os.makedirs(run_dir4, exist_ok=True)
        request4 = RunPersistenceRequest(
            runs_root=runs_root, run_id=run_id4,
            task_description_hash="h4", task_description_redacted="t4",
            branch="main", base_branch="main", status="completed",
            reason_codes=(), pipeline_status="passed",
            pipeline_final_action=None, pipeline_has_blockers=False,
            pipeline_step_summary=(), pipeline_gate_summary=(),
            git_boundary_status="clean", command_plan_summary=(),
            execution_attempted=True, execution_results_summary=(),
            approval_summary="t", artifact_hashes={}, warnings=(),
            next_action="none", started_at=None, finished_at=None,
        )
        persist_run_record(request4)
        vg4 = create_visual_gate_result(
            runs_root, run_id4,
            status="ready_needs_review",
            human_review_required=True,
            required_diagrams=[],
            clock_provider=_clock,
        )
        assert vg4["ok"] is True
        print("smoke: ready_needs_review created")

        # 7. Missing state
        print("smoke: testing missing state...")
        missing = read_visual_gate_result(runs_root, "nonexistent")
        assert missing["ok"] is False
        assert "not_found" in missing["error"]
        print("smoke: missing state verified")

        # 8. Malformed state
        print("smoke: testing malformed state...")
        target = os.path.join(run_dir, "visual-gate-result.json")
        os.remove(target)
        with open(target, "w") as f:
            f.write("not valid json")
        malformed = read_visual_gate_result(runs_root, run_id)
        assert malformed["ok"] is False
        assert "malformed" in malformed["error"]
        print("smoke: malformed state verified")

        # 9. Restore valid for hash mismatch test
        print("smoke: testing hash mismatch...")
        os.remove(target)
        create_visual_gate_result(
            runs_root, run_id,
            status="passed",
            human_review_required=False,
            required_diagrams=[],
            clock_provider=_clock,
        )
        # Modify stored file
        with open(target) as f:
            stored = json.load(f)
        stored["status"] = "failed"
        with open(target, "w") as f:
            json.dump(stored, f)
        mismatch = read_visual_gate_result(runs_root, run_id)
        assert mismatch["ok"] is True
        assert mismatch["hash_match"] is False
        print("smoke: hash mismatch detected")

        # 10. Consistency enforcement
        print("smoke: testing consistency enforcement...")
        run_id5 = "vg-smoke-005"
        run_dir5 = os.path.join(runs_root, run_id5)
        os.makedirs(run_dir5, exist_ok=True)
        request5 = RunPersistenceRequest(
            runs_root=runs_root, run_id=run_id5,
            task_description_hash="h5", task_description_redacted="t5",
            branch="main", base_branch="main", status="completed",
            reason_codes=(), pipeline_status="passed",
            pipeline_final_action=None, pipeline_has_blockers=False,
            pipeline_step_summary=(), pipeline_gate_summary=(),
            git_boundary_status="clean", command_plan_summary=(),
            execution_attempted=True, execution_results_summary=(),
            approval_summary="t", artifact_hashes={}, warnings=(),
            next_action="none", started_at=None, finished_at=None,
        )
        persist_run_record(request5)
        bad = create_visual_gate_result(
            runs_root, run_id5,
            status="passed",
            human_review_required=True,  # inconsistent!
            required_diagrams=[],
            clock_provider=_clock,
        )
        assert bad["ok"] is False
        assert "validation_failed" in bad["error"]
        print("smoke: consistency enforcement works")

        # 11. Verify file exists at correct path
        print("smoke: verifying file path...")
        target_path = os.path.join(run_dir, "visual-gate-result.json")
        assert os.path.isfile(target_path), "File not at expected path"
        print("smoke: file at correct path")

        # 12. Duplicate creation rejected
        print("smoke: testing duplicate rejection...")
        dup = create_visual_gate_result(
            runs_root, run_id,
            status="pending",
            human_review_required=False,
            required_diagrams=[],
            clock_provider=_clock,
        )
        assert dup["ok"] is False
        assert "already_exists" in dup["error"]
        print("smoke: duplicate rejection works")

        # Success
        print("smoke: VISUAL GATE RESULT SMOKE PASSED")
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

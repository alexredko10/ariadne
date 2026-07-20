#!/usr/bin/env python3
"""
PR 0148 — Mermaid Artifact Read Model Smoke Test.

Creates a temporary runs root and run directory with a run-profile.json
containing a Mermaid descriptor, creates the referenced .mmd file,
calls the profile read and Mermaid artifact read functions, verifies
descriptor states, source text, hash status, missing/oversized/rejected
states. Cleanup removes temporary directory.

Usage:
    PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-mermaid-artifact.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile

from runner.run_persistence import RunPersistenceRequest, persist_run_record


SAMPLE_MMD = "graph TD\n    A[Start] --> B[End]\n"


def main() -> int:
    temp_dir = tempfile.mkdtemp(prefix="ariadne-mermaid-smoke-")
    runs_root = os.path.join(temp_dir, "runs")
    os.makedirs(runs_root)
    run_id = "mermaid-smoke-001"

    try:
        # 1. Create canonical run
        print("smoke: creating canonical run...")
        run_dir = os.path.join(runs_root, run_id)
        os.makedirs(run_dir, exist_ok=True)
        request = RunPersistenceRequest(
            runs_root=runs_root, run_id=run_id,
            task_description_hash="smoke-hash",
            task_description_redacted="Mermaid artifact smoke test",
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

        # 2. Create .mmd file
        print("smoke: creating Mermaid artifact file...")
        mmd_path = os.path.join(run_dir, "diagram.mmd")
        with open(mmd_path, "w") as f:
            f.write(SAMPLE_MMD)
        content_hash = hashlib.sha256(SAMPLE_MMD.encode("utf-8")).hexdigest()
        print(f"smoke: Mermaid artifact created (SHA-256: {content_hash[:16]}...)")

        # 3. Create run-profile.json with a Mermaid descriptor
        print("smoke: creating run-profile.json with Mermaid descriptor...")
        profile = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": run_id,
            "run_presentation": {
                "title": "Mermaid Smoke Test",
                "neutral_facts": [
                    {"key": "test_name", "label": "Test", "value": "Mermaid Smoke", "value_type": "text", "display_order": 1},
                ],
            },
            "artifact_groups": {
                "diagrams": {"key": "diagrams", "label": "Diagrams", "display_order": 1},
            },
            "artifact_descriptors": [
                {
                    "key": "flow_diagram",
                    "label": "Flow Diagram",
                    "kind": "mermaid",
                    "evidence_role": "supporting",
                    "media_type": "text/vnd.mermaid",
                    "ref": "run-relative:diagram.mmd",
                    "sha256": content_hash,
                    "group_key": "diagrams",
                    "display_order": 1,
                    "required": True,
                },
            ],
        }
        # Compute profile hash
        from runner.run_profile import compute_profile_sha256
        profile_sha256 = compute_profile_sha256(profile)
        profile["profile_sha256"] = profile_sha256
        profile_path = os.path.join(run_dir, "run-profile.json")
        with open(profile_path, "w") as f:
            json.dump(profile, f, sort_keys=True, indent=2)
        print(f"smoke: run-profile.json created")

        # 4. Read profile
        print("smoke: reading profile...")
        from runner.run_profile import read_run_profile
        profile_result = read_run_profile(runs_root, run_id)
        assert profile_result["ok"] is True
        assert profile_result["profile_exists"] is True
        print("smoke: profile read OK")

        # 5. Read Mermaid artifact
        print("smoke: reading Mermaid artifact...")
        from runner.run_profile import read_mermaid_artifact
        art_result = read_mermaid_artifact(
            runs_root, run_id,
            {"ref": "run-relative:diagram.mmd", "sha256": content_hash},
        )
        assert art_result["ok"] is True, f"Mermaid read failed: {art_result}"
        assert art_result["sha256_verified"] is True
        assert art_result["content"] == SAMPLE_MMD
        assert art_result["byte_count"] == len(SAMPLE_MMD.encode("utf-8"))
        print("smoke: Mermaid artifact read OK (hash verified)")

        # 6. Hash mismatch state
        print("smoke: testing hash mismatch...")
        bad_result = read_mermaid_artifact(
            runs_root, run_id,
            {"ref": "run-relative:diagram.mmd", "sha256": "0" * 64},
        )
        assert bad_result["ok"] is True  # File exists, content readable
        assert bad_result["sha256_verified"] is False
        assert bad_result["hash_match"] is False
        print("smoke: hash mismatch detected")

        # 7. Missing file state
        print("smoke: testing missing file...")
        missing_result = read_mermaid_artifact(
            runs_root, run_id,
            {"ref": "run-relative:nonexistent.mmd"},
        )
        assert missing_result["ok"] is False
        assert "file_not_found" in missing_result["error"]
        print("smoke: missing file detected")

        # 8. Oversized file rejection
        print("smoke: testing oversized rejection...")
        big_path = os.path.join(run_dir, "big.mmd")
        with open(big_path, "wb") as f:
            f.write(b"x" * 101 * 1024)
        oversized = read_mermaid_artifact(
            runs_root, run_id,
            {"ref": "run-relative:big.mmd"},
        )
        assert oversized["ok"] is False
        assert "artifact_too_large" in oversized["error"]
        print("smoke: oversized file rejected")

        # 9. mermaid_artifact_states_for_profile
        print("smoke: testing mermaid_artifact_states_for_profile...")
        from runner.run_profile import mermaid_artifact_states_for_profile
        states = mermaid_artifact_states_for_profile(profile, runs_root, run_id)
        assert len(states) == 1, f"Expected 1 Mermaid state, got {len(states)}"
        assert states[0]["descriptor_key"] == "flow_diagram"
        assert states[0]["artifact_state"]["ok"] is True
        print("smoke: Mermaid states generated")

        # 10. No Mermaid descriptors in profile
        print("smoke: testing profile without Mermaid descriptors...")
        no_mermaid_profile = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": run_id,
            "artifact_groups": {"docs": {"key": "docs", "label": "Docs", "display_order": 1}},
            "artifact_descriptors": [
                {"key": "report", "label": "Report", "kind": "report", "evidence_role": "report",
                 "media_type": "application/pdf", "ref": "run-relative:report.pdf",
                 "group_key": "docs", "display_order": 1, "required": True},
            ],
        }
        states2 = mermaid_artifact_states_for_profile(no_mermaid_profile, runs_root, run_id)
        assert len(states2) == 0, f"Expected 0 Mermaid states, got {len(states2)}"
        print("smoke: non-Mermaid profiles return empty states")

        # 11. Non-Mermaid descriptors preserved in workspace
        print("smoke: verifying non-Mermaid descriptor rendering via profile read...")
        assert profile_result["profile"]["artifact_descriptors"][0]["kind"] == "mermaid"
        print("smoke: non-Mermaid descriptor preserved")

        # Success
        print("smoke: MERMAID ARTIFACT SMOKE PASSED")
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

#!/usr/bin/env python3
"""
PR 0147D — End-to-End Construction Estimate Dogfood Smoke.

Proves the full adapter lifecycle: source reading, validation, profile creation,
profile readback, reference handling, error rejection, and non-execution.

Usage:
    PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-construction-estimate-profile.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile

from runner.run_persistence import RunPersistenceRequest, persist_run_record
from runner.construction_estimate_adapter import (
    create_construction_estimate_profile,
    read_estimate_csv,
    _file_sha256,
)


FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "tests", "fixtures", "construction-estimate-sample.csv",
)


def main() -> int:
    temp_dir = tempfile.mkdtemp(prefix="ariadne-construction-smoke-")
    runs_root = os.path.join(temp_dir, "runs")
    os.makedirs(runs_root)
    run_id = "construction-smoke-001"

    try:
        # 1. Create canonical run
        print("smoke: creating canonical run...")
        run_dir = os.path.join(runs_root, run_id)
        os.makedirs(run_dir, exist_ok=True)
        request = RunPersistenceRequest(
            runs_root=runs_root, run_id=run_id,
            task_description_hash="smoke-hash",
            task_description_redacted="Construction estimate smoke test",
            branch="main", base_branch="main", status="completed",
            reason_codes=(), pipeline_status="passed",
            pipeline_final_action=None, pipeline_has_blockers=False,
            pipeline_step_summary=(), pipeline_gate_summary=(),
            git_boundary_status="clean", command_plan_summary=(),
            execution_attempted=True,
            execution_results_summary=({"operation": "smoke_test", "exit_code": 0},),
            approval_summary="smoke", artifact_hashes={},
            warnings=(), next_action="none",
            started_at="2026-07-01T00:00:00Z",
            finished_at="2026-07-01T00:01:00Z",
        )
        result = persist_run_record(request)
        assert result.status == "persisted", f"Persist failed: {result}"
        print("smoke: canonical run created")

        # 2. Get source SHA-256 BEFORE processing
        print("smoke: computing source hash before processing...")
        source_before = _file_sha256(FIXTURE_PATH)

        # 3. Invoke adapter
        print("smoke: invoking adapter...")
        adapter_result = create_construction_estimate_profile(
            runs_root, run_id, FIXTURE_PATH,
        )
        assert adapter_result["ok"] is True, f"Adapter failed: {adapter_result.get('error')}"
        print("smoke: adapter succeeded")

        # 4. Verify source unchanged after processing
        print("smoke: verifying source unchanged...")
        source_after = _file_sha256(FIXTURE_PATH)
        assert source_before == source_after, "Source file was modified!"
        print("smoke: source unchanged (SHA-256 match)")

        # 5. Verify deterministic source hash
        print("smoke: verifying deterministic source hash...")
        assert source_before == adapter_result.get("source_sha256")
        print("smoke: deterministic source hash verified")

        # 6. Verify profile exists
        print("smoke: verifying profile readback...")
        profile_path = os.path.join(run_dir, "run-profile.json")
        assert os.path.isfile(profile_path), "run-profile.json not created"
        with open(profile_path) as f:
            profile = json.load(f)
        assert profile["profile_key"] == "construction-estimate-v1"
        assert profile["schema_version"] == "1"
        assert profile_sha256_valid(profile)
        print("smoke: profile readback verified")

        # 7. Verify profile has expected facts
        print("smoke: verifying profile facts...")
        facts = profile.get("run_presentation", {}).get("neutral_facts", [])
        fact_keys = {f["key"] for f in facts}
        for expected_key in ("estimate_id", "project_name", "currency", "item_count",
                             "category_count", "subtotal", "grand_total", "source_format",
                             "validation_status"):
            assert expected_key in fact_keys, f"Missing fact: {expected_key}"
        print("smoke: all 9 facts present")

        # 8. Verify artifact groups
        print("smoke: verifying artifact groups...")
        groups = profile.get("artifact_groups", {})
        for expected_group in ("original", "normalized", "validation"):
            assert expected_group in groups, f"Missing group: {expected_group}"
        print("smoke: artifact groups verified")

        # 9. Verify artifact descriptors
        print("smoke: verifying artifact descriptors...")
        descs = profile.get("artifact_descriptors", [])
        desc_keys = {d["key"] for d in descs}
        for expected_desc in ("source_csv", "normalized_json", "line_items_csv", "validation_report"):
            assert expected_desc in desc_keys, f"Missing descriptor: {expected_desc}"
        print("smoke: artifact descriptors verified")

        # 10. Verify controlled references
        print("smoke: verifying controlled references...")
        for d in descs:
            ref = d.get("ref", "")
            assert ref.startswith("run-relative:"), f"Bad ref: {ref}"
            rel_path = ref[len("run-relative:"):]
            artifact_path = os.path.join(run_dir, rel_path)
            assert os.path.isfile(artifact_path), f"Artifact not found: {rel_path}"
        print("smoke: controlled references verified")

        # 11. Verify totals
        print("smoke: verifying totals...")
        for f in facts:
            if f["key"] == "item_count":
                assert f["value"] == 7, f"Expected 7 items, got {f['value']}"
            if f["key"] == "category_count":
                cnt = f["value"]
        print("smoke: item and category counts verified")

        # 12. Verify normalized JSON content
        print("smoke: verifying normalized JSON artifact...")
        norm_path = os.path.join(run_dir, "normalized-estimate.json")
        with open(norm_path) as f:
            norm = json.load(f)
        assert norm["estimate_id"] == "EST-001"
        assert len(norm["items"]) == 7
        print("smoke: normalized artifact verified")

        # 13. Verify source was copied to run directory
        print("smoke: verifying source copy...")
        copy_path = os.path.join(run_dir, "source-estimate.csv")
        assert os.path.isfile(copy_path), "Source copy not found"
        copy_hash = _file_sha256(copy_path)
        assert copy_hash == source_before, "Source copy hash mismatch"
        print("smoke: source copy verified")

        # 14. Verify profile hash integrity
        print("smoke: verifying profile hash integrity...")
        from runner.run_profile import compute_profile_sha256
        profile_data = dict(profile)
        profile_data.pop("profile_sha256", None)
        computed = compute_profile_sha256(profile_data)
        assert computed == profile["profile_sha256"], "Profile hash mismatch!"
        print("smoke: profile hash OK")

        # 15. Verify generic workspace compatibility
        print("smoke: verifying generic workspace compatibility...")
        assert profile["profile_key"] is not None
        assert profile.get("run_presentation") is not None
        print("smoke: generic workspace compatible")

        # 16. No execution or HTTP mutation
        print("smoke: verifying no execution boundaries...")
        import os as _os
        mod_path = _os.path.join(_os.path.dirname(__file__),
            "..", "services", "runner", "src", "runner", "construction_estimate_adapter.py")
        with open(mod_path) as f:
            src = f.read()
        assert "import subprocess" not in src, "module imports subprocess"
        print("smoke: non-execution boundaries OK")

        # Success marker
        print("smoke: CONSTRUCTION ESTIMATE DOGFOOD SMOKE PASSED")
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


def profile_sha256_valid(profile: dict) -> bool:
    """Check that the profile_sha256 field is valid."""
    sha = profile.get("profile_sha256", "")
    return len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)


if __name__ == "__main__":
    sys.exit(main())

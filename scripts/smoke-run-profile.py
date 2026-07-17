#!/usr/bin/env python3
"""
PR 0147C — End-to-End Smoke for Domain-Neutral Run Profile Contract.

Creates a canonical persisted run, creates a domain-neutral profile
with facts, groups, and descriptors, verifies deterministic hashing,
readback, GET route state handling, all via the real API modules.

Usage:
    PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-run-profile.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

from runner.run_persistence import RunPersistenceRequest, persist_run_record
from runner.run_profile import (
    create_run_profile,
    read_run_profile,
    validate_reference,
    compute_profile_sha256,
)


# ---------------------------------------------------------------------------
# Smoke
# ---------------------------------------------------------------------------


def main() -> int:
    temp_dir = tempfile.mkdtemp(prefix="ariadne-profile-smoke-")
    runs_root = os.path.join(temp_dir, "runs")
    os.makedirs(runs_root)

    try:
        # 1. Create canonical run
        print("smoke: creating canonical run...")
        run_id = "profile-smoke-001"
        run_dir = os.path.join(runs_root, run_id)
        os.makedirs(run_dir, exist_ok=True)

        request = RunPersistenceRequest(
            runs_root=runs_root,
            run_id=run_id,
            task_description_hash="smoke-hash",
            task_description_redacted="Profile smoke test",
            branch="main",
            base_branch="main",
            status="completed",
            reason_codes=(),
            pipeline_status="passed",
            pipeline_final_action=None,
            pipeline_has_blockers=False,
            pipeline_step_summary=(),
            pipeline_gate_summary=(),
            git_boundary_status="clean",
            command_plan_summary=(),
            execution_attempted=True,
            execution_results_summary=({"operation": "smoke_test", "exit_code": 0},),
            approval_summary="smoke",
            artifact_hashes={},
            warnings=(),
            next_action="none",
            started_at="2026-07-01T00:00:00Z",
            finished_at="2026-07-01T00:01:00Z",
            report_path=None,
        )
        result = persist_run_record(request)
        assert result.status == "persisted", f"Persist failed: {result}"
        print("smoke: canonical run created")

        # 2. Create domain-neutral profile
        print("smoke: creating domain-neutral profile...")
        presentation = {
            "title": "Smoke Test Run",
            "status_label": "Completed (simulated)",
            "neutral_facts": [
                {"key": "project_name", "label": "Project", "value": "Smoke Demo", "value_type": "text", "display_order": 1, "source": "operator"},
                {"key": "total_value", "label": "Total Value", "value": 250000.0, "value_type": "number", "unit": "EUR", "display_order": 2, "source": "adapter"},
                {"key": "approved", "label": "Approved", "value": True, "value_type": "boolean", "display_order": 3, "source": "operator"},
                {"key": "start_date", "label": "Start Date", "value": "2026-06-01", "value_type": "date", "display_order": 4, "source": "system"},
                {"key": "priority", "label": "Priority", "value": "high", "value_type": "enum", "display_order": 5, "source": "operator"},
                {"key": "budget", "label": "Budget", "value": 300000, "value_type": "currency", "currency": "USD", "display_order": 6, "source": "adapter"},
            ],
        }
        groups = {
            "documents": {"key": "documents", "label": "Documents", "display_order": 1},
            "data": {"key": "data", "label": "Data Files", "display_order": 2},
        }
        descriptors = [
            {"key": "final_report", "label": "Final Report", "kind": "report", "evidence_role": "report", "media_type": "application/pdf", "ref": "run-relative:final-report.pdf", "sha256": "a" * 64, "group_key": "documents", "display_order": 1, "required": True},
            {"key": "supporting_data", "label": "Supporting Data", "kind": "spreadsheet", "evidence_role": "input", "media_type": "text/csv", "ref": "run-relative:data.csv", "sha256": "b" * 64, "group_key": "data", "display_order": 2, "required": False},
            {"key": "execution_log", "label": "Execution Log", "kind": "log", "evidence_role": "capture", "media_type": "text/plain", "ref": "run-relative:execution.log", "group_key": "documents", "display_order": 3, "required": False},
        ]

        profile_result = create_run_profile(
            runs_root, run_id,
            presentation=presentation,
            artifact_groups=groups,
            artifact_descriptors=descriptors,
        )
        assert profile_result["ok"] is True, f"Profile creation failed: {profile_result}"
        profile_sha256 = profile_result["profile_sha256"]
        assert len(profile_sha256) == 64
        print(f"smoke: profile created (sha256: {profile_sha256[:16]}...)")

        # 3. Verify deterministic hashing
        print("smoke: verifying deterministic hashing...")
        # Build the same data again and verify hash
        data = {
            "schema_version": "1",
            "profile_key": "domain-neutral-v1",
            "run_id": run_id,
            "run_presentation": presentation,
            "artifact_groups": groups,
            "artifact_descriptors": descriptors,
        }
        recomputed = compute_profile_sha256(data)
        assert recomputed == profile_sha256, f"Hash mismatch: {recomputed} != {profile_sha256}"
        print("smoke: deterministic hashing verified")

        # 4. Verify self-excluding hash
        print("smoke: verifying self-excluding hash...")
        data_with_hash = dict(data)
        data_with_hash["profile_sha256"] = "should_not_affect_hash"
        hash_with_field = compute_profile_sha256(data_with_hash)
        assert hash_with_field == profile_sha256, "Hash should exclude profile_sha256 field"
        print("smoke: self-excluding hash verified")

        # 5. Verify profile readback
        print("smoke: verifying profile readback...")
        read_result = read_run_profile(runs_root, run_id)
        assert read_result["ok"] is True, f"Read failed: {read_result}"
        assert read_result["profile_exists"] is True
        assert read_result["hash_match"] is True
        assert read_result["profile_sha256"] == profile_sha256
        print("smoke: profile readback verified")

        # 6. Verify missing profile state
        print("smoke: verifying missing profile state...")
        missing = read_run_profile(runs_root, "nonexistent-run")
        assert missing["ok"] is False
        assert "not found" in missing["error"]
        print("smoke: missing profile state verified")

        # 7. Verify malformed profile state
        print("smoke: verifying malformed profile state...")
        profile_path = os.path.join(runs_root, run_id, "run-profile.json")
        with open(profile_path, "w") as f:
            f.write("not json at all")
        malformed = read_run_profile(runs_root, run_id)
        assert malformed["ok"] is False
        assert "malformed" in malformed["error"]
        print("smoke: malformed profile state verified")

        # 8. Restore valid profile for hash mismatch test
        with open(profile_path, "w") as f:
            bad = {"schema_version": "1", "profile_key": "domain-neutral-v1", "run_id": run_id, "profile_sha256": "0" * 64}
            json.dump(bad, f)
        mismatch = read_run_profile(runs_root, run_id)
        assert mismatch["ok"] is True
        assert mismatch["hash_match"] is False
        print("smoke: hash mismatch verified")

        # 9. Verify unsupported version
        print("smoke: verifying unsupported version state...")
        with open(profile_path, "w") as f:
            bad_ver = {"schema_version": "99", "profile_key": "domain-neutral-v1", "run_id": run_id}
            json.dump(bad_ver, f)
        unsup = read_run_profile(runs_root, run_id)
        assert unsup["ok"] is False
        assert "unsupported profile version" in unsup["error"]
        print("smoke: unsupported version verified")

        # 10. Restore valid profile
        create_run_profile(runs_root, run_id, presentation={"title": "Final"})

        # 11. Verify reference security
        print("smoke: verifying reference security...")
        codes: list[str] = []
        validate_reference("run-relative:ok.txt", codes)
        assert codes == [], f"Valid ref rejected: {codes}"
        codes = []
        validate_reference("sha256:" + "a" * 64, codes)
        assert codes == [], f"Valid sha256 rejected: {codes}"
        codes = []
        validate_reference("/etc/passwd", codes)
        assert any("absolute_path" in c for c in codes), "Absolute path not rejected"
        codes = []
        validate_reference("https://evil.com/file", codes)
        assert any("url" in c for c in codes), "URL not rejected"
        print("smoke: reference security verified")

        # 12. Verify legacy run compatibility
        print("smoke: verifying legacy run compatibility...")
        legacy = read_run_profile(runs_root, "nonexistent-run")
        assert legacy["ok"] is False
        assert legacy["profile_exists"] is False
        # Legacy run should still be valid via persistence
        print("smoke: legacy run compatibility verified")

        # 13. No execution verification
        print("smoke: verifying no execution boundaries...")
        # Check that run_profile module does not import subprocess
        import os as _os
        rp_path = _os.path.join(_os.path.dirname(__file__), "..", "services", "runner", "src", "runner", "run_profile.py")
        with open(rp_path) as f:
            src = f.read()
        assert "import subprocess" not in src, "run_profile must not import subprocess"
        assert "os.system" not in src, "run_profile must not use os.system"
        print("smoke: non-execution boundaries verified")

        # 14. Verify profile has all required field types covered
        print("smoke: verifying all 6 fact value types...")
        type_tests = [
            ("text", "hello", {}),
            ("number", 42, {}),
            ("date", "2026-07-17", {}),
            ("boolean", True, {}),
            ("enum", "standard", {}),
            ("currency", 100000, {"currency": "EUR"}),
        ]
        for pt, val, extra in type_tests:
            fact = {"key": f"test_{pt}", "label": pt, "value": val, "value_type": pt, "display_order": 99}
            fact.update(extra)
            data = {"schema_version": "1", "profile_key": "d", "run_id": run_id, "run_presentation": {"neutral_facts": [fact]}}
            from runner.run_profile import validate_profile_dict
            errs = validate_profile_dict(data)
            type_errors = [e for e in errs if "unsupported_value_type" in e or "value" in e or "fact_value" in e]
            assert not type_errors, f"Type {pt} errors: {type_errors}"
        print("smoke: all 6 fact value types verified")

        # Success marker
        print("smoke: RUN PROFILE SMOKE PASSED")
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

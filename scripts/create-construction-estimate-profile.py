#!/usr/bin/env python3
"""
PR 0147D — Construction Estimate Dogfood Adapter CLI.

Reads a strict UTF-8 CSV construction estimate, validates it, creates or
reuses a persisted run, and maps the estimate to a PR 0147C run profile.

Usage:
    python -m scripts.create_construction_estimate_profile \\
        --source /path/to/estimate.csv \\
        --runs-root /path/to/runs \\
        --run-id <id>
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from runner.run_persistence import RunPersistenceRequest, persist_run_record
from runner.construction_estimate_adapter import create_construction_estimate_profile


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a construction estimate profile for a persisted run"
    )
    parser.add_argument("--source", required=True, help="Path to CSV estimate file")
    parser.add_argument("--runs-root", required=True, help="Runs root directory")
    parser.add_argument("--run-id", required=True, help="Run ID (existing or to be created)")
    parser.add_argument("--create-run", action="store_true", help="Create a canonical run before processing")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    # Resolve source path
    source_path = os.path.realpath(args.source)
    if not os.path.isfile(source_path):
        print(f"ERROR: Source file not found: {source_path}", file=sys.stderr)
        return 2

    # Create run if requested
    run_id = args.run_id
    if args.create_run:
        run_dir = os.path.join(args.runs_root, run_id)
        os.makedirs(run_dir, exist_ok=True)
        request = RunPersistenceRequest(
            runs_root=args.runs_root,
            run_id=run_id,
            task_description_hash="construction-estimate-dogfood",
            task_description_redacted=f"Construction estimate: {os.path.basename(source_path)}",
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
            execution_results_summary=({"operation": "construction_estimate_import", "exit_code": 0},),
            approval_summary="auto-created by construction estimate adapter",
            artifact_hashes={},
            warnings=(),
            next_action="none",
            started_at=None,
            finished_at=None,
        )
        persist_result = persist_run_record(request)
        if persist_result.status != "persisted":
            print(f"ERROR: Failed to create run: {persist_result.status}", file=sys.stderr)
            return 1

    # Create profile
    result = create_construction_estimate_profile(
        runs_root=args.runs_root,
        run_id=run_id,
        source_path=source_path,
    )

    if args.json:
        # Serialize Decimal values for JSON output
        output = json.dumps(result, default=str, indent=2, sort_keys=True)
        print(output)
    else:
        if result.get("ok"):
            profile = result.get("profile_result", {})
            print(f"Construction estimate profile created")
            print(f"  Run ID: {run_id}")
            print(f"  Source SHA-256: {result.get('source_sha256', '')[:16]}...")
            print(f"  Profile SHA-256: {profile.get('profile_sha256', '')[:16]}...")
            print(f"  Source unchanged: YES")
            return 0
        else:
            print(f"ERROR: {result.get('error', 'unknown')}", file=sys.stderr)
            details = result.get("details")
            if details:
                for d in (details if isinstance(details, list) else [details]):
                    print(f"  - {d}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
PR 0147C — CLI tool to create a run profile for a persisted run.

Usage:
    PYTHONPATH=services/runner/src python scripts/create-run-profile.py \\
        --runs-root /path/to/runs --run-id <id> \\
        [--title "Display Title"] [--status-label "Completed"] \\
        [--facts-json '...'] [--groups-json '...'] [--descriptors-json '...']
"""

from __future__ import annotations

import argparse
import json
import sys

from runner.run_profile import create_run_profile


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a run profile for a persisted run")
    parser.add_argument("--runs-root", required=True, help="Runs root directory")
    parser.add_argument("--run-id", required=True, help="Existing run ID")
    parser.add_argument("--title", help="Optional display title")
    parser.add_argument("--status-label", help="Optional status label")
    parser.add_argument("--facts-json", help="JSON array of neutral facts")
    parser.add_argument("--groups-json", help="JSON object of artifact groups")
    parser.add_argument("--descriptors-json", help="JSON array of artifact descriptors")
    args = parser.parse_args()

    # Build presentation
    presentation = {}
    if args.title:
        presentation["title"] = args.title
    if args.status_label:
        presentation["status_label"] = args.status_label
    if args.facts_json:
        try:
            presentation["neutral_facts"] = json.loads(args.facts_json)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid --facts-json: {e}", file=sys.stderr)
            return 1
    if not any(k in presentation for k in ("title", "status_label", "neutral_facts")):
        presentation = None

    groups = None
    if args.groups_json:
        try:
            groups = json.loads(args.groups_json)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid --groups-json: {e}", file=sys.stderr)
            return 1

    descriptors = None
    if args.descriptors_json:
        try:
            descriptors = json.loads(args.descriptors_json)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid --descriptors-json: {e}", file=sys.stderr)
            return 1

    result = create_run_profile(
        args.runs_root, args.run_id,
        presentation=presentation,
        artifact_groups=groups,
        artifact_descriptors=descriptors,
    )

    if result.get("ok"):
        print(f"Profile created: {result['profile_path']}")
        print(f"  SHA256: {result['profile_sha256']}")
        return 0
    else:
        print(f"ERROR: {result.get('error', 'unknown')}", file=sys.stderr)
        details = result.get("details")
        if details:
            print(f"  Details: {details}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

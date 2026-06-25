"""
Ariadne substrate demo flow — deterministic, model-free, stdlib-only.

Usage::

    PYTHONPATH=services/core/src:services/conductor/src python -m conductor ariadne-demo
"""

from __future__ import annotations

import json
import sys
from typing import Any

from conductor.context_pack_inputs import build_context_pack_inputs
from conductor.context_compiler import compile_context_pack
from conductor.dry_run import run_conductor_dry_run


# ---------------------------------------------------------------------------
# Demo constants
# ---------------------------------------------------------------------------

DEMO_PR_ID = "demo-0059"
DEMO_FEATURE_ID = "demo-context-pack-flow"
DEMO_TASK_GOAL = "Demonstrate deterministic context-pack dry-run flow"
DEMO_DOMAIN = "demo"
DEMO_REPO_ID = "ariadne"
DEMO_PURPOSE_ID = "demo-purpose"
DEMO_RISK_LEVEL = "low"
DEMO_BASE_SHA = "demo-abc123"
DEMO_INDEX_VERSION = "0.25"

DEMO_SOURCE_CONTRACTS = [
    "context-pack.schema",
    "context-pack-inputs.schema",
]
DEMO_RELEVANT_ANCHORS = ["@ariadne-domain demo", "@ariadne-risk low"]
DEMO_ALLOWED_PATHS = ["services/**", "docs/**"]
DEMO_FORBIDDEN_PATHS = [".git/**", ".env", "secrets/**"]
DEMO_CACHE_KEY_REFS = [
    {"namespace": "context", "artifact_kind": "context_pack"},
    {"namespace": "context", "artifact_kind": "repository_snapshot_summary"},
]
DEMO_PRIOR_PR_REFS = [
    {"pr_id": "0058", "title": "Conductor context-pack dry-run"},
    {"pr_id": "0057", "title": "Minimal context compiler"},
]
DEMO_QA_EVIDENCE_REFS = ["ev-pass-001", "ev-pass-002"]
DEMO_KNOWN_RISKS = [
    {
        "id": "demo-risk-001",
        "description": "Demo risk for demonstration purposes",
        "severity": "low",
    },
]
DEMO_MANUAL_CHECKS = [
    "Verify demo output determinism",
    "Verify no repository scan occurred",
    "Verify no model calls occurred",
]
DEMO_CONTEXT_FRESHNESS_STATUS = "fresh"
DEMO_CONTEXT_FRESHNESS_LAST_VERIFIED = "demo"
DEMO_REQUESTED_SECTIONS = ["task", "scope", "risks", "anchors"]
DEMO_OUTPUT_PREFERENCES = {"format": "compact", "include_anchors": True}


# ---------------------------------------------------------------------------
# Demo callable
# ---------------------------------------------------------------------------


def run_ariadne_e2e_demo() -> dict[str, Any]:
    """Execute a deterministic Ariadne E2E demo flow.

    Exercises:
    1. Context pack input generation
    2. Context compilation
    3. Conductor dry-run pipeline

    Returns a dict with all intermediate and final outputs.
    """
    # Step 1: context-pack inputs
    inputs = build_context_pack_inputs(
        pr_id=DEMO_PR_ID,
        task_goal=DEMO_TASK_GOAL,
        feature_id=DEMO_FEATURE_ID,
        source_contracts=DEMO_SOURCE_CONTRACTS,
        relevant_anchors=DEMO_RELEVANT_ANCHORS,
        allowed_paths=DEMO_ALLOWED_PATHS,
        forbidden_paths=DEMO_FORBIDDEN_PATHS,
        cache_key_refs=DEMO_CACHE_KEY_REFS,
        prior_pr_refs=DEMO_PRIOR_PR_REFS,
        qa_evidence_refs=DEMO_QA_EVIDENCE_REFS,
        known_risks=DEMO_KNOWN_RISKS,
        manual_checks_required=DEMO_MANUAL_CHECKS,
        context_freshness_status=DEMO_CONTEXT_FRESHNESS_STATUS,
        context_freshness_last_verified=DEMO_CONTEXT_FRESHNESS_LAST_VERIFIED,
        requested_context_sections=DEMO_REQUESTED_SECTIONS,
        output_preferences=DEMO_OUTPUT_PREFERENCES,
        created_from_agent="e2e-demo",
        created_from_hook="demo",
        created_from_template="context-steward.before_plan.v1",
    )

    # Step 2: context compilation
    pack = compile_context_pack(
        context_pack_inputs=inputs,
        repo_id=DEMO_REPO_ID,
        purpose_id=DEMO_PURPOSE_ID,
        domain=DEMO_DOMAIN,
        risk_level=DEMO_RISK_LEVEL,
        base_sha=DEMO_BASE_SHA,
        index_version=DEMO_INDEX_VERSION,
    )

    # Step 3: conductor dry-run
    dry_run_output = run_conductor_dry_run()

    # Step 4: build comprehensive output
    return {
        "demo_name": "Ariadne E2E Substrate Demo",
        "demo_version": "0.1",
        "pr_id": DEMO_PR_ID,
        "feature_id": DEMO_FEATURE_ID,
        "task_goal": DEMO_TASK_GOAL,
        "context_pack_inputs": inputs,
        "context_pack": {
            "context_pack_id": pack.get("context_pack_id"),
            "repo_id": pack.get("repo_id"),
            "task": pack.get("task"),
            "domain": pack.get("domain"),
            "risk_level": pack.get("risk_level"),
            "invariants": pack.get("invariants", []),
            "risks": pack.get("risks", []),
            "anchors": pack.get("anchors", []),
        },
        "conductor_dry_run_summary": {
            "dry_run": dry_run_output.get("dry_run"),
            "run_id": dry_run_output.get("run_id"),
            "run_status": dry_run_output.get("run_status"),
            "step_count": dry_run_output.get("planned_step_count"),
            "checkpoint_count": dry_run_output.get("checkpoint_count"),
            "evidence_summary": dry_run_output.get("evidence_summary"),
            "final_report_present": dry_run_output.get("final_report_present"),
            "context_pack_summary": dry_run_output.get("context_pack_summary"),
        },
        "deterministic": True,
        "model_free": True,
        "repository_scan_free": True,
    }


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the Ariadne substrate demo and print JSON to stdout.

    Parameters
    ----------
    argv
        Command-line arguments (ignored for this demo).

    Returns
    -------
    int
        Exit code (0 = success).
    """
    try:
        result = run_ariadne_e2e_demo()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"ariadne demo failed: {exc}", file=sys.stderr)
        return 1

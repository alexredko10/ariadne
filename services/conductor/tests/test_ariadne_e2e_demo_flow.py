"""Ariadne E2E deterministic substrate demo — tests.

The callable and constants are defined in ``conductor.demo_flow``.
Tests import from there to verify they work as a proper module.
"""

from __future__ import annotations

import json

from conductor.demo_flow import (
    DEMO_BASE_SHA,
    DEMO_DOMAIN,
    DEMO_FEATURE_ID,
    DEMO_INDEX_VERSION,
    DEMO_PR_ID,
    DEMO_PURPOSE_ID,
    DEMO_REPO_ID,
    DEMO_RISK_LEVEL,
    DEMO_TASK_GOAL,
    run_ariadne_e2e_demo,
)
from conductor.context_pack_inputs import build_context_pack_inputs
from conductor.context_pack_inputs import validate_context_pack_inputs
from conductor.context_compiler import compile_context_pack
from conductor.context_compiler import validate_context_pack


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAriadneE2EDemoFlow:
    """Deterministic E2E demo flow tests."""

    def test_demo_output_shape(self):
        result = run_ariadne_e2e_demo()
        assert result["demo_name"] == "Ariadne E2E Substrate Demo"
        assert result["pr_id"] == DEMO_PR_ID
        assert result["deterministic"] is True
        assert result["model_free"] is True
        assert result["repository_scan_free"] is True

    def test_demo_context_pack_inputs(self):
        result = run_ariadne_e2e_demo()
        inputs = result["context_pack_inputs"]
        assert inputs["pr_id"] == DEMO_PR_ID
        assert len(inputs["source_contracts"]) > 0
        assert len(inputs["relevant_anchors"]) > 0
        assert len(inputs["allowed_paths"]) > 0
        assert len(inputs["forbidden_paths"]) > 0
        assert len(inputs["cache_key_refs"]) > 0
        assert len(inputs["known_risks"]) > 0

    def test_demo_context_pack(self):
        result = run_ariadne_e2e_demo()
        pack = result["context_pack"]
        assert pack["context_pack_id"] == f"cp-{DEMO_PR_ID}-{DEMO_REPO_ID}"
        assert pack["task"] == DEMO_TASK_GOAL
        assert pack["domain"] == DEMO_DOMAIN
        assert len(pack["invariants"]) > 0
        assert len(pack["risks"]) > 0
        assert len(pack["anchors"]) > 0

    def test_demo_conductor_dry_run(self):
        result = run_ariadne_e2e_demo()
        summary = result["conductor_dry_run_summary"]
        assert summary["dry_run"] == "conductor"
        assert summary["run_status"] == "completed"
        assert summary["step_count"] == 2
        assert summary["context_pack_summary"]["present"] is True

    def test_demo_deterministic(self):
        result1 = run_ariadne_e2e_demo()
        result2 = run_ariadne_e2e_demo()
        assert result1 == result2

    def test_demo_json_serializable(self):
        result = run_ariadne_e2e_demo()
        dumped = json.dumps(result, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == result

    def test_demo_inputs_validate(self):
        inputs = build_context_pack_inputs(
            pr_id=DEMO_PR_ID,
            task_goal=DEMO_TASK_GOAL,
        )
        validate_context_pack_inputs(inputs)

    def test_demo_pack_validates(self):
        inputs = build_context_pack_inputs(
            pr_id=DEMO_PR_ID,
            task_goal=DEMO_TASK_GOAL,
        )
        pack = compile_context_pack(
            context_pack_inputs=inputs,
            repo_id=DEMO_REPO_ID,
            purpose_id=DEMO_PURPOSE_ID,
            domain=DEMO_DOMAIN,
            risk_level=DEMO_RISK_LEVEL,
            base_sha=DEMO_BASE_SHA,
            index_version=DEMO_INDEX_VERSION,
        )
        validate_context_pack(pack)

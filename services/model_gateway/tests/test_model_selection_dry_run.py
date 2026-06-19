"""Tests for the Model Selection Dry-Run Decision Record."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from model_gateway.model_selection_dry_run import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_VALID_ARGS = [
    "--role", "reviewer",
    "--task-type", "verification",
    "--risk-level", "high",
    "--retrieval-stress", "high",
    "--aggregation-stress", "high",
    "--graph-reasoning-stress", "medium",
    "--long-code-stress", "high",
    "--icl-sensitivity", "medium",
    "--recommended-model", "provider:coder-model",
    "--reviewer-model", "provider:reviewer-model",
]


def _run(*extra: str) -> tuple[int, dict]:
    """Run main with VALID_ARGS + extra, return (exit_code, parsed_json)."""
    import io
    import sys

    old_out = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exit_code = main([*_VALID_ARGS, *extra])
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_out

    try:
        parsed = json.loads(output) if output else {}
    except json.JSONDecodeError:
        parsed = {"raw_output": output}

    return exit_code, parsed


# ---------------------------------------------------------------------------
# Valid output shape
# ---------------------------------------------------------------------------


class TestValidOutput:
    def test_exit_code_zero(self):
        code, _ = _run()
        assert code == 0

    def test_output_is_json(self):
        _, data = _run()
        # If data has 'raw_output', JSON parsing failed
        assert "raw_output" not in data, f"JSON parse failed: {data.get('raw_output')}"

    def test_has_required_fields(self):
        _, data = _run()
        for field in ("role", "task_type", "risk_level", "context_stress",
                       "recommended_model", "reviewer_model", "reason",
                       "selection_rules_applied"):
            assert field in data, f"Missing field: {field}"

    def test_context_stress_has_all_fields(self):
        _, data = _run()
        cs = data.get("context_stress", {})
        for field in ("retrieval_stress", "aggregation_stress",
                       "graph_reasoning_stress", "long_code_stress",
                       "icl_sensitivity"):
            assert field in cs, f"Missing context_stress field: {field}"

    def test_reason_present(self):
        _, data = _run()
        assert isinstance(data["reason"], str)
        assert len(data["reason"]) > 0

    def test_selection_rules_present(self):
        _, data = _run()
        assert isinstance(data["selection_rules_applied"], list)
        assert len(data["selection_rules_applied"]) > 0


# ---------------------------------------------------------------------------
# Invalid role
# ---------------------------------------------------------------------------


class TestInvalidRole:
    def test_invalid_role_rejected(self):
        code, data = _run("--role", "invalid_role")
        assert code == 1
        assert "error" in data
        assert "Invalid role" in data["error"]


# ---------------------------------------------------------------------------
# Invalid risk level
# ---------------------------------------------------------------------------


class TestInvalidRiskLevel:
    def test_invalid_risk_level_rejected(self):
        code, data = _run("--risk-level", "extreme")
        assert code == 1
        assert "error" in data
        assert "Invalid risk_level" in data["error"]


# ---------------------------------------------------------------------------
# Invalid context stress
# ---------------------------------------------------------------------------


class TestInvalidContextStress:
    def test_invalid_stress_rejected(self):
        code, data = _run("--retrieval-stress", "extreme")
        assert code == 1
        assert "error" in data

    def test_missing_context_stress_field_rejected(self):
        """Verify that argparse exits with non-zero for missing required args."""
        import subprocess, sys, os
        # Run a subprocess where one required arg is missing
        env = os.environ.copy()
        env["PYTHONPATH"] = "services/model_gateway/src"
        args = [sys.executable, "-m", "model_gateway.model_selection_dry_run",
                "--role", "architect",
                "--task-type", "analysis",
                "--risk-level", "low",
                "--retrieval-stress", "low",
                "--aggregation-stress", "low",
                "--graph-reasoning-stress", "low",
                "--long-code-stress", "low",
                # Missing --icl-sensitivity
                "--recommended-model", "p:m",
                "--reviewer-model", "p:m",
        ]
        result = subprocess.run(args, capture_output=True, text=True, timeout=10, env=env)
        # argparse missing required arg should exit non-zero (typically 2)
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage:" in result.stderr.lower()

    def test_context_stress_values_are_in_output(self):
        _, data = _run()
        cs = data["context_stress"]
        for v in cs.values():
            assert v in ("low", "medium", "high"), f"Unexpected stress value: {v}"


# ---------------------------------------------------------------------------
# High/critical risk — reviewer independence
# ---------------------------------------------------------------------------


class TestReviewerIndependence:
    def test_high_risk_rejects_same_model(self):
        code, data = _run("--recommended-model", "provider:model-x",
                          "--reviewer-model", "provider:model-x")
        assert code == 1
        assert "error" in data
        assert "must differ" in data["error"]

    def test_critical_risk_rejects_same_model(self):
        code, data = _run("--risk-level", "critical",
                          "--recommended-model", "provider:model-x",
                          "--reviewer-model", "provider:model-x")
        assert code == 1
        assert "error" in data

    def test_low_risk_allows_same_model(self):
        code, data = _run("--risk-level", "low",
                          "--recommended-model", "provider:same",
                          "--reviewer-model", "provider:same")
        assert code == 0

    def test_medium_risk_allows_same_model(self):
        code, data = _run("--risk-level", "medium",
                          "--recommended-model", "provider:same",
                          "--reviewer-model", "provider:same")
        assert code == 0


# ---------------------------------------------------------------------------
# selection_rules_applied content
# ---------------------------------------------------------------------------


class TestSelectionRulesContent:
    def test_high_risk_includes_independence_rule(self):
        _, data = _run()
        rules = data["selection_rules_applied"]
        assert "reviewer_model_differs_from_coder_on_high_risk" in rules

    def test_high_risk_includes_strong_for_purpose(self):
        _, data = _run()
        rules = data["selection_rules_applied"]
        assert "strong_for_purpose_cheap_for_execution" in rules

    def test_low_risk_includes_not_strongest(self):
        _, data = _run("--risk-level", "low",
                       "--retrieval-stress", "low",
                       "--aggregation-stress", "low",
                       "--graph-reasoning-stress", "low",
                       "--long-code-stress", "low",
                       "--icl-sensitivity", "low")
        rules = data["selection_rules_applied"]
        assert "model_not_strongest_by_default" in rules

    def test_includes_substrate_rule(self):
        _, data = _run()
        rules = data["selection_rules_applied"]
        assert "substrate_beats_model_loyalty" in rules

    def test_includes_no_hardcoded_vendor_rule(self):
        _, data = _run()
        rules = data["selection_rules_applied"]
        assert "no_hardcoded_model_vendor_assignments" in rules

    def test_high_context_stress_includes_subtask_rule(self):
        _, data = _run()
        rules = data["selection_rules_applied"]
        assert "long_context_profiled_by_subtask" in rules


# ---------------------------------------------------------------------------
# No side-effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_forbidden_imports(self):
        """Verify that the module does not import forbidden modules."""
        import inspect
        from model_gateway.model_selection_dry_run import main as m

        source = inspect.getsource(m)
        assert "subprocess" not in source
        assert "git " not in source or "git_" in source
        assert "docker" not in source
        assert "run_record" not in source.lower()
        assert ".ariadne" not in source
        assert "runner" not in source.lower()

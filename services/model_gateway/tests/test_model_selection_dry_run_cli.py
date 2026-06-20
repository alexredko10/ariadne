"""Tests for the Model Selection Dry-Run CLI smoke path (PR 0034).

Tests the simplified CLI arguments (--context-stress, --failure-mode, etc.)
against the existing deterministic dry-run decision logic.
"""

from __future__ import annotations

import json

import pytest

from model_gateway.model_selection_dry_run import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(*extra: str) -> tuple[int, dict]:
    """Run main with minimal valid simplified args + extra, return (code, parsed)."""
    base = [
        "--role", "coder",
        "--task-type", "long-context-code-review",
        "--context-stress", "high",
        "--failure-mode", "hallucinated-diff",
        "--cost-sensitivity", "medium",
        "--verification", "required",
    ]
    import io, sys
    old_out = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exit_code = main([*base, *extra])
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_out
    try:
        parsed = json.loads(output) if output else {}
    except json.JSONDecodeError:
        parsed = {"raw_output": output}
    return exit_code, parsed


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_exit_code_zero(self):
        code, _ = _run()
        assert code == 0

    def test_output_is_json(self):
        _, data = _run()
        assert "raw_output" not in data, f"JSON parse failed: {data.get('raw_output')}"

    def test_has_required_fields(self):
        _, data = _run()
        for field in ("role", "task_type", "risk_level", "context_stress",
                       "recommended_model", "reviewer_model", "reason",
                       "selection_rules_applied", "cost_sensitivity", "verification"):
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

    def test_failure_mode_present(self):
        _, data = _run()
        assert data.get("failure_mode") == "hallucinated-diff"

    def test_risk_level_derived_from_verification(self):
        _, data = _run()
        assert data["risk_level"] == "critical"  # verification=required maps to critical


# ---------------------------------------------------------------------------
# Invalid / missing args
# ---------------------------------------------------------------------------


class TestInvalidArgs:
    def test_invalid_role_rejected(self):
        code, data = _run("--role", "invalid_role")
        assert code == 1
        assert "error" in data

    def test_invalid_context_stress_rejected(self):
        code, data = _run("--context-stress", "extreme")
        assert code != 0

    def test_missing_required_arg_via_subprocess(self):
        import subprocess, sys, os
        env = os.environ.copy()
        env["PYTHONPATH"] = "services/model_gateway/src"
        args = [sys.executable, "-m", "model_gateway.model_selection_dry_run",
                "--role", "coder", "--task-type", "test"]
        # Missing --context-stress
        result = subprocess.run(args, capture_output=True, text=True, timeout=10, env=env)
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Deterministic output
# ---------------------------------------------------------------------------


class TestDeterministic:
    def test_same_input_same_output(self):
        base = ["--role", "coder", "--task-type", "x", "--context-stress", "low",
                "--cost-sensitivity", "low", "--verification", "none"]
        import io, sys
        def run():
            old_out = sys.stdout
            sys.stdout = io.StringIO()
            try:
                code = main(base)
                out = sys.stdout.getvalue()
            finally:
                sys.stdout = old_out
            return code, json.loads(out) if out else {}
        c1, d1 = run()
        c2, d2 = run()
        assert c1 == c2 == 0
        assert d1 == d2


# ---------------------------------------------------------------------------
# No side-effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_forbidden_imports(self):
        """Verify that the module does not import forbidden modules."""
        import inspect
        source = inspect.getsource(main)
        assert "subprocess" not in source
        assert "docker" not in source
        assert "run_record" not in source.lower()
        assert ".ariadne" not in source

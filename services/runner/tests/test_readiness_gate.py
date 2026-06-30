"""Tests for the pre-0100 readiness / stabilization gate."""

from __future__ import annotations

import json
from unittest.mock import patch

from runner.readiness_gate import run_readiness_gate


# ---------------------------------------------------------------------------
# Report shape
# ---------------------------------------------------------------------------


class TestReadinessReportShape:
    def test_returns_dict(self):
        report = run_readiness_gate()
        assert isinstance(report, dict)

    def test_has_timestamp(self):
        report = run_readiness_gate()
        assert "timestamp" in report

    def test_has_ok_field(self):
        report = run_readiness_gate()
        assert "ok" in report
        assert isinstance(report["ok"], bool)

    def test_has_release_readiness(self):
        report = run_readiness_gate()
        assert report["release_readiness"] in ("ready", "blocked", "needs_review")

    def test_has_gates_list(self):
        report = run_readiness_gate()
        assert "gates" in report
        assert isinstance(report["gates"], list)
        assert len(report["gates"]) == 9

    def test_has_summary(self):
        report = run_readiness_gate()
        assert "summary" in report
        for key in ("total_gates", "passed", "blockers", "warnings"):
            assert key in report["summary"]

    def test_has_assessment(self):
        report = run_readiness_gate()
        assert "assessment" in report
        assert isinstance(report["assessment"], str)
        assert len(report["assessment"]) > 10

    def test_each_gate_has_id(self):
        report = run_readiness_gate()
        for g in report["gates"]:
            assert "gate_id" in g

    def test_each_gate_has_passed(self):
        report = run_readiness_gate()
        for g in report["gates"]:
            assert "passed" in g
            assert isinstance(g["passed"], bool)


# ---------------------------------------------------------------------------
# All 9 gates present
# ---------------------------------------------------------------------------


class TestAllGatesPresent:
    def test_all_nine_gate_ids_present(self):
        report = run_readiness_gate()
        gate_ids = {g["gate_id"] for g in report["gates"]}
        expected = {
            "audit_invariants",
            "smoke_gate",
            "dual_gate_preserved",
            "review_boundary_preserved",
            "artifacts_preserved",
            "subprocess_isolation",
            "source_string_safety",
            "no_frontend_drift",
            "acceptance_checklist",
        }
        assert gate_ids == expected, f"Missing gates: {expected - gate_ids}"


# ---------------------------------------------------------------------------
# All gates pass (integration test with real modules)
# ---------------------------------------------------------------------------


class TestAllGatesPass:
    def test_all_nine_gates_pass(self):
        report = run_readiness_gate()
        assert report["ok"] is True, f"Gates failed: {[g['gate_id'] for g in report['gates'] if not g['passed']]}"

    def test_release_readiness_ready(self):
        report = run_readiness_gate()
        assert report["release_readiness"] == "ready"

    def test_summary_counts_match(self):
        report = run_readiness_gate()
        assert report["summary"]["passed"] == report["summary"]["total_gates"]
        assert report["summary"]["blockers"] == 0

    def test_summary_passed_equals_nine(self):
        report = run_readiness_gate()
        assert report["summary"]["passed"] == 9


# ---------------------------------------------------------------------------
# Smoke failure blocks readiness
# ---------------------------------------------------------------------------


class TestSmokeFailure:
    def test_release_readiness_blocked(self):
        with patch("runner.readiness_gate.run_execution_smoke") as mock_smoke:
            mock_smoke.return_value = {
                "ok": False,
                "checks": [{"check_id": "noop_completed", "passed": False}],
                "summary": {"total": 1, "passed": 0, "failed": 1},
            }
            report = run_readiness_gate()
            assert report["ok"] is False
            assert report["release_readiness"] == "blocked"

    def test_smoke_gate_check_fails(self):
        with patch("runner.readiness_gate.run_execution_smoke") as mock_smoke:
            mock_smoke.return_value = {
                "ok": False,
                "checks": [{"check_id": "noop_completed", "passed": False}],
                "summary": {"total": 1, "passed": 0, "failed": 1},
            }
            report = run_readiness_gate()
            smoke_gate = next(g for g in report["gates"] if g["gate_id"] == "smoke_gate")
            assert smoke_gate["passed"] is False


# ---------------------------------------------------------------------------
# Audit blocker blocks readiness
# ---------------------------------------------------------------------------


class TestAuditBlocker:
    def test_release_readiness_blocked(self):
        with patch("runner.readiness_gate.run_execution_substrate_audit") as mock_audit:
            mock_audit.return_value = {
                "checks": [],
                "summary": {"total": 1, "passed": 0, "failed": 1, "warning_count": 0, "blocker_count": 1},
            }
            report = run_readiness_gate()
            assert report["ok"] is False
            assert report["release_readiness"] == "blocked"

    def test_audit_invariants_check_fails(self):
        with patch("runner.readiness_gate.run_execution_substrate_audit") as mock_audit:
            mock_audit.return_value = {
                "checks": [],
                "summary": {"total": 1, "passed": 0, "failed": 1, "warning_count": 0, "blocker_count": 1},
            }
            report = run_readiness_gate()
            audit_gate = next(g for g in report["gates"] if g["gate_id"] == "audit_invariants")
            assert audit_gate["passed"] is False


# ---------------------------------------------------------------------------
# Deterministic
# ---------------------------------------------------------------------------


class TestDeterministic:
    def test_two_calls_identical(self):
        r1 = run_readiness_gate()
        r2 = run_readiness_gate()
        assert r1["ok"] == r2["ok"]
        assert r1["release_readiness"] == r2["release_readiness"]
        assert len(r1["gates"]) == len(r2["gates"])
        for g1, g2 in zip(r1["gates"], r2["gates"]):
            assert g1["gate_id"] == g2["gate_id"]
            assert g1["passed"] == g2["passed"]


# ---------------------------------------------------------------------------
# JSON serializable
# ---------------------------------------------------------------------------


class TestJsonSerializable:
    def test_report_json_serializable(self):
        report = run_readiness_gate()
        dumped = json.dumps(report, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded["ok"] == report["ok"]
        assert len(loaded["gates"]) == len(report["gates"])


# ---------------------------------------------------------------------------
# Assessment strings appropriate
# ---------------------------------------------------------------------------


class TestAssessment:
    def test_ready_has_positive_assessment(self):
        report = run_readiness_gate()
        assert report["ok"] is True
        assert "proceed" in report["assessment"].lower()

    def test_blocked_has_negative_assessment(self):
        with patch("runner.readiness_gate.run_execution_smoke") as mock_smoke:
            mock_smoke.return_value = {
                "ok": False,
                "checks": [{"check_id": "noop_completed", "passed": False}],
                "summary": {"total": 1, "passed": 0, "failed": 1},
            }
            report = run_readiness_gate()
            assert "blocked" in report["assessment"].lower()

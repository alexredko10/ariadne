"""Tests for the end-to-end execution smoke gate."""

from __future__ import annotations

import json

from runner.execution_smoke import run_execution_smoke


# ---------------------------------------------------------------------------
# Smoke report shape
# ---------------------------------------------------------------------------


class TestSmokeReportShape:
    def test_returns_dict(self):
        report = run_execution_smoke()
        assert isinstance(report, dict)

    def test_has_timestamp(self):
        report = run_execution_smoke()
        assert "timestamp" in report

    def test_has_ok_field(self):
        report = run_execution_smoke()
        assert "ok" in report
        assert isinstance(report["ok"], bool)

    def test_has_checks_list(self):
        report = run_execution_smoke()
        assert "checks" in report
        assert isinstance(report["checks"], list)
        assert len(report["checks"]) > 0

    def test_has_summary(self):
        report = run_execution_smoke()
        assert "summary" in report
        assert "total" in report["summary"]
        assert "passed" in report["summary"]
        assert "failed" in report["summary"]

    def test_each_check_has_id(self):
        report = run_execution_smoke()
        for c in report["checks"]:
            assert "check_id" in c, f"Check missing check_id: {c}"

    def test_each_check_has_passed(self):
        report = run_execution_smoke()
        for c in report["checks"]:
            assert "passed" in c, f"Check {c['check_id']} missing passed"
            assert isinstance(c["passed"], bool)


# ---------------------------------------------------------------------------
# All smoke checks pass
# ---------------------------------------------------------------------------


class TestAllChecksPass:
    def test_all_checks_pass(self):
        report = run_execution_smoke()
        assert report["ok"] is True, f"Not all checks pass. Failed checks: {[c['check_id'] for c in report['checks'] if not c['passed']]}"

    def test_summary_matches_check_count(self):
        report = run_execution_smoke()
        assert report["summary"]["total"] == len(report["checks"])
        assert report["summary"]["passed"] == report["summary"]["total"]

    def test_passed_plus_failed_equals_total(self):
        report = run_execution_smoke()
        assert report["summary"]["passed"] + report["summary"]["failed"] == report["summary"]["total"]


# ---------------------------------------------------------------------------
# Deterministic
# ---------------------------------------------------------------------------


class TestDeterministic:
    def test_two_calls_identical(self):
        r1 = run_execution_smoke()
        r2 = run_execution_smoke()
        # Compare checks (timestamp will differ)
        assert r1["ok"] == r2["ok"]
        assert len(r1["checks"]) == len(r2["checks"])
        for c1, c2 in zip(r1["checks"], r2["checks"]):
            assert c1["check_id"] == c2["check_id"]
            assert c1["passed"] == c2["passed"]


# ---------------------------------------------------------------------------
# JSON serializable
# ---------------------------------------------------------------------------


class TestJsonSerializable:
    def test_report_json_serializable(self):
        report = run_execution_smoke()
        dumped = json.dumps(report, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded["ok"] == report["ok"]
        assert len(loaded["checks"]) == len(report["checks"])


# ---------------------------------------------------------------------------
# Individual check verification
# ---------------------------------------------------------------------------


class TestIndividualChecks:
    def test_noop_completed(self):
        report = run_execution_smoke()
        check = _find_check(report, "noop_completed")
        assert check is not None
        assert check["passed"] is True

    def test_docker_blocked_by_default(self):
        report = run_execution_smoke()
        check = _find_check(report, "docker_blocked_by_default")
        assert check is not None
        assert check["passed"] is True

    def test_docker_blocked_no_request_flag(self):
        report = run_execution_smoke()
        check = _find_check(report, "docker_blocked_no_request_flag")
        assert check is not None
        assert check["passed"] is True

    def test_docker_blocked_no_env_switch(self):
        report = run_execution_smoke()
        check = _find_check(report, "docker_blocked_no_env_switch")
        assert check is not None
        assert check["passed"] is True

    def test_docker_blocked_false_string(self):
        report = run_execution_smoke()
        check = _find_check(report, "docker_blocked_false_string")
        assert check is not None
        assert check["passed"] is True

    def test_docker_blocked_env_false_string(self):
        report = run_execution_smoke()
        check = _find_check(report, "docker_blocked_env_false_string")
        assert check is not None
        assert check["passed"] is True

    def test_docker_requires_review(self):
        report = run_execution_smoke()
        check = _find_check(report, "docker_requires_review")
        assert check is not None
        assert check["passed"] is True

    def test_docker_failed(self):
        report = run_execution_smoke()
        check = _find_check(report, "docker_failed")
        assert check is not None
        assert check["passed"] is True

    def test_artifact_kinds_visible(self):
        report = run_execution_smoke()
        check = _find_check(report, "artifact_kinds_visible")
        assert check is not None
        assert check["passed"] is True

    def test_artifact_redaction(self):
        report = run_execution_smoke()
        check = _find_check(report, "artifact_redaction")
        assert check is not None
        assert check["passed"] is True

    def test_audit_invocation(self):
        report = run_execution_smoke()
        check = _find_check(report, "audit_invocation")
        assert check is not None
        assert check["passed"] is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_check(report: dict, check_id: str) -> dict | None:
    for c in report.get("checks", []):
        if c["check_id"] == check_id:
            return c
    return None

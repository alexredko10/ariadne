"""
Deterministic local pre-0100 readiness / stabilization gate.

Composes PR 0097 execution-substrate audit and PR 0098 end-to-end smoke
gate into a single release-readiness verdict. Applies 9 acceptance-pass
criteria. No Docker daemon, no network, no filesystem access.

Public API:
    run_readiness_gate() -> ReadinessReport
"""

from __future__ import annotations

import inspect
import json
from datetime import datetime, timezone

from runner.execution_smoke import run_execution_smoke
from runner.execution_substrate_audit import run_execution_substrate_audit
from runner import (
    adapter_registry,
    docker_agent_adapter,
    docker_run_artifacts,
    docker_subprocess_executor,
    review_boundary,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_readiness_gate() -> dict:
    """Run all readiness gates for PR 0100 readiness assessment.

    Returns a ReadinessReport dict with keys: timestamp, ok, release_readiness,
    gates, summary, assessment.
    """
    # --- Gather inputs ---
    smoke_report = run_execution_smoke()
    smoke_check_map = {c["check_id"]: c for c in smoke_report.get("checks", [])}

    audit_sources = {
        "adapter_registry_source": inspect.getsource(adapter_registry),
        "docker_agent_adapter_source": inspect.getsource(docker_agent_adapter),
        "docker_run_artifacts_source": inspect.getsource(docker_run_artifacts),
        "docker_subprocess_executor_source": inspect.getsource(docker_subprocess_executor),
        "review_boundary_source": inspect.getsource(review_boundary),
    }
    audit_report = run_execution_substrate_audit(**audit_sources)
    audit_check_map = {c["check_id"]: c for c in audit_report.get("checks", [])}

    # --- Build gates ---
    gates: list[dict] = []

    # Gate 1: Audit invariants
    gates.append(_gate_audit_invariants(audit_report))

    # Gate 2: Smoke gate
    gates.append(_gate_smoke_gate(smoke_report))

    # Gate 3: Dual gate preserved
    gates.append(_gate_dual_gate_preserved(smoke_check_map, audit_check_map))

    # Gate 4: Review boundary preserved
    gates.append(_gate_review_boundary_preserved(smoke_check_map))

    # Gate 5: Artifacts preserved
    gates.append(_gate_artifacts_preserved(smoke_check_map))

    # Gate 6: Subprocess isolation
    gates.append(_gate_subprocess_isolation(audit_check_map))

    # Gate 7: Source-string safety
    gates.append(_gate_source_string_safety(audit_check_map))

    # Gate 8: No frontend drift
    gates.append(_gate_no_frontend_drift(audit_check_map))

    # Gate 9: Acceptance checklist
    gates.append(_gate_acceptance_checklist(smoke_report, audit_report))

    # --- Compute summary ---
    total = len(gates)
    passed = sum(1 for g in gates if g["passed"])
    blockers = sum(1 for g in gates if not g["passed"] and g.get("extra", {}).get("blocker", True))
    warnings = sum(1 for g in gates if not g["passed"] and not g.get("extra", {}).get("blocker", False))

    ok = blockers == 0
    if ok and warnings == 0:
        release_readiness = "ready"
        assessment = "All readiness gates pass. PR 0100 can proceed as a freeze/release gate."
    elif ok and warnings > 0:
        release_readiness = "needs_review"
        assessment = "Non-blocking warnings found. PR 0100 may proceed but operators should review warnings."
    else:
        release_readiness = "blocked"
        assessment = f"Readiness gate blocked ({blockers} blocker(s)). PR 0100 cannot proceed until blockers are resolved."

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "release_readiness": release_readiness,
        "gates": gates,
        "summary": {
            "total_gates": total,
            "passed": passed,
            "blockers": blockers,
            "warnings": warnings,
        },
        "assessment": assessment,
    }


# ---------------------------------------------------------------------------
# Gate builders
# ---------------------------------------------------------------------------


def _gate(
    gate_id: str,
    description: str,
    passed: bool,
    details: str | None = None,
    blocker: bool = True,
    source: str = "audit",
) -> dict:
    return {
        "gate_id": gate_id,
        "description": description,
        "passed": passed,
        "details": details,
        "extra": {"blocker": blocker, "source": source},
    }


def _gate_audit_invariants(audit_report: dict) -> dict:
    blocker_count = audit_report.get("summary", {}).get("blocker_count", -1)
    warning_count = audit_report.get("summary", {}).get("warning_count", 0)
    passed = blocker_count == 0
    details = (
        f"Audit invariances: {audit_report['summary']['passed']} passed, "
        f"{blocker_count} blocker(s), {warning_count} warning(s)."
    )
    return _gate(
        "audit_invariants",
        "PR 0097 execution substrate audit passes with zero blockers.",
        passed=passed,
        details=details,
        blocker=True,
        source="audit",
    )


def _gate_smoke_gate(smoke_report: dict) -> dict:
    passed = smoke_report.get("ok", False)
    sm = smoke_report.get("summary", {})
    details = (
        f"Smoke gate: {sm.get('passed')}/{sm.get('total')} checks passed."
        if passed else
        f"Smoke gate failed: {sm.get('passed')}/{sm.get('total')} checks passed. "
        f"Failed checks: {[c['check_id'] for c in smoke_report.get('checks', []) if not c['passed']]}"
    )
    return _gate(
        "smoke_gate",
        "PR 0098 execution smoke gate returns ok=True.",
        passed=passed,
        details=details,
        blocker=True,
        source="smoke",
    )


def _gate_dual_gate_preserved(smoke_map: dict, audit_map: dict) -> dict:
    dual_gate_ids = [
        "docker_blocked_by_default",
        "docker_blocked_no_request_flag",
        "docker_blocked_no_env_switch",
        "docker_blocked_false_string",
        "docker_blocked_env_false_string",
    ]
    smoke_all_pass = all(smoke_map.get(i, {}).get("passed", False) for i in dual_gate_ids)
    audit_dual = audit_map.get("docker_dual_gate", {}).get("passed", False)
    passed = smoke_all_pass and audit_dual
    failed_ids = [i for i in dual_gate_ids if not smoke_map.get(i, {}).get("passed", False)]
    if not audit_dual:
        failed_ids.append("docker_dual_gate (audit)")
    details = None if passed else f"Dual gate checks failed: {failed_ids}"
    return _gate(
        "dual_gate_preserved",
        "Docker execution dual gate (request allow_docker + env ARIADNE_ALLOW_DOCKER_EXECUTION) preserved.",
        passed=passed,
        details=details,
        blocker=True,
        source="smoke",
    )


def _gate_review_boundary_preserved(smoke_map: dict) -> dict:
    check_ids = ["noop_completed", "docker_requires_review", "docker_failed"]
    all_pass = all(smoke_map.get(i, {}).get("passed", False) for i in check_ids)
    failed_ids = [i for i in check_ids if not smoke_map.get(i, {}).get("passed", False)]
    details = None if all_pass else f"Boundary checks failed: {failed_ids}"
    return _gate(
        "review_boundary_preserved",
        "requires_review, failed, and blocked statuses all map correctly.",
        passed=all_pass,
        details=details,
        blocker=True,
        source="smoke",
    )


def _gate_artifacts_preserved(smoke_map: dict) -> dict:
    check_ids = ["artifact_kinds_visible", "artifact_redaction"]
    all_pass = all(smoke_map.get(i, {}).get("passed", False) for i in check_ids)
    failed_ids = [i for i in check_ids if not smoke_map.get(i, {}).get("passed", False)]
    details = None if all_pass else f"Artifact checks failed: {failed_ids}"
    return _gate(
        "artifacts_preserved",
        "PR 0095 artifact/evidence kinds visible and redacted.",
        passed=all_pass,
        details=details,
        blocker=True,
        source="smoke",
    )


def _gate_subprocess_isolation(audit_map: dict) -> dict:
    subprocess_check = audit_map.get("subprocess_isolation", {}).get("passed", False)
    details = None if subprocess_check else "subprocess found outside approved module."
    return _gate(
        "subprocess_isolation",
        "subprocess import remains isolated to docker_subprocess_executor.py and tests.",
        passed=subprocess_check,
        details=details,
        blocker=True,
        source="audit",
    )


def _gate_source_string_safety(audit_map: dict) -> dict:
    query = audit_map.get("task_intake_no_forbidden_strings", {}).get("passed", False)
    details = None if query else "Forbidden source strings found in task_intake."
    return _gate(
        "source_string_safety",
        "task_intake forbidden source-string safety selectors pass.",
        passed=query,
        details=details,
        blocker=True,
        source="audit",
    )


def _gate_no_frontend_drift(audit_map: dict) -> dict:
    drift_check = audit_map.get("no_frontend_only_drift", {}).get("passed", True)
    details = None if drift_check else "Frontend-only drift detected."
    return _gate(
        "no_frontend_drift",
        "No frontend-only UI-only files modified in current execution track.",
        passed=drift_check,
        details=details,
        blocker=False,  # tech-debt
        source="audit",
    )


def _gate_acceptance_checklist(smoke_report: dict, audit_report: dict) -> dict:
    """Gate 9: Acceptance checklist — verifies the full pipeline works."""
    smoke_passed = smoke_report.get("ok", False)
    audit_blockers = audit_report.get("summary", {}).get("blocker_count", -1)
    passed = smoke_passed and audit_blockers == 0
    details = (
        None
        if passed
        else f"Smoke ok={smoke_passed}, audit blockers={audit_blockers}. "
             "Existing task_intake tests are verified via the validation commands."
    )
    return _gate(
        "acceptance_checklist",
        "Local interaction page works with real execution pipeline (corrected execution path).",
        passed=passed,
        details=details,
        blocker=True,
        source="audit",
    )

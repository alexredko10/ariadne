"""
Deterministic local end-to-end execution smoke gate.

Composes task intake handoff -> runner dispatch -> docker-agent safety ->
artifacts/evidence -> review boundary -> PR 0097 audit into one deterministic
smoke path. No Docker daemon, no network, no filesystem access, no persistence.

Public API:
    run_execution_smoke() -> SmokeReport
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from unittest.mock import patch

from runner.execution_substrate_audit import run_execution_substrate_audit
from runner.local_harness import run_local_execution_harness


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXPECTED_ARTIFACT_KINDS = (
    "docker_stdout",
    "docker_stderr",
    "docker_execution_metadata",
    "docker_command_metadata",
)

_EXPECTED_EVIDENCE_KINDS = (
    "execution_log",
    "execution_note",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_execution_smoke() -> dict:
    """Run all execution smoke checks.

    Returns a SmokeReport dict with keys: timestamp, ok, checks, summary.
    """
    checks: list[dict] = []

    # --- Path 1: Local/noop execution produces completed ---
    checks.append(_check_noop_completed())

    # --- Path 2: Docker-agent blocked by default ---
    checks.append(_check_docker_blocked_by_default())

    # --- Path 3: Docker-agent blocked when only env is set ---
    checks.append(_check_docker_blocked_no_request_flag())

    # --- Path 4: Docker-agent blocked when only request flag is set ---
    checks.append(_check_docker_blocked_no_env_switch())

    # --- Path 5: Docker-agent blocked when string "false" is passed ---
    checks.append(_check_docker_blocked_false_string())

    # --- Path 6: Docker-agent blocked when env false string ---
    checks.append(_check_docker_blocked_env_false_string())

    # --- Path 7: Docker-agent requires_review via fake executor ---
    checks.append(_check_docker_requires_review())

    # --- Path 8: Docker-agent failed via fake executor ---
    checks.append(_check_docker_failed())

    # --- Path 9: PR 0095 artifact kinds visible (from Path 7 result) ---
    checks.append(_check_artifact_kinds_visible())

    # --- Path 10: PR 0095 artifact redaction (from Path 7 result) ---
    checks.append(_check_artifact_redaction())

    # --- Path 11: PR 0097 audit can be invoked ---
    checks.append(_check_audit_invocation())

    # --- Summary ---
    total = len(checks)
    passed = sum(1 for c in checks if c["passed"])
    ok = passed == total

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "checks": checks,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
    }


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_BASE_REQUEST = {
    "execution_request_id": "smoke-er-001",
    "run_id": "smoke-run-001",
    "task_intake_id": "smoke-ti-001",
    "context_preview_id": "smoke-cp-001",
    "execution_mode": "execute",
    "inputs": {"task_goal": "smoke test"},
    "constraints": [],
}


def _noop_request() -> dict:
    req = dict(_BASE_REQUEST)
    req["requested_adapter"] = "noop-v1"
    req["execution_mode"] = "dry_run"
    return req


def _docker_request(**overrides: object) -> dict:
    req = dict(_BASE_REQUEST)
    req["requested_adapter"] = "docker-agent-v1"
    req.update(overrides)
    return req


def _fake_successful_executor(cmd: dict) -> dict:
    return {
        "exit_code": 0,
        "stdout": "Smoke test execution completed successfully.",
        "stderr": "",
        "success": True,
    }


def _fake_failing_executor(cmd: dict) -> dict:
    return {
        "exit_code": 1,
        "stdout": "",
        "stderr": "Smoke test execution failed: container error.",
        "success": False,
    }


# ---------------------------------------------------------------------------
# Check helpers (cached state for Path 7 -> Path 9/10)
# ---------------------------------------------------------------------------

_requires_review_result: dict | None = None


def _get_requires_review_result() -> dict:
    global _requires_review_result
    if _requires_review_result is not None:
        return _requires_review_result
    with patch("runner.adapter_registry.run_docker_subprocess", _fake_successful_executor):
        with patch.dict(os.environ, {"ARIADNE_ALLOW_DOCKER_EXECUTION": "1"}, clear=False):
            req = _docker_request(allow_docker=True)
            _requires_review_result = run_local_execution_harness(req)
    return _requires_review_result


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def _check_noop_completed() -> dict:
    check_id = "noop_completed"
    desc = "Local/noop execution produces runtime_status=completed and decision=completed."
    harness_result = run_local_execution_harness(_noop_request())
    rt = harness_result.get("runtime_status", "")
    boundary = harness_result.get("review_boundary", {})
    decision = boundary.get("decision", "")
    execution_result = harness_result.get("execution_result", {})
    er_status = execution_result.get("status", "")
    ok = rt == "completed" and decision == "completed" and er_status == "completed"
    return {
        "check_id": check_id,
        "description": desc,
        "passed": ok,
        "details": None if ok else f"runtime_status={rt!r}, decision={decision!r}, status={er_status!r}",
    }


def _check_docker_blocked_by_default() -> dict:
    check_id = "docker_blocked_by_default"
    desc = "Docker-agent without allow_docker and without env returns status=blocked."
    req = _docker_request()
    harness_result = run_local_execution_harness(req)
    rt = harness_result.get("runtime_status", "")
    boundary = harness_result.get("review_boundary", {})
    decision = boundary.get("decision", "")
    ok = rt == "blocked" and decision == "blocked"
    return {
        "check_id": check_id,
        "description": desc,
        "passed": ok,
        "details": None if ok else f"runtime_status={rt!r}, decision={decision!r}",
    }


def _check_docker_blocked_no_request_flag() -> dict:
    check_id = "docker_blocked_no_request_flag"
    desc = "Docker-agent with env set but no allow_docker returns status=blocked (both gates required)."
    with patch.dict(os.environ, {"ARIADNE_ALLOW_DOCKER_EXECUTION": "1"}, clear=False):
        req = _docker_request()
        harness_result = run_local_execution_harness(req)
    rt = harness_result.get("runtime_status", "")
    boundary = harness_result.get("review_boundary", {})
    decision = boundary.get("decision", "")
    ok = rt == "blocked" and decision == "blocked"
    return {
        "check_id": check_id,
        "description": desc,
        "passed": ok,
        "details": None if ok else f"runtime_status={rt!r}, decision={decision!r}",
    }


def _check_docker_blocked_no_env_switch() -> dict:
    check_id = "docker_blocked_no_env_switch"
    desc = "Docker-agent with allow_docker=True but no env returns status=blocked."
    req = _docker_request(allow_docker=True)
    harness_result = run_local_execution_harness(req)
    rt = harness_result.get("runtime_status", "")
    boundary = harness_result.get("review_boundary", {})
    decision = boundary.get("decision", "")
    ok = rt == "blocked" and decision == "blocked"
    return {
        "check_id": check_id,
        "description": desc,
        "passed": ok,
        "details": None if ok else f"runtime_status={rt!r}, decision={decision!r}",
    }


def _check_docker_blocked_false_string() -> dict:
    check_id = "docker_blocked_false_string"
    desc = "Docker-agent with allow_docker='false' (string) returns status=blocked."
    req = _docker_request(allow_docker="false")
    harness_result = run_local_execution_harness(req)
    rt = harness_result.get("runtime_status", "")
    ok = rt == "blocked"
    return {
        "check_id": check_id,
        "description": desc,
        "passed": ok,
        "details": None if ok else f"runtime_status={rt!r}",
    }


def _check_docker_blocked_env_false_string() -> dict:
    check_id = "docker_blocked_env_false_string"
    desc = "Docker-agent with allow_docker=True but env=FALSE returns status=blocked."
    with patch.dict(os.environ, {"ARIADNE_ALLOW_DOCKER_EXECUTION": "FALSE"}, clear=False):
        req = _docker_request(allow_docker=True)
        harness_result = run_local_execution_harness(req)
    rt = harness_result.get("runtime_status", "")
    ok = rt == "blocked"
    return {
        "check_id": check_id,
        "description": desc,
        "passed": ok,
        "details": None if ok else f"runtime_status={rt!r}",
    }


def _check_docker_requires_review() -> dict:
    check_id = "docker_requires_review"
    desc = "Docker-agent with both gates open and successful fake executor returns status=requires_review."
    with patch("runner.adapter_registry.run_docker_subprocess", _fake_successful_executor):
        with patch.dict(os.environ, {"ARIADNE_ALLOW_DOCKER_EXECUTION": "1"}, clear=False):
            req = _docker_request(allow_docker=True)
            harness_result = run_local_execution_harness(req)
    rt = harness_result.get("runtime_status", "")
    boundary = harness_result.get("review_boundary", {})
    decision = boundary.get("decision", "")
    ok = rt == "requires_review" and decision == "requires_review"
    return {
        "check_id": check_id,
        "description": desc,
        "passed": ok,
        "details": None if ok else f"runtime_status={rt!r}, decision={decision!r}",
    }


def _check_docker_failed() -> dict:
    check_id = "docker_failed"
    desc = "Docker-agent with both gates open and failing fake executor returns status=failed."
    with patch("runner.adapter_registry.run_docker_subprocess", _fake_failing_executor):
        with patch.dict(os.environ, {"ARIADNE_ALLOW_DOCKER_EXECUTION": "1"}, clear=False):
            req = _docker_request(allow_docker=True)
            harness_result = run_local_execution_harness(req)
    rt = harness_result.get("runtime_status", "")
    boundary = harness_result.get("review_boundary", {})
    decision = boundary.get("decision", "")
    ok = rt == "failed" and decision == "failed"
    return {
        "check_id": check_id,
        "description": desc,
        "passed": ok,
        "details": None if ok else f"runtime_status={rt!r}, decision={decision!r}",
    }


def _check_artifact_kinds_visible() -> dict:
    check_id = "artifact_kinds_visible"
    desc = "PR 0095 artifact kinds docker_stdout/stderr/execution_metadata/command_metadata present."
    result = _get_requires_review_result()
    execution_result = result.get("execution_result", {})
    artifacts = execution_result.get("artifacts", [])
    kinds = [a.get("kind", "") for a in artifacts]
    missing = [k for k in _EXPECTED_ARTIFACT_KINDS if k not in kinds]
    ok = not missing
    return {
        "check_id": check_id,
        "description": desc,
        "passed": ok,
        "details": None if ok else f"Missing artifact kinds: {missing!r}",
    }


def _check_artifact_redaction() -> dict:
    check_id = "artifact_redaction"
    desc = "Environment variable values redacted in artifacts; only key names and count."
    result = _get_requires_review_result()
    execution_result = result.get("execution_result", {})
    artifacts = execution_result.get("artifacts", [])
    ok = True
    details = ""
    for a in artifacts:
        content = a.get("content", "")
        if isinstance(content, dict):
            env_keys = content.get("environment_keys", None)
            if env_keys is not None:
                # Verify environment_keys is a list of safe key names
                if not isinstance(env_keys, list):
                    ok = False
                    details += f"environment_keys is not a list in {a['kind']}; "
                else:
                    # Check that no values leaked into env keys
                    for k in env_keys:
                        if "=" in k or k.startswith("ARIADNE_TASK_GOAL"):
                            ok = False
                            details += f"suspicious env key {k!r} in {a['kind']}; "
    if ok and not details:
        details = None
    return {
        "check_id": check_id,
        "description": desc,
        "passed": ok,
        "details": details,
    }


def _check_audit_invocation() -> dict:
    check_id = "audit_invocation"
    desc = "PR 0097 run_execution_substrate_audit can be invoked and returns without error."
    import inspect
    from runner import docker_agent_adapter, docker_run_artifacts, docker_subprocess_executor, adapter_registry, review_boundary
    sources = {
        "docker_agent_adapter_source": inspect.getsource(docker_agent_adapter),
        "docker_run_artifacts_source": inspect.getsource(docker_run_artifacts),
        "docker_subprocess_executor_source": inspect.getsource(docker_subprocess_executor),
        "adapter_registry_source": inspect.getsource(adapter_registry),
        "review_boundary_source": inspect.getsource(review_boundary),
    }
    report = run_execution_substrate_audit(**sources)
    blocker_count = report.get("summary", {}).get("blocker_count", -1)
    ok = blocker_count == 0
    return {
        "check_id": check_id,
        "description": desc,
        "passed": ok,
        "details": None if ok else f"Audit produced {blocker_count} blocker(s).",
    }

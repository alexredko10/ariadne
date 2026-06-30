"""
Deterministic Docker artifact and evidence builder for the Docker agent adapter.

Produces structured artifact and evidence entries from a Docker execution result
and its command metadata. No filesystem writes, no subprocess calls, no state.

Artifacts and evidence follow the existing RunnerExecutionResult shapes.
"""

from __future__ import annotations

import json
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_CONTENT_LENGTH = 10_000


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_docker_artifacts(
    executor_result: dict,
    command_metadata: dict,
    execution_request_id: str,
) -> list[dict]:
    """Build deterministic artifact entries from executor result and command metadata.

    Parameters
    ----------
    executor_result
        Dict with keys: exit_code, stdout, stderr, success.
    command_metadata
        Dict produced by ``build_docker_agent_command()``.
    execution_request_id
        The execution request ID used to derive deterministic artifact IDs.

    Returns
    -------
    list[dict]
        List of artifact entries conforming to RunnerExecutionResult.artifacts[].
    """
    req_id = execution_request_id
    _exit_code = executor_result.get("exit_code", -1)
    success = executor_result.get("success", False)
    status = "completed" if success else ("blocked" if _exit_code == -1 and not success and not executor_result.get("stdout") else "failed")

    artifacts: list[dict] = []

    # Blocked path: only command metadata artifact
    if status == "blocked" and _exit_code == -1 and not executor_result.get("stdout") and not executor_result.get("stderr"):
        artifacts.append(_build_command_meta_artifact(req_id, command_metadata, executed=False))
        return artifacts

    # Completed/failed path: all four artifacts
    stdout_content = _bound_content(executor_result.get("stdout", ""))
    stderr_content = _bound_content(executor_result.get("stderr", ""))

    artifacts.append({
        "artifact_id": f"{req_id}-docker-stdout",
        "kind": "docker_stdout",
        "reference": "in-memory",
        "summary": "Docker execution stdout.",
        "content": stdout_content,
    })
    artifacts.append({
        "artifact_id": f"{req_id}-docker-stderr",
        "kind": "docker_stderr",
        "reference": "in-memory",
        "summary": "Docker execution stderr.",
        "content": stderr_content,
    })
    artifacts.append(_build_exec_metadata_artifact(req_id, executor_result, command_metadata))
    artifacts.append(_build_command_meta_artifact(req_id, command_metadata, executed=True))

    return artifacts


def build_docker_evidence(
    executor_result: dict,
    command_metadata: dict,
    execution_request_id: str,
) -> list[dict]:
    """Build deterministic evidence entries from executor result and command metadata.

    Parameters
    ----------
    executor_result
        Dict with keys: exit_code, stdout, stderr, success.
    command_metadata
        Dict produced by ``build_docker_agent_command()``.
    execution_request_id
        The execution request ID used to derive deterministic evidence IDs.

    Returns
    -------
    list[dict]
        List of evidence entries conforming to RunnerExecutionResult.evidence[].
    """
    req_id = execution_request_id
    _exit_code = executor_result.get("exit_code", -1)
    success = executor_result.get("success", False)

    evidence: list[dict] = []

    # Blocked path: execution_note with skipped status
    if _exit_code == -1 and not success and not executor_result.get("stdout") and not executor_result.get("stderr"):
        evidence.append({
            "evidence_id": f"{req_id}-docker-blocked-evidence",
            "evidence_kind": "execution_note",
            "summary": "Docker execution requires explicit opt-in (allow_docker=True and ARIADNE_ALLOW_DOCKER_EXECUTION). No Docker command was executed.",
            "status": "skipped",
            "details": None,
        })
        return evidence

    # Completed/failed path
    evidence_status = "passed" if success else "failed"
    evidence.append({
        "evidence_id": f"{req_id}-docker-evidence",
        "evidence_kind": "execution_log",
        "summary": (
            "Docker agent execution completed via executor."
            if success
            else "Docker agent execution failed via executor."
        ),
        "status": evidence_status,
        "details": None if success else {"stderr": executor_result.get("stderr", "")},
    })

    return evidence


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _bound_content(content: str) -> str:
    """Truncate content if it exceeds the maximum allowed length."""
    if len(content) > _MAX_CONTENT_LENGTH:
        return content[:_MAX_CONTENT_LENGTH] + "\n... [truncated at 10000 characters]"
    return content


def _build_exec_metadata_artifact(
    req_id: str,
    executor_result: dict,
    command_metadata: dict,
) -> dict:
    """Build the docker_execution_metadata artifact with redacted env/volumes."""
    safe_env_keys = _safe_environment_key_list(command_metadata.get("environment", {}))
    return {
        "artifact_id": f"{req_id}-docker-exec-metadata",
        "kind": "docker_execution_metadata",
        "reference": "in-memory",
        "summary": "Docker execution metadata (exit code, container config).",
        "content": {
            "exit_code": executor_result.get("exit_code", -1),
            "success": executor_result.get("success", False),
            "container_image": command_metadata.get("container_image", ""),
            "network_mode": command_metadata.get("network_mode", ""),
            "execution_mode": command_metadata.get("execution_mode", ""),
            "timeout_seconds": command_metadata.get("timeout_seconds", 300),
            "environment_keys": safe_env_keys,
            "env_var_count": len(safe_env_keys),
        },
    }


def _build_command_meta_artifact(
    req_id: str,
    command_metadata: dict,
    executed: bool,
) -> dict:
    """Build the docker_command_metadata artifact with normalized volume/redacted env info."""
    volumes = command_metadata.get("volumes", {})
    volume_summaries: list[str] = []
    for host_path, vol_cfg in volumes.items():
        container_path = vol_cfg.get("bind", "")
        volume_summaries.append(container_path if container_path else "(unnamed)")
    volume_summary = ", ".join(volume_summaries) if volume_summaries else "none"

    env_keys = list(command_metadata.get("environment", {}).keys())

    return {
        "artifact_id": f"{req_id}-docker-command-meta",
        "kind": "docker_command_metadata",
        "reference": "in-memory",
        "summary": "Docker command metadata%s." % (" (executed)" if executed else " (not executed)"),
        "content": {
            "container_image": command_metadata.get("container_image", ""),
            "workdir": command_metadata.get("workdir", ""),
            "network_mode": command_metadata.get("network_mode", ""),
            "memory_limit": command_metadata.get("memory_limit", ""),
            "cpu_count": command_metadata.get("cpu_count", 0),
            "volume_count": len(volumes),
            "volume_mounts": volume_summary,
            "env_var_count": len(env_keys),
            "env_var_keys": env_keys,
            "timeout_seconds": command_metadata.get("timeout_seconds", 300),
        },
    }


def _safe_environment_key_list(environment: dict) -> list[str]:
    """Return a list of safe environment key names only (no values).

    Filters out keys that may contain sensitive or task-specific data.
    Includes only standard operational keys.
    """
    safe_keys = {"ARIADNE_RUN_ID", "ARIADNE_REQUEST_ID", "ARIADNE_MODE"}
    result: list[str] = []
    for key in environment:
        if key in safe_keys:
            result.append(key)
    return sorted(result)

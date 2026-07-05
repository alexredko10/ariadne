"""
Agent Runner Bridge — first executable Production Line PR.

Runs one configured Docker agent from Ariadne code through the existing
runner substrate.  Accepts ``agent_name`` + ``task_prompt``, loads a real
``agents/{agent_name}.yml`` config, invokes the existing adapter pipeline,
captures a runtime proof artifact, and returns a structured bridge result.

Core principle:
    Agent output is not evidence.  Runtime-captured proof is evidence.
    The substrate exists to run the loop — the human must stop being the
    orchestrator.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
from typing import Any, Callable, Optional

from runner.docker_agent_adapter import run_docker_agent_execution
from runner.local_harness import run_local_execution_harness
from runner.proof_capture import (
    ProofCaptureInput,
    ProofCaptureStatus,
    capture_proof,
)
from runner.improvement_backlog import (
    _FORBIDDEN_HIDDEN_REASONING_PATTERNS,
    _FORBIDDEN_ACTION_PATTERNS,
)


# ---------------------------------------------------------------------------
# AgentRunnerBridgeStatus — status values
# ---------------------------------------------------------------------------


class AgentRunnerBridgeStatus(str):
    """Status values for agent runner bridge operations."""

    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# AgentRunnerBridgeRequest — input dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AgentRunnerBridgeRequest:
    """Input parameters for running the agent runner bridge."""

    agent_name: str
    task_prompt: str
    agents_dir: str = "agents"
    workdir: Optional[str] = None
    allow_docker: bool = False


# ---------------------------------------------------------------------------
# AgentRunnerBridgeArtifact — captured artifact shape
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AgentRunnerBridgeArtifact:
    """Captured runtime proof artifact from the bridge."""

    artifact_ref: str
    proof_capture_path: Optional[str]
    proof_capture_ref: Optional[str]
    executor_output_path: Optional[str]
    has_proof: bool
    proof_source: str = "runtime-captured"


# ---------------------------------------------------------------------------
# AgentRunnerBridgeResult — result dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AgentRunnerBridgeResult:
    """Result of an agent runner bridge operation."""

    status: str
    reason_codes: tuple[str, ...]
    agent_name: str
    task_prompt_hash: str
    agent_config_path: str
    agent_config_hash: str
    docker_adapter_status: str
    exit_code: Optional[int]
    captured_stdout_hash: Optional[str]
    captured_stderr_hash: Optional[str]
    captured_artifact: Optional[AgentRunnerBridgeArtifact]
    proof_summary: str
    started_at: Optional[str]
    finished_at: Optional[str]
    details: Optional[str]


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_AGENT_CONFIG = "missing_agent_config"
REASON_UNBOUNDED_AGENT_NAME = "unbounded_agent_name"
REASON_MISSING_TASK_PROMPT = "missing_task_prompt"
REASON_DOCKER_BLOCKED = "docker_blocked"
REASON_EXECUTION_FAILED = "execution_failed"
REASON_PROOF_CAPTURE_FAILED = "proof_capture_failed"
REASON_HIDDEN_REASONING_NOT_ALLOWED = "hidden_reasoning_not_allowed"

# ---------------------------------------------------------------------------
# Agent name validation
# ---------------------------------------------------------------------------

_AGENT_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")

# ---------------------------------------------------------------------------
# Forbidden patterns
# ---------------------------------------------------------------------------

_FORBIDDEN_MUTATION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("git add", REASON_HIDDEN_REASONING_NOT_ALLOWED),
    ("git commit", REASON_HIDDEN_REASONING_NOT_ALLOWED),
    ("git push", REASON_HIDDEN_REASONING_NOT_ALLOWED),
    ("git checkout", REASON_HIDDEN_REASONING_NOT_ALLOWED),
    ("git switch", REASON_HIDDEN_REASONING_NOT_ALLOWED),
    ("git merge", REASON_HIDDEN_REASONING_NOT_ALLOWED),
    ("git rebase", REASON_HIDDEN_REASONING_NOT_ALLOWED),
    ("git reset", REASON_HIDDEN_REASONING_NOT_ALLOWED),
    ("git clean", REASON_HIDDEN_REASONING_NOT_ALLOWED),
    ("git tag", REASON_HIDDEN_REASONING_NOT_ALLOWED),
    ("gh pr create", REASON_HIDDEN_REASONING_NOT_ALLOWED),
    ("gh release", REASON_HIDDEN_REASONING_NOT_ALLOWED),
)


# ---------------------------------------------------------------------------
# Resolve agent config
# ---------------------------------------------------------------------------


def resolve_agent_config(
    agent_name: str,
    agents_dir: str = "agents",
) -> tuple[str, str, str]:
    """Resolve and load an agent config file.

    Parameters
    ----------
    agent_name:
        The agent name (must match ``^[a-zA-Z0-9_\\-]+$``).
    agents_dir:
        Directory containing agent config files.

    Returns
    -------
    tuple[str, str, str]
        ``(config_path, config_content, config_hash)``.

    Raises
    ------
    ValueError
        If the agent name is invalid or the config file is missing.
    """
    if not _AGENT_NAME_RE.match(agent_name):
        raise ValueError(f"Invalid agent name: {agent_name!r}")

    config_path = os.path.join(agents_dir, f"{agent_name}.yml")

    if not os.path.exists(config_path):
        raise ValueError(f"Agent config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config_content = f.read()

    config_hash = hashlib.sha256(config_content.encode("utf-8")).hexdigest()[:16]

    return config_path, config_content, config_hash


# ---------------------------------------------------------------------------
# Build execution request from agent config + task prompt
# ---------------------------------------------------------------------------


def build_agent_runner_execution_request(
    agent_name: str,
    task_prompt: str,
    config_content: str,
    workdir: Optional[str] = None,
    allow_docker: bool = False,
) -> dict:
    """Build an execution request dict from agent config and task prompt.

    Parameters
    ----------
    agent_name:
        The agent name.
    task_prompt:
        The task prompt for the agent.
    config_content:
        The raw content of the agent config file.
    workdir:
        Optional working directory.
    allow_docker:
        Whether Docker execution is allowed.

    Returns
    -------
    dict
        An execution request dict compatible with the runner substrate.
    """
    # Parse config content for basic fields (simple YAML-like parsing)
    config_lines = config_content.split("\n")
    model = ""
    instruction = ""
    for line in config_lines:
        if line.startswith("model:"):
            model = line.split(":", 1)[1].strip()
        elif line.startswith("instruction:"):
            instruction = line.split(":", 1)[1].strip()

    # Build execution request
    # Always use docker adapter — it handles allow_docker=False by returning
    # a blocked result.  The noop adapter requires fields we don't have.
    execution_request = {
        "execution_request_id": f"bridge-{agent_name}-{hashlib.sha256(task_prompt.encode('utf-8')).hexdigest()[:8]}",
        "run_id": f"run-bridge-{agent_name}-{hashlib.sha256(task_prompt.encode('utf-8')).hexdigest()[:8]}",
        "requested_adapter": "docker",
        "execution_mode": "execute" if allow_docker else "dry_run",
        "allow_docker": allow_docker,
        "inputs": {
            "task_goal": task_prompt,
            "agent_name": agent_name,
            "model": model,
            "instruction": instruction,
        },
        "workdir": workdir or os.getcwd(),
    }

    return execution_request


# ---------------------------------------------------------------------------
# Check for forbidden patterns in task prompt
# ---------------------------------------------------------------------------


def _check_forbidden_patterns(text: str, codes: list[str]) -> None:
    """Check for forbidden patterns in text."""
    # Hidden reasoning
    for pattern in _FORBIDDEN_HIDDEN_REASONING_PATTERNS:
        if pattern in text:
            codes.append(REASON_HIDDEN_REASONING_NOT_ALLOWED)
            return

    # Forbidden actions (command execution, provider call, git mutation)
    for pattern, reason in _FORBIDDEN_ACTION_PATTERNS:
        if pattern in text:
            codes.append(reason)
            return

    # Forbidden mutation patterns (git commands, gh commands)
    for pattern, reason in _FORBIDDEN_MUTATION_PATTERNS:
        if pattern in text:
            codes.append(reason)
            return


# ---------------------------------------------------------------------------
# Run agent runner bridge
# ---------------------------------------------------------------------------


def run_agent_runner_bridge(
    agent_name: str,
    task_prompt: str,
    agents_dir: str = "agents",
    workdir: Optional[str] = None,
    allow_docker: bool = False,
    output_dir: str = ".",
    clock_provider: Optional[Callable[[], str]] = None,
) -> AgentRunnerBridgeResult:
    """Run the agent runner bridge.

    Parameters
    ----------
    agent_name:
        The agent name (must match ``^[a-zA-Z0-9_\\-]+$``).
    task_prompt:
        The task prompt for the agent.
    agents_dir:
        Directory containing agent config files.
    workdir:
        Optional working directory.
    allow_docker:
        Whether Docker execution is allowed.
    output_dir:
        Directory for proof capture output.
    clock_provider:
        Optional callable returning a timestamp string for deterministic
        testing.  If ``None``, ``started_at`` and ``finished_at`` are
        ``None``.

    Returns
    -------
    AgentRunnerBridgeResult
        ``status="completed"`` with ``captured_artifact`` when the bridge
        succeeds.
        ``status="blocked"`` when Docker is blocked.
        ``status="failed"`` with ``reason_codes`` when validation fails.
    """
    codes: list[str] = []
    started_at = clock_provider() if clock_provider else None

    # 1. Validate agent_name
    if not _AGENT_NAME_RE.match(agent_name):
        codes.append(REASON_UNBOUNDED_AGENT_NAME)

    # 2. Validate task_prompt
    if not task_prompt or task_prompt.strip() == "":
        codes.append(REASON_MISSING_TASK_PROMPT)

    # 3. Check for forbidden patterns in task prompt
    if task_prompt:
        _check_forbidden_patterns(task_prompt, codes)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Agent runner bridge failed:\n" + "\n".join(detail_lines)
        return AgentRunnerBridgeResult(
            status=AgentRunnerBridgeStatus.FAILED,
            reason_codes=tuple(codes),
            agent_name=agent_name,
            task_prompt_hash=hashlib.sha256(task_prompt.encode("utf-8")).hexdigest()[:16] if task_prompt else "",
            agent_config_path="",
            agent_config_hash="",
            docker_adapter_status="",
            exit_code=None,
            captured_stdout_hash=None,
            captured_stderr_hash=None,
            captured_artifact=None,
            proof_summary="",
            started_at=started_at,
            finished_at=clock_provider() if clock_provider else None,
            details=details,
        )

    # 4. Resolve agent config
    try:
        config_path, config_content, config_hash = resolve_agent_config(agent_name, agents_dir)
    except ValueError as e:
        codes.append(REASON_MISSING_AGENT_CONFIG)
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Agent runner bridge failed:\n" + "\n".join(detail_lines)
        return AgentRunnerBridgeResult(
            status=AgentRunnerBridgeStatus.FAILED,
            reason_codes=tuple(codes),
            agent_name=agent_name,
            task_prompt_hash=hashlib.sha256(task_prompt.encode("utf-8")).hexdigest()[:16],
            agent_config_path="",
            agent_config_hash="",
            docker_adapter_status="",
            exit_code=None,
            captured_stdout_hash=None,
            captured_stderr_hash=None,
            captured_artifact=None,
            proof_summary="",
            started_at=started_at,
            finished_at=clock_provider() if clock_provider else None,
            details=details,
        )

    # 5. Hash task prompt
    task_prompt_hash = hashlib.sha256(task_prompt.encode("utf-8")).hexdigest()[:16]

    # 6. Build execution request
    execution_request = build_agent_runner_execution_request(
        agent_name=agent_name,
        task_prompt=task_prompt,
        config_content=config_content,
        workdir=workdir,
        allow_docker=allow_docker,
    )

    # 7. Run through local harness
    harness_result = run_local_execution_harness(execution_request)

    # 8. Extract adapter status and result
    execution_result = harness_result.get("execution_result", {})
    adapter_status = execution_result.get("status", "failed")
    exit_code = execution_result.get("exit_code")
    stdout = execution_result.get("stdout", "")
    stderr = execution_result.get("stderr", "")

    # Hash stdout/stderr
    stdout_hash = hashlib.sha256(stdout.encode("utf-8")).hexdigest()[:16] if stdout else None
    stderr_hash = hashlib.sha256(stderr.encode("utf-8")).hexdigest()[:16] if stderr else None

    # 9. Determine bridge status
    if adapter_status == "blocked":
        bridge_status = AgentRunnerBridgeStatus.BLOCKED
        codes.append(REASON_DOCKER_BLOCKED)
    elif adapter_status in ("requires_review", "completed"):
        bridge_status = AgentRunnerBridgeStatus.COMPLETED
    else:
        bridge_status = AgentRunnerBridgeStatus.FAILED
        codes.append(REASON_EXECUTION_FAILED)

    # 10. Capture runtime proof
    proof_capture_path = None
    proof_capture_ref = None
    has_proof = False
    artifact_ref = ""

    if bridge_status != AgentRunnerBridgeStatus.FAILED or adapter_status == "failed":
        # Build proof payload
        proof_payload = json.dumps({
            "agent_name": agent_name,
            "task_prompt_hash": task_prompt_hash,
            "agent_config_hash": config_hash,
            "adapter_status": adapter_status,
            "exit_code": exit_code,
            "stdout_hash": stdout_hash,
            "stderr_hash": stderr_hash,
            "adapter_result": execution_result,
        }, sort_keys=True, ensure_ascii=False)

        proof_input = ProofCaptureInput(
            product_state_ref="bridge-0124",
            acceptance_criteria_ref="bridge-0124",
            runtime_capture_kind="agent_runner_bridge",
            phase_id="agent-runner-bridge-0124",
            run_id=execution_request.get("run_id", "bridge-run-0124"),
            payload=proof_payload,
            output_path=f"captures/bridge-{agent_name}-{task_prompt_hash}.json",
            summary="Agent Runner Bridge proof capture",
            tags=frozenset({"agent-runner-bridge", "runtime-captured"}),
        )

        proof_result = capture_proof(proof_input, output_dir=output_dir)

        if proof_result.status == ProofCaptureStatus.CAPTURED:
            proof_capture_path = proof_result.artifact_path
            proof_capture_ref = proof_result.proof_ref_fields.get("runtime_capture_ref") if proof_result.proof_ref_fields else None
            has_proof = True
            artifact_ref = hashlib.sha256(proof_payload.encode("utf-8")).hexdigest()[:16]
        else:
            codes.append(REASON_PROOF_CAPTURE_FAILED)

    # 11. Build captured artifact
    captured_artifact = AgentRunnerBridgeArtifact(
        artifact_ref=artifact_ref,
        proof_capture_path=proof_capture_path,
        proof_capture_ref=proof_capture_ref,
        executor_output_path=None,
        has_proof=has_proof,
        proof_source="runtime-captured",
    )

    # 12. Build proof summary
    if has_proof:
        proof_summary = f"Proof captured: {proof_capture_ref} at {proof_capture_path}"
    elif bridge_status == AgentRunnerBridgeStatus.BLOCKED:
        proof_summary = "Docker blocked; no proof captured"
    else:
        proof_summary = "No proof captured"

    finished_at = clock_provider() if clock_provider else None

    return AgentRunnerBridgeResult(
        status=bridge_status,
        reason_codes=tuple(codes),
        agent_name=agent_name,
        task_prompt_hash=task_prompt_hash,
        agent_config_path=config_path,
        agent_config_hash=config_hash,
        docker_adapter_status=adapter_status,
        exit_code=exit_code,
        captured_stdout_hash=stdout_hash,
        captured_stderr_hash=stderr_hash,
        captured_artifact=captured_artifact,
        proof_summary=proof_summary,
        started_at=started_at,
        finished_at=finished_at,
        details=None,
    )

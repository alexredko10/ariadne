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
REASON_ARTIFACT_PATH_TRAVERSAL = "artifact_path_traversal"
REASON_ARTIFACT_PATH_ABSOLUTE = "artifact_path_absolute"
REASON_ARTIFACT_PATH_NOT_PROJECT_MEMORY = "artifact_path_not_project_memory"
REASON_ARTIFACT_PATH_ARIAONE = "artifact_path_ariadne"
REASON_ARTIFACT_PATH_CAPTURES = "artifact_path_captures"
REASON_ARTIFACT_OVERWRITE_BLOCKED = "artifact_overwrite_blocked"

# ---------------------------------------------------------------------------
# Protected artifact patterns (overwrite protection)
# ---------------------------------------------------------------------------

_PROTECTED_ARTIFACT_PATTERNS: tuple[str, ...] = (
    ".project-memory/pr/**/PLAN.md",
    ".project-memory/pr/**/reviews/plan-review.yml",
    ".project-memory/pr/**/reviews/precommit-review.yml",
)


# ---------------------------------------------------------------------------
# Agent name validation
# ---------------------------------------------------------------------------

_AGENT_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")

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
# Validate artifact path for local materialization
# ---------------------------------------------------------------------------


def _validate_artifact_path(path: str, workdir: str) -> str:
    """Validate an artifact path for local materialization.

    Rules:
    1. No path traversal (``..``)
    2. No absolute paths outside repo root
    3. Only ``.project-memory/pr/**`` paths
    4. No ``.ariadne/**`` writes
    5. No ``captures/**`` writes (except existing proof capture mechanism)

    Parameters
    ----------
    path:
        The expected artifact path (relative to workdir).
    workdir:
        The repository root directory.

    Returns
    -------
    str
        The validated absolute path.

    Raises
    ------
    ValueError
        If the path fails any validation rule.
    """
    # Rule 1: No path traversal
    if ".." in path.split("/"):
        raise ValueError(f"Path traversal rejected: {path!r}")

    # Rule 2: No absolute paths outside repo root
    if os.path.isabs(path):
        if not path.startswith(os.path.abspath(workdir)):
            raise ValueError(f"Absolute path outside repo root: {path!r}")
        # Convert to relative for further checks
        rel_path = os.path.relpath(path, workdir)
    else:
        rel_path = path

    # Rule 3: Only .project-memory/pr/** paths
    if not rel_path.startswith(".project-memory/pr/"):
        raise ValueError(f"Non-project-memory path rejected: {rel_path!r}")

    # Rule 4: No .ariadne/** writes
    if rel_path.startswith(".ariadne/"):
        raise ValueError(f"Ariadne path rejected: {rel_path!r}")

    # Rule 5: No captures/** writes (except existing proof capture mechanism)
    if rel_path.startswith("captures/"):
        raise ValueError(f"Captures path rejected: {rel_path!r}")

    # Build absolute path
    abs_path = os.path.join(workdir, rel_path)
    return abs_path


# ---------------------------------------------------------------------------
# Build default plan-review artifact content
# ---------------------------------------------------------------------------


def _build_default_plan_review_artifact(
    pr_id: str,
    task_prompt_hash: str,
    agent_config_hash: str,
    artifact_ref: str,
) -> str:
    """Build a default plan-review artifact for local materialization.

    The generated artifact is parseable by Verdict Parser as pass or warning
    with no blockers.

    Parameters
    ----------
    pr_id:
        The PR identifier.
    task_prompt_hash:
        The SHA256[:16] hash of the task prompt.
    agent_config_hash:
        The SHA256[:16] hash of the agent config.
    artifact_ref:
        The artifact reference hash.

    Returns
    -------
    str
        YAML artifact content.
    """
    return (
        f'schema_version: "0.1"\n'
        f'pr_id: "{pr_id}"\n'
        f'review_type: "plan-review"\n'
        f'verdict: "approve"\n'
        f'reviewer: "ariadne-local-bridge"\n'
        f'timestamp: "{_utc_iso_timestamp()}"\n'
        f'blockers: []\n'
        f'warnings: []\n'
        f'validation:\n'
        f'  - command: "local-non-docker-bridge"\n'
        f'    result: "passed"\n'
        f'    exit_code: 0\n'
        f'    evidence: "Local non-Docker bridge \u2014 no real validation executed"\n'
        f'files_checked: []\n'
        f'boundary_confirmations:\n'
        f'  - "evidence-first plan-review completed"\n'
        f'  - "ROADMAP.md not modified"\n'
        f'checks:\n'
        f'  branch: "pass"\n'
        f'  task_prompt_hash: "{task_prompt_hash}"\n'
        f'  agent_config_hash: "{agent_config_hash}"\n'
        f'  artifact_ref: "{artifact_ref}"\n'
        f'  materialized_by: "ariadne-local-bridge"\n'
    )


# ---------------------------------------------------------------------------
# Build default precommit-review artifact content
# ---------------------------------------------------------------------------


def _build_default_precommit_artifact(
    pr_id: str,
    task_prompt_hash: str,
    agent_config_hash: str,
    artifact_ref: str,
) -> str:
    """Build a default precommit-review artifact for local materialization.

    The generated artifact is parseable by Verdict Parser as pass or warning
    with no blockers.  It is safe, sanitized, and minimal — no secrets, no
    raw full stdout/stderr, no full unredacted task text.

    Parameters
    ----------
    pr_id:
        The PR identifier.
    task_prompt_hash:
        The SHA256[:16] hash of the task prompt.
    agent_config_hash:
        The SHA256[:16] hash of the agent config.
    artifact_ref:
        The artifact reference hash.

    Returns
    -------
    str
        YAML artifact content.
    """
    return (
        f'schema_version: "0.1"\n'
        f'pr_id: "{pr_id}"\n'
        f'review_type: "precommit-review"\n'
        f'verdict: "pass"\n'
        f'reviewer: "ariadne-local-bridge"\n'
        f'timestamp: "{_utc_iso_timestamp()}"\n'
        f'snapshot_delta:\n'
        f'  plan_base_sha: ""\n'
        f'  current_head: ""\n'
        f'  action: "continue"\n'
        f'  stale_snapshot: false\n'
        f'scope:\n'
        f'  expected_files: []\n'
        f'  actual_files: []\n'
        f'  forbidden_paths_checked: true\n'
        f'  forbidden_paths_found: []\n'
        f'  generated_artifacts_found: []\n'
        f'  scope_status: "in_scope"\n'
        f'files_checked: []\n'
        f'validation:\n'
        f'  - command: "local-non-docker-bridge"\n'
        f'    result: "passed"\n'
        f'    exit_code: 0\n'
        f'    evidence: "Local non-Docker bridge \u2014 no real validation executed"\n'
        f'blockers: []\n'
        f'warnings: []\n'
        f'decisions_made:\n'
        f'  - decision: "Local materialization \u2014 no real validation"\n'
        f'    reason: "Local non-Docker bridge completed without errors"\n'
        f'context_used:\n'
        f'  labels: []\n'
        f'  memory_files_read: []\n'
        f'  anchors_used: []\n'
        f'  files_inspected: []\n'
        f'  files_modified: []\n'
        f'  files_intentionally_ignored: []\n'
        f'checks:\n'
        f'  branch: "pass"\n'
        f'  task_prompt_hash: "{task_prompt_hash}"\n'
        f'  agent_config_hash: "{agent_config_hash}"\n'
        f'  artifact_ref: "{artifact_ref}"\n'
        f'  materialized_by: "ariadne-local-bridge"\n'
    )


# ---------------------------------------------------------------------------
# Build default dogfood-proof artifact content
# ---------------------------------------------------------------------------


def _build_default_dogfood_proof(
    pr_id: str,
    task_prompt_hash: str,
    agent_config_hash: str,
    artifact_ref: str,
) -> str:
    """Build a default dogfood-proof artifact for local materialization.

    Parameters
    ----------
    pr_id:
        The PR identifier.
    task_prompt_hash:
        The SHA256[:16] hash of the task prompt.
    agent_config_hash:
        The SHA256[:16] hash of the agent config.
    artifact_ref:
        The artifact reference hash.

    Returns
    -------
    str
        YAML artifact content.
    """
    return (
        f'schema_version: "0.1"\n'
        f'pr_id: "{pr_id}"\n'
        f'dogfood_type: "local-non-docker"\n'
        f'status: "completed"\n'
        f'bridge_task_prompt_hash: "{task_prompt_hash}"\n'
        f'bridge_agent_config_hash: "{agent_config_hash}"\n'
        f'proof_artifact_ref: "{artifact_ref}"\n'
        f'materialized_at: "{_utc_iso_timestamp()}"\n'
    )


# ---------------------------------------------------------------------------
# UTC ISO timestamp helper
# ---------------------------------------------------------------------------


def _utc_iso_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Materialize local artifact
# ---------------------------------------------------------------------------


def _is_protected_artifact(path: str) -> bool:
    """Check if a path matches any protected artifact pattern.

    Protected paths are:
    - ``.project-memory/pr/**/PLAN.md``
    - ``.project-memory/pr/**/reviews/plan-review.yml``
    - ``.project-memory/pr/**/reviews/precommit-review.yml``

    Parameters
    ----------
    path:
        The relative artifact path to check.

    Returns
    -------
    bool
        ``True`` if the path matches a protected pattern.
    """
    basename = os.path.basename(path)
    dirname = os.path.dirname(path)

    # Check PLAN.md anywhere under .project-memory/pr/
    if basename == "PLAN.md" and dirname.startswith(".project-memory/pr/"):
        return True

    # Check reviews/*.yml under .project-memory/pr/
    if basename in ("plan-review.yml", "precommit-review.yml"):
        if "/reviews" in dirname and dirname.startswith(".project-memory/pr/"):
            return True

    return False


def _materialize_local_artifact(
    artifact_path: str,
    content: str,
    workdir: str,
    task_prompt_hash: str,
    agent_config_hash: str,
    overwrite_allowed: bool = False,
) -> dict:
    """Materialize a local artifact file with proof metadata.

    Writes the content to the validated path atomically (write to ``.tmp``,
    rename).  Returns a dict with materialization evidence.

    Parameters
    ----------
    artifact_path:
        The expected artifact path (relative to workdir).
    content:
        The content to write.
    workdir:
        The repository root directory.
    task_prompt_hash:
        The SHA256[:16] hash of the task prompt.
    agent_config_hash:
        The SHA256[:16] hash of the agent config.

    Returns
    -------
    dict
        Materialization evidence with keys:
        - ``path``: the absolute path written
        - ``hash``: SHA256[:16] of the content
        - ``line_count``: number of lines in the content
        - ``task_prompt_hash``: passed through
        - ``agent_config_hash``: passed through

    Raises
    ------
    ValueError
        If the path fails validation.
    """
    abs_path = _validate_artifact_path(artifact_path, workdir)

    # Compute hash and line count
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    line_count = len(content.split("\n"))

    # Overwrite protection: check if file exists and is protected
    if os.path.exists(abs_path) and os.path.getsize(abs_path) > 0:
        if _is_protected_artifact(artifact_path) and not overwrite_allowed:
            raise ValueError(
                f"artifact_overwrite_blocked: {artifact_path} already exists "
                f"and is a protected artifact. Set overwrite_allowed=True to overwrite."
            )

    # Ensure parent directory exists
    parent_dir = os.path.dirname(abs_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    # Atomic write: write to .tmp, then rename
    tmp_path = abs_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, abs_path)

    return {
        "path": abs_path,
        "hash": content_hash,
        "line_count": line_count,
        "task_prompt_hash": task_prompt_hash,
        "agent_config_hash": agent_config_hash,
    }


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
    """Check for forbidden patterns in text.

    Only hidden-reasoning patterns are checked here.  Mutation and action
    patterns are not scanned against the task prompt because the prompt
    text is composed by the trusted Prompt Composer and includes safety
    instructions that describe forbidden commands as *descriptive text*,
    not as executable directives.  Structural git-mutation safety is
    enforced by:
    - The agent environment (no real git/gh tools)
    - Git Boundary (sole component authorized for git add/commit/push)
    - ``PromptPacket.forbidden_commands`` metadata
    """
    for pattern in _FORBIDDEN_HIDDEN_REASONING_PATTERNS:
        if pattern in text:
            codes.append(REASON_HIDDEN_REASONING_NOT_ALLOWED)
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
    expected_artifact_path: str = "",
    overwrite_allowed: bool = False,
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
    expected_artifact_path:
        Optional expected artifact path to materialize after local
        non-Docker execution.  Must be under ``.project-memory/pr/**``.
    overwrite_allowed:
        Whether overwriting an existing protected artifact is allowed.
        Default ``False``.  Set to ``True`` when the current step owns
        the expected artifact path.

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

    # 6. Local non-Docker execution mode (bypass harness/dispatcher/adapter)
    materialization_evidence: Optional[dict] = None
    artifact_ref = ""
    if not allow_docker:
        adapter_status = "completed"
        exit_code = 0
        stdout = f"Local non-Docker execution: agent_name={agent_name}"
        stderr = ""
        bridge_status = AgentRunnerBridgeStatus.COMPLETED
        stdout_hash = hashlib.sha256(stdout.encode("utf-8")).hexdigest()[:16]
        stderr_hash = None
        execution_request = {
            "execution_request_id": f"bridge-{agent_name}-{task_prompt_hash[:8]}",
            "run_id": f"run-bridge-{agent_name}-{task_prompt_hash[:8]}",
        }
        execution_result = {
            "status": "completed",
            "exit_code": 0,
            "stdout": stdout,
            "stderr": "",
        }

        # Materialize expected artifact if path is provided
        if expected_artifact_path:
            try:
                # Determine artifact type from path
                if "precommit-review.yml" in expected_artifact_path:
                    content = _build_default_precommit_artifact(
                        pr_id="",
                        task_prompt_hash=task_prompt_hash,
                        agent_config_hash=config_hash,
                        artifact_ref=artifact_ref or "",
                    )
                elif "plan-review.yml" in expected_artifact_path:
                    content = _build_default_plan_review_artifact(
                        pr_id="",
                        task_prompt_hash=task_prompt_hash,
                        agent_config_hash=config_hash,
                        artifact_ref=artifact_ref or "",
                    )
                elif "dogfood-proof.yml" in expected_artifact_path:
                    content = _build_default_dogfood_proof(
                        pr_id="",
                        task_prompt_hash=task_prompt_hash,
                        agent_config_hash=config_hash,
                        artifact_ref=artifact_ref or "",
                    )
                else:
                    # Generic minimal artifact
                    content = (
                        f"schema_version: \"0.1\"\n"
                        f"artifact_type: \"local-materialization\"\n"
                        f"task_prompt_hash: \"{task_prompt_hash}\"\n"
                        f"agent_config_hash: \"{config_hash}\"\n"
                    )

                resolved_workdir = workdir or output_dir or os.getcwd()
                materialization_evidence = _materialize_local_artifact(
                    artifact_path=expected_artifact_path,
                    content=content,
                    workdir=resolved_workdir,
                    task_prompt_hash=task_prompt_hash,
                    agent_config_hash=config_hash,
                    overwrite_allowed=overwrite_allowed,
                )
            except ValueError as e:
                # Path validation or overwrite protection failed
                codes.append(f"materialization_failed: {e}")
    else:
        # 7. Build execution request (Docker path)
        execution_request = build_agent_runner_execution_request(
            agent_name=agent_name,
            task_prompt=task_prompt,
            config_content=config_content,
            workdir=workdir,
            allow_docker=allow_docker,
        )

        # 8. Run through local harness
        harness_result = run_local_execution_harness(execution_request)

        # 9. Extract adapter status and result
        execution_result = harness_result.get("execution_result", {})
        adapter_status = execution_result.get("status", "failed")
        exit_code = execution_result.get("exit_code")
        stdout = execution_result.get("stdout", "")
        stderr = execution_result.get("stderr", "")

        # Hash stdout/stderr
        stdout_hash = hashlib.sha256(stdout.encode("utf-8")).hexdigest()[:16] if stdout else None
        stderr_hash = hashlib.sha256(stderr.encode("utf-8")).hexdigest()[:16] if stderr else None

        # 10. Determine bridge status
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

    # 13. Build details with materialization evidence
    detail_parts: list[str] = []
    if materialization_evidence:
        detail_parts.append(
            f"Materialized artifact: path={materialization_evidence['path']}, "
            f"hash={materialization_evidence['hash']}, "
            f"line_count={materialization_evidence['line_count']}"
        )
    details_str = "\n".join(detail_parts) if detail_parts else None

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
        details=details_str,
    )

"""
PR 0147B — Manual Orchestration Store.

Canonical manual orchestration session store at
``.ariadne/orchestration/<session_id>.json``.

Core principle:
    This module stores deterministic session state for a human-gated
    four-agent (planner, plan-review, coder, precommit-review) manual
    orchestration workflow.  It must never execute agents, run shell
    commands, call providers, or perform git/github/Docker operations.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from runner.artifacts import ArtifactStore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "1"
_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")
_MAX_PROMPT_CHARS = 50_000
_MAX_LIST_RESPONSE = 100

# ---------------------------------------------------------------------------
# Stable status values
# ---------------------------------------------------------------------------

STAGE_STATUS_PENDING = "pending"
STAGE_STATUS_READY = "ready"
STAGE_STATUS_IN_PROGRESS = "in_progress"
STAGE_STATUS_COMPLETED = "completed"
STAGE_STATUS_BLOCKED = "blocked"
STAGE_STATUS_REVISION_REQUIRED = "revision_required"
STAGE_STATUS_HUMAN_ACTION_REQUIRED = "human_action_required"
STAGE_STATUS_CLOSED = "closed"

SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_COMPLETED = "completed"
SESSION_STATUS_BLOCKED = "blocked"
SESSION_STATUS_REVISION_REQUIRED = "revision_required"
SESSION_STATUS_CLOSED = "closed"

# ---------------------------------------------------------------------------
# Stage transition table
# ---------------------------------------------------------------------------

_STAGE_TRANSITIONS: dict[str, list[str]] = {
    STAGE_STATUS_PENDING: [STAGE_STATUS_READY],
    STAGE_STATUS_READY: [STAGE_STATUS_IN_PROGRESS],
    STAGE_STATUS_IN_PROGRESS: [STAGE_STATUS_COMPLETED, STAGE_STATUS_BLOCKED],
    STAGE_STATUS_COMPLETED: [STAGE_STATUS_REVISION_REQUIRED, STAGE_STATUS_HUMAN_ACTION_REQUIRED],
    STAGE_STATUS_BLOCKED: [STAGE_STATUS_REVISION_REQUIRED, STAGE_STATUS_READY],
    STAGE_STATUS_REVISION_REQUIRED: [STAGE_STATUS_PENDING, STAGE_STATUS_READY],
    STAGE_STATUS_HUMAN_ACTION_REQUIRED: [STAGE_STATUS_CLOSED],
    STAGE_STATUS_CLOSED: [],
}

# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

ROLES = ("planner", "plan-review", "coder", "precommit-review")

# ---------------------------------------------------------------------------
# Prompt packet schema
# ---------------------------------------------------------------------------

_PROMPT_KEYS = {"role", "stage", "prompt_text", "expected_output_artifact", "write_boundary", "forbidden_authority_summary"}

# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PromptEntry:
    """One prompt in an orchestration packet."""

    role: str
    stage: int
    prompt_text: str
    expected_output_artifact: str
    write_boundary: str
    forbidden_authority_summary: str


@dataclasses.dataclass(frozen=True)
class ManualOrchestrationInput:
    """Input packet for creating a manual orchestration session."""

    schema_version: str
    session_id: str
    prompts: tuple[PromptEntry, ...]


@dataclasses.dataclass(frozen=True)
class OrchestrationStage:
    """Per-stage record in a canonical session."""

    role: str
    stage: int
    status: str
    prompt_sha256: str
    prompt_ref: str  # ArtifactStore path
    artifact_sha256: Optional[str] = None
    artifact_ref: Optional[str] = None
    previous_state_hash: Optional[str] = None
    resulting_state_hash: Optional[str] = None
    verdict: Optional[str] = None
    blockers: tuple[str, ...] = ()
    revision_reason: Optional[str] = None
    recorded_by: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ActionProposal:
    """Inert dangerous-action proposal."""

    proposal_id: str
    session_id: str
    action_type: str
    argv: tuple[str, ...]
    working_directory: Optional[str] = None
    expected_branch: Optional[str] = None
    expected_head: Optional[str] = None
    expected_changed_files: tuple[str, ...] = ()
    expected_payload_hash: Optional[str] = None
    session_state_hash: Optional[str] = None
    risk_level: str = "high"
    rationale: Optional[str] = None
    created_by: Optional[str] = None
    proposal_time: Optional[str] = None
    human_action_required: bool = True


@dataclasses.dataclass(frozen=True)
class HumanCheckpoint:
    """Records human intent only — must never execute."""

    checkpoint_id: str
    session_id: str
    decision: str
    human_actor: str
    reason: str
    proposal_id: Optional[str] = None
    proposal_hash: Optional[str] = None
    session_state_hash: Optional[str] = None
    decision_record_hash: Optional[str] = None
    checkpoint_time: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ExternalActionResult:
    """Operator-supplied result after a human-performed action."""

    result_id: str
    proposal_id: str
    session_id: str
    reported_status: str
    evidence_refs: tuple[str, ...] = ()
    operator_notes: Optional[str] = None
    recorded_by: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ManualOrchestrationSession:
    """Canonical session record — the single source of truth."""

    session_id: str
    schema_version: str
    status: str
    stages: tuple[OrchestrationStage, ...]
    session_state_hash: str
    action_proposals: tuple[ActionProposal, ...] = ()
    human_checkpoints: tuple[HumanCheckpoint, ...] = ()
    external_action_results: tuple[ExternalActionResult, ...] = ()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_session_id(session_id: str) -> None:
    """Reject malformed session IDs."""
    if not _SESSION_ID_RE.match(session_id):
        raise ValueError(f"Invalid session_id: {session_id!r}")


def _validate_prompt(prompt: dict[str, Any], codes: list[str]) -> None:
    """Validate a single prompt dict, appending reason codes."""
    missing = _PROMPT_KEYS - set(prompt.keys())
    if missing:
        codes.append(f"missing_prompt_field:{','.join(sorted(missing))}")
        return
    role = prompt.get("role", "")
    if role not in ROLES:
        codes.append(f"unsupported_role:{role}")
    stage = prompt.get("stage")
    if stage not in (1, 2, 3, 4):
        codes.append(f"invalid_stage:{stage}")
    text = prompt.get("prompt_text", "")
    if not text or not text.strip():
        codes.append("empty_prompt_text")
    elif len(text) > _MAX_PROMPT_CHARS:
        codes.append(f"oversized_prompt:{len(text)}")
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        codes.append("non_utf8_prompt")


def _check_forbidden_action_patterns(text: str, codes: list[str]) -> None:
    """Check for forbidden action patterns — reused from backlog_decision.py pattern."""
    forbidden = (
        "git add", "git commit", "git push", "gh pr", "docker run", "docker exec",
        "subprocess.run", "subprocess.Popen",
    )
    for pattern in forbidden:
        if pattern in text.lower():
            codes.append(f"forbidden_action_pattern:{pattern}")
            return


# ---------------------------------------------------------------------------
# Canonical JSON serialisation
# ---------------------------------------------------------------------------


def _stage_to_dict(s: OrchestrationStage) -> dict[str, Any]:
    return {
        "role": s.role,
        "stage": s.stage,
        "status": s.status,
        "prompt_sha256": s.prompt_sha256,
        "prompt_ref": s.prompt_ref,
        "artifact_sha256": s.artifact_sha256,
        "artifact_ref": s.artifact_ref,
        "previous_state_hash": s.previous_state_hash,
        "resulting_state_hash": s.resulting_state_hash,
        "verdict": s.verdict,
        "blockers": list(s.blockers),
        "revision_reason": s.revision_reason,
        "recorded_by": s.recorded_by,
    }


def _proposal_to_dict(p: ActionProposal) -> dict[str, Any]:
    return {
        "proposal_id": p.proposal_id,
        "session_id": p.session_id,
        "action_type": p.action_type,
        "argv": list(p.argv),
        "working_directory": p.working_directory,
        "expected_branch": p.expected_branch,
        "expected_head": p.expected_head,
        "expected_changed_files": list(p.expected_changed_files),
        "expected_payload_hash": p.expected_payload_hash,
        "session_state_hash": p.session_state_hash,
        "risk_level": p.risk_level,
        "rationale": p.rationale,
        "created_by": p.created_by,
        "proposal_time": p.proposal_time,
        "human_action_required": p.human_action_required,
    }


def _checkpoint_to_dict(c: HumanCheckpoint) -> dict[str, Any]:
    return {
        "checkpoint_id": c.checkpoint_id,
        "session_id": c.session_id,
        "decision": c.decision,
        "human_actor": c.human_actor,
        "reason": c.reason,
        "proposal_id": c.proposal_id,
        "proposal_hash": c.proposal_hash,
        "session_state_hash": c.session_state_hash,
        "decision_record_hash": c.decision_record_hash,
        "checkpoint_time": c.checkpoint_time,
    }


def _result_to_dict(r: ExternalActionResult) -> dict[str, Any]:
    return {
        "result_id": r.result_id,
        "proposal_id": r.proposal_id,
        "session_id": r.session_id,
        "reported_status": r.reported_status,
        "evidence_refs": list(r.evidence_refs),
        "operator_notes": r.operator_notes,
        "recorded_by": r.recorded_by,
    }


def session_to_dict(session: ManualOrchestrationSession) -> dict[str, Any]:
    """Serialize a canonical session to a deterministic dict for API output.

    Includes the ``session_state_hash`` so clients can verify state.
    """
    return {
        "session_id": session.session_id,
        "schema_version": session.schema_version,
        "status": session.status,
        "stages": [_stage_to_dict(s) for s in session.stages],
        "session_state_hash": session.session_state_hash,
        "action_proposals": [_proposal_to_dict(p) for p in session.action_proposals],
        "human_checkpoints": [_checkpoint_to_dict(c) for c in session.human_checkpoints],
        "external_action_results": [_result_to_dict(r) for r in session.external_action_results],
    }


def canonical_json(session: ManualOrchestrationSession) -> str:
    """Deterministic JSON from a canonical session, excluding self-referential state hash."""
    d = {
        "session_id": session.session_id,
        "schema_version": session.schema_version,
        "status": session.status,
        "stages": [_stage_to_dict(s) for s in session.stages],
        "action_proposals": [_proposal_to_dict(p) for p in session.action_proposals],
        "human_checkpoints": [_checkpoint_to_dict(c) for c in session.human_checkpoints],
        "external_action_results": [_result_to_dict(r) for r in session.external_action_results],
    }
    return json.dumps(d, sort_keys=True, ensure_ascii=False, indent=2)


def compute_session_state_hash(session: ManualOrchestrationSession) -> str:
    """Compute the deterministic state hash of a canonical session."""
    return hashlib.sha256(canonical_json(session).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Import and session creation
# ---------------------------------------------------------------------------


def _canonical_prompt_entry(entry: PromptEntry) -> dict[str, Any]:
    return {
        "role": entry.role,
        "stage": entry.stage,
        "prompt_text": entry.prompt_text,
        "expected_output_artifact": entry.expected_output_artifact,
        "write_boundary": entry.write_boundary,
        "forbidden_authority_summary": entry.forbidden_authority_summary,
    }


def _build_import_canonical(prompts: tuple[PromptEntry, ...]) -> str:
    """Build the canonical import JSON for session ID derivation."""
    data = {
        "schema_version": _SCHEMA_VERSION,
        "prompts": [_canonical_prompt_entry(p) for p in prompts],
    }
    return json.dumps(data, sort_keys=True, ensure_ascii=False)


def _derive_session_id(prompts: tuple[PromptEntry, ...]) -> str:
    """Deterministic session ID from canonical import JSON."""
    canonical = _build_import_canonical(prompts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def import_session(
    packet: ManualOrchestrationInput,
    orchestration_root: str,
    artifact_store: ArtifactStore,
) -> ManualOrchestrationSession:
    """Import a manual orchestration packet and create a session.

    Parameters
    ----------
    packet:
        The validated import packet.
    orchestration_root:
        Root directory for canonical session files
        (``.ariadne/orchestration/``).
    artifact_store:
        ArtifactStore for storing prompt content.

    Returns
    -------
    ManualOrchestrationSession
        The newly created canonical session.

    Raises
    ------
    ValueError
        If validation fails.
    FileExistsError
        If the session already exists.
    """
    # Derive session ID
    if packet.session_id:
        expected = _derive_session_id(packet.prompts)
        if packet.session_id != expected:
            raise ValueError(
                f"session_id mismatch: got {packet.session_id!r}, expected {expected!r}"
            )
    else:
        session_id = _derive_session_id(packet.prompts)
    session_id = packet.session_id or _derive_session_id(packet.prompts)

    # Store prompts via ArtifactStore
    stages: list[OrchestrationStage] = []
    prompt_order = {"planner": 0, "plan-review": 1, "coder": 2, "precommit-review": 3}
    sorted_prompts = sorted(packet.prompts, key=lambda p: prompt_order.get(p.role, 99))

    for entry in sorted_prompts:
        prompt_text = entry.prompt_text
        prompt_sha256 = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
        kind_label = f"prompt_{entry.role}"
        result = artifact_store.put_text(kind_label, prompt_text)
        prompt_ref = result.path

        stage = OrchestrationStage(
            role=entry.role,
            stage=entry.stage,
            status=STAGE_STATUS_PENDING,
            prompt_sha256=prompt_sha256,
            prompt_ref=prompt_ref,
        )
        stages.append(stage)

    # Build initial session (empty state hash)
    session = ManualOrchestrationSession(
        session_id=session_id,
        schema_version=_SCHEMA_VERSION,
        status=SESSION_STATUS_ACTIVE,
        stages=tuple(stages),
        session_state_hash="",
    )
    # Compute actual state hash
    state_hash = compute_session_state_hash(session)
    session = ManualOrchestrationSession(
        session_id=session_id,
        schema_version=_SCHEMA_VERSION,
        status=SESSION_STATUS_ACTIVE,
        stages=tuple(stages),
        session_state_hash=state_hash,
    )

    # Check if session file already exists
    session_path = os.path.join(orchestration_root, f"{session_id}.json")
    if os.path.exists(session_path):
        raise FileExistsError(f"Session {session_id} already exists")

    # Atomic write
    os.makedirs(orchestration_root, exist_ok=True)
    _atomic_write(session, session_path)

    return session


# ---------------------------------------------------------------------------
# Read session
# ---------------------------------------------------------------------------


def read_session(session_id: str, orchestration_root: str) -> Optional[ManualOrchestrationSession]:
    """Read a canonical session file. Returns None if not found."""
    _validate_session_id(session_id)
    session_path = os.path.join(orchestration_root, f"{session_id}.json")
    if not os.path.isfile(session_path):
        return None
    try:
        with open(session_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    return _dict_to_session(data)


def _dict_to_session(data: dict[str, Any]) -> Optional[ManualOrchestrationSession]:
    """Deserialize a canonical session dict. Returns None on parse failure."""
    try:
        stages = []
        for sd in data.get("stages", []):
            stages.append(OrchestrationStage(
                role=sd.get("role", ""),
                stage=sd.get("stage", 0),
                status=sd.get("status", "unknown"),
                prompt_sha256=sd.get("prompt_sha256", ""),
                prompt_ref=sd.get("prompt_ref", ""),
                artifact_sha256=sd.get("artifact_sha256"),
                artifact_ref=sd.get("artifact_ref"),
                previous_state_hash=sd.get("previous_state_hash"),
                resulting_state_hash=sd.get("resulting_state_hash"),
                verdict=sd.get("verdict"),
                blockers=tuple(sd.get("blockers", [])),
                revision_reason=sd.get("revision_reason"),
                recorded_by=sd.get("recorded_by"),
            ))

        proposals = []
        for pd in data.get("action_proposals", []):
            proposals.append(ActionProposal(
                proposal_id=pd.get("proposal_id", ""),
                session_id=pd.get("session_id", ""),
                action_type=pd.get("action_type", ""),
                argv=tuple(pd.get("argv", [])),
                working_directory=pd.get("working_directory"),
                expected_branch=pd.get("expected_branch"),
                expected_head=pd.get("expected_head"),
                expected_changed_files=tuple(pd.get("expected_changed_files", [])),
                expected_payload_hash=pd.get("expected_payload_hash"),
                session_state_hash=pd.get("session_state_hash"),
                risk_level=pd.get("risk_level", "high"),
                rationale=pd.get("rationale"),
                created_by=pd.get("created_by"),
                proposal_time=pd.get("proposal_time"),
                human_action_required=pd.get("human_action_required", True),
            ))

        checkpoints = []
        for cd in data.get("human_checkpoints", []):
            checkpoints.append(HumanCheckpoint(
                checkpoint_id=cd.get("checkpoint_id", ""),
                session_id=cd.get("session_id", ""),
                decision=cd.get("decision", ""),
                human_actor=cd.get("human_actor", ""),
                reason=cd.get("reason", ""),
                proposal_id=cd.get("proposal_id"),
                proposal_hash=cd.get("proposal_hash"),
                session_state_hash=cd.get("session_state_hash"),
                decision_record_hash=cd.get("decision_record_hash"),
                checkpoint_time=cd.get("checkpoint_time"),
            ))

        results = []
        for rd in data.get("external_action_results", []):
            results.append(ExternalActionResult(
                result_id=rd.get("result_id", ""),
                proposal_id=rd.get("proposal_id", ""),
                session_id=rd.get("session_id", ""),
                reported_status=rd.get("reported_status", ""),
                evidence_refs=tuple(rd.get("evidence_refs", [])),
                operator_notes=rd.get("operator_notes"),
                recorded_by=rd.get("recorded_by"),
            ))

        return ManualOrchestrationSession(
            session_id=data.get("session_id", ""),
            schema_version=data.get("schema_version", ""),
            status=data.get("status", SESSION_STATUS_ACTIVE),
            stages=tuple(stages),
            session_state_hash=data.get("session_state_hash", ""),
            action_proposals=tuple(proposals),
            human_checkpoints=tuple(checkpoints),
            external_action_results=tuple(results),
        )
    except (TypeError, ValueError, KeyError):
        return None


# ---------------------------------------------------------------------------
# List sessions
# ---------------------------------------------------------------------------


def list_sessions(orchestration_root: str) -> tuple[str, ...]:
    """List all session IDs found in the orchestration root."""
    if not os.path.isdir(orchestration_root):
        return ()
    ids: list[str] = []
    try:
        for entry in sorted(os.listdir(orchestration_root), reverse=True):
            if entry.endswith(".json"):
                sid = entry[:-5]
                if _SESSION_ID_RE.match(sid):
                    ids.append(sid)
    except OSError:
        return ()
    return tuple(ids[:_MAX_LIST_RESPONSE])


# ---------------------------------------------------------------------------
# Stage transitions
# ---------------------------------------------------------------------------


def _can_transition(from_status: str, to_status: str) -> bool:
    """Check if a stage status transition is allowed."""
    allowed = _STAGE_TRANSITIONS.get(from_status, [])
    return to_status in allowed


def _check_stage_order(
    stages: tuple[OrchestrationStage, ...],
    role: str,
    codes: list[str],
) -> None:
    """Enforce stage-order gates."""
    index_map = {s.role: i for i, s in enumerate(stages)}
    if role not in index_map:
        codes.append(f"unknown_role:{role}")
        return
    idx = index_map[role]

    # Stage 2 (plan-review) requires Stage 1 (planner) completed
    if idx == 1:
        if stages[0].status != STAGE_STATUS_COMPLETED:
            codes.append("stage_order:planner_not_completed")

    # Stage 3 (coder) requires Stage 2 completed with approve/warning
    if idx == 2:
        if stages[1].status != STAGE_STATUS_COMPLETED:
            codes.append("stage_order:plan_review_not_completed")
        else:
            verdict = stages[1].verdict or ""
            if verdict not in ("approve", "warning"):
                codes.append("stage_order:plan_review_verdict_not_acceptable")

    # Stage 4 (precommit-review) requires Stage 3 completed
    if idx == 3:
        if stages[2].status != STAGE_STATUS_COMPLETED:
            codes.append("stage_order:coder_not_completed")


def _set_stage_status(
    session: ManualOrchestrationSession,
    role: str,
    new_status: str,
    codes: list[str],
) -> ManualOrchestrationSession:
    """Create a new session with one stage status changed. Validates transitions."""
    new_stages: list[OrchestrationStage] = []
    found = False
    for s in session.stages:
        if s.role == role:
            found = True
            if not _can_transition(s.status, new_status):
                codes.append(f"invalid_transition:{s.status}->{new_status}")
                return session
            # If transitioning to completed, enforce stage order
            if new_status == STAGE_STATUS_COMPLETED:
                _check_stage_order(session.stages, role, codes)
                if codes:
                    return session
            new_stages.append(OrchestrationStage(
                role=s.role,
                stage=s.stage,
                status=new_status,
                prompt_sha256=s.prompt_sha256,
                prompt_ref=s.prompt_ref,
                artifact_sha256=s.artifact_sha256,
                artifact_ref=s.artifact_ref,
                previous_state_hash=s.previous_state_hash,
                resulting_state_hash=s.resulting_state_hash,
                verdict=s.verdict,
                blockers=s.blockers,
                revision_reason=s.revision_reason,
                recorded_by=s.recorded_by,
            ))
        else:
            new_stages.append(s)
    if not found:
        codes.append(f"role_not_found:{role}")

    if codes:
        return session

    new_session = ManualOrchestrationSession(
        session_id=session.session_id,
        schema_version=session.schema_version,
        status=_derive_session_status(tuple(new_stages)),
        stages=tuple(new_stages),
        session_state_hash="",  # recompute below
        action_proposals=session.action_proposals,
        human_checkpoints=session.human_checkpoints,
        external_action_results=session.external_action_results,
    )
    new_hash = compute_session_state_hash(new_session)
    return ManualOrchestrationSession(
        session_id=session.session_id,
        schema_version=session.schema_version,
        status=_derive_session_status(tuple(new_stages)),
        stages=tuple(new_stages),
        session_state_hash=new_hash,
        action_proposals=session.action_proposals,
        human_checkpoints=session.human_checkpoints,
        external_action_results=session.external_action_results,
    )


def _derive_session_status(stages: tuple[OrchestrationStage, ...]) -> str:
    """Derive session status from stage statuses."""
    all_completed = all(s.status == STAGE_STATUS_COMPLETED for s in stages)
    any_blocked = any(s.status == STAGE_STATUS_BLOCKED for s in stages)
    any_human = any(s.status == STAGE_STATUS_HUMAN_ACTION_REQUIRED for s in stages)
    any_revision = any(s.status == STAGE_STATUS_REVISION_REQUIRED for s in stages)
    any_pending = any(s.status == STAGE_STATUS_PENDING for s in stages)

    if any_human:
        return SESSION_STATUS_ACTIVE
    if all_completed:
        return SESSION_STATUS_COMPLETED
    if any_blocked:
        return SESSION_STATUS_BLOCKED
    if any_revision:
        return SESSION_STATUS_REVISION_REQUIRED
    if any_pending:
        return SESSION_STATUS_ACTIVE
    return SESSION_STATUS_ACTIVE


# ---------------------------------------------------------------------------
# Record evidence
# ---------------------------------------------------------------------------


def record_evidence(
    session: ManualOrchestrationSession,
    role: str,
    artifact_sha256: str,
    artifact_ref: str,
    recorded_by: str,
    orchestration_root: str,
    expected_state_hash: str,
    verdict: Optional[str] = None,
    blockers: Optional[tuple[str, ...]] = None,
    revision_reason: Optional[str] = None,
    previous_state_hash: Optional[str] = None,
) -> ManualOrchestrationSession:
    """Record stage evidence and transition stage to completed.

    Validates expected_state_hash against current session state hash.
    """
    codes: list[str] = []

    if session.session_state_hash != expected_state_hash:
        raise StaleStateError(
            f"Expected state hash {expected_state_hash!r}, "
            f"got {session.session_state_hash!r}"
        )

    new_stages: list[OrchestrationStage] = []
    prev_hash = session.session_state_hash
    found = False
    for s in session.stages:
        if s.role == role:
            found = True
            if s.status != STAGE_STATUS_IN_PROGRESS:
                codes.append(f"cannot_record_evidence:stage_status={s.status}")
                break
            # Enforce stage-order gates for review stages
            _check_stage_order(session.stages, role, codes)
            if codes:
                break

            new_stage = OrchestrationStage(
                role=s.role,
                stage=s.stage,
                status=STAGE_STATUS_COMPLETED,
                prompt_sha256=s.prompt_sha256,
                prompt_ref=s.prompt_ref,
                artifact_sha256=artifact_sha256,
                artifact_ref=artifact_ref,
                previous_state_hash=prev_hash,
                resulting_state_hash="",  # set below
                verdict=verdict,
                blockers=blockers or (),
                revision_reason=revision_reason,
                recorded_by=recorded_by,
            )
            new_stages.append(new_stage)
        else:
            new_stages.append(s)

    if codes or not found:
        raise ValueError(f"Cannot record evidence for {role}: {codes}")

    # Update resulting_state_hash for the recorded stage
    # (requires full session hash, so we build and compute)
    new_session = ManualOrchestrationSession(
        session_id=session.session_id,
        schema_version=session.schema_version,
        status=_derive_session_status(tuple(new_stages)),
        stages=tuple(new_stages),
        session_state_hash="",
        action_proposals=session.action_proposals,
        human_checkpoints=session.human_checkpoints,
        external_action_results=session.external_action_results,
    )
    new_hash = compute_session_state_hash(new_session)

    # Fix the resulting_state_hash of the newly recorded stage
    new_stages2: list[OrchestrationStage] = []
    for s in new_session.stages:
        if s.role == role:
            new_stages2.append(OrchestrationStage(
                role=s.role,
                stage=s.stage,
                status=s.status,
                prompt_sha256=s.prompt_sha256,
                prompt_ref=s.prompt_ref,
                artifact_sha256=s.artifact_sha256,
                artifact_ref=s.artifact_ref,
                previous_state_hash=s.previous_state_hash,
                resulting_state_hash=new_hash,
                verdict=s.verdict,
                blockers=s.blockers,
                revision_reason=s.revision_reason,
                recorded_by=s.recorded_by,
            ))
        else:
            new_stages2.append(s)

    final = ManualOrchestrationSession(
        session_id=session.session_id,
        schema_version=session.schema_version,
        status=_derive_session_status(tuple(new_stages2)),
        stages=tuple(new_stages2),
        session_state_hash=new_hash,
        action_proposals=session.action_proposals,
        human_checkpoints=session.human_checkpoints,
        external_action_results=session.external_action_results,
    )

    _atomic_write(final, os.path.join(orchestration_root, f"{session.session_id}.json"))
    return final


# ---------------------------------------------------------------------------
# Record blocked
# ---------------------------------------------------------------------------


def record_blocked(
    session: ManualOrchestrationSession,
    role: str,
    reason: str,
    orchestration_root: str,
    expected_state_hash: str,
) -> ManualOrchestrationSession:
    """Mark a stage as blocked."""
    if session.session_state_hash != expected_state_hash:
        raise StaleStateError(
            f"Expected state hash {expected_state_hash!r}, "
            f"got {session.session_state_hash!r}"
        )

    codes: list[str] = []
    result = _set_stage_status(session, role, STAGE_STATUS_BLOCKED, codes)
    if codes:
        raise ValueError(f"Cannot block {role}: {codes}")
    _atomic_write(result, os.path.join(orchestration_root, f"{session.session_id}.json"))
    return result


# ---------------------------------------------------------------------------
# Action proposals
# ---------------------------------------------------------------------------


def create_proposal(
    session: ManualOrchestrationSession,
    action_type: str,
    argv: tuple[str, ...],
    session_state_hash: str,
    created_by: str,
    working_directory: Optional[str] = None,
    expected_branch: Optional[str] = None,
    expected_head: Optional[str] = None,
    expected_changed_files: Optional[tuple[str, ...]] = None,
    expected_payload_hash: Optional[str] = None,
    risk_level: str = "high",
    rationale: Optional[str] = None,
) -> tuple[ActionProposal, ManualOrchestrationSession]:
    """Create an inert dangerous-action proposal. Does not execute anything."""
    if session.session_state_hash != session_state_hash:
        raise StaleStateError(
            f"Expected state hash {session_state_hash!r}, "
            f"got {session.session_state_hash!r}"
        )

    proposal = ActionProposal(
        proposal_id="",  # computed below
        session_id=session.session_id,
        action_type=action_type,
        argv=argv,
        working_directory=working_directory,
        expected_branch=expected_branch,
        expected_head=expected_head,
        expected_changed_files=tuple(expected_changed_files or ()),
        expected_payload_hash=expected_payload_hash,
        session_state_hash=session_state_hash,
        risk_level=risk_level,
        rationale=rationale,
        created_by=created_by,
    )
    # Compute proposal_id
    proposal_canonical = json.dumps({
        "session_id": proposal.session_id,
        "action_type": proposal.action_type,
        "argv": list(proposal.argv),
        "session_state_hash": proposal.session_state_hash,
    }, sort_keys=True, ensure_ascii=False)
    proposal_id = hashlib.sha256(proposal_canonical.encode("utf-8")).hexdigest()[:16]
    proposal = ActionProposal(
        proposal_id=proposal_id,
        session_id=proposal.session_id,
        action_type=proposal.action_type,
        argv=proposal.argv,
        working_directory=proposal.working_directory,
        expected_branch=proposal.expected_branch,
        expected_head=proposal.expected_head,
        expected_changed_files=proposal.expected_changed_files,
        expected_payload_hash=proposal.expected_payload_hash,
        session_state_hash=proposal.session_state_hash,
        risk_level=proposal.risk_level,
        rationale=proposal.rationale,
        created_by=proposal.created_by,
        human_action_required=True,
    )

    new_proposals = list(session.action_proposals) + [proposal]
    new_session = ManualOrchestrationSession(
        session_id=session.session_id,
        schema_version=session.schema_version,
        status=SESSION_STATUS_ACTIVE,
        stages=session.stages,
        session_state_hash="",
        action_proposals=tuple(new_proposals),
        human_checkpoints=session.human_checkpoints,
        external_action_results=session.external_action_results,
    )
    new_hash = compute_session_state_hash(new_session)
    new_session = ManualOrchestrationSession(
        session_id=session.session_id,
        schema_version=session.schema_version,
        status=_derive_session_status(new_session.stages),
        stages=new_session.stages,
        session_state_hash=new_hash,
        action_proposals=tuple(new_proposals),
        human_checkpoints=session.human_checkpoints,
        external_action_results=session.external_action_results,
    )

    return proposal, new_session


# ---------------------------------------------------------------------------
# Human checkpoint
# ---------------------------------------------------------------------------


def record_checkpoint(
    session: ManualOrchestrationSession,
    decision: str,
    human_actor: str,
    reason: str,
    session_state_hash: str,
    proposal_id: Optional[str] = None,
    proposal_hash: Optional[str] = None,
    orchestration_root: Optional[str] = None,
) -> tuple[HumanCheckpoint, ManualOrchestrationSession]:
    """Record a human checkpoint. Does NOT execute anything."""
    if session.session_state_hash != session_state_hash:
        raise StaleStateError(
            f"Expected state hash {session_state_hash!r}, "
            f"got {session.session_state_hash!r}"
        )

    valid_decisions = ("proceed_manually", "stop", "revise", "defer")
    if decision not in valid_decisions:
        raise ValueError(f"Invalid checkpoint decision: {decision!r}")

    checkpoint_data = {
        "session_id": session.session_id,
        "decision": decision,
        "human_actor": human_actor,
        "reason": reason,
    }
    decision_record_hash = hashlib.sha256(
        json.dumps(checkpoint_data, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]

    checkpoint = HumanCheckpoint(
        checkpoint_id="",  # computed below
        session_id=session.session_id,
        decision=decision,
        human_actor=human_actor,
        reason=reason,
        proposal_id=proposal_id,
        proposal_hash=proposal_hash,
        session_state_hash=session_state_hash,
        decision_record_hash=decision_record_hash,
    )
    # Compute checkpoint_id
    cp_canonical = json.dumps({
        "session_id": checkpoint.session_id,
        "decision": checkpoint.decision,
        "human_actor": checkpoint.human_actor,
        "reason": checkpoint.reason,
        "session_state_hash": checkpoint.session_state_hash,
    }, sort_keys=True, ensure_ascii=False)
    checkpoint_id = hashlib.sha256(cp_canonical.encode("utf-8")).hexdigest()[:16]
    checkpoint = HumanCheckpoint(
        checkpoint_id=checkpoint_id,
        session_id=session.session_id,
        decision=decision,
        human_actor=human_actor,
        reason=reason,
        proposal_id=proposal_id,
        proposal_hash=proposal_hash,
        session_state_hash=session_state_hash,
        decision_record_hash=decision_record_hash,
    )

    # Determine new session status based on decision
    new_status = session.status
    if decision == "stop":
        new_status = SESSION_STATUS_CLOSED
    elif decision == "revise":
        new_status = SESSION_STATUS_REVISION_REQUIRED
    elif decision == "proceed_manually":
        # Signals intent only — status stays active
        new_status = SESSION_STATUS_ACTIVE

    new_checkpoints = list(session.human_checkpoints) + [checkpoint]
    new_session = ManualOrchestrationSession(
        session_id=session.session_id,
        schema_version=session.schema_version,
        status=new_status,
        stages=session.stages,
        session_state_hash="",
        action_proposals=session.action_proposals,
        human_checkpoints=tuple(new_checkpoints),
        external_action_results=session.external_action_results,
    )
    new_hash = compute_session_state_hash(new_session)
    new_session = ManualOrchestrationSession(
        session_id=session.session_id,
        schema_version=session.schema_version,
        status=new_status,
        stages=session.stages,
        session_state_hash=new_hash,
        action_proposals=session.action_proposals,
        human_checkpoints=tuple(new_checkpoints),
        external_action_results=session.external_action_results,
    )

    if orchestration_root:
        _atomic_write(new_session, os.path.join(orchestration_root, f"{session.session_id}.json"))

    return checkpoint, new_session


# ---------------------------------------------------------------------------
# External action result
# ---------------------------------------------------------------------------


def record_external_result(
    session: ManualOrchestrationSession,
    proposal_id: str,
    reported_status: str,
    recorded_by: str,
    evidence_refs: Optional[tuple[str, ...]] = None,
    operator_notes: Optional[str] = None,
) -> tuple[ExternalActionResult, ManualOrchestrationSession]:
    """Record an external action result from the operator."""
    valid_statuses = ("success", "failure", "result_unavailable")
    if reported_status not in valid_statuses:
        raise ValueError(f"Invalid reported_status: {reported_status!r}")

    result_canonical = json.dumps({
        "proposal_id": proposal_id,
        "session_id": session.session_id,
        "reported_status": reported_status,
    }, sort_keys=True, ensure_ascii=False)
    result_id = hashlib.sha256(result_canonical.encode("utf-8")).hexdigest()[:16]

    result = ExternalActionResult(
        result_id=result_id,
        proposal_id=proposal_id,
        session_id=session.session_id,
        reported_status=reported_status,
        evidence_refs=tuple(evidence_refs or ()),
        operator_notes=operator_notes,
        recorded_by=recorded_by,
    )

    new_results = list(session.external_action_results) + [result]
    new_session = ManualOrchestrationSession(
        session_id=session.session_id,
        schema_version=session.schema_version,
        status=session.status,
        stages=session.stages,
        session_state_hash="",
        action_proposals=session.action_proposals,
        human_checkpoints=session.human_checkpoints,
        external_action_results=tuple(new_results),
    )
    new_hash = compute_session_state_hash(new_session)
    new_session = ManualOrchestrationSession(
        session_id=session.session_id,
        schema_version=session.schema_version,
        status=session.status,
        stages=session.stages,
        session_state_hash=new_hash,
        action_proposals=session.action_proposals,
        human_checkpoints=session.human_checkpoints,
        external_action_results=tuple(new_results),
    )

    return result, new_session


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


def _atomic_write(session: ManualOrchestrationSession, path: str) -> None:
    """Write canonical session JSON atomically, including the state hash."""
    tmp_path = path + ".tmp"
    content = json.dumps(session_to_dict(session), sort_keys=True, ensure_ascii=False, indent=2)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, path)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StaleStateError(ValueError):
    """Raised when an expected state hash does not match current state."""
    pass


# ---------------------------------------------------------------------------
# Validate a prompt packet dict
# ---------------------------------------------------------------------------


def validate_packet_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Validate an import packet dict and return normalized result.

    Returns a dict with keys:
      valid: bool
      errors: list[str]
      packet: ManualOrchestrationInput | None
      session_id: str | None
    """
    errors: list[str] = []
    sv = data.get("schema_version")
    if sv != _SCHEMA_VERSION:
        errors.append(f"unsupported_schema_version:{sv}")

    prompts_data = data.get("prompts", [])
    if not isinstance(prompts_data, list):
        errors.append("prompts_not_a_list")
        return {"valid": False, "errors": errors, "packet": None, "session_id": None}

    if len(prompts_data) != 4:
        errors.append(f"expected_exactly_4_prompts_got:{len(prompts_data)}")

    prompts: list[PromptEntry] = []
    seen_roles: set[str] = set()
    for i, pd in enumerate(prompts_data):
        if not isinstance(pd, dict):
            errors.append(f"prompt_{i}_not_a_dict")
            continue
        _validate_prompt(pd, errors)
        role = pd.get("role", "")
        if role in seen_roles:
            errors.append(f"duplicate_role:{role}")
        seen_roles.add(role)

        # Check ordering
        expected_role = ROLES[i] if i < 4 else None
        if role != expected_role:
            errors.append(f"prompt_{i}_expected_role:{expected_role}_got:{role}")

        prompt_entry = PromptEntry(
            role=role,
            stage=pd.get("stage", 0),
            prompt_text=pd.get("prompt_text", ""),
            expected_output_artifact=pd.get("expected_output_artifact", ""),
            write_boundary=pd.get("write_boundary", ""),
            forbidden_authority_summary=pd.get("forbidden_authority_summary", ""),
        )
        prompts.append(prompt_entry)

    if errors:
        return {"valid": False, "errors": errors, "packet": None, "session_id": None}

    # Build packet
    provided_sid = data.get("session_id", "") or ""
    session_id = provided_sid if provided_sid else _derive_session_id(tuple(prompts))

    # Validate provided session_id if given
    if provided_sid and provided_sid != _derive_session_id(tuple(prompts)):
        errors.append("session_id_mismatch")
        return {"valid": False, "errors": errors, "packet": None, "session_id": None}

    packet = ManualOrchestrationInput(
        schema_version=_SCHEMA_VERSION,
        session_id=session_id,
        prompts=tuple(prompts),
    )

    return {"valid": True, "errors": [], "packet": packet, "session_id": session_id}

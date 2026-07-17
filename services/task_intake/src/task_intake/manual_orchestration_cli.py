"""
PR 0147B — Manual Orchestration CLI.

Human-run command-line interface for the manual orchestration mode.
Must never execute agents, call providers, run shell commands,
or perform git/github/Docker operations.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from task_intake.manual_orchestration import (
    STAGE_STATUS_COMPLETED,
    STAGE_STATUS_IN_PROGRESS,
    STAGE_STATUS_PENDING,
    STAGE_STATUS_READY,
    StaleStateError,
    ActionProposal,
    ManualOrchestrationInput,
    PromptEntry,
    canonical_json,
    compute_session_state_hash,
    create_proposal,
    import_session,
    list_sessions,
    read_session,
    record_blocked,
    record_checkpoint,
    record_evidence,
    record_external_result,
    session_to_dict,
    validate_packet_dict,
)
from runner.artifacts import ArtifactStore


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _get_orchestration_root() -> str:
    """Return the default orchestration root.
    
    Resolved relative to the repository root (parent of services/).
    """
    current = os.path.dirname(os.path.abspath(__file__))
    while current != os.path.dirname(current):
        if os.path.basename(current) == "services":
            repo_root = os.path.dirname(current)
            return os.path.join(repo_root, ".ariadne", "orchestration")
        current = os.path.dirname(current)
    return os.path.join(os.getcwd(), ".ariadne", "orchestration")


def _get_artifact_store_root() -> str:
    """Return the default artifact store root for orchestration."""
    return os.path.join(_get_orchestration_root(), "artifacts")


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------


def _cmd_import_session(args: argparse.Namespace) -> int:
    """import-session: Import a new orchestration packet."""
    packet_path = args.packet
    if not os.path.isfile(packet_path):
        print(f"ERROR: Packet file not found: {packet_path}", file=sys.stderr)
        return 1
    try:
        with open(packet_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR: Cannot read packet file: {e}", file=sys.stderr)
        return 1

    result = validate_packet_dict(data)
    if not result["valid"]:
        for err in result["errors"]:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    packet = result["packet"]
    orchestration_root = getattr(args, "orchestration_root", None) or _get_orchestration_root()
    artifact_root = getattr(args, "artifact_root", None) or _get_artifact_store_root()

    store = ArtifactStore(Path(artifact_root))
    try:
        session = import_session(packet, orchestration_root, store)
    except FileExistsError:
        print(f"Session {packet.session_id} already exists.")
        if args.json:
            print(json.dumps({"session_id": packet.session_id, "status": "duplicate"}))
        return 0
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(canonical_json(session))
    else:
        print(f"Session imported: {session.session_id}")
        print(f"  Status: {session.status}")
        print(f"  State hash: {session.session_state_hash}")
    return 0


def _cmd_stage_status(args: argparse.Namespace) -> int:
    """stage-status: Show session stage status."""
    session = _get_validated_session(args)
    if session is None:
        return 1

    if args.json:
        print(canonical_json(session))
        return 0

    print(f"Session: {session.session_id}")
    print(f"  Status: {session.status}")
    print(f"  State hash: {session.session_state_hash}")
    print("  Stages:")
    for s in session.stages:
        verdict_str = f"  verdict={s.verdict}" if s.verdict else ""
        blockers_str = f"  blockers={s.blockers}" if s.blockers else ""
        hash_str = f"  hash={s.resulting_state_hash}" if s.resulting_state_hash else ""
        print(f"    {s.role} (stage {s.stage}): {s.status}{verdict_str}{blockers_str}{hash_str}")
    return 0


def _cmd_record_evidence(args: argparse.Namespace) -> int:
    """record-evidence: Record completed stage evidence."""
    session = _get_validated_session(args)
    if session is None:
        return 1

    expected_hash = getattr(args, "expected_hash", None)
    if not expected_hash:
        print("ERROR: --expected-hash is required", file=sys.stderr)
        return 1

    try:
        new_session = record_evidence(
            session=session,
            role=args.role,
            artifact_sha256=args.artifact_sha256,
            artifact_ref=args.artifact_ref,
            recorded_by=args.recorded_by or "cli",
            orchestration_root=getattr(args, "orchestration_root", None) or _get_orchestration_root(),
            expected_state_hash=expected_hash,
            verdict=args.verdict,
            blockers=tuple(args.blockers.split(",")) if getattr(args, "blockers", None) else None,
            revision_reason=args.reason,
        )
    except StaleStateError as e:
        print(f"STALE: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(canonical_json(new_session))
    else:
        print(f"Evidence recorded for {args.role}")
        print(f"  New state hash: {new_session.session_state_hash}")
    return 0


def _cmd_record_blocked(args: argparse.Namespace) -> int:
    """record-blocked: Mark a stage as blocked."""
    session = _get_validated_session(args)
    if session is None:
        return 1

    expected_hash = getattr(args, "expected_hash", None)
    if not expected_hash:
        print("ERROR: --expected-hash is required", file=sys.stderr)
        return 1

    try:
        new_session = record_blocked(
            session=session,
            role=args.role,
            reason=args.reason,
            orchestration_root=getattr(args, "orchestration_root", None) or _get_orchestration_root(),
            expected_state_hash=expected_hash,
        )
    except StaleStateError as e:
        print(f"STALE: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(canonical_json(new_session))
    else:
        print(f"Stage {args.role} marked as blocked")
        print(f"  New state hash: {new_session.session_state_hash}")
    return 0


def _cmd_propose_action(args: argparse.Namespace) -> int:
    """propose-action: Create an inert dangerous-action proposal."""
    session = _get_validated_session(args)
    if session is None:
        return 1

    expected_hash = getattr(args, "expected_hash", None)
    if not expected_hash:
        print("ERROR: --expected-hash is required", file=sys.stderr)
        return 1

    # Parse argv from JSON
    try:
        argv = json.loads(args.argv_json)
        if not isinstance(argv, list):
            raise ValueError("argv must be a JSON list")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: Invalid --argv JSON: {e}", file=sys.stderr)
        return 1

    # Validate that argv doesn't contain dangerous patterns
    for item in argv:
        if not isinstance(item, str):
            print(f"ERROR: argv items must be strings, got {type(item).__name__}", file=sys.stderr)
            return 1

    try:
        proposal, new_session = create_proposal(
            session=session,
            action_type=args.action_type,
            argv=tuple(argv),
            session_state_hash=expected_hash,
            created_by=args.created_by or "cli",
        )
    except StaleStateError as e:
        print(f"STALE: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(canonical_json(new_session))
    else:
        print(f"Proposal created: {proposal.proposal_id}")
        print(f"  Action: {proposal.action_type}")
        print(f"  New state hash: {new_session.session_state_hash}")
    return 0


def _cmd_checkpoint(args: argparse.Namespace) -> int:
    """checkpoint: Record a human checkpoint (does NOT execute)."""
    session = _get_validated_session(args)
    if session is None:
        return 1

    expected_hash = getattr(args, "expected_hash", None)
    if not expected_hash:
        print("ERROR: --expected-hash is required", file=sys.stderr)
        return 1

    try:
        checkpoint, new_session = record_checkpoint(
            session=session,
            decision=args.decision,
            human_actor=args.human_actor,
            reason=args.reason,
            session_state_hash=expected_hash,
            proposal_id=getattr(args, "proposal_id", None),
            proposal_hash=getattr(args, "proposal_hash", None),
            orchestration_root=getattr(args, "orchestration_root", None) or _get_orchestration_root(),
        )
    except StaleStateError as e:
        print(f"STALE: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({
            "checkpoint_id": checkpoint.checkpoint_id,
            "decision": checkpoint.decision,
            "session_state_hash": new_session.session_state_hash,
        }))
    else:
        print(f"Checkpoint recorded: {checkpoint.checkpoint_id}")
        print(f"  Decision: {checkpoint.decision}")
        print(f"  New state hash: {new_session.session_state_hash}")
        print(f"  (Checkpoint records intent only — nothing was executed)")
    return 0


def _cmd_record_result(args: argparse.Namespace) -> int:
    """record-result: Record an external action result."""
    session = _get_validated_session(args)
    if session is None:
        return 1

    try:
        result, new_session = record_external_result(
            session=session,
            proposal_id=args.proposal_id,
            reported_status=args.status,
            recorded_by=args.recorded_by or "cli",
            evidence_refs=tuple(getattr(args, "evidence_path", [])),
            operator_notes=getattr(args, "operator_notes", None),
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(canonical_json(new_session))
    else:
        print(f"Result recorded: {result.result_id}")
        print(f"  Status: {result.reported_status} (operator-reported — not runtime verified)")
    return 0


def _cmd_show_session(args: argparse.Namespace) -> int:
    """show-session: Print session JSON."""
    session = _get_validated_session(args)
    if session is None:
        return 1
    print(canonical_json(session))
    return 0


def _cmd_list_sessions(args: argparse.Namespace) -> int:
    """list-sessions: List all session IDs."""
    orchestration_root = getattr(args, "orchestration_root", None) or _get_orchestration_root()
    sessions = list_sessions(orchestration_root)
    if args.json:
        print(json.dumps({"sessions": list(sessions), "count": len(sessions)}))
    else:
        if not sessions:
            print("No sessions found.")
            return 0
        print(f"Sessions ({len(sessions)}):")
        for sid in sessions:
            print(f"  {sid}")
    return 0


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _get_validated_session(args: argparse.Namespace) -> ManualOrchestrationSession | None:
    """Read and validate a session. Returns None (prints error) on failure."""
    orchestration_root = getattr(args, "orchestration_root", None) or _get_orchestration_root()
    if not args.session_id:
        print("ERROR: --session-id is required", file=sys.stderr)
        return None
    session = read_session(args.session_id, orchestration_root)
    if session is None:
        print(f"ERROR: Session not found: {args.session_id}", file=sys.stderr)
        return None
    # Verify state hash integrity
    computed = compute_session_state_hash(session)
    if computed != session.session_state_hash:
        print(f"ERROR: Session state hash mismatch (file may be corrupted)", file=sys.stderr)
        return None
    return session


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Main entrypoint for the manual orchestration CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m task_intake.manual_orchestration_cli",
        description="Ariadne — Manual Orchestration CLI (human-run only)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    # Helper to add common args to each subparser
    def _add_common_args(p):
        p.add_argument("--orchestration-root", help="Orchestration root directory")
        p.add_argument("--artifact-root", help="Artifact store root directory")

    # import-session
    p_import = sub.add_parser("import-session", help="Import a new orchestration packet")
    p_import.add_argument("--packet", required=True, help="Path to packet JSON file")
    _add_common_args(p_import)
    p_import.set_defaults(func=_cmd_import_session)

    # stage-status
    p_status = sub.add_parser("stage-status", help="Show session stage status")
    p_status.add_argument("--session-id", required=True)
    _add_common_args(p_status)
    p_status.set_defaults(func=_cmd_stage_status)

    # record-evidence
    p_ev = sub.add_parser("record-evidence", help="Record completed stage evidence")
    p_ev.add_argument("--session-id", required=True)
    p_ev.add_argument("--role", required=True, choices=("planner", "plan-review", "coder", "precommit-review"))
    p_ev.add_argument("--artifact-sha256", required=True)
    p_ev.add_argument("--artifact-ref", required=True)
    p_ev.add_argument("--verdict")
    p_ev.add_argument("--blockers")
    p_ev.add_argument("--reason")
    p_ev.add_argument("--recorded-by", default="cli")
    p_ev.add_argument("--expected-hash", required=True)
    _add_common_args(p_ev)
    p_ev.set_defaults(func=_cmd_record_evidence)

    # record-blocked
    p_bl = sub.add_parser("record-blocked", help="Mark a stage as blocked")
    p_bl.add_argument("--session-id", required=True)
    p_bl.add_argument("--role", required=True, choices=("planner", "plan-review", "coder", "precommit-review"))
    p_bl.add_argument("--reason", required=True)
    p_bl.add_argument("--expected-hash", required=True)
    _add_common_args(p_bl)
    p_bl.set_defaults(func=_cmd_record_blocked)

    # propose-action
    p_pr = sub.add_parser("propose-action", help="Create an inert action proposal")
    p_pr.add_argument("--session-id", required=True)
    p_pr.add_argument("--action-type", required=True)
    p_pr.add_argument("--argv-json", required=True, help="JSON list of argv strings")
    p_pr.add_argument("--created-by", default="cli")
    p_pr.add_argument("--expected-hash", required=True)
    _add_common_args(p_pr)
    p_pr.set_defaults(func=_cmd_propose_action)

    # checkpoint
    p_cp = sub.add_parser("checkpoint", help="Record a human checkpoint (no execution)")
    p_cp.add_argument("--session-id", required=True)
    p_cp.add_argument("--decision", required=True,
                      choices=("proceed_manually", "stop", "revise", "defer"))
    p_cp.add_argument("--human-actor", required=True)
    p_cp.add_argument("--reason", required=True)
    p_cp.add_argument("--proposal-id")
    p_cp.add_argument("--proposal-hash")
    p_cp.add_argument("--expected-hash", required=True)
    _add_common_args(p_cp)
    p_cp.set_defaults(func=_cmd_checkpoint)

    # record-result
    p_rr = sub.add_parser("record-result", help="Record external action result")
    p_rr.add_argument("--session-id", required=True)
    p_rr.add_argument("--proposal-id", required=True)
    p_rr.add_argument("--status", required=True, choices=("success", "failure", "result_unavailable"))
    p_rr.add_argument("--recorded-by", default="cli")
    p_rr.add_argument("--operator-notes")
    p_rr.add_argument("--evidence-path", action="append")
    _add_common_args(p_rr)
    p_rr.set_defaults(func=_cmd_record_result)

    # show-session
    p_sh = sub.add_parser("show-session", help="Print session JSON")
    p_sh.add_argument("--session-id", required=True)
    _add_common_args(p_sh)
    p_sh.set_defaults(func=_cmd_show_session)

    # list-sessions
    p_ls = sub.add_parser("list-sessions", help="List all session IDs")
    _add_common_args(p_ls)
    p_ls.set_defaults(func=_cmd_list_sessions)

    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

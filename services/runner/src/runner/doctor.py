"""
Platform-runner doctor command for Ariadne: validates that key runner modules are importable.

This module exposes:
- ``run_doctor()`` → returns 0 on success, 1 on failure
- ``main(argv)`` → argument-parsing entry point
- ``validate_proof_file(path)`` → validates a JSON proof ref file
- ``validate_handoff_file(path, ...)`` → validates a JSON handoff packet file
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .handoff_packet import (
    GateReadyHandoffPacket,
    validate_handoff_packet,
)
from .proof_capture import (
    ProofCaptureInput,
    capture_proof,
)
from .proof_ref import (
    ProofRef,
    validate_proof_ref,
)


EXPECTED_OUTPUT_LINES = (
    "platform-runner doctor",
    "runner import: ok",
    "patch models: ok",
    "patch safety: ok",
)


# ---------------------------------------------------------------------------
# Doctor checks
# ---------------------------------------------------------------------------


def run_doctor() -> int:
    """Run all doctor checks and print results to stdout.

    Returns 0 if all checks pass, 1 otherwise.
    """
    checks = (
        ("runner import", "runner"),
        ("patch models", "runner.models"),
        ("patch safety", "runner.patch"),
    )

    print(EXPECTED_OUTPUT_LINES[0])

    for label, module_name in checks:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            print(f"{label}: failed", file=sys.stderr)
            print(f"{module_name}: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1
        print(f"{label}: ok")

    return 0


# ---------------------------------------------------------------------------
# Validate proof file
# ---------------------------------------------------------------------------


def validate_proof_file(path: str) -> dict:
    """Read a JSON file, parse as ProofRef, and validate.

    Parameters
    ----------
    path:
        Path to a JSON file containing ProofRef data.

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "status": "error",
            "command": "validate proof",
            "result": None,
            "error": f"File not found: {path}",
        }
    except OSError as exc:
        return {
            "status": "error",
            "command": "validate proof",
            "result": None,
            "error": f"Error reading file: {exc}",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "command": "validate proof",
            "result": None,
            "error": f"Invalid JSON: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "command": "validate proof",
            "result": None,
            "error": "JSON root must be an object",
        }

    try:
        proof_ref = ProofRef(**data)
    except (TypeError, ValueError) as exc:
        return {
            "status": "error",
            "command": "validate proof",
            "result": None,
            "error": f"Invalid ProofRef data: {exc}",
        }

    # Determine current_product_state_ref from the proof ref itself
    # (the file may embed it; caller can override via CLI flag in future)
    current_product_state_ref = proof_ref.product_state_ref

    validation = validate_proof_ref(proof_ref, current_product_state_ref)

    return {
        "status": "ok",
        "command": "validate proof",
        "result": {
            "admissible": validation.admissible,
            "reason_codes": list(validation.reason_codes),
            "details": validation.details,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Validate handoff file
# ---------------------------------------------------------------------------


def validate_handoff_file(
    path: str,
    current_product_state_ref: str | None = None,
    admissible_ref_ids: list[str] | None = None,
) -> dict:
    """Read a JSON file, parse as GateReadyHandoffPacket, and validate.

    Parameters
    ----------
    path:
        Path to a JSON file containing GateReadyHandoffPacket data.
    current_product_state_ref:
        Override for the current product state ref. If None, uses the value
        from the packet itself (which means stale-state check is skipped).
    admissible_ref_ids:
        List of admissible proof ref IDs. If None, uses the packet's own
        proof_ref_ids (which means inadmissible-proof-ref check is skipped).

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "status": "error",
            "command": "validate handoff",
            "result": None,
            "error": f"File not found: {path}",
        }
    except OSError as exc:
        return {
            "status": "error",
            "command": "validate handoff",
            "result": None,
            "error": f"Error reading file: {exc}",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "command": "validate handoff",
            "result": None,
            "error": f"Invalid JSON: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "command": "validate handoff",
            "result": None,
            "error": "JSON root must be an object",
        }

    # Convert proof_ref_ids list to tuple if present
    if "proof_ref_ids" in data and isinstance(data["proof_ref_ids"], list):
        data["proof_ref_ids"] = tuple(data["proof_ref_ids"])

    # Convert metadata list of lists to tuple of tuples if present
    if "metadata" in data and isinstance(data["metadata"], list):
        data["metadata"] = tuple(tuple(pair) for pair in data["metadata"])

    try:
        packet = GateReadyHandoffPacket(**data)
    except (TypeError, ValueError) as exc:
        return {
            "status": "error",
            "command": "validate handoff",
            "result": None,
            "error": f"Invalid GateReadyHandoffPacket data: {exc}",
        }

    # Resolve validation parameters
    state_ref = current_product_state_ref if current_product_state_ref is not None else packet.product_state_ref
    ref_ids = frozenset(admissible_ref_ids) if admissible_ref_ids is not None else frozenset(packet.proof_ref_ids)

    validation = validate_handoff_packet(packet, state_ref, ref_ids)

    return {
        "status": "ok",
        "command": "validate handoff",
        "result": {
            "status": validation.status.value,
            "reason_codes": list(validation.reason_codes),
            "details": validation.details,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Capture proof file
# ---------------------------------------------------------------------------


def capture_proof_file(path: str, output_dir: str = ".") -> dict:
    """Read a JSON file, parse as ProofCaptureInput, and capture proof.

    Parameters
    ----------
    path:
        Path to a JSON file containing ProofCaptureInput data.
    output_dir:
        Directory where the artifact will be written.

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "status": "error",
            "command": "capture proof",
            "result": None,
            "error": f"File not found: {path}",
        }
    except OSError as exc:
        return {
            "status": "error",
            "command": "capture proof",
            "result": None,
            "error": f"Error reading file: {exc}",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "command": "capture proof",
            "result": None,
            "error": f"Invalid JSON: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "command": "capture proof",
            "result": None,
            "error": "JSON root must be an object",
        }

    # Convert tags list to frozenset if present
    if "tags" in data and isinstance(data["tags"], list):
        data["tags"] = frozenset(data["tags"])

    try:
        capture_input = ProofCaptureInput(**data)
    except (TypeError, ValueError) as exc:
        return {
            "status": "error",
            "command": "capture proof",
            "result": None,
            "error": f"Invalid ProofCaptureInput data: {exc}",
        }

    result = capture_proof(capture_input, output_dir=output_dir)

    return {
        "status": "ok",
        "command": "capture proof",
        "result": {
            "capture_status": result.status.value,
            "reason_codes": list(result.reason_codes),
            "artifact_path": result.artifact_path,
            "proof_ref_fields": result.proof_ref_fields,
            "details": result.details,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """Argument-based entry point for ``python -m runner``."""
    parser = argparse.ArgumentParser(
        prog="python -m runner",
        description="Platform runner command line utilities.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Existing doctor subcommand
    subparsers.add_parser("doctor", help="Run platform-runner runtime diagnostics.")

    # Validate subcommand group
    validate_parser = subparsers.add_parser("validate", help="Validate proof refs or handoff packets.")
    validate_subparsers = validate_parser.add_subparsers(dest="validate_command", required=True)

    # validate proof <path>
    proof_parser = validate_subparsers.add_parser("proof", help="Validate a proof ref JSON file.")
    proof_parser.add_argument("path", help="Path to the proof ref JSON file.")

    # validate handoff <path>
    handoff_parser = validate_subparsers.add_parser("handoff", help="Validate a handoff packet JSON file.")
    handoff_parser.add_argument("path", help="Path to the handoff packet JSON file.")
    handoff_parser.add_argument(
        "--current-product-state-ref",
        help="Override current product state ref for stale-state check.",
    )
    handoff_parser.add_argument(
        "--admissible-ref-ids",
        nargs="*",
        help="List of admissible proof ref IDs.",
    )

    # Capture subcommand group
    capture_parser = subparsers.add_parser("capture", help="Capture proof artifacts.")
    capture_subparsers = capture_parser.add_subparsers(dest="capture_command", required=True)

    # capture proof <path>
    capture_proof_parser = capture_subparsers.add_parser("proof", help="Capture a proof artifact from a JSON input file.")
    capture_proof_parser.add_argument("path", help="Path to the proof capture input JSON file.")
    capture_proof_parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where the artifact will be written (default: current directory).",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "doctor":
        return run_doctor()

    if args.command == "validate":
        if args.validate_command == "proof":
            result = validate_proof_file(args.path)
            _print_json_result(result)
            return 0 if result["status"] == "ok" and result["result"] and result["result"].get("admissible") else 1

        if args.validate_command == "handoff":
            result = validate_handoff_file(
                args.path,
                current_product_state_ref=args.current_product_state_ref,
                admissible_ref_ids=args.admissible_ref_ids,
            )
            _print_json_result(result)
            if result["status"] == "error":
                return 1
            if result["result"] and result["result"].get("status") == "not_gate_ready":
                return 1
            return 0

    if args.command == "capture":
        if args.capture_command == "proof":
            result = capture_proof_file(args.path, output_dir=args.output_dir)
            _print_json_result(result)
            if result["status"] == "error":
                return 1
            if result["result"] and result["result"].get("capture_status") == "rejected":
                return 1
            return 0

    parser.print_usage(sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Output helper
# ---------------------------------------------------------------------------


def _print_json_result(result: dict) -> None:
    """Print a JSON result dict to stdout with deterministic formatting."""
    print(json.dumps(result, sort_keys=True, indent=2))

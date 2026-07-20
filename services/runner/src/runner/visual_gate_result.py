"""
PR 0149 — Visual Gate Runtime Object.

Canonical path: ``<runs_root>/<run_id>/visual-gate-result.json``

Core principle:
    VisualGateResult is a runtime object for Visual Gate passage state.
    It is not human approval evidence.  It is not a diagram viewer.
    It does not enforce pipeline readiness.  ``status`` and
    ``human_review_required`` reflect current gate state without
    claiming human approval occurred.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "1"
_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")
_VISUAL_GATE_ID_RE = re.compile(r"^vg-[a-zA-Z0-9_\-]+-[0-9a-f]{16}$")
_DIAGRAM_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")
_DESCRIPTOR_KEY_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")
_PROFILE_DESCRIPTOR_KEY_RE = re.compile(r"^profile_descriptor_key:([a-zA-Z0-9_\-]+)$")
_RUN_RELATIVE_RE = re.compile(r"^run-relative:(.+)$")
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

_VALID_STATUSES = frozenset({"pending", "ready_needs_review", "passed", "failed"})
_VALID_DIAGRAM_TYPES = frozenset({"requirement", "state", "sequence"})

_MAX_DIAGRAMS = 20
_MAX_EVIDENCE_REFS = 50
_MAX_REASON_CODES = 20
_MAX_WARNINGS = 10
_MAX_REF_LENGTH = 500
_MAX_REASON_CODE_LENGTH = 100
_MAX_SOURCE_LENGTH = 100
_MAX_WARNING_LENGTH = 500
_MAX_PHASE_ID_LENGTH = 128
_MAX_VISUAL_GATE_ID_LENGTH = 200
_MAX_FILE_BYTES = 1_000_000  # 1 MB for the stored file


# ---------------------------------------------------------------------------
# Canonical JSON helpers
# ---------------------------------------------------------------------------


def _build_canonical_dict(
    schema_version: str,
    visual_gate_id: str,
    run_id: str,
    phase_id: Optional[str],
    required_diagrams: list[dict],
    status: str,
    human_review_required: bool,
    evidence_refs: Optional[list[str]],
    reason_codes: Optional[list[str]],
    created_at: str,
    source: Optional[str],
    warnings: Optional[list[str]],
) -> dict:
    """Build canonical dict for hashing (excludes visual_gate_sha256)."""
    canonical: dict[str, Any] = {
        "created_at": created_at,
        "human_review_required": human_review_required,
        "required_diagrams": sorted(required_diagrams, key=lambda d: d.get("diagram_id", "")),
        "run_id": run_id,
        "schema_version": schema_version,
        "status": status,
    }

    if phase_id is not None:
        canonical["phase_id"] = phase_id
    if evidence_refs:
        canonical["evidence_refs"] = sorted(set(evidence_refs))
    if reason_codes:
        canonical["reason_codes"] = sorted(reason_codes)
    if source:
        canonical["source"] = source
    if warnings:
        canonical["warnings"] = sorted(warnings)

    return canonical


def canonical_json(data: dict) -> str:
    """Deterministic JSON from a visual gate result dict."""
    return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------


def compute_visual_gate_sha256(data: dict) -> str:
    """Compute visual_gate_sha256 from canonical JSON (excluding self-field)."""
    canonical = _build_canonical_dict(
        schema_version=data.get("schema_version", ""),
        visual_gate_id=data.get("visual_gate_id", ""),
        run_id=data.get("run_id", ""),
        phase_id=data.get("phase_id"),
        required_diagrams=data.get("required_diagrams", []),
        status=data.get("status", ""),
        human_review_required=data.get("human_review_required", False),
        evidence_refs=data.get("evidence_refs"),
        reason_codes=data.get("reason_codes"),
        created_at=data.get("created_at", ""),
        source=data.get("source"),
        warnings=data.get("warnings"),
    )
    content = canonical_json(canonical)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_string(value: Any, field: str, max_len: int, codes: list[str], pattern: Optional[re.Pattern] = None) -> None:
    if not isinstance(value, str):
        codes.append(f"missing_field:{field}")
        return
    if len(value) > max_len:
        codes.append(f"field_too_long:{field}")
        return
    if pattern is not None and not pattern.match(value):
        codes.append(f"invalid_field_format:{field}")


def _validate_required_diagram(diagram: dict, codes: list[str]) -> None:
    """Validate a single required diagram entry."""
    if not isinstance(diagram, dict):
        codes.append("invalid_required_diagram")
        return

    did = diagram.get("diagram_id", "")
    _validate_string(did, "diagram_id", 100, codes, _DIAGRAM_ID_RE)
    dtype = diagram.get("diagram_type", "")
    _validate_string(dtype, "diagram_type", 100, codes)
    if dtype and dtype not in _VALID_DIAGRAM_TYPES:
        codes.append(f"unsupported_diagram_type:{dtype}")
    dref = diagram.get("descriptor_ref", "")
    _validate_string(dref, "descriptor_ref", 500, codes)
    if dref:
        m = _PROFILE_DESCRIPTOR_KEY_RE.match(dref)
        if not m:
            codes.append(f"invalid_descriptor_ref:{dref}")
        else:
            key = m.group(1)
            if not key:
                codes.append(f"invalid_descriptor_ref:{dref}")
    if not isinstance(diagram.get("required"), bool):
        codes.append("missing_field:required")


def _validate_evidence_ref(ref: str, codes: list[str]) -> None:
    """Validate a single evidence reference."""
    if not isinstance(ref, str) or not ref:
        codes.append("invalid_evidence_ref:empty")
        return
    if len(ref) > _MAX_REF_LENGTH:
        codes.append(f"too_long_evidence_ref:{len(ref)}")
        return

    # Check for profile_descriptor_key:
    if ref.startswith("profile_descriptor_key:"):
        m = _PROFILE_DESCRIPTOR_KEY_RE.match(ref)
        if not m or not m.group(1):
            codes.append(f"invalid_evidence_ref:{ref}")
        return

    # Use existing controlled reference validation for run-relative: and sha256:
    from runner.run_profile import validate_reference
    validate_reference(ref, codes)


def validate_visual_gate_result(data: dict) -> list[str]:
    """Validate a VisualGateResult dict. Returns list of error codes."""
    codes: list[str] = []

    # schema_version
    sv = data.get("schema_version", "")
    _validate_string(sv, "schema_version", 10, codes)
    if sv and sv != _SCHEMA_VERSION:
        codes.append(f"unsupported_schema_version:{sv}")

    # visual_gate_id
    vgid = data.get("visual_gate_id", "")
    _validate_string(vgid, "visual_gate_id", _MAX_VISUAL_GATE_ID_LENGTH, codes, _VISUAL_GATE_ID_RE)

    # run_id
    rid = data.get("run_id", "")
    _validate_string(rid, "run_id", 128, codes, _RUN_ID_RE)

    # phase_id
    pid = data.get("phase_id")
    if pid is not None:
        _validate_string(pid, "phase_id", _MAX_PHASE_ID_LENGTH, codes)

    # status
    status = data.get("status", "")
    _validate_string(status, "status", 30, codes)
    if status and status not in _VALID_STATUSES:
        codes.append(f"invalid_status:{status}")

    # human_review_required consistency
    hrr = data.get("human_review_required")
    if not isinstance(hrr, bool):
        codes.append("missing_field:human_review_required")
    elif status == "ready_needs_review" and hrr is False:
        codes.append(f"human_review_required_mismatch:expected:true:got:false")
    elif status in ("pending", "passed", "failed") and hrr is True:
        codes.append(f"human_review_required_mismatch:expected:false:got:true")

    # required_diagrams
    diags = data.get("required_diagrams")
    if not isinstance(diags, list):
        codes.append("missing_field:required_diagrams")
    elif len(diags) > _MAX_DIAGRAMS:
        codes.append(f"too_many_required_diagrams:{len(diags)}")
    else:
        seen_ids: set[str] = set()
        for d in diags:
            _validate_required_diagram(d, codes)
            did = d.get("diagram_id", "") if isinstance(d, dict) else ""
            if did and did in seen_ids:
                codes.append(f"duplicate_diagram_id:{did}")
            seen_ids.add(did)

    # evidence_refs
    refs = data.get("evidence_refs")
    if refs is not None:
        if not isinstance(refs, list):
            codes.append("invalid_evidence_refs_type")
        elif len(refs) > _MAX_EVIDENCE_REFS:
            codes.append(f"too_many_evidence_refs:{len(refs)}")
        else:
            for r in refs:
                _validate_evidence_ref(r, codes)

    # reason_codes
    rc = data.get("reason_codes")
    if rc is not None:
        if not isinstance(rc, list):
            codes.append("invalid_reason_codes_type")
        elif len(rc) > _MAX_REASON_CODES:
            codes.append(f"too_many_reason_codes:{len(rc)}")
        else:
            for r in rc:
                if not isinstance(r, str) or len(r) > _MAX_REASON_CODE_LENGTH:
                    codes.append("invalid_reason_code")

    # created_at
    ca = data.get("created_at", "")
    _validate_string(ca, "created_at", 30, codes)
    if ca and not _is_valid_iso8601(ca):
        codes.append("invalid_created_at")

    # source
    src = data.get("source")
    if src is not None:
        _validate_string(src, "source", _MAX_SOURCE_LENGTH, codes)

    # warnings
    wns = data.get("warnings")
    if wns is not None:
        if not isinstance(wns, list):
            codes.append("invalid_warnings_type")
        elif len(wns) > _MAX_WARNINGS:
            codes.append(f"too_many_warnings:{len(wns)}")
        else:
            for w in wns:
                if not isinstance(w, str) or len(w) > _MAX_WARNING_LENGTH:
                    codes.append("invalid_warning")

    return codes


_ISO8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")


def _is_valid_iso8601(s: str) -> bool:
    """Check if string is valid ISO 8601 UTC or with timezone offset."""
    return bool(_ISO8601_RE.match(s))


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


def create_visual_gate_result(
    runs_root: str,
    run_id: str,
    status: str,
    human_review_required: bool,
    required_diagrams: list[dict],
    phase_id: Optional[str] = None,
    evidence_refs: Optional[list[str]] = None,
    reason_codes: Optional[list[str]] = None,
    source: Optional[str] = None,
    warnings: Optional[list[str]] = None,
    clock_provider: Optional[callable] = None,
) -> dict:
    """Create and persist a VisualGateResult.

    Parameters
    ----------
    runs_root:
        The runs root directory.
    run_id:
        Validated run ID.
    status:
        One of pending, ready_needs_review, passed, failed.
    human_review_required:
        Whether human review is required (must be consistent with status).
    required_diagrams:
        List of RequiredDiagramEntry dicts.
    phase_id:
        Optional phase identifier.
    evidence_refs:
        Optional controlled reference list.
    reason_codes:
        Optional reason codes.
    source:
        Optional producer identity.
    warnings:
        Optional warning list.
    clock_provider:
        Callable returning ISO 8601 UTC timestamp. Default: current UTC.

    Returns
    -------
    dict with keys: ok, error, visual_gate_sha256, visual_gate_id, ...
    """
    clock_provider = clock_provider or (lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    created_at = clock_provider()

    if not _RUN_ID_RE.match(run_id):
        return {"ok": False, "error": "invalid_run_id"}

    run_dir = os.path.join(runs_root, run_id)
    if not os.path.isdir(run_dir):
        return {"ok": False, "error": "run_not_found"}

    # Check if file already exists
    target_path = os.path.join(run_dir, "visual-gate-result.json")
    if os.path.exists(target_path):
        return {"ok": False, "error": "already_exists"}

    # Build initial data (without hash)
    data: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "run_id": run_id,
        "status": status,
        "human_review_required": human_review_required,
        "required_diagrams": required_diagrams,
        "created_at": created_at,
    }
    if phase_id is not None:
        data["phase_id"] = phase_id
    if evidence_refs:
        data["evidence_refs"] = evidence_refs
    if reason_codes:
        data["reason_codes"] = reason_codes
    if source:
        data["source"] = source
    if warnings:
        data["warnings"] = warnings

    # Compute hash
    vg_hash = compute_visual_gate_sha256(data)

    # Generate visual_gate_id (uses hash, so must be after hash computation)
    data["visual_gate_id"] = f"vg-{run_id}-{vg_hash[:16]}"

    # Set hash
    data["visual_gate_sha256"] = vg_hash

    # Validate
    codes = validate_visual_gate_result(data)
    if codes:
        return {"ok": False, "error": "validation_failed", "details": codes}

    # Atomic write
    tmp_path = target_path + ".tmp"
    try:
        content = canonical_json(data)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)
    except OSError as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return {"ok": False, "error": f"write_error:{e}"}

    # Readback verify
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            stored = json.load(f)
        stored_sha = stored.get("visual_gate_sha256", "")
        readback_ok = stored_sha == vg_hash
    except (OSError, json.JSONDecodeError):
        readback_ok = False

    if not readback_ok:
        return {
            "ok": False,
            "error": "readback_hash_mismatch",
            "visual_gate_sha256": vg_hash,
        }

    return {
        "ok": True,
        "visual_gate_sha256": vg_hash,
        "visual_gate_id": data["visual_gate_id"],
    }


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def read_visual_gate_result(
    runs_root: str,
    run_id: str,
) -> dict:
    """Read and validate a VisualGateResult.

    Returns dict with keys:
      - ok: bool
      - error: str or None
      - run_id: str
      - visual_gate_result_exists: bool
      - visual_gate_sha256: str or None
      - hash_match: bool or None
      - visual_gate_result: dict or None
    """
    if not _RUN_ID_RE.match(run_id):
        return {
            "ok": False,
            "error": "invalid_run_id",
            "run_id": run_id,
            "visual_gate_result_exists": False,
            "visual_gate_sha256": None,
            "hash_match": None,
            "visual_gate_result": None,
        }

    target_path = os.path.join(runs_root, run_id, "visual-gate-result.json")
    if not os.path.isfile(target_path):
        return {
            "ok": False,
            "error": "not_found",
            "run_id": run_id,
            "visual_gate_result_exists": False,
            "visual_gate_sha256": None,
            "hash_match": None,
            "visual_gate_result": None,
        }

    # Size check
    try:
        if os.path.getsize(target_path) > _MAX_FILE_BYTES:
            return {
                "ok": False,
                "error": "malformed",
                "run_id": run_id,
                "visual_gate_result_exists": True,
                "visual_gate_sha256": None,
                "hash_match": None,
                "visual_gate_result": None,
            }
    except OSError:
        pass

    # Read JSON
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error": "malformed",
            "run_id": run_id,
            "visual_gate_result_exists": True,
            "visual_gate_sha256": None,
            "hash_match": None,
            "visual_gate_result": None,
        }
    except OSError as e:
        return {
            "ok": False,
            "error": "read_error",
            "run_id": run_id,
            "visual_gate_result_exists": True,
            "visual_gate_sha256": None,
            "hash_match": None,
            "visual_gate_result": None,
        }

    # Check schema version
    sv = data.get("schema_version", "")
    if sv != _SCHEMA_VERSION:
        return {
            "ok": False,
            "error": "unsupported_schema_version",
            "run_id": run_id,
            "visual_gate_result_exists": True,
            "visual_gate_sha256": None,
            "hash_match": None,
            "visual_gate_result": None,
        }

    # Validate fields
    codes = validate_visual_gate_result(data)
    if codes:
        return {
            "ok": False,
            "error": "validation_failed",
            "run_id": run_id,
            "visual_gate_result_exists": True,
            "visual_gate_sha256": None,
            "hash_match": None,
            "visual_gate_result": None,
            "details": codes,
        }

    # Hash check
    stored_sha = data.get("visual_gate_sha256", "")
    computed_sha = compute_visual_gate_sha256(data)
    hash_match = stored_sha == computed_sha

    if not hash_match:
        return {
            "ok": True,
            "error": "hash_mismatch",
            "run_id": run_id,
            "visual_gate_result_exists": True,
            "visual_gate_sha256": computed_sha,
            "hash_match": False,
            "visual_gate_result": data,
        }

    return {
        "ok": True,
        "error": None,
        "run_id": run_id,
        "visual_gate_result_exists": True,
        "visual_gate_sha256": stored_sha,
        "hash_match": True,
        "visual_gate_result": data,
    }

"""
Verdict Parser for Ariadne — third executable Production Line PR.

Parses review artifacts (plan-review and precommit-review), extracts
verdict/blockers/warnings/evidence/normalized fields, and returns
deterministic control decisions (``continue``, ``continue_with_warning``,
``stop``, and optional ``retry_candidate`` recommendation) for the future
PR 0127 Pipeline Runner.

Core principle:
    Agent output is not evidence.  Runtime/file-captured review artifact
    proof is evidence.  The substrate exists to run the loop — the human
    must stop being the orchestrator.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
import re
from typing import Any, Optional


# ---------------------------------------------------------------------------
# VerdictDecisionStatus — control decision status
# ---------------------------------------------------------------------------


class VerdictDecisionStatus(str):
    """Control decision status values."""

    CONTINUE = "continue"
    CONTINUE_WITH_WARNING = "continue_with_warning"
    STOP = "stop"
    INVALID = "invalid"


# ---------------------------------------------------------------------------
# VerdictParserRequest — input dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class VerdictParserRequest:
    """Input parameters for parsing a review artifact."""

    artifact_path: str
    artifact_text: Optional[str] = None
    expected_review_type: Optional[str] = None
    expected_pr_id: Optional[str] = None
    schema_path: Optional[str] = None
    strict: bool = False


# ---------------------------------------------------------------------------
# ParsedReviewArtifact — parsed artifact data
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ParsedReviewArtifact:
    """Parsed review artifact data."""

    review_type: str
    pr_id: Optional[str]
    raw_verdict: str
    normalized_verdict: str
    has_blockers: bool
    blockers: tuple[tuple[str, str, str], ...]  # (id, description, severity)
    warnings: tuple[tuple[str, str], ...]  # (id, description)
    validation_summary: tuple[dict[str, Any], ...]
    evidence_ledger_summary: tuple[dict[str, str], ...]
    files_read: tuple[str, ...]
    files_written: tuple[str, ...]
    boundary_confirmations: tuple[str, ...]
    checks: dict[str, str]
    artifact_hash: str
    artifact_line_count: int
    schema_version: Optional[str]


# ---------------------------------------------------------------------------
# VerdictDecision — control decision
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class VerdictDecision:
    """Control decision derived from a parsed review artifact."""

    next_action: str
    normalized_verdict: str
    has_blockers: bool
    reason_codes: tuple[str, ...]
    is_retry_candidate: bool
    retry_reason: Optional[str]
    human_required: bool
    details: Optional[str]
    parsed_artifact: Optional[ParsedReviewArtifact]


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_ARTIFACT_READ_FAILURE = "artifact_read_failure"
REASON_YAML_PARSE_FAILURE = "yaml_parse_failure"
REASON_MISSING_VERDICT = "missing_verdict"
REASON_UNKNOWN_VERDICT = "unknown_verdict"
REASON_STRICT_TYPE_MISMATCH = "strict_type_mismatch"
REASON_STRICT_PR_MISMATCH = "strict_pr_mismatch"
REASON_BLOCKER_SAFETY_VIOLATION = "blocker_safety_violation"
REASON_BLOCKERS_PRESENT = "blockers_present"

# ---------------------------------------------------------------------------
# Safety violation patterns
# ---------------------------------------------------------------------------

_SAFETY_VIOLATION_PATTERNS: tuple[str, ...] = (
    "git add",
    "git commit",
    "git push",
    "git checkout",
    "git switch",
    "git merge",
    "git rebase",
    "git reset",
    "git clean",
    "git tag",
    "gh pr create",
    "gh release",
    "docker",
    "docker compose",
    "subprocess.run",
    "os.system",
    "pip install",
    "python -m pip install",
    "hidden reasoning",
    "chain-of-thought",
    "provider call",
    "network call",
)

# ---------------------------------------------------------------------------
# Normalized verdict mapping
# ---------------------------------------------------------------------------

_PLAN_REVIEW_VERDICT_MAP: dict[str, str] = {
    "approve": "pass",
    "warning": "warning",
    "block": "block",
}

_PRECOMMIT_REVIEW_VERDICT_MAP: dict[str, str] = {
    "pass": "pass",
    "warning": "warning",
    "block": "block",
}


# ---------------------------------------------------------------------------
# Normalize verdict
# ---------------------------------------------------------------------------


def _normalize_verdict(
    raw_verdict: str,
    review_type: str,
) -> str:
    """Normalize a raw verdict string.

    Parameters
    ----------
    raw_verdict:
        Raw verdict from the review artifact.
    review_type:
        Review type (``"plan-review"`` or ``"precommit-review"``).

    Returns
    -------
    str
        Normalized verdict: ``"pass"``, ``"warning"``, ``"block"``, or
        ``"invalid"``.
    """
    if not raw_verdict:
        return "invalid"

    raw_lower = raw_verdict.strip().lower()

    if review_type == "plan-review":
        return _PLAN_REVIEW_VERDICT_MAP.get(raw_lower, "invalid")
    elif review_type == "precommit-review":
        return _PRECOMMIT_REVIEW_VERDICT_MAP.get(raw_lower, "invalid")
    else:
        return "invalid"


# ---------------------------------------------------------------------------
# Check retry candidate
# ---------------------------------------------------------------------------


def _check_retry_candidate(
    blockers: tuple[tuple[str, str, str], ...],
    boundary_confirmations: tuple[str, ...],
) -> tuple[bool, Optional[str]]:
    """Check if a retry is viable.

    Parameters
    ----------
    blockers:
        List of (id, description, severity) tuples.
    boundary_confirmations:
        List of boundary confirmation strings.

    Returns
    -------
    tuple[bool, Optional[str]]
        ``(is_retry_candidate, retry_reason)``.
    """
    # Check for critical severity blockers
    for _, _, severity in blockers:
        if severity == "critical":
            return False, "Critical severity blocker present"

    # Check for safety violation patterns in blocker descriptions
    for _, description, _ in blockers:
        desc_lower = description.lower()
        for pattern in _SAFETY_VIOLATION_PATTERNS:
            if pattern in desc_lower:
                return False, f"Safety violation pattern in blocker: {pattern}"

    # Check for safety violation patterns in boundary confirmations
    for bc in boundary_confirmations:
        bc_lower = bc.lower()
        for pattern in _SAFETY_VIOLATION_PATTERNS:
            if pattern in bc_lower:
                return False, f"Safety violation pattern in boundary confirmation: {pattern}"

    # If blockers exist and no safety violation, retry is viable
    if blockers:
        return True, "Fixable blocker class — retry recommended"

    return False, None


# ---------------------------------------------------------------------------
# Line-oriented YAML fallback parser
# ---------------------------------------------------------------------------


def _line_parse_artifact(text: str) -> dict[str, Any]:
    """Parse a review artifact using line-oriented fallback.

    Extracts known top-level fields from YAML-like text without a YAML
    parser.  Handles simple key: value and list entries.

    Parameters
    ----------
    text:
        Raw artifact text.

    Returns
    -------
    dict
        Parsed fields.
    """
    result: dict[str, Any] = {
        "schema_version": None,
        "pr_id": None,
        "review_type": None,
        "verdict": None,
        "blockers": [],
        "warnings": [],
        "validation": [],
        "evidence_ledger": [],
        "files_checked": [],
        "boundary_confirmations": [],
        "checks": {},
    }

    lines = text.split("\n")
    current_section: Optional[str] = None
    current_item: dict[str, str] = {}

    for line in lines:
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith("#"):
            continue

        # Detect section headers (top-level keys followed by colon, no leading whitespace)
        if not line.startswith(" ") and not stripped.startswith("-"):
            section_match = re.match(r"^([a-zA-Z_]+):\s*(.*)", stripped)
            if section_match:
                key = section_match.group(1)
                value = section_match.group(2).strip()

                if key in ("schema_version", "pr_id", "review_type", "verdict"):
                    # Strip surrounding quotes
                    clean_value = value.strip('"').strip("'").strip()
                    result[key] = clean_value
                    current_section = None
                elif key in ("blockers", "warnings", "validation", "evidence_ledger", "files_checked", "boundary_confirmations"):
                    current_section = key
                elif key == "checks":
                    current_section = "checks"
                else:
                    current_section = None
                continue

        # Detect list items
        if stripped.startswith("- "):
            item_text = stripped[2:].strip()

            if current_section == "blockers":
                current_item = {"id": "", "description": "", "severity": "medium"}
                # Try to parse inline sub-fields
                sub_match = re.match(r"^([a-zA-Z_]+):\s*(.*)", item_text)
                if sub_match:
                    sub_key = sub_match.group(1)
                    sub_value = sub_match.group(2).strip().strip('"').strip("'")
                    current_item[sub_key] = sub_value
                else:
                    current_item["description"] = item_text
                result["blockers"].append(current_item)
            elif current_section == "warnings":
                current_item = {"id": "", "description": ""}
                sub_match = re.match(r"^([a-zA-Z_]+):\s*(.*)", item_text)
                if sub_match:
                    sub_key = sub_match.group(1)
                    sub_value = sub_match.group(2).strip().strip('"').strip("'")
                    current_item[sub_key] = sub_value
                else:
                    current_item["description"] = item_text
                result["warnings"].append(current_item)
            elif current_section == "files_checked":
                result["files_checked"].append(item_text.strip('"').strip("'"))
            elif current_section == "boundary_confirmations":
                result["boundary_confirmations"].append(item_text.strip('"').strip("'"))
            elif current_section == "validation":
                current_item = {"command": item_text, "result": "unknown", "exit_code": None, "evidence": ""}
                result["validation"].append(current_item)
            elif current_section == "evidence_ledger":
                current_item = {"claim": item_text, "evidence_source": "", "result": "unknown"}
                result["evidence_ledger"].append(current_item)
            continue

        # Detect sub-fields of current item (use raw line, not stripped)
        if current_section == "checks":
            sub_match = re.match(r"^\s+([a-zA-Z_]+):\s*(.*)", line)
            if sub_match:
                sub_key = sub_match.group(1)
                sub_value = sub_match.group(2).strip().strip('"').strip("'")
                result["checks"][sub_key] = sub_value
            continue

        if current_section in ("blockers", "warnings", "validation", "evidence_ledger"):
            sub_match = re.match(r"^\s+([a-zA-Z_]+):\s*(.*)", line)
            if sub_match:
                sub_key = sub_match.group(1)
                sub_value = sub_match.group(2).strip().strip('"').strip("'")
                if current_item:
                    current_item[sub_key] = sub_value

    return result


# ---------------------------------------------------------------------------
# Parse review artifact
# ---------------------------------------------------------------------------


def parse_review_artifact(
    request: VerdictParserRequest,
) -> Optional[ParsedReviewArtifact]:
    """Parse a review artifact file.

    Parameters
    ----------
    request:
        Input parameters including artifact path, optional text override,
        optional expected review type, optional expected PR ID, optional
        schema path, and strict mode flag.

    Returns
    -------
    ParsedReviewArtifact or None
        Parsed artifact data, or ``None`` on file read failure.
    """
    # 1. Read artifact text
    if request.artifact_text is not None:
        text = request.artifact_text
    else:
        if not os.path.exists(request.artifact_path):
            return None
        try:
            with open(request.artifact_path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            return None

    # 2. Compute artifact hash and line count
    artifact_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    artifact_line_count = len(text.split("\n"))

    # 3. Try YAML parsing, fall back to line-oriented
    data: dict[str, Any] = {}
    yaml_success = False

    try:
        import yaml
        parsed = yaml.safe_load(text)
        if isinstance(parsed, dict):
            data = parsed
            yaml_success = True
    except ImportError:
        pass
    except Exception:
        pass

    if not yaml_success:
        data = _line_parse_artifact(text)

    # 4. Extract fields
    schema_version = data.get("schema_version")
    pr_id = data.get("pr_id")
    review_type = data.get("review_type", "")
    raw_verdict = data.get("verdict", "")

    # 5. Strict mode checks
    if request.strict:
        if request.expected_review_type is not None and review_type != request.expected_review_type:
            return None
        if request.expected_pr_id is not None and pr_id != request.expected_pr_id:
            return None

    # 6. Normalize verdict
    normalized_verdict = _normalize_verdict(raw_verdict, review_type)

    # 7. Extract blockers
    blockers_raw = data.get("blockers", [])
    blockers: list[tuple[str, str, str]] = []
    for b in blockers_raw:
        if isinstance(b, dict):
            bid = b.get("id", "")
            desc = b.get("description", "")
            severity = b.get("severity", "medium")
            blockers.append((bid, desc, severity))
        elif isinstance(b, str):
            blockers.append(("", b, "medium"))

    has_blockers = len(blockers) > 0

    # 8. Extract warnings
    warnings_raw = data.get("warnings", [])
    warnings: list[tuple[str, str]] = []
    for w in warnings_raw:
        if isinstance(w, dict):
            wid = w.get("id", "")
            desc = w.get("description", "")
            warnings.append((wid, desc))
        elif isinstance(w, str):
            warnings.append(("", w))

    # 9. Extract validation
    validation_raw = data.get("validation", [])
    validation_summary: list[dict[str, Any]] = []
    for v in validation_raw:
        if isinstance(v, dict):
            validation_summary.append({
                "command": v.get("command", ""),
                "result": v.get("result", "unknown"),
                "exit_code": v.get("exit_code"),
                "evidence": v.get("evidence", ""),
            })

    # 10. Extract evidence ledger
    ledger_raw = data.get("evidence_ledger", [])
    evidence_ledger_summary: list[dict[str, str]] = []
    for e in ledger_raw:
        if isinstance(e, dict):
            evidence_ledger_summary.append({
                "claim": e.get("claim", ""),
                "evidence_source": e.get("evidence_source", ""),
                "result": e.get("result", "unknown"),
            })

    # 11. Extract files_checked
    files_checked_raw = data.get("files_checked", [])
    files_checked: list[str] = [str(f) for f in files_checked_raw if isinstance(f, str)]

    # 12. Extract files_written (from context_used or top-level)
    files_written: list[str] = []
    context_used = data.get("context_used", {})
    if isinstance(context_used, dict):
        fw = context_used.get("files_modified", [])
        if isinstance(fw, list):
            files_written = [str(f) for f in fw if isinstance(f, str)]

    # 13. Extract boundary confirmations
    boundary_raw = data.get("boundary_confirmations", [])
    boundary_confirmations: list[str] = [str(b) for b in boundary_raw if isinstance(b, str)]

    # 14. Extract checks
    checks_raw = data.get("checks", {})
    checks: dict[str, str] = {}
    if isinstance(checks_raw, dict):
        for k, v in checks_raw.items():
            checks[str(k)] = str(v)

    return ParsedReviewArtifact(
        review_type=review_type,
        pr_id=pr_id,
        raw_verdict=raw_verdict,
        normalized_verdict=normalized_verdict,
        has_blockers=has_blockers,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        validation_summary=tuple(validation_summary),
        evidence_ledger_summary=tuple(evidence_ledger_summary),
        files_read=tuple(files_checked),
        files_written=tuple(files_written),
        boundary_confirmations=tuple(boundary_confirmations),
        checks=checks,
        artifact_hash=artifact_hash,
        artifact_line_count=artifact_line_count,
        schema_version=schema_version,
    )


# ---------------------------------------------------------------------------
# Decide next action
# ---------------------------------------------------------------------------


def decide_next_action(
    parsed: ParsedReviewArtifact,
) -> VerdictDecision:
    """Derive a control decision from a parsed review artifact.

    Parameters
    ----------
    parsed:
        Parsed review artifact data.

    Returns
    -------
    VerdictDecision
        Control decision with ``next_action``, ``is_retry_candidate``,
        ``human_required``, and supporting fields.
    """
    codes: list[str] = []

    # 1. Check for invalid normalized verdict
    if parsed.normalized_verdict == "invalid":
        if not parsed.raw_verdict:
            codes.append(REASON_MISSING_VERDICT)
        else:
            codes.append(REASON_UNKNOWN_VERDICT)
        return VerdictDecision(
            next_action=VerdictDecisionStatus.STOP,
            normalized_verdict=parsed.normalized_verdict,
            has_blockers=parsed.has_blockers,
            reason_codes=tuple(codes),
            is_retry_candidate=False,
            retry_reason=None,
            human_required=False,
            details="Invalid verdict: " + (parsed.raw_verdict or "missing"),
            parsed_artifact=parsed,
        )

    # 2. Check for blockers (regardless of verdict)
    if parsed.has_blockers:
        codes.append(REASON_BLOCKERS_PRESENT)

        # Check for safety violations in blockers
        is_retry, retry_reason = _check_retry_candidate(
            parsed.blockers,
            parsed.boundary_confirmations,
        )

        if not is_retry:
            codes.append(REASON_BLOCKER_SAFETY_VIOLATION)

        return VerdictDecision(
            next_action=VerdictDecisionStatus.STOP,
            normalized_verdict=parsed.normalized_verdict,
            has_blockers=True,
            reason_codes=tuple(codes),
            is_retry_candidate=is_retry,
            retry_reason=retry_reason,
            human_required=not is_retry,
            details=f"Blockers present: {len(parsed.blockers)} blocker(s)",
            parsed_artifact=parsed,
        )

    # 3. No blockers — determine action from normalized verdict
    if parsed.normalized_verdict == "pass":
        return VerdictDecision(
            next_action=VerdictDecisionStatus.CONTINUE,
            normalized_verdict=parsed.normalized_verdict,
            has_blockers=False,
            reason_codes=(),
            is_retry_candidate=False,
            retry_reason=None,
            human_required=False,
            details=None,
            parsed_artifact=parsed,
        )

    if parsed.normalized_verdict == "warning":
        return VerdictDecision(
            next_action=VerdictDecisionStatus.CONTINUE_WITH_WARNING,
            normalized_verdict=parsed.normalized_verdict,
            has_blockers=False,
            reason_codes=(),
            is_retry_candidate=False,
            retry_reason=None,
            human_required=False,
            details=None,
            parsed_artifact=parsed,
        )

    # 4. Fallback — stop
    codes.append(REASON_UNKNOWN_VERDICT)
    return VerdictDecision(
        next_action=VerdictDecisionStatus.STOP,
        normalized_verdict=parsed.normalized_verdict,
        has_blockers=parsed.has_blockers,
        reason_codes=tuple(codes),
        is_retry_candidate=False,
        retry_reason=None,
        human_required=False,
        details="Unknown normalized verdict: " + parsed.normalized_verdict,
        parsed_artifact=parsed,
    )

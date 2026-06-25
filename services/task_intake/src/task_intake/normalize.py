"""
Deterministic task intake normalization — pure function mock.

Accepts raw task input and returns a normalized Ariadne task-intake structure.

No model calls, no repository scanning, no Git inspection, no persistence.
"""

from __future__ import annotations

from typing import Any

from task_intake.models import _make_task_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_text(text: str) -> str:
    """Trim whitespace and collapse multiple spaces."""
    import re as _re
    return _re.sub(r"\s+", " ", text.strip())


# ---------------------------------------------------------------------------
# Inference heuristics
# ---------------------------------------------------------------------------

_FEATURE_WORDS = frozenset({"add", "implement", "feature", "create", "new"})
_REFACTOR_WORDS = frozenset({"refactor", "cleanup", "reorganize", "simplify"})
_REVIEW_WORDS = frozenset({"review", "audit", "check", "inspect"})
_TEST_WORDS = frozenset({"test", "tests", "testing", "coverage"})

_DOMAIN_WORDS: dict[str, frozenset[str]] = {
    "auth": frozenset({"auth", "login", "jwt", "password", "permission", "token"}),
    "testing": frozenset({"test", "tests", "testing", "coverage", "spec"}),
    "api": frozenset({"api", "endpoint", "route", "rest", "graphql"}),
    "database": frozenset({"db", "database", "sql", "migration", "query"}),
}


def _infer_mode(raw_task: str, constraints: list[str]) -> str:
    """Infer task mode from raw_task text and constraints."""
    lower = raw_task.lower()

    # Check constraints first
    for c in constraints:
        c_lower = c.lower()
        if "test" in c_lower or "coverage" in c_lower:
            return "test"

    # Check raw_task content
    words = set(lower.split())
    if words & _TEST_WORDS:
        return "test"
    if words & _REVIEW_WORDS:
        return "review"
    if words & _REFACTOR_WORDS:
        return "refactor"
    if words & _FEATURE_WORDS:
        return "feature"

    return "bugfix"


def _infer_domains(raw_task: str) -> list[str]:
    """Infer task domains from raw_task text."""
    lower = raw_task.lower()
    words = set(lower.split())
    domains: list[str] = []

    for domain, keywords in _DOMAIN_WORDS.items():
        if words & keywords:
            domains.append(domain)

    if not domains:
        domains.append("core")

    return sorted(domains)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_request(data: dict) -> list[str]:
    """Validate a raw task intake request.

    Parameters
    ----------
    data
        The raw request dict.

    Returns
    -------
    list[str]
        A list of validation errors (empty if valid).
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Request body must be a JSON object."]

    raw_task = data.get("raw_task")
    if raw_task is None:
        errors.append("raw_task is required")
    elif not isinstance(raw_task, str):
        errors.append("raw_task must be a string")
    elif not raw_task.strip():
        errors.append("raw_task must not be blank")

    source = data.get("source")
    if source is not None and not isinstance(source, str):
        errors.append("source must be a string if provided")

    metadata = data.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        errors.append("metadata must be a dict if provided")

    constraints = data.get("constraints")
    if constraints is not None:
        if not isinstance(constraints, list):
            errors.append("constraints must be a list if provided")
        elif any(not isinstance(c, str) for c in constraints):
            errors.append("each constraint must be a string")

    requested_output = data.get("requested_output")
    if requested_output is not None and not isinstance(requested_output, str):
        errors.append("requested_output must be a string if provided")

    return errors


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize_task_intake(raw: dict) -> dict:
    """Normalize a raw task intake request.

    Parameters
    ----------
    raw
        The raw request dict.

    Returns
    -------
    dict
        A normalized response with ``ok``, ``task_intake_id``,
        ``normalized_task``, ``validation``, and ``next`` fields.
    """
    # Validate
    errors = _validate_request(raw)

    if errors:
        return {
            "ok": False,
            "validation": {
                "valid": False,
                "errors": errors,
                "warnings": [],
            },
        }

    raw_task = raw["raw_task"]
    source = raw.get("source", "manual")
    metadata = raw.get("metadata", {})
    constraints = raw.get("constraints", [])
    requested_output = raw.get("requested_output", "plan")

    # Normalize
    task_goal = _normalize_text(raw_task)
    task_intake_id = _make_task_id(raw_task)
    inferred_mode = _infer_mode(raw_task, constraints)
    inferred_domains = _infer_domains(raw_task)

    # Warnings
    warnings: list[str] = []
    word_count = len(raw_task.split())
    if word_count < 8:
        warnings.append(
            f"raw_task is short ({word_count} words). "
            "Consider providing more detail."
        )

    return {
        "ok": True,
        "task_intake_id": task_intake_id,
        "normalized_task": {
            "raw_task": raw_task,
            "task_goal": task_goal,
            "source": source,
            "metadata": metadata,
            "constraints": sorted(constraints),
            "requested_output": requested_output,
            "inferred_mode": inferred_mode,
            "inferred_domains": inferred_domains,
            "warnings": warnings,
        },
        "validation": {
            "valid": True,
            "errors": [],
            "warnings": warnings,
        },
        "next": "/context/preview",
    }

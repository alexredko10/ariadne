"""
Context Pack Input Generator — pure deterministic function module.

Converts explicit caller-provided inputs into a canonical dict compatible
with ``schemas/context-pack-inputs.schema.yml``.

No I/O, no subprocess, no network, no models, no filesystem access.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Allowed freshness values
# ---------------------------------------------------------------------------

_VALID_FRESHNESS = frozenset({"fresh", "stale", "in_progress", "unknown"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_absolute_path(p: str) -> bool:
    """Return whether *p* looks like an absolute POSIX path."""
    return p.startswith("/")


def _has_shell_placeholder(s: str) -> bool:
    """Return whether *s* contains a shell placeholder ``$(``."""
    return "$(" in s


def _normalize_str_list(items: list[str] | None) -> list[str]:
    """Sort a list of strings and strip whitespace (deterministic)."""
    if not items:
        return []
    return sorted(str(i).strip() for i in items if i and str(i).strip())


def _normalize_dict_list(
    items: list[dict] | None,
    sort_key: str | None = None,
) -> list[dict]:
    """Normalize a list of dicts — sort by *sort_key* if provided."""
    if not items:
        return []
    result: list[dict] = []
    for item in items:
        if item:
            result.append(dict(item))
    if sort_key:
        result.sort(key=lambda d: str(d.get(sort_key, "")))
    return result


def _omit_empty(value: Any) -> Any | None:
    """Return ``None`` for empty values (to be omitted from output)."""
    if value is None:
        return None
    if isinstance(value, str) and not value:
        return None
    if isinstance(value, list) and not value:
        return None
    if isinstance(value, dict) and not value:
        return None
    return value


def _sorted_dict(d: dict[str, Any] | None) -> dict[str, Any]:
    """Return a dict with keys sorted lexicographically."""
    if not d:
        return {}
    return dict(sorted(d.items()))


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------


def context_pack_inputs_error(field: str, reason: str) -> ValueError:
    """Create a structured ``ValueError`` for validation failures."""
    return ValueError(
        f"context_pack_inputs validation failed: [{field}] {reason}"
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_context_pack_inputs(raw: dict) -> None:
    """Validate a context-pack-inputs dict.

    Parameters
    ----------
    raw
        The dict to validate.

    Raises
    ------
    ValueError
        If validation fails.
    """
    pr_id = raw.get("pr_id", "")
    if not isinstance(pr_id, str) or not pr_id.strip():
        raise context_pack_inputs_error(
            "pr_id", "pr_id is required and must be a non-empty string."
        )

    task_goal = raw.get("task_goal", "")
    if not isinstance(task_goal, str) or not task_goal.strip():
        raise context_pack_inputs_error(
            "task_goal", "task_goal is required and must be a non-empty string."
        )

    # Validate freshness status
    status = raw.get("context_freshness", {}).get("status", "fresh")
    if status not in _VALID_FRESHNESS:
        raise context_pack_inputs_error(
            "context_freshness.status",
            f"Must be one of {sorted(_VALID_FRESHNESS)}, got {status!r}.",
        )

    # Validate cache_key_refs entries
    cache_key_refs = raw.get("cache_key_refs", [])
    if isinstance(cache_key_refs, list):
        for i, ref in enumerate(cache_key_refs):
            if not isinstance(ref, dict):
                raise context_pack_inputs_error(
                    f"cache_key_refs[{i}]",
                    "Each cache key ref must be a dict.",
                )
            if "namespace" not in ref and "artifact_kind" not in ref:
                raise context_pack_inputs_error(
                    f"cache_key_refs[{i}]",
                    "Each cache key ref must have at least "
                    "'namespace' and 'artifact_kind' keys.",
                )


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize_context_pack_inputs(raw: dict) -> dict:
    """Normalize a context-pack-inputs dict to canonical form.

    Applies sorting, empty-value omission, and path validation.
    Does **not** modify the input dict in-place.

    Parameters
    ----------
    raw
        The dict to normalize.

    Returns
    -------
    dict
        A new normalized dict.
    """
    result: dict[str, Any] = {}

    # Schema version
    result["schema_version"] = "0.1"

    # Identity
    pr_id = raw.get("pr_id", "")
    if pr_id:
        result["pr_id"] = pr_id.strip()

    feature_id = raw.get("feature_id")
    if feature_id and isinstance(feature_id, str) and feature_id.strip():
        result["feature_id"] = feature_id.strip()

    task_goal = raw.get("task_goal", "")
    if task_goal:
        result["task_goal"] = task_goal.strip()

    # Lists
    source_contracts = _normalize_str_list(raw.get("source_contracts"))
    if source_contracts:
        result["source_contracts"] = source_contracts

    relevant_anchors = _normalize_str_list(raw.get("relevant_anchors"))
    if relevant_anchors:
        result["relevant_anchors"] = relevant_anchors

    allowed_paths = _normalize_str_list(raw.get("allowed_paths"))
    if allowed_paths:
        result["allowed_paths"] = allowed_paths

    forbidden_paths = _normalize_str_list(raw.get("forbidden_paths"))
    if forbidden_paths:
        result["forbidden_paths"] = forbidden_paths

    cache_key_refs = _normalize_dict_list(
        raw.get("cache_key_refs"), sort_key="namespace"
    )
    if cache_key_refs:
        result["cache_key_refs"] = cache_key_refs

    prior_pr_refs = _normalize_dict_list(
        raw.get("prior_pr_refs"), sort_key="pr_id"
    )
    if prior_pr_refs:
        result["prior_pr_refs"] = prior_pr_refs

    qa_evidence_refs = _normalize_str_list(raw.get("qa_evidence_refs"))
    if qa_evidence_refs:
        result["qa_evidence_refs"] = qa_evidence_refs

    known_risks = _normalize_dict_list(
        raw.get("known_risks"), sort_key="id"
    )
    if known_risks:
        result["known_risks"] = known_risks

    manual_checks_required = _normalize_str_list(
        raw.get("manual_checks_required")
    )
    if manual_checks_required:
        result["manual_checks_required"] = manual_checks_required

    requested_context_sections = _normalize_str_list(
        raw.get("requested_context_sections")
    )
    if requested_context_sections:
        result["requested_context_sections"] = requested_context_sections

    # Context freshness
    freshness = {}
    f_status = raw.get("context_freshness", {}).get("status", "fresh")
    if f_status:
        freshness["status"] = f_status
    f_last = raw.get("context_freshness", {}).get("last_verified_hook", "none")
    if f_last:
        freshness["last_verified_hook"] = f_last
    if freshness:
        result["context_freshness"] = freshness

    # Dict fields
    invalidation_inputs = _sorted_dict(raw.get("invalidation_inputs"))
    if invalidation_inputs:
        result["invalidation_inputs"] = invalidation_inputs

    output_preferences = _sorted_dict(raw.get("output_preferences"))
    if output_preferences:
        result["output_preferences"] = output_preferences

    # Source ref
    created_from = {}
    agent = raw.get("created_from", {}).get("agent", "")
    if agent:
        created_from["agent"] = agent
    hook = raw.get("created_from", {}).get("hook", "before_plan")
    if hook:
        created_from["hook"] = hook
    tmpl = raw.get("created_from", {}).get("template", "")
    if tmpl:
        created_from["template"] = tmpl
    created_from.get("agent") or created_from.get("hook") or None
    if created_from:
        result["created_from"] = created_from

    # Updated by (caller-provided)
    updated_by = raw.get("updated_by", [])
    if isinstance(updated_by, list) and updated_by:
        result["updated_by"] = list(updated_by)

    return result


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def build_context_pack_inputs(
    *,
    pr_id: str,
    task_goal: str,
    feature_id: str | None = None,
    source_contracts: list[str] | None = None,
    relevant_anchors: list[str] | None = None,
    allowed_paths: list[str] | None = None,
    forbidden_paths: list[str] | None = None,
    cache_key_refs: list[dict] | None = None,
    prior_pr_refs: list[dict] | None = None,
    qa_evidence_refs: list[str] | None = None,
    known_risks: list[dict] | None = None,
    manual_checks_required: list[str] | None = None,
    context_freshness_status: str = "fresh",
    context_freshness_last_verified: str = "none",
    invalidation_inputs: dict | None = None,
    requested_context_sections: list[str] | None = None,
    output_preferences: dict | None = None,
    created_from_agent: str = "",
    created_from_hook: str = "before_plan",
    created_from_template: str = "",
) -> dict:
    """Build a validated context-pack-inputs dict.

    Parameters are explicit caller-provided inputs.  This function does
    **not** read the filesystem, run Git, or infer values from the
    environment.

    Parameters
    ----------
    pr_id
        Required PR identifier.
    task_goal
        Required task goal description.
    feature_id
        Optional feature identifier.
    source_contracts
        Optional list of contract identifiers.
    relevant_anchors
        Optional list of anchor identifiers.
    allowed_paths
        Optional list of portable relative path patterns.
    forbidden_paths
        Optional list of forbidden path patterns.
    cache_key_refs
        Optional list of cache key reference dicts (must have
        ``namespace`` and ``artifact_kind``).
    prior_pr_refs
        Optional list of prior PR reference dicts.
    qa_evidence_refs
        Optional list of QA evidence identifiers.
    known_risks
        Optional list of risk dicts.
    manual_checks_required
        Optional list of manual check descriptions.
    context_freshness_status
        Context freshness (default ``"fresh"``).
    context_freshness_last_verified
        Last verified lifecycle hook (default ``"none"``).
    invalidation_inputs
        Optional dict of invalidation inputs.
    requested_context_sections
        Optional list of requested context section names.
    output_preferences
        Optional dict of output preferences.
    created_from_agent
        Optional agent identifier for provenance.
    created_from_hook
        Lifecycle hook (default ``"before_plan"``).
    created_from_template
        Optional template identifier.

    Returns
    -------
    dict
        A validated dict conforming to ``schemas/context-pack-inputs.schema.yml``.

    Raises
    ------
    ValueError
        If validation of required fields fails.
    """
    # Build raw dict
    raw: dict[str, Any] = {
        "pr_id": pr_id,
        "task_goal": task_goal,
        "context_freshness": {
            "status": context_freshness_status,
            "last_verified_hook": context_freshness_last_verified,
        },
        "created_from": {
            "agent": created_from_agent,
            "hook": created_from_hook,
            "template": created_from_template,
        },
    }

    # Optional fields (only add if non-None)
    if feature_id is not None:
        raw["feature_id"] = feature_id
    if source_contracts is not None:
        raw["source_contracts"] = source_contracts
    if relevant_anchors is not None:
        raw["relevant_anchors"] = relevant_anchors
    if allowed_paths is not None:
        raw["allowed_paths"] = allowed_paths
    if forbidden_paths is not None:
        raw["forbidden_paths"] = forbidden_paths
    if cache_key_refs is not None:
        raw["cache_key_refs"] = cache_key_refs
    if prior_pr_refs is not None:
        raw["prior_pr_refs"] = prior_pr_refs
    if qa_evidence_refs is not None:
        raw["qa_evidence_refs"] = qa_evidence_refs
    if known_risks is not None:
        raw["known_risks"] = known_risks
    if manual_checks_required is not None:
        raw["manual_checks_required"] = manual_checks_required
    if invalidation_inputs is not None:
        raw["invalidation_inputs"] = invalidation_inputs
    if requested_context_sections is not None:
        raw["requested_context_sections"] = requested_context_sections
    if output_preferences is not None:
        raw["output_preferences"] = output_preferences

    # Validate paths and shell placeholders
    if allowed_paths:
        for p in allowed_paths:
            if _is_absolute_path(p):
                raise context_pack_inputs_error(
                    "allowed_paths",
                    f"Absolute path not allowed: {p!r}",
                )
            if _has_shell_placeholder(p):
                raise context_pack_inputs_error(
                    "allowed_paths",
                    f"Shell placeholder not allowed: {p!r}",
                )
    if forbidden_paths:
        for p in forbidden_paths:
            if _is_absolute_path(p):
                raise context_pack_inputs_error(
                    "forbidden_paths",
                    f"Absolute path not allowed: {p!r}",
                )
            if _has_shell_placeholder(p):
                raise context_pack_inputs_error(
                    "forbidden_paths",
                    f"Shell placeholder not allowed: {p!r}",
                )

    # Normalize and return
    normalized = normalize_context_pack_inputs(raw)
    validate_context_pack_inputs(normalized)
    return normalized

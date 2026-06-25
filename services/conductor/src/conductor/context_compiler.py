"""
Minimal Context Compiler — pure deterministic function module.

Consumes context-pack-inputs dictionaries (from
``services/conductor/src/conductor/context_pack_inputs.py``) and produces
compact context-pack dictionaries compatible with
``schemas/context-pack.schema.yml``.

No I/O, no subprocess, no network, no models, no filesystem access.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_str_list(items: list[str] | None) -> list[str]:
    """Sort and strip a list of strings (deterministic)."""
    if not items:
        return []
    return sorted(str(i).strip() for i in items if i and str(i).strip())


def _omit_empty(value: Any) -> Any | None:
    """Return ``None`` for empty values (to be omitted from output)."""
    if value is None:
        return None
    if isinstance(value, str) and not value:
        return None
    if isinstance(value, list) and not value:
        return None
    return value


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------


def _pack_error(field: str, reason: str) -> ValueError:
    return ValueError(
        f"context_pack validation failed: [{field}] {reason}"
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_context_pack(raw: dict) -> None:
    """Validate a context-pack dict.

    Parameters
    ----------
    raw
        The dict to validate.

    Raises
    ------
    ValueError
        If validation fails.
    """
    required_strs = [
        "context_pack_id",
        "repo_id",
        "task",
        "purpose_id",
        "domain",
        "risk_level",
        "base_sha",
        "index_version",
    ]
    for key in required_strs:
        val = raw.get(key)
        if not isinstance(val, str) or not val.strip():
            raise _pack_error(
                key,
                f"{key} is required and must be a non-empty string.",
            )


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize_context_pack(raw: dict) -> dict:
    """Normalize a context-pack dict to canonical form.

    Applies sorting and empty-value omission.
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

    # Pass through scalar fields (sorted keys)
    scalar_keys = [
        "context_pack_id", "repo_id", "task", "purpose_id", "domain",
        "risk_level", "base_sha", "index_version",
    ]
    for key in scalar_keys:
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            result[key] = val.strip()

    # Pass through list fields
    list_keys = [
        "task_subgraph", "relevant_files", "relevant_symbols",
        "related_tests", "configs", "invariants", "risks",
        "recent_changes", "suggested_entry_points",
        "stable_prompt_blocks", "anchors",
    ]
    for key in list_keys:
        val = _normalize_str_list(raw.get(key))
        if val:
            result[key] = val

    # state_first_context
    sfc = raw.get("state_first_context")
    if sfc is not None:
        result["state_first_context"] = sfc

    return result


# ---------------------------------------------------------------------------
# Compile
# ---------------------------------------------------------------------------


def compile_context_pack(
    *,
    context_pack_inputs: dict,
    repo_id: str,
    purpose_id: str,
    domain: str,
    risk_level: str,
    base_sha: str,
    index_version: str,
    task_subgraph: list[str] | None = None,
    relevant_files: list[str] | None = None,
    relevant_symbols: list[str] | None = None,
    related_tests: list[str] | None = None,
    configs: list[str] | None = None,
    invariants: list[str] | None = None,
    recent_changes: list[str] | None = None,
    suggested_entry_points: list[str] | None = None,
) -> dict:
    """Compile a context-pack from explicit inputs.

    Parameters are explicit caller-provided inputs.  This function does
    **not** read the filesystem, run Git, or infer values from the
    environment.

    Parameters
    ----------
    context_pack_inputs
        A validated context-pack-inputs dict (e.g. from
        ``build_context_pack_inputs``).
    repo_id
        Repository identifier.
    purpose_id
        Purpose identifier.
    domain
        Domain name.
    risk_level
        Risk level string.
    base_sha
        Git base SHA at pack creation time.
    index_version
        Memory index version at pack creation time.
    task_subgraph
        Relevant dependency subgraph file paths.
    relevant_files
        Relevant file paths.
    relevant_symbols
        Relevant symbol names.
    related_tests
        Related test file paths.
    configs
        Configuration file paths.
    invariants
        Invariant identifiers.
    recent_changes
        Recent commit descriptions.
    suggested_entry_points
        Entry point suggestions.

    Returns
    -------
    dict
        A compact context-pack dict compatible with
        ``schemas/context-pack.schema.yml``.

    Raises
    ------
    ValueError
        If required fields are missing or invalid.
    """
    # --- Validate context_pack_inputs ---
    if not isinstance(context_pack_inputs, dict):
        raise _pack_error(
            "context_pack_inputs",
            "context_pack_inputs must be a dict.",
        )

    pr_id = context_pack_inputs.get("pr_id", "")
    if not isinstance(pr_id, str) or not pr_id.strip():
        raise _pack_error(
            "context_pack_inputs.pr_id",
            "context_pack_inputs must have a non-empty pr_id.",
        )

    # --- Validate required explicit params ---
    for name, val in [
        ("repo_id", repo_id),
        ("purpose_id", purpose_id),
        ("domain", domain),
        ("risk_level", risk_level),
        ("base_sha", base_sha),
        ("index_version", index_version),
    ]:
        if not isinstance(val, str) or not val.strip():
            raise _pack_error(
                name,
                f"{name} is required and must be a non-empty string.",
            )

    # --- Build raw context pack ---
    task_goal = context_pack_inputs.get("task_goal", "")
    raw: dict[str, Any] = {
        "context_pack_id": f"cp-{pr_id}-{repo_id}",
        "repo_id": repo_id.strip(),
        "task": task_goal.strip() if task_goal else task_goal,
        "purpose_id": purpose_id.strip(),
        "domain": domain.strip(),
        "risk_level": risk_level.strip(),
        "base_sha": base_sha.strip(),
        "index_version": index_version.strip(),
    }

    # Map invariants from source_contracts
    inputs_contracts = context_pack_inputs.get("source_contracts", [])
    if isinstance(inputs_contracts, list) and inputs_contracts:
        raw["invariants"] = _normalize_str_list(inputs_contracts)

    # Map risks from known_risks descriptions
    input_risks = context_pack_inputs.get("known_risks", [])
    if isinstance(input_risks, list) and input_risks:
        risk_descriptions: list[str] = []
        for r in input_risks:
            if isinstance(r, dict):
                desc = r.get("description", "")
                if desc:
                    risk_descriptions.append(desc)
        if risk_descriptions:
            raw["risks"] = sorted(risk_descriptions)

    # Map anchors from relevant_anchors
    input_anchors = context_pack_inputs.get("relevant_anchors", [])
    if isinstance(input_anchors, list) and input_anchors:
        raw["anchors"] = _normalize_str_list(input_anchors)

    # Explicit optional lists
    optional_lists = {
        "task_subgraph": task_subgraph,
        "relevant_files": relevant_files,
        "relevant_symbols": relevant_symbols,
        "related_tests": related_tests,
        "configs": configs,
        "recent_changes": recent_changes,
        "suggested_entry_points": suggested_entry_points,
    }
    for list_key, list_val in optional_lists.items():
        if list_val is not None:
            raw[list_key] = list_val

    # Additional explicit invariants (merge with source_contracts)
    explicit_invariants = _normalize_str_list(invariants)
    if explicit_invariants:
        existing = set(raw.get("invariants", []))
        merged = sorted(existing | set(explicit_invariants))
        raw["invariants"] = merged

    # Static fields
    raw["stable_prompt_blocks"] = []
    raw["state_first_context"] = None

    # Normalize and validate
    normalized = normalize_context_pack(raw)
    validate_context_pack(normalized)
    return normalized

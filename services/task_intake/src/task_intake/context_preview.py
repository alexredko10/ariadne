"""
Deterministic context preview mock — pure function.

Accepts normalized task intake data and returns a deterministic preview
of the context Ariadne would use for a future run.

No model calls, no repository scanning, no Git inspection, no persistence.
Self-contained mock — does not import from ``services/conductor/``.
"""

from __future__ import annotations

import hashlib
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_preview_id(task_intake: dict) -> str:
    """Generate a deterministic context preview ID from task intake data."""
    task_goal = task_intake.get("task_goal", "")
    source = task_intake.get("source", "manual")
    digest = hashlib.sha256(
        f"{task_goal}{source}".encode("utf-8")
    ).hexdigest()
    return f"ctxpreview_{digest[:12]}"


def _infer_anchor_domain(inferred_domains: list[str]) -> str:
    """Generate an Ariadne anchor from inferred domains."""
    if inferred_domains:
        return f"@ariadne-domain {inferred_domains[0]}"
    return "@ariadne-domain core"


_DEFAULT_SECTIONS = ["task", "scope", "risks"]

_ALLOWED_DEFAULT_PATHS = ["services/**"]
_FORBIDDEN_DEFAULT_PATHS = [".git/**", ".env", "secrets/**"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_request(data: dict) -> list[str]:
    """Validate a context preview request.

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

    task_intake = data.get("task_intake")
    if task_intake is None:
        errors.append("task_intake is required")
    elif not isinstance(task_intake, dict):
        errors.append("task_intake must be a dict")
    else:
        task_goal = task_intake.get("task_goal")
        if task_goal is None:
            errors.append("task_intake.task_goal is required")
        elif not isinstance(task_goal, str) or not task_goal.strip():
            errors.append("task_intake.task_goal must be a non-empty string")

    include_sections = data.get("include_sections")
    if include_sections is not None and not isinstance(include_sections, list):
        errors.append("include_sections must be a list if provided")

    preview_options = data.get("preview_options")
    if preview_options is not None and not isinstance(preview_options, dict):
        errors.append("preview_options must be a dict if provided")

    return errors


# ---------------------------------------------------------------------------
# Preview sections
# ---------------------------------------------------------------------------


def _build_task_section(ti: dict) -> dict:
    return {
        "goal": ti.get("task_goal", ""),
        "constraints": sorted(ti.get("constraints", [])),
        "requested_output": ti.get("requested_output", "plan"),
    }


def _build_scope_section(ti: dict) -> dict:
    return {
        "allowed_paths": list(_ALLOWED_DEFAULT_PATHS),
        "forbidden_paths": list(_FORBIDDEN_DEFAULT_PATHS),
        "inferred_domain": (ti.get("inferred_domains") or ["core"])[0],
    }


def _build_risks_section(ti: dict) -> dict:
    return {
        "warnings": list(ti.get("warnings", [])),
    }


def _build_anchors_section(ti: dict) -> dict:
    return {
        "relevant": [_infer_anchor_domain(ti.get("inferred_domains", []))],
    }


def _build_contracts_section() -> dict:
    return {
        "references": [
            "context-pack.schema",
            "context-pack-inputs.schema",
        ],
    }


def _build_cache_section(ti: dict) -> dict:
    task_goal = ti.get("task_goal", "")
    input_digest = hashlib.sha256(task_goal.encode("utf-8")).hexdigest()
    return {
        "mock_cache_key_refs": [
            {
                "namespace": "context",
                "artifact_kind": "context_pack",
                "input_digest": input_digest,
            }
        ],
    }


_SECTION_BUILDERS: dict[str, callable] = {
    "task": _build_task_section,
    "scope": _build_scope_section,
    "risks": _build_risks_section,
    "anchors": _build_anchors_section,
    "contracts": _build_contracts_section,
    "cache": _build_cache_section,
}


# ---------------------------------------------------------------------------
# Preview generation
# ---------------------------------------------------------------------------


def generate_context_preview(raw: dict) -> dict:
    """Generate a deterministic context preview from a raw request.

    Parameters
    ----------
    raw
        The raw request dict containing ``task_intake`` and optional fields.

    Returns
    -------
    dict
        A normalized response with ``ok``, ``context_preview_id``,
        ``task_intake_id``, ``preview``, ``validation``, and ``next`` fields.
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

    ti = raw["task_intake"]
    task_goal = ti.get("task_goal", "")
    inferred_mode = ti.get("inferred_mode", "unknown")
    inferred_domains = ti.get("inferred_domains", [])
    task_intake_id = ti.get("task_intake_id", "")
    source = ti.get("source", "manual")

    include_sections = raw.get("include_sections") or list(_DEFAULT_SECTIONS)
    preview_options = raw.get("preview_options") or {}

    # Build ID
    preview_id = _make_preview_id(ti)

    # Build context sections
    context_sections: dict[str, Any] = {}
    warning_list: list[str] = []
    missing_inputs: list[str] = []

    for section_name in include_sections:
        builder = _SECTION_BUILDERS.get(section_name)
        if builder:
            context_sections[section_name] = builder(ti)
        else:
            context_sections[section_name] = {"note": f"Section '{section_name}' not available in mock"}

    # Identify missing inputs
    if not ti.get("constraints"):
        missing_inputs.append("constraints")
        warning_list.append("No constraints provided — consider adding constraints")
    if not ti.get("metadata"):
        missing_inputs.append("metadata")

    return {
        "ok": True,
        "context_preview_id": preview_id,
        "task_intake_id": task_intake_id,
        "preview": {
            "task_summary": task_goal,
            "inferred_mode": inferred_mode,
            "inferred_domains": list(inferred_domains),
            "context_sections": context_sections,
            "context_pack_preview_summary": {
                "schema_version": "0.1",
                "sections_included": sorted(include_sections),
                "field_count": sum(len(v) if isinstance(v, dict) else 0 for v in context_sections.values()),
            },
            "missing_inputs": missing_inputs,
        },
        "validation": {
            "valid": True,
            "errors": [],
            "warnings": warning_list,
        },
        "next": "/runs",
    }

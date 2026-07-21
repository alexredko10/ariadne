"""PR 0151 — Visual Gate Readiness Checker.

On-demand computed readiness assessment for a selected run's Visual Gate.

Readiness is a deterministic, read-only, fail-closed assessment:
- Is a VisualGateResult configured for the run?
- Are the required Mermaid diagrams present, valid, and renderable?
- Is the Node.js renderer available and producing SVG?
- Does the sanitizer accept every SVG?

Ready means the gate is technically ready for human review — not approved,
not accepted, not executable, not mergeable, not authorized.

No persistence. No caching. No mutation of VG result or profile.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_DIAGRAM_TYPES = frozenset({"requirement", "state", "sequence"})
_MAX_SOURCE_BYTES = 100 * 1024  # 100 KB


# ---------------------------------------------------------------------------
# Readiness check
# ---------------------------------------------------------------------------


def check_visual_gate_readiness(
    runs_root: str,
    run_id: str,
    node_render_script: str | None = None,
) -> dict[str, Any]:
    """Determine whether the Visual Gate is technically ready for human review.

    Parameters
    ----------
    runs_root:
        Absolute path to the runs root directory.
    run_id:
        Canonical run identifier (alphanumeric, underscore, hyphen only).
    node_render_script:
        Optional explicit path to ``scripts/mermaid-render.cjs``. If None,
        the renderer module's default path is used.

    Returns
    -------
    dict with keys:
        ok (bool) — True if readiness could be determined.
        is_ready (bool) — True if gate is technically ready.
        status (str) — "ready", "not_ready", "no_gate", "unavailable".
        reason_codes (list of str) — Blocking condition identifiers.
        explanation (str) — Human-readable summary.
        diagram_results (list of dict or None) — Per-diagram readiness.
        renderer_available (bool) — Whether Node.js renderer is available.
        staleness_guard (str) — Deterministic hash for stale detection.
    """
    # --- Step 1: Check renderer availability ---
    renderer_available = _check_renderer_available(node_render_script)
    vg_found = False
    profile_found = False
    profile_sha256_val: str | None = None
    vg_sha256_val: str | None = None

    # --- Step 2: Load VisualGateResult ---
    from runner.visual_gate_result import read_visual_gate_result

    vg_result_raw = read_visual_gate_result(runs_root, run_id)

    if vg_result_raw.get("ok") is False:
        err = vg_result_raw.get("error", "")
        # Check if validation_failed is only about unsupported diagram types
        # (these are soft errors — continue evaluating)
        details = vg_result_raw.get("details", [])
        unsupported_only = all(
            "unsupported_diagram_type" in str(d) or "invalid_descriptor_ref" in str(d) or "missing_field" in str(d)
            for d in (details if isinstance(details, list) else [])
        )
        if err == "validation_failed" and unsupported_only and details:
            # Allow VG with unsupported types — the readiness checker handles them
            pass
        elif err == "not_found":
            return _result_no_gate(run_id, renderer_available)
        elif err == "malformed" or "validation_failed" in str(err):
            return _result_unavailable(run_id, "visual_gate_result_malformed", renderer_available)
        elif err == "unsupported_schema_version":
            return _result_unavailable(run_id, "visual_gate_result_unsupported_version", renderer_available)
        elif err == "invalid_run_id":
            return _result_unavailable(run_id, "run_not_found", renderer_available)
        else:
            return _result_unavailable(run_id, "visual_gate_result_malformed", renderer_available)

    # Check if VG was returned or only rejected for soft validation errors
    vg_data = vg_result_raw.get("visual_gate_result")
    
    # If VG exists but validation only flagged unsupported types, read directly
    if not vg_data and vg_result_raw.get("visual_gate_result_exists"):
        err = vg_result_raw.get("error", "")
        details = vg_result_raw.get("details", [])
        if err == "validation_failed" and details:
            # Read the VG file directly to proceed with partial validation
            import json as _json
            vg_path = os.path.join(runs_root, run_id, "visual-gate-result.json")
            try:
                with open(vg_path, "r", encoding="utf-8") as _f:
                    vg_data = _json.load(_f)
            except (OSError, _json.JSONDecodeError):
                pass
    
    if not vg_data:
        return _result_no_gate(run_id, renderer_available)

    vg_found = True
    vg_sha256_val = vg_result_raw.get("visual_gate_sha256")

    # Check hash_match from read_visual_gate_result
    if vg_result_raw.get("hash_match") is False:
        return _result_unavailable(run_id, "visual_gate_result_hash_mismatch", renderer_available)

    # --- Step 3: Check required_diagrams not empty ---
    required_diagrams = vg_data.get("required_diagrams", [])
    if not required_diagrams:
        return _build_result(
            run_id=run_id,
            is_ready=False,
            status="not_ready",
            reason_codes=["no_required_diagrams"],
            explanation="VisualGateResult has no required_diagrams.",
            diagram_results=[],
            renderer_available=renderer_available,
            profile_sha256=None,
            vg_sha256=vg_sha256_val,
        )

    # --- Step 4: Check for duplicate diagram_ids ---
    seen_ids: set[str] = set()
    for d in required_diagrams:
        did = d.get("diagram_id", "")
        if did and did in seen_ids:
            return _build_result(
                run_id=run_id,
                is_ready=False,
                status="not_ready",
                reason_codes=[f"duplicate_diagram_id:{did}"],
                explanation=f"Duplicate diagram_id '{did}' in required_diagrams.",
                diagram_results=[],
                renderer_available=renderer_available,
                profile_sha256=None,
                vg_sha256=vg_sha256_val,
            )
        seen_ids.add(did)

    # --- Step 5: Load run profile ---
    from runner.run_profile import read_run_profile

    profile_result = read_run_profile(runs_root, run_id)

    if profile_result.get("ok") is False:
        err = profile_result.get("error", "")
        if err == "profile not found":
            return _build_result(
                run_id=run_id,
                is_ready=False,
                status="no_gate",
                reason_codes=["profile_not_found"],
                explanation="Run profile not found — cannot resolve Mermaid artifact descriptors.",
                diagram_results=[],
                renderer_available=renderer_available,
                profile_sha256=None,
                vg_sha256=vg_sha256_val,
            )
        else:
            return _result_unavailable(run_id, "profile_malformed", renderer_available)

    profile_data = profile_result.get("profile")
    if not profile_data:
        return _build_result(
            run_id=run_id,
            is_ready=False,
            status="no_gate",
            reason_codes=["profile_not_found"],
            explanation="Run profile not found — cannot resolve Mermaid artifact descriptors.",
            diagram_results=[],
            renderer_available=renderer_available,
            profile_sha256=None,
            vg_sha256=vg_sha256_val,
        )

    profile_found = True
    profile_sha256_val = profile_result.get("profile_sha256")

    descriptors = profile_data.get("artifact_descriptors", [])
    # Build descriptor lookup by key
    desc_by_key: dict[str, dict] = {}
    for desc in descriptors:
        k = desc.get("key", "")
        if k:
            desc_by_key[k] = desc

    # --- Step 6: Evaluate each required diagram ---
    from runner.run_profile import resolve_run_relative
    from runner.mermaid_renderer import render_mermaid_to_svg
    from task_intake.svg_sanitizer import sanitize_svg

    # Sort by diagram_id for stable ordering
    sorted_diagrams = sorted(required_diagrams, key=lambda d: d.get("diagram_id", ""))

    diagram_results: list[dict[str, Any]] = []
    agg_reason_codes: list[str] = []
    all_diagrams_pass = True

    for rd in sorted_diagrams:
        diagram_id = rd.get("diagram_id", "")
        diagram_type = rd.get("diagram_type", "")
        descriptor_ref = rd.get("descriptor_ref", "")
        required = rd.get("required", True)

        result: dict[str, Any] = {
            "diagram_id": diagram_id,
            "diagram_type": diagram_type,
            "required": required,
            "descriptor_found": False,
            "source_found": False,
            "hash_match": None,
            "render_ok": None,
            "sanitize_ok": None,
            "error": None,
            "source_size_bytes": None,
        }

        # 6a. Resolve descriptor_ref
        import re as _re
        ref_match = _re.match(r"^profile_descriptor_key:(.+)$", descriptor_ref)
        if not ref_match:
            result["error"] = f"invalid_descriptor_ref:{descriptor_ref}"
            diagram_results.append(result)
            if required:
                all_diagrams_pass = False

        if ref_match:
            descriptor_key = ref_match.group(1)
            matching_desc = desc_by_key.get(descriptor_key)

            if matching_desc is None:
                # Check if a descriptor exists with this key but wrong kind
                found_wrong_kind = False
                for d in descriptors:
                    if d.get("key") == descriptor_key:
                        found_wrong_kind = True
                        result["error"] = f"descriptor_kind_mismatch:{descriptor_key}"
                        break
                if not found_wrong_kind:
                    result["error"] = f"descriptor_not_found:{descriptor_key}"
                    agg_reason_codes.append(f"descriptor_not_found:{descriptor_key}")
                else:
                    agg_reason_codes.append(f"descriptor_kind_mismatch:{descriptor_key}")
                if required:
                    all_diagrams_pass = False
                diagram_results.append(result)
                continue

            # 6c. Check kind == "mermaid"
            if matching_desc.get("kind") != "mermaid":
                result["error"] = f"descriptor_kind_mismatch:{descriptor_key}"
                agg_reason_codes.append(f"descriptor_kind_mismatch:{descriptor_key}")
                if required:
                    all_diagrams_pass = False
                diagram_results.append(result)
                continue

            result["descriptor_found"] = True

            # 6d. Resolve ref and read source
            ref = matching_desc.get("ref", "")
            declared_sha = matching_desc.get("sha256")

            if not ref.startswith("run-relative:"):
                result["error"] = f"source_not_found:{diagram_id}"
                agg_reason_codes.append(f"source_not_found:{diagram_id}")
                if required:
                    all_diagrams_pass = False
                diagram_results.append(result)
                continue

            file_path = resolve_run_relative(ref, runs_root, run_id)
            if file_path is None or not os.path.isfile(file_path):
                result["error"] = f"source_not_found:{diagram_id}"
                agg_reason_codes.append(f"source_not_found:{diagram_id}")
                if required:
                    all_diagrams_pass = False
                diagram_results.append(result)
                continue

            # 6f. Check size
            try:
                file_size = os.path.getsize(file_path)
            except OSError:
                result["error"] = f"source_not_found:{diagram_id}"
                agg_reason_codes.append(f"source_not_found:{diagram_id}")
                if required:
                    all_diagrams_pass = False
                diagram_results.append(result)
                continue

            if file_size > _MAX_SOURCE_BYTES:
                result["error"] = f"source_too_large:{diagram_id}"
                result["source_size_bytes"] = file_size
                agg_reason_codes.append(f"source_too_large:{diagram_id}")
                if required:
                    all_diagrams_pass = False
                diagram_results.append(result)
                continue

            result["source_size_bytes"] = file_size

            # Read file as bytes for hash verification
            try:
                with open(file_path, "rb") as f:
                    raw_bytes = f.read()
            except OSError:
                result["error"] = f"source_not_found:{diagram_id}"
                agg_reason_codes.append(f"source_not_found:{diagram_id}")
                if required:
                    all_diagrams_pass = False
                diagram_results.append(result)
                continue

            # Strip BOM
            if raw_bytes.startswith(b"\xef\xbb\xbf"):
                raw_bytes = raw_bytes[3:]

            # Decode as UTF-8
            try:
                content = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                result["error"] = f"source_encoding_error:{diagram_id}"
                agg_reason_codes.append(f"source_encoding_error:{diagram_id}")
                if required:
                    all_diagrams_pass = False
                diagram_results.append(result)
                continue

            result["source_found"] = True

            # 6g. Hash match
            content_hash = hashlib.sha256(raw_bytes).hexdigest()
            if declared_sha:
                result["hash_match"] = declared_sha == content_hash
                if not result["hash_match"]:
                    result["error"] = f"hash_mismatch:{diagram_id}"
                    agg_reason_codes.append(f"hash_mismatch:{diagram_id}")
                    if required:
                        all_diagrams_pass = False
                    diagram_results.append(result)
                    continue
            else:
                result["hash_match"] = None

            # 6h. Check diagram_type is in allowed set (warning only)
            if diagram_type and diagram_type not in _VALID_DIAGRAM_TYPES:
                agg_reason_codes.append(f"unsupported_diagram_type:{diagram_id}")
                if required:
                    all_diagrams_pass = False
                # Continue evaluating — unsupported type is warning, not hard stop

            # 6i-i. Render Mermaid to SVG
            if not renderer_available:
                result["error"] = "renderer_unavailable"
                agg_reason_codes.append("renderer_unavailable")
                if required:
                    all_diagrams_pass = False
                diagram_results.append(result)
                continue

            render_result = render_mermaid_to_svg(content, diagram_type)

            if not render_result.get("ok"):
                err_code = render_result.get("error", "render_error")
                result["error"] = f"render_error:{diagram_id}"
                agg_reason_codes.append(f"render_error:{diagram_id}")
                if required:
                    all_diagrams_pass = False
                diagram_results.append(result)
                continue

            result["render_ok"] = True

            # 6k. Sanitize SVG
            sanitize_result = sanitize_svg(render_result["svg"])
            if not sanitize_result.get("ok"):
                result["error"] = f"santize_error:{diagram_id}"
                agg_reason_codes.append(f"santize_error:{diagram_id}")
                if required:
                    all_diagrams_pass = False
                diagram_results.append(result)
                continue

            result["sanitize_ok"] = True
            result["error"] = None

            # All checks pass for this diagram
            diagram_results.append(result)

    # --- Step 7: Aggregate ---
    if all_diagrams_pass and not agg_reason_codes:
        return _build_result(
            run_id=run_id,
            is_ready=True,
            status="ready",
            reason_codes=[],
            explanation="Gate is ready for human review.",
            diagram_results=diagram_results,
            renderer_available=renderer_available,
            profile_sha256=profile_sha256_val,
            vg_sha256=vg_sha256_val,
        )
    else:
        # Deduplicate and sort reason codes for stable ordering
        unique_reasons = sorted(set(agg_reason_codes))
        explanation = _build_explanation(unique_reasons)
        return _build_result(
            run_id=run_id,
            is_ready=False,
            status="not_ready",
            reason_codes=unique_reasons,
            explanation=explanation,
            diagram_results=diagram_results,
            renderer_available=renderer_available,
            profile_sha256=profile_sha256_val,
            vg_sha256=vg_sha256_val,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _check_renderer_available(node_render_script: str | None = None) -> bool:
    """Check if the Node.js renderer is available."""
    from runner.mermaid_renderer import _check_renderer_available as _renderer_check
    return _renderer_check()


def _build_result(
    run_id: str,
    is_ready: bool,
    status: str,
    reason_codes: list[str],
    explanation: str,
    diagram_results: list[dict[str, Any]] | None,
    renderer_available: bool,
    profile_sha256: str | None,
    vg_sha256: str | None,
) -> dict[str, Any]:
    """Build a readiness result dict."""
    staleness_guard = _compute_staleness_guard(run_id, profile_sha256, vg_sha256)

    result: dict[str, Any] = {
        "ok": status != "unavailable",
        "is_ready": is_ready,
        "status": status,
        "reason_codes": reason_codes,
        "explanation": explanation,
        "renderer_available": renderer_available,
        "staleness_guard": staleness_guard,
    }

    if diagram_results is not None:
        result["diagram_results"] = diagram_results

    return result


def _build_explanation(reason_codes: list[str]) -> str:
    """Build a human-readable explanation from reason codes."""
    if not reason_codes:
        return ""

    parts: list[str] = []
    for code in reason_codes:
        if code == "no_required_diagrams":
            parts.append("VisualGateResult has no required_diagrams.")
        elif code.startswith("descriptor_not_found:"):
            key = code.split(":", 1)[1]
            parts.append(f"Required diagram references descriptor key '{key}' which does not exist in run profile.")
        elif code.startswith("descriptor_kind_mismatch:"):
            key = code.split(":", 1)[1]
            parts.append(f"Descriptor '{key}' exists but its kind is not 'mermaid'.")
        elif code.startswith("source_not_found:"):
            did = code.split(":", 1)[1]
            parts.append(f"Mermaid source file for diagram '{did}' was not found.")
        elif code.startswith("source_too_large:"):
            did = code.split(":", 1)[1]
            parts.append(f"Mermaid source file for diagram '{did}' exceeds 100 KB.")
        elif code.startswith("source_encoding_error:"):
            did = code.split(":", 1)[1]
            parts.append(f"Mermaid source file for diagram '{did}' is not valid UTF-8.")
        elif code.startswith("hash_mismatch:"):
            did = code.split(":", 1)[1]
            parts.append(f"Mermaid source for diagram '{did}' has content hash mismatch.")
        elif code == "renderer_unavailable":
            parts.append("Mermaid renderer (Node.js + mermaid npm package) is not available.")
        elif code.startswith("render_error:"):
            did = code.split(":", 1)[1]
            parts.append(f"Failed to render diagram '{did}'.")
        elif code.startswith("santize_error:"):
            did = code.split(":", 1)[1]
            parts.append(f"SVG output for diagram '{did}' failed sanitization.")
        elif code.startswith("unsupported_diagram_type:"):
            parts.append("Unsupported diagram type found.")
        elif code.startswith("duplicate_diagram_id:"):
            did = code.split(":", 1)[1]
            parts.append(f"Duplicate diagram_id '{did}' in required_diagrams.")
        elif code == "run_not_found":
            parts.append("Run not found at specified path.")
        elif code == "visual_gate_result_not_found":
            parts.append("No VisualGateResult exists for this run.")
        elif code == "visual_gate_result_malformed":
            parts.append("VisualGateResult is malformed or unreadable.")
        elif code == "visual_gate_result_unsupported_version":
            parts.append("VisualGateResult has an unsupported schema version.")
        elif code == "visual_gate_result_hash_mismatch":
            parts.append("VisualGateResult stored hash does not match computed hash.")
        elif code == "profile_not_found":
            parts.append("Run profile not found — cannot resolve Mermaid artifact descriptors.")
        elif code == "profile_malformed":
            parts.append("Run profile is malformed or unreadable.")
        elif code == "internal_error":
            parts.append("Internal error while checking readiness.")
        elif code == "stale_response":
            parts.append("Readiness check completed for a stale selection.")
        else:
            parts.append(f"Readiness issue: {code}")

    return " ".join(parts)


def _compute_staleness_guard(
    run_id: str,
    profile_sha256: str | None,
    vg_sha256: str | None,
) -> str:
    """Compute a deterministic staleness guard hash."""
    raw = f"{run_id}:{profile_sha256 or ''}:{vg_sha256 or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _result_no_gate(run_id: str, renderer_available: bool) -> dict[str, Any]:
    """Return a no_gate result."""
    return _build_result(
        run_id=run_id,
        is_ready=False,
        status="no_gate",
        reason_codes=["visual_gate_result_not_found"],
        explanation="No VisualGateResult exists for this run.",
        diagram_results=None,
        renderer_available=renderer_available,
        profile_sha256=None,
        vg_sha256=None,
    )


def _result_unavailable(
    run_id: str, error_code: str, renderer_available: bool
) -> dict[str, Any]:
    """Return an unavailable result."""
    return _build_result(
        run_id=run_id,
        is_ready=False,
        status="unavailable",
        reason_codes=[error_code],
        explanation=_build_explanation([error_code]),
        diagram_results=None,
        renderer_available=renderer_available,
        profile_sha256=None,
        vg_sha256=None,
    )

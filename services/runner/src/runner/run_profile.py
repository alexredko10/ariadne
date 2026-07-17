"""
PR 0147C — Domain-Neutral Run and Artifact Profile Contract.

OPTION A — Run-Directory Profile Sidecar.

Canonical path: ``<runs_root>/<run_id>/run-profile.json``

Core principle:
    The profile is optional descriptive metadata that supplements existing
    runtime evidence.  It must not override or replace run.json, manifest,
    runtime status, review state, or any existing evidence.  Profile metadata
    is not runtime proof.
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
_PROFILE_KEY_RE = re.compile(r"^[a-z][a-z0-9\-]{1,63}$")
_FACT_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_ENUM_VALUE_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_GROUP_KEY_RE = re.compile(r"^[a-z][a-z0-9_\-]{1,63}$")
_DESCRIPTOR_KEY_RE = re.compile(r"^[a-z][a-z0-9_\-]{1,63}$")
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_RUN_RELATIVE_RE = re.compile(r"^run-relative:(.+)$")
_SHA256_REF_RE = re.compile(r"^sha256:([0-9a-f]{64})$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")

_MAX_FACTS = 50
_MAX_GROUPS = 20
_MAX_DESCRIPTORS = 100
_MAX_KEY_LENGTH = 64
_MAX_LABEL_LENGTH = 200
_MAX_VALUE_SERIALIZED = 1000
_MAX_TITLE_LENGTH = 200
_MAX_STATUS_LABEL_LENGTH = 100
_MAX_KIND_LENGTH = 50
_MAX_EVIDENCE_ROLE_LENGTH = 20
_MAX_MEDIA_TYPE_LENGTH = 100
_MAX_REF_LENGTH = 500
_MAX_SHA256_LENGTH = 64
_MAX_SOURCE_LENGTH = 50
_MAX_UNIT_LENGTH = 50
_MAX_CURRENCY_LENGTH = 3
_MAX_VALUE_TYPE_LENGTH = 20
_MAX_PROFILE_KEY_LENGTH = 64
_MAX_SCHEMA_VERSION_LENGTH = 10

VALID_VALUE_TYPES = frozenset(("text", "number", "date", "boolean", "enum", "currency"))
VALID_EVIDENCE_ROLES = frozenset(("input", "output", "report", "capture", "supporting"))
VALID_SOURCES = frozenset(("operator", "adapter", "system"))


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_string(value: Any, field: str, max_len: int, codes: list[str], pattern: Optional[re.Pattern] = None) -> None:
    """Validate a string field."""
    if not isinstance(value, str):
        codes.append(f"invalid_{field}_type")
        return
    if len(value) > max_len:
        codes.append(f"{field}_too_long")
        return
    if pattern is not None and not pattern.match(value):
        codes.append(f"invalid_{field}_format")


def _validate_run_id(run_id: str) -> None:
    """Reject malformed run IDs."""
    if not _RUN_ID_RE.match(run_id):
        raise ValueError(f"Invalid run_id: {run_id!r}")


# ---------------------------------------------------------------------------
# Reference validation
# ---------------------------------------------------------------------------


def validate_reference(ref: str, codes: list[str]) -> str:
    """Validate a controlled reference. Returns the reference type."""
    if not isinstance(ref, str) or len(ref) == 0:
        codes.append("invalid_ref_type")
        return "invalid"
    if len(ref) > _MAX_REF_LENGTH:
        codes.append("ref_too_long")
        return "invalid"

    # Check for banned patterns first
    ref_lower = ref.lower()
    banned_prefixes = ("https://", "http://", "file://", "javascript:", "data:", "ftp://")
    for prefix in banned_prefixes:
        if ref_lower.startswith(prefix):
            codes.append(f"ref_url_not_allowed:{prefix.rstrip('/')}")
            return "url"

    # Absolute path check
    if ref.startswith("/"):
        codes.append("ref_absolute_path_not_allowed")
        return "absolute"

    # run-relative: check
    m = _RUN_RELATIVE_RE.match(ref)
    if m:
        path = m.group(1)
        if not path or path.strip() == "":
            codes.append("ref_empty_run_relative_path")
            return "run-relative"
        if path.startswith("/"):
            codes.append("ref_absolute_in_run_relative")
            return "run-relative"
        # Check traversal
        normalized = os.path.normpath(path)
        if normalized.startswith("..") or "/.." in normalized:
            codes.append("ref_traversal_not_allowed")
            return "run-relative"
        if normalized == ".":
            codes.append("ref_empty_run_relative_path")
            return "run-relative"
        return "run-relative"

    # sha256: check
    m = _SHA256_REF_RE.match(ref)
    if m:
        return "sha256"

    codes.append("invalid_ref_format")
    return "invalid"


def resolve_run_relative(ref: str, runs_root: str, run_id: str) -> Optional[str]:
    """Resolve a run-relative reference to an absolute filesystem path.

    Returns None if the resolved path escapes the run directory.
    """
    m = _RUN_RELATIVE_RE.match(ref)
    if not m:
        return None
    sub_path = m.group(1)
    run_dir = os.path.join(runs_root, run_id)
    resolved = os.path.realpath(os.path.join(run_dir, sub_path))
    run_dir_real = os.path.realpath(run_dir)
    if not resolved.startswith(run_dir_real + os.sep) and resolved != run_dir_real:
        return None
    return resolved


# ---------------------------------------------------------------------------
# Fact validation
# ---------------------------------------------------------------------------


def _validate_fact(fact: dict, codes: list[str]) -> None:
    """Validate a single neutral fact."""
    if not isinstance(fact, dict):
        codes.append("fact_not_dict")
        return

    key = fact.get("key", "")
    _validate_string(key, "fact_key", _MAX_KEY_LENGTH, codes, _FACT_KEY_RE)
    label = fact.get("label", "")
    _validate_string(label, "fact_label", _MAX_LABEL_LENGTH, codes)
    value_type = fact.get("value_type", "")
    _validate_string(value_type, "fact_value_type", _MAX_VALUE_TYPE_LENGTH, codes)
    if value_type not in VALID_VALUE_TYPES:
        codes.append(f"unsupported_value_type:{value_type}")

    value = fact.get("value")
    if value_type == "text":
        if not isinstance(value, str):
            codes.append("fact_value_not_text")
        elif len(value) > _MAX_VALUE_SERIALIZED:
            codes.append("fact_value_too_long")
    elif value_type == "number":
        if not isinstance(value, (int, float)):
            codes.append("fact_value_not_number")
        elif isinstance(value, float) and (value != value or value == float("inf") or value == float("-inf")):
            codes.append("fact_value_not_finite")
    elif value_type == "date":
        if not isinstance(value, str) or not _ISO_DATE_RE.match(value):
            codes.append("fact_value_not_valid_date")
    elif value_type == "boolean":
        if not isinstance(value, bool):
            codes.append("fact_value_not_boolean")
    elif value_type == "enum":
        if not isinstance(value, str) or not _ENUM_VALUE_RE.match(value):
            codes.append("fact_value_not_valid_enum")
    elif value_type == "currency":
        if not isinstance(value, (int, float)):
            codes.append("fact_value_not_number")
        elif isinstance(value, float) and (value != value or value == float("inf") or value == float("-inf")):
            codes.append("fact_value_not_finite")

    unit = fact.get("unit")
    if unit is not None:
        if value_type != "number":
            codes.append("unit_only_for_number")
        elif not isinstance(unit, str) or len(unit) > _MAX_UNIT_LENGTH:
            codes.append("invalid_unit")

    currency = fact.get("currency")
    if currency is not None:
        if value_type != "currency":
            codes.append("currency_only_for_currency_type")
        elif not isinstance(currency, str) or not _ISO_CURRENCY_RE.match(currency):
            codes.append("invalid_currency")

    display_order = fact.get("display_order")
    if not isinstance(display_order, int) or display_order < 0:
        codes.append("invalid_display_order")

    source = fact.get("source")
    if source is not None:
        if not isinstance(source, str) or len(source) > _MAX_SOURCE_LENGTH:
            codes.append("invalid_source")
        elif source not in VALID_SOURCES:
            codes.append(f"unsupported_source:{source}")


# ---------------------------------------------------------------------------
# Group validation
# ---------------------------------------------------------------------------


def _validate_group(key: str, group: dict, codes: list[str]) -> None:
    """Validate a single artifact group."""
    if not isinstance(group, dict):
        codes.append(f"group_not_dict:{key}")
        return
    gkey = group.get("key", "")
    _validate_string(gkey, "group_key", _MAX_KEY_LENGTH, codes, _GROUP_KEY_RE)
    label = group.get("label", "")
    _validate_string(label, "group_label", _MAX_LABEL_LENGTH, codes)
    display_order = group.get("display_order")
    if not isinstance(display_order, int) or display_order < 0:
        codes.append(f"invalid_group_display_order:{key}")


# ---------------------------------------------------------------------------
# Descriptor validation
# ---------------------------------------------------------------------------


def _validate_descriptor(desc: dict, valid_group_keys: set[str], codes: list[str]) -> None:
    """Validate a single artifact descriptor."""
    if not isinstance(desc, dict):
        codes.append("descriptor_not_dict")
        return

    key = desc.get("key", "")
    _validate_string(key, "descriptor_key", _MAX_KEY_LENGTH, codes, _DESCRIPTOR_KEY_RE)
    label = desc.get("label", "")
    _validate_string(label, "descriptor_label", _MAX_LABEL_LENGTH, codes)
    kind = desc.get("kind", "")
    _validate_string(kind, "descriptor_kind", _MAX_KIND_LENGTH, codes)
    evidence_role = desc.get("evidence_role", "")
    _validate_string(evidence_role, "evidence_role", _MAX_EVIDENCE_ROLE_LENGTH, codes)
    if evidence_role not in VALID_EVIDENCE_ROLES:
        codes.append(f"invalid_evidence_role:{evidence_role}")
    media_type = desc.get("media_type", "")
    _validate_string(media_type, "media_type", _MAX_MEDIA_TYPE_LENGTH, codes)
    ref = desc.get("ref", "")
    validate_reference(ref, codes)
    group_key = desc.get("group_key", "")
    _validate_string(group_key, "group_key", _MAX_KEY_LENGTH, codes)
    if group_key and group_key not in valid_group_keys:
        codes.append(f"invalid_group_ref:{group_key}")
    dorder = desc.get("display_order")
    if not isinstance(dorder, int) or dorder < 0:
        codes.append("invalid_descriptor_display_order")
    if not isinstance(desc.get("required"), bool):
        codes.append("invalid_required_flag")
    sha256 = desc.get("sha256")
    if sha256 is not None:
        _validate_string(sha256, "descriptor_sha256", _MAX_SHA256_LENGTH, codes, _SHA256_HEX_RE)


# ---------------------------------------------------------------------------
# Canonical JSON builder
# ---------------------------------------------------------------------------


def _build_canonical_profile(
    schema_version: str,
    profile_key: str,
    run_id: str,
    presentation: Optional[dict],
    groups: Optional[dict[str, dict]],
    descriptors: Optional[list[dict]],
) -> dict:
    """Build canonical profile dict (without profile_sha256)."""
    data: dict[str, Any] = {
        "schema_version": schema_version,
        "profile_key": profile_key,
        "run_id": run_id,
    }

    if presentation:
        data["run_presentation"] = {
            "title": presentation.get("title"),
            "status_label": presentation.get("status_label"),
            "neutral_facts": sorted(presentation.get("neutral_facts", []), key=lambda f: (f.get("display_order", 0), f.get("key", ""))),
        }
        # Remove None values for optional fields
        if data["run_presentation"]["title"] is None:
            del data["run_presentation"]["title"]
        if data["run_presentation"]["status_label"] is None:
            del data["run_presentation"]["status_label"]
        if not data["run_presentation"]["neutral_facts"]:
            del data["run_presentation"]["neutral_facts"]

    if groups:
        data["artifact_groups"] = dict(sorted(groups.items()))
    if descriptors:
        data["artifact_descriptors"] = sorted(descriptors, key=lambda d: (d.get("display_order", 0), d.get("key", "")))

    return data


def canonical_json(data: dict) -> str:
    """Deterministic JSON from a profile dict."""
    return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2)


def compute_profile_sha256(data: dict) -> str:
    """Compute profile_sha256 from canonical JSON (excluding profile_sha256)."""
    canonical = _build_canonical_profile(
        data.get("schema_version", _SCHEMA_VERSION),
        data.get("profile_key", ""),
        data.get("run_id", ""),
        data.get("run_presentation"),
        data.get("artifact_groups"),
        data.get("artifact_descriptors"),
    )
    content = canonical_json(canonical)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Validate full profile
# ---------------------------------------------------------------------------


def validate_profile_dict(data: dict) -> list[str]:
    """Validate a complete profile dict. Returns list of error codes."""
    codes: list[str] = []

    sv = data.get("schema_version", "")
    _validate_string(sv, "schema_version", _MAX_SCHEMA_VERSION_LENGTH, codes)
    if sv != _SCHEMA_VERSION:
        codes.append(f"unsupported_schema_version:{sv}")

    pk = data.get("profile_key", "")
    _validate_string(pk, "profile_key", _MAX_PROFILE_KEY_LENGTH, codes, _PROFILE_KEY_RE)

    rid = data.get("run_id", "")
    _validate_string(rid, "run_id", _MAX_KEY_LENGTH, codes, _RUN_ID_RE)

    presentation = data.get("run_presentation")
    if presentation is not None:
        if not isinstance(presentation, dict):
            codes.append("presentation_not_dict")
        else:
            title = presentation.get("title")
            if title is not None:
                _validate_string(title, "title", _MAX_TITLE_LENGTH, codes)
            status_label = presentation.get("status_label")
            if status_label is not None:
                _validate_string(status_label, "status_label", _MAX_STATUS_LABEL_LENGTH, codes)
            facts = presentation.get("neutral_facts")
            if facts is not None:
                if not isinstance(facts, list):
                    codes.append("neutral_facts_not_list")
                elif len(facts) > _MAX_FACTS:
                    codes.append(f"too_many_facts:{len(facts)}")
                else:
                    seen_keys: set[str] = set()
                    for fact in facts:
                        _validate_fact(fact, codes)
                        fk = fact.get("key", "") if isinstance(fact, dict) else ""
                        if fk in seen_keys:
                            codes.append(f"duplicate_fact_key:{fk}")
                        seen_keys.add(fk)

    # Validate artifact groups
    groups = data.get("artifact_groups")
    valid_group_keys: set[str] = set()
    if groups is not None:
        if not isinstance(groups, dict):
            codes.append("artifact_groups_not_dict")
        elif len(groups) > _MAX_GROUPS:
            codes.append(f"too_many_groups:{len(groups)}")
        else:
            for gk, gv in groups.items():
                _validate_group(gk, gv, codes)
                if gk in valid_group_keys:
                    codes.append(f"duplicate_group_key:{gk}")
                valid_group_keys.add(gk)

    # Validate artifact descriptors
    descriptors = data.get("artifact_descriptors")
    if descriptors is not None:
        if not isinstance(descriptors, list):
            codes.append("artifact_descriptors_not_list")
        elif len(descriptors) > _MAX_DESCRIPTORS:
            codes.append(f"too_many_descriptors:{len(descriptors)}")
        else:
            seen_desc_keys: set[str] = set()
            seen_refs: dict[str, str] = {}
            for desc in descriptors:
                _validate_descriptor(desc, valid_group_keys, codes)
                dk = desc.get("key", "") if isinstance(desc, dict) else ""
                if dk in seen_desc_keys:
                    codes.append(f"duplicate_descriptor_key:{dk}")
                seen_desc_keys.add(dk)
                # Conflict check: same ref, different sha256
                if isinstance(desc, dict):
                    ref = desc.get("ref", "")
                    sha256 = desc.get("sha256")
                    if ref in seen_refs and sha256 != seen_refs[ref]:
                        codes.append(f"conflicting_ref:{ref}")
                    if ref:
                        seen_refs[ref] = sha256

    return codes


# ---------------------------------------------------------------------------
# Create run profile
# ---------------------------------------------------------------------------


def create_run_profile(
    runs_root: str,
    run_id: str,
    presentation: Optional[dict] = None,
    artifact_groups: Optional[dict[str, dict]] = None,
    artifact_descriptors: Optional[list[dict]] = None,
) -> dict:
    """Create and persist a validated run profile.

    Parameters
    ----------
    runs_root:
        The runs root directory.
    run_id:
        The existing run ID.
    presentation:
        Run presentation with title, status_label, neutral_facts.
    artifact_groups:
        Artifact group definitions keyed by group key.
    artifact_descriptors:
        Ordered list of artifact presentation descriptors.

    Returns
    -------
    dict with keys: ok, profile_sha256, profile_path, error (optional), details (optional).
    """
    # Validate run_id
    if not _RUN_ID_RE.match(run_id):
        return {"ok": False, "error": "invalid run_id", "details": None}

    # Validate runs_root
    if not os.path.isdir(runs_root):
        return {"ok": False, "error": "runs_root_not_found", "details": None}

    # Validate run directory exists
    run_dir = os.path.join(runs_root, run_id)
    run_json_path = os.path.join(run_dir, "run.json")
    if not os.path.isfile(run_json_path):
        return {"ok": False, "error": "run_not_found", "details": None}

    # Build profile data
    profile_data: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "profile_key": "domain-neutral-v1",
        "run_id": run_id,
    }

    if presentation:
        profile_data["run_presentation"] = {
            "title": presentation.get("title"),
            "status_label": presentation.get("status_label"),
            "neutral_facts": presentation.get("neutral_facts", []),
        }
        # Drop None-only optional fields from canonical
        if profile_data["run_presentation"]["title"] is None:
            del profile_data["run_presentation"]["title"]
        if profile_data["run_presentation"]["status_label"] is None:
            del profile_data["run_presentation"]["status_label"]

    if artifact_groups:
        profile_data["artifact_groups"] = artifact_groups
    if artifact_descriptors:
        profile_data["artifact_descriptors"] = artifact_descriptors

    # Validate
    codes = validate_profile_dict(profile_data)
    if codes:
        return {
            "ok": False,
            "error": "profile validation failed",
            "details": codes,
        }

    # Compute profile_sha256 (excludes self)
    profile_sha256 = compute_profile_sha256(profile_data)
    profile_data["profile_sha256"] = profile_sha256

    # Atomic write to run directory
    profile_path = os.path.join(run_dir, "run-profile.json")
    tmp_path = profile_path + ".tmp"
    try:
        content = json.dumps(profile_data, sort_keys=True, ensure_ascii=False, indent=2)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, profile_path)
    except OSError as e:
        # Clean up temp file
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return {"ok": False, "error": f"write_failed:{e}", "details": None}

    # Readback verify
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            stored = json.load(f)
        stored_sha = stored.get("profile_sha256", "")
        readback_ok = stored_sha == profile_sha256
    except (OSError, json.JSONDecodeError):
        stored_sha = None
        readback_ok = False

    if not readback_ok:
        return {
            "ok": False,
            "error": "readback_hash_mismatch",
            "profile_sha256": profile_sha256,
            "profile_path": profile_path,
            "details": None,
        }

    return {
        "ok": True,
        "profile_sha256": profile_sha256,
        "profile_path": profile_path,
        "error": None,
        "details": None,
    }


# ---------------------------------------------------------------------------
# Read run profile
# ---------------------------------------------------------------------------


def read_run_profile(
    runs_root: str,
    run_id: str,
) -> dict:
    """Read and validate a run profile.

    Returns dict with keys:
      - ok: bool
      - error: str or None
      - details: str or None
      - profile: dict or None (validated profile data)
      - profile_sha256: str or None
      - profile_exists: bool
      - hash_match: bool or None
    """
    if not _RUN_ID_RE.match(run_id):
        return {
            "ok": False,
            "error": "invalid run_id",
            "profile_exists": False,
            "profile_sha256": None,
            "profile": None,
            "hash_match": None,
            "details": None,
        }

    profile_path = os.path.join(runs_root, run_id, "run-profile.json")
    if not os.path.isfile(profile_path):
        return {
            "ok": False,
            "error": "profile not found",
            "profile_exists": False,
            "profile_sha256": None,
            "profile": None,
            "hash_match": None,
            "details": None,
        }

    # Read raw JSON
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile_data = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "ok": False,
            "error": "profile malformed",
            "profile_exists": True,
            "profile_sha256": None,
            "profile": None,
            "hash_match": None,
            "details": f"json_decode_error:{e}",
        }
    except OSError as e:
        return {
            "ok": False,
            "error": "profile malformed",
            "profile_exists": True,
            "profile_sha256": None,
            "profile": None,
            "hash_match": None,
            "details": f"read_error:{e}",
        }

    # Check schema version
    sv = profile_data.get("schema_version", "")
    if sv != _SCHEMA_VERSION:
        return {
            "ok": False,
            "error": "unsupported profile version",
            "profile_exists": True,
            "profile_sha256": None,
            "profile": None,
            "hash_match": None,
            "details": f"schema_version:{sv}",
        }

    # Validate fields
    codes = validate_profile_dict(profile_data)
    if codes:
        return {
            "ok": False,
            "error": "profile validation failed",
            "profile_exists": True,
            "profile_sha256": None,
            "profile": None,
            "hash_match": None,
            "details": codes,
        }

    # Verify hash
    stored_sha = profile_data.get("profile_sha256", "")
    computed_sha = compute_profile_sha256(profile_data)
    hash_match = stored_sha == computed_sha

    if not hash_match:
        return {
            "ok": True,
            "error": "profile hash mismatch",
            "profile_exists": True,
            "profile_sha256": computed_sha,
            "profile": profile_data,
            "hash_match": False,
            "details": None,
        }

    return {
        "ok": True,
        "error": None,
        "profile_exists": True,
        "profile_sha256": stored_sha,
        "profile": profile_data,
        "hash_match": True,
        "details": None,
    }

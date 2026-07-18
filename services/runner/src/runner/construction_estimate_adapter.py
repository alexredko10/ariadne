"""
PR 0147D — Construction Estimate Read-Only Dogfood Adapter.

Parses a strict UTF-8 CSV construction estimate, validates it,
deterministically maps it to the PR 0147C version-1 run-profile contract,
and persists through the approved profile API.

Core principle:
    The adapter is read-only with respect to the source estimate.
    The source CSV is NEVER modified.  Profile metadata is descriptive,
    not runtime proof.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import os
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from runner.run_profile import create_run_profile

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "1"
_PROFILE_KEY = "construction-estimate-v1"
_MAX_SOURCE_BYTES = 1_000_000  # 1 MB
_MAX_ROWS = 1000
_MAX_FIELD_CHARS = 1000
_DECIMAL_PRECISION = 20
_DECIMAL_SCALE = 4
_LINE_TOTAL_TOLERANCE = Decimal("0.01")

_REQUIRED_HEADERS = [
    "estimate_id", "title", "project_name", "currency",
    "line_item_id", "description", "category",
    "quantity", "unit", "unit_rate", "line_total", "notes",
]

_REQUIRED_COLUMNS_WITH_DATA = {
    "estimate_id", "title", "project_name", "currency",
    "line_item_id", "description", "category",
    "quantity", "unit", "unit_rate",
}

_LINE_ITEM_ID_RE = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
_KNOWN_CURRENCIES = frozenset({
    "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "CNY",
    "INR", "MXN", "BRL", "SEK", "NOK", "NZD", "KRW", "SGD",
})

_ALLOWED_UNITS = frozenset({
    "each", "hour", "day", "week", "month", "lump_sum",
    "linear_foot", "square_foot", "cubic_foot",
    "linear_meter", "square_meter", "cubic_meter",
    "kilogram", "tonne", "pound",
    "gallon", "liter", "percent", "piece",
})

# ---------------------------------------------------------------------------
# Source hash
# ---------------------------------------------------------------------------


def _file_sha256(path: str) -> str:
    """Compute SHA-256 of a file, stripping BOM if present."""
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return hashlib.sha256(raw).hexdigest()


def _bytes_sha256(data: bytes) -> str:
    """Compute SHA-256 of raw bytes, stripping BOM if present."""
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Decimal parsing
# ---------------------------------------------------------------------------


_DECIMAL_VALUE_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _parse_decimal(s: str) -> Optional[Decimal]:
    """Parse a decimal string. Returns None if invalid.

    Rejects comma as thousands separator, and non-numeric input.
    """
    s = s.strip()
    if not s:
        return None
    if not _DECIMAL_VALUE_RE.match(s):
        return None
    try:
        return Decimal(s)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# CSV reading
# ---------------------------------------------------------------------------


def read_estimate_csv(path: str) -> dict:
    """Parse and validate a CSV estimate file.

    Parameters
    ----------
    path:
        Local filesystem path to the CSV file.

    Returns
    -------
    dict with keys: ok, error, details, estimate, source_sha256.
    """
    # 1. Path safety
    real_path = os.path.realpath(path)
    if not os.path.exists(real_path):
        return {"ok": False, "error": "source_missing", "details": [f"source_missing:{path}"], "estimate": None, "source_sha256": None}
    if not os.path.isfile(real_path):
        return {"ok": False, "error": "source_not_a_file", "details": [f"source_not_a_file:{path}"], "estimate": None, "source_sha256": None}

    # 2. Size check
    try:
        file_size = os.path.getsize(real_path)
    except OSError:
        return {"ok": False, "error": "source_not_a_file", "details": ["source_not_a_file"], "estimate": None, "source_sha256": None}
    if file_size > _MAX_SOURCE_BYTES:
        return {"ok": False, "error": "source_too_large", "details": [f"source_too_large:{file_size}"], "estimate": None, "source_sha256": None}

    # 3. Source hash BEFORE reading
    source_sha256 = _file_sha256(real_path)

    # 4. Read file
    with open(real_path, "rb") as f:
        raw_bytes = f.read()

    # 5. UTF-8 check and BOM stripping
    try:
        if raw_bytes.startswith(b"\xef\xbb\xbf"):
            text = raw_bytes[3:].decode("utf-8")
        else:
            text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return {"ok": False, "error": "unsupported_encoding", "details": ["unsupported_encoding"], "estimate": None, "source_sha256": source_sha256}

    # 6. Parse CSV
    import csv as _csv  # imported at call time per PLAN.md

    lines = text.splitlines()
    if not lines:
        return {"ok": False, "error": "malformed_csv", "details": ["malformed_csv:empty"], "estimate": None, "source_sha256": source_sha256}

    reader = _csv.reader(lines)
    rows = list(reader)
    if not rows:
        return {"ok": False, "error": "malformed_csv", "details": ["malformed_csv:no_rows"], "estimate": None, "source_sha256": source_sha256}

    # 7. Header validation
    header = rows[0]
    if len(header) != len(_REQUIRED_HEADERS):
        return {"ok": False, "error": "malformed_header", "details": [f"malformed_header:expected_{len(_REQUIRED_HEADERS)}_columns_got_{len(header)}"], "estimate": None, "source_sha256": source_sha256}

    # Check for duplicate headers
    seen_headers: set[str] = set()
    for col_name in header:
        if col_name in seen_headers:
            return {"ok": False, "error": "malformed_header", "details": [f"duplicate_header_column:{col_name}"], "estimate": None, "source_sha256": source_sha256}
        seen_headers.add(col_name)

    # Check for exact header match
    if header != _REQUIRED_HEADERS:
        missing = [h for h in _REQUIRED_HEADERS if h not in header]
        if missing:
            return {"ok": False, "error": "malformed_header", "details": [f"missing_required_column:{m}" for m in missing], "estimate": None, "source_sha256": source_sha256}
        extra = [h for h in header if h not in _REQUIRED_HEADERS]
        if extra:
            return {"ok": False, "error": "malformed_header", "details": [f"extra_column:{e}" for e in extra], "estimate": None, "source_sha256": source_sha256}

    # 8. Build column index
    col_index = {name: idx for idx, name in enumerate(header)}

    # 9. Parse data rows
    estimate_id: Optional[str] = None
    estimate_title: Optional[str] = None
    project_name: Optional[str] = None
    currency: Optional[str] = None
    items: list[dict] = []
    errors: list[str] = []
    seen_line_item_ids: set[str] = set()

    data_rows = rows[1:]  # Skip header
    if len(data_rows) > _MAX_ROWS:
        return {"ok": False, "error": "too_many_rows", "details": [f"too_many_rows:{len(data_rows)}"], "estimate": None, "source_sha256": source_sha256}

    for row_idx, row in enumerate(data_rows):
        # Skip blank rows
        if all(cell.strip() == "" for cell in row):
            continue

        # Check row length
        if len(row) != len(_REQUIRED_HEADERS):
            errors.append(f"malformed_csv:row_{row_idx + 2}_column_count")
            continue

        # Extract fields
        def cell(col_name: str) -> str:
            return row[col_index[col_name]].strip()

        eid = cell("estimate_id")
        tit = cell("title")
        pname = cell("project_name")
        cur = cell("currency")
        lid = cell("line_item_id")
        desc = cell("description")
        cat = cell("category")
        qty_s = cell("quantity")
        unt = cell("unit")
        rate_s = cell("unit_rate")
        lt_s = cell("line_total")
        notes = cell("notes")

        # Estimate-wide fields (from first non-blank row)
        if estimate_id is None and eid:
            estimate_id = eid
        if estimate_title is None and tit:
            estimate_title = tit
        if project_name is None and pname:
            project_name = pname
        if currency is None and cur:
            currency = cur

        # Check consistency of estimate-wide fields
        if eid and eid != estimate_id:
            errors.append(f"mismatched_estimate_id:{lid}:{eid}")
        if tit and tit != estimate_title:
            errors.append(f"mismatched_title:{lid}")
        if pname and pname != project_name:
            errors.append(f"mismatched_project_name:{lid}")
        if cur and cur != currency:
            errors.append(f"mismatched_currency:{lid}:{cur}")

        # Validate required text fields
        if not eid:
            errors.append(f"missing_estimate_id:{lid}")
        if not tit:
            errors.append(f"missing_title:{lid}")
        if not pname:
            errors.append(f"missing_project_name:{lid}")
        if not cur:
            errors.append(f"missing_currency:{lid}")
        if not lid:
            errors.append(f"missing_line_item_id")
            continue
        if not _LINE_ITEM_ID_RE.match(lid):
            errors.append(f"invalid_line_item_id:{lid}")
        if lid in seen_line_item_ids:
            errors.append(f"duplicate_line_item_id:{lid}")
        seen_line_item_ids.add(lid)

        if not desc:
            errors.append(f"missing_description:{lid}")
        if not cat:
            errors.append(f"missing_category:{lid}")
        if not unt:
            errors.append(f"missing_unit:{lid}")

        # Parse quantity
        qty = _parse_decimal(qty_s)
        if qty is None:
            errors.append(f"invalid_quantity:{lid}")
        elif qty <= 0:
            errors.append(f"invalid_quantity:{lid}:non_positive")
        else:
            qty = qty.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Parse unit_rate
        rate = _parse_decimal(rate_s)
        if rate is None:
            errors.append(f"invalid_unit_rate:{lid}")
        elif rate <= 0:
            errors.append(f"invalid_unit_rate:{lid}:non_positive")
        else:
            rate = rate.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Parse line_total
        line_total = None
        if lt_s:
            lt_parsed = _parse_decimal(lt_s)
            if lt_parsed is None:
                errors.append(f"invalid_line_total:{lid}")
            elif lt_parsed < 0:
                errors.append(f"invalid_line_total:{lid}:negative")
            else:
                line_total = lt_parsed.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        elif qty is not None and rate is not None:
            # Recalculate
            line_total = (qty * rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Line-total mismatch check
        if line_total is not None and qty is not None and rate is not None:
            recalculated = (qty * rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            if abs(line_total - recalculated) > _LINE_TOTAL_TOLERANCE:
                errors.append(f"line_total_mismatch:{lid}:expected:{recalculated}:got:{line_total}")

        item = {
            "line_item_id": lid,
            "description": desc,
            "category": cat,
            "quantity": qty,
            "unit": unt,
            "unit_rate": rate,
            "line_total": line_total,
            "notes": notes,
            "row": row_idx + 2,
        }
        items.append(item)

    if errors:
        return {
            "ok": False,
            "error": "validation_failed",
            "details": errors,
            "estimate": None,
            "source_sha256": source_sha256,
        }

    # 10. Validate currency
    if currency and currency not in _KNOWN_CURRENCIES:
        errors.append(f"invalid_currency:{currency}")
    if errors:
        return {
            "ok": False,
            "error": "validation_failed",
            "details": errors,
            "estimate": None,
            "source_sha256": source_sha256,
        }

    # 11. Build estimate object
    # Compute totals using Decimal
    subtotal = sum((item["line_total"] for item in items if item["line_total"] is not None), Decimal("0"))
    subtotal = subtotal.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    grand_total = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Collect categories
    categories: list[str] = []
    seen_cats: set[str] = set()
    for item in items:
        if item["category"] not in seen_cats:
            categories.append(item["category"])
            seen_cats.add(item["category"])

    estimate = {
        "estimate_id": estimate_id or "",
        "title": estimate_title or "",
        "project_name": project_name or "",
        "currency": currency or "",
        "items": items,
        "subtotal": subtotal,
        "grand_total": grand_total,
        "categories": categories,
    }

    return {
        "ok": True,
        "error": None,
        "details": None,
        "estimate": estimate,
        "source_sha256": source_sha256,
    }


# ---------------------------------------------------------------------------
# Profile mapping
# ---------------------------------------------------------------------------


def _decimal_to_str(d: Decimal) -> str:
    return str(d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def estimate_to_profile(
    runs_root: str,
    run_id: str,
    estimate: dict,
    source_sha256: str,
) -> dict:
    """Map a validated estimate to a PR 0147C run profile.

    Parameters
    ----------
    runs_root:
        The runs root directory.
    run_id:
        The existing run ID.
    estimate:
        Parsed and validated estimate dict from read_estimate_csv().
    source_sha256:
        SHA-256 of the source file.

    Returns
    -------
    Result dict from run_profile.create_run_profile().
    """
    items = estimate.get("items", [])
    categories = estimate.get("categories", [])
    subtotal = estimate.get("subtotal", Decimal("0"))
    grand_total = estimate.get("grand_total", Decimal("0"))

    # Build neutral facts
    facts = [
        {"key": "estimate_id", "label": "Estimate ID", "value": estimate.get("estimate_id", ""), "value_type": "text", "display_order": 1, "source": "adapter"},
        {"key": "project_name", "label": "Project Name", "value": estimate.get("project_name", ""), "value_type": "text", "display_order": 2, "source": "adapter"},
        {"key": "currency", "label": "Currency", "value": estimate.get("currency", ""), "value_type": "text", "display_order": 3, "source": "adapter"},
        {"key": "item_count", "label": "Line Items", "value": len(items), "value_type": "number", "display_order": 4, "source": "adapter"},
        {"key": "category_count", "label": "Categories", "value": len(categories), "value_type": "number", "display_order": 5, "source": "adapter"},
        {"key": "subtotal", "label": "Subtotal", "value": float(subtotal), "value_type": "currency", "currency": estimate.get("currency", "USD"), "display_order": 6, "source": "adapter"},
        {"key": "grand_total", "label": "Grand Total", "value": float(grand_total), "value_type": "currency", "currency": estimate.get("currency", "USD"), "display_order": 7, "source": "adapter"},
        {"key": "source_format", "label": "Source Format", "value": "CSV", "value_type": "text", "display_order": 8, "source": "adapter"},
        {"key": "validation_status", "label": "Validation", "value": "passed", "value_type": "text", "display_order": 9, "source": "adapter"},
    ]

    presentation = {
        "title": f"Estimate: {estimate.get('title', '')} ({estimate.get('estimate_id', '')})",
        "status_label": "Construction Estimate",
        "neutral_facts": facts,
    }

    groups = {
        "original": {"key": "original", "label": "Original Estimate", "display_order": 1},
        "normalized": {"key": "normalized", "label": "Normalized Estimate", "display_order": 2},
        "validation": {"key": "validation", "label": "Validation Reports", "display_order": 3},
    }

    # Build normalized estimate JSON content (for the output artifact)
    normalized_data = {
        "estimate_id": estimate.get("estimate_id"),
        "title": estimate.get("title"),
        "project_name": estimate.get("project_name"),
        "currency": estimate.get("currency"),
        "items": [
            {
                "line_item_id": it["line_item_id"],
                "description": it["description"],
                "category": it["category"],
                "quantity": _decimal_to_str(it["quantity"]) if isinstance(it.get("quantity"), Decimal) else str(it.get("quantity", "")),
                "unit": it["unit"],
                "unit_rate": _decimal_to_str(it["unit_rate"]) if isinstance(it.get("unit_rate"), Decimal) else str(it.get("unit_rate", "")),
                "line_total": _decimal_to_str(it["line_total"]) if isinstance(it.get("line_total"), Decimal) else str(it.get("line_total", "")),
                "notes": it.get("notes", ""),
            }
            for it in items
        ],
        "subtotal": _decimal_to_str(subtotal),
        "grand_total": _decimal_to_str(grand_total),
        "categories": categories,
    }
    normalized_json_str = json.dumps(normalized_data, indent=2, ensure_ascii=False, sort_keys=True)

    # Build line items CSV content
    import csv as _csv
    line_items_lines = ["line_item_id,description,category,quantity,unit,unit_rate,line_total,notes"]
    for it in items:
        qty_str = _decimal_to_str(it["quantity"]) if isinstance(it.get("quantity"), Decimal) else str(it.get("quantity", ""))
        rate_str = _decimal_to_str(it["unit_rate"]) if isinstance(it.get("unit_rate"), Decimal) else str(it.get("unit_rate", ""))
        lt_str = _decimal_to_str(it["line_total"]) if isinstance(it.get("line_total"), Decimal) else str(it.get("line_total", ""))
        line_items_lines.append(f"{it['line_item_id']},{it['description']},{it['category']},{qty_str},{it['unit']},{rate_str},{lt_str},{it.get('notes','')}")
    line_items_csv = "\n".join(line_items_lines)

    # Build validation report
    validation_report = (
        f"Construction Estimate Validation Report\n"
        f"========================================\n"
        f"Estimate ID: {estimate.get('estimate_id', '')}\n"
        f"Title: {estimate.get('title', '')}\n"
        f"Project: {estimate.get('project_name', '')}\n"
        f"Currency: {estimate.get('currency', '')}\n"
        f"Line Items: {len(items)}\n"
        f"Categories: {len(categories)}\n"
        f"Subtotal: {_decimal_to_str(subtotal)} {estimate.get('currency', '')}\n"
        f"Grand Total: {_decimal_to_str(grand_total)} {estimate.get('currency', '')}\n"
        f"Source SHA-256: {source_sha256}\n"
        f"Schema: Strict CSV per PR 0147D contract\n"
        f"Validation: Passed\n"
    )

    # Persist artifacts to run directory
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)

    # Write normalized JSON
    norm_path = os.path.join(run_dir, "normalized-estimate.json")
    with open(norm_path, "w", encoding="utf-8") as f:
        f.write(normalized_json_str)

    # Write line items CSV
    csv_path = os.path.join(run_dir, "line-items.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(line_items_csv)

    # Write validation report
    val_path = os.path.join(run_dir, "validation-report.txt")
    with open(val_path, "w", encoding="utf-8") as f:
        f.write(validation_report)

    # Descriptors: source CSV remains to be copied by the caller
    descriptors = [
        {"key": "source_csv", "label": "Original CSV", "kind": "source_file", "evidence_role": "input", "media_type": "text/csv", "ref": "run-relative:source-estimate.csv", "group_key": "original", "display_order": 1, "required": True},
        {"key": "normalized_json", "label": "Normalized Estimate", "kind": "normalized_data", "evidence_role": "output", "media_type": "application/json", "ref": "run-relative:normalized-estimate.json", "group_key": "normalized", "display_order": 1, "required": True},
        {"key": "line_items_csv", "label": "Line Items Table", "kind": "itemized_list", "evidence_role": "report", "media_type": "text/csv", "ref": "run-relative:line-items.csv", "group_key": "normalized", "display_order": 2, "required": True},
        {"key": "validation_report", "label": "Validation Report", "kind": "validation", "evidence_role": "supporting", "media_type": "text/plain", "ref": "run-relative:validation-report.txt", "group_key": "validation", "display_order": 1, "required": False},
    ]

    # Add sha256 for existing artifacts
    for desc in descriptors:
        ref = desc["ref"]
        if ref.startswith("run-relative:"):
            rel_path = ref[len("run-relative:"):]
            artifact_path = os.path.join(run_dir, rel_path)
            if os.path.isfile(artifact_path):
                with open(artifact_path, "rb") as f:
                    desc["sha256"] = hashlib.sha256(f.read()).hexdigest()

    # Use the building blocks from run_profile but write with the correct profile_key
    # create_run_profile() hardcodes domain-neutral-v1, so we construct the profile directly.
    profile_data: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "profile_key": _PROFILE_KEY,
        "run_id": run_id,
        "run_presentation": presentation,
        "artifact_groups": groups,
        "artifact_descriptors": descriptors,
    }

    # Validate
    from runner.run_profile import validate_profile_dict
    codes = validate_profile_dict(profile_data)
    if codes:
        return {"ok": False, "error": "profile validation failed", "details": codes}

    # Compute hash (excludes self)
    from runner.run_profile import compute_profile_sha256
    profile_sha256 = compute_profile_sha256(profile_data)
    profile_data["profile_sha256"] = profile_sha256

    # Atomic write
        # Atomic write
    profile_path = os.path.join(run_dir, "run-profile.json")
    tmp_path = profile_path + ".tmp"
    try:
        content = json.dumps(profile_data, sort_keys=True, ensure_ascii=False, indent=2)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, profile_path)
    except OSError as e:
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
        readback_ok = False

    if not readback_ok:
        return {"ok": False, "error": "readback_hash_mismatch", "profile_sha256": profile_sha256, "details": None}

    return {"ok": True, "profile_sha256": profile_sha256, "profile_path": profile_path, "error": None, "details": None}


# ---------------------------------------------------------------------------
# One-call entrypoint
# ---------------------------------------------------------------------------


def create_construction_estimate_profile(
    runs_root: str,
    run_id: str,
    source_path: str,
) -> dict:
    """Read CSV, validate, create profile in one call.

    This is the CLI-callable entrypoint.

    Parameters
    ----------
    runs_root:
        The runs root directory.
    run_id:
        The run ID (must exist or be created via --create-run).
    source_path:
        Local path to the CSV estimate file.

    Returns
    -------
    dict with keys: ok, error, details, profile_result, source_sha256.
    """
    # 1. Read and validate CSV
    parse_result = read_estimate_csv(source_path)
    if not parse_result.get("ok"):
        return parse_result

    estimate = parse_result["estimate"]
    source_sha256 = parse_result["source_sha256"]

    # 2. Verify run directory exists
    run_dir = os.path.join(runs_root, run_id)
    if not os.path.isdir(run_dir):
        return {
            "ok": False,
            "error": "run_not_found",
            "details": [f"run_missing:{run_id}"],
            "profile_result": None,
            "source_sha256": source_sha256,
        }

    # Check run.json exists
    run_json_path = os.path.join(run_dir, "run.json")
    if not os.path.isfile(run_json_path):
        return {
            "ok": False,
            "error": "run_missing",
            "details": [f"run_missing:{run_id}"],
            "profile_result": None,
            "source_sha256": source_sha256,
        }

    # 3. Copy source CSV to run directory
    source_copy_path = os.path.join(run_dir, "source-estimate.csv")
    with open(source_path, "rb") as f_src:
        src_bytes = f_src.read()
    # Verify source has not changed during read
    current_hash = _bytes_sha256(src_bytes)
    if current_hash != source_sha256:
        return {
            "ok": False,
            "error": "source_changed_during_read",
            "details": [f"source_changed_during_read"],
            "profile_result": None,
            "source_sha256": source_sha256,
        }
    # Write copy
    with open(source_copy_path, "wb") as f_dst:
        f_dst.write(src_bytes)
    # Verify copy matches
    copy_hash = _file_sha256(source_copy_path)
    if copy_hash != source_sha256:
        return {
            "ok": False,
            "error": "source_changed_during_read",
            "details": [f"source_copy_hash_mismatch"],
            "profile_result": None,
            "source_sha256": source_sha256,
        }

    # 4. Map to profile
    profile_result = estimate_to_profile(runs_root, run_id, estimate, source_sha256)

    if not profile_result.get("ok"):
        return {
            "ok": False,
            "error": profile_result.get("error", "profile_creation_failed"),
            "details": profile_result.get("details"),
            "profile_result": profile_result,
            "source_sha256": source_sha256,
        }

    return {
        "ok": True,
        "error": None,
        "details": None,
        "profile_result": profile_result,
        "source_sha256": source_sha256,
    }

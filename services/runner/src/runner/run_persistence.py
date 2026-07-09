"""
Run Persistence for Ariadne — third Stage 2 Closed Loop PR.

Persists ``ariadne task`` run results as local file evidence under
``<runs_root>/<run_id>/run.json`` and ``manifest.json``.
Supports readback by ``run_id``.  No dashboard, no control plane,
no retry loop.

Core principle:
    Agent output is not evidence.  Runtime/file-captured artifacts are
    evidence.  A dogfood run must be inspectable after process exit.
    Run persistence is local file evidence, not a dashboard or control
    plane.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
import re
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# RunPersistenceStatus — status values
# ---------------------------------------------------------------------------


class RunPersistenceStatus(str, enum.Enum):
    """Status values for run persistence operations."""

    PERSISTED = "persisted"
    READ_OK = "read_ok"
    REJECTED = "rejected"
    NOT_FOUND = "not_found"


# ---------------------------------------------------------------------------
# RunPersistenceRequest — input dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class RunPersistenceRequest:
    """Input parameters for persisting a run record."""

    runs_root: str
    run_id: str
    task_description_hash: str
    task_description_redacted: str
    branch: str
    base_branch: str
    status: str
    reason_codes: tuple[str, ...]
    pipeline_status: Optional[str]
    pipeline_final_action: Optional[str]
    pipeline_has_blockers: Optional[bool]
    pipeline_step_summary: tuple[dict, ...]
    pipeline_gate_summary: tuple[dict, ...]
    git_boundary_status: Optional[str]
    command_plan_summary: tuple[dict, ...]
    execution_attempted: bool
    execution_results_summary: tuple[dict, ...]
    approval_summary: str
    artifact_hashes: dict[str, str]
    warnings: tuple[str, ...]
    next_action: str
    started_at: Optional[str]
    finished_at: Optional[str]
    clock_provider: Optional[Callable] = None
    report_path: Optional[str] = None


# ---------------------------------------------------------------------------
# PersistedRunRecord — stored record model
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PersistedRunRecord:
    """A persisted run record."""

    schema_version: str
    run_id: str
    run_json_hash: str
    task_description_hash: str
    task_description_redacted: str
    branch: str
    base_branch: str
    status: str
    reason_codes: tuple[str, ...]
    pipeline_status: Optional[str]
    pipeline_final_action: Optional[str]
    pipeline_has_blockers: Optional[bool]
    git_boundary_status: Optional[str]
    command_plan_summary: tuple[dict, ...]
    execution_attempted: bool
    execution_results_summary: tuple[dict, ...]
    approval_summary: str
    artifact_hashes: dict[str, str]
    warnings: tuple[str, ...]
    next_action: str
    started_at: Optional[str]
    finished_at: Optional[str]


# ---------------------------------------------------------------------------
# RunPersistenceResult — write result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class RunPersistenceResult:
    """Result of a persist operation."""

    status: str
    reason_codes: tuple[str, ...]
    run_id: str
    run_dir: str
    files_written: tuple[str, ...]
    manifest_path: str
    run_json_path: str
    run_json_hash: str
    bytes_written: int
    readback_ok: bool
    started_at: Optional[str]
    finished_at: Optional[str]
    details: Optional[str]


# ---------------------------------------------------------------------------
# RunPersistenceReadResult — read result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class RunPersistenceReadResult:
    """Result of a read operation."""

    status: str
    reason_codes: tuple[str, ...]
    run_id: str
    record: Optional[PersistedRunRecord]
    stored_hash: Optional[str]
    recomputed_hash: Optional[str]
    hash_match: bool
    details: Optional[str]


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_INVALID_RUN_ID = "invalid_run_id"
REASON_WRITE_FAILED = "write_failed"
REASON_READ_FAILED = "read_failed"
REASON_HASH_MISMATCH = "hash_mismatch"

# ---------------------------------------------------------------------------
# Run ID validation
# ---------------------------------------------------------------------------

_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "1"


# ---------------------------------------------------------------------------
# Atomic JSON write
# ---------------------------------------------------------------------------


def _write_json_atomically(data: dict, path: str) -> None:
    """Write a JSON dict atomically to a file.

    Writes to a ``.tmp`` file first, then renames to the target path.
    """
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, sort_keys=True, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


# ---------------------------------------------------------------------------
# Persist run record
# ---------------------------------------------------------------------------


def persist_run_record(
    request: RunPersistenceRequest,
) -> RunPersistenceResult:
    """Persist a run record to the local filesystem.

    Parameters
    ----------
    request:
        Input parameters including runs_root, run_id, and all run data.

    Returns
    -------
    RunPersistenceResult
        ``status="persisted"`` when the record is written.
        ``status="rejected"`` when validation fails.
    """
    codes: list[str] = []
    started_at = request.clock_provider() if request.clock_provider else None

    # 1. Validate run_id
    if not _RUN_ID_RE.match(request.run_id):
        codes.append(REASON_INVALID_RUN_ID)
        finished_at = request.clock_provider() if request.clock_provider else None
        return RunPersistenceResult(
            status=RunPersistenceStatus.REJECTED.value,
            reason_codes=tuple(codes),
            run_id=request.run_id,
            run_dir="",
            files_written=(),
            manifest_path="",
            run_json_path="",
            run_json_hash="",
            bytes_written=0,
            readback_ok=False,
            started_at=started_at,
            finished_at=finished_at,
            details=f"Invalid run_id: {request.run_id!r}",
        )

    # 2. Build run directory
    run_dir = os.path.join(request.runs_root, request.run_id)
    run_json_path = os.path.join(run_dir, "run.json")
    manifest_path = os.path.join(run_dir, "manifest.json")

    # 3. Build run.json data
    run_json_data = {
        "schema_version": _SCHEMA_VERSION,
        "run_id": request.run_id,
        "task_description_hash": request.task_description_hash,
        "task_description_redacted": request.task_description_redacted,
        "branch": request.branch,
        "base_branch": request.base_branch,
        "status": request.status,
        "reason_codes": list(request.reason_codes),
        "pipeline_status": request.pipeline_status,
        "pipeline_final_action": request.pipeline_final_action,
        "pipeline_has_blockers": request.pipeline_has_blockers,
        "pipeline_step_summary": list(request.pipeline_step_summary),
        "pipeline_gate_summary": list(request.pipeline_gate_summary),
        "git_boundary_status": request.git_boundary_status,
        "command_plan_summary": list(request.command_plan_summary),
        "execution_attempted": request.execution_attempted,
        "execution_results_summary": list(request.execution_results_summary),
        "approval_summary": request.approval_summary,
        "artifact_hashes": dict(request.artifact_hashes),
        "warnings": list(request.warnings),
        "next_action": request.next_action,
        "started_at": request.started_at,
        "finished_at": request.finished_at,
    }

    # 4. Compute run.json hash
    run_json_canonical = json.dumps(run_json_data, sort_keys=True, ensure_ascii=False)
    run_json_hash = hashlib.sha256(run_json_canonical.encode("utf-8")).hexdigest()[:16]

    # 5. Build manifest.json data
    manifest_files = ["run.json"]
    if getattr(request, "report_path", None):
        manifest_files.append("run-report.txt")
    manifest_data = {
        "schema_version": _SCHEMA_VERSION,
        "run_id": request.run_id,
        "run_json_hash": run_json_hash,
        "files": manifest_files,
    }

    # 6. Write files
    try:
        os.makedirs(run_dir, exist_ok=True)
        _write_json_atomically(run_json_data, run_json_path)
        _write_json_atomically(manifest_data, manifest_path)
    except OSError as e:
        codes.append(REASON_WRITE_FAILED)
        finished_at = request.clock_provider() if request.clock_provider else None
        return RunPersistenceResult(
            status=RunPersistenceStatus.REJECTED.value,
            reason_codes=tuple(codes),
            run_id=request.run_id,
            run_dir=run_dir,
            files_written=(),
            manifest_path=manifest_path,
            run_json_path=run_json_path,
            run_json_hash="",
            bytes_written=0,
            readback_ok=False,
            started_at=started_at,
            finished_at=finished_at,
            details=f"Write failed: {e}",
        )

    # 7. Compute bytes written
    bytes_written = 0
    try:
        bytes_written += os.path.getsize(run_json_path)
        bytes_written += os.path.getsize(manifest_path)
    except OSError:
        pass

    # 8. Readback check
    readback_ok = False
    try:
        with open(run_json_path, "r", encoding="utf-8") as f:
            readback_data = json.load(f)
        readback_id = readback_data.get("run_id", "")
        readback_ok = readback_id == request.run_id
    except (OSError, json.JSONDecodeError):
        readback_ok = False

    finished_at = request.clock_provider() if request.clock_provider else None

    return RunPersistenceResult(
        status=RunPersistenceStatus.PERSISTED.value,
        reason_codes=(),
        run_id=request.run_id,
        run_dir=run_dir,
        files_written=("run.json", "manifest.json"),
        manifest_path=manifest_path,
        run_json_path=run_json_path,
        run_json_hash=run_json_hash,
        bytes_written=bytes_written,
        readback_ok=readback_ok,
        started_at=started_at,
        finished_at=finished_at,
        details=None,
    )


# ---------------------------------------------------------------------------
# Load run record
# ---------------------------------------------------------------------------


def load_run_record(
    runs_root: str,
    run_id: str,
) -> RunPersistenceReadResult:
    """Load a persisted run record.

    Parameters
    ----------
    runs_root:
        Root directory for run records.
    run_id:
        The run ID to load.

    Returns
    -------
    RunPersistenceReadResult
        ``status="read_ok"`` when the record is loaded.
        ``status="not_found"`` when the record is missing.
        ``status="rejected"`` when validation fails.
    """
    codes: list[str] = []

    # 1. Validate run_id
    if not _RUN_ID_RE.match(run_id):
        codes.append(REASON_INVALID_RUN_ID)
        return RunPersistenceReadResult(
            status=RunPersistenceStatus.REJECTED.value,
            reason_codes=tuple(codes),
            run_id=run_id,
            record=None,
            stored_hash=None,
            recomputed_hash=None,
            hash_match=False,
            details=f"Invalid run_id: {run_id!r}",
        )

    # 2. Check run directory
    run_dir = os.path.join(runs_root, run_id)
    run_json_path = os.path.join(run_dir, "run.json")

    if not os.path.exists(run_json_path):
        return RunPersistenceReadResult(
            status=RunPersistenceStatus.NOT_FOUND.value,
            reason_codes=(),
            run_id=run_id,
            record=None,
            stored_hash=None,
            recomputed_hash=None,
            hash_match=False,
            details=f"Run record not found: {run_json_path}",
        )

    # 3. Read run.json
    try:
        with open(run_json_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        codes.append(REASON_READ_FAILED)
        return RunPersistenceReadResult(
            status=RunPersistenceStatus.REJECTED.value,
            reason_codes=tuple(codes),
            run_id=run_id,
            record=None,
            stored_hash=None,
            recomputed_hash=None,
            hash_match=False,
            details=f"Read failed: {e}",
        )

    # 4. Parse JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        codes.append(REASON_READ_FAILED)
        return RunPersistenceReadResult(
            status=RunPersistenceStatus.REJECTED.value,
            reason_codes=tuple(codes),
            run_id=run_id,
            record=None,
            stored_hash=None,
            recomputed_hash=None,
            hash_match=False,
            details=f"Malformed JSON: {e}",
        )

    if not isinstance(data, dict):
        codes.append(REASON_READ_FAILED)
        return RunPersistenceReadResult(
            status=RunPersistenceStatus.REJECTED.value,
            reason_codes=tuple(codes),
            run_id=run_id,
            record=None,
            stored_hash=None,
            recomputed_hash=None,
            hash_match=False,
            details="run.json is not a dict",
        )

    # 5. Verify run_id consistency
    stored_run_id = data.get("run_id", "")
    if stored_run_id != run_id:
        codes.append(REASON_HASH_MISMATCH)
        return RunPersistenceReadResult(
            status=RunPersistenceStatus.REJECTED.value,
            reason_codes=tuple(codes),
            run_id=run_id,
            record=None,
            stored_hash=None,
            recomputed_hash=None,
            hash_match=False,
            details=f"run_id mismatch: stored={stored_run_id!r}, requested={run_id!r}",
        )

    # 6. Compute hash
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    recomputed_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    # 7. Get stored hash from manifest
    manifest_path = os.path.join(run_dir, "manifest.json")
    stored_hash = None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        stored_hash = manifest_data.get("run_json_hash")
    except (OSError, json.JSONDecodeError):
        pass

    hash_match = stored_hash == recomputed_hash if stored_hash else False

    # 8. Build record
    record = PersistedRunRecord(
        schema_version=data.get("schema_version", ""),
        run_id=data.get("run_id", ""),
        run_json_hash=recomputed_hash,
        task_description_hash=data.get("task_description_hash", ""),
        task_description_redacted=data.get("task_description_redacted", ""),
        branch=data.get("branch", ""),
        base_branch=data.get("base_branch", ""),
        status=data.get("status", ""),
        reason_codes=tuple(data.get("reason_codes", [])),
        pipeline_status=data.get("pipeline_status"),
        pipeline_final_action=data.get("pipeline_final_action"),
        pipeline_has_blockers=data.get("pipeline_has_blockers"),
        git_boundary_status=data.get("git_boundary_status"),
        command_plan_summary=tuple(data.get("command_plan_summary", [])),
        execution_attempted=data.get("execution_attempted", False),
        execution_results_summary=tuple(data.get("execution_results_summary", [])),
        approval_summary=data.get("approval_summary", ""),
        artifact_hashes=dict(data.get("artifact_hashes", {})),
        warnings=tuple(data.get("warnings", [])),
        next_action=data.get("next_action", ""),
        started_at=data.get("started_at"),
        finished_at=data.get("finished_at"),
    )

    return RunPersistenceReadResult(
        status=RunPersistenceStatus.READ_OK.value,
        reason_codes=(),
        run_id=run_id,
        record=record,
        stored_hash=stored_hash,
        recomputed_hash=recomputed_hash,
        hash_match=hash_match,
        details=None,
    )

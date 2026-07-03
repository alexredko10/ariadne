"""Tests for the read-only decision-to-backlog trace summary."""

from __future__ import annotations

import copy
import inspect
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from task_intake.backlog_decision import (
    BacklogDecisionInput,
    BacklogDecisionType,
    record_human_decision,
)
from task_intake.decision_backlog_trace_summary import (
    DecisionTraceInput,
    DecisionTraceStatus,
    build_decision_trace,
    REASON_MISSING_BACKLOG_STORE,
    REASON_MISSING_DECISION_STORE,
)
from runner.improvement_backlog import (
    BacklogItemInput,
    enqueue_backlog_item,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_backlog_input(**overrides: object) -> BacklogItemInput:
    kwargs = {
        "candidate_ref": "candidate-abc123",
        "continuity_ref": "continuity-def456",
        "product_state_ref": "abc123",
        "source_reason_codes": ("missing_proof_refs",),
        "evidence_refs": ("pr-001", "capture-text-abc123def456"),
        "improvement_category": "self_improvement",
        "next_safe_action": "Review and merge the improvement candidate",
        "blocked_actions": ("Waiting for PR 0108 merge",),
        "drift_risks": ("Scope must not include frontend",),
        "requires_human_review": True,
        "phase_id": "phase-1",
        "run_id": "run-001",
        "output_path": "backlog/item.json",
        "session_label": "PR 0115 backlog item",
    }
    kwargs.update(overrides)
    return BacklogItemInput(**kwargs)  # type: ignore[arg-type]


def _valid_decision_input(**overrides: object) -> BacklogDecisionInput:
    kwargs = {
        "backlog_item_ref": "backlog-item-abc123",
        "decision_type": BacklogDecisionType.DEFER.value,
        "human_actor": "human-reviewer-001",
        "decision_reason": "Need more evidence before proceeding.",
        "evidence_refs": ("pr-001", "capture-text-abc123def456"),
        "next_human_action": "Gather additional evidence from PR 0115.",
        "candidate_ref": "candidate-abc123",
        "continuity_ref": "continuity-def456",
    }
    kwargs.update(overrides)
    return BacklogDecisionInput(**kwargs)  # type: ignore[arg-type]


def _backlog_store(tmp_path: Path, name: str = "backlog") -> str:
    return str(tmp_path / name)


def _decision_store(tmp_path: Path, name: str = "decisions") -> str:
    return str(tmp_path / name)


def _enqueue_item(tmp_path: Path, store: str, **overrides: object) -> str:
    inp = _valid_backlog_input(**overrides)
    result = enqueue_backlog_item(inp, backlog_store_dir=store, output_dir=str(tmp_path))
    assert result.status == "enqueued", f"reason_codes={result.reason_codes}"
    assert result.backlog_item is not None
    return result.backlog_item.backlog_item_ref


def _record_decision(store: str, **overrides: object) -> str:
    inp = _valid_decision_input(decision_store_dir=store, **overrides)
    result = record_human_decision(inp)
    assert result.status == "recorded", f"reason_codes={result.reason_codes}"
    assert result.decision_ref is not None
    return result.decision_ref


def _plain(value: Any) -> Any:
    """Convert dataclasses / nested objects into comparable plain structures."""
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if hasattr(value, "__dict__"):
        return _plain(vars(value))
    return value


def _walk(value: Any) -> list[Any]:
    """Flatten a nested structure into all contained values."""
    out: list[Any] = []

    def visit(node: Any) -> None:
        out.append(node)
        if isinstance(node, dict):
            for key, val in node.items():
                visit(key)
                visit(val)
        elif isinstance(node, list):
            for val in node:
                visit(val)

    visit(_plain(value))
    return out


def _contains(value: Any, expected: str) -> bool:
    return any(str(node) == expected or expected in str(node) for node in _walk(value))


def _jsonable(value: Any) -> str:
    return json.dumps(_plain(value), sort_keys=True, default=str)


def _status_name(value: Any) -> str:
    status = _plain(value).get("status") if isinstance(_plain(value), dict) else getattr(value, "status", None)
    if hasattr(status, "value"):
        return str(status.value)
    return str(status)


def _reason_codes(value: Any) -> set[str]:
    plain = _plain(value)
    raw = plain.get("reason_codes", []) if isinstance(plain, dict) else getattr(value, "reason_codes", [])
    return {str(item) for item in raw}


def _trace_items(result: Any) -> list[Any]:
    plain = _plain(result)

    candidates: list[Any] = []
    if isinstance(plain, dict):
        for key in ("items", "trace_items", "traces"):
            value = plain.get(key)
            if isinstance(value, list):
                candidates = value
                break

        summary = plain.get("summary")
        if not candidates and isinstance(summary, dict):
            for key in ("items", "trace_items", "traces"):
                value = summary.get(key)
                if isinstance(value, list):
                    candidates = value
                    break

    assert candidates, f"trace result did not expose item list: {plain}"
    return candidates


def _make_trace_input(tmp_path: Path, backlog_store: str, decision_store: str, **overrides: object) -> DecisionTraceInput:
    """Create DecisionTraceInput while tolerating small field-name differences."""
    sig = inspect.signature(DecisionTraceInput)
    kwargs: dict[str, object] = {}

    for name, param in sig.parameters.items():
        if name in overrides:
            kwargs[name] = overrides[name]
            continue

        lowered = name.lower()

        if "backlog" in lowered and ("store" in lowered or "dir" in lowered or "path" in lowered):
            kwargs[name] = backlog_store
        elif ("decision" in lowered or "history" in lowered) and (
            "store" in lowered or "dir" in lowered or "path" in lowered
        ):
            kwargs[name] = decision_store
        elif name in {"root_dir", "workspace_dir", "base_dir", "output_dir"}:
            kwargs[name] = str(tmp_path)
        elif name in {"limit", "max_items", "max_trace_items"}:
            kwargs[name] = 100
        elif name in {"include_unresolved", "include_missing", "include_missing_evidence"}:
            kwargs[name] = True
        elif param.default is not inspect.Parameter.empty:
            continue
        else:
            raise AssertionError(f"DecisionTraceInput has unsupported required field: {name}")

    return DecisionTraceInput(**kwargs)  # type: ignore[arg-type]


def _build_trace(tmp_path: Path, backlog_store: str, decision_store: str, **overrides: object) -> Any:
    inp = _make_trace_input(tmp_path, backlog_store, decision_store, **overrides)
    return build_decision_trace(inp)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_decision_trace_summary_includes_decision_backlog_and_evidence_refs(tmp_path: Path) -> None:
    backlog_store = _backlog_store(tmp_path)
    decision_store = _decision_store(tmp_path)

    backlog_item_ref = _enqueue_item(
        tmp_path,
        backlog_store,
        candidate_ref="candidate-abc123",
        evidence_refs=("proof-ref-001", "capture-ref-001"),
    )
    decision_ref = _record_decision(
        decision_store,
        backlog_item_ref=backlog_item_ref,
        candidate_ref="candidate-abc123",
        evidence_refs=("decision-proof-001",),
    )

    result = _build_trace(tmp_path, backlog_store, decision_store)
    result_json = _jsonable(result)

    assert _status_name(result).lower() in {"ready", "ok", "success", DecisionTraceStatus.READY.value.lower()}
    assert decision_ref in result_json
    assert backlog_item_ref in result_json
    assert "candidate-abc123" in result_json
    assert "decision-proof-001" in result_json
    assert "proof-ref-001" in result_json or "capture-ref-001" in result_json

    items = _trace_items(result)
    assert len(items) >= 1


def test_decision_trace_summary_orders_items_deterministically(tmp_path: Path) -> None:
    backlog_store = _backlog_store(tmp_path)
    decision_store = _decision_store(tmp_path)

    first_backlog_ref = _enqueue_item(
        tmp_path,
        backlog_store,
        candidate_ref="candidate-001",
        evidence_refs=("proof-ref-001",),
    )
    second_backlog_ref = _enqueue_item(
        tmp_path,
        backlog_store,
        candidate_ref="candidate-002",
        evidence_refs=("proof-ref-002",),
    )

    _record_decision(
        decision_store,
        backlog_item_ref=second_backlog_ref,
        candidate_ref="candidate-002",
        evidence_refs=("decision-proof-002",),
    )
    _record_decision(
        decision_store,
        backlog_item_ref=first_backlog_ref,
        candidate_ref="candidate-001",
        evidence_refs=("decision-proof-001",),
    )

    first_result = _build_trace(tmp_path, backlog_store, decision_store)
    second_result = _build_trace(tmp_path, backlog_store, decision_store)

    assert _jsonable(first_result) == _jsonable(second_result)

    items = _trace_items(first_result)
    serialized_items = [_jsonable(item) for item in items]
    assert serialized_items == sorted(serialized_items)


def test_decision_trace_summary_represents_unresolved_backlog_item_ref(tmp_path: Path) -> None:
    backlog_store = _backlog_store(tmp_path)
    decision_store = _decision_store(tmp_path)

    # Create the backlog store so the trace builder can run, but do not create
    # the specific backlog item referenced by the decision.
    _enqueue_item(
        tmp_path,
        backlog_store,
        candidate_ref="different-candidate",
        evidence_refs=("unrelated-proof",),
    )

    decision_ref = _record_decision(
        decision_store,
        backlog_item_ref="missing-backlog-item-ref",
        candidate_ref="candidate-missing",
        evidence_refs=("decision-proof-missing",),
    )

    result = _build_trace(tmp_path, backlog_store, decision_store)
    result_json = _jsonable(result)
    plain = _plain(result)

    assert decision_ref in result_json
    assert "decision-proof-missing" in result_json

    # The implementation represents unresolved backlog linkage as a partial
    # trace with an explicit untraced_decisions section.
    assert _status_name(result).lower() == "partial"
    assert "untraced_decisions" in result_json
    assert "partial" in result_json.lower()

    assert isinstance(plain, dict)
    assert isinstance(plain.get("untraced_decisions"), list)
    assert plain["untraced_decisions"], plain

def test_decision_trace_summary_reports_missing_store_inputs(tmp_path: Path) -> None:
    missing_backlog_store = _backlog_store(tmp_path, "missing-backlog")
    missing_decision_store = _decision_store(tmp_path, "missing-decisions")

    result = _build_trace(tmp_path, missing_backlog_store, missing_decision_store)
    reason_codes = _reason_codes(result)
    result_json = _jsonable(result).lower()

    assert (
        REASON_MISSING_BACKLOG_STORE in reason_codes
        or REASON_MISSING_DECISION_STORE in reason_codes
        or "missing" in result_json
    )


def test_decision_trace_summary_is_read_only(tmp_path: Path) -> None:
    backlog_store = _backlog_store(tmp_path)
    decision_store = _decision_store(tmp_path)

    backlog_item_ref = _enqueue_item(
        tmp_path,
        backlog_store,
        candidate_ref="candidate-readonly",
        evidence_refs=("proof-readonly",),
    )
    decision_ref = _record_decision(
        decision_store,
        backlog_item_ref=backlog_item_ref,
        candidate_ref="candidate-readonly",
        evidence_refs=("decision-proof-readonly",),
    )

    before_files = {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in sorted(tmp_path.rglob("*"))
        if path.is_file()
    }
    before_snapshot = copy.deepcopy(before_files)

    result = _build_trace(tmp_path, backlog_store, decision_store)

    after_files = {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in sorted(tmp_path.rglob("*"))
        if path.is_file()
    }

    assert before_snapshot == after_files
    assert decision_ref in _jsonable(result)
    assert backlog_item_ref in _jsonable(result)
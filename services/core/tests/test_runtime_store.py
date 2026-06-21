"""Tests for the runtime in-memory store."""

from __future__ import annotations

import pytest

from core.runtime_substrate import (
    RunState,
    StepBoundary,
    StepStatus,
    AgentRole,
    FinalReportDraft,
    create_run_state,
)
from core.runtime.verification import (
    VerificationEvidence,
    create_verification_evidence,
    _reset_evidence_store,
)
from core.runtime.store import (
    InMemoryRuntimeStore,
    RuntimeStoreError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run(run_id: str = "run-001") -> RunState:
    rs = create_run_state(run_id, "task-001", "p-001", "coding")
    rs.steps.append(
        StepBoundary(step_id="s1", agent_role=AgentRole.WORKER_CODER, status=StepStatus.COMPLETED)
    )
    rs.current_step_id = "s1"
    return rs


def _make_running_run(run_id: str = "run-001") -> RunState:
    rs = _make_run(run_id)
    rs.status = rs.status.__class__("running")
    return rs


def _make_evidence(evidence_id: str = "ev-001", step_id: str = "s1", status: str = "passed") -> VerificationEvidence:
    return create_verification_evidence(
        evidence_id=evidence_id,
        step_id=step_id,
        check_name="check",
        status=status,
    )


# ---------------------------------------------------------------------------
# create_run
# ---------------------------------------------------------------------------


class TestCreateRun:
    def test_creates_and_returns_run(self):
        store = InMemoryRuntimeStore()
        run = _make_run("run-001")
        stored = store.create_run(run)
        assert stored.run_id == "run-001"
        assert store.has_run("run-001")

    def test_empty_run_id_raises(self):
        store = InMemoryRuntimeStore()
        run = _make_run("")
        with pytest.raises(RuntimeStoreError) as exc:
            store.create_run(run)
        assert "must not be empty" in exc.value.reason

    def test_duplicate_run_id_raises(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_run("run-001"))
        with pytest.raises(RuntimeStoreError) as exc:
            store.create_run(_make_run("run-001"))
        assert "Duplicate" in exc.value.reason

    def test_create_run_stores_copy(self):
        store = InMemoryRuntimeStore()
        original = _make_run("run-001")
        stored = store.create_run(original)
        # Mutate original — stored should be unaffected
        original.run_id = "changed"
        retrieved = store.get_run("run-001")
        assert retrieved.run_id == "run-001"


# ---------------------------------------------------------------------------
# get_run
# ---------------------------------------------------------------------------


class TestGetRun:
    def test_returns_matching_run(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_run("run-001"))
        run = store.get_run("run-001")
        assert run.run_id == "run-001"

    def test_missing_run_raises(self):
        store = InMemoryRuntimeStore()
        with pytest.raises(RuntimeStoreError) as exc:
            store.get_run("nonexistent")
        assert "not found" in exc.value.reason

    def test_returns_copy(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_run("run-001"))
        r1 = store.get_run("run-001")
        r2 = store.get_run("run-001")
        # Mutation of r1 should not affect r2
        r1.task_id = "mutated"
        assert r2.task_id == "task-001"


# ---------------------------------------------------------------------------
# has_run
# ---------------------------------------------------------------------------


class TestHasRun:
    def test_exists(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_run("run-001"))
        assert store.has_run("run-001") is True

    def test_not_exists(self):
        store = InMemoryRuntimeStore()
        assert store.has_run("nonexistent") is False


# ---------------------------------------------------------------------------
# save_run
# ---------------------------------------------------------------------------


class TestSaveRun:
    def test_saves_and_returns(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_run("run-001"))
        run = store.get_run("run-001")
        run.task_id = "updated-task"
        saved = store.save_run(run)
        assert saved.task_id == "updated-task"

    def test_missing_run_raises(self):
        store = InMemoryRuntimeStore()
        run = _make_run("run-001")
        with pytest.raises(RuntimeStoreError) as exc:
            store.save_run(run)
        assert "not found" in exc.value.reason
        assert "create_run" in exc.value.reason


# ---------------------------------------------------------------------------
# list_runs
# ---------------------------------------------------------------------------


class TestListRuns:
    def test_empty_by_default(self):
        store = InMemoryRuntimeStore()
        assert store.list_runs() == []

    def test_returns_insertion_order(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_run("run-001"))
        store.create_run(_make_run("run-002"))
        store.create_run(_make_run("run-003"))
        ids = [r.run_id for r in store.list_runs()]
        assert ids == ["run-001", "run-002", "run-003"]

    def test_returns_copies(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_run("run-001"))
        runs = store.list_runs()
        runs[0].task_id = "mutated"
        # Store should remain unchanged
        assert store.get_run("run-001").task_id == "task-001"


# ---------------------------------------------------------------------------
# delete_run
# ---------------------------------------------------------------------------


class TestDeleteRun:
    def test_removes_run(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_run("run-001"))
        store.delete_run("run-001")
        assert store.has_run("run-001") is False

    def test_removes_evidence(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_running_run("run-001"))
        ev = _make_evidence("ev-001", "s1")
        store.attach_verification_evidence("run-001", ev)
        store.delete_run("run-001")
        assert store.get_evidence_for_run("run-001") == []

    def test_missing_run_raises(self):
        store = InMemoryRuntimeStore()
        with pytest.raises(RuntimeStoreError) as exc:
            store.delete_run("nonexistent")
        assert "not found" in exc.value.reason


# ---------------------------------------------------------------------------
# Evidence methods
# ---------------------------------------------------------------------------


class TestEvidenceMethods:
    def test_attach_and_get_evidence(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_running_run("run-001"))
        ev = _make_evidence("ev-001", "s1")
        store.attach_verification_evidence("run-001", ev)
        result = store.get_evidence_for_run("run-001")
        assert len(result) == 1
        assert result[0].evidence_id == "ev-001"

    def test_attach_to_nonexistent_run_raises(self):
        store = InMemoryRuntimeStore()
        ev = _make_evidence("ev-001", "s1")
        with pytest.raises(RuntimeStoreError):
            store.attach_verification_evidence("nonexistent", ev)

    def test_get_empty_for_no_evidence(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_run("run-001"))
        assert store.get_evidence_for_run("run-001") == []

    def test_summarize_after_attach(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_running_run("run-001"))
        store.attach_verification_evidence("run-001", _make_evidence("ev-001", "s1", "passed"))
        store.attach_verification_evidence("run-001", _make_evidence("ev-002", "s1", "failed"))
        summary = store.summarize_verification_evidence("run-001")
        assert summary["total"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1

    def test_build_final_report(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_running_run("run-001"))
        store.attach_verification_evidence("run-001", _make_evidence("ev-001", "s1", "passed"))
        report = store.build_final_report("run-001")
        assert isinstance(report, FinalReportDraft)
        assert report.run_id == "run-001"

    def test_validate_readiness_passes(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_running_run("run-001"))
        store.attach_verification_evidence("run-001", _make_evidence("ev-001", "s1", "passed"))
        store.validate_final_report_readiness("run-001")

    def test_validate_readiness_fails_with_failed_evidence(self):
        store = InMemoryRuntimeStore()
        store.create_run(_make_running_run("run-001"))
        store.attach_verification_evidence("run-001", _make_evidence("ev-001", "s1", "failed"))
        with pytest.raises(Exception):
            store.validate_final_report_readiness("run-001")

    def test_evidence_isolation_per_instance(self):
        store1 = InMemoryRuntimeStore()
        store2 = InMemoryRuntimeStore()
        store1.create_run(_make_running_run("run-001"))
        store2.create_run(_make_running_run("run-001"))
        store1.attach_verification_evidence("run-001", _make_evidence("ev-001", "s1", "passed"))
        assert len(store2.get_evidence_for_run("run-001")) == 0


# ---------------------------------------------------------------------------
# RuntimeStoreError
# ---------------------------------------------------------------------------


class TestRuntimeStoreError:
    def test_includes_operation(self):
        store = InMemoryRuntimeStore()
        try:
            store.get_run("nonexistent")
        except RuntimeStoreError as exc:
            assert exc.operation == "get_run"

    def test_includes_subject(self):
        store = InMemoryRuntimeStore()
        try:
            store.get_run("missing")
        except RuntimeStoreError as exc:
            assert exc.subject == "missing"

    def test_includes_reason(self):
        store = InMemoryRuntimeStore()
        try:
            store.get_run("missing")
        except RuntimeStoreError as exc:
            assert isinstance(exc.reason, str)
            assert len(exc.reason) > 0

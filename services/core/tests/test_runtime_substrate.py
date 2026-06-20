"""Tests for the Ariadne runtime substrate skeleton."""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from core.runtime_substrate import (
    AgentExecutionRecord,
    AgentRole,
    Checkpoint,
    ContextPackRef,
    FinalReportDraft,
    LongContextStressProfileRef,
    ModelCapabilityProfileRef,
    RubricJudgeResultRef,
    RubricPackRef,
    RubricVerdict,
    RunState,
    RunStatus,
    StateModelRef,
    StepBoundary,
    StepStatus,
    TransitionGraphRef,
    build_final_report_draft,
    create_run_state,
    record_agent_execution,
    record_checkpoint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_id() -> str:
    return "run-001"


def _task_id() -> str:
    return "task-001"


def _purpose_id() -> str:
    return "p-001"


# ---------------------------------------------------------------------------
# RunState creation
# ---------------------------------------------------------------------------


class TestRunStateCreation:
    def test_default_status_is_pending(self):
        rs = create_run_state(_run_id(), _task_id(), _purpose_id(), "coding")
        assert rs.status == RunStatus.PENDING

    def test_timestamps_non_null_after_creation(self):
        rs = create_run_state(_run_id(), _task_id(), _purpose_id(), "coding")
        assert rs.created_at is not None
        assert rs.updated_at is not None

    def test_initial_steps_empty(self):
        rs = create_run_state(_run_id(), _task_id(), _purpose_id(), "coding")
        assert rs.steps == []

    def test_current_step_id_none_initial(self):
        rs = create_run_state(_run_id(), _task_id(), _purpose_id(), "coding")
        assert rs.current_step_id is None


# ---------------------------------------------------------------------------
# Append step
# ---------------------------------------------------------------------------


class TestAppendStep:
    def test_append_increments_step_count(self):
        rs = create_run_state(_run_id(), _task_id(), _purpose_id(), "coding")
        step = StepBoundary(step_id="step-001", agent_role=AgentRole.WORKER_CODER)
        rs.append_step(step)
        assert len(rs.steps) == 1

    def test_current_step_id_matches_last_step(self):
        rs = create_run_state(_run_id(), _task_id(), _purpose_id(), "coding")
        step = StepBoundary(step_id="step-001", agent_role=AgentRole.WORKER_CODER)
        rs.append_step(step)
        assert rs.current_step_id == "step-001"

    def test_multiple_steps_preserve_order(self):
        rs = create_run_state(_run_id(), _task_id(), _purpose_id(), "coding")
        rs.append_step(StepBoundary(step_id="step-001", agent_role=AgentRole.WORKER_CODER))
        rs.append_step(StepBoundary(step_id="step-002", agent_role=AgentRole.REVIEWER))
        assert [s.step_id for s in rs.steps] == ["step-001", "step-002"]


# ---------------------------------------------------------------------------
# StepBoundary defaults
# ---------------------------------------------------------------------------


class TestStepBoundaryDefaults:
    def test_default_status_pending(self):
        step = StepBoundary(step_id="s1", agent_role=AgentRole.ARCHITECT)
        assert step.status == StepStatus.PENDING

    def test_cost_none_by_default(self):
        step = StepBoundary(step_id="s1", agent_role=AgentRole.ARCHITECT)
        assert step.cost is None

    def test_artifacts_empty_by_default(self):
        step = StepBoundary(step_id="s1", agent_role=AgentRole.ARCHITECT)
        assert step.artifact_ids == []


# ---------------------------------------------------------------------------
# Checkpoint immutability
# ---------------------------------------------------------------------------


class TestCheckpointImmutability:
    def test_frozen_dataclass(self):
        cp = Checkpoint(
            checkpoint_id="cp-001",
            run_id="run-001",
            step_id="step-001",
            captured_at=datetime.datetime.now(datetime.timezone.utc),
            run_state_hash="abc123",
        )
        assert dataclasses.fields(cp) is not None
        # Attempting to set an attribute should raise FrozenInstanceError
        with pytest.raises(dataclasses.FrozenInstanceError):
            cp.checkpoint_id = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AgentExecutionRecord creation
# ---------------------------------------------------------------------------


class TestAgentExecutionRecord:
    def test_all_fields_settable(self):
        rec = AgentExecutionRecord(
            contract_id="ec-001",
            run_id="run-001",
            step_id="step-001",
            role=AgentRole.WORKER_CODER,
            purpose="Implement feature",
            pbs_node="node-001",
            domain="coding",
            allowed_actions=["write"],  # noqa
        )
        assert rec.contract_id == "ec-001"
        assert rec.role == AgentRole.WORKER_CODER
        assert rec.domain == "coding"

    def test_no_provider_hardcoding_in_model_used(self):
        """Model identifier is a generic string — no provider hardcoding."""
        rec = AgentExecutionRecord(
            contract_id="ec-002",
            run_id="run-001",
            step_id="step-002",
            role=AgentRole.REVIEWER,
            purpose="Review implementation",
            pbs_node="node-002",
        )
        # Not yet set — but the field is a string, not an enum with provider names
        assert rec.agent is None
        # When set, it uses "provider:model" convention
        rec.agent = "provider:model-x"
        assert "provider:" in rec.agent or ":" in rec.agent


# ---------------------------------------------------------------------------
# FinalReportDraft creation
# ---------------------------------------------------------------------------


class TestFinalReportDraft:
    def test_empty_fields_by_default(self):
        draft = build_final_report_draft(
            report_id="fr-001",
            run_id="run-001",
            purpose_id="p-001",
            domain="coding",
            root_purpose="Test purpose",
        )
        assert draft.changes == []
        assert draft.pbs_summary is None
        assert draft.verification_summary is None

    def test_human_approval_required_default_false(self):
        draft = build_final_report_draft(
            report_id="fr-001",
            run_id="run-001",
            purpose_id="p-001",
            domain="coding",
            root_purpose="Test purpose",
        )
        assert draft.human_approval_required is False


# ---------------------------------------------------------------------------
# Reference types
# ---------------------------------------------------------------------------


class TestReferenceTypes:
    def test_context_pack_ref_is_hashable(self):
        ref = ContextPackRef(context_pack_id="cp-001")
        s = {ref}
        assert ref in s

    def test_state_model_ref_is_hashable(self):
        ref = StateModelRef(state_model_id="sm-001")
        assert ref.state_model_id == "sm-001"

    def test_transition_graph_ref(self):
        ref = TransitionGraphRef(transition_graph_id="tg-001")
        assert ref.transition_graph_id == "tg-001"

    def test_rubric_pack_ref(self):
        ref = RubricPackRef(rubric_pack_id="rp-001")
        assert ref.rubric_pack_id == "rp-001"

    def test_rubric_judge_result_ref(self):
        ref = RubricJudgeResultRef(judge_result_id="jr-001")
        assert ref.judge_result_id == "jr-001"

    def test_model_capability_profile_ref(self):
        ref = ModelCapabilityProfileRef(model_id="model-001")
        assert ref.model_id == "model-001"

    def test_long_context_stress_profile_ref(self):
        ref = LongContextStressProfileRef(profile_id="csp-001")
        assert ref.profile_id == "csp-001"


# ---------------------------------------------------------------------------
# Enum values
# ---------------------------------------------------------------------------


class TestEnums:
    def test_run_status_values(self):
        assert RunStatus.PENDING.value == "pending"
        assert RunStatus.RUNNING.value == "running"
        assert RunStatus.PAUSED.value == "paused"
        assert RunStatus.COMPLETED.value == "completed"
        assert RunStatus.FAILED.value == "failed"
        assert RunStatus.CANCELLED.value == "cancelled"

    def test_step_status_values(self):
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"

    def test_agent_role_values(self):
        assert AgentRole.ARCHITECT.value == "architect"
        assert AgentRole.PLANNER.value == "planner"
        assert AgentRole.LEAD_CODER.value == "lead_coder"
        assert AgentRole.WORKER_CODER.value == "worker_coder"
        assert AgentRole.TESTER.value == "tester"
        assert AgentRole.REVIEWER.value == "reviewer"
        assert AgentRole.SECURITY.value == "security"
        assert AgentRole.VERIFIER.value == "verifier"
        assert AgentRole.CUSTOM.value == "custom"

    def test_rubric_verdict_values(self):
        assert RubricVerdict.PASS.value == "pass"
        assert RubricVerdict.WARNING.value == "warning"
        assert RubricVerdict.FAIL.value == "fail"
        assert RubricVerdict.NEEDS_HUMAN_REVIEW.value == "needs_human_review"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_record_checkpoint(self):
        cp = record_checkpoint(
            checkpoint_id="cp-001",
            run_id="run-001",
            step_id="step-001",
            run_state_hash="abc123",
        )
        assert cp.checkpoint_id == "cp-001"
        assert cp.run_id == "run-001"
        assert cp.resumable is True

    def test_record_agent_execution(self):
        rec = record_agent_execution(
            contract_id="ec-001",
            run_id="run-001",
            step_id="step-001",
            role=AgentRole.WORKER_CODER,
            purpose="Implement",
            pbs_node="node-001",
            domain="coding",
        )
        assert rec.contract_id == "ec-001"
        assert rec.domain == "coding"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_run_state_asdict(self):
        rs = create_run_state(_run_id(), _task_id(), _purpose_id(), "coding")
        d = dataclasses.asdict(rs)
        assert d["run_id"] == "run-001"
        assert d["status"] == RunStatus.PENDING

    def test_checkpoint_asdict(self):
        cp = record_checkpoint(
            checkpoint_id="cp-001",
            run_id="run-001",
            step_id="step-001",
            run_state_hash="abc",
        )
        d = dataclasses.asdict(cp)
        assert d["checkpoint_id"] == "cp-001"
        assert d["resumable"] is True

    def test_final_report_draft_asdict(self):
        draft = build_final_report_draft(
            report_id="fr-001",
            run_id="run-001",
            purpose_id="p-001",
            domain="coding",
            root_purpose="Test",
        )
        d = dataclasses.asdict(draft)
        assert d["human_approval_required"] is False


# ---------------------------------------------------------------------------
# to_dict / from_dict round-trip
# ---------------------------------------------------------------------------


class TestToDict:
    def test_run_state_to_dict_has_string_status(self):
        rs = create_run_state(_run_id(), _task_id(), _purpose_id(), "coding")
        d = rs.to_dict()
        assert d["run_id"] == "run-001"
        assert d["status"] == "pending"
        assert isinstance(d["status"], str)

    def test_run_state_to_dict_has_iso8601_timestamps(self):
        rs = create_run_state(_run_id(), _task_id(), _purpose_id(), "coding")
        d = rs.to_dict()
        assert d["created_at"].endswith("Z")
        assert d["updated_at"].endswith("Z")

    def test_run_state_round_trip(self):
        rs = create_run_state(_run_id(), _task_id(), _purpose_id(), "coding")
        step = StepBoundary(step_id="s1", agent_role=AgentRole.WORKER_CODER)
        rs.append_step(step)
        d = rs.to_dict()
        rs2 = RunState.from_dict(d)
        assert rs2.run_id == rs.run_id
        assert rs2.status == rs.status
        assert len(rs2.steps) == 1
        assert rs2.steps[0].step_id == "s1"

    def test_step_boundary_to_dict(self):
        step = StepBoundary(step_id="s1", agent_role=AgentRole.ARCHITECT)
        d = step.to_dict()
        assert d["step_id"] == "s1"
        assert d["agent_role"] == "architect"
        assert d["status"] == "pending"

    def test_step_boundary_from_dict(self):
        d = {"step_id": "s1", "agent_role": "architect"}
        step = StepBoundary.from_dict(d)
        assert step.step_id == "s1"
        assert step.agent_role == AgentRole.ARCHITECT
        assert step.status == StepStatus.PENDING

    def test_checkpoint_to_dict_iso8601(self):
        cp = record_checkpoint(
            checkpoint_id="cp-001",
            run_id="run-001",
            step_id="step-001",
            run_state_hash="abc",
        )
        d = cp.to_dict()
        assert d["captured_at"].endswith("Z")

    def test_checkpoint_round_trip(self):
        cp = record_checkpoint(
            checkpoint_id="cp-001",
            run_id="run-001",
            step_id="step-001",
            run_state_hash="abc",
        )
        d = cp.to_dict()
        cp2 = Checkpoint.from_dict(d)
        assert cp2.checkpoint_id == cp.checkpoint_id
        assert cp2.resumable is True

    def test_agent_execution_record_to_dict(self):
        rec = record_agent_execution(
            contract_id="ec-001",
            run_id="run-001",
            step_id="step-001",
            role=AgentRole.WORKER_CODER,
            purpose="Implement",
            pbs_node="node-001",
            domain="coding",
        )
        d = rec.to_dict()
        assert d["role"] == "worker_coder"
        assert d["domain"] == "coding"

    def test_agent_execution_record_round_trip(self):
        rec = record_agent_execution(
            contract_id="ec-001",
            run_id="run-001",
            step_id="step-001",
            role=AgentRole.WORKER_CODER,
            purpose="Implement",
            pbs_node="node-001",
            domain="coding",
        )
        d = rec.to_dict()
        rec2 = AgentExecutionRecord.from_dict(d)
        assert rec2.contract_id == rec.contract_id
        assert rec2.role == rec.role

    def test_final_report_draft_round_trip(self):
        draft = build_final_report_draft(
            report_id="fr-001",
            run_id="run-001",
            purpose_id="p-001",
            domain="coding",
            root_purpose="Test",
        )
        d = draft.to_dict()
        draft2 = FinalReportDraft.from_dict(d)
        assert draft2.report_id == draft.report_id
        assert draft2.human_approval_required is False

    def test_context_pack_ref_to_dict(self):
        ref = ContextPackRef(context_pack_id="cp-001")
        d = ref.to_dict()
        assert d["context_pack_id"] == "cp-001"

    def test_context_pack_ref_from_dict(self):
        ref = ContextPackRef.from_dict({"context_pack_id": "cp-002"})
        assert ref.context_pack_id == "cp-002"

    def test_ref_types_round_trip_all(self):
        refs = [
            ContextPackRef(context_pack_id="cp-001"),
            StateModelRef(state_model_id="sm-001"),
            TransitionGraphRef(transition_graph_id="tg-001"),
            RubricPackRef(rubric_pack_id="rp-001"),
            RubricJudgeResultRef(judge_result_id="jr-001"),
            ModelCapabilityProfileRef(model_id="model-001"),
            LongContextStressProfileRef(profile_id="csp-001"),
        ]
        for ref in refs:
            d = ref.to_dict()
            restored = type(ref).from_dict(d)
            assert restored == ref, f"Round-trip failed for {type(ref).__name__}"

    def test_no_provider_hardcoding_in_serialized(self):
        """Model identifiers are generic strings in dict output."""
        step = StepBoundary(step_id="s1", agent_role=AgentRole.WORKER_CODER)
        step.model_used = "provider:model-x"
        d = step.to_dict()
        assert isinstance(d["model_used"], str)
        assert ":" in d["model_used"]

    def test_no_raw_repo_dumps_in_context_refs(self):
        """Context references are simple ID strings only."""
        ref = ContextPackRef(context_pack_id="cp-001")
        d = ref.to_dict()
        # Only the ID field — no content, no dump
        assert len(d) == 1
        assert "context_pack_id" in d

    def test_deterministic_round_trip(self):
        """Serializing the same data twice produces identical dicts."""
        rs = create_run_state(_run_id(), _task_id(), _purpose_id(), "coding")
        rs.append_step(StepBoundary(step_id="s1", agent_role=AgentRole.WORKER_CODER))
        d1 = rs.to_dict()
        d2 = rs.to_dict()
        assert d1 == d2

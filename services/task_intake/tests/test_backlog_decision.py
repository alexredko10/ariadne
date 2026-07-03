"""Tests for the human backlog decision intake layer."""

from __future__ import annotations

import json
import os
from pathlib import Path

from task_intake.backlog_decision import (
    BacklogDecisionInput,
    BacklogDecisionRecord,
    BacklogDecisionResult,
    BacklogDecisionType,
    record_human_decision,
    REASON_MISSING_BACKLOG_ITEM_REF,
    REASON_INVALID_DECISION_TYPE,
    REASON_MISSING_HUMAN_ACTOR,
    REASON_MISSING_DECISION_REASON,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
    REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED,
    REASON_MUTATION_NOT_ALLOWED,
    REASON_ARCHIVE_NOT_ALLOWED,
    REASON_APPROVAL_NOT_ALLOWED,
    REASON_GATE_FINALIZATION_NOT_ALLOWED,
    REASON_COMMAND_EXECUTION_NOT_ALLOWED,
    REASON_PROVIDER_CALL_NOT_ALLOWED,
    REASON_GIT_MUTATION_NOT_ALLOWED,
    REASON_DUPLICATE_DECISION_REF,
    REASON_UNBOUNDED_DECISION_STORE_PATH,
    REASON_OVERSIZED_DECISION_PAYLOAD,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_input(**overrides: object) -> BacklogDecisionInput:
    kwargs = {
        "backlog_item_ref": "backlog-item-abc123",
        "decision_type": BacklogDecisionType.DEFER.value,
        "human_actor": "human-reviewer-001",
        "decision_reason": "Need more evidence before proceeding.",
        "evidence_refs": ("pr-001", "capture-text-abc123def456"),
        "next_human_action": "Gather additional evidence from PR 0113.",
        "candidate_ref": "candidate-abc123",
        "continuity_ref": "continuity-def456",
    }
    kwargs.update(overrides)
    return BacklogDecisionInput(**kwargs)  # type: ignore[arg-type]


def _store_dir(tmp_path: Path, name: str = "decisions") -> str:
    """Return a unique decision store directory path."""
    return str(tmp_path / name)


# ---------------------------------------------------------------------------
# Valid decision
# ---------------------------------------------------------------------------


class TestValidDecision:
    def test_valid_decision_recorded(self, tmp_path: Path):
        """Valid decision → status recorded, decision_ref present."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store)
        result = record_human_decision(inp)
        assert result.status == "recorded"
        assert result.decision_ref is not None
        assert len(result.decision_ref) == 16
        assert result.decision_record is not None
        assert result.decision_record.backlog_item_ref == "backlog-item-abc123"
        assert result.decision_record.decision_type == BacklogDecisionType.DEFER.value
        assert result.decision_record.human_actor == "human-reviewer-001"
        assert result.decision_record.decision_reason == "Need more evidence before proceeding."
        assert result.decision_record.created_at is None

    def test_decision_file_written(self, tmp_path: Path):
        """Decision JSON file is written to store."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store)
        result = record_human_decision(inp)
        assert result.status == "recorded"
        assert result.decision_ref is not None
        decision_file = Path(store) / f"{result.decision_ref}.json"
        assert decision_file.exists()
        data = json.loads(decision_file.read_text(encoding="utf-8"))
        assert data["decision_ref"] == result.decision_ref
        assert data["backlog_item_ref"] == "backlog-item-abc123"
        assert data["decision_type"] == BacklogDecisionType.DEFER.value
        assert data["human_actor"] == "human-reviewer-001"
        assert data["decision_reason"] == "Need more evidence before proceeding."
        assert data["created_at"] is None

    def test_all_decision_types(self, tmp_path: Path):
        """All BacklogDecisionType values are accepted."""
        store = _store_dir(tmp_path)
        for dt in BacklogDecisionType:
            inp = _valid_input(
                decision_store_dir=store,
                decision_type=dt.value,
                backlog_item_ref=f"backlog-item-{dt.value}",
            )
            result = record_human_decision(inp)
            assert result.status == "recorded", f"Failed for {dt.value}: {result.reason_codes}"


# ---------------------------------------------------------------------------
# Deterministic decision_ref
# ---------------------------------------------------------------------------


class TestDeterministicRef:
    def test_same_input_same_ref(self, tmp_path: Path):
        """Same input → same decision_ref."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store)
        result1 = record_human_decision(inp)
        assert result1.status == "recorded"
        ref1 = result1.decision_ref

        # Different store dir → different ref (because store dir is not part of canonical)
        store2 = _store_dir(tmp_path, "decisions2")
        inp2 = _valid_input(decision_store_dir=store2)
        result2 = record_human_decision(inp2)
        assert result2.status == "recorded"
        ref2 = result2.decision_ref

        # Same canonical input → same ref regardless of store dir
        assert ref1 == ref2


# ---------------------------------------------------------------------------
# Decision includes all required fields
# ---------------------------------------------------------------------------


class TestDecisionFields:
    def test_decision_includes_all_fields(self, tmp_path: Path):
        """Decision record includes all required fields."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store)
        result = record_human_decision(inp)
        assert result.status == "recorded"
        assert result.decision_record is not None
        record = result.decision_record
        assert record.decision_ref is not None
        assert record.backlog_item_ref == "backlog-item-abc123"
        assert record.decision_type == BacklogDecisionType.DEFER.value
        assert record.human_actor == "human-reviewer-001"
        assert record.decision_reason == "Need more evidence before proceeding."
        assert record.evidence_refs == ("capture-text-abc123def456", "pr-001")
        assert record.next_human_action == "Gather additional evidence from PR 0113."
        assert record.candidate_ref == "candidate-abc123"
        assert record.continuity_ref == "continuity-def456"
        assert record.created_at is None


# ---------------------------------------------------------------------------
# Missing backlog_item_ref
# ---------------------------------------------------------------------------


class TestMissingBacklogItemRef:
    def test_missing_ref_rejected(self, tmp_path: Path):
        """Missing backlog_item_ref → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, backlog_item_ref="")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_MISSING_BACKLOG_ITEM_REF in result.reason_codes


# ---------------------------------------------------------------------------
# Missing human_actor
# ---------------------------------------------------------------------------


class TestMissingHumanActor:
    def test_missing_actor_rejected(self, tmp_path: Path):
        """Missing human_actor → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, human_actor="")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_MISSING_HUMAN_ACTOR in result.reason_codes


# ---------------------------------------------------------------------------
# Missing decision_reason
# ---------------------------------------------------------------------------


class TestMissingDecisionReason:
    def test_missing_reason_rejected(self, tmp_path: Path):
        """Missing decision_reason → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, decision_reason="")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_MISSING_DECISION_REASON in result.reason_codes


# ---------------------------------------------------------------------------
# Invalid decision_type
# ---------------------------------------------------------------------------


class TestInvalidDecisionType:
    def test_invalid_type_rejected(self, tmp_path: Path):
        """Invalid decision_type → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, decision_type="invalid_type")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_INVALID_DECISION_TYPE in result.reason_codes


# ---------------------------------------------------------------------------
# Hidden reasoning
# ---------------------------------------------------------------------------


class TestHiddenReasoning:
    def test_hidden_reasoning_rejected(self, tmp_path: Path):
        """Hidden reasoning in decision_reason → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, decision_reason="Some text <cot> hidden")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# External URL-only evidence
# ---------------------------------------------------------------------------


class TestExternalUrlOnly:
    def test_external_url_only_rejected(self, tmp_path: Path):
        """URL-only decision_reason → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, decision_reason="http://example.com/evidence")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Duplicate decision
# ---------------------------------------------------------------------------


class TestDuplicateDecision:
    def test_duplicate_decision_returns_duplicate(self, tmp_path: Path):
        """Duplicate decision → status duplicate."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store)
        result1 = record_human_decision(inp)
        assert result1.status == "recorded"

        result2 = record_human_decision(inp)
        assert result2.status == "duplicate"
        assert REASON_DUPLICATE_DECISION_REF in result2.reason_codes
        assert result2.decision_ref == result1.decision_ref


# ---------------------------------------------------------------------------
# Decision does NOT mutate backlog item files
# ---------------------------------------------------------------------------


class TestNoBacklogMutation:
    def test_decision_does_not_mutate_backlog(self, tmp_path: Path):
        """Decision does not write to backlog store."""
        store = _store_dir(tmp_path)
        backlog_store = tmp_path / "backlog"
        os.makedirs(backlog_store, exist_ok=True)
        # Write a backlog item
        backlog_file = backlog_store / "backlog-item-abc123.json"
        backlog_file.write_text('{"backlog_item_ref": "backlog-item-abc123"}', encoding="utf-8")
        backlog_mtime = backlog_file.stat().st_mtime

        inp = _valid_input(decision_store_dir=store)
        result = record_human_decision(inp)
        assert result.status == "recorded"

        # Backlog file unchanged
        assert backlog_file.exists()
        assert backlog_file.stat().st_mtime == backlog_mtime
        assert backlog_file.read_text(encoding="utf-8") == '{"backlog_item_ref": "backlog-item-abc123"}'


# ---------------------------------------------------------------------------
# Decision does NOT archive backlog items
# ---------------------------------------------------------------------------


class TestNoArchive:
    def test_archive_pattern_rejected(self, tmp_path: Path):
        """Archive pattern in decision_reason → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, decision_reason="archive this item")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_ARCHIVE_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Decision does NOT approve gates
# ---------------------------------------------------------------------------


class TestNoApproval:
    def test_approval_pattern_rejected(self, tmp_path: Path):
        """Approval pattern in decision_reason → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, decision_reason="approve the gate")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_APPROVAL_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# No filesystem writes outside decisions dir
# ---------------------------------------------------------------------------


class TestNoFilesystemWritesOutside:
    def test_no_writes_outside_decisions(self, tmp_path: Path):
        """Only decision files are written."""
        store = _store_dir(tmp_path)
        # Record files before
        files_before = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_before.add(os.path.relpath(os.path.join(root, f), tmp_path))
        inp = _valid_input(decision_store_dir=store)
        result = record_human_decision(inp)
        assert result.status == "recorded"
        # Record files after
        files_after = set()
        for root, dirs, files in os.walk(tmp_path):
            for f in files:
                files_after.add(os.path.relpath(os.path.join(root, f), tmp_path))
        # Only the decision file was added
        assert len(files_after) == len(files_before) + 1


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self, tmp_path: Path):
        """Uses tmp_path, not .ariadne/."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store)
        result = record_human_decision(inp)
        assert result.status == "recorded"
        # Verify no .ariadne/ was created
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# Mutation not allowed
# ---------------------------------------------------------------------------


class TestMutationNotAllowed:
    def test_mutation_pattern_rejected(self, tmp_path: Path):
        """Mutation pattern in decision_reason → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, decision_reason="accept the changes")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_MUTATION_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Gate finalization not allowed
# ---------------------------------------------------------------------------


class TestGateFinalizationNotAllowed:
    def test_gate_finalization_rejected(self, tmp_path: Path):
        """Gate finalization pattern in decision_reason → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, decision_reason="finalize the gate")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_GATE_FINALIZATION_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Command execution not allowed
# ---------------------------------------------------------------------------


class TestCommandExecutionNotAllowed:
    def test_command_execution_rejected(self, tmp_path: Path):
        """Command execution pattern in decision_reason → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, decision_reason="subprocess.run('ls')")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_COMMAND_EXECUTION_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Provider call not allowed
# ---------------------------------------------------------------------------


class TestProviderCallNotAllowed:
    def test_provider_call_rejected(self, tmp_path: Path):
        """Provider call pattern in decision_reason → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, decision_reason="import openai to fix this")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_PROVIDER_CALL_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Git mutation not allowed
# ---------------------------------------------------------------------------


class TestGitMutationNotAllowed:
    def test_git_mutation_rejected(self, tmp_path: Path):
        """Git mutation pattern in decision_reason → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, decision_reason="git commit -m 'fix'")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_GIT_MUTATION_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Unbounded decision store path
# ---------------------------------------------------------------------------


class TestUnboundedPath:
    def test_unbounded_path_rejected(self, tmp_path: Path):
        """Unbounded decision store path → rejected."""
        inp = _valid_input(decision_store_dir="../etc/passwd")
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_UNBOUNDED_DECISION_STORE_PATH in result.reason_codes


# ---------------------------------------------------------------------------
# Oversized decision payload
# ---------------------------------------------------------------------------


class TestOversizedPayload:
    def test_oversized_payload_rejected(self, tmp_path: Path):
        """Oversized decision payload → rejected."""
        store = _store_dir(tmp_path)
        inp = _valid_input(decision_store_dir=store, decision_reason="x" * 200_000)
        result = record_human_decision(inp)
        assert result.status == "rejected"
        assert REASON_OVERSIZED_DECISION_PAYLOAD in result.reason_codes


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import task_intake.backlog_decision
        doc = task_intake.backlog_decision.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from task_intake.backlog_decision import record_human_decision
        source = inspect.getsource(record_human_decision)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"

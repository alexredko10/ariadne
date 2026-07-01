"""Tests for the deterministic acceptance criteria freeze runtime object."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from runner.acceptance_criteria import (
    AcceptanceCriterion,
    AcceptanceCriteriaFreezeInput,
    AcceptanceCriteriaFreezeResult,
    AcceptanceCriteriaFreezeStatus,
    freeze_acceptance_criteria,
    REASON_DUPLICATE_CRITERION_ID,
    REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
    REASON_MISSING_CRITERIA,
    REASON_MISSING_CRITERION_ID,
    REASON_MISSING_CRITERION_TEXT,
    REASON_MISSING_OUTPUT_PATH,
    REASON_MISSING_PRODUCT_STATE_REF,
    REASON_OVERSIZED_CRITERIA_SET,
    REASON_UNBOUNDED_CRITERION_TEXT,
    REASON_UNBOUNDED_OUTPUT_PATH,
)
from runner.proof_capture import (
    ProofCaptureInput,
    capture_proof,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_input(**overrides: object) -> AcceptanceCriteriaFreezeInput:
    kwargs = {
        "product_state_ref": "abc123",
        "criteria": (
            AcceptanceCriterion(criterion_id="AC-001", description="System must return exit code 0 on success."),
            AcceptanceCriterion(criterion_id="AC-002", description="System must reject invalid input with exit code 1."),
        ),
        "phase_id": "phase-1",
        "run_id": "run-001",
        "output_path": "criteria/frozen.json",
        "title": "PR 0105 acceptance criteria",
    }
    kwargs.update(overrides)
    return AcceptanceCriteriaFreezeInput(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Valid freeze
# ---------------------------------------------------------------------------


class TestValidFreeze:
    def test_valid_freeze_writes_deterministic_artifact(self, tmp_path: Path):
        """Valid input writes artifact JSON and returns FROZEN."""
        inp = _valid_input()
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.FROZEN
        assert result.reason_codes == ()
        assert result.artifact_path is not None
        assert result.acceptance_criteria_ref is not None
        assert result.criteria_count == 2
        assert result.criterion_ids == ("AC-001", "AC-002")

        # Verify artifact was written
        artifact_file = tmp_path / result.artifact_path
        assert artifact_file.exists()
        artifact = json.loads(artifact_file.read_text(encoding="utf-8"))
        assert artifact["ariadne_acceptance_criteria_version"] == "1"
        assert artifact["product_state_ref"] == "abc123"
        assert artifact["frozen_at"] is None
        assert len(artifact["criteria"]) == 2

    def test_valid_freeze_returns_acceptance_criteria_ref(self, tmp_path: Path):
        """Ref is non-empty and starts with hex chars."""
        inp = _valid_input()
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.FROZEN
        ref = result.acceptance_criteria_ref
        assert ref is not None
        assert len(ref) == 16
        int(ref, 16)  # should not raise

    def test_frozen_artifact_deterministic_key_ordering(self, tmp_path: Path):
        """sort_keys=True ensures consistent key order."""
        inp = _valid_input()
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        artifact_file = tmp_path / result.artifact_path
        content = artifact_file.read_text(encoding="utf-8")
        # Parse and re-serialize to verify determinism
        parsed = json.loads(content)
        re_serialized = json.dumps(parsed, sort_keys=True, indent=2)
        assert content == re_serialized

    def test_same_input_same_reference(self, tmp_path: Path):
        """Freezing same input twice produces same acceptance_criteria_ref."""
        inp = _valid_input()
        result1 = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        result2 = freeze_acceptance_criteria(inp, output_dir=str(tmp_path / "other"))
        assert result1.acceptance_criteria_ref == result2.acceptance_criteria_ref

    def test_changing_criterion_text_changes_reference(self, tmp_path: Path):
        """Different description produces different ref."""
        inp1 = _valid_input()
        inp2 = _valid_input(
            criteria=(
                AcceptanceCriterion(criterion_id="AC-001", description="Original description."),
                AcceptanceCriterion(criterion_id="AC-002", description="Changed description."),
            ),
        )
        result1 = freeze_acceptance_criteria(inp1, output_dir=str(tmp_path))
        result2 = freeze_acceptance_criteria(inp2, output_dir=str(tmp_path / "other"))
        assert result1.acceptance_criteria_ref != result2.acceptance_criteria_ref

    def test_criteria_sorted_by_id_in_artifact(self, tmp_path: Path):
        """Criteria in artifact JSON sorted by criterion_id."""
        inp = _valid_input(
            criteria=(
                AcceptanceCriterion(criterion_id="AC-003", description="Third criterion."),
                AcceptanceCriterion(criterion_id="AC-001", description="First criterion."),
                AcceptanceCriterion(criterion_id="AC-002", description="Second criterion."),
            ),
        )
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        artifact_file = tmp_path / result.artifact_path
        artifact = json.loads(artifact_file.read_text(encoding="utf-8"))
        ids = [c["criterion_id"] for c in artifact["criteria"]]
        assert ids == ["AC-001", "AC-002", "AC-003"]

    def test_artifact_has_no_placeholder_strings(self, tmp_path: Path):
        """No non-semantic placeholders in artifact."""
        inp = _valid_input()
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        artifact_file = tmp_path / result.artifact_path
        content = artifact_file.read_text(encoding="utf-8")
        assert "PLACEHOLDER" not in content


# ---------------------------------------------------------------------------
# Missing fields
# ---------------------------------------------------------------------------


class TestMissingFields:
    def test_missing_product_state_ref_fails(self, tmp_path: Path):
        inp = _valid_input(product_state_ref="")
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.REJECTED
        assert REASON_MISSING_PRODUCT_STATE_REF in result.reason_codes

    def test_missing_criteria_fails(self, tmp_path: Path):
        inp = _valid_input(criteria=())
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.REJECTED
        assert REASON_MISSING_CRITERIA in result.reason_codes

    def test_missing_criterion_id_fails(self, tmp_path: Path):
        inp = _valid_input(
            criteria=(AcceptanceCriterion(criterion_id="", description="Some text."),),
        )
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.REJECTED
        assert REASON_MISSING_CRITERION_ID in result.reason_codes

    def test_missing_criterion_text_fails(self, tmp_path: Path):
        inp = _valid_input(
            criteria=(AcceptanceCriterion(criterion_id="AC-001", description=""),),
        )
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.REJECTED
        assert REASON_MISSING_CRITERION_TEXT in result.reason_codes

    def test_missing_output_path_fails(self, tmp_path: Path):
        inp = _valid_input(output_path="")
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.REJECTED
        assert REASON_MISSING_OUTPUT_PATH in result.reason_codes


# ---------------------------------------------------------------------------
# Duplicate criterion ID
# ---------------------------------------------------------------------------


class TestDuplicateCriterionId:
    def test_duplicate_criterion_id_fails(self, tmp_path: Path):
        inp = _valid_input(
            criteria=(
                AcceptanceCriterion(criterion_id="AC-001", description="First."),
                AcceptanceCriterion(criterion_id="AC-001", description="Duplicate."),
            ),
        )
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.REJECTED
        assert REASON_DUPLICATE_CRITERION_ID in result.reason_codes


# ---------------------------------------------------------------------------
# Unbounded criterion text
# ---------------------------------------------------------------------------


class TestUnboundedCriterionText:
    def test_unbounded_criterion_text_fails(self, tmp_path: Path):
        long_text = "x" * 4097
        inp = _valid_input(
            criteria=(AcceptanceCriterion(criterion_id="AC-001", description=long_text),),
        )
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.REJECTED
        assert REASON_UNBOUNDED_CRITERION_TEXT in result.reason_codes

    def test_boundary_4096_passes(self, tmp_path: Path):
        boundary_text = "x" * 4096
        inp = _valid_input(
            criteria=(
                AcceptanceCriterion(criterion_id="AC-001", description=boundary_text),
                AcceptanceCriterion(criterion_id="AC-002", description="Normal text."),
            ),
        )
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.FROZEN


# ---------------------------------------------------------------------------
# Oversized criteria set
# ---------------------------------------------------------------------------


class TestOversizedCriteriaSet:
    def test_oversized_criteria_set_fails(self, tmp_path: Path):
        many_criteria = tuple(
            AcceptanceCriterion(criterion_id=f"AC-{i:03d}", description=f"Criterion {i}.")
            for i in range(101)
        )
        inp = _valid_input(criteria=many_criteria)
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.REJECTED
        assert REASON_OVERSIZED_CRITERIA_SET in result.reason_codes

    def test_boundary_100_passes(self, tmp_path: Path):
        many_criteria = tuple(
            AcceptanceCriterion(criterion_id=f"AC-{i:03d}", description=f"Criterion {i}.")
            for i in range(100)
        )
        inp = _valid_input(criteria=many_criteria)
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.FROZEN
        assert result.criteria_count == 100


# ---------------------------------------------------------------------------
# Hidden reasoning
# ---------------------------------------------------------------------------


class TestHiddenReasoning:
    def test_cot_tag_fails(self, tmp_path: Path):
        inp = _valid_input(
            criteria=(AcceptanceCriterion(criterion_id="AC-001", description="Some text <cot> hidden"),),
        )
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.REJECTED
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes

    def test_chain_of_thought_tag_fails(self, tmp_path: Path):
        inp = _valid_input(
            criteria=(AcceptanceCriterion(criterion_id="AC-001", description="<chain_of_thought> reasoning"),),
        )
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes

    def test_hidden_reasoning_string_fails(self, tmp_path: Path):
        inp = _valid_input(
            criteria=(AcceptanceCriterion(criterion_id="AC-001", description="contains hidden_reasoning"),),
        )
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# External URL-only criteria
# ---------------------------------------------------------------------------


class TestExternalUrlOnly:
    def test_http_url_only_fails(self, tmp_path: Path):
        inp = _valid_input(
            criteria=(AcceptanceCriterion(criterion_id="AC-001", description="http://example.com/criteria"),),
        )
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.REJECTED
        assert REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED in result.reason_codes

    def test_https_url_only_fails(self, tmp_path: Path):
        inp = _valid_input(
            criteria=(AcceptanceCriterion(criterion_id="AC-001", description="https://example.com/criteria"),),
        )
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED in result.reason_codes

    def test_url_with_context_passes(self, tmp_path: Path):
        inp = _valid_input(
            criteria=(
                AcceptanceCriterion(criterion_id="AC-001", description="See https://example.com for details."),
                AcceptanceCriterion(criterion_id="AC-002", description="Normal criterion."),
            ),
        )
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.FROZEN


# ---------------------------------------------------------------------------
# Unbounded output path
# ---------------------------------------------------------------------------


class TestUnboundedOutputPath:
    def test_parent_dotdot_fails(self, tmp_path: Path):
        inp = _valid_input(output_path="../escape/criteria.json")
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.REJECTED
        assert REASON_UNBOUNDED_OUTPUT_PATH in result.reason_codes

    def test_leading_slash_fails(self, tmp_path: Path):
        inp = _valid_input(output_path="/absolute/path/criteria.json")
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert REASON_UNBOUNDED_OUTPUT_PATH in result.reason_codes

    def test_too_long_fails(self, tmp_path: Path):
        long_path = "a" * 300
        inp = _valid_input(output_path=long_path)
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert REASON_UNBOUNDED_OUTPUT_PATH in result.reason_codes


# ---------------------------------------------------------------------------
# No filesystem write when rejected
# ---------------------------------------------------------------------------


class TestNoFilesystemWriteWhenRejected:
    def test_no_write_when_rejected(self, tmp_path: Path):
        """Rejected freeze does not write any file."""
        inp = _valid_input(product_state_ref="")
        initial_files = set(os.listdir(tmp_path))
        result = freeze_acceptance_criteria(inp, output_dir=str(tmp_path))
        assert result.status == AcceptanceCriteriaFreezeStatus.REJECTED
        final_files = set(os.listdir(tmp_path))
        assert final_files == initial_files


# ---------------------------------------------------------------------------
# Integration with proof capture
# ---------------------------------------------------------------------------


class TestProofCaptureIntegration:
    def test_proof_capture_can_consume_ref_shape(self, tmp_path: Path):
        """Freeze criteria, then use acceptance_criteria_ref in ProofCaptureInput."""
        # Step 1: Freeze criteria
        freeze_inp = _valid_input()
        freeze_result = freeze_acceptance_criteria(freeze_inp, output_dir=str(tmp_path))
        assert freeze_result.status == AcceptanceCriteriaFreezeStatus.FROZEN
        assert freeze_result.acceptance_criteria_ref is not None

        # Step 2: Use the ref in a proof capture
        capture_inp = ProofCaptureInput(
            product_state_ref="abc123",
            acceptance_criteria_ref=freeze_result.acceptance_criteria_ref,
            runtime_capture_kind="text",
            phase_id="phase-1",
            run_id="run-001",
            payload="Evidence captured against frozen criteria.",
            output_path="proofs/evidence.json",
            summary="Proof against frozen criteria",
            tags=frozenset({"frozen_criteria_test"}),
        )
        capture_result = capture_proof(capture_inp, output_dir=str(tmp_path))
        assert capture_result.status.value == "captured"
        assert capture_result.proof_ref_fields is not None
        assert capture_result.proof_ref_fields["acceptance_criteria_ref"] == freeze_result.acceptance_criteria_ref


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        import runner.acceptance_criteria
        doc = runner.acceptance_criteria.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """The acceptance_criteria source should not contain forbidden legacy names."""
        import inspect
        source = inspect.getsource(_valid_input)
        source += inspect.getsource(freeze_acceptance_criteria)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"

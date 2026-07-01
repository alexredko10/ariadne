"""Tests for the deterministic evidence-backed self-improvement candidate."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from runner.improvement_candidate import (
    ImprovementCandidate,
    ImprovementCandidateInput,
    ImprovementCandidateResult,
    ImprovementCandidateStatus,
    ImprovementCategory,
    propose_improvement_candidate,
    REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED,
    REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED,
    REASON_GIT_MUTATION_NOT_ALLOWED,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
    REASON_MISSING_ACCEPTANCE_CRITERIA_REF,
    REASON_MISSING_EVIDENCE_REF,
    REASON_MISSING_GATE_EVIDENCE,
    REASON_MISSING_PRODUCT_STATE_REF,
    REASON_MISSING_REASON_CODE,
    REASON_OVERSIZED_CANDIDATE,
    REASON_PROVIDER_CALL_NOT_ALLOWED,
    REASON_UNBOUNDED_CANDIDATE_OUTPUT_PATH,
    _determine_improvement_category,
    _map_reason_code_to_category,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_input(**overrides: object) -> ImprovementCandidateInput:
    kwargs = {
        "product_state_ref": "abc123",
        "acceptance_criteria_ref": "def456",
        "phase_id": "phase-1",
        "run_id": "run-001",
        "source_bundle_ref": "deadbeef12345678",
        "source_reason_codes": ("missing_proof_refs", "inconsistent_product_state_ref"),
        "output_path": "candidates/improvement.json",
        "evidence_refs": ("pr-001", "capture-text-abc123def456"),
        "proposed_next_action": "Add proof capture before creating handoff packet",
        "affected_runtime_area": "runner/proof_capture",
        "requires_human_review": True,
    }
    kwargs.update(overrides)
    return ImprovementCandidateInput(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Valid candidate
# ---------------------------------------------------------------------------


class TestValidCandidate:
    def test_valid_candidate_proposed(self, tmp_path: Path):
        """Valid input → PROPOSED with candidate and artifact."""
        inp = _valid_input()
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.PROPOSED, f"reason_codes={result.reason_codes}"
        assert result.reason_codes == ()
        assert result.candidate is not None
        assert result.artifact_path is not None

        # Verify artifact was written
        artifact_file = tmp_path / result.artifact_path
        assert artifact_file.exists()
        artifact = json.loads(artifact_file.read_text(encoding="utf-8"))
        assert artifact["ariadne_candidate_version"] == "1"
        assert artifact["proposed_at"] is None
        assert artifact["candidate_id"] == result.candidate.candidate_id

    def test_candidate_deterministic_output_fields(self, tmp_path: Path):
        """Candidate includes all required fields."""
        inp = _valid_input()
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.PROPOSED
        c = result.candidate
        assert c is not None
        assert c.candidate_id is not None
        assert len(c.candidate_id) == 16
        int(c.candidate_id, 16)  # should not raise
        assert c.product_state_ref == "abc123"
        assert c.acceptance_criteria_ref == "def456"
        assert c.source_bundle_ref == "deadbeef12345678"
        assert c.source_reason_codes == ("inconsistent_product_state_ref", "missing_proof_refs")
        assert c.evidence_refs == ("capture-text-abc123def456", "pr-001")
        assert c.improvement_category is not None
        assert c.proposed_next_action == "Add proof capture before creating handoff packet"
        assert c.affected_runtime_area == "runner/proof_capture"
        assert c.phase_id == "phase-1"
        assert c.run_id == "run-001"
        assert c.requires_human_review is True

    def test_same_input_same_candidate_id(self, tmp_path: Path):
        """Same input twice produces same candidate_id."""
        inp = _valid_input()
        result1 = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        result2 = propose_improvement_candidate(inp, output_dir=str(tmp_path / "other"))
        assert result1.candidate is not None
        assert result2.candidate is not None
        assert result1.candidate.candidate_id == result2.candidate.candidate_id

    def test_changed_reason_code_changes_candidate_id(self, tmp_path: Path):
        """Different reason code changes candidate_id."""
        inp1 = _valid_input()
        inp2 = _valid_input(source_reason_codes=("hidden_reasoning_not_allowed",))
        result1 = propose_improvement_candidate(inp1, output_dir=str(tmp_path))
        result2 = propose_improvement_candidate(inp2, output_dir=str(tmp_path / "other"))
        assert result1.candidate is not None
        assert result2.candidate is not None
        assert result1.candidate.candidate_id != result2.candidate.candidate_id

    def test_changed_evidence_ref_changes_candidate_id(self, tmp_path: Path):
        """Different evidence refs change candidate_id."""
        inp1 = _valid_input()
        inp2 = _valid_input(evidence_refs=("pr-999",))
        result1 = propose_improvement_candidate(inp1, output_dir=str(tmp_path))
        result2 = propose_improvement_candidate(inp2, output_dir=str(tmp_path / "other"))
        assert result1.candidate is not None
        assert result2.candidate is not None
        assert result1.candidate.candidate_id != result2.candidate.candidate_id

    def test_artifact_json_deterministic(self, tmp_path: Path):
        """Same input produces identical JSON."""
        inp = _valid_input()
        result1 = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        result2 = propose_improvement_candidate(inp, output_dir=str(tmp_path / "other"))
        assert result1.candidate is not None
        assert result2.candidate is not None
        assert result1.candidate.candidate_id == result2.candidate.candidate_id

        art1 = json.loads((tmp_path / result1.artifact_path).read_text(encoding="utf-8"))
        art2 = json.loads((tmp_path / "other" / result2.artifact_path).read_text(encoding="utf-8"))
        assert art1 == art2


# ---------------------------------------------------------------------------
# Missing fields
# ---------------------------------------------------------------------------


class TestMissingFields:
    def test_missing_gate_evidence_fails(self, tmp_path: Path):
        inp = _valid_input(source_bundle_ref="")
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        assert REASON_MISSING_GATE_EVIDENCE in result.reason_codes

    def test_missing_product_state_ref_fails(self, tmp_path: Path):
        inp = _valid_input(product_state_ref="")
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        assert REASON_MISSING_PRODUCT_STATE_REF in result.reason_codes

    def test_missing_acceptance_criteria_ref_fails(self, tmp_path: Path):
        inp = _valid_input(acceptance_criteria_ref="")
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        assert REASON_MISSING_ACCEPTANCE_CRITERIA_REF in result.reason_codes

    def test_missing_reason_code_fails(self, tmp_path: Path):
        inp = _valid_input(source_reason_codes=())
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        assert REASON_MISSING_REASON_CODE in result.reason_codes

    def test_missing_evidence_ref_fails(self, tmp_path: Path):
        inp = _valid_input(evidence_refs=())
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        assert REASON_MISSING_EVIDENCE_REF in result.reason_codes


# ---------------------------------------------------------------------------
# Hidden reasoning
# ---------------------------------------------------------------------------


class TestHiddenReasoning:
    def test_hidden_reasoning_not_allowed(self, tmp_path: Path):
        inp = _valid_input(proposed_next_action="Some text <cot> hidden")
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# External URL-only evidence
# ---------------------------------------------------------------------------


class TestExternalUrlOnly:
    def test_external_url_only_evidence_fails(self, tmp_path: Path):
        inp = _valid_input(proposed_next_action="http://example.com/evidence")
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        assert REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Forbidden actions
# ---------------------------------------------------------------------------


class TestForbiddenActions:
    def test_autonomous_code_change_rejected(self, tmp_path: Path):
        inp = _valid_input(proposed_next_action="Run pip install requests")
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        assert REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED in result.reason_codes

    def test_git_mutation_rejected(self, tmp_path: Path):
        inp = _valid_input(proposed_next_action="Run git commit -m 'fix'")
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        assert REASON_GIT_MUTATION_NOT_ALLOWED in result.reason_codes

    def test_provider_call_rejected(self, tmp_path: Path):
        inp = _valid_input(proposed_next_action="import openai to fix this")
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        assert REASON_PROVIDER_CALL_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Unbounded output path
# ---------------------------------------------------------------------------


class TestUnboundedOutputPath:
    def test_parent_dotdot_fails(self, tmp_path: Path):
        inp = _valid_input(output_path="../escape/candidate.json")
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        assert REASON_UNBOUNDED_CANDIDATE_OUTPUT_PATH in result.reason_codes

    def test_leading_slash_fails(self, tmp_path: Path):
        inp = _valid_input(output_path="/absolute/path/candidate.json")
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert REASON_UNBOUNDED_CANDIDATE_OUTPUT_PATH in result.reason_codes


# ---------------------------------------------------------------------------
# Oversized candidate
# ---------------------------------------------------------------------------


class TestOversizedCandidate:
    def test_oversized_candidate_fails(self, tmp_path: Path):
        long_action = "x" * 4097
        inp = _valid_input(proposed_next_action=long_action)
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        assert REASON_OVERSIZED_CANDIDATE in result.reason_codes


# ---------------------------------------------------------------------------
# No filesystem write when rejected
# ---------------------------------------------------------------------------


class TestNoFilesystemWriteWhenRejected:
    def test_no_write_when_rejected(self, tmp_path: Path):
        inp = _valid_input(product_state_ref="")
        initial_files = set(os.listdir(tmp_path))
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.REJECTED
        final_files = set(os.listdir(tmp_path))
        assert final_files == initial_files


# ---------------------------------------------------------------------------
# Category mapping
# ---------------------------------------------------------------------------


class TestCategoryMapping:
    def test_category_mapping_validation_gap(self):
        """missing_product_state_ref → VALIDATION_GAP."""
        cat = _map_reason_code_to_category("missing_product_state_ref")
        assert cat == ImprovementCategory.VALIDATION_GAP

    def test_category_mapping_evidence_gap(self):
        """missing_proof_refs → EVIDENCE_GAP."""
        cat = _map_reason_code_to_category("missing_proof_refs")
        assert cat == ImprovementCategory.EVIDENCE_GAP

    def test_category_mapping_consistency_gap(self):
        """inconsistent_product_state_ref → CONSISTENCY_GAP."""
        cat = _map_reason_code_to_category("inconsistent_product_state_ref")
        assert cat == ImprovementCategory.CONSISTENCY_GAP

    def test_category_mapping_scope_drift(self):
        """hidden_reasoning_not_allowed → SCOPE_DRIFT."""
        cat = _map_reason_code_to_category("hidden_reasoning_not_allowed")
        assert cat == ImprovementCategory.SCOPE_DRIFT

    def test_category_mapping_missing_runtime_artifact(self):
        """unbounded_bundle_output_path → MISSING_RUNTIME_ARTIFACT."""
        cat = _map_reason_code_to_category("unbounded_bundle_output_path")
        assert cat == ImprovementCategory.MISSING_RUNTIME_ARTIFACT

    def test_category_mapping_cli_surface_gap(self):
        """cli_unknown_command → CLI_SURFACE_GAP."""
        cat = _map_reason_code_to_category("cli_unknown_command")
        assert cat == ImprovementCategory.CLI_SURFACE_GAP

    def test_category_mapping_frontend_gap(self):
        """frontend_missing_button → FRONTEND_VISIBILITY_GAP."""
        cat = _map_reason_code_to_category("frontend_missing_button")
        assert cat == ImprovementCategory.FRONTEND_VISIBILITY_GAP

    def test_category_mapping_multiple_codes(self, tmp_path: Path):
        """Multiple codes produce deterministic single category."""
        inp = _valid_input(
            source_reason_codes=("missing_proof_refs", "inconsistent_product_state_ref"),
        )
        result = propose_improvement_candidate(inp, output_dir=str(tmp_path))
        assert result.status == ImprovementCandidateStatus.PROPOSED
        assert result.candidate is not None
        # missing_proof_refs → EVIDENCE_GAP, inconsistent_product_state_ref → CONSISTENCY_GAP
        # First in sort order: CONSISTENCY_GAP < EVIDENCE_GAP
        assert result.candidate.improvement_category == ImprovementCategory.CONSISTENCY_GAP.value

    def test_category_mapping_fallback(self):
        """Unknown reason code falls back to VALIDATION_GAP."""
        cat = _map_reason_code_to_category("some_unknown_code")
        assert cat == ImprovementCategory.VALIDATION_GAP

    def test_category_mapping_deterministic(self):
        """Same code always maps to same category."""
        cat1 = _map_reason_code_to_category("missing_proof_refs")
        cat2 = _map_reason_code_to_category("missing_proof_refs")
        assert cat1 == cat2


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        import runner.improvement_candidate
        doc = runner.improvement_candidate.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """The improvement_candidate source should not contain forbidden legacy names."""
        import inspect
        source = inspect.getsource(propose_improvement_candidate)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"

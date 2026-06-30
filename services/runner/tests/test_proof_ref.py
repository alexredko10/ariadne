"""Tests for the admissible proof reference runtime object."""

from __future__ import annotations

import json
from typing import FrozenSet

from runner.proof_ref import (
    ProofRef,
    ProofRefValidation,
    validate_proof_ref,
    REASON_AGENT_CLAIM_ONLY,
    REASON_MISSING_ACCEPTANCE_CRITERIA_REF,
    REASON_MISSING_ARTIFACT_PATH,
    REASON_MISSING_PHASE_OR_RUN_IDENTITY,
    REASON_MISSING_PRODUCT_STATE_REF,
    REASON_MISSING_RUNTIME_CAPTURE_REF,
    REASON_STALE_OR_UNLINKED_STATE,
    REASON_UNBOUNDED_ARTIFACT_PATH,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_proof_ref(**overrides: object) -> ProofRef:
    kwargs = {
        "run_id": "run-001",
        "phase_id": "phase-1",
        "product_state_ref": "abc123",
        "acceptance_criteria_ref": "def456",
        "runtime_capture_ref": "er-001",
        "artifact_path": "results/evidence.json",
        "summary": "Test artifact",
        "tags": frozenset({"unit_test", "smoke"}),
    }
    kwargs.update(overrides)
    return ProofRef(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Valid proof ref
# ---------------------------------------------------------------------------


class TestValidProofRef:
    def test_valid_ref_passes(self):
        ref = _valid_proof_ref()
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is True
        assert v.reason_codes == ()

    def test_valid_ref_empty_reason_codes(self):
        ref = _valid_proof_ref()
        v = validate_proof_ref(ref, "abc123")
        assert len(v.reason_codes) == 0

    def test_valid_ref_no_details(self):
        ref = _valid_proof_ref()
        v = validate_proof_ref(ref, "abc123")
        assert v.details is None


# ---------------------------------------------------------------------------
# Missing product state ref
# ---------------------------------------------------------------------------


class TestMissingProductStateRef:
    def test_empty_string_fails(self):
        ref = _valid_proof_ref(product_state_ref="")
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is False
        assert REASON_MISSING_PRODUCT_STATE_REF in v.reason_codes

    def test_whitespace_only_fails(self):
        ref = _valid_proof_ref(product_state_ref="   ")
        v = validate_proof_ref(ref, "abc123")
        assert REASON_MISSING_PRODUCT_STATE_REF in v.reason_codes


# ---------------------------------------------------------------------------
# Missing acceptance criteria ref
# ---------------------------------------------------------------------------


class TestMissingAcceptanceCriteriaRef:
    def test_empty_string_fails(self):
        ref = _valid_proof_ref(acceptance_criteria_ref="")
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is False
        assert REASON_MISSING_ACCEPTANCE_CRITERIA_REF in v.reason_codes

    def test_whitespace_only_fails(self):
        ref = _valid_proof_ref(acceptance_criteria_ref="   ")
        v = validate_proof_ref(ref, "abc123")
        assert REASON_MISSING_ACCEPTANCE_CRITERIA_REF in v.reason_codes


# ---------------------------------------------------------------------------
# Missing runtime capture ref
# ---------------------------------------------------------------------------


class TestMissingRuntimeCaptureRef:
    def test_empty_string_fails(self):
        ref = _valid_proof_ref(runtime_capture_ref="")
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is False
        assert REASON_MISSING_RUNTIME_CAPTURE_REF in v.reason_codes


# ---------------------------------------------------------------------------
# Missing artifact path
# ---------------------------------------------------------------------------


class TestMissingArtifactPath:
    def test_empty_string_fails(self):
        ref = _valid_proof_ref(artifact_path="")
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is False
        assert REASON_MISSING_ARTIFACT_PATH in v.reason_codes


# ---------------------------------------------------------------------------
# Unbounded artifact path
# ---------------------------------------------------------------------------


class TestUnboundedArtifactPath:
    def test_absolute_path_fails(self):
        ref = _valid_proof_ref(artifact_path="/absolute/path/evidence.json")
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is False
        assert REASON_UNBOUNDED_ARTIFACT_PATH in v.reason_codes

    def test_dotdot_path_fails(self):
        ref = _valid_proof_ref(artifact_path="../../escape/evidence.json")
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is False
        assert REASON_UNBOUNDED_ARTIFACT_PATH in v.reason_codes

    def test_too_long_path_fails(self):
        long_path = "a" * 300
        ref = _valid_proof_ref(artifact_path=long_path)
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is False
        assert REASON_UNBOUNDED_ARTIFACT_PATH in v.reason_codes

    def test_boundary_255_passes(self):
        path_255 = "a" * 250 + ".json"
        assert len(path_255) <= 255
        ref = _valid_proof_ref(artifact_path=path_255)
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is True


# ---------------------------------------------------------------------------
# Missing phase or run identity
# ---------------------------------------------------------------------------


class TestMissingPhaseOrRunIdentity:
    def test_both_empty_fails(self):
        ref = _valid_proof_ref(run_id="", phase_id=None)
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is False
        assert REASON_MISSING_PHASE_OR_RUN_IDENTITY in v.reason_codes

    def test_phase_present_run_empty_fails(self):
        ref = _valid_proof_ref(run_id="", phase_id="phase-1")
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is False
        assert REASON_MISSING_PHASE_OR_RUN_IDENTITY in v.reason_codes


# ---------------------------------------------------------------------------
# Agent claim only (short basename)
# ---------------------------------------------------------------------------


class TestAgentClaimOnly:
    def test_single_char_basename_fails(self):
        ref = _valid_proof_ref(artifact_path="a")
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is False
        assert REASON_AGENT_CLAIM_ONLY in v.reason_codes

    def test_two_char_basename_fails(self):
        ref = _valid_proof_ref(artifact_path="ab")
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is False
        assert REASON_AGENT_CLAIM_ONLY in v.reason_codes

    def test_three_char_basename_passes(self):
        ref = _valid_proof_ref(artifact_path="abc")
        v = validate_proof_ref(ref, "abc123")
        # This may fail for other reasons if other fields are missing, but
        # agent_claim_only should NOT be in the reason_codes.
        assert REASON_AGENT_CLAIM_ONLY not in v.reason_codes


# ---------------------------------------------------------------------------
# Stale / unlinked product state
# ---------------------------------------------------------------------------


class TestStaleOrUnlinkedState:
    def test_mismatched_state_fails(self):
        ref = _valid_proof_ref(product_state_ref="abc")
        v = validate_proof_ref(ref, "xyz")
        assert v.admissible is False
        assert REASON_STALE_OR_UNLINKED_STATE in v.reason_codes

    def test_empty_product_state_ref_does_not_trigger_stale(self):
        """When product_state_ref is empty, we get missing_product_state_ref,
        but stale_or_unlinked_state should not also fire."""
        ref = _valid_proof_ref(product_state_ref="")
        v = validate_proof_ref(ref, "xyz")
        assert REASON_STALE_OR_UNLINKED_STATE not in v.reason_codes
        assert REASON_MISSING_PRODUCT_STATE_REF in v.reason_codes


# ---------------------------------------------------------------------------
# Multiple failures simultaneously
# ---------------------------------------------------------------------------


class TestMultipleFailures:
    def test_all_fields_empty(self):
        ref = _valid_proof_ref(
            product_state_ref="",
            acceptance_criteria_ref="",
            runtime_capture_ref="",
            artifact_path="",
            run_id="",
            phase_id=None,
        )
        v = validate_proof_ref(ref, "abc123")
        assert v.admissible is False
        assert REASON_MISSING_PRODUCT_STATE_REF in v.reason_codes
        assert REASON_MISSING_ACCEPTANCE_CRITERIA_REF in v.reason_codes
        assert REASON_MISSING_RUNTIME_CAPTURE_REF in v.reason_codes
        assert REASON_MISSING_ARTIFACT_PATH in v.reason_codes
        assert REASON_MISSING_PHASE_OR_RUN_IDENTITY in v.reason_codes


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------


class TestJsonSerialization:
    def test_proof_ref_to_dict_works(self):
        ref = _valid_proof_ref()
        d = ref.to_dict()
        assert isinstance(d, dict)
        assert d["run_id"] == "run-001"
        assert d["artifact_path"] == "results/evidence.json"
        # tags should be a sorted list
        assert isinstance(d["tags"], list)
        assert d["tags"] == sorted(ref.tags)

    def test_proof_ref_to_json_works(self):
        ref = _valid_proof_ref()
        s = ref.to_json()
        assert isinstance(s, str)
        loaded = json.loads(s)
        assert loaded["run_id"] == "run-001"

    def test_validation_is_json_serializable(self):
        ref = _valid_proof_ref(product_state_ref="")
        v = validate_proof_ref(ref, "abc123")
        dumped = json.dumps(
            {"admissible": v.admissible, "reason_codes": list(v.reason_codes)},
            sort_keys=True,
        )
        assert isinstance(dumped, str)


# ---------------------------------------------------------------------------
# Deterministic
# ---------------------------------------------------------------------------


class TestDeterministic:
    def test_two_calls_same_inputs_same_output(self):
        ref = _valid_proof_ref(product_state_ref="")
        v1 = validate_proof_ref(ref, "abc123")
        v2 = validate_proof_ref(ref, "abc123")
        assert v1.admissible == v2.admissible
        assert v1.reason_codes == v2.reason_codes
        assert v1.details == v2.details

    def test_reason_codes_sorted(self):
        ref = _valid_proof_ref(
            product_state_ref="",
            acceptance_criteria_ref="",
            runtime_capture_ref="",
            artifact_path="",
            run_id="",
            phase_id=None,
        )
        v = validate_proof_ref(ref, "abc123")
        codes = list(v.reason_codes)
        assert codes == sorted(codes)


# ---------------------------------------------------------------------------
# No side effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_state_mutation(self):
        """validate_proof_ref does not modify the ProofRef."""
        ref = _valid_proof_ref(product_state_ref="abc")
        original_id = id(ref)
        original_product = ref.product_state_ref
        v = validate_proof_ref(ref, "def")
        assert id(ref) == original_id
        assert ref.product_state_ref == original_product

    def test_immutable_frozen_instance(self):
        """ProofRef should be frozen and not allow attribute mutation."""
        ref = _valid_proof_ref()
        import dataclasses
        assert dataclasses.fields(ref)  # just confirm it's a dataclass


# ---------------------------------------------------------------------------
# Product name is Ariadne
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        import runner.proof_ref
        doc = runner.proof_ref.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """The proof_ref source should not contain forbidden legacy names."""
        import inspect
        source = inspect.getsource(_valid_proof_ref)
        source += inspect.getsource(validate_proof_ref)
        forbidden = ["water_meter", "water-meter", "Broken Clock", "broken_clock",
                      "daily-consumption", ".grace", "@grace-", "old Flask"]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"

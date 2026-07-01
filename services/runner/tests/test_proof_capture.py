"""Tests for the deterministic local proof capture runtime object."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from runner.proof_capture import (
    ProofCaptureInput,
    ProofCaptureResult,
    ProofCaptureStatus,
    capture_proof,
    REASON_ARBITRARY_COMMAND_EXECUTION_NOT_ALLOWED,
    REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
    REASON_MISSING_ACCEPTANCE_CRITERIA_REF,
    REASON_MISSING_OUTPUT_PATH,
    REASON_MISSING_PHASE_IDENTITY,
    REASON_MISSING_PRODUCT_STATE_REF,
    REASON_MISSING_RUNTIME_CAPTURE_KIND,
    REASON_MISSING_RUN_IDENTITY,
    REASON_OVERSIZED_CAPTURE,
    REASON_UNBOUNDED_OUTPUT_PATH,
)
from runner.proof_ref import (
    ProofRef,
    validate_proof_ref,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_input(**overrides: object) -> ProofCaptureInput:
    kwargs = {
        "product_state_ref": "abc123",
        "acceptance_criteria_ref": "def456",
        "runtime_capture_kind": "text",
        "phase_id": "phase-1",
        "run_id": "run-001",
        "payload": "All automated checks passed. Evidence captured.",
        "output_path": "captures/evidence.json",
        "summary": "Test capture",
        "tags": frozenset({"unit_test", "smoke"}),
    }
    kwargs.update(overrides)
    return ProofCaptureInput(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Valid capture
# ---------------------------------------------------------------------------


class TestValidCapture:
    def test_valid_text_capture(self, tmp_path: Path):
        """Valid input with text payload writes artifact and returns CAPTURED."""
        inp = _valid_input()
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.CAPTURED
        assert result.reason_codes == ()
        assert result.artifact_path is not None
        assert result.proof_ref_fields is not None

        # Verify artifact was written
        artifact_file = tmp_path / result.artifact_path
        assert artifact_file.exists()
        artifact = json.loads(artifact_file.read_text(encoding="utf-8"))
        assert artifact["ariadne_capture_version"] == "1"
        assert artifact["product_state_ref"] == "abc123"
        assert artifact["payload"] == "All automated checks passed. Evidence captured."
        assert artifact["captured_at"] is None

    def test_valid_json_capture(self, tmp_path: Path):
        """Valid input with JSON payload writes artifact and returns CAPTURED."""
        json_payload = json.dumps({"result": "pass", "score": 0.95})
        inp = _valid_input(payload=json_payload, runtime_capture_kind="json")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.CAPTURED
        assert result.reason_codes == ()

        artifact_file = tmp_path / result.artifact_path
        assert artifact_file.exists()

    def test_captured_proof_ref_compatible(self, tmp_path: Path):
        """proof_ref_fields can construct a ProofRef that passes validate_proof_ref()."""
        inp = _valid_input()
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.CAPTURED
        assert result.proof_ref_fields is not None

        # Construct ProofRef from capture result fields
        fields = result.proof_ref_fields
        proof_ref = ProofRef(
            run_id=fields["run_id"],
            phase_id=fields["phase_id"],
            product_state_ref=fields["product_state_ref"],
            acceptance_criteria_ref=fields["acceptance_criteria_ref"],
            runtime_capture_ref=fields["runtime_capture_ref"],
            artifact_path=fields["artifact_path"],
            summary=fields["summary"],
            tags=frozenset(fields["tags"]),
        )
        validation = validate_proof_ref(proof_ref, fields["product_state_ref"])
        assert validation.admissible is True

    def test_artifact_json_deterministic(self, tmp_path: Path):
        """Same input produces identical artifact JSON."""
        inp = _valid_input()
        result1 = capture_proof(inp, output_dir=str(tmp_path))
        result2 = capture_proof(inp, output_dir=str(tmp_path / "other"))

        assert result1.proof_ref_fields is not None
        assert result2.proof_ref_fields is not None
        # runtime_capture_ref should differ because artifact content differs
        # (different output_dir changes the file path in the artifact? No — output_dir
        # is not stored in the artifact. So they should be identical.)
        assert result1.proof_ref_fields["runtime_capture_ref"] == result2.proof_ref_fields["runtime_capture_ref"]

        # Read both artifacts
        art1 = json.loads((tmp_path / result1.artifact_path).read_text(encoding="utf-8"))
        art2 = json.loads((tmp_path / "other" / result2.artifact_path).read_text(encoding="utf-8"))
        assert art1 == art2

    def test_runtime_capture_ref_derived(self, tmp_path: Path):
        """runtime_capture_ref matches capture-{kind}-{sha256_prefix} format."""
        inp = _valid_input()
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.CAPTURED
        assert result.proof_ref_fields is not None

        ref = result.proof_ref_fields["runtime_capture_ref"]
        assert ref.startswith("capture-text-")
        assert len(ref) == len("capture-text-") + 12  # 12 hex chars

        # Verify it's a valid SHA256 prefix
        prefix = ref.split("-")[-1]
        assert len(prefix) == 12
        int(prefix, 16)  # should not raise

    def test_output_path_includes_output_dir(self, tmp_path: Path):
        """Artifact written to {output_dir}/{output_path}."""
        inp = _valid_input(output_path="subdir/capture.json")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.CAPTURED
        artifact_file = tmp_path / "subdir" / "capture.json"
        assert artifact_file.exists()


# ---------------------------------------------------------------------------
# Missing fields
# ---------------------------------------------------------------------------


class TestMissingFields:
    def test_missing_product_state_ref(self, tmp_path: Path):
        inp = _valid_input(product_state_ref="")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_MISSING_PRODUCT_STATE_REF in result.reason_codes

    def test_missing_acceptance_criteria_ref(self, tmp_path: Path):
        inp = _valid_input(acceptance_criteria_ref="")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_MISSING_ACCEPTANCE_CRITERIA_REF in result.reason_codes

    def test_missing_runtime_capture_kind(self, tmp_path: Path):
        inp = _valid_input(runtime_capture_kind="")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_MISSING_RUNTIME_CAPTURE_KIND in result.reason_codes

    def test_missing_phase_identity(self, tmp_path: Path):
        inp = _valid_input(phase_id="")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_MISSING_PHASE_IDENTITY in result.reason_codes

    def test_missing_run_identity(self, tmp_path: Path):
        inp = _valid_input(run_id="")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_MISSING_RUN_IDENTITY in result.reason_codes

    def test_missing_output_path(self, tmp_path: Path):
        inp = _valid_input(output_path="")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_MISSING_OUTPUT_PATH in result.reason_codes


# ---------------------------------------------------------------------------
# Unbounded output path
# ---------------------------------------------------------------------------


class TestUnboundedOutputPath:
    def test_parent_dotdot(self, tmp_path: Path):
        inp = _valid_input(output_path="../escape/evidence.json")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_UNBOUNDED_OUTPUT_PATH in result.reason_codes

    def test_leading_slash(self, tmp_path: Path):
        inp = _valid_input(output_path="/absolute/path/evidence.json")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_UNBOUNDED_OUTPUT_PATH in result.reason_codes

    def test_too_long(self, tmp_path: Path):
        long_path = "a" * 300
        inp = _valid_input(output_path=long_path)
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_UNBOUNDED_OUTPUT_PATH in result.reason_codes


# ---------------------------------------------------------------------------
# Oversized payload
# ---------------------------------------------------------------------------


class TestOversizedPayload:
    def test_oversized_payload(self, tmp_path: Path):
        long_payload = "x" * 65537
        inp = _valid_input(payload=long_payload)
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_OVERSIZED_CAPTURE in result.reason_codes

    def test_boundary_65536_passes(self, tmp_path: Path):
        boundary_payload = "x" * 65536
        inp = _valid_input(payload=boundary_payload)
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.CAPTURED

    def test_empty_payload_fails(self, tmp_path: Path):
        inp = _valid_input(payload="")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_OVERSIZED_CAPTURE in result.reason_codes


# ---------------------------------------------------------------------------
# Hidden reasoning
# ---------------------------------------------------------------------------


class TestHiddenReasoning:
    def test_cot_tag_fails(self, tmp_path: Path):
        inp = _valid_input(payload="Some text <cot> hidden reasoning here")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes

    def test_chain_of_thought_tag_fails(self, tmp_path: Path):
        inp = _valid_input(payload="<chain_of_thought> reasoning")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes

    def test_hidden_reasoning_string_fails(self, tmp_path: Path):
        inp = _valid_input(payload="contains hidden_reasoning content")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# External URL-only proof
# ---------------------------------------------------------------------------


class TestExternalUrlOnly:
    def test_http_url_only_fails(self, tmp_path: Path):
        inp = _valid_input(payload="http://example.com/evidence")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED in result.reason_codes

    def test_https_url_only_fails(self, tmp_path: Path):
        inp = _valid_input(payload="https://storage.example.com/artifact.json")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED in result.reason_codes

    def test_url_with_context_passes(self, tmp_path: Path):
        """URL with additional context should pass."""
        inp = _valid_input(payload="Evidence at https://example.com/artifact.json plus local verification")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.CAPTURED


# ---------------------------------------------------------------------------
# Command execution not allowed
# ---------------------------------------------------------------------------


class TestCommandExecutionNotAllowed:
    def test_command_execution_kind_fails(self, tmp_path: Path):
        inp = _valid_input(runtime_capture_kind="command_execution")
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        assert REASON_ARBITRARY_COMMAND_EXECUTION_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# No filesystem write when rejected
# ---------------------------------------------------------------------------


class TestNoFilesystemWriteWhenRejected:
    def test_no_write_when_rejected(self, tmp_path: Path):
        """Rejected capture does not write any file."""
        inp = _valid_input(product_state_ref="")
        initial_files = set(os.listdir(tmp_path))
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.REJECTED
        final_files = set(os.listdir(tmp_path))
        assert final_files == initial_files


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        import runner.proof_capture
        doc = runner.proof_capture.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """The proof_capture source should not contain forbidden legacy names."""
        import inspect
        source = inspect.getsource(_valid_input)
        source += inspect.getsource(capture_proof)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"


# ---------------------------------------------------------------------------
# No PLACEHOLDER in output
# ---------------------------------------------------------------------------


class TestNoPlaceholder:
    def test_no_placeholder_in_artifact(self, tmp_path: Path):
        """Artifact JSON does not contain the string 'PLACEHOLDER'."""
        inp = _valid_input()
        result = capture_proof(inp, output_dir=str(tmp_path))
        assert result.status == ProofCaptureStatus.CAPTURED
        artifact_file = tmp_path / result.artifact_path
        content = artifact_file.read_text(encoding="utf-8")
        assert "PLACEHOLDER" not in content

    def test_no_placeholder_in_source(self):
        """Source code does not contain 'PLACEHOLDER'."""
        import runner.proof_capture
        source = Path(runner.proof_capture.__file__).read_text(encoding="utf-8")
        assert "PLACEHOLDER" not in source

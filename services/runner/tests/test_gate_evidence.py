"""Tests for the deterministic gate evidence bundle runtime object."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from runner.acceptance_criteria import (
    AcceptanceCriterion,
    AcceptanceCriteriaFreezeInput,
    freeze_acceptance_criteria,
)
from runner.gate_evidence import (
    GateEvidenceBundleInput,
    GateEvidenceBundleResult,
    GateEvidenceBundleStatus,
    build_gate_evidence_bundle,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
    REASON_INADMISSIBLE_PROOF_REF,
    REASON_INCONSISTENT_ACCEPTANCE_CRITERIA_REF,
    REASON_INCONSISTENT_PHASE_IDENTITY,
    REASON_INCONSISTENT_PRODUCT_STATE_REF,
    REASON_INCONSISTENT_RUN_IDENTITY,
    REASON_MISSING_ACCEPTANCE_CRITERIA_REF,
    REASON_MISSING_HANDOFF_PACKET,
    REASON_MISSING_PHASE_IDENTITY,
    REASON_MISSING_PRODUCT_STATE_REF,
    REASON_MISSING_PROOF_REFS,
    REASON_MISSING_RUN_IDENTITY,
    REASON_UNBOUNDED_BUNDLE_OUTPUT_PATH,
    REASON_UNKNOWN_CAPTURE_REF,
)
from runner.handoff_packet import (
    GateReadyHandoffPacket,
)
from runner.proof_capture import (
    ProofCaptureInput,
    capture_proof,
)


# ---------------------------------------------------------------------------
# Fixture: create valid artifacts once per test class
# ---------------------------------------------------------------------------


def _create_artifacts(
    tmp_path: Path,
    *,
    product_state_ref: str = "abc123",
    phase_id: str = "phase-1",
    run_id: str = "run-001",
    gate_id: str = "human_review_gate",
    actor_or_role: str = "reviewer",
    proof_ref_ids: tuple[str, ...] = ("pr-001", "pr-002"),
    handoff_payload: str = "All automated checks passed.",
    capture_payload: str = "Evidence captured.",
    capture_kind: str = "text",
) -> dict:
    """Create valid artifact files and return their paths and refs."""
    # 1. Freeze acceptance criteria
    criteria_inp = AcceptanceCriteriaFreezeInput(
        product_state_ref=product_state_ref,
        criteria=(
            AcceptanceCriterion(criterion_id="AC-001", description="System must return exit code 0."),
            AcceptanceCriterion(criterion_id="AC-002", description="System must reject invalid input."),
        ),
        phase_id=phase_id,
        run_id=run_id,
        output_path="criteria/frozen.json",
        title="Test criteria",
    )
    criteria_result = freeze_acceptance_criteria(criteria_inp, output_dir=str(tmp_path))
    assert criteria_result.status.value == "frozen"
    ac_ref = criteria_result.acceptance_criteria_ref
    criteria_path = str(tmp_path / criteria_result.artifact_path)

    # 2. Capture proof
    capture_inp = ProofCaptureInput(
        product_state_ref=product_state_ref,
        acceptance_criteria_ref=ac_ref,
        runtime_capture_kind=capture_kind,
        phase_id=phase_id,
        run_id=run_id,
        payload=capture_payload,
        output_path="captures/evidence.json",
        summary="Test capture",
        tags=frozenset({"test"}),
    )
    capture_result = capture_proof(capture_inp, output_dir=str(tmp_path))
    assert capture_result.status.value == "captured"
    capture_path = str(tmp_path / capture_result.artifact_path)
    runtime_capture_ref = capture_result.proof_ref_fields["runtime_capture_ref"]

    # 3. Build handoff packet JSON file
    handoff_packet = GateReadyHandoffPacket(
        product_state_ref=product_state_ref,
        acceptance_criteria_ref=ac_ref,
        phase_id=phase_id,
        run_id=run_id,
        gate_id=gate_id,
        actor_or_role=actor_or_role,
        proof_ref_ids=proof_ref_ids,
        payload=handoff_payload,
    )
    handoff_path = str(tmp_path / "handoff.json")
    with open(handoff_path, "w", encoding="utf-8") as f:
        f.write(handoff_packet.to_json())

    return {
        "handoff_packet_path": handoff_path,
        "acceptance_criteria_path": criteria_path,
        "capture_artifact_paths": (capture_path,),
        "acceptance_criteria_ref": ac_ref,
        "runtime_capture_refs": (runtime_capture_ref,),
        "product_state_ref": product_state_ref,
        "phase_id": phase_id,
        "run_id": run_id,
        "gate_id": gate_id,
        "actor_or_role": actor_or_role,
        "proof_ref_ids": proof_ref_ids,
    }


def _bundle_input(artifacts: dict, **overrides: object) -> GateEvidenceBundleInput:
    """Build a GateEvidenceBundleInput from artifact dict, with optional overrides."""
    kwargs = {
        "product_state_ref": artifacts["product_state_ref"],
        "acceptance_criteria_ref": artifacts["acceptance_criteria_ref"],
        "phase_id": artifacts["phase_id"],
        "run_id": artifacts["run_id"],
        "proof_ref_ids": artifacts["proof_ref_ids"],
        "runtime_capture_refs": artifacts["runtime_capture_refs"],
        "handoff_packet_path": artifacts["handoff_packet_path"],
        "acceptance_criteria_path": artifacts["acceptance_criteria_path"],
        "output_path": "bundle/evidence.json",
        "capture_artifact_paths": artifacts["capture_artifact_paths"],
        "gate_id": artifacts["gate_id"],
        "actor_or_role": artifacts["actor_or_role"],
    }
    kwargs.update(overrides)
    return GateEvidenceBundleInput(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Valid bundle
# ---------------------------------------------------------------------------


class TestValidBundle:
    def test_valid_bundle_succeeds(self, tmp_path: Path):
        """Consistent input with real artifact files → BUNDLED."""
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts)
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.BUNDLED, f"reason_codes={result.reason_codes}"
        assert result.reason_codes == ()
        assert result.artifact_path is not None
        assert result.bundle_ref is not None
        assert result.consistency_summary is not None

        # Verify artifact was written
        artifact_file = tmp_path / result.artifact_path
        assert artifact_file.exists()
        artifact = json.loads(artifact_file.read_text(encoding="utf-8"))
        assert artifact["ariadne_bundle_version"] == "1"
        assert artifact["product_state_ref"] == "abc123"
        assert artifact["bundled_at"] is None

    def test_valid_bundle_deterministic_output_fields(self, tmp_path: Path):
        """Bundle includes deterministic fields."""
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts)
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.BUNDLED
        assert result.bundle_ref is not None
        assert len(result.bundle_ref) == 16
        int(result.bundle_ref, 16)  # should not raise
        assert "proof ref" in result.consistency_summary
        assert "capture" in result.consistency_summary
        assert "criterion" in result.consistency_summary

    def test_bundle_artifact_json_deterministic(self, tmp_path: Path):
        """Same input produces identical JSON."""
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts)
        result1 = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        result2 = build_gate_evidence_bundle(inp, output_dir=str(tmp_path / "other"))
        assert result1.bundle_ref == result2.bundle_ref

        art1 = json.loads((tmp_path / result1.artifact_path).read_text(encoding="utf-8"))
        art2 = json.loads((tmp_path / "other" / result2.artifact_path).read_text(encoding="utf-8"))
        assert art1 == art2

    def test_same_input_same_bundle_ref(self, tmp_path: Path):
        """Same input twice produces same bundle_ref."""
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts)
        result1 = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        result2 = build_gate_evidence_bundle(inp, output_dir=str(tmp_path / "other"))
        assert result1.bundle_ref == result2.bundle_ref

    def test_changed_proof_refs_changes_bundle_ref(self, tmp_path: Path):
        """Different proof_ref_ids changes bundle_ref."""
        artifacts = _create_artifacts(tmp_path)
        inp1 = _bundle_input(artifacts)
        inp2 = _bundle_input(artifacts, proof_ref_ids=("pr-001", "pr-002", "pr-003"))
        result1 = build_gate_evidence_bundle(inp1, output_dir=str(tmp_path))
        result2 = build_gate_evidence_bundle(inp2, output_dir=str(tmp_path / "other"))
        assert result1.bundle_ref != result2.bundle_ref

    def test_consistency_summary_includes_counts(self, tmp_path: Path):
        """Bundled result includes summary string with counts."""
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts)
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.BUNDLED
        assert result.consistency_summary is not None
        assert "2 proof ref" in result.consistency_summary
        assert "1 capture" in result.consistency_summary
        assert "2 criterion" in result.consistency_summary


# ---------------------------------------------------------------------------
# Missing fields
# ---------------------------------------------------------------------------


class TestMissingFields:
    def test_missing_product_state_ref(self, tmp_path: Path):
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, product_state_ref="")
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_MISSING_PRODUCT_STATE_REF in result.reason_codes

    def test_missing_acceptance_criteria_ref(self, tmp_path: Path):
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, acceptance_criteria_ref="")
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_MISSING_ACCEPTANCE_CRITERIA_REF in result.reason_codes

    def test_missing_handoff_packet(self, tmp_path: Path):
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, handoff_packet_path="/nonexistent/handoff.json")
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_MISSING_HANDOFF_PACKET in result.reason_codes

    def test_missing_proof_refs(self, tmp_path: Path):
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, proof_ref_ids=())
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_MISSING_PROOF_REFS in result.reason_codes

    def test_missing_phase_identity(self, tmp_path: Path):
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, phase_id="")
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_MISSING_PHASE_IDENTITY in result.reason_codes

    def test_missing_run_identity(self, tmp_path: Path):
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, run_id="")
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_MISSING_RUN_IDENTITY in result.reason_codes


# ---------------------------------------------------------------------------
# Inconsistency checks
# ---------------------------------------------------------------------------


class TestInconsistency:
    def test_inconsistent_product_state_ref(self, tmp_path: Path):
        """Handoff packet has different product_state_ref than input."""
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, product_state_ref="different")
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_INCONSISTENT_PRODUCT_STATE_REF in result.reason_codes

    def test_inconsistent_acceptance_criteria_ref(self, tmp_path: Path):
        """Handoff packet has different acceptance_criteria_ref than input."""
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, acceptance_criteria_ref="deadbeef12345678")
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_INCONSISTENT_ACCEPTANCE_CRITERIA_REF in result.reason_codes

    def test_inconsistent_phase_identity(self, tmp_path: Path):
        """Handoff packet has different phase_id than input."""
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, phase_id="different-phase")
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_INCONSISTENT_PHASE_IDENTITY in result.reason_codes

    def test_inconsistent_run_identity(self, tmp_path: Path):
        """Handoff packet has different run_id than input."""
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, run_id="different-run")
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_INCONSISTENT_RUN_IDENTITY in result.reason_codes

    def test_inadmissible_proof_ref(self, tmp_path: Path):
        """Handoff packet missing a proof ref from input."""
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, proof_ref_ids=("pr-001", "pr-002", "pr-999"))
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_INADMISSIBLE_PROOF_REF in result.reason_codes

    def test_unknown_capture_ref(self, tmp_path: Path):
        """runtime_capture_ref not matching any capture artifact."""
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, runtime_capture_refs=("capture-unknown-abcdef123456",))
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_UNKNOWN_CAPTURE_REF in result.reason_codes


# ---------------------------------------------------------------------------
# Unbounded output path
# ---------------------------------------------------------------------------


class TestUnboundedOutputPath:
    def test_parent_dotdot_fails(self, tmp_path: Path):
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, output_path="../escape/bundle.json")
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_UNBOUNDED_BUNDLE_OUTPUT_PATH in result.reason_codes

    def test_leading_slash_fails(self, tmp_path: Path):
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, output_path="/absolute/path/bundle.json")
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert REASON_UNBOUNDED_BUNDLE_OUTPUT_PATH in result.reason_codes


# ---------------------------------------------------------------------------
# Hidden reasoning in artifacts
# ---------------------------------------------------------------------------


class TestHiddenReasoning:
    def test_hidden_reasoning_in_handoff_payload(self, tmp_path: Path):
        """Handoff payload with <cot> → REJECTED."""
        artifacts = _create_artifacts(tmp_path, handoff_payload="Some text <cot> hidden")
        inp = _bundle_input(artifacts)
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes

    def test_hidden_reasoning_in_capture_payload(self, tmp_path: Path):
        """Capture payload with <cot> → REJECTED.

        We create the capture artifact manually (bypassing capture_proof which
        would also reject it) to test that the bundle detects hidden reasoning.
        """
        # Create valid artifacts first
        artifacts = _create_artifacts(tmp_path)
        ac_ref = artifacts["acceptance_criteria_ref"]

        # Manually create a capture artifact with hidden reasoning
        capture_artifact = {
            "ariadne_capture_version": "1",
            "product_state_ref": "abc123",
            "acceptance_criteria_ref": ac_ref,
            "runtime_capture_kind": "text",
            "phase_id": "phase-1",
            "run_id": "run-001",
            "payload": "Some text <cot> hidden",
            "summary": "Hidden reasoning capture",
            "tags": [],
            "captured_at": None,
        }
        capture_dir = tmp_path / "hidden_captures"
        capture_dir.mkdir()
        capture_path = str(capture_dir / "evidence.json")
        with open(capture_path, "w", encoding="utf-8") as f:
            json.dump(capture_artifact, f, sort_keys=True, indent=2)

        # Compute runtime_capture_ref the same way proof_capture does
        import hashlib
        cap_json = json.dumps(capture_artifact, sort_keys=True, indent=2)
        cap_sha256 = hashlib.sha256(cap_json.encode("utf-8")).hexdigest()[:12]
        runtime_capture_ref = f"capture-text-{cap_sha256}"

        inp = _bundle_input(
            artifacts,
            runtime_capture_refs=(runtime_capture_ref,),
            capture_artifact_paths=(capture_path,),
        )
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# No filesystem write when rejected
# ---------------------------------------------------------------------------


class TestNoFilesystemWriteWhenRejected:
    def test_no_write_when_rejected(self, tmp_path: Path):
        """Rejected bundle writes no files."""
        artifacts = _create_artifacts(tmp_path)
        inp = _bundle_input(artifacts, product_state_ref="")
        initial_files = set(os.listdir(tmp_path))
        result = build_gate_evidence_bundle(inp, output_dir=str(tmp_path))
        assert result.status == GateEvidenceBundleStatus.REJECTED
        final_files = set(os.listdir(tmp_path))
        assert final_files == initial_files


# ---------------------------------------------------------------------------
# End-to-end workflow
# ---------------------------------------------------------------------------


class TestEndToEndWorkflow:
    def test_end_to_end_bundle_workflow(self, tmp_path: Path):
        """Freeze criteria → capture proof → build handoff → build bundle → BUNDLED."""
        # Step 1: Freeze criteria
        criteria_inp = AcceptanceCriteriaFreezeInput(
            product_state_ref="abc123",
            criteria=(
                AcceptanceCriterion(criterion_id="AC-001", description="System must return exit code 0."),
                AcceptanceCriterion(criterion_id="AC-002", description="System must reject invalid input."),
            ),
            phase_id="phase-1",
            run_id="run-001",
            output_path="criteria/frozen.json",
            title="End-to-end test criteria",
        )
        criteria_result = freeze_acceptance_criteria(criteria_inp, output_dir=str(tmp_path))
        assert criteria_result.status.value == "frozen"
        ac_ref = criteria_result.acceptance_criteria_ref
        criteria_path = str(tmp_path / criteria_result.artifact_path)

        # Step 2: Capture proof
        capture_inp = ProofCaptureInput(
            product_state_ref="abc123",
            acceptance_criteria_ref=ac_ref,
            runtime_capture_kind="text",
            phase_id="phase-1",
            run_id="run-001",
            payload="All automated checks passed.",
            output_path="captures/evidence.json",
            summary="End-to-end capture",
            tags=frozenset({"e2e"}),
        )
        capture_result = capture_proof(capture_inp, output_dir=str(tmp_path))
        assert capture_result.status.value == "captured"
        capture_path = str(tmp_path / capture_result.artifact_path)
        runtime_capture_ref = capture_result.proof_ref_fields["runtime_capture_ref"]

        # Step 3: Build handoff packet
        handoff_packet = GateReadyHandoffPacket(
            product_state_ref="abc123",
            acceptance_criteria_ref=ac_ref,
            phase_id="phase-1",
            run_id="run-001",
            gate_id="human_review_gate",
            actor_or_role="reviewer",
            proof_ref_ids=("pr-001", "pr-002"),
            payload="All checks passed.",
        )
        handoff_path = str(tmp_path / "handoff.json")
        with open(handoff_path, "w", encoding="utf-8") as f:
            f.write(handoff_packet.to_json())

        # Step 4: Build bundle
        bundle_inp = GateEvidenceBundleInput(
            product_state_ref="abc123",
            acceptance_criteria_ref=ac_ref,
            phase_id="phase-1",
            run_id="run-001",
            proof_ref_ids=("pr-001", "pr-002"),
            runtime_capture_refs=(runtime_capture_ref,),
            handoff_packet_path=handoff_path,
            acceptance_criteria_path=criteria_path,
            output_path="bundle/evidence.json",
            capture_artifact_paths=(capture_path,),
            gate_id="human_review_gate",
            actor_or_role="reviewer",
        )
        bundle_result = build_gate_evidence_bundle(bundle_inp, output_dir=str(tmp_path))
        assert bundle_result.status == GateEvidenceBundleStatus.BUNDLED, f"reason_codes={bundle_result.reason_codes}"
        assert bundle_result.reason_codes == ()
        assert bundle_result.bundle_ref is not None
        assert bundle_result.consistency_summary is not None

        # Verify bundle artifact
        bundle_file = tmp_path / bundle_result.artifact_path
        assert bundle_file.exists()
        bundle_artifact = json.loads(bundle_file.read_text(encoding="utf-8"))
        assert bundle_artifact["product_state_ref"] == "abc123"
        assert bundle_artifact["acceptance_criteria_ref"] == ac_ref
        assert bundle_artifact["bundled_at"] is None


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        import runner.gate_evidence
        doc = runner.gate_evidence.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """The gate_evidence source should not contain forbidden legacy names."""
        import inspect
        source = inspect.getsource(build_gate_evidence_bundle)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"

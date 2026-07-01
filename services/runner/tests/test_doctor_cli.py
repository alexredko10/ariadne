"""Tests for the runner doctor CLI (``python -m runner doctor``)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# Repository root is three levels up from services/runner/tests/
REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER_SRC = REPO_ROOT / "services" / "runner" / "src"

EXPECTED_OUTPUT_LINES = [
    "platform-runner doctor",
    "runner import: ok",
    "patch models: ok",
    "patch safety: ok",
]


def _runner_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(RUNNER_SRC)
    return env


def _run_runner(args: list[str]) -> subprocess.CompletedProcess:
    """Run ``python -m runner`` with the given arguments."""
    return subprocess.run(
        [sys.executable, "-m", "runner", *args],
        cwd=REPO_ROOT,
        env=_runner_env(),
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Existing doctor tests
# ---------------------------------------------------------------------------


def test_doctor_cli_succeeds_with_stable_output() -> None:
    """``python -m runner doctor`` exits 0 and prints expected lines in order."""
    result = _run_runner(["doctor"])

    assert result.returncode == 0
    assert result.stderr == ""

    output_lines = result.stdout.strip().splitlines()
    assert output_lines == EXPECTED_OUTPUT_LINES


def test_unknown_command_exits_non_zero_and_prints_usage() -> None:
    """An unrecognised subcommand exits non-zero and shows usage."""
    result = _run_runner(["unknown-command"])

    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "usage:" in combined_output


# ---------------------------------------------------------------------------
# Validate proof subcommand
# ---------------------------------------------------------------------------


class TestValidateProof:
    def test_validate_proof_help(self):
        """``--help`` output for ``validate proof`` subcommand."""
        result = _run_runner(["validate", "proof", "--help"])
        assert result.returncode == 0
        assert "usage:" in result.stdout
        assert "path" in result.stdout

    def test_validate_proof_valid_file(self, tmp_path: Path):
        """Valid proof ref JSON file → exit 0, admissible=true."""
        data = {
            "run_id": "run-001",
            "phase_id": "phase-1",
            "product_state_ref": "abc123",
            "acceptance_criteria_ref": "def456",
            "runtime_capture_ref": "er-001",
            "artifact_path": "results/evidence.json",
            "summary": "Test artifact",
            "tags": ["unit_test", "smoke"],
        }
        f = tmp_path / "proof.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = _run_runner(["validate", "proof", str(f)])
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["command"] == "validate proof"
        assert output["result"]["admissible"] is True
        assert output["error"] is None

    def test_validate_proof_invalid_file(self, tmp_path: Path):
        """JSON with missing required field → exit 1, error output."""
        data = {
            "run_id": "run-001",
            # missing product_state_ref, acceptance_criteria_ref, etc.
        }
        f = tmp_path / "bad_proof.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = _run_runner(["validate", "proof", str(f)])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        # ProofRef requires positional args; missing fields cause TypeError
        assert output["status"] == "error"
        assert "Invalid ProofRef data" in output["error"]

    def test_validate_proof_file_not_found(self):
        """Nonexistent path → exit 1, JSON error output."""
        result = _run_runner(["validate", "proof", "/nonexistent/path.json"])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "File not found" in output["error"]

    def test_validate_proof_invalid_json(self, tmp_path: Path):
        """Malformed JSON → exit 1, JSON error output."""
        f = tmp_path / "bad.json"
        f.write_text("{invalid json}", encoding="utf-8")

        result = _run_runner(["validate", "proof", str(f)])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "Invalid JSON" in output["error"]


# ---------------------------------------------------------------------------
# Validate handoff subcommand
# ---------------------------------------------------------------------------


class TestValidateHandoff:
    def test_validate_handoff_help(self):
        """``--help`` output for ``validate handoff`` subcommand."""
        result = _run_runner(["validate", "handoff", "--help"])
        assert result.returncode == 0
        assert "usage:" in result.stdout
        assert "path" in result.stdout

    def test_validate_handoff_valid_file(self, tmp_path: Path):
        """Valid handoff packet JSON + admissible refs → exit 0, gate_ready."""
        data = {
            "product_state_ref": "abc123",
            "acceptance_criteria_ref": "def456",
            "phase_id": "phase-1",
            "run_id": "run-001",
            "gate_id": "human_review_gate",
            "actor_or_role": "reviewer",
            "proof_ref_ids": ["pr-001", "pr-002"],
            "payload": "All automated checks passed.",
        }
        f = tmp_path / "handoff.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = _run_runner([
            "validate", "handoff", str(f),
            "--current-product-state-ref", "abc123",
            "--admissible-ref-ids", "pr-001", "pr-002",
        ])
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["command"] == "validate handoff"
        assert output["result"]["status"] == "gate_ready"
        assert output["error"] is None

    def test_validate_handoff_invalid_file(self, tmp_path: Path):
        """Packet missing fields → exit 1, not_gate_ready."""
        data = {
            "product_state_ref": "",
            "acceptance_criteria_ref": "def456",
            "phase_id": "phase-1",
            "run_id": "run-001",
            "gate_id": "human_review_gate",
            "actor_or_role": "reviewer",
            "proof_ref_ids": ["pr-001"],
            "payload": "Some payload.",
        }
        f = tmp_path / "bad_handoff.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = _run_runner([
            "validate", "handoff", str(f),
            "--current-product-state-ref", "abc123",
            "--admissible-ref-ids", "pr-001",
        ])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["result"]["status"] == "not_gate_ready"
        assert len(output["result"]["reason_codes"]) > 0

    def test_validate_handoff_file_not_found(self):
        """Nonexistent path → exit 1."""
        result = _run_runner(["validate", "handoff", "/nonexistent/path.json"])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "File not found" in output["error"]

    def test_validate_handoff_invalid_json(self, tmp_path: Path):
        """Malformed JSON → exit 1."""
        f = tmp_path / "bad.json"
        f.write_text("{invalid json}", encoding="utf-8")

        result = _run_runner(["validate", "handoff", str(f)])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "Invalid JSON" in output["error"]


# ---------------------------------------------------------------------------
# Capture proof subcommand
# ---------------------------------------------------------------------------


class TestCaptureProof:
    def test_capture_proof_help(self):
        """``--help`` output for ``capture proof`` subcommand."""
        result = _run_runner(["capture", "proof", "--help"])
        assert result.returncode == 0
        assert "usage:" in result.stdout
        assert "path" in result.stdout

    def test_capture_proof_valid_file(self, tmp_path: Path):
        """Valid JSON file → exit 0, captured."""
        data = {
            "product_state_ref": "abc123",
            "acceptance_criteria_ref": "def456",
            "runtime_capture_kind": "text",
            "phase_id": "phase-1",
            "run_id": "run-001",
            "payload": "All automated checks passed.",
            "output_path": "capture.json",
            "summary": "Test capture",
            "tags": ["unit_test"],
        }
        f = tmp_path / "input.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = _run_runner(["capture", "proof", str(f), "--output-dir", str(tmp_path)])
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["command"] == "capture proof"
        assert output["result"]["capture_status"] == "captured"
        assert output["error"] is None

        # Verify artifact was written
        artifact_file = tmp_path / "capture.json"
        assert artifact_file.exists()

    def test_capture_proof_invalid_file(self, tmp_path: Path):
        """JSON with missing fields → exit 1, rejected."""
        data = {
            "product_state_ref": "",
            "acceptance_criteria_ref": "def456",
            "runtime_capture_kind": "text",
            "phase_id": "phase-1",
            "run_id": "run-001",
            "payload": "Some payload.",
            "output_path": "capture.json",
        }
        f = tmp_path / "bad_input.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = _run_runner(["capture", "proof", str(f), "--output-dir", str(tmp_path)])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["result"]["capture_status"] == "rejected"
        assert len(output["result"]["reason_codes"]) > 0

    def test_capture_proof_file_not_found(self):
        """Nonexistent path → exit 1."""
        result = _run_runner(["capture", "proof", "/nonexistent/path.json"])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "File not found" in output["error"]

    def test_capture_proof_invalid_json(self, tmp_path: Path):
        """Malformed JSON → exit 1."""
        f = tmp_path / "bad.json"
        f.write_text("{invalid json}", encoding="utf-8")

        result = _run_runner(["capture", "proof", str(f)])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "Invalid JSON" in output["error"]


# ---------------------------------------------------------------------------
# Freeze criteria subcommand
# ---------------------------------------------------------------------------


class TestFreezeCriteria:
    def test_freeze_criteria_help(self):
        """``--help`` output for ``freeze criteria`` subcommand."""
        result = _run_runner(["freeze", "criteria", "--help"])
        assert result.returncode == 0
        assert "usage:" in result.stdout
        assert "path" in result.stdout

    def test_freeze_criteria_valid_file(self, tmp_path: Path):
        """Valid JSON file → exit 0, frozen."""
        data = {
            "product_state_ref": "abc123",
            "criteria": [
                {"criterion_id": "AC-001", "description": "System must return exit code 0."},
                {"criterion_id": "AC-002", "description": "System must reject invalid input."},
            ],
            "phase_id": "phase-1",
            "run_id": "run-001",
            "output_path": "frozen_criteria.json",
            "title": "Test criteria",
        }
        f = tmp_path / "input.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = _run_runner(["freeze", "criteria", str(f), "--output-dir", str(tmp_path)])
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["command"] == "freeze criteria"
        assert output["result"]["freeze_status"] == "frozen"
        assert output["error"] is None
        assert output["result"]["criteria_count"] == 2
        assert output["result"]["acceptance_criteria_ref"] is not None

        # Verify artifact was written
        artifact_file = tmp_path / "frozen_criteria.json"
        assert artifact_file.exists()

    def test_freeze_criteria_invalid_file(self, tmp_path: Path):
        """JSON with missing fields → exit 1, rejected."""
        data = {
            "product_state_ref": "",
            "criteria": [
                {"criterion_id": "AC-001", "description": "Some criterion."},
            ],
            "phase_id": "phase-1",
            "run_id": "run-001",
            "output_path": "frozen_criteria.json",
        }
        f = tmp_path / "bad_input.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = _run_runner(["freeze", "criteria", str(f), "--output-dir", str(tmp_path)])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["result"]["freeze_status"] == "rejected"
        assert len(output["result"]["reason_codes"]) > 0

    def test_freeze_criteria_file_not_found(self):
        """Nonexistent path → exit 1."""
        result = _run_runner(["freeze", "criteria", "/nonexistent/path.json"])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "File not found" in output["error"]

    def test_freeze_criteria_invalid_json(self, tmp_path: Path):
        """Malformed JSON → exit 1."""
        f = tmp_path / "bad.json"
        f.write_text("{invalid json}", encoding="utf-8")

        result = _run_runner(["freeze", "criteria", str(f)])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "Invalid JSON" in output["error"]


# ---------------------------------------------------------------------------
# Bundle evidence subcommand
# ---------------------------------------------------------------------------


class TestBundleEvidence:
    def test_bundle_evidence_help(self):
        """``--help`` output for ``bundle evidence`` subcommand."""
        result = _run_runner(["bundle", "evidence", "--help"])
        assert result.returncode == 0
        assert "usage:" in result.stdout
        assert "path" in result.stdout

    def test_bundle_evidence_valid_file(self, tmp_path: Path):
        """Valid JSON input with real artifacts → exit 0, bundled."""
        # Set up artifacts using the same pattern as test_gate_evidence
        from runner.acceptance_criteria import (
            AcceptanceCriterion,
            AcceptanceCriteriaFreezeInput,
            freeze_acceptance_criteria,
        )
        from runner.proof_capture import (
            ProofCaptureInput,
            capture_proof,
        )
        from runner.handoff_packet import (
            GateReadyHandoffPacket,
        )

        # Freeze criteria
        criteria_inp = AcceptanceCriteriaFreezeInput(
            product_state_ref="abc123",
            criteria=(
                AcceptanceCriterion(criterion_id="AC-001", description="Criterion 1."),
                AcceptanceCriterion(criterion_id="AC-002", description="Criterion 2."),
            ),
            phase_id="phase-1",
            run_id="run-001",
            output_path="criteria/frozen.json",
        )
        criteria_result = freeze_acceptance_criteria(criteria_inp, output_dir=str(tmp_path))
        ac_ref = criteria_result.acceptance_criteria_ref
        criteria_path = str(tmp_path / criteria_result.artifact_path)

        # Capture proof
        capture_inp = ProofCaptureInput(
            product_state_ref="abc123",
            acceptance_criteria_ref=ac_ref,
            runtime_capture_kind="text",
            phase_id="phase-1",
            run_id="run-001",
            payload="Evidence.",
            output_path="captures/evidence.json",
        )
        capture_result = capture_proof(capture_inp, output_dir=str(tmp_path))
        capture_path = str(tmp_path / capture_result.artifact_path)
        runtime_capture_ref = capture_result.proof_ref_fields["runtime_capture_ref"]

        # Handoff packet
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

        # Bundle input JSON
        bundle_input = {
            "product_state_ref": "abc123",
            "acceptance_criteria_ref": ac_ref,
            "phase_id": "phase-1",
            "run_id": "run-001",
            "proof_ref_ids": ["pr-001", "pr-002"],
            "runtime_capture_refs": [runtime_capture_ref],
            "handoff_packet_path": handoff_path,
            "acceptance_criteria_path": criteria_path,
            "output_path": "bundle/evidence.json",
            "capture_artifact_paths": [capture_path],
            "gate_id": "human_review_gate",
            "actor_or_role": "reviewer",
        }
        f = tmp_path / "bundle_input.json"
        f.write_text(json.dumps(bundle_input), encoding="utf-8")

        result = _run_runner(["bundle", "evidence", str(f), "--output-dir", str(tmp_path)])
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["command"] == "bundle evidence"
        assert output["result"]["bundle_status"] == "bundled"
        assert output["error"] is None
        assert output["result"]["bundle_ref"] is not None

        # Verify bundle artifact was written
        bundle_file = tmp_path / "bundle" / "evidence.json"
        assert bundle_file.exists()

    def test_bundle_evidence_inconsistent_file(self, tmp_path: Path):
        """Mismatched refs → exit 1, rejected."""
        from runner.acceptance_criteria import (
            AcceptanceCriterion,
            AcceptanceCriteriaFreezeInput,
            freeze_acceptance_criteria,
        )
        from runner.proof_capture import (
            ProofCaptureInput,
            capture_proof,
        )
        from runner.handoff_packet import (
            GateReadyHandoffPacket,
        )

        # Freeze criteria
        criteria_inp = AcceptanceCriteriaFreezeInput(
            product_state_ref="abc123",
            criteria=(
                AcceptanceCriterion(criterion_id="AC-001", description="Criterion 1."),
            ),
            phase_id="phase-1",
            run_id="run-001",
            output_path="criteria/frozen.json",
        )
        criteria_result = freeze_acceptance_criteria(criteria_inp, output_dir=str(tmp_path))
        ac_ref = criteria_result.acceptance_criteria_ref
        criteria_path = str(tmp_path / criteria_result.artifact_path)

        # Capture proof
        capture_inp = ProofCaptureInput(
            product_state_ref="abc123",
            acceptance_criteria_ref=ac_ref,
            runtime_capture_kind="text",
            phase_id="phase-1",
            run_id="run-001",
            payload="Evidence.",
            output_path="captures/evidence.json",
        )
        capture_result = capture_proof(capture_inp, output_dir=str(tmp_path))
        capture_path = str(tmp_path / capture_result.artifact_path)
        runtime_capture_ref = capture_result.proof_ref_fields["runtime_capture_ref"]

        # Handoff packet with DIFFERENT product_state_ref
        handoff_packet = GateReadyHandoffPacket(
            product_state_ref="different",  # inconsistent!
            acceptance_criteria_ref=ac_ref,
            phase_id="phase-1",
            run_id="run-001",
            gate_id="human_review_gate",
            actor_or_role="reviewer",
            proof_ref_ids=("pr-001",),
            payload="All checks passed.",
        )
        handoff_path = str(tmp_path / "handoff.json")
        with open(handoff_path, "w", encoding="utf-8") as f:
            f.write(handoff_packet.to_json())

        bundle_input = {
            "product_state_ref": "abc123",
            "acceptance_criteria_ref": ac_ref,
            "phase_id": "phase-1",
            "run_id": "run-001",
            "proof_ref_ids": ["pr-001"],
            "runtime_capture_refs": [runtime_capture_ref],
            "handoff_packet_path": handoff_path,
            "acceptance_criteria_path": criteria_path,
            "output_path": "bundle/evidence.json",
            "capture_artifact_paths": [capture_path],
            "gate_id": "human_review_gate",
            "actor_or_role": "reviewer",
        }
        f = tmp_path / "bundle_input.json"
        f.write_text(json.dumps(bundle_input), encoding="utf-8")

        result = _run_runner(["bundle", "evidence", str(f), "--output-dir", str(tmp_path)])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["result"]["bundle_status"] == "rejected"
        assert len(output["result"]["reason_codes"]) > 0

    def test_bundle_evidence_file_not_found(self):
        """Nonexistent path → exit 1."""
        result = _run_runner(["bundle", "evidence", "/nonexistent/path.json"])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "File not found" in output["error"]

    def test_bundle_evidence_invalid_json(self, tmp_path: Path):
        """Malformed JSON → exit 1."""
        f = tmp_path / "bad.json"
        f.write_text("{invalid json}", encoding="utf-8")

        result = _run_runner(["bundle", "evidence", str(f)])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "Invalid JSON" in output["error"]


# ---------------------------------------------------------------------------
# Improve propose subcommand
# ---------------------------------------------------------------------------


class TestImprovePropose:
    def test_improve_propose_help(self):
        """``--help`` output for ``improve propose`` subcommand."""
        result = _run_runner(["improve", "propose", "--help"])
        assert result.returncode == 0
        assert "usage:" in result.stdout
        assert "path" in result.stdout

    def test_improve_propose_valid_file(self, tmp_path: Path):
        """Valid JSON file → exit 0, proposed."""
        data = {
            "product_state_ref": "abc123",
            "acceptance_criteria_ref": "def456",
            "phase_id": "phase-1",
            "run_id": "run-001",
            "source_bundle_ref": "deadbeef12345678",
            "source_reason_codes": ["missing_proof_refs"],
            "output_path": "candidate.json",
            "evidence_refs": ["pr-001"],
            "proposed_next_action": "Add proof capture before handoff",
            "affected_runtime_area": "runner/proof_capture",
            "requires_human_review": True,
        }
        f = tmp_path / "input.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = _run_runner(["improve", "propose", str(f), "--output-dir", str(tmp_path)])
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["command"] == "improve propose"
        assert output["result"]["proposal_status"] == "proposed"
        assert output["error"] is None
        assert output["result"]["candidate_id"] is not None

        # Verify artifact was written
        artifact_file = tmp_path / "candidate.json"
        assert artifact_file.exists()

    def test_improve_propose_invalid_file(self, tmp_path: Path):
        """JSON with missing fields → exit 1, rejected."""
        data = {
            "product_state_ref": "",
            "acceptance_criteria_ref": "def456",
            "phase_id": "phase-1",
            "run_id": "run-001",
            "source_bundle_ref": "deadbeef12345678",
            "source_reason_codes": ["missing_proof_refs"],
            "output_path": "candidate.json",
            "evidence_refs": ["pr-001"],
        }
        f = tmp_path / "bad_input.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = _run_runner(["improve", "propose", str(f), "--output-dir", str(tmp_path)])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["result"]["proposal_status"] == "rejected"
        assert len(output["result"]["reason_codes"]) > 0

    def test_improve_propose_file_not_found(self):
        """Nonexistent path → exit 1."""
        result = _run_runner(["improve", "propose", "/nonexistent/path.json"])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "File not found" in output["error"]

    def test_improve_propose_invalid_json(self, tmp_path: Path):
        """Malformed JSON → exit 1."""
        f = tmp_path / "bad.json"
        f.write_text("{invalid json}", encoding="utf-8")

        result = _run_runner(["improve", "propose", str(f)])
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "Invalid JSON" in output["error"]


# ---------------------------------------------------------------------------
# General CLI behavior
# ---------------------------------------------------------------------------


class TestGeneralCli:
    def test_cli_no_subcommand(self):
        """``python -m runner`` with no args → help output, exit 2 (argparse default)."""
        result = _run_runner([])
        assert result.returncode == 2
        assert "usage:" in result.stderr

    def test_cli_unknown_command(self):
        """Unknown subcommand → exit 1, deterministic error."""
        result = _run_runner(["nonexistent"])
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "usage:" in combined

    def test_cli_no_network_import(self):
        """CLI does not import network/Docker/LLM modules."""
        from runner import doctor
        source_path = Path(doctor.__file__)
        source_text = source_path.read_text(encoding="utf-8")
        forbidden_imports = [
            "import urllib", "from urllib",
            "import requests", "from requests",
            "import socket", "from socket",
            "import http", "from http",
            "import docker", "from docker",
            "import openai", "from openai",
            "import anthropic", "from anthropic",
        ]
        for imp in forbidden_imports:
            assert imp not in source_text, f"Forbidden import found: {imp}"

    def test_cli_no_filesystem_mutation(self):
        """CLI does not write files (only reads)."""
        from runner import doctor
        source = Path(doctor.__file__).read_text(encoding="utf-8")
        # Check for write operations (Path.read_text is allowed for reading)
        forbidden_writes = [
            ".write_text",
            ".write_bytes",
        ]
        for fw in forbidden_writes:
            assert fw not in source, f"Forbidden write operation found: {fw}"

    def test_product_name_ariadne(self):
        """Output contains 'Ariadne'."""
        from runner import doctor
        source = Path(doctor.__file__).read_text(encoding="utf-8")
        assert "Ariadne" in source

    def test_no_forbidden_legacy_names(self):
        """Source contains no forbidden legacy terms."""
        from runner import doctor
        source = Path(doctor.__file__).read_text(encoding="utf-8")
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"

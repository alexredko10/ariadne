"""Tests for the deterministic session continuity packet runtime object."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from runner.session_continuity import (
    SessionContinuityInput,
    SessionContinuityPacket,
    SessionContinuityResult,
    SessionContinuityStatus,
    build_session_continuity_packet,
    REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED,
    REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED,
    REASON_GIT_MUTATION_NOT_ALLOWED,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
    REASON_INVALID_SCOPE_BOUNDARY,
    REASON_MISSING_APPROVED_PLAN_REF,
    REASON_MISSING_CURRENT_GOAL,
    REASON_MISSING_CURRENT_PR,
    REASON_MISSING_DRIFT_RISK,
    REASON_MISSING_EVIDENCE_REFS,
    REASON_MISSING_NEXT_SAFE_ACTION,
    REASON_MISSING_PRODUCT_STATE_REF,
    REASON_MISSING_REVIEW_STATUS,
    REASON_OVERSIZED_CONTINUITY_PACKET,
    REASON_PROVIDER_CALL_NOT_ALLOWED,
    REASON_UNBOUNDED_CONTINUITY_OUTPUT_PATH,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_input(**overrides: object) -> SessionContinuityInput:
    kwargs = {
        "product_state_ref": "abc123",
        "phase_id": "phase-1",
        "run_id": "run-001",
        "current_pr": "0108-session-continuity-packet",
        "current_goal": "Add session continuity packet runtime object",
        "approved_plan_ref": ".project-memory/pr/0108-session-continuity-packet/PLAN.md",
        "latest_review_status": "pending",
        "latest_validation_status": "pending",
        "gate_evidence_refs": ("deadbeef12345678",),
        "improvement_candidate_refs": (),
        "known_drift_risks": ("PR 0108 scope must not include frontend",),
        "deferred_capabilities": ("Frontend continuity UI",),
        "next_safe_action": "Review and merge PR 0108",
        "blocked_actions": ("Waiting for PR 0107 merge",),
        "files_in_scope": ("services/runner/src/runner/session_continuity.py",),
        "files_out_of_scope": ("apps/frontend/",),
        "output_path": "continuity/session.json",
        "session_label": "PR 0108 implementation",
        "evidence_refs": ("pr-001", "capture-text-abc123def456"),
        "requires_human_review": True,
    }
    kwargs.update(overrides)
    return SessionContinuityInput(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Valid packet
# ---------------------------------------------------------------------------


class TestValidPacket:
    def test_valid_continuity_packet_created(self, tmp_path: Path):
        """Valid input with all fields → CREATED."""
        inp = _valid_input()
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.CREATED, f"reason_codes={result.reason_codes}"
        assert result.reason_codes == ()
        assert result.packet is not None
        assert result.artifact_path is not None

        # Verify artifact was written
        artifact_file = tmp_path / result.artifact_path
        assert artifact_file.exists()
        artifact = json.loads(artifact_file.read_text(encoding="utf-8"))
        assert artifact["ariadne_continuity_version"] == "1"
        assert artifact["created_at"] is None
        assert artifact["continuity_ref"] == result.packet.continuity_ref

    def test_packet_deterministic_output_fields(self, tmp_path: Path):
        """Packet includes all required fields."""
        inp = _valid_input()
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.CREATED
        p = result.packet
        assert p is not None
        assert p.continuity_ref is not None
        assert len(p.continuity_ref) == 16
        int(p.continuity_ref, 16)  # should not raise
        assert p.product_state_ref == "abc123"
        assert p.current_pr == "0108-session-continuity-packet"
        assert p.current_goal == "Add session continuity packet runtime object"
        assert p.approved_plan_ref == ".project-memory/pr/0108-session-continuity-packet/PLAN.md"
        assert p.latest_review_status == "pending"
        assert p.latest_validation_status == "pending"
        assert p.gate_evidence_refs == ("deadbeef12345678",)
        assert p.known_drift_risks == ("PR 0108 scope must not include frontend",)
        assert p.next_safe_action == "Review and merge PR 0108"
        assert p.files_in_scope == ("services/runner/src/runner/session_continuity.py",)
        assert p.files_out_of_scope == ("apps/frontend/",)
        assert p.requires_human_review is True

    def test_same_input_same_continuity_ref(self, tmp_path: Path):
        """Same input twice produces same continuity_ref."""
        inp = _valid_input()
        result1 = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        result2 = build_session_continuity_packet(inp, output_dir=str(tmp_path / "other"))
        assert result1.packet is not None
        assert result2.packet is not None
        assert result1.packet.continuity_ref == result2.packet.continuity_ref

    def test_changed_goal_changes_continuity_ref(self, tmp_path: Path):
        """Different goal changes continuity_ref."""
        inp1 = _valid_input()
        inp2 = _valid_input(current_goal="Different goal")
        result1 = build_session_continuity_packet(inp1, output_dir=str(tmp_path))
        result2 = build_session_continuity_packet(inp2, output_dir=str(tmp_path / "other"))
        assert result1.packet is not None
        assert result2.packet is not None
        assert result1.packet.continuity_ref != result2.packet.continuity_ref

    def test_changed_next_safe_action_changes_ref(self, tmp_path: Path):
        """Different next_safe_action changes continuity_ref."""
        inp1 = _valid_input()
        inp2 = _valid_input(next_safe_action="Different action")
        result1 = build_session_continuity_packet(inp1, output_dir=str(tmp_path))
        result2 = build_session_continuity_packet(inp2, output_dir=str(tmp_path / "other"))
        assert result1.packet is not None
        assert result2.packet is not None
        assert result1.packet.continuity_ref != result2.packet.continuity_ref

    def test_resume_summary_deterministic(self, tmp_path: Path):
        """Summary is template-based and deterministic."""
        inp = _valid_input()
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.CREATED
        p = result.packet
        assert p is not None
        assert "Session: PR 0108 implementation" in p.resume_summary
        assert "Goal: Add session continuity packet" in p.resume_summary
        assert "Next safe action: Review and merge PR 0108" in p.resume_summary
        assert "Drift risks: 1 risk(s)" in p.resume_summary
        assert "Files in scope: 1 file(s)" in p.resume_summary
        assert "Review status: pending" in p.resume_summary
        assert "Requires human review: True" in p.resume_summary

    def test_resume_prompt_template_based(self, tmp_path: Path):
        """Prompt includes objective, scope, evidence, drift, next action, forbidden actions."""
        inp = _valid_input()
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.CREATED
        p = result.packet
        assert p is not None
        assert "## Resume Context" in p.resume_prompt
        assert "Objective:" in p.resume_prompt
        assert "PR:" in p.resume_prompt
        assert "Plan ref:" in p.resume_prompt
        assert "## Evidence" in p.resume_prompt
        assert "## Scope" in p.resume_prompt
        assert "## Drift Risks" in p.resume_prompt
        assert "## Next Safe Action" in p.resume_prompt
        assert "## Blocked Actions" in p.resume_prompt
        assert "## Forbidden Actions" in p.resume_prompt
        assert "Do not edit source code autonomously" in p.resume_prompt
        assert "Do not create git commits or PRs" in p.resume_prompt
        assert "Do not call external providers or models" in p.resume_prompt
        assert "Do not execute shell commands" in p.resume_prompt
        assert "Do not approve gates or finalize work" in p.resume_prompt
        assert "Do not modify files outside files_in_scope" in p.resume_prompt

    def test_resume_prompt_no_hidden_reasoning(self, tmp_path: Path):
        """Prompt does not contain hidden reasoning patterns."""
        inp = _valid_input()
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.CREATED
        p = result.packet
        assert p is not None
        assert "<cot>" not in p.resume_prompt
        assert "<chain_of_thought>" not in p.resume_prompt
        assert "hidden_reasoning" not in p.resume_prompt

    def test_artifact_json_deterministic(self, tmp_path: Path):
        """Same input produces identical JSON."""
        inp = _valid_input()
        result1 = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        result2 = build_session_continuity_packet(inp, output_dir=str(tmp_path / "other"))
        assert result1.packet is not None
        assert result2.packet is not None
        assert result1.packet.continuity_ref == result2.packet.continuity_ref

        art1 = json.loads((tmp_path / result1.artifact_path).read_text(encoding="utf-8"))
        art2 = json.loads((tmp_path / "other" / result2.artifact_path).read_text(encoding="utf-8"))
        assert art1 == art2

    def test_packet_includes_files_in_scope(self, tmp_path: Path):
        """files_in_scope present and sorted in output."""
        inp = _valid_input(
            files_in_scope=("z_file.py", "a_file.py", "m_file.py"),
        )
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.CREATED
        p = result.packet
        assert p is not None
        assert p.files_in_scope == ("a_file.py", "m_file.py", "z_file.py")

    def test_packet_includes_files_out_of_scope(self, tmp_path: Path):
        """files_out_of_scope present and sorted in output."""
        inp = _valid_input(
            files_out_of_scope=("z_dir/", "a_dir/"),
        )
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.CREATED
        p = result.packet
        assert p is not None
        assert p.files_out_of_scope == ("a_dir/", "z_dir/")


# ---------------------------------------------------------------------------
# Missing fields
# ---------------------------------------------------------------------------


class TestMissingFields:
    def test_missing_product_state_ref_fails(self, tmp_path: Path):
        inp = _valid_input(product_state_ref="")
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_MISSING_PRODUCT_STATE_REF in result.reason_codes

    def test_missing_current_pr_fails(self, tmp_path: Path):
        inp = _valid_input(current_pr="")
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_MISSING_CURRENT_PR in result.reason_codes

    def test_missing_current_goal_fails(self, tmp_path: Path):
        inp = _valid_input(current_goal="")
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_MISSING_CURRENT_GOAL in result.reason_codes

    def test_missing_approved_plan_ref_fails(self, tmp_path: Path):
        inp = _valid_input(approved_plan_ref="")
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_MISSING_APPROVED_PLAN_REF in result.reason_codes

    def test_missing_evidence_refs_fails(self, tmp_path: Path):
        """All evidence ref groups empty → REJECTED."""
        inp = _valid_input(
            gate_evidence_refs=(),
            improvement_candidate_refs=(),
            evidence_refs=(),
        )
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_MISSING_EVIDENCE_REFS in result.reason_codes

    def test_missing_next_safe_action_fails(self, tmp_path: Path):
        inp = _valid_input(next_safe_action="")
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_MISSING_NEXT_SAFE_ACTION in result.reason_codes

    def test_missing_review_status_fails(self, tmp_path: Path):
        inp = _valid_input(latest_review_status="")
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_MISSING_REVIEW_STATUS in result.reason_codes

    def test_missing_drift_risk_fails(self, tmp_path: Path):
        inp = _valid_input(known_drift_risks=())
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_MISSING_DRIFT_RISK in result.reason_codes


# ---------------------------------------------------------------------------
# Invalid scope boundary
# ---------------------------------------------------------------------------


class TestInvalidScopeBoundary:
    def test_invalid_scope_boundary_fails(self, tmp_path: Path):
        """Same file in both in_scope and out_of_scope → REJECTED."""
        inp = _valid_input(
            files_in_scope=("shared_file.py", "a_file.py"),
            files_out_of_scope=("shared_file.py", "b_file.py"),
        )
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_INVALID_SCOPE_BOUNDARY in result.reason_codes


# ---------------------------------------------------------------------------
# Hidden reasoning
# ---------------------------------------------------------------------------


class TestHiddenReasoning:
    def test_hidden_reasoning_in_goal_fails(self, tmp_path: Path):
        inp = _valid_input(current_goal="Some text <cot> hidden")
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# External URL-only evidence
# ---------------------------------------------------------------------------


class TestExternalUrlOnly:
    def test_external_url_only_evidence_fails(self, tmp_path: Path):
        inp = _valid_input(next_safe_action="http://example.com/evidence")
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Forbidden actions
# ---------------------------------------------------------------------------


class TestForbiddenActions:
    def test_autonomous_code_change_in_action_fails(self, tmp_path: Path):
        inp = _valid_input(next_safe_action="Run pip install requests")
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED in result.reason_codes

    def test_git_mutation_in_action_fails(self, tmp_path: Path):
        inp = _valid_input(next_safe_action="Run git commit -m 'fix'")
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_GIT_MUTATION_NOT_ALLOWED in result.reason_codes

    def test_provider_call_in_action_fails(self, tmp_path: Path):
        inp = _valid_input(next_safe_action="import openai to fix this")
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_PROVIDER_CALL_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Unbounded output path
# ---------------------------------------------------------------------------


class TestUnboundedOutputPath:
    def test_unbounded_output_path_fails(self, tmp_path: Path):
        inp = _valid_input(output_path="../escape/session.json")
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_UNBOUNDED_CONTINUITY_OUTPUT_PATH in result.reason_codes


# ---------------------------------------------------------------------------
# Oversized packet
# ---------------------------------------------------------------------------


class TestOversizedPacket:
    def test_oversized_packet_fails(self, tmp_path: Path):
        long_action = "x" * 4097
        inp = _valid_input(next_safe_action=long_action)
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        assert REASON_OVERSIZED_CONTINUITY_PACKET in result.reason_codes


# ---------------------------------------------------------------------------
# No filesystem write when rejected
# ---------------------------------------------------------------------------


class TestNoFilesystemWriteWhenRejected:
    def test_no_filesystem_write_when_rejected(self, tmp_path: Path):
        inp = _valid_input(product_state_ref="")
        initial_files = set(os.listdir(tmp_path))
        result = build_session_continuity_packet(inp, output_dir=str(tmp_path))
        assert result.status == SessionContinuityStatus.REJECTED
        final_files = set(os.listdir(tmp_path))
        assert final_files == initial_files


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        import runner.session_continuity
        doc = runner.session_continuity.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """The session_continuity source should not contain forbidden legacy names."""
        import inspect
        source = inspect.getsource(build_session_continuity_packet)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"

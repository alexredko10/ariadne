"""Tests for the prompt composer."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from runner.prompt_composer import (
    PromptComposerRequest,
    PromptPacket,
    PromptComposerResult,
    PromptComposerStatus,
    compose_pr_prompts,
    REASON_MISSING_PR_ID,
    REASON_MISSING_BRANCH,
    REASON_MISSING_TASK_TITLE,
    REASON_MISSING_TASK_DESCRIPTION,
    REASON_MISSING_ROADMAP,
    REASON_MISSING_AGENTS_DIR,
    _FORBIDDEN_COMMANDS,
    _TEMPLATE_IDS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agents_dir(tmp_path: Path) -> str:
    """Create a temporary agents directory with required configs."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(exist_ok=True)

    # coder.yml
    (agents_dir / "coder.yml").write_text(
        "model: coder-model\ninstruction: You are the coder.\n", encoding="utf-8"
    )
    # plan-review.yml
    (agents_dir / "plan-review.yml").write_text(
        "model: plan-review-model\ninstruction: You are the plan-review agent.\n", encoding="utf-8"
    )
    # precommit-review.yml
    (agents_dir / "precommit-review.yml").write_text(
        "model: precommit-model\ninstruction: You are the precommit-review agent.\n", encoding="utf-8"
    )
    return str(agents_dir)


def _roadmap(tmp_path: Path) -> str:
    """Create a temporary ROADMAP.md with Production Line Stream."""
    roadmap_path = tmp_path / "ROADMAP.md"
    roadmap_path.write_text(
        "## Production Line Stream (ACTIVE)\n"
        "0124 — Agent Runner Bridge\n"
        "0125 — Prompt Composer\n"
        "## Frozen until PR 0136 acceptance\n"
        "Frozen streams list.\n",
        encoding="utf-8",
    )
    return str(roadmap_path)


def _valid_request(tmp_path: Path) -> PromptComposerRequest:
    """Create a valid PromptComposerRequest."""
    agents_dir = _agents_dir(tmp_path)
    roadmap_path = _roadmap(tmp_path)
    return PromptComposerRequest(
        pr_id="0125",
        branch="0125-prompt-composer",
        task_title="Prompt Composer",
        task_description="Implement the prompt composer module.",
        roadmap_path=roadmap_path,
        agents_dir=agents_dir,
        repo_root=str(tmp_path),
    )


# ---------------------------------------------------------------------------
# Four packets
# ---------------------------------------------------------------------------


class TestComposeFourPackets:
    def test_four_packets(self, tmp_path: Path):
        """compose_pr_prompts returns exactly four prompt packets."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        assert result.status == PromptComposerStatus.READY
        assert len(result.prompt_packets) == 4


# ---------------------------------------------------------------------------
# Prompt order
# ---------------------------------------------------------------------------


class TestPromptOrder:
    def test_prompt_order(self, tmp_path: Path):
        """Packets in order: planner → plan-review → coder → precommit-review."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        assert result.prompt_order == ("planner", "plan-review", "coder", "precommit-review")
        kinds = [p.prompt_kind for p in result.prompt_packets]
        assert kinds == ["planner", "plan-review", "coder", "precommit-review"]


# ---------------------------------------------------------------------------
# Packet fields
# ---------------------------------------------------------------------------


class TestPacketFields:
    def test_packet_fields(self, tmp_path: Path):
        """Each packet has all required fields."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        for packet in result.prompt_packets:
            assert packet.agent_name is not None
            assert packet.prompt_kind is not None
            assert packet.prompt_text is not None
            assert len(packet.prompt_text) > 0
            assert packet.prompt_hash is not None
            assert len(packet.prompt_hash) == 16
            assert isinstance(packet.required_inputs, tuple)
            assert packet.expected_output_path is not None
            assert isinstance(packet.allowed_write_paths, tuple)
            assert isinstance(packet.forbidden_write_paths, tuple)
            assert isinstance(packet.forbidden_commands, tuple)
            assert isinstance(packet.evidence_requirements, tuple)
            assert isinstance(packet.boundary_confirmations, tuple)
            assert packet.source_template_hash is not None
            assert len(packet.source_template_hash) == 16
            assert packet.source_context_hash is not None
            assert len(packet.source_context_hash) == 16
            assert packet.ready_for_agent_runner_bridge is True


# ---------------------------------------------------------------------------
# Prompt hash stable
# ---------------------------------------------------------------------------


class TestPromptHashStable:
    def test_prompt_hash_stable(self, tmp_path: Path):
        """Same request → same prompt_hash per packet."""
        request = _valid_request(tmp_path)
        result1 = compose_pr_prompts(request)
        result2 = compose_pr_prompts(request)
        for p1, p2 in zip(result1.prompt_packets, result2.prompt_packets):
            assert p1.prompt_hash == p2.prompt_hash


# ---------------------------------------------------------------------------
# Task description hash
# ---------------------------------------------------------------------------


class TestTaskDescriptionHash:
    def test_task_description_hash_deterministic(self, tmp_path: Path):
        """task_description_hash is deterministic SHA256[:16]."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        expected = hashlib.sha256(request.task_description.encode("utf-8")).hexdigest()[:16]
        assert result.task_description_hash == expected

    def test_different_description_different_hash(self, tmp_path: Path):
        """Different descriptions → different hashes."""
        request1 = _valid_request(tmp_path)
        request2 = PromptComposerRequest(
            pr_id="0125",
            branch="0125-prompt-composer",
            task_title="Different",
            task_description="Different description.",
            roadmap_path=request1.roadmap_path,
            agents_dir=request1.agents_dir,
            repo_root=request1.repo_root,
        )
        result1 = compose_pr_prompts(request1)
        result2 = compose_pr_prompts(request2)
        assert result1.task_description_hash != result2.task_description_hash


# ---------------------------------------------------------------------------
# Context hash
# ---------------------------------------------------------------------------


class TestContextHash:
    def test_context_hash_includes_evidence(self, tmp_path: Path):
        """context_hash includes ROADMAP and agents configs."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        assert result.context_hash is not None
        assert len(result.context_hash) == 16

    def test_context_hash_deterministic(self, tmp_path: Path):
        """Same inputs → same context_hash."""
        request = _valid_request(tmp_path)
        result1 = compose_pr_prompts(request)
        result2 = compose_pr_prompts(request)
        assert result1.context_hash == result2.context_hash


# ---------------------------------------------------------------------------
# Source template hash
# ---------------------------------------------------------------------------


class TestSourceTemplateHash:
    def test_same_kind_same_template_hash(self, tmp_path: Path):
        """Same prompt_kind → same source_template_hash."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        for packet in result.prompt_packets:
            template_id = _TEMPLATE_IDS[packet.prompt_kind]
            expected_hash = hashlib.sha256(template_id.encode("utf-8")).hexdigest()[:16]
            assert packet.source_template_hash == expected_hash


# ---------------------------------------------------------------------------
# Planner template
# ---------------------------------------------------------------------------


class TestPlannerTemplate:
    def test_planner_includes_roadmap_evidence(self, tmp_path: Path):
        """Planner prompt includes roadmap evidence."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        planner = result.prompt_packets[0]
        assert planner.prompt_kind == "planner"
        assert "Production Line Stream" in planner.prompt_text
        assert "Agent Runner Bridge" in planner.prompt_text
        assert "Prompt Composer" in planner.prompt_text

    def test_planner_includes_agent_config_inventory(self, tmp_path: Path):
        """Planner prompt includes agent config inventory."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        planner = result.prompt_packets[0]
        assert "coder.yml" in planner.prompt_text
        assert "plan-review.yml" in planner.prompt_text
        assert "precommit-review.yml" in planner.prompt_text


# ---------------------------------------------------------------------------
# Plan-review template
# ---------------------------------------------------------------------------


class TestPlanReviewTemplate:
    def test_plan_review_includes_plan_ref(self, tmp_path: Path):
        """Plan-review prompt includes reference to PLAN.md."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        plan_review = result.prompt_packets[1]
        assert plan_review.prompt_kind == "plan-review"
        assert "PLAN.md" in plan_review.prompt_text


# ---------------------------------------------------------------------------
# Coder template
# ---------------------------------------------------------------------------


class TestCoderTemplate:
    def test_coder_includes_plan_ref(self, tmp_path: Path):
        """Coder prompt includes reference to approved PLAN.md."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        coder = result.prompt_packets[2]
        assert coder.prompt_kind == "coder"
        assert "PLAN.md" in coder.prompt_text


# ---------------------------------------------------------------------------
# Precommit template
# ---------------------------------------------------------------------------


class TestPrecommitTemplate:
    def test_precommit_includes_validation(self, tmp_path: Path):
        """Precommit-review prompt includes PLAN DRIFT GATE and validation."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        precommit = result.prompt_packets[3]
        assert precommit.prompt_kind == "precommit-review"
        assert "PLAN DRIFT GATE" in precommit.prompt_text
        assert "validation" in precommit.prompt_text.lower()


# ---------------------------------------------------------------------------
# Forbidden git commands
# ---------------------------------------------------------------------------


class TestForbiddenGitCommands:
    def test_forbidden_git_commands_in_prompts(self, tmp_path: Path):
        """Generated prompts forbid git add/commit/push, gh pr create, gh release."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        for packet in result.prompt_packets:
            text = packet.prompt_text
            assert "git add" in text
            assert "git commit" in text
            assert "git push" in text
            assert "gh pr create" in text
            assert "gh release" in text


# ---------------------------------------------------------------------------
# Forbidden Docker commands
# ---------------------------------------------------------------------------


class TestForbiddenDockerCommands:
    def test_forbidden_docker_commands_in_prompts(self, tmp_path: Path):
        """Generated prompts forbid docker, docker compose."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        for packet in result.prompt_packets:
            assert "docker" in packet.prompt_text
            assert "docker compose" in packet.prompt_text


# ---------------------------------------------------------------------------
# Forbidden agent modification
# ---------------------------------------------------------------------------


class TestForbiddenAgentModification:
    def test_forbidden_agent_modification(self, tmp_path: Path):
        """Generated prompts forbid editing agents/*.yml."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        for packet in result.prompt_packets:
            assert "agents/*.yml" in packet.prompt_text


# ---------------------------------------------------------------------------
# Missing ROADMAP
# ---------------------------------------------------------------------------


class TestMissingRoadmap:
    def test_missing_roadmap_blocked(self, tmp_path: Path):
        """Missing ROADMAP.md → BLOCKED."""
        agents_dir = _agents_dir(tmp_path)
        request = PromptComposerRequest(
            pr_id="0125",
            branch="0125-prompt-composer",
            task_title="Test",
            task_description="Test task.",
            roadmap_path=str(tmp_path / "nonexistent.md"),
            agents_dir=agents_dir,
            repo_root=str(tmp_path),
        )
        result = compose_pr_prompts(request)
        assert result.status == PromptComposerStatus.BLOCKED
        assert REASON_MISSING_ROADMAP in result.reason_codes


# ---------------------------------------------------------------------------
# Missing agents dir
# ---------------------------------------------------------------------------


class TestMissingAgentsDir:
    def test_missing_agents_dir_blocked(self, tmp_path: Path):
        """Missing agents directory → BLOCKED."""
        roadmap_path = _roadmap(tmp_path)
        request = PromptComposerRequest(
            pr_id="0125",
            branch="0125-prompt-composer",
            task_title="Test",
            task_description="Test task.",
            roadmap_path=roadmap_path,
            agents_dir=str(tmp_path / "nonexistent-agents"),
            repo_root=str(tmp_path),
        )
        result = compose_pr_prompts(request)
        assert result.status == PromptComposerStatus.BLOCKED
        assert REASON_MISSING_AGENTS_DIR in result.reason_codes


# ---------------------------------------------------------------------------
# Missing required fields
# ---------------------------------------------------------------------------


class TestMissingRequiredFields:
    def test_missing_pr_id(self, tmp_path: Path):
        """Missing pr_id → FAILED."""
        request = PromptComposerRequest(
            pr_id="",
            branch="test",
            task_title="Test",
            task_description="Test.",
        )
        result = compose_pr_prompts(request)
        assert result.status == PromptComposerStatus.FAILED
        assert REASON_MISSING_PR_ID in result.reason_codes

    def test_missing_branch(self, tmp_path: Path):
        """Missing branch → FAILED."""
        request = PromptComposerRequest(
            pr_id="0125",
            branch="",
            task_title="Test",
            task_description="Test.",
        )
        result = compose_pr_prompts(request)
        assert result.status == PromptComposerStatus.FAILED
        assert REASON_MISSING_BRANCH in result.reason_codes

    def test_missing_task_title(self, tmp_path: Path):
        """Missing task_title → FAILED."""
        request = PromptComposerRequest(
            pr_id="0125",
            branch="test",
            task_title="",
            task_description="Test.",
        )
        result = compose_pr_prompts(request)
        assert result.status == PromptComposerStatus.FAILED
        assert REASON_MISSING_TASK_TITLE in result.reason_codes

    def test_missing_task_description(self, tmp_path: Path):
        """Missing task_description → FAILED."""
        request = PromptComposerRequest(
            pr_id="0125",
            branch="test",
            task_title="Test",
            task_description="",
        )
        result = compose_pr_prompts(request)
        assert result.status == PromptComposerStatus.FAILED
        assert REASON_MISSING_TASK_DESCRIPTION in result.reason_codes


# ---------------------------------------------------------------------------
# Ready for bridge
# ---------------------------------------------------------------------------


class TestReadyForBridge:
    def test_all_packets_ready_for_bridge(self, tmp_path: Path):
        """All packets have ready_for_agent_runner_bridge=True."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        for packet in result.prompt_packets:
            assert packet.ready_for_agent_runner_bridge is True


# ---------------------------------------------------------------------------
# Prompt text is string
# ---------------------------------------------------------------------------


class TestPromptTextIsString:
    def test_prompt_text_is_non_empty_string(self, tmp_path: Path):
        """Each prompt_text is a non-empty string."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        for packet in result.prompt_packets:
            assert isinstance(packet.prompt_text, str)
            assert len(packet.prompt_text) > 0


# ---------------------------------------------------------------------------
# No raw agent output
# ---------------------------------------------------------------------------


class TestNoRawAgentOutput:
    def test_no_raw_agent_output_reference(self, tmp_path: Path):
        """Composer does not reference raw agent output as evidence."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        for packet in result.prompt_packets:
            assert "agent output" not in packet.prompt_text.lower() or "Agent output is not evidence" in packet.prompt_text


# ---------------------------------------------------------------------------
# Deterministic repeats
# ---------------------------------------------------------------------------


class TestDeterministicRepeats:
    def test_same_inputs_identical_output(self, tmp_path: Path):
        """Same inputs → identical output."""
        request = _valid_request(tmp_path)
        result1 = compose_pr_prompts(request)
        result2 = compose_pr_prompts(request)
        assert result1.task_description_hash == result2.task_description_hash
        assert result1.context_hash == result2.context_hash
        assert len(result1.prompt_packets) == len(result2.prompt_packets)
        for p1, p2 in zip(result1.prompt_packets, result2.prompt_packets):
            assert p1.prompt_hash == p2.prompt_hash
            assert p1.prompt_text == p2.prompt_text


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self, tmp_path: Path):
        """Uses tmp_path, not .ariadne/."""
        request = _valid_request(tmp_path)
        result = compose_pr_prompts(request)
        assert result.status == PromptComposerStatus.READY
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import runner.prompt_composer
        doc = runner.prompt_composer.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from runner.prompt_composer import compose_pr_prompts
        source = inspect.getsource(compose_pr_prompts)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"

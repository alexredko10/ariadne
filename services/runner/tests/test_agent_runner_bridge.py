"""Tests for the agent runner bridge."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from runner.agent_runner_bridge import (
    AgentRunnerBridgeRequest,
    AgentRunnerBridgeResult,
    AgentRunnerBridgeArtifact,
    AgentRunnerBridgeStatus,
    run_agent_runner_bridge,
    resolve_agent_config,
    build_agent_runner_execution_request,
    REASON_MISSING_AGENT_CONFIG,
    REASON_UNBOUNDED_AGENT_NAME,
    REASON_MISSING_TASK_PROMPT,
    REASON_DOCKER_BLOCKED,
    REASON_EXECUTION_FAILED,
    REASON_PROOF_CAPTURE_FAILED,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clock_provider() -> str:
    """Deterministic clock provider for tests."""
    return "2026-07-05T18:00:00Z"


def _agents_dir(tmp_path: Path) -> str:
    """Create a temporary agents directory with a test config."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(exist_ok=True)
    config = {
        "model": "test-model",
        "instruction": "You are a test agent.",
        "permissions": {"allow_docker": False},
        "toolsets": ["read", "write"],
    }
    config_file = agents_dir / "test-agent.yml"
    config_file.write_text(
        "model: test-model\ninstruction: You are a test agent.\n"
        "permissions:\n  allow_docker: false\n"
        "toolsets:\n  - read\n  - write\n",
        encoding="utf-8",
    )
    return str(agents_dir)


# ---------------------------------------------------------------------------
# Success — blocked (allow_docker=False)
# ---------------------------------------------------------------------------


class TestSuccessBlocked:
    def test_blocked_without_docker(self, tmp_path: Path):
        """allow_docker=False → BLOCKED with proof artifact."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
        )
        assert result.status == AgentRunnerBridgeStatus.BLOCKED
        assert REASON_DOCKER_BLOCKED in result.reason_codes
        assert result.agent_name == "test-agent"
        assert result.task_prompt_hash is not None
        assert result.agent_config_path is not None
        assert result.agent_config_hash is not None
        assert result.docker_adapter_status == "blocked"
        assert result.captured_artifact is not None
        assert result.captured_artifact.has_proof is True
        assert result.captured_artifact.proof_source == "runtime-captured"
        assert result.started_at == "2026-07-05T18:00:00Z"
        assert result.finished_at == "2026-07-05T18:00:00Z"


# ---------------------------------------------------------------------------
# Missing agent config
# ---------------------------------------------------------------------------


class TestMissingAgentConfig:
    def test_missing_config(self, tmp_path: Path):
        """Unknown agent_name → FAILED with missing_agent_config."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="nonexistent-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        assert result.status == AgentRunnerBridgeStatus.FAILED
        assert REASON_MISSING_AGENT_CONFIG in result.reason_codes


# ---------------------------------------------------------------------------
# Path traversal
# ---------------------------------------------------------------------------


class TestPathTraversal:
    def test_path_traversal_rejected(self, tmp_path: Path):
        """Path traversal agent_name → FAILED with unbounded_agent_name."""
        result = run_agent_runner_bridge(
            agent_name="../../etc/passwd",
            task_prompt="Run a test task.",
            agents_dir=str(tmp_path / "agents"),
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        assert result.status == AgentRunnerBridgeStatus.FAILED
        assert REASON_UNBOUNDED_AGENT_NAME in result.reason_codes


# ---------------------------------------------------------------------------
# Invalid agent name
# ---------------------------------------------------------------------------


class TestInvalidAgentName:
    def test_invalid_agent_name(self, tmp_path: Path):
        """Invalid agent_name → FAILED with unbounded_agent_name."""
        result = run_agent_runner_bridge(
            agent_name="agent name with spaces",
            task_prompt="Run a test task.",
            agents_dir=str(tmp_path / "agents"),
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        assert result.status == AgentRunnerBridgeStatus.FAILED
        assert REASON_UNBOUNDED_AGENT_NAME in result.reason_codes


# ---------------------------------------------------------------------------
# Empty task prompt
# ---------------------------------------------------------------------------


class TestEmptyTaskPrompt:
    def test_empty_prompt(self, tmp_path: Path):
        """Empty task prompt → FAILED with missing_task_prompt."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        assert result.status == AgentRunnerBridgeStatus.FAILED
        assert REASON_MISSING_TASK_PROMPT in result.reason_codes


# ---------------------------------------------------------------------------
# Task prompt hash
# ---------------------------------------------------------------------------


class TestTaskPromptHash:
    def test_task_prompt_hash_deterministic(self, tmp_path: Path):
        """Same prompt → same hash."""
        agents_dir = _agents_dir(tmp_path)
        result1 = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        result2 = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        assert result1.task_prompt_hash == result2.task_prompt_hash

    def test_different_prompt_different_hash(self, tmp_path: Path):
        """Different prompts → different hashes."""
        agents_dir = _agents_dir(tmp_path)
        result1 = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Task one.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        result2 = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Task two.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        assert result1.task_prompt_hash != result2.task_prompt_hash


# ---------------------------------------------------------------------------
# Agent config hash
# ---------------------------------------------------------------------------


class TestAgentConfigHash:
    def test_agent_config_hash_deterministic(self, tmp_path: Path):
        """Same config → same hash."""
        agents_dir = _agents_dir(tmp_path)
        result1 = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        result2 = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        assert result1.agent_config_hash == result2.agent_config_hash


# ---------------------------------------------------------------------------
# Captured artifact
# ---------------------------------------------------------------------------


class TestCapturedArtifact:
    def test_captured_artifact_has_runtime_fields(self, tmp_path: Path):
        """Captured artifact contains runtime-captured fields."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        assert result.captured_artifact is not None
        assert result.captured_artifact.artifact_ref is not None
        assert result.captured_artifact.proof_capture_path is not None
        assert result.captured_artifact.proof_capture_ref is not None
        assert result.captured_artifact.has_proof is True
        assert result.captured_artifact.proof_source == "runtime-captured"

    def test_proof_file_written(self, tmp_path: Path):
        """Proof capture file is written to output_dir."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        assert result.captured_artifact is not None
        assert result.captured_artifact.proof_capture_path is not None
        proof_file = tmp_path / result.captured_artifact.proof_capture_path
        assert proof_file.exists()
        data = json.loads(proof_file.read_text(encoding="utf-8"))
        assert data["runtime_capture_kind"] == "agent_runner_bridge"
        assert "agent_name" in data["payload"]
        assert "task_prompt_hash" in data["payload"]
        assert "agent_config_hash" in data["payload"]
        assert "adapter_status" in data["payload"]


# ---------------------------------------------------------------------------
# Proof source
# ---------------------------------------------------------------------------


class TestProofSource:
    def test_proof_source_is_runtime_captured(self, tmp_path: Path):
        """proof_source == 'runtime-captured'."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        assert result.captured_artifact is not None
        assert result.captured_artifact.proof_source == "runtime-captured"


# ---------------------------------------------------------------------------
# No direct Docker
# ---------------------------------------------------------------------------


class TestNoDirectDocker:
    def test_no_docker_in_bridge_code(self):
        """Bridge code does not import or call Docker directly."""
        import inspect
        from runner.agent_runner_bridge import run_agent_runner_bridge
        source = inspect.getsource(run_agent_runner_bridge)
        # The bridge uses run_local_execution_harness which uses
        # dispatch_execution which uses docker_agent_adapter.
        # The bridge itself should not import docker directly.
        assert "import docker" not in source
        assert "subprocess.run" not in source
        assert "docker compose" not in source


# ---------------------------------------------------------------------------
# No git mutation
# ---------------------------------------------------------------------------


class TestNoGitMutation:
    def test_no_git_in_bridge_code(self):
        """Bridge code does not call git commands."""
        import inspect
        from runner.agent_runner_bridge import run_agent_runner_bridge
        source = inspect.getsource(run_agent_runner_bridge)
        assert "git add" not in source
        assert "git commit" not in source
        assert "git push" not in source
        assert "git checkout" not in source
        assert "git switch" not in source
        assert "git merge" not in source
        assert "git rebase" not in source
        assert "git reset" not in source
        assert "git clean" not in source
        assert "git tag" not in source
        assert "gh pr create" not in source
        assert "gh release" not in source


# ---------------------------------------------------------------------------
# Hidden reasoning rejected
# ---------------------------------------------------------------------------


class TestHiddenReasoningRejected:
    def test_hidden_reasoning_rejected(self, tmp_path: Path):
        """Hidden reasoning in task prompt → FAILED."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Some text <cot> hidden",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        assert result.status == AgentRunnerBridgeStatus.FAILED
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in result.reason_codes


# ---------------------------------------------------------------------------
# Deterministic refs
# ---------------------------------------------------------------------------


class TestDeterministicRefs:
    def test_same_inputs_same_hashes(self, tmp_path: Path):
        """Same inputs → same hashes and refs."""
        agents_dir = _agents_dir(tmp_path)
        result1 = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
        )
        result2 = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
        )
        assert result1.task_prompt_hash == result2.task_prompt_hash
        assert result1.agent_config_hash == result2.agent_config_hash
        assert result1.captured_artifact is not None
        assert result2.captured_artifact is not None
        assert result1.captured_artifact.artifact_ref == result2.captured_artifact.artifact_ref


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self, tmp_path: Path):
        """Uses tmp_path, not .ariadne/."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
        )
        assert result.status == AgentRunnerBridgeStatus.BLOCKED
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# Resolve agent config
# ---------------------------------------------------------------------------


class TestResolveAgentConfig:
    def test_resolve_valid_config(self, tmp_path: Path):
        """Valid agent config → returns path, content, hash."""
        agents_dir = _agents_dir(tmp_path)
        config_path, config_content, config_hash = resolve_agent_config(
            "test-agent", agents_dir
        )
        assert config_path is not None
        assert config_content is not None
        assert config_hash is not None
        assert len(config_hash) == 16

    def test_resolve_missing_config(self, tmp_path: Path):
        """Missing config → ValueError."""
        agents_dir = _agents_dir(tmp_path)
        import pytest
        with pytest.raises(ValueError, match="Agent config not found"):
            resolve_agent_config("nonexistent", agents_dir)

    def test_resolve_invalid_name(self, tmp_path: Path):
        """Invalid name → ValueError."""
        import pytest
        with pytest.raises(ValueError, match="Invalid agent name"):
            resolve_agent_config("../../etc/passwd", str(tmp_path / "agents"))


# ---------------------------------------------------------------------------
# Build execution request
# ---------------------------------------------------------------------------


class TestBuildExecutionRequest:
    def test_build_request_shape(self, tmp_path: Path):
        """Execution request has expected shape."""
        agents_dir = _agents_dir(tmp_path)
        config_path, config_content, config_hash = resolve_agent_config(
            "test-agent", agents_dir
        )
        request = build_agent_runner_execution_request(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            config_content=config_content,
            allow_docker=False,
        )
        assert "execution_request_id" in request
        assert "run_id" in request
        assert "requested_adapter" in request
        assert "execution_mode" in request
        assert "allow_docker" in request
        assert "inputs" in request
        assert request["inputs"]["task_goal"] == "Run a test task."
        assert request["inputs"]["agent_name"] == "test-agent"
        # Always uses docker adapter
        assert request["requested_adapter"] == "docker"

    def test_build_request_with_docker(self, tmp_path: Path):
        """allow_docker=True → execution_mode is execute."""
        agents_dir = _agents_dir(tmp_path)
        config_path, config_content, config_hash = resolve_agent_config(
            "test-agent", agents_dir
        )
        request = build_agent_runner_execution_request(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            config_content=config_content,
            allow_docker=True,
        )
        assert request["requested_adapter"] == "docker"
        assert request["execution_mode"] == "execute"
        assert request["allow_docker"] is True


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import runner.agent_runner_bridge
        doc = runner.agent_runner_bridge.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# Non-mutating prompt allowed (PR 0131C)
# ---------------------------------------------------------------------------


class TestNonMutatingPromptAllowed:
    """Prompt text containing git mutation references is allowed."""

    def test_git_mutation_in_prompt_not_blocked(self, tmp_path: Path):
        """Git command text in prompt no longer triggers git_mutation_not_allowed."""
        agents_dir = _agents_dir(tmp_path)
        prompt = (
            "Implement a feature.\n"
            "Forbidden commands:\n"
            "- git commit\n"
            "- git push\n"
            "- pip install\n"
            "- subprocess.run\n"
        )
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt=prompt,
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
        )
        # Should not be FAILED — should proceed to Docker-blocked (BLOCKED)
        assert result.status == AgentRunnerBridgeStatus.BLOCKED
        assert REASON_DOCKER_BLOCKED in result.reason_codes
        # Should NOT contain git_mutation_not_allowed or hidden_reasoning_not_allowed
        for rc in result.reason_codes:
            assert "git_mutation" not in rc
            assert "hidden_reasoning" not in rc
            assert "action" not in rc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from runner.agent_runner_bridge import run_agent_runner_bridge
        source = inspect.getsource(run_agent_runner_bridge)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"

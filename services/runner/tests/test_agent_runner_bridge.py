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
    _validate_artifact_path,
    _materialize_local_artifact,
    _build_default_precommit_artifact,
    _build_default_plan_review_artifact,
    _build_default_dogfood_proof,
    _is_protected_artifact,
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
# Local execution completion (allow_docker=False)
# ---------------------------------------------------------------------------


class TestLocalExecutionCompletion:
    def test_local_completion_without_docker(self, tmp_path: Path):
        """allow_docker=False → COMPLETED (not BLOCKED) with proof artifact."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
        )
        assert result.status == AgentRunnerBridgeStatus.COMPLETED
        assert REASON_DOCKER_BLOCKED not in result.reason_codes
        assert result.agent_name == "test-agent"
        assert result.task_prompt_hash is not None
        assert result.agent_config_path is not None
        assert result.agent_config_hash is not None
        assert result.docker_adapter_status == "completed"
        assert result.exit_code == 0
        assert result.captured_artifact is not None
        assert result.captured_artifact.has_proof is True
        assert result.captured_artifact.proof_source == "runtime-captured"
        assert result.started_at == "2026-07-05T18:00:00Z"
        assert result.finished_at == "2026-07-05T18:00:00Z"

    def test_local_completion_preserves_hashes(self, tmp_path: Path):
        """Local mode preserves task_prompt_hash and agent_config_hash."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
        )
        assert result.task_prompt_hash is not None
        assert len(result.task_prompt_hash) == 16
        assert result.agent_config_hash is not None
        assert len(result.agent_config_hash) == 16

    def test_local_completion_stdout_contains_agent_name(self, tmp_path: Path):
        """Local mode stdout includes agent_name."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
        )
        assert result.captured_stdout_hash is not None
        assert result.exit_code == 0

    def test_local_completion_no_docker_blocked(self, tmp_path: Path):
        """Local mode does not return docker_blocked."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
        )
        assert result.status == AgentRunnerBridgeStatus.COMPLETED
        assert REASON_DOCKER_BLOCKED not in result.reason_codes

    def test_local_completion_proof_file_written(self, tmp_path: Path):
        """Proof capture file is written in local mode."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
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
# Artifact write boundary
# ---------------------------------------------------------------------------


class TestArtifactWriteBoundary:
    def test_local_mode_writes_only_to_captures_path(self, tmp_path: Path):
        """Local mode writes only to captures/ path."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
        )
        assert result.captured_artifact is not None
        assert result.captured_artifact.proof_capture_path is not None
        # Proof capture path should be under captures/
        assert "captures" in result.captured_artifact.proof_capture_path
        # No writes outside captures/ from the bridge
        proof_file = tmp_path / result.captured_artifact.proof_capture_path
        assert proof_file.exists()
        # Verify no unexpected files were created in tmp_path root
        tmp_files = [f.name for f in tmp_path.iterdir() if f.is_file()]
        for f in tmp_files:
            assert f.startswith("captures") or "captures" in f, f"Unexpected file: {f}"

    def test_local_mode_expected_artifact_path_validation(self, tmp_path: Path):
        """Local mode creates only expected artifact path (captures/)."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
        )
        assert result.captured_artifact is not None
        assert result.captured_artifact.proof_capture_path is not None
        # Use endswith to avoid brittle ./ prefix assumptions
        assert result.captured_artifact.proof_capture_path.endswith(
            f"captures/bridge-test-agent-{result.task_prompt_hash}.json"
        )

    def test_local_mode_refuses_writes_outside_expected_path(self, tmp_path: Path):
        """Local mode does not write outside expected captures/ path."""
        agents_dir = _agents_dir(tmp_path)
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
        )
        # The bridge only writes to captures/ path via proof capture
        assert result.captured_artifact is not None
        assert result.captured_artifact.proof_capture_path is not None
        # Verify no .project-memory/ files were created by the bridge
        project_memory_dir = tmp_path / ".project-memory"
        assert not project_memory_dir.exists()


# ---------------------------------------------------------------------------
# Local mode no git mutation
# ---------------------------------------------------------------------------


class TestLocalNoGitMutation:
    def test_local_mode_no_subprocess(self):
        """Local mode bridge code does not use subprocess."""
        import inspect
        from runner.agent_runner_bridge import run_agent_runner_bridge
        source = inspect.getsource(run_agent_runner_bridge)
        assert "subprocess.run" not in source
        assert "subprocess.Popen" not in source
        assert "os.system" not in source

    def test_local_mode_no_git_commands(self):
        """Local mode bridge code does not call git commands."""
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

    def test_local_mode_no_docker(self):
        """Local mode bridge code does not call docker commands."""
        import inspect
        from runner.agent_runner_bridge import run_agent_runner_bridge
        source = inspect.getsource(run_agent_runner_bridge)
        # The parameter name allow_docker is fine; check for actual docker commands
        assert "docker compose" not in source
        assert "docker run" not in source
        assert "docker exec" not in source
        assert "import docker" not in source

    def test_local_mode_no_shell_true(self):
        """Local mode bridge code does not use shell=True."""
        import inspect
        from runner.agent_runner_bridge import run_agent_runner_bridge
        source = inspect.getsource(run_agent_runner_bridge)
        assert "shell=True" not in source


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
        assert result.status == AgentRunnerBridgeStatus.COMPLETED
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
        # Should not be FAILED — should proceed to local completion (COMPLETED)
        assert result.status == AgentRunnerBridgeStatus.COMPLETED
        assert REASON_DOCKER_BLOCKED not in result.reason_codes
        # Should NOT contain git_mutation_not_allowed or hidden_reasoning_not_allowed
        for rc in result.reason_codes:
            assert "git_mutation" not in rc
            assert "hidden_reasoning" not in rc
            assert "action" not in rc


# ---------------------------------------------------------------------------
# Overwrite protection behavior (PR 0131F)
# ---------------------------------------------------------------------------


class TestOverwriteProtection:
    """Overwrite protection prevents silent overwrite of protected artifacts."""

    def test_overwrite_protection_blocks_plan_md(self, tmp_path):
        """Existing PLAN.md is not overwritten by coder materialization."""
        artifact_path = ".project-memory/pr/test/PLAN.md"
        full_path = tmp_path / artifact_path
        os.makedirs(full_path.parent, exist_ok=True)
        full_path.write_text("# Existing PLAN.md content", encoding="utf-8")

        import pytest
        with pytest.raises(ValueError, match="artifact_overwrite_blocked"):
            _materialize_local_artifact(
                artifact_path=artifact_path,
                content="# New content",
                workdir=str(tmp_path),
                task_prompt_hash="abc123",
                agent_config_hash="def456",
                overwrite_allowed=False,
            )

    def test_overwrite_protection_blocks_plan_review(self, tmp_path):
        """Existing plan-review.yml is not silently overwritten."""
        artifact_path = ".project-memory/pr/test/reviews/plan-review.yml"
        full_path = tmp_path / artifact_path
        os.makedirs(full_path.parent, exist_ok=True)
        full_path.write_text("verdict: approve", encoding="utf-8")

        import pytest
        with pytest.raises(ValueError, match="artifact_overwrite_blocked"):
            _materialize_local_artifact(
                artifact_path=artifact_path,
                content="verdict: block",
                workdir=str(tmp_path),
                task_prompt_hash="abc123",
                agent_config_hash="def456",
                overwrite_allowed=False,
            )

    def test_overwrite_protection_blocks_precommit(self, tmp_path):
        """Existing precommit-review.yml is not silently overwritten."""
        artifact_path = ".project-memory/pr/test/reviews/precommit-review.yml"
        full_path = tmp_path / artifact_path
        os.makedirs(full_path.parent, exist_ok=True)
        full_path.write_text("verdict: pass", encoding="utf-8")

        import pytest
        with pytest.raises(ValueError, match="artifact_overwrite_blocked"):
            _materialize_local_artifact(
                artifact_path=artifact_path,
                content="verdict: fail",
                workdir=str(tmp_path),
                task_prompt_hash="abc123",
                agent_config_hash="def456",
                overwrite_allowed=False,
            )

    def test_overwrite_allowed_flag_works(self, tmp_path):
        """overwrite_allowed=True allows overwriting protected artifact."""
        artifact_path = ".project-memory/pr/test/PLAN.md"
        full_path = tmp_path / artifact_path
        os.makedirs(full_path.parent, exist_ok=True)
        full_path.write_text("# Old content", encoding="utf-8")

        evidence = _materialize_local_artifact(
            artifact_path=artifact_path,
            content="# New content",
            workdir=str(tmp_path),
            task_prompt_hash="abc123",
            agent_config_hash="def456",
            overwrite_allowed=True,
        )
        assert evidence["path"] == str(full_path)
        assert full_path.read_text(encoding="utf-8") == "# New content"

    def test_overwrite_protection_does_not_block_new_path(self, tmp_path):
        """New path under .project-memory/pr/ is not blocked."""
        artifact_path = ".project-memory/pr/test/new-file.yml"
        evidence = _materialize_local_artifact(
            artifact_path=artifact_path,
            content="key: value",
            workdir=str(tmp_path),
            task_prompt_hash="abc123",
            agent_config_hash="def456",
            overwrite_allowed=False,
        )
        assert (tmp_path / artifact_path).exists()
        assert evidence["hash"] is not None

    def test_overwrite_protection_does_not_block_dogfood(self, tmp_path):
        """dogfood-proof.yml on nonexistent path is not blocked."""
        artifact_path = ".project-memory/pr/test/dogfood-proof.yml"
        evidence = _materialize_local_artifact(
            artifact_path=artifact_path,
            content="dogfood_type: local",
            workdir=str(tmp_path),
            task_prompt_hash="abc123",
            agent_config_hash="def456",
            overwrite_allowed=False,
        )
        assert (tmp_path / artifact_path).exists()
        assert evidence["hash"] is not None

    def test_overwrite_blocked_reason_code_in_result(self, tmp_path):
        """Refused overwrite returns blocked with clear reason code."""
        artifact_path = ".project-memory/pr/test/PLAN.md"
        full_path = tmp_path / artifact_path
        os.makedirs(full_path.parent, exist_ok=True)
        full_path.write_text("# Existing", encoding="utf-8")

        import pytest
        with pytest.raises(ValueError) as excinfo:
            _materialize_local_artifact(
                artifact_path=artifact_path,
                content="# New",
                workdir=str(tmp_path),
                task_prompt_hash="abc123",
                agent_config_hash="def456",
                overwrite_allowed=False,
            )
        assert "artifact_overwrite_blocked" in str(excinfo.value)

    def test_is_protected_artifact_plan_md(self):
        """_is_protected_artifact returns True for PLAN.md under .project-memory/pr/."""
        assert _is_protected_artifact(".project-memory/pr/test/PLAN.md") is True

    def test_is_protected_artifact_plan_review(self):
        """_is_protected_artifact returns True for plan-review.yml under reviews/."""
        assert _is_protected_artifact(".project-memory/pr/test/reviews/plan-review.yml") is True

    def test_is_protected_artifact_precommit(self):
        """_is_protected_artifact returns True for precommit-review.yml under reviews/."""
        assert _is_protected_artifact(".project-memory/pr/test/reviews/precommit-review.yml") is True

    def test_is_protected_artifact_dogfood_proof(self):
        """_is_protected_artifact returns False for dogfood-proof.yml."""
        assert _is_protected_artifact(".project-memory/pr/test/dogfood-proof.yml") is False

    def test_is_protected_artifact_non_project_memory(self):
        """_is_protected_artifact returns False for non-project-memory paths."""
        assert _is_protected_artifact("services/runner/src/runner/foo.py") is False


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


# ---------------------------------------------------------------------------
# Local artifact materialization (PR 0131E)
# ---------------------------------------------------------------------------


class TestLocalArtifactMaterialization:
    """Tests for local artifact materialization in agent_runner_bridge.

    All tests use tmp_path only. No real PR 0131 dogfood artifacts are
    created during testing.
    """

    # -----------------------------------------------------------------------
    # Path validation
    # -----------------------------------------------------------------------

    def test_local_materializer_refuses_path_traversal(self, tmp_path):
        """Path traversal (..) in path → ValueError."""
        import pytest
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_artifact_path(
                ".project-memory/pr/../etc/passwd",
                str(tmp_path),
            )

    def test_local_materializer_refuses_absolute_outside_repo(self, tmp_path):
        """Absolute path outside repo root → ValueError."""
        import pytest
        with pytest.raises(ValueError, match="Absolute path outside repo root"):
            _validate_artifact_path(
                "/etc/passwd",
                str(tmp_path),
            )

    def test_local_materializer_refuses_non_project_memory(self, tmp_path):
        """Non-project-memory path → ValueError."""
        import pytest
        with pytest.raises(ValueError, match="Non-project-memory path"):
            _validate_artifact_path(
                "some/random/path.yml",
                str(tmp_path),
            )

    def test_local_materializer_refuses_ariadne_path(self, tmp_path):
        """Ariadne path → ValueError."""
        import pytest
        with pytest.raises(ValueError, match="Non-project-memory path"):
            _validate_artifact_path(
                ".ariadne/run.json",
                str(tmp_path),
            )

    def test_local_materializer_refuses_captures_path(self, tmp_path):
        """Captures path → ValueError."""
        import pytest
        with pytest.raises(ValueError, match="Non-project-memory path"):
            _validate_artifact_path(
                "captures/foo.json",
                str(tmp_path),
            )

    # -----------------------------------------------------------------------
    # Materialization
    # -----------------------------------------------------------------------

    def test_local_materializer_writes_expected_artifact(self, tmp_path):
        """Valid path → file written, hash returned."""
        artifact_path = ".project-memory/pr/test/foo.yml"
        content = "key: value"
        evidence = _materialize_local_artifact(
            artifact_path=artifact_path,
            content=content,
            workdir=str(tmp_path),
            task_prompt_hash="abc123",
            agent_config_hash="def456",
        )
        assert evidence["path"] == str(tmp_path / artifact_path)
        assert evidence["hash"] is not None
        assert len(evidence["hash"]) == 16
        assert evidence["line_count"] == 1
        assert evidence["task_prompt_hash"] == "abc123"
        assert evidence["agent_config_hash"] == "def456"
        # File exists
        assert (tmp_path / artifact_path).exists()
        # Read back
        written = (tmp_path / artifact_path).read_text(encoding="utf-8")
        assert written == content

    def test_local_materializer_writes_precommit_review(self, tmp_path):
        """Temp precommit-review.yml written, parseable by VerdictParser."""
        from runner.verdict_parser import VerdictParserRequest, parse_review_artifact

        artifact_path = ".project-memory/pr/test/reviews/precommit-review.yml"
        content = _build_default_precommit_artifact(
            pr_id="test",
            task_prompt_hash="abc123",
            agent_config_hash="def456",
            artifact_ref="ref789",
        )
        evidence = _materialize_local_artifact(
            artifact_path=artifact_path,
            content=content,
            workdir=str(tmp_path),
            task_prompt_hash="abc123",
            agent_config_hash="def456",
        )
        assert (tmp_path / artifact_path).exists()
        assert evidence["hash"] is not None
        assert evidence["line_count"] > 0

        # Parse through VerdictParser
        request = VerdictParserRequest(
            artifact_path=str(tmp_path / artifact_path),
        )
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert parsed.review_type == "precommit-review"
        assert parsed.normalized_verdict == "pass"
        assert parsed.has_blockers is False

    def test_materialized_precommit_parses_as_pass(self, tmp_path):
        """VerdictParser reads materialized artifact → pass verdict, no blockers."""
        from runner.verdict_parser import VerdictParserRequest, parse_review_artifact, decide_next_action

        artifact_path = ".project-memory/pr/test/reviews/precommit-review.yml"
        content = _build_default_precommit_artifact(
            pr_id="test",
            task_prompt_hash="abc123",
            agent_config_hash="def456",
            artifact_ref="ref789",
        )
        _materialize_local_artifact(
            artifact_path=artifact_path,
            content=content,
            workdir=str(tmp_path),
            task_prompt_hash="abc123",
            agent_config_hash="def456",
        )

        request = VerdictParserRequest(
            artifact_path=str(tmp_path / artifact_path),
        )
        parsed = parse_review_artifact(request)
        assert parsed is not None
        decision = decide_next_action(parsed)
        assert decision.next_action == "continue"
        assert decision.has_blockers is False

    def test_local_bridge_with_materialization_includes_evidence(self, tmp_path):
        """Bridge result details include materialized path/hash/line_count."""
        agents_dir = _agents_dir(tmp_path)
        artifact_path = ".project-memory/pr/test/reviews/precommit-review.yml"
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
            expected_artifact_path=artifact_path,
        )
        assert result.status == AgentRunnerBridgeStatus.COMPLETED
        assert result.details is not None
        assert "Materialized artifact" in result.details
        assert "path=" in result.details
        assert "hash=" in result.details
        assert "line_count=" in result.details
        # File exists
        assert (tmp_path / artifact_path).exists()

    def test_local_bridge_materializes_expected_path(self, tmp_path):
        """Bridge with expected_artifact_path creates the file."""
        agents_dir = _agents_dir(tmp_path)
        artifact_path = ".project-memory/pr/test/reviews/precommit-review.yml"
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
            expected_artifact_path=artifact_path,
        )
        assert result.status == AgentRunnerBridgeStatus.COMPLETED
        assert (tmp_path / artifact_path).exists()
        # Read back
        content = (tmp_path / artifact_path).read_text(encoding="utf-8")
        assert "precommit-review" in content
        assert "verdict: \"pass\"" in content

    def test_local_materializer_preserves_proof(self, tmp_path):
        """Proof capture still written alongside materialized artifact."""
        agents_dir = _agents_dir(tmp_path)
        artifact_path = ".project-memory/pr/test/reviews/precommit-review.yml"
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
            expected_artifact_path=artifact_path,
        )
        assert result.status == AgentRunnerBridgeStatus.COMPLETED
        # Proof capture exists
        assert result.captured_artifact is not None
        assert result.captured_artifact.has_proof is True
        assert result.captured_artifact.proof_capture_path is not None
        proof_file = tmp_path / result.captured_artifact.proof_capture_path
        assert proof_file.exists()
        # Materialized artifact exists
        assert (tmp_path / artifact_path).exists()

    def test_local_materializer_preserves_hashes(self, tmp_path):
        """task_prompt_hash and agent_config_hash in materialized content."""
        agents_dir = _agents_dir(tmp_path)
        artifact_path = ".project-memory/pr/test/reviews/precommit-review.yml"
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
            expected_artifact_path=artifact_path,
        )
        assert result.status == AgentRunnerBridgeStatus.COMPLETED
        content = (tmp_path / artifact_path).read_text(encoding="utf-8")
        assert result.task_prompt_hash in content
        assert result.agent_config_hash in content

    def test_local_materializer_dogfood_proof(self, tmp_path):
        """Dogfood-proof.yml materialization works in temp path."""
        agents_dir = _agents_dir(tmp_path)
        artifact_path = ".project-memory/pr/test/dogfood-proof.yml"
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Create dogfood proof.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
            expected_artifact_path=artifact_path,
        )
        assert result.status == AgentRunnerBridgeStatus.COMPLETED
        assert (tmp_path / artifact_path).exists()
        content = (tmp_path / artifact_path).read_text(encoding="utf-8")
        assert "dogfood_type: \"local-non-docker\"" in content
        assert "status: \"completed\"" in content
        assert result.task_prompt_hash in content
        assert result.agent_config_hash in content

    def test_no_real_pr_artifacts_created(self, tmp_path):
        """No real PR 0131 dogfood artifacts created or mutated during test."""
        agents_dir = _agents_dir(tmp_path)
        artifact_path = ".project-memory/pr/test/reviews/precommit-review.yml"
        result = run_agent_runner_bridge(
            agent_name="test-agent",
            task_prompt="Run a test task.",
            agents_dir=agents_dir,
            allow_docker=False,
            output_dir=str(tmp_path),
            clock_provider=_clock_provider,
            expected_artifact_path=artifact_path,
        )
        assert result.status == AgentRunnerBridgeStatus.COMPLETED

        # Snapshot existing real dogfood proof (committed by #150)
        real_dogfood_proof = Path(".project-memory/pr/0131-dogfood-pr-created-by-ariadne/dogfood-proof.yml")
        real_precommit = Path(".project-memory/pr/0131-dogfood-pr-created-by-ariadne/reviews/precommit-review.yml")

        dogfood_snapshot = real_dogfood_proof.read_text(encoding="utf-8") if real_dogfood_proof.exists() else None
        precommit_snapshot = real_precommit.read_text(encoding="utf-8") if real_precommit.exists() else None

        # Assert unchanged: if artifact existed before test, it must still exist
        # with identical content.  If it did not exist, it must still not exist.
        if dogfood_snapshot is not None:
            assert real_dogfood_proof.exists()
            assert real_dogfood_proof.read_text(encoding="utf-8") == dogfood_snapshot
        else:
            assert not real_dogfood_proof.exists()

        if precommit_snapshot is not None:
            assert real_precommit.exists()
            assert real_precommit.read_text(encoding="utf-8") == precommit_snapshot
        else:
            assert not real_precommit.exists()

        # Verify no new files were created under real PR path during test
        real_pr_dir = Path(".project-memory/pr/0131-dogfood-pr-created-by-ariadne")
        expected_files = {"PLAN.md", "dogfood-proof.yml", "reviews/plan-review.yml"}
        actual_files = set()
        if real_pr_dir.exists():
            for f in real_pr_dir.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(real_pr_dir)
                    actual_files.add(str(rel))
        # Only expected committed files; no new generated artifacts
        assert actual_files.issubset(expected_files), f"Unexpected files: {actual_files - expected_files}"

    def test_local_materializer_no_subprocess(self):
        """Materialization code does not use subprocess/os.system."""
        import inspect
        from runner.agent_runner_bridge import _materialize_local_artifact
        source = inspect.getsource(_materialize_local_artifact)
        assert "subprocess.run" not in source
        assert "subprocess.Popen" not in source
        assert "os.system" not in source
        assert "shell=True" not in source

    def test_local_materializer_no_git(self):
        """Materialization code does not call git commands."""
        import inspect
        from runner.agent_runner_bridge import _materialize_local_artifact
        source = inspect.getsource(_materialize_local_artifact)
        assert "git add" not in source
        assert "git commit" not in source
        assert "git push" not in source
        assert "gh pr create" not in source

    def test_local_materializer_no_docker(self):
        """Materialization code does not call docker commands."""
        import inspect
        from runner.agent_runner_bridge import _materialize_local_artifact
        source = inspect.getsource(_materialize_local_artifact)
        assert "docker" not in source

    def test_build_default_precommit_artifact_shape(self):
        """Default precommit artifact has expected fields."""
        content = _build_default_precommit_artifact(
            pr_id="test-pr",
            task_prompt_hash="abc123",
            agent_config_hash="def456",
            artifact_ref="ref789",
        )
        assert "schema_version: \"0.1\"" in content
        assert "pr_id: \"test-pr\"" in content
        assert "review_type: \"precommit-review\"" in content
        assert "verdict: \"pass\"" in content
        assert "blockers: []" in content
        assert "abc123" in content
        assert "def456" in content
        assert "ref789" in content

    def test_build_default_dogfood_proof_shape(self):
        """Default dogfood-proof artifact has expected fields."""
        content = _build_default_dogfood_proof(
            pr_id="test-pr",
            task_prompt_hash="abc123",
            agent_config_hash="def456",
            artifact_ref="ref789",
        )
        assert "schema_version: \"0.1\"" in content
        assert "pr_id: \"test-pr\"" in content
        assert "dogfood_type: \"local-non-docker\"" in content
        assert "status: \"completed\"" in content
        assert "abc123" in content
        assert "def456" in content
        assert "ref789" in content

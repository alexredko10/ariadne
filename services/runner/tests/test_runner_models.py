"""Tests for runner typed models."""

import pytest

from services.runner.src.runner.models import (
    CommandSpec,
    NormalizedPatch,
    RunArtifact,
    RunResult,
    RunSpec,
)


class TestCommandSpec:
    def test_holds_argv_and_timeout(self):
        cmd = CommandSpec(argv=("python", "script.py"), cwd="/tmp", timeout_seconds=120)
        assert cmd.argv == ("python", "script.py")
        assert cmd.cwd == "/tmp"
        assert cmd.timeout_seconds == 120

    def test_defaults(self):
        cmd = CommandSpec(argv=("ls",))
        assert cmd.cwd is None
        assert cmd.timeout_seconds == 60

    def test_rejects_empty_argv(self):
        with pytest.raises(ValueError, match="argv must not be empty"):
            CommandSpec(argv=())

    def test_rejects_zero_timeout(self):
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            CommandSpec(argv=("echo",), timeout_seconds=0)

    def test_rejects_negative_timeout(self):
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            CommandSpec(argv=("echo",), timeout_seconds=-1)


class TestRunSpec:
    def test_holds_fields(self):
        cmd = CommandSpec(argv=("ls", "-la"))
        spec = RunSpec(
            run_id="run-1",
            task_id="task-1",
            command=cmd,
            allowed_write_paths=("src/module.py",),
            timeout_seconds=300,
        )
        assert spec.run_id == "run-1"
        assert spec.task_id == "task-1"
        assert spec.command is cmd
        assert spec.allowed_write_paths == ("src/module.py",)
        assert spec.timeout_seconds == 300

    def test_rejects_negative_timeout(self):
        cmd = CommandSpec(argv=("echo",))
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            RunSpec(run_id="r", task_id="t", command=cmd, timeout_seconds=-5)


class TestRunArtifact:
    def test_holds_fields(self):
        result = RunResult(exit_code=0, stdout="ok", stderr="")
        patch = NormalizedPatch(text="diff", touched_paths=("file.py",))
        artifact = RunArtifact(
            run_id="run-1",
            task_id="task-1",
            result=result,
            normalized_patch=patch,
            touched_paths=("file.py",),
            runner_version="0.2.0",
        )
        assert artifact.run_id == "run-1"
        assert artifact.task_id == "task-1"
        assert artifact.result.exit_code == 0
        assert artifact.result.stdout == "ok"
        assert artifact.normalized_patch is patch
        assert artifact.touched_paths == ("file.py",)
        assert artifact.runner_version == "0.2.0"

    def test_default_version(self):
        result = RunResult(exit_code=0, stdout="", stderr="")
        patch = NormalizedPatch(text="", touched_paths=())
        artifact = RunArtifact(
            run_id="r", task_id="t", result=result, normalized_patch=patch
        )
        assert artifact.runner_version == "0.1.0"

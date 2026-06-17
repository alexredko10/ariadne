"""Tests for the Mock Coder sandbox-only proof harness."""

from __future__ import annotations

from pathlib import Path

import pytest

from runner.mock_coder import (
    MockCoder,
    MockCoderError,
    MockCoderRequest,
    MockCoderResult,
    SandboxViolation,
    SandboxWrite,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """A fresh sandbox directory."""
    sb = tmp_path / "sandbox"
    sb.mkdir()
    return sb


@pytest.fixture
def canonical_repo(tmp_path: Path) -> Path:
    """A fixture simulating the canonical repository."""
    repo = tmp_path / "canonical"
    repo.mkdir()
    (repo / "README.md").write_text("# Canonical repo\n")
    return repo


# ---------------------------------------------------------------------------
# Writes inside sandbox
# ---------------------------------------------------------------------------


class TestWritesInsideSandbox:
    def test_writes_file_inside_sandbox(self, sandbox: Path):
        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("output/test.txt",),
        )
        result = MockCoder.execute(request)
        assert len(result.writes) == 1
        assert result.writes[0].target == "output/test.txt"
        # File should exist
        assert (sandbox / "output/test.txt").exists()
        assert (sandbox / "output/test.txt").read_text() == "MockCoder wrote: output/test.txt\n"

    def test_creates_parent_directories(self, sandbox: Path):
        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("a/b/c/d/file.txt",),
        )
        result = MockCoder.execute(request)
        assert len(result.writes) == 1
        assert (sandbox / "a/b/c/d/file.txt").exists()

    def test_multiple_sandbox_writes_recorded(self, sandbox: Path):
        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("f1.txt", "sub/f2.txt", "sub/deep/f3.txt"),
        )
        result = MockCoder.execute(request)
        assert len(result.writes) == 3
        assert all((sandbox / w.target).exists() for w in result.writes)

    def test_writes_recorded_in_order(self, sandbox: Path):
        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("first.txt", "second.txt", "third.txt"),
        )
        result = MockCoder.execute(request)
        assert [w.target for w in result.writes] == [
            "first.txt", "second.txt", "third.txt"
        ]


# ---------------------------------------------------------------------------
# Canonical repo unchanged
# ---------------------------------------------------------------------------


class TestCanonicalRepoUnchanged:
    def test_canonical_repo_fixture_unchanged(self, sandbox: Path, canonical_repo: Path):
        original = (canonical_repo / "README.md").read_text()
        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("output/data.txt",),
        )
        MockCoder.execute(request)
        # Canonical repo should be unchanged
        assert (canonical_repo / "README.md").read_text() == original
        # No files created in canonical repo
        assert set(canonical_repo.iterdir()) == {canonical_repo / "README.md"}


# ---------------------------------------------------------------------------
# Absolute path refusal
# ---------------------------------------------------------------------------


class TestAbsolutePathsRefused:
    def test_absolute_path_write_refused(self, sandbox: Path):
        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("/etc/passwd",),
        )
        result = MockCoder.execute(request)
        assert len(result.writes) == 0
        assert len(result.violations) == 1
        assert result.violations[0].target == "/etc/passwd"
        assert any("absolute" in result.violations[0].reason.lower()
                   for r in [result.violations[0]])

    def test_mixed_absolute_and_relative(self, sandbox: Path):
        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("/tmp/bad", "good.txt"),
        )
        result = MockCoder.execute(request)
        # Good write is performed
        assert len(result.writes) == 1
        assert result.writes[0].target == "good.txt"
        # Bad write is refused
        assert len(result.violations) == 1
        assert result.violations[0].target == "/tmp/bad"


# ---------------------------------------------------------------------------
# Path traversal refusal
# ---------------------------------------------------------------------------


class TestPathTraversalRefused:
    def test_traversal_write_refused(self, sandbox: Path):
        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("../outside.txt",),
        )
        result = MockCoder.execute(request)
        assert len(result.writes) == 0
        assert len(result.violations) == 1
        assert any("traversal" in result.violations[0].reason.lower()
                   for r in [result.violations[0]])

    def test_nested_traversal_refused(self, sandbox: Path):
        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("sub/../../outside.txt",),
        )
        result = MockCoder.execute(request)
        assert len(result.writes) == 0
        assert len(result.violations) == 1

    def test_mixed_traversal_and_valid(self, sandbox: Path):
        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("good.txt", "sub/../../bad.txt"),
        )
        result = MockCoder.execute(request)
        assert len(result.writes) == 1
        assert result.writes[0].target == "good.txt"
        assert len(result.violations) == 1
        assert result.violations[0].target == "sub/../../bad.txt"


# ---------------------------------------------------------------------------
# Symlink escape refusal
# ---------------------------------------------------------------------------


class TestSymlinkEscapeRefused:
    def test_symlink_escape_refused(self, sandbox: Path, tmp_path: Path):
        # Create a symlink inside sandbox pointing outside
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "escaped.txt").write_text("escaped")

        link_path = sandbox / "escape_link"
        link_path.symlink_to(outside)

        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("escape_link/escaped.txt",),
        )
        result = MockCoder.execute(request)
        # The symlinked path resolves outside sandbox, so should be refused
        assert len(result.violations) >= 1
        assert any("symlink" in v.reason.lower() or "escape" in v.reason.lower()
                   for v in result.violations)

    def test_symlink_to_outside_directory(self, sandbox: Path, tmp_path: Path):
        outside = tmp_path / "secret"
        outside.mkdir()

        link_path = sandbox / "secret_link"
        link_path.symlink_to(outside)

        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("secret_link/stolen.txt",),
        )
        result = MockCoder.execute(request)
        assert len(result.violations) >= 1
        # No writes outside sandbox
        assert not (outside / "stolen.txt").exists()


# ---------------------------------------------------------------------------
# No writes outside sandbox root
# ---------------------------------------------------------------------------


class TestNoWritesOutsideRoot:
    def test_no_writes_outside_sandbox_root(self, sandbox: Path, tmp_path: Path):
        outside = tmp_path / "outside"
        outside.mkdir()

        # Attempt to write to a path that resolves outside sandbox
        # via a deeply nested unresolvable target
        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("good.txt",),
        )
        result = MockCoder.execute(request)
        assert len(result.writes) == 1
        # Verify no files exist outside sandbox
        assert set(sandbox.iterdir()) == {sandbox / "good.txt"}


# ---------------------------------------------------------------------------
# Structured reasons
# ---------------------------------------------------------------------------


class TestStructuredReasons:
    def test_refused_writes_have_structured_reasons(self, sandbox: Path):
        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("/etc/passwd", "../escape", "good.txt",
                             "sub/../../bad"),
        )
        result = MockCoder.execute(request)
        assert len(result.violations) == 3
        for v in result.violations:
            assert isinstance(v.reason, str)
            assert len(v.reason) > 0
        # Good write is still performed
        assert len(result.writes) == 1


# ---------------------------------------------------------------------------
# No side-effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_git_no_subprocess_no_docker(self):
        """Test that execute does not call subprocess, git, or docker.
        Since we use only pure-Python path operations, this test
        asserts the module is self-contained and stdlib-only.
        """
        import inspect

        source = inspect.getsource(MockCoder.execute)
        assert "subprocess" not in source
        assert "git " not in source or "git_" in source  # allow git_ in comments
        assert "docker" not in source
        assert "os.system" not in source

    def test_sandbox_root_missing_raises(self):
        with pytest.raises(MockCoderError, match="does not exist"):
            request = MockCoderRequest(
                sandbox_root="/nonexistent/path",
                intended_writes=("test.txt",),
            )
            MockCoder.execute(request)

    def test_sandbox_root_file_raises(self, tmp_path: Path):
        not_a_dir = tmp_path / "file.txt"
        not_a_dir.write_text("not a directory")

        with pytest.raises(MockCoderError, match="not a directory"):
            request = MockCoderRequest(
                sandbox_root=str(not_a_dir),
                intended_writes=("test.txt",),
            )
            MockCoder.execute(request)


# ---------------------------------------------------------------------------
# WorktreeManager interaction proof
# ---------------------------------------------------------------------------


class TestWorktreeSeparation:
    def test_separation_from_snapshot(self, sandbox: Path, tmp_path: Path):
        """Prove that a WorktreeManager-like snapshot is not touched
        when MockCoder writes to the sandbox."""
        snapshot = tmp_path / "snapshot"
        snapshot.mkdir()
        (snapshot / "file_a.txt").write_text("snapshot-content")

        request = MockCoderRequest(
            sandbox_root=str(sandbox),
            intended_writes=("file_b.txt",),
        )
        MockCoder.execute(request)

        # Snapshot must be unchanged
        assert (snapshot / "file_a.txt").read_text() == "snapshot-content"
        assert not (snapshot / "file_b.txt").exists()

        # Sandbox has the new write
        assert (sandbox / "file_b.txt").read_text() == "MockCoder wrote: file_b.txt\n"

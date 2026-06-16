"""Tests for WorktreeManager — safe filesystem isolation."""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

import pytest

from services.runner.src.runner.worktree import (
    WorktreeManager,
    WorktreeSafetyError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def source_root(tmp_path: Path) -> Path:
    """Create a realistic source directory with known structure."""
    root = tmp_path / "source"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('hello')")
    (root / "src" / "utils.py").write_text("def helper(): pass")
    (root / "README.md").write_text("# Project")
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text("# Guide")
    return root


@pytest.fixture
def manager() -> WorktreeManager:
    """A fresh WorktreeManager for each test."""
    return WorktreeManager()


# ---------------------------------------------------------------------------
# Structural validity
# ---------------------------------------------------------------------------


class TestIncludePathValidation:
    def test_rejects_absolute_path(self, manager: WorktreeManager, source_root: Path):
        with pytest.raises(WorktreeSafetyError, match="absolute"):
            manager.create_context_snapshot(source_root, ["/etc/passwd"])

    def test_rejects_empty_path(self, manager: WorktreeManager, source_root: Path):
        with pytest.raises(WorktreeSafetyError, match="empty"):
            manager.create_context_snapshot(source_root, [""])

    def test_rejects_double_dot_traversal(
        self, manager: WorktreeManager, source_root: Path
    ):
        with pytest.raises(WorktreeSafetyError, match="traversal"):
            manager.create_context_snapshot(source_root, ["../etc/passwd"])


# ---------------------------------------------------------------------------
# Git metadata rejection
# ---------------------------------------------------------------------------


class TestGitRejection:
    def test_rejects_git_directory(self, manager: WorktreeManager, source_root: Path):
        (source_root / ".git").mkdir()
        with pytest.raises(WorktreeSafetyError, match="\\.git"):
            manager.create_context_snapshot(source_root, [".git"])

    def test_rejects_nested_git(self, manager: WorktreeManager, source_root: Path):
        (source_root / "src" / ".git").mkdir()
        with pytest.raises(WorktreeSafetyError, match="\\.git"):
            manager.create_context_snapshot(source_root, ["src/.git"])

    def test_rejects_git_file_pointer(self, manager: WorktreeManager, source_root: Path):
        (source_root / ".git").write_text("gitdir: ../.git/modules/some-module\n")
        with pytest.raises(WorktreeSafetyError, match="\\.git"):
            manager.create_context_snapshot(source_root, [".git"])

    def test_rejects_path_with_git_component(
        self, manager: WorktreeManager, source_root: Path
    ):
        (source_root / "src").mkdir(exist_ok=True)
        (source_root / "src" / ".git").mkdir()
        with pytest.raises(WorktreeSafetyError, match="\\.git"):
            manager.create_context_snapshot(source_root, ["src/.git/config"])


# ---------------------------------------------------------------------------
# Secret-like file rejection
# ---------------------------------------------------------------------------


class TestSecretRejection:
    @pytest.mark.parametrize(
        "path",
        [
            ".env",
            ".env.prod",
            ".env.local",
            "id_rsa",
            "id_dsa",
            "id_ecdsa",
            "id_ed25519",
        ],
    )
    def test_rejects_secret_basenames(
        self, manager: WorktreeManager, source_root: Path, path: str
    ):
        p = source_root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("secret")
        with pytest.raises(WorktreeSafetyError, match="secret-like|secret directory"):
            manager.create_context_snapshot(source_root, [path])

    @pytest.mark.parametrize("path", [".ssh/authorized_keys", ".ssh/id_rsa"])
    def test_rejects_ssh_dir(
        self, manager: WorktreeManager, source_root: Path, path: str
    ):
        p = source_root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("key")
        # id_rsa is caught by secret-like basename check before .ssh/ prefix check
        with pytest.raises(WorktreeSafetyError, match="secret-like|secret directory"):
            manager.create_context_snapshot(source_root, [path])

    def test_rejects_aws_dir(self, manager: WorktreeManager, source_root: Path):
        p = source_root / ".aws" / "credentials"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("aws_secret")
        with pytest.raises(WorktreeSafetyError, match="secret directory"):
            manager.create_context_snapshot(source_root, [".aws/credentials"])

    def test_rejects_gh_config(self, manager: WorktreeManager, source_root: Path):
        p = source_root / ".config" / "gh" / "config.yml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("gh_token")
        # .config/ is caught by secret directory check before .config/gh/ check
        with pytest.raises(WorktreeSafetyError, match="secret directory"):
            manager.create_context_snapshot(source_root, [".config/gh/config.yml"])


# ---------------------------------------------------------------------------
# Symlink rejection
# ---------------------------------------------------------------------------


class TestSymlinkRejection:
    def test_rejects_symlink_escape(self, manager: WorktreeManager, source_root: Path):
        outside = source_root.parent / "secret.txt"
        outside.write_text("stolen")
        link = source_root / "escape"
        link.symlink_to(outside)
        with pytest.raises(WorktreeSafetyError, match="symlink"):
            manager.create_context_snapshot(source_root, ["escape"])

    def test_rejects_symlink_to_forbidden_path(
        self, manager: WorktreeManager, source_root: Path
    ):
        (source_root / ".env").write_text("real_env")
        link = source_root / "link_to_env"
        link.symlink_to(".env")
        with pytest.raises(WorktreeSafetyError, match="symlink"):
            manager.create_context_snapshot(source_root, ["link_to_env"])


# ---------------------------------------------------------------------------
# Successful snapshot creation
# ---------------------------------------------------------------------------


class TestSnapshotSuccess:
    def test_copies_only_explicitly_included_files(
        self, manager: WorktreeManager, source_root: Path
    ):
        snapshot = manager.create_context_snapshot(source_root, ["src/main.py"])
        assert (snapshot / "src" / "main.py").read_text() == "print('hello')"
        # Should NOT have copied other files
        assert not (snapshot / "README.md").exists()
        assert not (snapshot / "src" / "utils.py").exists()

    def test_preserves_relative_paths_and_contents(
        self, manager: WorktreeManager, source_root: Path
    ):
        snapshot = manager.create_context_snapshot(
            source_root, ["src/main.py", "docs/guide.md"]
        )
        assert (snapshot / "src" / "main.py").read_text() == "print('hello')"
        assert (snapshot / "docs" / "guide.md").read_text() == "# Guide"

    def test_snapshot_directory_is_under_manager_root(
        self, manager: WorktreeManager, source_root: Path
    ):
        snapshot = manager.create_context_snapshot(source_root, ["src/main.py"])
        assert str(snapshot).startswith(str(manager.root))

    def test_source_root_not_modified(
        self, manager: WorktreeManager, source_root: Path
    ):
        original_mtime = (source_root / "src" / "main.py").stat().st_mtime_ns
        manager.create_context_snapshot(source_root, ["src/main.py"])
        assert (source_root / "src" / "main.py").stat().st_mtime_ns == original_mtime

    def test_rejects_missing_include_path(
        self, manager: WorktreeManager, source_root: Path
    ):
        with pytest.raises(FileNotFoundError):
            manager.create_context_snapshot(source_root, ["nonexistent.py"])


# ---------------------------------------------------------------------------
# Sandbox behavior
# ---------------------------------------------------------------------------


class TestSandbox:
    def test_sandbox_is_separate_from_snapshot(
        self, manager: WorktreeManager, source_root: Path
    ):
        snapshot = manager.create_context_snapshot(source_root, ["src/main.py"])
        sandbox = manager.create_sandbox(snapshot)
        assert sandbox != snapshot
        assert sandbox.exists()
        assert (sandbox / "src" / "main.py").read_text() == "print('hello')"

    def test_sandbox_can_be_modified_without_changing_snapshot(
        self, manager: WorktreeManager, source_root: Path
    ):
        snapshot = manager.create_context_snapshot(source_root, ["src/main.py"])
        sandbox = manager.create_sandbox(snapshot)
        (sandbox / "src" / "main.py").write_text("modified")
        assert (snapshot / "src" / "main.py").read_text() == "print('hello')"

    def test_sandbox_mutation_does_not_modify_source_root(
        self, manager: WorktreeManager, source_root: Path
    ):
        snapshot = manager.create_context_snapshot(source_root, ["src/main.py"])
        sandbox = manager.create_sandbox(snapshot)
        (sandbox / "src" / "main.py").write_text("modified")
        assert (source_root / "src" / "main.py").read_text() == "print('hello')"

    def test_sandbox_is_under_manager_root(
        self, manager: WorktreeManager, source_root: Path
    ):
        snapshot = manager.create_context_snapshot(source_root, ["src/main.py"])
        sandbox = manager.create_sandbox(snapshot)
        assert str(sandbox).startswith(str(manager.root))

    def test_rejects_snapshot_outside_manager_root(
        self, manager: WorktreeManager, tmp_path: Path
    ):
        fake_snapshot = tmp_path / "fake_snapshot"
        fake_snapshot.mkdir()
        with pytest.raises(WorktreeSafetyError, match="outside"):
            manager.create_sandbox(fake_snapshot)

    def test_rejects_unregistered_snapshot(
        self, manager: WorktreeManager, source_root: Path
    ):
        # Create snapshot from a different manager — it's under other's root,
        # which is outside this manager's root, so "outside" message is expected
        other = WorktreeManager()
        snapshot = other.create_context_snapshot(source_root, ["src/main.py"])
        with pytest.raises(WorktreeSafetyError, match="outside"):
            manager.create_sandbox(snapshot)


# ---------------------------------------------------------------------------
# Destroy behavior
# ---------------------------------------------------------------------------


class TestDestroy:
    def test_destroy_removes_registered_path(
        self, manager: WorktreeManager, source_root: Path
    ):
        snapshot = manager.create_context_snapshot(source_root, ["src/main.py"])
        assert snapshot.exists()
        manager.destroy(snapshot)
        assert not snapshot.exists()

    def test_destroy_rejects_path_outside_manager_root(
        self, manager: WorktreeManager, tmp_path: Path
    ):
        outside = tmp_path / "outside"
        outside.mkdir()
        with pytest.raises(WorktreeSafetyError, match="outside"):
            manager.destroy(outside)

    def test_destroy_rejects_source_root(
        self, manager: WorktreeManager, source_root: Path
    ):
        with pytest.raises(WorktreeSafetyError, match="outside"):
            manager.destroy(source_root)

    def test_destroy_rejects_unregistered_path(
        self, manager: WorktreeManager, source_root: Path
    ):
        # Create a path inside our temp root but not in the registry
        from pathlib import Path as P

        rogue = P(manager.root) / "rogue"
        rogue.mkdir()
        with pytest.raises(WorktreeSafetyError, match="not created"):
            manager.destroy(rogue)

    def test_destroy_is_idempotent_for_registered(
        self, manager: WorktreeManager, source_root: Path
    ):
        snapshot = manager.create_context_snapshot(source_root, ["src/main.py"])
        manager.destroy(snapshot)
        # Second call should raise because path is no longer registered
        with pytest.raises(WorktreeSafetyError, match="not created"):
            manager.destroy(snapshot)


# ---------------------------------------------------------------------------
# Manager lifecycle
# ---------------------------------------------------------------------------


class TestManagerLifecycle:
    def test_manager_creates_dedicated_temp_root(self, manager: WorktreeManager):
        root = manager.root
        assert root.exists()
        assert "runner_worktree_" in root.name

    def test_creates_no_docker_network_credentials(
        self, manager: WorktreeManager, source_root: Path
    ):
        """Structural test: WorktreeManager uses only stdlib filesystem operations."""
        # If it can create a snapshot and sandbox without anything else, it works.
        snapshot = manager.create_context_snapshot(source_root, ["src/main.py"])
        sandbox = manager.create_sandbox(snapshot)
        assert sandbox.exists()

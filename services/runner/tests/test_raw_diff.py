"""Tests for raw_diff — deterministic unified diff between snapshot and sandbox."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from services.runner.src.runner.diff import RawDiffError, raw_diff


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def snap(tmp_path: Path) -> Path:
    """Create a snapshot directory with known content."""
    d = tmp_path / "snap"
    d.mkdir()
    (d / "app.py").write_text("old\ncontent\n")
    (d / "README.md").write_text("# Project\n")
    (d / "src").mkdir()
    (d / "src" / "main.py").write_text("print('hello')\n")
    (d / "src" / "utils.py").write_text("def helper(): pass\n")
    return d


@pytest.fixture
def sand(snap: Path, tmp_path: Path) -> Path:
    """Create a sandbox by copying snapshot and applying changes."""
    import shutil

    d = tmp_path / "sand"
    shutil.copytree(snap, d)
    # Modify a file
    (d / "app.py").write_text("new\ncontent\n")
    # Add a file
    (d / "new_file.py").write_text("print('new')\n")
    # Delete a file
    (d / "src" / "utils.py").unlink()
    return d


# ---------------------------------------------------------------------------
# Basic diff functionality
# ---------------------------------------------------------------------------


class TestBasicDiff:
    def test_no_changes_returns_empty_string(self, snap: Path, tmp_path: Path):
        import shutil

        same = tmp_path / "same"
        shutil.copytree(snap, same)
        assert raw_diff(snap, same) == ""

    def test_modified_file_returns_diff(self, snap: Path, sand: Path):
        result = raw_diff(snap, sand)
        assert "--- a/app.py" in result
        assert "+++ b/app.py" in result
        assert "-old" in result
        assert "+new" in result

    def test_added_file_uses_devnull(self, snap: Path, sand: Path):
        result = raw_diff(snap, sand)
        assert "/dev/null" in result
        assert "+++ b/new_file.py" in result
        assert "+print('new')" in result

    def test_deleted_file_uses_devnull(self, snap: Path, sand: Path):
        result = raw_diff(snap, sand)
        assert "--- a/src/utils.py" in result
        assert "/dev/null" in result
        assert "-def helper(): pass" in result

    def test_multiple_changes_in_one_diff(self, snap: Path, sand: Path):
        result = raw_diff(snap, sand)
        # Three hunks: modified app.py, added new_file.py, deleted utils.py
        assert result.count("--- ") == 3


# ---------------------------------------------------------------------------
# Nested paths and ordering
# ---------------------------------------------------------------------------


class TestNestedPathsAndOrdering:
    def test_nested_relative_paths_are_stable(self, snap: Path, sand: Path):
        result = raw_diff(snap, sand)
        # Path separators must be POSIX-style
        assert "a/src/utils.py" in result
        # Deleted file uses /dev/null on the new side
        assert "/dev/null" in result
        assert "\\" not in result

    def test_sorted_file_ordering(self, snap: Path, sand: Path):
        result = raw_diff(snap, sand)
        # Expect app.py, new_file.py, src/utils.py in that order
        idx_app = result.index("--- a/app.py")
        idx_new = result.index("+++ b/new_file.py")
        idx_utils = result.index("--- a/src/utils.py")
        assert idx_app < idx_new < idx_utils


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_snapshot_must_exist(self, tmp_path: Path):
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            raw_diff(nonexistent, tmp_path)

    def test_sandbox_must_exist(self, tmp_path: Path):
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            raw_diff(tmp_path, nonexistent)

    def test_snapshot_must_be_directory(self, tmp_path: Path):
        f = tmp_path / "file.txt"
        f.write_text("hello")
        with pytest.raises(RawDiffError, match="not a directory"):
            raw_diff(f, tmp_path)

    def test_sandbox_must_be_directory(self, tmp_path: Path):
        f = tmp_path / "file.txt"
        f.write_text("hello")
        with pytest.raises(RawDiffError, match="not a directory"):
            raw_diff(tmp_path, f)

    def test_same_path_rejected(self, tmp_path: Path):
        with pytest.raises(RawDiffError, match="must differ"):
            raw_diff(tmp_path, tmp_path)


# ---------------------------------------------------------------------------
# Git metadata rejection
# ---------------------------------------------------------------------------


class TestGitRejection:
    def test_rejects_git_directory(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_git"
        sand.mkdir()
        (sand / ".git").mkdir()
        with pytest.raises(RawDiffError, match="\\.git"):
            raw_diff(snap, sand)

    def test_rejects_nested_git(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_nested_git"
        sand.mkdir()
        (sand / "src").mkdir()
        (sand / "src" / ".git").mkdir()
        with pytest.raises(RawDiffError, match="\\.git"):
            raw_diff(snap, sand)


# ---------------------------------------------------------------------------
# Secret-like file rejection
# ---------------------------------------------------------------------------


class TestSecretRejection:
    @pytest.mark.parametrize(
        "name", [".env", ".env.prod", ".env.local", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"]
    )
    def test_rejects_secret_basename(self, snap: Path, tmp_path: Path, name: str):
        sand = tmp_path / "sand_secret"
        sand.mkdir()
        (sand / name).write_text("secret")
        with pytest.raises(RawDiffError, match="secret-like"):
            raw_diff(snap, sand)

    @pytest.mark.parametrize("path", [".ssh/authorized_keys", ".aws/credentials"])
    def test_rejects_secret_dir(self, snap: Path, tmp_path: Path, path: str):
        sand = tmp_path / "sand_secret_dir"
        sand.mkdir()
        p = sand / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("secret")
        with pytest.raises(RawDiffError, match="secret directory"):
            raw_diff(snap, sand)

    def test_rejects_gh_config(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_gh_config"
        sand.mkdir()
        p = sand / ".config" / "gh" / "config.yml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("gh_token")
        # .config/ matches secret directory check before .config/gh/ check
        with pytest.raises(RawDiffError, match="secret directory"):
            raw_diff(snap, sand)


# ---------------------------------------------------------------------------
# Symlink handling
# ---------------------------------------------------------------------------


class TestSymlinkRejection:
    def test_rejects_symlink_in_snapshot(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_symlink"
        sand.mkdir()
        # Create a symlink pointing outside the directory — os.walk will
        # follow it on some platforms, potentially accessing external files
        link = snap / "escape.link"
        link.symlink_to(snap.parent / "secret.txt")
        # Write the target so the symlink resolves
        (snap.parent / "secret.txt").write_text("stolen")
        # Create a corresponding file in sandbox to force a diff
        (sand / "escape.link").write_text("dummy")
        with pytest.raises(RawDiffError):
            raw_diff(snap, sand)
        link.unlink()
        (snap.parent / "secret.txt").unlink()


# ---------------------------------------------------------------------------
# Binary / unsupported file rejection
# ---------------------------------------------------------------------------


class TestBinaryRejection:
    def test_rejects_nul_byte(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_nul"
        sand.mkdir()
        (sand / "binary.bin").write_bytes(b"\x00\x01\x02")
        with pytest.raises(RawDiffError, match="NUL byte"):
            raw_diff(snap, sand)

    def test_rejects_invalid_utf8(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_bad_utf8"
        sand.mkdir()
        (sand / "bad.txt").write_bytes(b"\xff\xfe")
        with pytest.raises(RawDiffError, match="UTF-8"):
            raw_diff(snap, sand)


# ---------------------------------------------------------------------------
# CRLF / line ending handling
# ---------------------------------------------------------------------------


class TestLineEndings:
    def test_crlf_normalized_to_lf(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_crlf"
        sand.mkdir()
        (sand / "app.py").write_bytes(b"new\r\ncontent\r\n")
        result = raw_diff(snap, sand)
        # All newlines in the diff output should be LF
        assert "\r\n" not in result

    def test_cr_normalized_to_lf(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_cr"
        sand.mkdir()
        (sand / "app.py").write_bytes(b"new\rcontent\r")
        result = raw_diff(snap, sand)
        assert "\r\n" not in result
        # Single \r should have been normalized
        assert result.count("\n") > 0


# ---------------------------------------------------------------------------
# Empty directories and metadata changes
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_directories_ignored(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_empty"
        sand.mkdir()
        (sand / "empty_dir").mkdir()
        result = raw_diff(snap, sand)
        # Empty dir should not produce any diff output
        assert "empty_dir" not in result

    def test_hidden_non_secret_file_allowed(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_hidden"
        sand.mkdir()
        (sand / ".gitignore").write_text("*.pyc\n")
        result = raw_diff(snap, sand)
        assert ".gitignore" in result
        assert "*.pyc" in result

    def test_snapshot_not_mutated(self, snap: Path, sand: Path):
        before = (snap / "app.py").read_text()
        raw_diff(snap, sand)
        assert (snap / "app.py").read_text() == before

    def test_sandbox_not_mutated(self, snap: Path, sand: Path):
        before = (sand / "app.py").read_text()
        raw_diff(snap, sand)
        assert (sand / "app.py").read_text() == before

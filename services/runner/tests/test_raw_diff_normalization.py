"""Tests for normalize_sandbox_diff — integration of raw_diff + PatchNormalizer."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from runner.diff import raw_diff
from runner.models import NormalizedPatch
from runner.normalize import normalize_sandbox_diff
from runner.patch import normalize_patch_text


def _is_normalized_patch(obj) -> bool:
    """Duck-type check for NormalizedPatch.

    isinstance may fail due to Python import path duplication
    (runner.models vs services.runner.src.runner.models).
    """
    return hasattr(obj, "text") and hasattr(obj, "touched_paths")


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
    return d


@pytest.fixture
def sand(snap: Path, tmp_path: Path) -> Path:
    """Create a sandbox by copying snapshot and applying changes."""
    d = tmp_path / "sand"
    shutil.copytree(snap, d)
    # Modify a file
    (d / "app.py").write_text("new\ncontent\n")
    # Add a file
    (d / "new_file.py").write_text("print('new')\n")
    # Delete a file
    (d / "README.md").unlink()
    return d


# ---------------------------------------------------------------------------
# Empty diff
# ---------------------------------------------------------------------------


class TestEmptyDiff:
    def test_returns_empty_normalized_patch(self, snap: Path, tmp_path: Path):
        same = tmp_path / "same"
        shutil.copytree(snap, same)
        result = normalize_sandbox_diff(snap, same)
        assert _is_normalized_patch(result)
        assert result.text == ""
        assert result.touched_paths == ()

    def test_empty_diff_matches_patch_normalizer_behavior(self, snap: Path, tmp_path: Path):
        same = tmp_path / "same"
        shutil.copytree(snap, same)
        result = normalize_sandbox_diff(snap, same)
        expected = normalize_patch_text("")
        assert result == expected


# ---------------------------------------------------------------------------
# Successful normalization
# ---------------------------------------------------------------------------


class TestSuccessfulNormalization:
    def test_modified_file_returns_normalized_patch(self, snap: Path, sand: Path):
        result = normalize_sandbox_diff(snap, sand)
        assert _is_normalized_patch(result)
        # Touched paths are alphabetically sorted (README.md, app.py, new_file.py)
        assert len(result.touched_paths) == 3
        assert "app.py" in result.touched_paths
        assert "new_file.py" in result.touched_paths
        assert "README.md" in result.touched_paths

    def test_added_file_appears_in_touched_paths(self, snap: Path, sand: Path):
        result = normalize_sandbox_diff(snap, sand)
        assert "new_file.py" in result.touched_paths

    def test_deleted_file_appears_in_touched_paths(self, snap: Path, sand: Path):
        result = normalize_sandbox_diff(snap, sand)
        assert "README.md" in result.touched_paths

    def test_text_matches_patch_normalizer_on_same_input(self, snap: Path, sand: Path):
        result = normalize_sandbox_diff(snap, sand)
        diff = raw_diff(snap, sand)
        expected = normalize_patch_text(diff)
        assert result == expected

    def test_output_is_deterministic(self, snap: Path, sand: Path):
        r1 = normalize_sandbox_diff(snap, sand)
        r2 = normalize_sandbox_diff(snap, sand)
        assert r1 == r2


# ---------------------------------------------------------------------------
# Safety preserved
# ---------------------------------------------------------------------------


class TestSafetyPreserved:
    def test_rejects_git_metadata(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_git"
        sand.mkdir()
        (sand / ".git").mkdir()
        (sand / ".git" / "config").write_text("test")
        with pytest.raises(Exception):
            normalize_sandbox_diff(snap, sand)

    @pytest.mark.parametrize("name", [".env", ".env.prod", "id_rsa", "id_dsa"])
    def test_rejects_secret_like_files(self, snap: Path, tmp_path: Path, name: str):
        sand = tmp_path / "sand_secret"
        sand.mkdir()
        (sand / name).write_text("secret")
        with pytest.raises(Exception):
            normalize_sandbox_diff(snap, sand)

    def test_rejects_binary_files(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_binary"
        sand.mkdir()
        (sand / "binary.bin").write_bytes(b"\x00\x01\x02")
        with pytest.raises(Exception):
            normalize_sandbox_diff(snap, sand)

    def test_rejects_symlinks(self, snap: Path, tmp_path: Path):
        sand = tmp_path / "sand_symlink"
        sand.mkdir()
        (sand / "link.txt").symlink_to(snap / "app.py")
        with pytest.raises(Exception):
            normalize_sandbox_diff(snap, sand)


# ---------------------------------------------------------------------------
# Mutation checks
# ---------------------------------------------------------------------------


class TestNoMutation:
    def test_snapshot_not_mutated(self, snap: Path, sand: Path):
        before = (snap / "app.py").read_text()
        normalize_sandbox_diff(snap, sand)
        assert (snap / "app.py").read_text() == before

    def test_sandbox_not_mutated(self, snap: Path, sand: Path):
        before = (sand / "app.py").read_text()
        normalize_sandbox_diff(snap, sand)
        assert (sand / "app.py").read_text() == before

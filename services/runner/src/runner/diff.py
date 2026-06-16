"""
Raw diff contract — compares a WorktreeManager snapshot and sandbox and
returns a unified diff string using Python stdlib only.

See PLAN.md for full contract, determinism rules, and forbidden path lists.
"""

from __future__ import annotations

import difflib
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class RawDiffError(ValueError):
    """Raised when raw_diff encounters an unsafe or unsupported input."""


# ---------------------------------------------------------------------------
# Secret-like path rejection constants
# ---------------------------------------------------------------------------

_FORBIDDEN_BASENAMES: frozenset[str] = frozenset(
    {".env", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}
)
_FORBIDDEN_DIR_CHILDREN: tuple[str, ...] = (
    ".ssh/",
    ".aws/",
    ".config/",
)
_FORBIDDEN_GH_CONFIG_CHILDREN: tuple[str, ...] = (".config/gh/",)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def raw_diff(snapshot_path: Path, sandbox_path: Path) -> str:
    """Compare *snapshot_path* and *sandbox_path* recursively and return a
    unified diff string.

    Parameters
    ----------
    snapshot_path
        Read-only snapshot directory (e.g. from WorktreeManager).
    sandbox_path
        Writable sandbox directory (e.g. from WorktreeManager).

    Returns
    -------
    str
        Unified diff text, or empty string if no differences.

    Raises
    ------
    RawDiffError
        If inputs are invalid, paths are unsafe, or files cannot be decoded.
    FileNotFoundError
        If either path does not exist.
    """
    snap = snapshot_path.resolve()
    sand = sandbox_path.resolve()

    # -- Input validation ---------------------------------------------------
    if not snap.exists():
        raise FileNotFoundError(f"snapshot_path does not exist: {snap}")
    if not sand.exists():
        raise FileNotFoundError(f"sandbox_path does not exist: {sand}")
    if not snap.is_dir():
        raise RawDiffError(f"snapshot_path is not a directory: {snap}")
    if not sand.is_dir():
        raise RawDiffError(f"sandbox_path is not a directory: {sand}")
    if snap == sand:
        raise RawDiffError(
            f"snapshot_path and sandbox_path must differ, but both resolve to: {snap}"
        )

    # -- Collect relative file paths in sorted order ------------------------
    snap_files = _collect_relative_paths(snap)
    sand_files = _collect_relative_paths(sand)
    all_paths = sorted(set(snap_files) | set(sand_files))

    # -- Check for forbidden directories that os.walk may skip ------------
    _check_forbidden_directories(snap)
    _check_forbidden_directories(sand)

    # -- Build unified diff lines -------------------------------------------
    diff_lines: list[str] = []

    for rel in all_paths:
        # Validate each path before diffing
        _validate_relative_path(rel)

        snap_full = snap / rel
        sand_full = sand / rel

        snap_exists = snap_full.exists() and snap_full.is_file()
        sand_exists = sand_full.exists() and sand_full.is_file()

        if not snap_exists and not sand_exists:
            # Empty directory or metadata-only — ignored
            continue
        if snap_exists and sand_exists:
            # Compare contents
            old_text = _read_file(snap_full)
            new_text = _read_file(sand_full)
            if old_text == new_text:
                continue
            diff_lines.extend(
                difflib.unified_diff(
                    old_text.splitlines(keepends=True),
                    new_text.splitlines(keepends=True),
                    fromfile=f"a/{rel}",
                    tofile=f"b/{rel}",
                )
            )
        elif snap_exists:
            # Deleted file
            old_text = _read_file(snap_full)
            diff_lines.extend(
                difflib.unified_diff(
                    old_text.splitlines(keepends=True),
                    [],
                    fromfile=f"a/{rel}",
                    tofile="/dev/null",
                )
            )
        else:
            # Added file
            new_text = _read_file(sand_full)
            diff_lines.extend(
                difflib.unified_diff(
                    [],
                    new_text.splitlines(keepends=True),
                    fromfile="/dev/null",
                    tofile=f"b/{rel}",
                )
            )

    return "".join(diff_lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _check_forbidden_directories(directory: Path) -> None:
    """Walk *directory* and reject if any forbidden dir (e.g. .git) exists.

    os.walk skips certain hidden directories by default, so we explicitly
    check for known forbidden directory names.
    """
    for root, dirs, files in os.walk(str(directory)):
        for d in dirs:
            if d == ".git":
                rel = os.path.relpath(os.path.join(root, d), str(directory))
                raise RawDiffError(
                    f"Directory contains .git metadata and is rejected: {rel}"
                )
            if d.startswith("."):
                # Also check for secret directories at this level
                full = os.path.join(root, d)
                rel = os.path.relpath(full, str(directory))
                _validate_relative_path(rel + "/dummy")


def _collect_relative_paths(directory: Path) -> list[str]:
    """Recursively collect relative paths of all files under *directory*.

    Symlink files are explicitly rejected.
    Directories are not included in the list; only regular files are.
    """
    result: list[str] = []
    for root, dirs, files in os.walk(str(directory)):
        rel_root = os.path.relpath(root, str(directory))
        # Normalise to POSIX and skip root marker
        if rel_root == ".":
            rel_root = ""
        for fname in files:
            full = os.path.join(rel_root, fname).replace("\\", "/")
            fp = Path(root) / fname
            if fp.is_symlink():
                raise RawDiffError(
                    f"Diff contains a symlink and is rejected: {full}"
                )
            result.append(full)
    return result


def _read_file(path: Path) -> str:
    """Read the file at *path*, decode as UTF-8 strict, normalise line endings.

    Raises
    ------
    RawDiffError
        If the file contains a NUL byte or cannot be decoded as UTF-8.
    """
    raw = path.read_bytes()

    # NUL byte check: also catches binary files
    if b"\0" in raw:
        raise RawDiffError(
            f"File contains NUL byte and is treated as binary/unsupported: {path}"
        )

    # UTF-8 strict decoding
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RawDiffError(
            f"File is not valid UTF-8 and is treated as binary/unsupported: {path}"
        ) from exc

    # Normalise CRLF and CR to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    return text


def _validate_relative_path(rel: str) -> None:
    """Check a single relative path against forbidden patterns.

    Raises RawDiffError if the path matches a forbidden entry.
    """
    # .git component
    if ".git" in rel.split("/"):
        raise RawDiffError(
            f"Diff contains .git metadata path and is rejected: {rel}"
        )

    # Secret-like basenames
    basename = Path(rel).name
    if basename in _FORBIDDEN_BASENAMES:
        raise RawDiffError(
            f"Diff contains a secret-like file and is rejected: {rel}"
        )
    if basename.startswith(".env."):
        raise RawDiffError(
            f"Diff contains a secret-like file and is rejected: {rel}"
        )

    # Forbidden directory children
    for prefix in _FORBIDDEN_DIR_CHILDREN:
        if rel == prefix.rstrip("/") or rel.startswith(prefix):
            raise RawDiffError(
                f"Diff contains a secret directory path and is rejected: {rel}"
            )

    # GitHub CLI config
    for prefix in _FORBIDDEN_GH_CONFIG_CHILDREN:
        if rel == prefix.rstrip("/") or rel.startswith(prefix):
            raise RawDiffError(
                f"Diff contains GitHub CLI config path and is rejected: {rel}"
            )

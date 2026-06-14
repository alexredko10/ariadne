"""
Repo-relative patch path normalisation and forbidden-path rejection.

All functions operate on POSIX-style repo-relative paths and follow the
algorithm specified in PLAN.md.
"""

from __future__ import annotations

import os
import posixpath
import re
import string

from services.runner.src.runner.models import NormalizedPatch

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DRIVE_LETTER_RE = re.compile(r"^[A-Za-z]:")
_WHITESPACE_ONLY_RE = re.compile(r"^\s+$")
_CONTROL_CHARS = frozenset(chr(i) for i in range(0x20))
_FORBIDDEN_BASENAMES: frozenset[str] = frozenset({".env", "id_rsa", "id_ed25519"})
_FORBIDDEN_EXTENSIONS: frozenset[str] = frozenset({".pem", ".key"})
_FORBIDDEN_SUBSTRINGS: frozenset[str] = frozenset({"secret", "token", "credential"})
_PROJECT_MEMORY_WHITELIST: str = (
    ".project-memory/pr/0001-runner-patch-contracts/PLAN.md"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_repo_path(path: str) -> str:
    """Normalise a single repo-relative path.

    Raises
    ------
    ValueError
        If the path is structurally invalid (empty, absolute, contains ``..``,
        contains NUL / control characters, has leading/trailing whitespace,
        or is a Windows drive-letter path).
    """
    _validate_input(path)
    normalized = _normalize(path)
    return normalized


def is_forbidden_patch_path(path: str) -> bool:
    """Return ``True`` if *path* targets a forbidden location.

    The path is expected to already be normalised (call ``normalize_repo_path``
    first).  This function checks directory prefixes, exact whitelists, and
    secret-like basenames.
    """
    # .git/ subtree
    if path.startswith(".git/") or path == ".git":
        return True

    # .project-memory/ subtree (with exact whitelist)
    if path.startswith(".project-memory/") or path == ".project-memory":
        if path == _PROJECT_MEMORY_WHITELIST:
            return False
        return True

    return _is_forbidden_basename(path)


def validate_patch_path(path: str) -> str:
    """Normalise and validate a repo-relative patch path.

    Returns the normalised path on success.

    Raises
    ------
    ValueError
        If the path is structurally invalid *or* targets a forbidden location.
    """
    normalized = normalize_repo_path(path)
    if is_forbidden_patch_path(normalized):
        raise ValueError(f"Patch path targets a forbidden location: {normalized!r}")
    return normalized


def normalize_patch_text(diff_text: str) -> NormalizedPatch:
    """Parse a basic unified-diff string and return a ``NormalizedPatch``.

    Extracts touched paths from:
    - ``+++ b/path``
    - ``--- a/path``
    - ``diff --git a/path b/path``

    All touched paths are validated with ``validate_patch_path``.  If any
    is invalid or forbidden a ``ValueError`` is raised.
    """
    if not isinstance(diff_text, str) or not diff_text.strip():
        return NormalizedPatch(text=diff_text or "", touched_paths=())

    seen: dict[str, str] = {}

    for line in diff_text.splitlines():
        candidate: str | None = None
        if line.startswith("+++ b/"):
            candidate = _strip_prefix(line, "+++ b/")
        elif line.startswith("--- a/"):
            candidate = _strip_prefix(line, "--- a/")
        elif line.startswith("diff --git"):
            parts = line.split()
            if len(parts) >= 4:
                # diff --git a/path b/path → take the second (b) path
                b_part = parts[3]
                if b_part.startswith("b/"):
                    candidate = _strip_prefix(b_part, "b/")
        if candidate is not None and candidate not in seen:
            # validate immediately – raises ValueError on failure
            validated = validate_patch_path(candidate)
            seen[candidate] = validated

    touched = tuple(seen.values())
    return NormalizedPatch(text=diff_text, touched_paths=touched)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_input(path: str) -> None:
    """Check structural validity *before* normalisation."""
    if not isinstance(path, str):
        raise TypeError(f"Expected str, got {type(path).__name__}")

    # Empty string
    if not path:
        raise ValueError("Path must not be empty")

    # Whitespace-only
    if _WHITESPACE_ONLY_RE.match(path):
        raise ValueError("Path must not be whitespace-only")

    # Leading / trailing whitespace
    stripped = path.strip()
    if stripped != path:
        raise ValueError(
            f"Path must not have leading or trailing whitespace: {path!r}"
        )

    # NUL byte
    if "\0" in path:
        raise ValueError("Path must not contain NUL byte")

    # Control characters (< 0x20, excluding \t for now — keep strict)
    for ch in path:
        if ch in _CONTROL_CHARS:
            raise ValueError(
                f"Path must not contain control character {ord(ch):#x}"
            )


def _normalize(path: str) -> str:
    """Backslash-to-slash conversion, drive-letter rejection, .. rejection,
    posixpath.normpath, and final safety checks.

    Raises ValueError on failure.
    """
    # 5. Convert backslashes to forward slashes
    path = path.replace("\\", "/")

    # 6. Reject Windows drive-letter absolute paths
    if _DRIVE_LETTER_RE.match(path):
        raise ValueError(
            f"Path must not be a Windows drive-letter path: {path!r}"
        )

    # 7. Reject any path containing ".."
    if ".." in path.split("/"):
        raise ValueError(
            f"Path must not contain directory traversal (..): {path!r}"
        )

    # 8. Normalize with posixpath.normpath
    normalized = posixpath.normpath(path)

    # 9. Reject normalized path starting with /
    if normalized.startswith("/"):
        raise ValueError(
            f"Path must not be absolute after normalisation: {normalized!r}"
        )

    # 10. Reject normalized path equal to "."
    if normalized == ".":
        raise ValueError("Path must not be the current-directory alias (.)")

    return normalized


def _is_forbidden_basename(path: str) -> bool:
    """Check the final path component against secret-like patterns."""
    basename = os.path.basename(path)
    if not basename:
        return False

    # Exact basename matches
    if basename in _FORBIDDEN_BASENAMES:
        return True

    # .env.* (e.g. .env.prod, .env.local)
    if basename.startswith(".env."):
        return True

    # Extension checks (case-insensitive)
    _, ext = os.path.splitext(basename)
    if ext.lower() in _FORBIDDEN_EXTENSIONS:
        return True

    # Substring checks (case-insensitive) on the full basename including extension
    lower = basename.lower()
    for sub in _FORBIDDEN_SUBSTRINGS:
        if sub in lower:
            return True

    return False


def _strip_prefix(line: str, prefix: str) -> str:
    """Remove *prefix* from *line* and return the remainder."""
    start = line.index(prefix) + len(prefix)
    return line[start:]

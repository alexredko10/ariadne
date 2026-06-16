"""
WorktreeManager — safe filesystem isolation for agent execution context.

The manager creates read-only context snapshots from a source root, then
creates writable sandbox copies from those snapshots. All temporary paths
are tracked and owned by the manager. See PLAN.md for full contract.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class WorktreeSafetyError(ValueError):
    """Raised when an unsafe path is passed to a WorktreeManager method."""


# ---------------------------------------------------------------------------
# Secret-like file basenames and directories to reject
# ---------------------------------------------------------------------------

_FORBIDDEN_BASENAMES: frozenset[str] = frozenset(
    {".env", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}
)
_FORBIDDEN_DIRS: tuple[str, ...] = (".ssh", ".aws", ".config")
_FORBIDDEN_DIR_CHILDREN: set[str] = set()
for _d in _FORBIDDEN_DIRS:
    _FORBIDDEN_DIR_CHILDREN.add(f"{_d}/")


# ---------------------------------------------------------------------------
# WorktreeManager
# ---------------------------------------------------------------------------


class WorktreeManager:
    """Creates and destroys isolated context snapshots and sandboxes.

    All artifacts are placed under a single manager-owned temporary root
    and tracked in an internal registry.
    """

    def __init__(self) -> None:
        self._root: Path = Path(os.path.realpath(tempfile.mkdtemp(prefix="runner_worktree_")))
        self._created: set[Path] = set()

    @property
    def root(self) -> Path:
        """The manager-owned temporary root directory."""
        return self._root

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_context_snapshot(
        self,
        source_root: Path,
        include_paths: Sequence[str],
    ) -> Path:
        """Copy requested paths from *source_root* into a new snapshot.

        Returns the absolute path of the created snapshot directory.

        Raises
        ------
        WorktreeSafetyError
            If any include path is invalid, forbidden, or unsafe.
        FileNotFoundError
            If an include path does not exist under *source_root*.
        """
        source_root = source_root.resolve()

        snapshot = Path(tempfile.mkdtemp(dir=self._root, prefix="snapshot_"))
        self._created.add(snapshot)

        for raw_path in include_paths:
            self._validate_include_path(raw_path, source_root)

            src = source_root / raw_path
            dst = snapshot / raw_path

            # Check for symlinks before resolving — reject all for safety
            if src.is_symlink():
                raise WorktreeSafetyError(
                    f"Include path contains a symlink, which is rejected: {raw_path}"
                )

            src = src.resolve()

            if not src.exists():
                raise FileNotFoundError(
                    f"Include path does not exist: {raw_path} (resolved: {src})"
                )

            dst.parent.mkdir(parents=True, exist_ok=True)

            if src.is_dir():
                shutil.copytree(src, dst, symlinks=False)
            else:
                shutil.copy2(src, dst)

        return snapshot

    def create_sandbox(self, snapshot_path: Path) -> Path:
        """Create a writable copy of *snapshot_path*.

        *snapshot_path* must have been created by this manager instance.
        Returns the absolute path of the created sandbox directory.
        """
        self._validate_ownership(snapshot_path, "snapshot_path")

        sandbox = Path(tempfile.mkdtemp(dir=self._root, prefix="sandbox_"))
        self._created.add(sandbox)

        for item in snapshot_path.iterdir():
            dst = sandbox / item.name
            if item.is_dir():
                shutil.copytree(item, dst, symlinks=False)
            else:
                shutil.copy2(item, dst)

        return sandbox

    def destroy(self, path: Path) -> None:
        """Remove a previously created snapshot or sandbox.

        Raises
        ------
        WorktreeSafetyError
            If *path* is unsafe or was not created by this manager instance.
        """
        resolved = path.resolve()

        # Reject anything that is not under our temp root
        if not str(resolved).startswith(str(self._root)):
            raise WorktreeSafetyError(
                f"Refusing to destroy path outside manager-owned temp root: {path}"
            )

        # Reject paths not created by this manager
        if resolved not in self._created:
            raise WorktreeSafetyError(
                f"Refusing to destroy path not created by this manager: {path}"
            )

        if resolved.exists():
            if resolved.is_dir():
                shutil.rmtree(resolved)
            else:
                resolved.unlink()

        self._created.discard(resolved)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_include_path(self, raw_path: str, source_root: Path) -> None:
        """Check a single include path for structural and safety rules."""
        # Reject absolute paths
        if raw_path.startswith("/"):
            raise WorktreeSafetyError(
                f"Include path is absolute, must be relative: {raw_path}"
            )

        # Reject empty paths
        if not raw_path:
            raise WorktreeSafetyError("Include path must not be empty")

        # Reject .. traversal
        if ".." in raw_path.split("/"):
            raise WorktreeSafetyError(
                f"Include path contains '..' traversal: {raw_path}"
            )

        # Reject any .git component
        if _has_git_component(raw_path):
            raise WorktreeSafetyError(
                f"Include path contains .git component: {raw_path}"
            )

        # Reject known secret-like file basenames
        basename = Path(raw_path).name
        if basename in _FORBIDDEN_BASENAMES:
            raise WorktreeSafetyError(
                f"Include path targets a secret-like file: {raw_path}"
            )

        # Reject .env.* (e.g. .env.prod)
        if basename.startswith(".env."):
            raise WorktreeSafetyError(
                f"Include path targets a secret-like file: {raw_path}"
            )

        # Reject paths under forbidden directories (.ssh/, .aws/, .config/)
        for _prefix in _FORBIDDEN_DIR_CHILDREN:
            if raw_path == _prefix.rstrip("/") or raw_path.startswith(_prefix):
                raise WorktreeSafetyError(
                    f"Include path targets a secret directory: {raw_path}"
                )

        # Reject .config/gh/ children (GitHub CLI config)
        if raw_path.startswith(".config/gh/") or raw_path == ".config/gh":
            raise WorktreeSafetyError(
                f"Include path targets GitHub CLI config: {raw_path}"
            )

    def _validate_ownership(self, path: Path, label: str) -> None:
        """Ensure *path* belongs to this manager instance."""
        resolved = path.resolve()
        if not str(resolved).startswith(str(self._root)):
            raise WorktreeSafetyError(
                f"{label} is outside manager-owned temp root: {path}"
            )
        if resolved not in self._created:
            raise WorktreeSafetyError(
                f"{label} was not created by this manager instance: {path}"
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_git_component(path: str) -> bool:
    """Return True if any path segment equals '.git'."""
    parts = path.replace("\\", "/").split("/")
    return ".git" in parts

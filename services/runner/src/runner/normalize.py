"""
Integration layer that converts WorktreeManager sandbox changes into the
existing normalized patch representation.

Pipeline::

    snapshot + sandbox
    → runner.diff.raw_diff(snapshot, sandbox)
    → runner.patch.normalize_patch_text(diff_text)
    → runner.models.NormalizedPatch
"""

from __future__ import annotations

from pathlib import Path

from runner.diff import raw_diff
from runner.models import NormalizedPatch
from runner.patch import normalize_patch_text


def normalize_sandbox_diff(snapshot_path: Path, sandbox_path: Path) -> NormalizedPatch:
    """Compare *snapshot_path* and *sandbox_path* and return a
    ``NormalizedPatch``.

    The function delegates all safety and validation to:
    1. ``runner.diff.raw_diff`` — deterministic unified diff generation
    2. ``runner.patch.normalize_patch_text`` — path validation and extraction

    No new safety logic is added here.  No patch application occurs.

    Parameters
    ----------
    snapshot_path
        Read-only snapshot directory (e.g. from ``WorktreeManager``).
    sandbox_path
        Writable sandbox directory (e.g. from ``WorktreeManager``).

    Returns
    -------
    NormalizedPatch
        An empty ``NormalizedPatch`` when no differences are found.
    """
    diff_text = raw_diff(snapshot_path, sandbox_path)
    return normalize_patch_text(diff_text)

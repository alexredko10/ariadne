"""Shared test fixtures for runner tests.

This conftest adds a narrow autouse fixture that removes exact known
generated residue paths before and after each test.  Known generated
residue is not commit payload and must not be staged or committed.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

# Exact known generated residue paths relative to repository root.
# These are created by test or fake runtime execution and are not
# commit payload.  They must not be staged or committed.
_KNOWN_RESIDUE_PATHS: tuple[str, ...] = (
    "captures",
    ".ariadne",
    ".project-memory/pr/test",
    ".project-memory/pr/0127",
    ".project-memory/pr/dogfood",
    "test_stage_file.py",
)


def _remove_if_exists(path: str) -> None:
    """Remove a file or directory if it exists.  No-op if absent."""
    p = Path(path)
    if not p.exists():
        return
    if p.is_dir():
        shutil.rmtree(p)
    else:
        p.unlink()


@pytest.fixture(autouse=True, scope="function")
def cleanup_known_residue():
    """Remove exact known generated residue paths before and after each test.

    This fixture runs before and after every test in the runner test suite.
    It removes only the exact paths listed in _KNOWN_RESIDUE_PATHS.
    It tolerates paths that do not exist.
    It does not call shell commands.
    It does not delete committed project-memory artifacts.
    """
    for path in _KNOWN_RESIDUE_PATHS:
        _remove_if_exists(path)
    yield
    for path in _KNOWN_RESIDUE_PATHS:
        _remove_if_exists(path)

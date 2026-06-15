"""
Platform-runner doctor command: validates that key runner modules are importable.

This module exposes:
- ``run_doctor()`` → returns 0 on success, 1 on failure
- ``main(argv)`` → argument-parsing entry point
"""

from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Sequence


EXPECTED_OUTPUT_LINES = (
    "platform-runner doctor",
    "runner import: ok",
    "patch models: ok",
    "patch safety: ok",
)


def run_doctor() -> int:
    """Run all doctor checks and print results to stdout.

    Returns 0 if all checks pass, 1 otherwise.
    """
    checks = (
        ("runner import", "runner"),
        ("patch models", "runner.models"),
        ("patch safety", "runner.patch"),
    )

    print(EXPECTED_OUTPUT_LINES[0])

    for label, module_name in checks:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            print(f"{label}: failed", file=sys.stderr)
            print(f"{module_name}: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1
        print(f"{label}: ok")

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Argument-based entry point for ``python -m runner doctor``."""
    parser = argparse.ArgumentParser(
        prog="python -m runner",
        description="Platform runner command line utilities.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="Run platform-runner runtime diagnostics.")

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "doctor":
        return run_doctor()

    parser.print_usage(sys.stderr)
    return 2

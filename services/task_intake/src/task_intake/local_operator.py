"""
Local Operator — safe loopback server entrypoint with server-owned runs-root.

PR 0147A: OPTION B — Minimal ASGI runtime and operator entrypoint.

Usage:
    python -m task_intake.local_operator [--host HOST] [--port PORT] [--runs-root PATH] [--check]
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _resolve_runs_root(runs_root_arg: str | None, repo_root: str) -> str:
    """Resolve and normalize the runs-root path."""
    if runs_root_arg:
        path = runs_root_arg
    else:
        path = os.path.join(repo_root, ".ariadne", "runs")
    return os.path.abspath(path)


def _ensure_runs_root(runs_root: str) -> None:
    """Create runs-root directory if it does not exist."""
    os.makedirs(runs_root, exist_ok=True)


def _validate_host(host: str, allow_public_bind: bool) -> str:
    """Validate host and return normalized value."""
    if host in ("0.0.0.0", "::"):
        if not allow_public_bind:
            print(
                "Ariadne — Local Operator",
                file=sys.stderr,
            )
            print(
                "  Error: Public bind (0.0.0.0) is not permitted by default.",
                file=sys.stderr,
            )
            print(
                "  Use --allow-public-bind to bind publicly (unsafe).",
                file=sys.stderr,
            )
            print(
                "  Run with --check to validate configuration.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(
            "WARNING: Binding to 0.0.0.0 — server is publicly accessible on this network.",
            file=sys.stderr,
        )
    return host


def _validate_port(port: int, allow_privileged_port: bool) -> int:
    """Validate port number. Returns port or exits with error."""
    if not isinstance(port, int):
        print(
            "Ariadne — Local Operator",
            file=sys.stderr,
        )
        print(
            f"  Error: Port must be an integer, got {port}.",
            file=sys.stderr,
        )
        print(
            "  Run with --check to validate configuration.",
            file=sys.stderr,
        )
        sys.exit(1)
    if port < 1 or port > 65535:
        print(
            "Ariadne — Local Operator",
            file=sys.stderr,
        )
        print(
            f"  Error: Port must be between 1 and 65535, got {port}.",
            file=sys.stderr,
        )
        print(
            "  Run with --check to validate configuration.",
            file=sys.stderr,
        )
        sys.exit(1)
    if port < 1024 and not allow_privileged_port:
        print(
            "Ariadne — Local Operator",
            file=sys.stderr,
        )
        print(
            f"  Error: Privileged port ({port}) is not permitted without --allow-privileged-port.",
            file=sys.stderr,
        )
        print(
            "  Run with --check to validate configuration.",
            file=sys.stderr,
        )
        sys.exit(1)
    return port


def _print_startup(
    host: str,
    port: int,
    runs_root: str,
) -> None:
    """Print startup diagnostics."""
    print("Ariadne — Local Operator")
    print(f"  Runs root: {runs_root}")
    print(f"  Workspace: http://{host}:{port}/workspace")
    print(f"  Health:    http://{host}:{port}/health")
    print("  Status:    READ-ONLY — no agent execution, no mutation, no orchestration.")
    print("  Press Ctrl-C to stop.")


def _print_check_json(
    host: str,
    port: int,
    runs_root: str,
) -> None:
    """Print configuration as JSON for --check mode."""
    config = {
        "host": host,
        "port": port,
        "runs_root": runs_root,
        "health_url": f"http://{host}:{port}/health",
        "workspace_url": f"http://{host}:{port}/workspace",
        "status": "READ-ONLY",
    }
    print(json.dumps(config, sort_keys=True, indent=2))


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser for local_operator."""
    parser = argparse.ArgumentParser(
        prog="python -m task_intake.local_operator",
        description="Ariadne Local Operator — read-only Artifact Workspace server.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port (default: 8000)",
    )
    parser.add_argument(
        "--runs-root",
        default=None,
        help="Runs root directory (default: .ariadne/runs relative to repository root)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate configuration and exit (does not start server)",
    )
    parser.add_argument(
        "--allow-public-bind",
        action="store_true",
        help="Allow binding to 0.0.0.0 (unsafe)",
    )
    parser.add_argument(
        "--allow-privileged-port",
        action="store_true",
        help="Allow privileged ports (<1024)",
    )
    return parser


def _get_repo_root() -> str:
    """Return the repository root (parent of the services directory).
    
    The local_operator module lives in:
        services/task_intake/src/task_intake/local_operator.py
    
    The repository root is resolved from __file__ by walking up to find
    the parent of the 'services' directory.
    """
    # Start from this module's directory and walk up
    current = os.path.dirname(os.path.abspath(__file__))
    # Walk up: .../task_intake/src/task_intake -> .../task_intake/src -> .../task_intake -> .../services -> repo_root
    while current != os.path.dirname(current):
        if os.path.basename(current) == "services":
            return os.path.dirname(current)
        current = os.path.dirname(current)
    # Fallback to cwd
    return os.getcwd()


def main(argv: list[str] | None = None) -> int:
    """Local operator entrypoint.

    Returns exit code: 0 on clean shutdown, 1 on configuration error.
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    repo_root = _get_repo_root()
    runs_root = _resolve_runs_root(args.runs_root, repo_root)

    # Validate host (sys.exit caught and translated to non-zero return)
    try:
        host = _validate_host(args.host, args.allow_public_bind)
    except SystemExit:
        return 1

    # Validate port
    try:
        port = _validate_port(args.port, args.allow_privileged_port)
    except SystemExit:
        return 1

    # --check mode: print config and exit (no mutation)
    if args.check:
        _print_check_json(host, port, runs_root)
        return 0

    # Ensure runs-root exists (only for normal launch, not --check)
    _ensure_runs_root(runs_root)

    # Print startup diagnostics
    _print_startup(host, port, runs_root)

    # Import and launch uvicorn
    try:
        import uvicorn
    except ImportError:
        print(
            "Ariadne — Local Operator",
            file=sys.stderr,
        )
        print(
            "  Error: uvicorn is not installed.",
            file=sys.stderr,
        )
        print(
            "  Install with: make install-dev",
            file=sys.stderr,
        )
        return 1

    # Create a wrapper ASGI app that injects the server-owned runs_root
    from task_intake.server import app as _original_app

    async def _operator_app(scope, receive, send):
        await _original_app(scope, receive, send, runs_root=runs_root)

    uvicorn.run(
        _operator_app,
        host=host,
        port=port,
        log_level="info",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

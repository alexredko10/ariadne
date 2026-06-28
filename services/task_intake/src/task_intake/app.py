"""Task Intake app callable — accept_task and local runtime entrypoint.

The local app runtime serves the existing ASGI ``app`` from ``server.py``
via uvicorn.  No new routes.  Docker adapter remains opt-in.  Test-mode CLI
remains unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from task_intake.models import (
    MAX_PROMPT_LENGTH,
    TaskIntakeAccepted,
    TaskIntakeError,
    TaskIntakeRejected,
    TaskIntakeRequest,
    _make_task_id,
)


def accept_task(request: TaskIntakeRequest) -> TaskIntakeAccepted | TaskIntakeRejected:
    """Accept or reject a task intake request.

    Parameters
    ----------
    request
        The task submission request.

    Returns
    -------
    TaskIntakeAccepted or TaskIntakeRejected
        Accepted response with a deterministic task id, or
        rejected response with a structured reason.
    """
    prompt = request.prompt

    if not prompt or not prompt.strip():
        return TaskIntakeRejected(
            reason="Prompt must not be blank.",
            error_code=TaskIntakeError.BLANK_PROMPT,
        )

    if len(prompt) > MAX_PROMPT_LENGTH:
        return TaskIntakeRejected(
            reason=f"Prompt must be at most {MAX_PROMPT_LENGTH} characters, got {len(prompt)}.",
            error_code=TaskIntakeError.OVERSIZED_PROMPT,
        )

    task_id = _make_task_id(prompt)
    return TaskIntakeAccepted(task_id=task_id)


# ---------------------------------------------------------------------------
# Runtime config
# ---------------------------------------------------------------------------

_ROUTES = [
    "/health",
    "/submit",
    "/task-intake/submit",
    "/task-intake/normalize",
    "/context/preview",
    "/runs",
    "/mock-loop",
    "/runs/execute",
]


def build_runtime_config(argv: list[str] | None = None) -> dict:
    """Build a deterministic runtime config dict from CLI arguments.

    Parameters
    ----------
    argv
        Command-line arguments (default: ``sys.argv[1:]``).

    Returns
    -------
    dict
        A deterministic config dict with host, port, and check mode flag.
    """
    parser = argparse.ArgumentParser(description="Ariadne local app runtime")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--check", action="store_true", help="Print config as JSON and exit")
    parser.add_argument("--json", action="store_true", help="Format output as JSON")

    args = parser.parse_args(argv)

    return {
        "service": "task_intake",
        "host": args.host,
        "port": args.port if isinstance(args.port, int) else 8000,
        "check": args.check,
        "routes": list(_ROUTES),
        "dependencies": ["uvicorn"],
        "default_adapter": "noop",
        "status": "ready" if args.check else "configured",
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Local app runtime entrypoint.

    Parameters
    ----------
    argv
        Command-line arguments (default: ``sys.argv[1:]``).

    Returns
    -------
    int
        Exit code (0 = success).
    """
    config = build_runtime_config(argv)

    if config.get("check"):
        print(json.dumps(config, indent=2, sort_keys=True))
        return 0

    host = config["host"]
    port = config["port"]

    try:
        import uvicorn
        from task_intake.server import app as server_app

        print(f"Ariadne running at http://{host}:{port}")
        uvicorn.run(server_app, host=host, port=port)
        return 0
    except ImportError:
        print("uvicorn is required: pip install uvicorn", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())

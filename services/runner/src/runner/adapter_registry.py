"""
Runner adapter registry / dispatcher — deterministic selection layer.

Maps explicit request fields to an approved adapter implementation.

For PR 0070, the only supported adapter is the no-op adapter from PR 0069.

No plugin discovery, no dynamic imports, no filesystem access, no subprocess.
"""

from __future__ import annotations

from typing import Any

from runner.noop_adapter import run_noop_execution
from runner.docker_agent_adapter import run_docker_agent_execution


# ---------------------------------------------------------------------------
# Supported adapter registry
# ---------------------------------------------------------------------------

# Static mapping: (substring_key, adapter_function)
# Selection checks if requested_adapter.lower() contains the key.
_ADAPTERS: list[tuple[str, Any]] = [
    ("noop", run_noop_execution),
    ("docker", run_docker_agent_execution),
]


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------


def _dispatcher_error(
    code: str,
    message: str,
    execution_request_id: str = "",
    run_id: str = "",
) -> dict:
    return {
        "execution_result_id": "",
        "execution_request_id": execution_request_id,
        "run_id": run_id,
        "status": "failed",
        "adapter": "dispatcher",
        "artifacts": [],
        "evidence": [],
        "errors": [
            {
                "code": code,
                "message": message,
            },
        ],
        "warnings": [],
        "review_required": False,
        "next": "",
    }


# ---------------------------------------------------------------------------
# Supported adapters
# ---------------------------------------------------------------------------


def get_supported_adapters() -> dict:
    """Return a deterministic dict of supported adapter identifiers.

    Returns
    -------
    dict
        A dict keyed by adapter id, with version and supported modes.
    """
    return {
        "noop": {
            "version": "v1",
            "modes": ["dry_run", "preview"],
        },
        "docker-agent": {
            "version": "v1",
            "modes": ["dry_run", "execute", "preview"],
        },
    }


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def dispatch_execution(execution_request: dict) -> dict:
    """Dispatch an execution request to the appropriate runner adapter.

    Parameters
    ----------
    execution_request
        A RunnerExecutionRequest dict (PR 0068 contract).

    Returns
    -------
    dict
        A RunnerExecutionResult dict from the selected adapter.
    """
    # --- Validate input type ---
    if not isinstance(execution_request, dict):
        return _dispatcher_error(
            code="invalid_request",
            message="Request must be a dict.",
        )

    requested_adapter = execution_request.get("requested_adapter", "")
    execution_request_id = execution_request.get("execution_request_id", "")
    run_id = execution_request.get("run_id", "")

    # --- Find adapter ---
    adapter_fn: Any = None
    for key, fn in _ADAPTERS:
        if key in requested_adapter.lower():
            adapter_fn = fn
            break

    if adapter_fn is None:
        supported = list(get_supported_adapters().keys())
        return _dispatcher_error(
            code="unsupported_adapter",
            message=(
                f"Unsupported adapter: {requested_adapter!r}. "
                f"Supported adapters: {supported}."
            ),
            execution_request_id=execution_request_id,
            run_id=run_id,
        )

    # --- Dispatch to adapter ---
    result = adapter_fn(execution_request)

    # Pass through — do not modify adapter result.
    return result

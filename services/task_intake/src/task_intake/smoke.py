"""Task Intake HTTP smoke/demo command.

Usage::

    python -m task_intake.smoke --base-url http://127.0.0.1:8001

Smoke/demo is intake-only.  It does not invoke the runner, create runner
requests, orchestrate agents, execute tasks, create ``run_record.yml``,
or write to ``.ariadne/**``.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _request_json(
    base_url: str,
    method: str,
    path: str,
    body: dict | None = None,
) -> tuple[int, dict] | tuple[int, str]:
    """Send an HTTP request and return (status_code, parsed_json_or_error)."""
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
            return status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            return exc.code, json.loads(raw)  # type: ignore[return-value]
        except (json.JSONDecodeError, ValueError):
            return exc.code, raw
    except urllib.error.URLError as exc:
        return 0, str(exc.reason)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_health(base_url: str) -> tuple[bool, str]:
    """Check ``GET /health`` and return (ok, message)."""
    status, data = _request_json(base_url, "GET", "/health")
    if status == 200 and isinstance(data, dict) and data.get("status") == "ok":
        return True, "ok"
    return False, f"expected status=ok, got status={status!r} data={data!r}"


def check_submit_accepted(base_url: str) -> tuple[bool, str]:
    """Check ``POST /submit`` with a valid prompt and return (ok, message)."""
    status, data = _request_json(
        base_url, "POST", "/submit",
        body={"prompt": "Fix the login bug"},
    )
    if (
        status == 200
        and isinstance(data, dict)
        and data.get("status") == "accepted"
        and isinstance(data.get("task_id"), str)
        and data["task_id"].startswith("task_")
    ):
        return True, data["task_id"]
    return False, f"expected accepted, got status={status!r} data={data!r}"


def check_blank_prompt_rejected(base_url: str) -> tuple[bool, str]:
    """Check ``POST /submit`` with a blank prompt and return (ok, message)."""
    status, data = _request_json(
        base_url, "POST", "/submit",
        body={"prompt": ""},
    )
    if (
        status == 200
        and isinstance(data, dict)
        and data.get("status") == "rejected"
        and isinstance(data.get("error_code"), str)
        and data["error_code"] == "blank_prompt"
    ):
        return True, data["error_code"]
    return False, f"expected rejected/blank_prompt, got status={status!r} data={data!r}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the smoke/demo checks.

    Parameters
    ----------
    argv
        Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns
    -------
    int
        Exit code (0 = all checks passed, 1 = any check failed).
    """
    parser = argparse.ArgumentParser(
        description="Task Intake HTTP smoke/demo",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8001",
        help="Base URL of the running Task Intake server (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    base_url = args.base_url
    ok_count = 0
    fail_count = 0

    # Health check
    ok, msg = check_health(base_url)
    if ok:
        print(f"health: {msg}")
        ok_count += 1
    else:
        print(f"health: FAILED — {msg}")
        fail_count += 1

    # Submit accepted
    ok, msg = check_submit_accepted(base_url)
    if ok:
        print(f"submit accepted: {msg}")
        ok_count += 1
    else:
        print(f"submit accepted: FAILED — {msg}")
        fail_count += 1

    # Blank prompt rejected
    ok, msg = check_blank_prompt_rejected(base_url)
    if ok:
        print(f"blank prompt rejected: {msg}")
        ok_count += 1
    else:
        print(f"blank prompt rejected: FAILED — {msg}")
        fail_count += 1

    if fail_count == 0:
        print("smoke: ok")
        return 0

    print(f"smoke: FAILED — {fail_count} check(s) failed")
    return 1


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())

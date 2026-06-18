"""Doctor callable for Task Intake health check."""

from __future__ import annotations


def doctor() -> dict[str, str]:
    """Return the health status of the Task Intake service.

    Returns
    -------
    dict
        A dictionary with ``service`` and ``status`` keys.
    """
    return {
        "service": "task_intake",
        "status": "ok",
    }

"""Task Intake HTTP server — FastAPI application.

Exposes the Task Intake service via HTTP endpoints.
This is intake-only.  It does not invoke the runner, orchestrate agents,
create run records, or write to ``.ariadne/**``.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from task_intake.app import accept_task
from task_intake.doctor import doctor
from task_intake.models import TaskIntakeRequest

app = FastAPI(
    title="Task Intake API",
    description="Intake-only service. Does not execute tasks or invoke the runner.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class SubmitRequest(BaseModel):
    """JSON body for the /submit endpoint."""

    prompt: str
    title: str | None = Field(default=None, description="Optional short title")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns
    -------
    dict
        JSON with ``service`` and ``status`` keys.
    """
    return dict(doctor())


@app.post("/submit")
async def submit(body: SubmitRequest) -> dict[str, str | list[str]]:
    """Submit a task for intake.

    Parameters
    ----------
    body
        JSON body with ``prompt`` (required) and optional ``title``.

    Returns
    -------
    dict
        Accepted: ``{"status": "accepted", "task_id": "task_..."}``
        Rejected: ``{"status": "rejected", "reason": "...", "error_code": "..."}``
    """
    result = accept_task(TaskIntakeRequest(prompt=body.prompt))

    if result.status.value == "accepted":
        return {
            "status": "accepted",
            "task_id": result.task_id,
        }
    else:
        return {
            "status": "rejected",
            "reason": result.reason,
            "error_code": result.error_code.value if result.error_code else "",
        }


@app.post("/task-intake/submit")
async def submit_alias(body: SubmitRequest) -> dict[str, str | list[str]]:
    """Alias for :func:`submit`."""
    return await submit(body)

"""Task Intake app callable — accept_task."""

from __future__ import annotations

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

    Notes
    -----
    This function is a pure validation boundary.  It does **not**:
    - invoke the runner
    - orchestrate agents
    - call subprocess, Docker, or git
    - write files
    - make network requests
    - write to ``.ariadne/**``
    - create ``run_record.yml``
    """
    prompt = request.prompt

    # --- Blank / empty prompt ---
    if not prompt or not prompt.strip():
        return TaskIntakeRejected(
            reason="Prompt must not be blank.",
            error_code=TaskIntakeError.BLANK_PROMPT,
        )

    # --- Oversized prompt ---
    if len(prompt) > MAX_PROMPT_LENGTH:
        return TaskIntakeRejected(
            reason=(
                f"Prompt must be at most {MAX_PROMPT_LENGTH} characters, "
                f"got {len(prompt)}."
            ),
            error_code=TaskIntakeError.OVERSIZED_PROMPT,
        )

    # --- Accepted ---
    task_id = _make_task_id(prompt)
    return TaskIntakeAccepted(task_id=task_id)

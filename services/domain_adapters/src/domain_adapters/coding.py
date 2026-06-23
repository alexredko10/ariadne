"""
Coding Domain Adapter — minimal deterministic adapter for the coding domain.

Conforms to the Ariadne Domain Adapter Contract (``.project-memory/domain-adapter.schema.yml``).

No model calls, no Git operations, no code execution, no filesystem access.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Constants — contract-aligned policy data
# ---------------------------------------------------------------------------

_ADAPTER_ID = "coding-v1"
_DOMAIN = "coding"
_DESCRIPTION = "Standard coding adapter for source code changes."

_VALID_INTENTS = frozenset({"inspect", "plan", "implement", "review"})

_INTENT_ACTIONS: dict[str, list[str]] = {
    "inspect": ["read_target_files", "analyze_structure", "report_findings"],
    "plan": ["read_target_files", "analyze_structure", "design_changes", "propose_plan"],
    "implement": ["read_target_files", "apply_changes", "run_validation", "report_results"],
    "review": ["read_target_files", "analyze_changes", "check_quality", "report_review"],
}

_DEFAULT_ACTIONS = ["analyze_request", "determine_actions"]

_CAPABILITIES: list[dict[str, str]] = [
    {"id": "apply_patch", "description": "Apply normalized patches to the working tree."},
    {"id": "normalize_diff", "description": "Normalize raw diffs into runnable patches."},
    {"id": "run_tests", "description": "Execute domain-appropriate validation commands."},
    {"id": "detect_generated_artifacts", "description": "Identify generated or stale artifacts."},
]

ALLOWED_WRITE_PATHS: list[str] = ["services/**", "packages/**", "tests/**"]
FORBIDDEN_WRITE_PATHS: list[str] = [".git/**", ".env", "secrets/**"]
VALIDATION_COMMANDS: list[str] = ["python -m pytest -q"]
EXECUTION_ENVIRONMENT: str = "worktree"

APPLY_MECHANISM: dict[str, Any] = {
    "mechanism": "git_apply",
    "description": "Apply patch via git apply after human approval.",
    "git_based": True,
    "requires_human_apply": True,
}

ROLLBACK_MECHANISM: dict[str, Any] = {
    "mechanism": "git_reset",
    "description": "Reset worktree to snapshot.",
    "git_based": True,
    "manual_rollback_required": False,
}

RISKS: list[dict[str, str]] = [
    {
        "id": "uncommitted_changes_lost",
        "description": "Uncommitted changes may be lost on rollback.",
        "severity": "medium",
    },
]

STOP_CONDITIONS: list[dict[str, str]] = [
    {
        "id": "validation_failed",
        "description": "Validation must pass before apply.",
        "severity": "critical",
    },
]

HUMAN_APPROVAL_POLICY: str = (
    "Apply requires explicit human approval. "
    "Rollback may be automatic for recoverable states."
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class CodingAdapterError(Exception):
    """Raised when a coding adapter operation cannot be completed.

    Attributes
    ----------
    operation
        The adapter operation that failed.
    subject
        The subject of the operation.
    reason
        Human-readable explanation.
    """

    def __init__(
        self,
        operation: str,
        subject: str,
        reason: str,
    ) -> None:
        self.operation = operation
        self.subject = subject
        self.reason = reason
        super().__init__(
            f"Coding adapter error on {operation}({subject}): {reason}"
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class CodingDomainAdapter:
    """Minimal deterministic Coding Domain Adapter.

    Provides contract-aligned identity, capabilities, request validation,
    and dry-run planning.  No model calls, no Git, no filesystem access.
    """

    adapter_id: str = _ADAPTER_ID
    domain: str = _DOMAIN
    description: str = _DESCRIPTION

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    def describe(self) -> dict[str, str]:
        """Return adapter identity metadata.

        Returns
        -------
        dict
            A dict with ``adapter_id``, ``domain``, and ``description``.
        """
        return {
            "adapter_id": self.adapter_id,
            "domain": self.domain,
            "description": self.description,
        }

    def describe_capabilities(self) -> list[dict[str, str]]:
        """Return the list of capabilities supported by this adapter.

        Returns
        -------
        list[dict]
            Each entry has ``id`` and ``description``.
        """
        return list(_CAPABILITIES)

    # ------------------------------------------------------------------
    # Request validation
    # ------------------------------------------------------------------

    def validate_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Validate a coding adapter request.

        Parameters
        ----------
        request
            The request dict to validate.

        Returns
        -------
        dict
            A validated request with ``valid: True`` and normalized fields.

        Raises
        ------
        CodingAdapterError
            If the request is invalid.
        """
        if not isinstance(request, dict):
            raise CodingAdapterError(
                operation="validate_request",
                subject="request",
                reason="Request must be a dict.",
            )

        task_id = request.get("task_id")
        if not task_id or not isinstance(task_id, str):
            raise CodingAdapterError(
                operation="validate_request",
                subject="task_id",
                reason="task_id is required and must be a non-empty string.",
            )

        intent = request.get("intent")
        if not intent or not isinstance(intent, str):
            raise CodingAdapterError(
                operation="validate_request",
                subject="intent",
                reason="intent is required and must be a non-empty string.",
            )
        if intent not in _VALID_INTENTS:
            raise CodingAdapterError(
                operation="validate_request",
                subject="intent",
                reason=(
                    f"Invalid intent: {intent!r}. "
                    f"Must be one of: {sorted(_VALID_INTENTS)}."
                ),
            )

        target_paths = request.get("target_paths")
        if not isinstance(target_paths, list) or not target_paths:
            raise CodingAdapterError(
                operation="validate_request",
                subject="target_paths",
                reason="target_paths is required and must be a non-empty list of strings.",
            )

        constraints = request.get("constraints")
        if constraints is not None:
            if not isinstance(constraints, list):
                raise CodingAdapterError(
                    operation="validate_request",
                    subject="constraints",
                    reason="constraints must be a list of strings if provided.",
                )

        return {
            "valid": True,
            "task_id": task_id,
            "intent": intent,
            "target_paths": sorted(target_paths),
            "constraints": sorted(constraints) if constraints else [],
        }

    # ------------------------------------------------------------------
    # Dry-run planning
    # ------------------------------------------------------------------

    def plan_dry_run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Produce a deterministic dry-run preview for a validated request.

        Parameters
        ----------
        request
            A validated request dict (caller should validate first).

        Returns
        -------
        dict
            A deterministic preview of adapter behavior.
        """
        # Validate first
        validated = self.validate_request(request)

        actions = _INTENT_ACTIONS.get(validated["intent"], _DEFAULT_ACTIONS)

        return {
            "adapter_id": self.adapter_id,
            "domain": self.domain,
            "task_id": validated["task_id"],
            "intent": validated["intent"],
            "target_paths": list(validated["target_paths"]),
            "constraints": list(validated["constraints"]),
            "planned_actions": list(actions),
            "side_effects": [],
            "requires_human_approval": False,
            "model_required": False,
            "validation_commands": list(VALIDATION_COMMANDS),
        }

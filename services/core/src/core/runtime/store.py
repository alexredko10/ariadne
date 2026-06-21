"""
Ariadne runtime in-memory store — holds runs, steps, checkpoints, evidence,
and final reports across operations.

In-memory only.  No persistence, no database, no filesystem, no network.
"""

from __future__ import annotations

import copy
from typing import Any

from core.runtime_substrate import (
    FinalReportDraft,
    RunState,
)
from core.runtime.verification import (
    VerificationEvidence,
    attach_verification_evidence as _verify_attach,
    build_final_report as _verify_build_report,
    get_evidence_for_run as _verify_get_evidence,
    summarize_verification_evidence as _verify_summarize,
    validate_final_report_readiness as _verify_validate_readiness,
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class RuntimeStoreError(Exception):
    """Raised when a store operation cannot be completed.

    Attributes
    ----------
    operation
        The store operation that failed.
    subject
        The subject of the operation (e.g. run_id).
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
            f"Store error on {operation}({subject}): {reason}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deep_copy_run(run: RunState) -> RunState:
    """Create a fully independent deep copy via serialization round-trip."""
    return RunState.from_dict(run.to_dict())


# ---------------------------------------------------------------------------
# InMemoryRuntimeStore
# ---------------------------------------------------------------------------


class InMemoryRuntimeStore:
    """In-memory store for Ariadne runtime objects.

    Dict-backed by ``run_id``.  Insertion order preserved for ``list_runs``.
    Deep copy via serialization round-trip for ``get_run`` and ``list_runs``.
    Separate evidence dict per instance (isolated from ``verification.py``).
    """

    def __init__(self) -> None:
        self._runs: dict[str, RunState] = {}
        self._evidence: dict[str, list[VerificationEvidence]] = {}

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def create_run(self, run: RunState) -> RunState:
        """Store a new run.

        Parameters
        ----------
        run
            The run to store.

        Returns
        -------
        RunState
            The stored copy of the run.

        Raises
        ------
        RuntimeStoreError
            If ``run_id`` is empty or a duplicate.
        """
        if not run.run_id:
            raise RuntimeStoreError(
                operation="create_run",
                subject="",
                reason="run_id must not be empty.",
            )
        if run.run_id in self._runs:
            raise RuntimeStoreError(
                operation="create_run",
                subject=run.run_id,
                reason=f"Duplicate run_id: {run.run_id!r}.",
            )
        stored = _deep_copy_run(run)
        self._runs[run.run_id] = stored
        self._evidence[run.run_id] = []
        return stored

    def get_run(self, run_id: str) -> RunState:
        """Return a deep copy of the run identified by *run_id*.

        Parameters
        ----------
        run_id
            The run identifier.

        Returns
        -------
        RunState
            A deep copy of the stored run.

        Raises
        ------
        RuntimeStoreError
            If *run_id* is not found.
        """
        if run_id not in self._runs:
            raise RuntimeStoreError(
                operation="get_run",
                subject=run_id,
                reason=f"Run not found: {run_id!r}.",
            )
        return _deep_copy_run(self._runs[run_id])

    def has_run(self, run_id: str) -> bool:
        """Return whether *run_id* exists in the store."""
        return run_id in self._runs

    def save_run(self, run: RunState) -> RunState:
        """Replace the stored run with *run* (upsert by run_id).

        Parameters
        ----------
        run
            The run to store.

        Returns
        -------
        RunState
            The stored run.

        Raises
        ------
        RuntimeStoreError
            If *run.run_id* is not found (create must precede save).
        """
        if run.run_id not in self._runs:
            raise RuntimeStoreError(
                operation="save_run",
                subject=run.run_id,
                reason=f"Run not found: {run.run_id!r}. Use create_run first.",
            )
        # Store the caller-provided object directly — caller is responsible
        # for state validity.
        self._runs[run.run_id] = run
        return run

    def list_runs(self) -> list[RunState]:
        """Return a list of all runs in insertion order (deep copies)."""
        return [_deep_copy_run(r) for r in self._runs.values()]

    def delete_run(self, run_id: str) -> None:
        """Delete a run and its associated evidence.

        Parameters
        ----------
        run_id
            The run identifier to delete.

        Raises
        ------
        RuntimeStoreError
            If *run_id* is not found.
        """
        if run_id not in self._runs:
            raise RuntimeStoreError(
                operation="delete_run",
                subject=run_id,
                reason=f"Run not found: {run_id!r}.",
            )
        del self._runs[run_id]
        self._evidence.pop(run_id, None)

    # ------------------------------------------------------------------
    # Evidence convenience methods
    # ------------------------------------------------------------------

    def attach_verification_evidence(
        self,
        run_id: str,
        evidence: VerificationEvidence,
    ) -> None:
        """Attach *evidence* to the run identified by *run_id*.

        Delegates to ``verification.attach_verification_evidence`` using
        the store's internal evidence dict.
        """
        run = self.get_run(run_id)
        import core.runtime.verification as _vmod
        _old = _vmod._run_evidence_store
        _vmod._run_evidence_store = self._evidence
        try:
            _verify_attach(run, evidence)
        finally:
            _vmod._run_evidence_store = _old

    def get_evidence_for_run(
        self,
        run_id: str,
    ) -> list[VerificationEvidence]:
        """Return evidence attached to *run_id*."""
        return list(self._evidence.get(run_id, []))

    def summarize_verification_evidence(
        self,
        run_id: str,
    ) -> dict[str, Any]:
        """Summarize verification evidence for *run_id*.

        Delegates to ``verification.summarize_verification_evidence`` using
        the store's internal evidence dict.
        """
        run = self.get_run(run_id)
        # Temporarily populate the verification module's evidence dict
        # with store's evidence so summarization has data to work with.
        # We use a trick: replace the module-level dict, call summarize,
        # then restore.
        import core.runtime.verification as _vmod
        _old = _vmod._run_evidence_store  # noqa
        _vmod._run_evidence_store = self._evidence  # noqa
        try:
            result = _verify_summarize(run)
        finally:
            _vmod._run_evidence_store = _old
        return result

    def build_final_report(self, run_id: str) -> FinalReportDraft:
        """Build a final report for *run_id*.

        Delegates to ``verification.build_final_report`` using the
        store's internal evidence dict.
        """
        run = self.get_run(run_id)
        import core.runtime.verification as _vmod
        _old = _vmod._run_evidence_store
        _vmod._run_evidence_store = self._evidence
        try:
            report = _verify_build_report(run)
        finally:
            _vmod._run_evidence_store = _old
        return report

    def validate_final_report_readiness(self, run_id: str) -> None:
        """Validate that *run_id* is ready for a final report.

        Delegates to ``verification.validate_final_report_readiness``.
        """
        run = self.get_run(run_id)
        import core.runtime.verification as _vmod
        _old = _vmod._run_evidence_store
        _vmod._run_evidence_store = self._evidence
        try:
            _verify_validate_readiness(run)
        finally:
            _vmod._run_evidence_store = _old

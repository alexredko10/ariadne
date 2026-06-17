"""
Content-addressed artifact store for runner evidence artifacts.

All artifacts are stored by lowercase hex sha256 under a caller-provided
store root.  The store is evidence storage only — artifact presence does
not authorise canonical repository mutation.

See PLAN.md for full contract.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ArtifactKind(str, enum.Enum):
    """Well-known artifact kinds produced by the runner."""

    RAW_DIFF = "raw_diff"
    NORMALIZED_PATCH = "normalized_patch"
    APPLY_REQUEST = "apply_request"
    RUN_RECORD_SNAPSHOT = "run_record_snapshot"
    GENERIC_TEXT = "generic_text"
    GENERIC_JSON = "generic_json"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ArtifactWriteResult:
    """Result of a successful artifact write operation."""

    sha256: str
    path: str
    metadata_path: str
    kind: str
    size_bytes: int


@dataclasses.dataclass(frozen=True)
class ArtifactRecord:
    """Metadata record for a stored artifact."""

    sha256: str
    kind: str
    media_type: str
    size_bytes: int
    path: str
    metadata_path: str


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ArtifactStoreError(ValueError):
    """Raised when an unsafe or invalid operation is attempted."""


class ArtifactNotFoundError(FileNotFoundError):
    """Raised when an artifact sha256 is not found in the store."""


# ---------------------------------------------------------------------------
# ArtifactStore
# ---------------------------------------------------------------------------


class ArtifactStore:
    """Content-addressed artifact store.

    All artifacts are stored under *root* using the deterministic layout::

        <root>/sha256/<first2>/<full_sha256>/artifact.bin
        <root>/sha256/<first2>/<full_sha256>/metadata.json

    The store is evidence storage only.  Artifact presence does not
    authorise canonical repository mutation.
    """

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    @property
    def root(self) -> Path:
        """The resolved store root directory."""
        return self._root

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def put_bytes(
        self,
        kind: ArtifactKind | str,
        content: bytes,
        *,
        media_type: str | None = None,
    ) -> ArtifactWriteResult:
        """Store *content* as a binary artifact of the given *kind*.

        Parameters
        ----------
        kind
            An ``ArtifactKind`` member or a free-form string.
        content
            Arbitrary byte content to store.
        media_type
            Optional media type (e.g. ``"application/octet-stream"``).
            If ``None``, defaults to ``"application/octet-stream"`` for bytes.

        Returns
        -------
        ArtifactWriteResult
            Metadata about the stored artifact.

        Raises
        ------
        ArtifactStoreError
            If the sha256 is malformed or path is unsafe.
        """
        sha256 = _sha256_hex(content)
        kind_str = kind.value if isinstance(kind, ArtifactKind) else str(kind)
        return self._store(sha256, kind_str, content, media_type or "application/octet-stream")

    def put_text(
        self,
        kind: ArtifactKind | str,
        text: str,
        *,
        media_type: str = "text/plain; charset=utf-8",
    ) -> ArtifactWriteResult:
        """Store *text* as a text artifact of the given *kind*.

        Parameters
        ----------
        kind
            An ``ArtifactKind`` member or a free-form string.
        text
            Unicode text to store (encoded as UTF-8).
        media_type
            Media type string (default ``"text/plain; charset=utf-8"``).

        Returns
        -------
        ArtifactWriteResult
            Metadata about the stored artifact.

        Raises
        ------
        ArtifactStoreError
            If the sha256 is malformed or path is unsafe.
        """
        content = text.encode("utf-8")
        sha256 = _sha256_hex(content)
        kind_str = kind.value if isinstance(kind, ArtifactKind) else str(kind)
        return self._store(sha256, kind_str, content, media_type)

    def read_record(self, sha256: str) -> ArtifactRecord:
        """Read artifact metadata for *sha256*.

        Parameters
        ----------
        sha256
            Lowercase hex sha256 of the artifact.

        Returns
        -------
        ArtifactRecord
            The stored metadata.

        Raises
        ------
        ArtifactNotFoundError
            If the artifact does not exist.
        """
        metadata_path = self._resolve_metadata_path(sha256)
        if not metadata_path.exists():
            raise ArtifactNotFoundError(
                f"Artifact not found for sha256: {sha256}"
            )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return ArtifactRecord(
            sha256=metadata["sha256"],
            kind=metadata["kind"],
            media_type=metadata["media_type"],
            size_bytes=metadata["size_bytes"],
            path=metadata["path"],
            metadata_path=metadata["metadata_path"],
        )

    def read_bytes(self, sha256: str) -> bytes:
        """Read the raw byte content of an artifact.

        Parameters
        ----------
        sha256
            Lowercase hex sha256 of the artifact.

        Returns
        -------
        bytes
            The stored artifact content.

        Raises
        ------
        ArtifactNotFoundError
            If the artifact does not exist.
        """
        artifact_path = self._resolve_artifact_path(sha256)
        if not artifact_path.exists():
            raise ArtifactNotFoundError(
                f"Artifact not found for sha256: {sha256}"
            )
        return artifact_path.read_bytes()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _store(
        self,
        sha256: str,
        kind: str,
        content: bytes,
        media_type: str,
    ) -> ArtifactWriteResult:
        """Write *content* to the store and return its metadata."""
        self._validate_sha256(sha256)

        artifact_dir = self._artifact_dir(sha256)
        artifact_path = artifact_dir / "artifact.bin"
        metadata_path = artifact_dir / "metadata.json"

        # Idempotent: if both exist and sha matches, return existing record
        if artifact_path.exists() and metadata_path.exists():
            existing = json.loads(metadata_path.read_text(encoding="utf-8"))
            if existing.get("sha256") == sha256:
                # Ensure the store root in the metadata is current
                return ArtifactWriteResult(
                    sha256=sha256,
                    path=str(
                        artifact_path.relative_to(self._root)
                    ),
                    metadata_path=str(
                        metadata_path.relative_to(self._root)
                    ),
                    kind=kind,
                    size_bytes=len(content),
                )

        # Create the artifact directory
        artifact_dir.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file then rename
        tmp = artifact_dir / f".tmp_{sha256}"
        try:
            tmp.write_bytes(content)
            os.replace(str(tmp), str(artifact_path))
        finally:
            if tmp.exists():
                tmp.unlink()

        # Write metadata
        metadata = {
            "sha256": sha256,
            "kind": kind,
            "media_type": media_type,
            "size_bytes": len(content),
            "path": str(artifact_path.relative_to(self._root)),
            "metadata_path": str(metadata_path.relative_to(self._root)),
        }
        tmp_meta = artifact_dir / f".tmp_meta_{sha256}"
        try:
            tmp_meta.write_text(
                json.dumps(metadata, sort_keys=True), encoding="utf-8"
            )
            os.replace(str(tmp_meta), str(metadata_path))
        finally:
            if tmp_meta.exists():
                tmp_meta.unlink()

        return ArtifactWriteResult(
            sha256=sha256,
            path=str(artifact_path.relative_to(self._root)),
            metadata_path=str(metadata_path.relative_to(self._root)),
            kind=kind,
            size_bytes=len(content),
        )

    def _artifact_dir(self, sha256: str) -> Path:
        """Return the deterministic directory for a sha256.

        All containment checks happen here via ``resolve()``.
        """
        first_two = sha256[:2]
        candidate = (self._root / "sha256" / first_two / sha256).resolve()

        # Reject resolve escaping store root
        if not str(candidate).startswith(str(self._root)):
            raise ArtifactStoreError(
                f"Resolved artifact path escapes store root: {candidate}"
            )

        return candidate

    def _resolve_artifact_path(self, sha256: str) -> Path:
        """Resolve the artifact file path, rejecting unsafe inputs."""
        self._validate_sha256(sha256)
        candidate = (self._root / "sha256" / sha256[:2] / sha256 / "artifact.bin").resolve()
        if not str(candidate).startswith(str(self._root)):
            raise ArtifactStoreError(
                f"Resolved artifact path escapes store root: {candidate}"
            )
        return candidate

    def _resolve_metadata_path(self, sha256: str) -> Path:
        """Resolve the metadata file path, rejecting unsafe inputs."""
        self._validate_sha256(sha256)
        candidate = (self._root / "sha256" / sha256[:2] / sha256 / "metadata.json").resolve()
        if not str(candidate).startswith(str(self._root)):
            raise ArtifactStoreError(
                f"Resolved metadata path escapes store root: {candidate}"
            )
        return candidate

    @staticmethod
    def _validate_sha256(sha256: str) -> None:
        """Reject malformed sha256 strings."""
        if not _SHA256_RE.match(sha256):
            raise ArtifactStoreError(
                f"sha256 must be lowercase 64-char hex, got: {sha256!r}"
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_hex(content: bytes) -> str:
    """Return the lowercase hex sha256 of *content*."""
    return hashlib.sha256(content).hexdigest()

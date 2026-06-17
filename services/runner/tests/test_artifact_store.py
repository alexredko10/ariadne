"""Tests for the content-addressed artifact store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.artifacts import (
    ArtifactKind,
    ArtifactNotFoundError,
    ArtifactRecord,
    ArtifactStore,
    ArtifactStoreError,
    ArtifactWriteResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> ArtifactStore:
    """A fresh ArtifactStore rooted at a temporary directory."""
    return ArtifactStore(tmp_path / "artifact_root")


# ---------------------------------------------------------------------------
# put_text
# ---------------------------------------------------------------------------


class TestPutText:
    def test_creates_artifact_and_metadata(self, store: ArtifactStore):
        result = store.put_text(ArtifactKind.GENERIC_TEXT, "hello world")
        assert result.sha256 == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        assert result.kind == "generic_text"
        assert result.size_bytes == 11

        # Verify paths exist
        assert (store.root / result.path).exists()
        assert (store.root / result.metadata_path).exists()

    def test_metadata_content(self, store: ArtifactStore):
        result = store.put_text(ArtifactKind.GENERIC_TEXT, "hello")
        meta = json.loads((store.root / result.metadata_path).read_text(encoding="utf-8"))
        assert meta["sha256"] == result.sha256
        assert meta["kind"] == "generic_text"
        assert meta["size_bytes"] == 5
        assert meta["path"] == result.path
        assert meta["media_type"] == "text/plain; charset=utf-8"


# ---------------------------------------------------------------------------
# put_bytes
# ---------------------------------------------------------------------------


class TestPutBytes:
    def test_creates_artifact_and_metadata(self, store: ArtifactStore):
        content = b"\x00\x01\x02"
        result = store.put_bytes(ArtifactKind.RAW_DIFF, content)
        assert result.sha256 == "ae4b3280e56e2faf83f414a6e3dabe9d5fbe18976544c05fed121accb85b53fc"
        assert result.kind == "raw_diff"
        assert result.size_bytes == 3

    def test_binary_content_roundtrip(self, store: ArtifactStore):
        original = b"\xff\xfe\x00\x01\x02\x03"
        result = store.put_bytes(ArtifactKind.RAW_DIFF, original)
        retrieved = store.read_bytes(result.sha256)
        assert retrieved == original

    def test_media_type_default(self, store: ArtifactStore):
        result = store.put_bytes(ArtifactKind.RAW_DIFF, b"data")
        meta = json.loads((store.root / result.metadata_path).read_text(encoding="utf-8"))
        assert meta["media_type"] == "application/octet-stream"

    def test_custom_media_type(self, store: ArtifactStore):
        result = store.put_bytes(
            ArtifactKind.RAW_DIFF, b"data", media_type="text/x-diff"
        )
        meta = json.loads((store.root / result.metadata_path).read_text(encoding="utf-8"))
        assert meta["media_type"] == "text/x-diff"


# ---------------------------------------------------------------------------
# Determinism and idempotency
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_content_same_sha256(self, store: ArtifactStore):
        r1 = store.put_text(ArtifactKind.GENERIC_TEXT, "same text")
        r2 = store.put_text(ArtifactKind.GENERIC_TEXT, "same text")
        assert r1.sha256 == r2.sha256

    def test_same_content_and_kind_are_idempotent(self, store: ArtifactStore):
        r1 = store.put_text(ArtifactKind.GENERIC_TEXT, "idempotent")
        r2 = store.put_text(ArtifactKind.GENERIC_TEXT, "idempotent")
        # Both calls return valid results
        assert r1.sha256 == r2.sha256
        # Second call does not raise

    def test_different_content_different_sha256(self, store: ArtifactStore):
        r1 = store.put_text(ArtifactKind.GENERIC_TEXT, "content a")
        r2 = store.put_text(ArtifactKind.GENERIC_TEXT, "content b")
        assert r1.sha256 != r2.sha256

    def test_deterministic_metadata_json(self, store: ArtifactStore):
        result = store.put_text(ArtifactKind.GENERIC_TEXT, "deterministic")
        raw = (store.root / result.metadata_path).read_text(encoding="utf-8")
        # Expected: deterministic key order from sort_keys=True
        assert '"sha256"' in raw
        assert '"kind"' in raw
        assert '"size_bytes"' in raw
        # Re-parse and re-dump to verify deterministic representation
        parsed = json.loads(raw)
        re_dumped = json.dumps(parsed, sort_keys=True)
        assert raw == re_dumped


# ---------------------------------------------------------------------------
# read_bytes / read_record
# ---------------------------------------------------------------------------


class TestRead:
    def test_read_bytes_returns_original(self, store: ArtifactStore):
        text = "original content"
        result = store.put_text(ArtifactKind.GENERIC_TEXT, text)
        retrieved = store.read_bytes(result.sha256)
        assert retrieved.decode("utf-8") == text

    def test_read_record_returns_metadata(self, store: ArtifactStore):
        result = store.put_text(ArtifactKind.GENERIC_TEXT, "metadata test")
        record = store.read_record(result.sha256)
        assert isinstance(record, ArtifactRecord)
        assert record.sha256 == result.sha256
        assert record.kind == "generic_text"
        assert record.size_bytes == 13
        assert record.path == result.path
        assert record.metadata_path == result.metadata_path

    def test_read_record_unknown_sha_raises(self, store: ArtifactStore):
        unknown = "a" * 64
        with pytest.raises(ArtifactNotFoundError):
            store.read_record(unknown)

    def test_read_bytes_unknown_sha_raises(self, store: ArtifactStore):
        unknown = "b" * 64
        with pytest.raises(ArtifactNotFoundError):
            store.read_bytes(unknown)


# ---------------------------------------------------------------------------
# Malformed sha rejection
# ---------------------------------------------------------------------------


class TestMalformedSha:
    @pytest.mark.parametrize(
        "bad_sha",
        [
            "",  # empty
            "abc",  # too short
            "gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg",  # invalid hex
            "abcdef",  # too short (6 chars)
            "ABCDEF0123456789abcdef0123456789ABCDEF0123456789abcdef0123456789",  # uppercase
            "a" * 63,  # 63 chars
            "a" * 65,  # 65 chars
            None,  # not a string
        ],
    )
    def test_malformed_sha_rejected_on_read(self, store: ArtifactStore, bad_sha):
        if bad_sha is None:
            with pytest.raises((TypeError, ArtifactStoreError)):
                store.read_bytes(bad_sha)  # type: ignore[arg-type]
        else:
            with pytest.raises(ArtifactStoreError):
                store.read_bytes(bad_sha)


# ---------------------------------------------------------------------------
# Path traversal rejection
# ---------------------------------------------------------------------------


class TestPathTraversal:
    def test_traversal_via_sha_rejected(self, store: ArtifactStore):
        # Attempt to resolve a sha that contains traversal patterns
        with pytest.raises(ArtifactStoreError, match="sha256"):
            store.read_bytes("../etc/passwd")

    def test_upward_traversal_rejected(self, store: ArtifactStore):
        with pytest.raises(ArtifactStoreError, match="sha256"):
            store.read_bytes("../../etc/passwd")


# ---------------------------------------------------------------------------
# Symlink safety
# ---------------------------------------------------------------------------


class TestSymlinkSafety:
    def test_symlink_under_store_root_rejected(self, store: ArtifactStore, tmp_path: Path):
        # Create a store root with a symlink inside it
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("stolen")

        # Create a symlink inside the store that points outside
        symlink_dir = store.root / "sha256" / "aa"
        symlink_dir.mkdir(parents=True, exist_ok=True)
        link = symlink_dir / "aaa"  # resolves to something that looks like a sha256 dir
        link.symlink_to(outside)

        # Attempting to read through the symlink should fail
        with pytest.raises((ArtifactStoreError, ArtifactNotFoundError)):
            store.read_bytes("aa" + "a" * 62)


# ---------------------------------------------------------------------------
# No writes outside tmp_path
# ---------------------------------------------------------------------------


class TestNoWritesOutsideRoot:
    def test_no_writes_outside_store_root(self, store: ArtifactStore, tmp_path: Path):
        result = store.put_text(ArtifactKind.GENERIC_TEXT, "inside")
        # All files should be under the store root
        for p in [store.root / result.path, store.root / result.metadata_path]:
            assert str(p.resolve()).startswith(str(store.root))


# ---------------------------------------------------------------------------
# Free-form strings as kinds
# ---------------------------------------------------------------------------


class TestFreeformKind:
    def test_accepts_string_kind(self, store: ArtifactStore):
        result = store.put_bytes("custom_kind", b"data")
        assert result.kind == "custom_kind"

    def test_accepts_string_kind_via_put_text(self, store: ArtifactStore):
        result = store.put_text("custom_text", "data")
        assert result.kind == "custom_text"

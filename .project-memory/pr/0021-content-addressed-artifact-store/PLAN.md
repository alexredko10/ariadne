# PR 0021: Content-addressed Artifact Store

## Goal

```text
Add a runner-local content-addressed artifact store for deterministic, hash-addressed storage of runner evidence artifacts without enabling canonical repository mutation.
```

## Context snapshot verified at plan time

```yaml
context_snapshot:
  base_sha: "68a0f652eef24dd77c63116ae7f4f49bb6e82a57"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.5"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "68a0f652eef24dd77c63116ae7f4f49bb6e82a57"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

## Snapshot policy

```text
PLAN.md base_sha is historical evidence from PLAN creation time.
Implementation and review should report snapshot deltas but must not block solely because current HEAD differs from PLAN.md base_sha, unless scope evidence shows unrelated or forbidden changes.
```

## Non-goals

```text
- no ApplyPatch implementation
- no HITL apply gate execution
- no canonical repository writes
- no git apply
- no git mutation commands by agents
- no Docker commands by agents
- no API server
- no frontend
- no automatic team runner
- no .ariadne/** namespace introduction
- no real run_record.yml backfill
- no secrets or credentials
- no workflow/GHCR/Dockerfile changes
```

## Future implementation allowed_write_paths

The implementation PR may modify/create only:

```text
services/runner/src/runner/artifacts.py
services/runner/tests/test_artifact_store.py
.project-memory/pr/0021-content-addressed-artifact-store/PLAN.md
```

Optional only if justified by import/export need:

```text
services/runner/src/runner/__init__.py
```

Do not modify memory schemas/contracts in this PR unless the PLAN explicitly finds a required metadata contract gap. Prefer code-only runner implementation.

## Future implementation forbidden_write_paths

Implementation must not modify:

```text
.project-memory/apply-gate.schema.yml
.project-memory/run-record.schema.yml
.project-memory/context-bundles/agent-config.yml
.project-memory/pr/*/run_record.yml
.ariadne/**
agents/**
services/conductor/**
services/core/**
services/model_gateway/**
services/task_intake/**
packages/**
apps/**
docs/**
.github/**
docker/**
Dockerfile*
prompts/**
pyproject.toml
package.json
Makefile
docker-compose.yml
.env
.env.*
```

## Required implementation design

Create a stdlib-only runner artifact store.

```text
services/runner/src/runner/artifacts.py
```

### Design concepts

```text
ArtifactStore
ArtifactRecord
ArtifactKind
ArtifactWriteResult
```

### Artifact kinds

Must include at minimum:

```text
raw_diff
normalized_patch
apply_request
run_record_snapshot
generic_text
generic_json
```

### Required behavior

```text
- content-addressed by sha256
- deterministic path layout
- stores artifacts under a caller-provided root
- does not write to canonical repo unless caller chooses a store root inside repo
- default tests must use tmp_path only
- refuses absolute artifact-relative paths
- refuses path traversal
- refuses symlinks
- writes bytes atomically where practical
- records content length
- records sha256
- records artifact kind
- records created_at optional or deterministic-test-friendly
- same content produces same sha256
- same content and kind are idempotent
- different content produces different sha256
- binary content supported
- no secrets scanning yet, but artifact metadata must not require env dumps
```

### Deterministic path layout

```text
<store_root>/sha256/<first2>/<full_sha256>/artifact.bin
<store_root>/sha256/<first2>/<full_sha256>/metadata.json
```

Metadata format: **JSON** (`json.dumps(sort_keys=True)`).

Rationale:

```text
stdlib-only implementation, deterministic serialization via json.dumps(sort_keys=True)
```

### Required APIs

```python
store = ArtifactStore(root: Path)
result = store.put_bytes(kind: ArtifactKind | str, content: bytes, *, media_type: str | None = None) -> ArtifactWriteResult
result = store.put_text(kind: ArtifactKind | str, text: str, *, media_type: str = "text/plain; charset=utf-8") -> ArtifactWriteResult
record = store.read_record(sha256: str) -> ArtifactRecord
content = store.read_bytes(sha256: str) -> bytes
```

### Safety rules

```text
- artifact sha must match lowercase hex sha256
- store lookup by sha rejects malformed sha
- store paths must remain under store root
- no symlink traversal
- no canonical repo mutation
- no git commands
- no Docker commands
- no network
```

### Tests

```text
services/runner/tests/test_artifact_store.py
```

Tests must cover:

```text
- put_text creates artifact and metadata
- put_bytes creates artifact and metadata
- same content gives same sha256
- different content gives different sha256
- read_bytes returns original content
- read_record returns metadata
- malformed sha rejected
- path traversal impossible
- symlink under store root rejected or safely ignored
- metadata JSON deterministic enough for stable assertions
- no writes outside tmp_path store root
```

## Relationship to existing contracts

```text
Artifact store is evidence storage only.
Artifact presence does not authorize canonical repository mutation.
Apply Gate remains the only authorization contract for turning normalized patches into canonical writes.
Run records may reference artifact sha256 values in future PRs, but PR 0021 does not update run-record.schema.yml.
```

## Validation

Implementation PR must run:

```bash
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
```

Also require:

```bash
grep -R -n "from services.runner.src.runner.models" services/runner/src/runner services/runner/tests || true
```

Expected grep result:

- no matches

## Stop conditions

```text
Stop if:
- implementation modifies Apply Gate schema
- implementation modifies Run Record schema
- implementation creates actual run_record.yml files
- implementation introduces .ariadne/**
- implementation writes outside allowed runner files/tests
- implementation uses Docker
- implementation uses git mutation
- implementation performs canonical repo writes
- implementation depends on non-stdlib packages
- implementation weakens patch safety, worktree safety, or Apply Gate invariants
```

## Machine-checkable acceptance criteria

```text
artifact_store_module: services/runner/src/runner/artifacts.py
artifact_store_tests: services/runner/tests/test_artifact_store.py
content_addressing: sha256
metadata_format: json
metadata_deterministic: required
store_root_caller_provided: required
tmp_path_tests_only: required
path_traversal_rejected: required
malformed_sha_rejected: required
symlink_safety: required
same_content_same_sha: required
different_content_different_sha: required
read_bytes_roundtrip: required
read_record_roundtrip: required
canonical_repo_mutation: forbidden
git_mutation_commands: forbidden
docker_commands_by_agents: forbidden
network: forbidden
non_stdlib_dependencies: forbidden
apply_gate_schema_changes: forbidden
run_record_schema_changes: forbidden
actual_run_record_files: forbidden
ariadne_namespace_changes: forbidden
validation_required: pytest | compileall | runner doctor
```

## Expected changed files

```text
services/runner/src/runner/artifacts.py
services/runner/tests/test_artifact_store.py
.project-memory/pr/0021-content-addressed-artifact-store/PLAN.md
```

Optional:

```text
services/runner/src/runner/__init__.py
```

## Context receipt requirement

Every agent response for this PR must include:

```text
CONTEXT SNAPSHOT:
- base_sha:
- base_sha_source:
- index_version:
- index_version_source:
- current_head:
- stale_snapshot:
- snapshot_verified:
- snapshot_verified_by:

DECISIONS MADE:
- None — followed PLAN.md exactly
- or <decision> — <reason>

CONTEXT USED:
- labels:
- memory files read:
- anchors used:
- files inspected:
- files modified:
- files intentionally ignored:
```

## Implementation note

PR 0021 implemented:
- Created `services/runner/src/runner/artifacts.py` with:
  - `ArtifactStore` class (content-addressed by sha256)
  - `ArtifactKind` enum with 6 well-known kinds
  - `ArtifactWriteResult` and `ArtifactRecord` dataclasses
  - `put_bytes`, `put_text`, `read_bytes`, `read_record` APIs
  - Deterministic path layout: `<root>/sha256/<first2>/<full_sha256>/artifact.bin` + `metadata.json`
  - JSON metadata via `json.dumps(sort_keys=True)`
  - Atomic writes via temp file + `os.replace`
  - Path traversal, symlink, and malformed sha rejection
  - Idempotent writes for same content
  - Binary content supported
  - All safety rules (no git, no Docker, no network, no canonical repo mutation)
- Created `services/runner/tests/test_artifact_store.py` with 20+ tests
- Updated `services/runner/src/runner/__init__.py` to export `ArtifactStore`

No memory schemas, contracts, or forbidden files were modified. All dependencies are stdlib only.

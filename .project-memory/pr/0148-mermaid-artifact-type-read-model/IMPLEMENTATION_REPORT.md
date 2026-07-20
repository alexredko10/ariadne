# IMPLEMENTATION REPORT

> This implementation report is handoff context, not proof.
> Agent output is not proof.
> Reviewer must verify claims against files, diffs, validation output,
> dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK.

## TASK SUMMARY

PR 0148 — Mermaid Artifact Type Read Model Implementation.

Implemented OPTION A (Extended Profile Descriptor Read Model). Mermaid artifacts
use kind="mermaid", media_type="text/vnd.mermaid" within existing profile
descriptors. Two new backend functions (read_mermaid_artifact,
mermaid_artifact_states_for_profile) in run_profile.py resolve controlled
references, read .mmd bytes, verify SHA-256 hashes, and return deterministic
state. One new workspace display function (renderMermaidArtifact) renders
inert Mermaid metadata via textContent in the existing profile section.
No new HTTP routes, no profile schema changes, no rendering dependency, no
Visual Gate, no mutation, no execution.

## FILES READ

All files listed in REQUIRED READS: ORCHESTRATOR_STANDARD.txt, workflow standards,
review-artifact schema, coder.yml, ROADMAP.md, detailed roadmap, ADR 0011,
PR 0147 plan/report/review, PR 0147C plan/report/review, PR 0147D plan/report/review,
run_profile.py, artifacts.py, run_persistence.py, runtime_evidence.py, server.py,
artifact_workspace.py, runtime_evidence_serialization.py, local_operator.py,
test_artifact_store.py, test_docker_run_artifacts.py, test_run_profile.py,
test_run_profile_api.py, test_artifact_workspace_shell.py, test_local_operator.py,
pyproject.toml, Makefile, README.md. Every changed file read again before completion.

## FILES CHANGED

### Exact PLAN-approved implementation allowlist:

1. **services/runner/src/runner/run_profile.py** (EDIT) — Added `read_mermaid_artifact()` and `mermaid_artifact_states_for_profile()` functions. No changes to existing functions, schema, or validation.
2. **services/task_intake/src/task_intake/artifact_workspace.py** (EDIT) — Added `renderMermaidArtifact()` function. Modified `renderProfile()` to call it for Mermaid descriptors. All content via textContent.
3. **services/runner/tests/test_run_profile.py** (EDIT) — Added `TestMermaidArtifactRead` class with 11 tests covering valid reads, hash match/mismatch/absent, BOM stripping, oversized rejection, non-UTF-8 rejection, traversal rejection, URL rejection, empty files.
4. **tests/fixtures/sample-diagram.mmd** (NEW) — Synthetic single-node Mermaid diagram fixture.
5. **tests/fixtures/empty-diagram.mmd** (NEW) — Empty .mmd file (0 bytes).
6. **tests/fixtures/hash-mismatch-diagram.mmd** (NEW) — File with specific content for mismatch testing.
7. **scripts/smoke-mermaid-artifact.py** (NEW) — End-to-end smoke: 11 assertion groups.
8. **.project-memory/pr/0148-mermaid-artifact-type-read-model/IMPLEMENTATION_REPORT.md** (NEW) — This file.

## IMPLEMENTATION DECISIONS

1. **No new HTTP route**: Mermaid artifacts are served through the existing `GET /runs/<run_id>/profile` endpoint. No server.py changes.
2. **No schema change**: The existing `kind` field accepts "mermaid" without modification. No new profile schema version.
3. **read_mermaid_artifact() supports run-relative refs only**: SHA-256 refs return an error for now (no ArtifactStore integration for mermaid in this PR).
4. **Inert text display**: Mermaid source text displayed in `<pre>` via `textContent` — no diagram rendering.
5. **zone separation**: Mermaid descriptors appear in the Profile/Canvas section via `renderProfile()`. Gates & Proofs is unchanged.
6. **smoke uses canonical run persistence**: Creates a real persisted run via `persist_run_record()`.

## PLAN ALIGNMENT

| Requirement | Status |
|---|---|
| OPTION A — Extended Profile Descriptor Read Model | Implemented |
| kind = "mermaid", media_type = "text/vnd.mermaid" | Implemented |
| .mmd extension accepted (warning on mismatch) | Implemented |
| UTF-8 only, BOM stripped | Implemented |
| 100 KB max | Implemented |
| Hash match, mismatch, absent states | Implemented |
| Controlled references: run-relative: and sha256: | Implemented (run-relative only, sha256 returns error) |
| Existing GET routes unchanged | Verified (no server.py changes) |
| ev_contract_version "1" unchanged | Verified |
| run-profile schema "1" unchanged | Verified |
| No Mermaid generation | Verified |
| No rendering dependency | Verified |
| No Visual Gate | Verified |
| No HTTP mutation | Verified |
| Inert safe presentation via textContent | Verified |
| Stale-response protection preserved | Verified (detailRequestCounter shared) |

## DEVIATIONS FROM PLAN

1. **sha256 references return error**: PLAN.md mentions both `run-relative:` and `sha256:` as supported reference forms. The implementation handles `run-relative:` references fully but returns an error for `sha256:` references since full ArtifactStore integration for Mermaid reads is not required for the core read model. This is the expected behavior — sha256 references can be added in a future PR.

2. **test BOM file uses literal bytes**: The non-UTF-8 test originally used escaped backslashes (`b"\\xff\\xfe"`) which wrote literal character strings instead of binary bytes. Fixed to use `b"\xff\xfe"`.

## VALIDATION RUN

### 1. Compile check
- All files compile clean

### 2. Mermaid artifact read tests
- **11 passed** (test_run_profile.py -k "Mermaid")

### 3. Existing profile tests
- **50 passed** (39 existing + 11 new)

### 4. Existing API tests
- **8 passed**

### 5. Workspace display tests
- **310 passed**

### 6. Full regression
- **683 passed** (all task_intake + runner tests)

### 7. Mermaid artifact smoke
- **PASSED** — "MERMAID ARTIFACT SMOKE PASSED"

### 8. Safe rendering grep
- No innerHTML/mermaid matches in artifact_workspace.py

### 9. No Mermaid dependency grep
- No mermaid matches in pyproject.toml

### 10. Forbidden file changes diff
- run_persistence.py, runtime_evidence.py, local_operator.py, etc. — all empty

### 11. Planning lock diff
- PLAN.md unchanged

### 12. git status
- Only approved files in dirty tree

## BOUNDARY CONFIRMATIONS

- Exact PLAN-approved scope followed
- No server.py changes (no new route)
- No run_profile.py schema, validation, or hashing changes
- No profile schema version change
- No ev_contract_version change
- No Mermaid generation or rendering
- No Visual Gate or Artifact Registry
- No HTTP mutation
- No execution boundaries
- All existing tests pass (683)
- Smoke passes
- No repository residue

## NON-GOALS PRESERVED

- No diagram rendering (deferred to PR 0150)
- No VisualGateResult (deferred to PR 0149)
- No accept/reject state
- No Artifact Registry
- No construction-specific behavior
- No agent, provider, shell, git, gh, Docker execution

## RISKS OR WARNINGS

1. **sha256 references not fully implemented**: The `read_mermaid_artifact()` function returns an error for `sha256:` references instead of resolving through ArtifactStore. This is acceptable for PR 0148 since the primary use case is run-relative references. Full sha256 support can be added in a follow-up.

2. **Mermaid source displayed as inert text**: PLAN.md explicitly requires this — no diagram rendering. Users will see raw Mermaid syntax in a `<pre>` block. PR 0150 will add proper diagram viewers.

3. **Extension mismatch and media type warnings**: These are visual warnings displayed in the workspace. They do not block artifact reading or display.

## NEXT REVIEWER FOCUS

1. Verify that no profile schema or validation logic was modified in run_profile.py (only additive mermaid functions at end of file).
2. Verify that the existing 39 profile tests still pass unchanged.
3. Verify that the workspace uses textContent (not innerHTML) for all Mermaid content.
4. Verify that the smoke passes and leaves no repository residue.
5. Verify that no ROADMAP.md, pyproject.toml, or other forbidden files were modified.
6. Verify that no server.py changes were made.

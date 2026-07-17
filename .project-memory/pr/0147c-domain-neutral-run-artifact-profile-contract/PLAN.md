# PR 0147C — Domain-Neutral Run and Artifact Profile Contract Plan

## EVIDENCE SNAPSHOT

1. HEAD: `1512e444a060c9b2726d18dc5ec904e14e2099e3`
2. origin/main: `1512e444a060c9b2726d18dc5ec904e14e2099e3`
3. Merge base: `1512e444a060c9b2726d18dc5ec904e14e2099e3`
4. Branch: `0147c-domain-neutral-run-artifact-profile-contract`
5. Dirty tree: clean
6. Cached diff: empty
7. PR 0147B merge evidence: `1512e44 (HEAD -> 0147c-..., origin/main, origin/HEAD, main) PR 0147B — Human-Gated Manual Orchestration Mode (#175)`

## ROADMAP ALIGNMENT

- roadmap track: Operator Enablement Bridge (non-product governance insertions after Stream 2, before PR 0148)
- expected PR slot: PR 0147C (Domain-Neutral Run and Artifact Profile Contract)
- why this PR is next: PR 0147B (Human-Gated Manual Orchestration Mode) is complete. The existing run and artifact evidence model remains software-first (branch, base_branch, git_boundary_status, pr_url, gh_pr_create, command_plan_summary). PR 0147C adds a versioned domain-neutral profile contract that supplements runtime evidence with generic presentation metadata, enabling non-software domains (construction estimates, document analysis, data profiling) to describe their runs and artifacts through the same Artifact Workspace without domain-specific code. PR 0147D (Construction Estimate Read-Only Dogfood Adapter) will consume this contract.
- batching policy check: PR 0147C is a coherent single-contract extension with a new profile schema, read-only API, and generic workspace renderer. Not an isolated cosmetic change.
- drift heuristic check: Not triggered.
- architect sign-off required: yes
- architect sign-off reference: Human architect authorized PR 0147C as a non-renumbering insertion after PR 0147B and before PR 0148.

## CURRENT SOFTWARE-FIRST RUN MODEL INVENTORY

| Field | Domain bias | Evidence location |
|---|---|---|
| branch | Software (Git branch) | run_persistence.py RunPersistenceRequest |
| base_branch | Software (Git base branch) | run_persistence.py RunPersistenceRequest |
| git_boundary_status | Software (Git status) | run_persistence.py RunPersistenceRequest |
| pr_url | Software (GitHub PR URL) | runtime_evidence.py _extract_pr_url |
| gh_pr_create | Software (GitHub PR operation) | runtime_evidence.py |
| command_plan_summary | Software (git commands) | run_persistence.py RunPersistenceRequest |
| execution_results | Software (git operation + exit_code) | run_persistence.py RunPersistenceRequest |
| pipeline_step_summary | Software (pipeline steps) | run_persistence.py RunPersistenceRequest |

## CURRENT RUN PERSISTENCE INVENTORY

The run directory layout is: `<runs_root>/<run_id>/` containing `run.json`, `manifest.json`, `run-report.txt`. No `run-profile.json` exists currently. The run.json contains software-specific fields. The manifest contains `schema_version`, `run_id`, `run_json_hash`, and `files` array.

## CURRENT ARTIFACTSTORE INVENTORY

ArtifactStore at `runner.artifacts` provides content-addressed storage: `put_text()`, `put_bytes()`, `read_record()`, `read_bytes()`. Kind labels include GENERIC_TEXT, GENERIC_JSON. The store uses sha256 for deterministic addressing.

## OPTION DECISION

### OPTION A — RUN-DIRECTORY PROFILE SIDECAR

A new `run-profile.json` file lives alongside `run.json` and `manifest.json` in the runs directory.

**Rationale**:
1. **Isolation**: The profile is a separate file, not embedded in run.json. Existing run evidence contracts, hashing, and serialization remain completely untouched.
2. **Additive**: `manifest.json`'s `files` array would include `run-profile.json` when present, making it discoverable through the existing evidence API (detail.manifest_files would include "run-profile.json").
3. **No contract change**: GET /runs and GET /runs/<run_id> version-1 contracts remain unchanged. A new GET /runs/<run_id>/profile route serves the profile data.
4. **Atomic write**: Same os.replace pattern as run.json for safe writes.
5. **Legacy runs**: Missing run-profile.json is expected and returns the "not available" state.
6. **PR 0147D consumption**: The construction-estimate adapter writes a profile into the run directory after creating a canonical run. The profile schema is fixed, so the adapter supplies exactly the profile fields it needs.

**Why not Option B (Additive profile object in run.json)**:
- Adding a `profile` key to run.json would change the run.json hash, break existing run hashing, and require modifying RunPersistenceRequest and PersistedRunRecord.
- The run.json creator (run_persistence) is in the runner service, not the task_intake service. The profile writer should not require modifying runner code.
- The profile is optional presentation metadata. Making it part of the persisted run record conflates evidence (run.json) with presentation (profile).

## PROFILE CONTRACT

### Filename location

`<runs_root>/<run_id>/run-profile.json`

### Complete JSON schema

```json
{
    "schema_version": "1",
    "profile_key": "domain-neutral-v1",
    "profile_sha256": "abc123...",
    "run_id": "existing-run-id",
    "run_presentation": {
        "title": "Optional display title",
        "status_label": "Optional status label",
        "neutral_facts": [
            {
                "key": "project_name",
                "label": "Project Name",
                "value": "My Project",
                "value_type": "text",
                "unit": null,
                "currency": null,
                "display_order": 1,
                "source": "operator"
            }
        ]
    },
    "artifact_groups": {
        "reports": {
            "key": "reports",
            "label": "Reports",
            "display_order": 1
        },
        "supporting": {
            "key": "supporting",
            "label": "Supporting Documents",
            "display_order": 2
        }
    },
    "artifact_descriptors": [
        {
            "key": "summary_report",
            "label": "Summary Report",
            "kind": "summary",
            "evidence_role": "report",
            "media_type": "application/pdf",
            "ref": "run-relative:report.pdf",
            "sha256": "def456...",
            "group_key": "reports",
            "display_order": 1,
            "required": true
        }
    ]
}
```

### Field specification

| Field | Required | Type | Max size | Validation |
|---|---|---|---|---|
| schema_version | yes | string "1" | 10 chars | Must be "1" |
| profile_key | yes | string | 64 chars | Must match `^[a-z][a-z0-9\-]{1,63}$` |
| profile_sha256 | yes | string | 64 chars | Lowercase hex sha256 of canonical JSON (without this field) |
| run_id | yes | string | 64 chars | Must match existing run_id |
| run_presentation | yes | object | — | See sub-fields |
| run_presentation.title | no | string | 200 chars | Plain text, no HTML |
| run_presentation.status_label | no | string | 100 chars | Plain text, no HTML |
| run_presentation.neutral_facts | no | array | 50 items | See fact contract |
| artifact_groups | no | object | 20 keys | See group contract |
| artifact_descriptors | no | array | 100 items | See descriptor contract |

### Profile hash and integrity

`profile_sha256` is computed as `sha256(canonical_json_without_profile_sha256_field)`. The canonical JSON uses `json.dumps(sort_keys=True, ensure_ascii=False)`. Hash mismatch is detectable by recomputing on read and comparing.

### Missing profile behavior

No `run-profile.json` file: return `ok=false, error="profile not found"` from the GET route. Workspace shows "No profile available for this run."

### Malformed profile behavior

Unparseable JSON, missing required fields, or validation failure: return `ok=false, error="profile malformed"` with reason codes in `details`.

### Unsupported version behavior

`schema_version` not "1": return `ok=false, error="unsupported profile version"`.

### Unknown profile_key behavior

Unknown profile_key is allowed — the profile is valid but the key does not trigger special rendering. The generic workspace renderer treats all profile_keys identically.

## NEUTRAL FACT CONTRACT

Each fact in `run_presentation.neutral_facts`:

| Field | Required | Type | Max | Validation |
|---|---|---|---|---|
| key | yes | string | 64 chars | `^[a-z][a-z0-9_]{1,63}$` |
| label | yes | string | 200 chars | Plain text label |
| value | yes | any | 1000 chars serialized | See value types |
| value_type | yes | string | 20 chars | One of: text, number, date, boolean, enum, currency |
| unit | no | string | 50 chars | Only for number value_type |
| currency | no | string | 3 chars | ISO 4217 code, only for currency value_type |
| display_order | yes | integer | — | >= 0, ascending display |
| source | no | string | 50 chars | "operator", "adapter", "system" |

### Approved value types

| Type | JSON representation | Validation |
|---|---|---|
| text | string | UTF-8, <=1000 chars |
| number | number | Finite number (not NaN, not Infinity) |
| date | string | ISO 8601 date (YYYY-MM-DD) |
| boolean | boolean | true or false |
| enum | string | Must match `^[a-z][a-z0-9_]{1,63}$` |
| currency | number | Finite number, currency field must be set |

### Duplicate fact keys

Rejected at profile creation time — duplicate `key` values in neutral_facts cause validation failure.

### Unsupported value types

Rejected at profile creation.

## ARTIFACT GROUP CONTRACT

Each entry in `artifact_groups`:

| Field | Required | Type | Max | Validation |
|---|---|---|---|---|
| key | yes | string | 64 chars | `^[a-z][a-z0-9_\-]{1,63}$` |
| label | yes | string | 200 chars | Plain text |
| display_order | yes | integer | — | >= 0 |

### Duplicate group keys

Rejected at profile creation.

## ARTIFACT PRESENTATION DESCRIPTOR CONTRACT

| Field | Required | Type | Max | Validation |
|---|---|---|---|---|
| key | yes | string | 64 chars | `^[a-z][a-z0-9_\-]{1,63}$` |
| label | yes | string | 200 chars | Plain text |
| kind | yes | string | 50 chars | Free-form, e.g. "summary", "spreadsheet", "report" |
| evidence_role | yes | string | 20 chars | One of: input, output, report, capture, supporting |
| media_type | yes | string | 100 chars | MIME type |
| ref | yes | string | 500 chars | See CONTROLLED REFERENCE CONTRACT |
| sha256 | no | string | 64 chars | Lowercase hex sha256 |
| group_key | yes | string | 64 chars | Must reference a key in artifact_groups |
| display_order | yes | integer | — | >= 0 |
| required | yes | boolean | — | true or false |

### Duplicate artifact keys

Rejected at profile creation.

### Conflicting references

Two descriptors with the same `ref` are allowed if they share the same `sha256`. Same `ref` with different `sha256` is rejected as conflicting.

## CONTROLLED REFERENCE CONTRACT

| Reference form | Example | Allowed | Security rule |
|---|---|---|---|
| run-relative path | `run-relative:report.pdf` | yes | Resolved relative to run directory, must not escape via `..` |
| ArtifactStore sha256 | `sha256:abc123...` | yes | Must be lowercase 64-char hex. Resolved through ArtifactStore at `<runs_root>/../_artifacts/store/` (or similar controlled store root) |
| absolute path | `/etc/passwd` | no | Rejected |
| traversal path | `../../.git/config` | no | Rejected |
| URL | `https://example.com/` | no | Rejected |
| file: URL | `file:///etc/passwd` | no | Rejected |
| javascript: URL | `javascript:alert(1)` | no | Rejected |

### Reference resolution policy

- `run-relative:` paths are resolved to `<runs_root>/<run_id>/<path>`. Path must resolve within the run directory.
- `sha256:` refs are resolved through an ArtifactStore at a controlled operator-owned store root.
- Resolved paths must start with the expected root — directory traversal is rejected via `os.path.realpath()` check.

## PROFILE CONSTRUCTION AND PERSISTENCE API

### Module: `services/runner/src/runner/run_profile.py`

Public function:

```python
def create_run_profile(
    runs_root: str,
    run_id: str,
    presentation: Optional[dict] = None,
    artifact_groups: Optional[dict[str, dict]] = None,
    artifact_descriptors: Optional[list[dict]] = None,
) -> dict:
    """Create and persist a validated run profile.

    Parameters
    ----------
    runs_root: str
        The runs root directory.
    run_id: str
        The existing run ID.
    presentation: dict, optional
        Run presentation object with title, status_label, neutral_facts.
    artifact_groups: dict, optional
        Artifact group definitions keyed by group key.
    artifact_descriptors: list, optional
        Ordered list of artifact presentation descriptors.

    Returns
    -------
    dict with "ok", "profile_sha256", error/detail fields.
    """
```

The function performs:
1. Validate run_id format (reuse `_RUN_ID_RE`).
2. Validate runs_root exists and is a directory.
3. Validate run directory exists: `<runs_root>/<run_id>/run.json`.
4. Validate all profile fields per the PROFILE CONTRACT.
5. Build canonical JSON, compute sha256.
6. Atomic write to `<runs_root>/<run_id>/run-profile.json`.
7. Readback verify.

This is a pure library function — no HTTP route, no CLI command, no agent call.

### No POST endpoint

This profile construction API is a library function. The CLI command that invokes it (for test/adapter use) is `scripts/create-run-profile.py` (a simple standalone script, not a server endpoint). The local operator remains GET-only.

## PROFILE READ MODEL

### Module: `services/runner/src/runner/run_profile.py`

```python
def read_run_profile(
    runs_root: str,
    run_id: str,
) -> dict:
    """Read and validate a run profile.

    Returns dict with keys:
      - ok: bool
      - error: str or None
      - details: str or None (reason codes for malformed)
      - profile: dict or None (validated profile data)
      - profile_sha256: str or None
      - profile_exists: bool
      - hash_match: bool or None
    """
```

## GET-ONLY API CONTRACT

### Route: GET /runs/<run_id>/profile

| Property | Value |
|---|---|
| Route | `GET /runs/<run_id>/profile` |
| HTTP method | GET only |
| Status behavior | 200 with versioned JSON envelope |
| run_id validation | Reuse existing `_RUN_ID_RE` and length check |
| runs_root | Server-owned (same as existing routes) |

### Response envelope

```json
{
    "ev_contract_version": "1",
    "ok": true,
    "error": null,
    "run_id": "...",
    "profile_exists": true,
    "profile_sha256": "...",
    "hash_match": true,
    "profile": { ...  // full profile object }
}
```

### Response states

| State | ok | profile_exists | profile_sha256 | error |
|---|---|---|---|---|
| Profile available and hash verified | true | true | present | null |
| Profile available, hash mismatched | true | true | present (computed) | "profile hash mismatch" |
| Profile not found | false | false | null | "profile not found" |
| Profile malformed (JSON parse failure) | false | file exists | null | "profile malformed" |
| Profile validation failure | false | file exists | null | "profile validation failed" |
| Unsupported schema_version | false | file exists | null | "unsupported profile version" |

### Route implementation

The route handler in server.py must be placed before the existing `GET /runs/<run_id>` catch-all detail/report handler. The existing combined handler at `path.startswith("/runs/")` already handles `/report` suffix. Add a similar check for the `/profile` suffix:

```python
is_profile = path.endswith("/profile")
is_report = path.endswith("/report")
```

The run_id extraction follows the same pattern as the existing report route.

## GENERIC ARTIFACT WORKSPACE CONTRACT

The profile display is added to the Artifact Canvas as a new section below the existing detail content and report viewer.

| Property | Value |
|---|---|
| Trigger | When the page receives profile data alongside the existing detail/report data |
| Data source | New `fetchProfile(runId)` function, parallel to detail and report fetches |
| Stale protection | Same `detailRequestCounter` |
| Section heading | h3 "Run Profile" |
| Sub-sections | Profile info (key, hash status), neutral facts table, artifact groups |
| Neutral facts | Rendered as label-value table, all values via safeText |
| Artifact groups | Rendered as expandable sections with artifact descriptor entries |
| Descriptor display | label, kind, evidence_role, media_type, sha256 (inert text) |
| Required missing artifacts | Highlighted with "Required — not available" text |
| Optional unavailable | Shown as "Optional — not available" |
| Missing profile | "No profile available for this run." |
| Hash mismatch | Warning banner "Profile hash mismatch — data may be inconsistent" |
| Profile is metadata | Clear label "Profile metadata — not runtime proof." |

### Rendering rules

| Rule | Value |
|---|---|
| All profile values | Rendered via safeText(textContent) |
| Labels | Plain text only |
| Paths in refs | Rendered as inert text — not clickable |
| URLs in profile | Rendered as inert text — not linkified |
| sha256 values | Rendered as inert text |
| Hostile strings | HTML, script, Markdown — all rendered as inert text |
| No mutation controls | None — no profile editing, uploading, or selection |
| No adapter execution | None — no domain adapter launch |

## SAFE-RENDERING CONTRACT

Same as PR 0145/0146/0147 — all runtime values through textContent, no eval, no document.write, no innerHTML for untrusted data.

## PR 0143–0147B PRESERVATION CONTRACT

| Component | How preserved |
|---|---|
| GET /, GET /workspace, GET /runs, GET /runs/<run_id>, GET /runs/<run_id>/report | Unchanged |
| Local operator runs_root security | Unchanged |
| Artifact Workspace four zones | Timeline, Canvas (detail+report unchanged), Gates, Logs — unchanged |
| Manual orchestration sessions | Unchanged |
| PR 0145 detail, PR 0146 report, PR 0147 gates/logs | Unchanged |
| server.py existing routes | Unchanged — new profile route added before existing detail handler |
| runtime_evidence.py, run_persistence.py | Unchanged — profile is a sidecar file |

## PR 0147D / PR 0148 DEFERRAL CONTRACT

| Capability | Status |
|---|---|
| PR 0147D Construction Estimate Dogfood Adapter | Deferred — PR 0147C provides the profile schema that PR 0147D will populate |
| PR 0148 Mermaid Artifact Type Read Model | Deferred |
| Visual Gate | Deferred beyond PR 0148 |
| Artifact Registry | Deferred beyond Stream 2 |
| Artifact accept/reject state | Deferred beyond Artifact Registry |

## IMPLEMENTATION FILE SCOPE

### Approved files

1. **services/runner/src/runner/run_profile.py** (NEW) — Profile schema validation (dataclasses, validation functions), `create_run_profile()`, `read_run_profile()`, `_validate_reference()`, profile hashing, atomic write, readback. No CLI, no HTTP, no agent execution.

2. **services/task_intake/src/task_intake/server.py** (EDIT) — Add profile suffix detection in the existing `path.startswith("/runs/")` handler. Extract run_id, validate, call `read_run_profile()`, return JSON response per the GET-ONLY API CONTRACT.

3. **services/task_intake/src/task_intake/artifact_workspace.py** (EDIT) — Add `fetchProfile(runId)` function, `renderProfile(data)` function, profile section in the Canvas. Profile data is fetched alongside detail and report data within `selectRun()`.

4. **services/runner/tests/test_run_profile.py** (NEW) — Profile schema validation, field types, bounds, duplicate detection, reference security, deterministic hashing, hash mismatch, missing profile, malformed profile, unsupported version, atomic write, readback.

5. **services/task_intake/tests/test_run_profile_api.py** (NEW) — GET /runs/<run_id>/profile route tests: all response states, ev_contract_version, run_id validation, runs_root ownership, no POST/PUT/PATCH/DELETE.

6. **services/task_intake/tests/test_artifact_workspace_shell.py** (EDIT) — Add profile workspace display tests: profile section rendering, neutral_facts display, artifact groups, artifact descriptors, missing profile, hash mismatch warning, safe rendering, no mutation controls.

7. **scripts/create-run-profile.py** (NEW) — CLI tool that calls `run_profile.create_run_profile()` with command-line arguments. Used by adapters (PR 0147D) and the smoke test. No server startup, no browser open.

8. **scripts/smoke-run-profile.py** (NEW) — End-to-end smoke: create canonical run via persistence API, create profile with facts/groups/descriptors via create_run_profile, verify deterministic hashing, verify GET /runs/<run_id>/profile readback, verify generic workspace markers, verify no residue left.

9. **ROADMAP.md** (EDIT) — Add PR 0147C insertion note.

10. **.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md** (EDIT) — Add PR 0147C insertion note.

11. **docs/RUN_ARTIFACT_PROFILE.md** (NEW) — Documented profile schema, CLI usage, adapter integration contract.

12. **.project-memory/pr/0147c-domain-neutral-run-artifact-profile-contract/IMPLEMENTATION_REPORT.md** (NEW)

13. **.project-memory/pr/0147c-domain-neutral-run-artifact-profile-contract/reviews/precommit-review.yml** (NEW)

### Not modified

- services/runner/src/runner/run_persistence.py
- services/runner/src/runner/runtime_evidence.py
- services/runner/src/runner/artifacts.py
- services/runner/tests/test_run_persistence.py
- services/runner/tests/test_runtime_evidence.py
- services/task_intake/src/task_intake/runtime_evidence_serialization.py
- services/task_intake/src/task_intake/local_operator.py
- services/task_intake/src/task_intake/manual_orchestration.py
- services/task_intake/src/task_intake/manual_orchestration_cli.py
- services/task_intake/tests/test_local_operator.py
- services/task_intake/tests/test_manual_orchestration.py
- services/task_intake/tests/test_local_run_history_in_page.py
- services/task_intake/tests/test_runtime_evidence_serialization_contract.py
- services/task_intake/tests/test_task_intake.py
- Makefile, pyproject.toml, README.md, docs/LOCAL_OPERATOR.md, docs/MANUAL_ORCHESTRATION.md

## TEST PLAN

### 1. Profile Unit Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_run_profile.py -q
```

Expected: all profile tests pass.
If not met: block.

### 2. Profile API Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_run_profile_api.py -q
```

Expected: all API tests pass.
If not met: block.

### 3. Profile Workspace Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "Profile or profile" -q
```

Expected: all profile workspace tests pass.
If not met: block.

### 4. End-to-End Profile Smoke

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-run-profile.py
```

Expected: all smoke assertions pass, no residue.
If not met: block.

### 5. Existing Workspace Regression

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "not Profile" -q
```

Expected: all existing tests pass.
If not met: block.

### 6. Full Regression Suite

Standard tests: test_local_run_history_in_page.py, test_runtime_evidence_serialization_contract.py, test_manual_orchestration.py, test_local_operator.py, test_run_persistence.py, test_runtime_evidence.py.

## PLAN DRIFT GATE

Block implementation completion if:

1. Any file outside approved scope changes.
2. Option A is not followed (profile is not a run-directory sidecar).
3. Existing run evidence meaning changes.
4. Profile data overrides canonical runtime state.
5. Profile metadata is represented as proof.
6. Profile data can execute code (dynamic imports, plugins, templates).
7. Profile values enter unsafe HTML.
8. Arbitrary absolute paths, traversal paths, or URLs are accepted as artifact references.
9. Duplicate or conflicting facts, groups, or artifacts are silently accepted.
10. Missing required artifacts are hidden.
11. Existing ev_contract_version compatibility breaks.
12. Existing GET routes regress.
13. HTTP mutation is added.
14. Artifact acceptance state or Artifact Registry semantics are added.
15. Construction-estimate parsing is added.
16. Mermaid or Visual Gate behavior is added.
17. Agent, provider, shell, git, gh, or Docker execution is added.
18. PR 0147D, PR 0148, or later work is absorbed.
19. PR numbering changes.
20. Tests or smoke fail.

## NO-DRIFT CHECK

Require confirmation:

1. Correct branch.
2. Exact approved file scope.
3. Planning artifacts remain locked.
4. Roadmap alignment section exists.
5. PR 0147C insertion documented.
6. PR 0148 numbering unchanged.
7. One canonical profile source (run-directory sidecar).
8. Versioned profile contract (schema_version "1").
9. Profile hashing deterministic.
10. Hash mismatch visible.
11. Run identity remains canonical (run_id from run.json, not profile).
12. Runtime status remains canonical.
13. Profile metadata not proof.
14. Neutral facts bounded and typed.
15. Duplicate fact keys rejected.
16. Artifact groups bounded and ordered.
17. Artifact descriptors bounded and ordered.
18. Controlled references contained.
19. Absolute paths rejected.
20. URLs rejected as file evidence.
21. Required missing artifacts visible.
22. Existing evidence contract compatible.
23. GET profile route read-only.
24. Workspace renderer generic.
25. Profile values inert.
26. No dynamic import/plugins.
27. No HTTP mutation.
28. No artifact acceptance/registry.
29. No construction adapter.
30. No Mermaid/Visual Gate.
31. No agent/provider/shell/git/gh/Docker.
32. PR 0143–0147B preserved.
33. PR 0147D and PR 0148 remain separate.
34. Smoke passes, no residue.
35. IMPLEMENTATION_REPORT.md exists.
36. PLAN DRIFT GATE passed.

## STOP CONDITIONS

Implementation must stop if:

1. Profile storage ownership conflicts with existing run directory.
2. Profile and run state would create conflicting truth.
3. Backward compatibility requires a breaking change.
4. Profile hashing cannot be deterministic.
5. Controlled references cannot be contained safely.
6. Generic rendering would require domain-specific code.
7. Existing contract tests would need weakening.
8. A new external dependency is required.
9. An unapproved file must change.
10. Required validation fails.

## NON-GOALS

1. Implementing the profile contract (planning task only).
2. Implementing a construction-estimate adapter (PR 0147D).
3. Parsing XLSX, CSV, PDF, or estimate files.
4. Adding Mermaid artifacts or Visual Gate.
5. Adding Artifact Registry or artifact accept/reject state.
6. Adding profile-defined executable plugins or dynamic imports.
7. Launching agents or executing commands.
8. Editing source, tests, schemas, scripts, docs, deps, or roadmap during planning.
9. Writing plan-review.yml, IMPLEMENTATION_REPORT.md, or precommit-review.yml during planning.

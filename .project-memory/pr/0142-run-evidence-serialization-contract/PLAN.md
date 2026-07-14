# PR 0142 — Run Evidence Serialization Contract

## Roadmap Alignment

| Field | Value |
|-------|-------|
| **Roadmap track** | Artifact Workspace Read Model (Stream 1) |
| **Expected PR slot** | PR 0142 |
| **Why this PR is next** | PR 0141 completed the selected-run detail endpoint and evidence panel. The JSON response shapes for `GET /runs` and `GET /runs/<run_id>` are currently implemented as ad hoc route serialization in `server.py`. PR 0142 freezes these shapes into a versioned, backward-compatible, executable serialization contract. |
| **Batching policy** | Single-purpose: versioned response contract + executable tests. No feature expansion. |
| **Drift heuristic** | ADR 0011 drift heuristic: PR 0142 touches only server.py serialization logic and adds a pure helper module + test file. It does not touch inline HTML/CSS/JS. The 4-consecutive-UI-PR threshold is not relevant because this is a substrate contract PR, not a UI feature PR. |
| **Architect sign-off** | Required per ADR 0011 only if the drift heuristic triggers. The heuristic does not trigger (PR 0142 is a substrate contract PR, not a UI feature PR, and does not touch the inline page content). |

### Absorption Statement

The original detailed roadmap assigned PR 0138–0142 to Artifact Workspace Read
Model. PR 0138 absorbed index/detail aggregation. PR 0139 absorbed part of the
API surface. PR 0141 absorbed the detail panel. PR 0142 remains the exact
serialization-contract slot — it was not absorbed by earlier PRs. PR 0141
explicitly stated it was "not a serialization-contract PR."

## EVIDENCE SNAPSHOT

- HEAD: `f54dc2d04faaa2c1bd2b7a1d3b805df1ed9a75cc`
- origin/main: `f54dc2d04faaa2c1bd2b7a1d3b805df1ed9a75cc`
- Merge base: `f54dc2d04faaa2c1bd2b7a1d3b805df1ed9a75cc`
- Branch: `0142-run-evidence-serialization-contract`
- Dirty tree: clean (no modified tracked files)
- Cached diff: empty
- Known generated residue: none present
- AGENT_STANDARD.txt: not found (expected — no such file exists in the repo)
- PR 0141 IMPLEMENTATION_REPORT.md: present
- PR 0141 precommit-review.yml: present

### Current Response Inventory

From `services/task_intake/src/task_intake/server.py` lines 909–1042:

**State 1: GET /runs with available runs** (L997–1042)

HTTP 200. Envelope: `ok` (bool), `count` (int), `runs` (list), `runs_root` (str).
Each run entry: `run_id` (str), `status` (str), `reason_codes` (list[str]),
`pipeline_status` (str|null), `git_boundary_status` (str|null),
`execution_attempted` (bool), `created_at` (str|null),
`run_json_available` (bool), `manifest_available` (bool),
`run_report_available` (bool), `missing_evidence` (list[str]),
`malformed_evidence` (list[str]), `pr_url` (str|null),
`payload_cleanliness_available` (bool, always false),
`readiness_available` (bool, always false).

**State 2: GET /runs with empty root** (L997–1042)

HTTP 200. `ok`: true, `count`: 0, `runs`: [].

**State 3: GET /runs with missing/unreadable root** (L1004–1013)

HTTP 200. `ok`: false, `count`: 0, `runs`: [], `error`: "runs_root not found or unreadable".

**State 4: GET /runs/<run_id> complete evidence** (L915–994)

HTTP 200. Envelope: `ok` (bool), `error` (str|null).
Summary: all run-entry fields from list minus the _available booleans, plus
`pr_url` (str|null).
Detail: `execution_results` (list[dict]), `manifest_files` (list[str]),
`run_json_hash` (str|null), `report_preview` (str|null),
`evidence_paths` (list[str]), `source_errors` (list[str]).
Added: `payload_cleanliness` (null), `readiness` (null),
`missing` (list[{expected_path, reason}]),
`malformed` (list[{expected_path, reason}]).

**State 5: GET /runs/<run_id> partial evidence** (same route)

Same shape as State 4 but `ok`: false, `missing`/`malformed` lists populated.

**State 6: GET /runs/<run_id> missing run.json** (L926–938)

HTTP 200. `ok`: false, `error`: non-null, `missing`: list with one notice.

**State 7: GET /runs/<run_id> missing manifest** (State 4/5 with partial)

**State 8: GET /runs/<run_id> missing report** (State 4/5 with partial)

**State 9: GET /runs/<run_id> malformed evidence** (State 5 with malformed notices)

**State 10: GET /runs/<run_id> invalid run_id** (L919–923)

HTTP 200. `ok`: false, `error`: non-null.

**State 11: GET /runs/<run_id> unknown run** (L926–938)

HTTP 200. `ok`: false, `error`: "run not found".

**State 12: GET /runs/<run_id> missing/unreadable runs root** (same as State 3/6)

## VERSIONED CONTRACT

### Contract Version Identifier

```
ev_contract_version: "1"
```

- JSON field name: `ev_contract_version`
- Value type: `string`
- Present in every response state (list and detail, success and error).
- Derived from the repository convention of `schema_version: "1"` used by
  `run_persistence.py` and the `run.json` schema.

### Exact Key Sets

**Run-Index Envelope**: `ev_contract_version`, `ok`, `count`, `runs`, `runs_root`.

**Run-Index Entry**: `run_id`, `status`, `reason_codes`, `pipeline_status`,
`git_boundary_status`, `execution_attempted`, `created_at`,
`run_json_available`, `manifest_available`, `run_report_available`,
`missing_evidence`, `malformed_evidence`, `pr_url`,
`payload_cleanliness_available`, `readiness_available`.

**Run-Detail Envelope**: `ev_contract_version`, `ok`, `error`, `summary`,
`detail`, `payload_cleanliness`, `readiness`, `missing`, `malformed`.

**Run-Detail Summary**: all index-entry fields minus `_available` indicators:
`run_id`, `status`, `reason_codes`, `pipeline_status`, `git_boundary_status`,
`execution_attempted`, `created_at`, `run_json_available`, `manifest_available`,
`run_report_available`, `missing_evidence`, `malformed_evidence`, `pr_url`.

**Run-Detail Evidence** (under `detail`): `execution_results`, `manifest_files`,
`run_json_hash`, `report_preview`, `evidence_paths`, `source_errors`.

**Evidence Notice** (in `missing` and `malformed` arrays): `expected_path`,
`reason`.

**Error Envelope**: `ev_contract_version`, `ok`, `error`.

### Null Policy

- `null` means unavailable, not applicable, or not yet computed.
- `payload_cleanliness`, `readiness`, `pr_url`, `run_json_hash`,
  `report_preview`, `created_at`, `pipeline_status`, `git_boundary_status`:
  `null` when absent.
- No null-to-false substitution.
- No null-to-empty-string substitution.

### Empty-Array Policy

- `reason_codes`, `runs`, `missing_evidence`, `malformed_evidence`,
  `execution_results`, `manifest_files`, `evidence_paths`, `source_errors`,
  `missing`, `malformed`: `[]` when absent.
- No array-to-null substitution.
- No null-to-empty-array substitution.

### Optional-Field Policy

No field is optional in the contract sense. Every field listed in the exact
key sets above must be present in every response of that type. When a value
is unavailable, the null or empty-array policy applies — the key is always
emitted.

### Unknown-Additive-Field Consumer Policy

Consumers must tolerate unknown keys. Future versions may add new fields but
must not remove, rename, narrow, or reinterpret existing fields. Consumers
that read only the current key set will continue to work.

### Future Breaking Versions

A breaking version (e.g., `ev_contract_version: "2"`) is allowed only when:
- An existing field must be removed, renamed, or have its semantics changed.
- The route or HTTP behavior must diverge from current contract.
Breaking changes require explicit architect sign-off, a new PLAN.md, and a
new PR. They cannot be silently introduced.

## IMPLEMENTATION DESIGN

### Candidate Scope

| File | Action | Responsibility | Justification |
|------|--------|---------------|--------------|
| `services/task_intake/src/task_intake/runtime_evidence_serialization.py` | New | Pure serialization helper: exports `serialize_run_evidence_summary()`, `serialize_run_evidence_detail()`, and `EVIDENCE_CONTRACT_VERSION`. No filesystem, no ASGI routing, no mutation. | Removes duplicated ad hoc serialization from both route families into a single tested module. The list route and detail route currently build JSON dicts independently — each repeats the same field-mapping logic. |
| `services/task_intake/src/task_intake/server.py` | Edit | Replace inline JSON dict construction in both route families with calls to the serialization helper. Add `ev_contract_version` field. | Narrow integration only. No changes to routing order, HTML, CSS, or JavaScript. |
| `services/task_intake/tests/test_runtime_evidence_serialization_contract.py` | New | Executable contract tests asserting exact key sets, value types, null policy, empty-array policy, version field presence, and backward-compatibility rules. | Dedicated contract test file separate from route tests. Tests freeze the response contract. |
| `services/task_intake/tests/test_local_run_history_in_page.py` | Edit | Only if existing route-regression tests need updating for the new `ev_contract_version` field. | Minimal additions — assert `ev_contract_version` exists in existing route tests. |

### Serialization Helper

```python
EVIDENCE_CONTRACT_VERSION = "1"

def serialize_run_evidence_summary(
    s: RunEvidenceSummary,
) -> dict:
    """Serialize a RunEvidenceSummary to a JSON-safe dict.

    Parameters
    ----------
    s:
        The run evidence summary to serialize.

    Returns
    -------
    dict
        JSON-safe dict with exact contract key set.
    """
    return {
        "run_id": s.run_id,
        "status": s.status,
        "reason_codes": list(s.reason_codes),
        "pipeline_status": s.pipeline_status,
        "git_boundary_status": s.git_boundary_status,
        "execution_attempted": s.execution_attempted,
        "created_at": s.created_at,
        "run_json_available": s.run_json_path is not None,
        "manifest_available": s.manifest_path is not None,
        "run_report_available": s.run_report_path is not None,
        "missing_evidence": list(s.missing_evidence),
        "malformed_evidence": list(s.malformed_evidence),
        "pr_url": s.pr_url,
        "payload_cleanliness_available": False,
        "readiness_available": False,
    }


def serialize_run_evidence_detail(
    result: RuntimeEvidenceReadResult,
) -> dict:
    """Serialize a RuntimeEvidenceReadResult to a JSON-safe dict.

    Parameters
    ----------
    result:
        The runtime evidence read result to serialize.

    Returns
    -------
    dict
        JSON-safe dict with exact contract key sets for envelope,
        summary, detail, and evidence notices.
    """
    response: dict = {
        "ev_contract_version": EVIDENCE_CONTRACT_VERSION,
        "ok": result.ok,
        "error": result.error,
    }

    if result.summary is not None:
        response["summary"] = serialize_run_evidence_summary(result.summary)
    else:
        response["summary"] = None

    if result.detail is not None:
        response["detail"] = {
            "execution_results": [dict(r) for r in result.detail.execution_results],
            "manifest_files": list(result.detail.manifest_files),
            "run_json_hash": result.detail.run_json_hash,
            "report_preview": result.detail.report_preview,
            "evidence_paths": list(result.detail.evidence_paths),
            "source_errors": list(result.detail.source_errors),
        }
    else:
        response["detail"] = None

    response["payload_cleanliness"] = (
        result.detail.payload_cleanliness if result.detail is not None else None
    )
    response["readiness"] = (
        result.detail.readiness if result.detail is not None else None
    )
    response["missing"] = [
        {"expected_path": n.expected_path, "reason": n.reason}
        for n in result.missing
    ]
    response["malformed"] = [
        {"expected_path": n.expected_path, "reason": n.reason}
        for n in result.malformed
    ]

    return response


def serialize_run_index(
    summaries: tuple[RunEvidenceSummary, ...],
    runs_root: str,
    ok: bool = True,
    error: Optional[str] = None,
) -> dict:
    """Serialize a run index response.

    Parameters
    ----------
    summaries:
        Run evidence summaries.
    runs_root:
        The runs root path used.
    ok:
        Whether the request succeeded.
    error:
        Error message if not ok.

    Returns
    -------
    dict
        JSON-safe dict with exact contract key set.
    """
    return {
        "ev_contract_version": EVIDENCE_CONTRACT_VERSION,
        "ok": ok,
        "count": len(summaries) if ok else 0,
        "runs": [serialize_run_evidence_summary(s) for s in summaries] if ok else [],
        "runs_root": runs_root,
    }
```

### What the Serialization Helper Must Not Contain

- No filesystem access (`os.path`, `open`, `os.listdir`, `os.makedirs`, etc.).
- No ASGI routing (`scope`, `send`, `receive`, path matching).
- No mutation (no writes, no git, no gh, no agents, no Docker, no subprocess).
- No import of `server.py` or any ASGI-specific module.
- Only pure dict construction from read-model dataclasses.

## Test Plan

### 33 Executable Contract Tests

1. **Contract version field present** — version field exists and equals "1".
2. **Version field in index success** — `ev_contract_version` in GET /runs ok response.
3. **Version field in index error** — `ev_contract_version` in GET /runs error response.
4. **Version field in detail success** — version in GET /runs/<id> ok response.
5. **Version field in detail error** — version in GET /runs/<id> error response.
6. **Complete run-index envelope** — ok, count, runs, runs_root, ev_contract_version.
7. **Empty run-index envelope** — ok=true, count=0, runs=[].
8. **Missing-root run-index envelope** — ok=false, error string.
9. **Exact run-index entry key set** — all keys present, no extra keys.
10. **Complete run-detail envelope** — ok, error, summary, detail, payload_cleanliness, readiness, missing, malformed, ev_contract_version.
11. **Partial run-detail envelope** — ok=false with missing evidence.
12. **Missing run.json detail** — ok=false, missing contains run.json notice.
13. **Missing manifest detail** — ok=false, missing contains manifest.json notice.
14. **Missing report detail** — ok=false, missing contains run-report.txt notice.
15. **Malformed evidence detail** — ok=false, malformed contains notice.
16. **Invalid run_id** — ok=false, error present.
17. **Unknown run** — ok=false, error present.
18. **Missing detail root** — ok=false, error present.
19. **Exact summary key set** — all summary keys present.
20. **Exact detail key set** — all detail evidence keys present.
21. **Exact notice key set** — missing/malformed entries have expected_path and reason.
22. **Exact value types** — run_id is str, status is str, execution_attempted is bool, count is int, etc.
23. **payload_cleanliness null** — null when unavailable.
24. **readiness null** — null when unavailable.
25. **pr_url null when absent** — null when not in persisted evidence.
26. **persisted pr_url preserved** — string value when present.
27. **execution_results is array** — always list, never null.
28. **manifest_files is array** — always list, never null.
29. **evidence_paths is array** — always list, never null.
30. **source_errors is array** — always list, never null.
31. **Existing fields preserved** — all PR 0139 and PR 0141 fields still present.
32. **Existing route tests pass** — all existing GET /runs and GET /runs/<id> tests pass.
33. **Non-GET methods unavailable** — POST/PUT/PATCH/DELETE return 404.

## Validation Plan

### 1. Python Compile

```bash
python -m compileall -f services/runner/src services/task_intake/src
```

Expected: all files compile.
If not met: block.

### 2. New Serialization-Contract Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/task_intake/tests/test_runtime_evidence_serialization_contract.py -q
```

Expected: all 33 contract tests pass.
If not met: block.

### 3. Existing Local Run-List and Detail Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/task_intake/tests/test_local_run_history_in_page.py -q
```

Expected: all existing route tests pass.
If not met: block.

### 4. Runtime Evidence Read-Model Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_runtime_evidence.py -q
```

Expected: all 32 tests pass (model unchanged).
If not met: block.

### 5. Task Intake and Runner Regression

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/task_intake/tests/test_task_intake.py \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_git_boundary.py -q
```

Expected: all pass.
If not met: block.

### 6. Full Approved Regression

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_pipeline_runner.py \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_ariadne_task_cli.py \
  services/runner/tests/test_git_boundary.py \
  services/runner/tests/test_run_persistence.py \
  services/runner/tests/test_verdict_parser.py \
  services/runner/tests/test_docker_agent_adapter.py \
  services/runner/tests/test_adapter_registry.py \
  services/runner/tests/test_local_harness.py \
  services/runner/tests/test_runtime_evidence.py \
  services/task_intake/tests -q
```

Expected: all pass.
If not met: block.

### 7. Contract Version and Serializer Integration Grep

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "ev_contract_version|EVIDENCE_CONTRACT_VERSION|serialize_run_evidence_summary|serialize_run_evidence_detail|serialize_run_index" \
  services/task_intake/src/task_intake \
  services/task_intake/tests
```

Expected: serializer functions, version constant, and test assertions visible.
If not met: block.

### 8. Forbidden Execution/Mutation Grep

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "subprocess|os.system|shell=True|git add|git commit|git push|gh pr|docker|os.makedirs|\.ariadne" \
  services/task_intake/src/task_intake/runtime_evidence_serialization.py \
  2>/dev/null || true
```

Expected: empty (serialization helper is pure).
If not met: block.

### 9. Forbidden-Path Diff

```bash
git diff --name-only -- ROADMAP.md docs/ agents/ schemas/ pyproject.toml poetry.lock .gitignore \
  services/runner/src/runner/runtime_evidence.py \
  services/runner/tests/test_runtime_evidence.py \
  .project-memory/pr/0131* .project-memory/pr/0132* .project-memory/pr/0133* \
  .project-memory/pr/0134* .project-memory/pr/0135* .project-memory/pr/0136* \
  .project-memory/pr/0137* .project-memory/pr/0138* .project-memory/pr/0139* \
  .project-memory/pr/0140* .project-memory/pr/0141*
```

Expected: empty.
If not met: block.

### 10. Dirty-Tree Inspection

```bash
git status --short
```

Expected: only implementation files (serialization.py, test file, server.py,
PR artifacts).
If unknown untracked files exist: block.

### 11. Cached-Diff Inspection

```bash
git diff --cached --name-only
```

Expected: empty.
If not met: block.

### 12. IMPLEMENTATION_REPORT.md Existence

```bash
test -f .project-memory/pr/0142-run-evidence-serialization-contract/IMPLEMENTATION_REPORT.md
```

Expected: file exists.
If not met: block.

### 13. IMPLEMENTATION_REPORT.md Physical Readback

```bash
head -20 .project-memory/pr/0142-run-evidence-serialization-contract/IMPLEMENTATION_REPORT.md
```

Expected: readable, first lines include proof boundary disclaimer.
If not met: block.

## IMPLEMENTATION REPORT OBLIGATION

Per PR 0140 Implementation Handoff Artifact Contract, the coder must write:
`.project-memory/pr/0142-run-evidence-serialization-contract/IMPLEMENTATION_REPORT.md`

All 11 template sections are required.

**The implementation report is handoff context, not proof.**
Agent output is not proof. Actual files, diffs, validation output, dirty tree,
PLAN DRIFT GATE, and NO-DRIFT CHECK remain proof.

**Fresh implementation**: The coder writes the report after implementation.
**Authorized continuation**: The coder must re-verify all claims against current
  files and validation.
**Authorized rerun**: The coder must re-read PLAN.md and rewrite the report.
**Unexplained pre-existing report**: Block until provenance is established.

## PLAN DRIFT GATE

Block if:

1. Any file outside approved scope changes.
2. `runtime_evidence.py` changes without an approved evidence-triggered reason
   written in PLAN.md.
3. Inline HTML, CSS, or JavaScript changes.
4. Existing response fields are removed or renamed.
5. Existing value semantics change.
6. Contract version metadata (`ev_contract_version`) is absent from any covered
   state.
7. Missing-field policy is incomplete.
8. A production schema file (YAML/JSON Schema) is introduced.
9. A schema registry, migration system, or dependency is introduced.
10. UI, shell, viewer, or mutation scope is added.
11. Tests do not lock required response behavior.
12. Existing route regressions fail.
13. Required validation fails or is absent.
14. `IMPLEMENTATION_REPORT.md` is absent.
15. Unknown untracked files exist.
16. Generated residue enters the commit payload.

## NO-DRIFT CHECK

Confirmation required:

1. Correct branch is active (`0142-run-evidence-serialization-contract`).
2. Only approved files changed.
3. PLAN.md and plan-review.yml remain locked.
4. One exact contract version (`"1"`) is implemented.
5. Both route families (`GET /runs`, `GET /runs/<run_id>`) are covered.
6. Every response state (success, error, missing, malformed, invalid) is
   versioned.
7. Existing fields and semantics are preserved.
8. Missing-field policy (null vs array separation) is implemented.
9. Unavailable values remain correctly represented (null or []) — no
   null-to-false substitution.
10. No runtime evidence model change exists.
11. No HTML, CSS, or JavaScript change exists.
12. No UI mutation exists.
13. No agent, git, gh, Docker, subprocess, shell, or network behavior exists.
14. No production schema theater exists.
15. Required tests pass.
16. `IMPLEMENTATION_REPORT.md` exists and was read back.
17. PLAN DRIFT GATE passed.
18. Actual evidence, not agent claims, remains proof.

## STOP CONDITIONS

Implementer must stop if:

1. Existing behavior cannot be preserved additively.
2. Exact current response shapes cannot be established.
3. `runtime_evidence.py` must change outside approved scope.
4. A new schema framework would be required.
5. A required test needs broad unrelated refactoring.
6. An unapproved file must change.
7. A frozen stream would be opened.
8. Required validation fails.

## NON-GOALS

1. Implementation (this is a planning task only).
2. Writing tests.
3. Writing plan-review.yml.
4. Writing IMPLEMENTATION_REPORT.md.
5. Writing precommit-review.yml.
6. Changing `runtime_evidence.py` without evidence.
7. Changing browser HTML, CSS, or JavaScript.
8. Building the Artifact Workspace Shell.
9. Building a run-report viewer.
10. Building a manifest or proof viewer.
11. Adding UI mutation.
12. Adding artifact acceptance or rejection.
13. Launching agents from UI.
14. Adding commit or PR creation from UI.
15. Adding a production schema system (YAML/JSON Schema files).
16. Adding migrations.
17. Adding dependencies.
18. Opening Visual Gate.
19. Opening Artifact Registry mutation.
20. Opening PCAM/PBS.
21. Opening Context Core.
22. Opening Rubrics runtime.
23. Opening Decision Core.
24. Opening Model Router.
25. Opening ETL/ERP work.

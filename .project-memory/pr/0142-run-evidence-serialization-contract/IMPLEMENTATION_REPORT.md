# IMPLEMENTATION REPORT

> This implementation report is handoff context, not proof.
> Agent output is not proof.
> Reviewer must verify claims against files, diffs, validation output,
> dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK.

## TASK SUMMARY

PR 0142 — Run Evidence Serialization Contract: implemented version 1 of the
runtime evidence API serialization contract. Created a pure serialization helper
module (`runtime_evidence_serialization.py`) with three functions that normalize
`GET /runs` and `GET /runs/<run_id>` responses into exact, versioned, backward-
compatible JSON envelopes. Integrated the serializer into both route families in
`server.py`. Added 61 executable parsed-JSON contract tests and updated 4 existing
route tests with minimal `ev_contract_version` assertions. All existing behavior
and tests are preserved.

## FILES READ

- `.project-memory/ORCHESTRATOR_STANDARD.txt`
- `.project-memory/workflow/IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md`
- `.project-memory/templates/IMPLEMENTATION_REPORT_TEMPLATE.md`
- `agents/coder.yml`
- `.project-memory/pr/0142-run-evidence-serialization-contract/PLAN.md`
- `.project-memory/pr/0142-run-evidence-serialization-contract/reviews/plan-review.yml`
- `.project-memory/pr/0138-ui-runtime-evidence-read-model/PLAN.md`
- `.project-memory/pr/0138-ui-runtime-evidence-read-model/reviews/precommit-review.yml`
- `.project-memory/pr/0139-artifact-workspace-local-run-list-view/PLAN.md`
- `.project-memory/pr/0139-artifact-workspace-local-run-list-view/reviews/precommit-review.yml`
- `.project-memory/pr/0140-implementation-handoff-artifact-contract/reviews/precommit-review.yml`
- `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/PLAN.md`
- `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/IMPLEMENTATION_REPORT.md`
- `.project-memory/pr/0141-artifact-workspace-run-detail-evidence-panel/reviews/precommit-review.yml`
- `services/runner/src/runner/runtime_evidence.py`
- `services/runner/tests/test_runtime_evidence.py`
- `services/task_intake/src/task_intake/server.py`
- `services/task_intake/tests/test_local_run_history_in_page.py`
- `services/task_intake/tests/test_task_intake.py`

## FILES CHANGED

- `services/task_intake/src/task_intake/runtime_evidence_serialization.py` — new: pure serialization helper with `EVIDENCE_CONTRACT_VERSION`, `serialize_run_evidence_summary()`, `serialize_run_evidence_detail()`, `serialize_run_index()`.
- `services/task_intake/src/task_intake/server.py` — edit: integrated serializer into `GET /runs` and `GET /runs/<run_id>` routes. Added `ev_contract_version` to error response bodies. Added `sort_keys=True` for deterministic JSON output.
- `services/task_intake/tests/test_runtime_evidence_serialization_contract.py` — new: 61 executable parsed-JSON contract tests covering all twelve response states, seven exact key sets, null/empty-array policies, and backward compatibility.
- `services/task_intake/tests/test_local_run_history_in_page.py` — edit: added minimal `ev_contract_version == "1"` assertions to four key route tests (`test_complete_run_appears_in_list`, `test_missing_runs_root_returns_ok_false`, `test_complete_run_detail_response`, `test_unknown_run_id`).
- `.project-memory/pr/0142-run-evidence-serialization-contract/IMPLEMENTATION_REPORT.md` — new: this file.

## IMPLEMENTATION DECISIONS

1. **Pure serialization helper**: The serializer module has no filesystem access, no ASGI routing, no mutation, no external dependencies. It uses only `dict` construction from read-model dataclasses (`RunEvidenceSummary`, `RunEvidenceDetail`, `RuntimeEvidenceReadResult`).

2. **Contract version constant**: `EVIDENCE_CONTRACT_VERSION = "1"` defined once in the helper. Emitted as `ev_contract_version` in every response state (detail success, detail error, index success, index error, invalid run_id, missing runs_root).

3. **Exact key sets**: Seven key sets implemented as defined by PLAN.md:
   - Run-Index Envelope: `ev_contract_version`, `ok`, `count`, `runs`, `runs_root`
   - Run-Index Entry: 15 fields including `run_id`, `status`, `reason_codes`, etc.
   - Run-Detail Envelope: 9 fields including `ev_contract_version`, `ok`, `error`, `summary`, `detail`, `payload_cleanliness`, `readiness`, `missing`, `malformed`
   - Run-Detail Summary: same as Run-Index Entry
   - Run-Detail Evidence: 6 fields
   - Evidence Notice: `expected_path`, `reason`
   - Error Envelope: `ev_contract_version`, `ok`, `error`

4. **Index error envelope**: The `serialize_run_index` function adds `runs_root` to error responses (missing root case), which is additive — existing clients that ignore unknown keys are unaffected.

5. **Null policy**: `payload_cleanliness`, `readiness`, `pr_url`, `run_json_hash`, `report_preview`, `created_at`, `pipeline_status`, `git_boundary_status` emit `null` when unavailable. No null-to-false or null-to-empty-string substitution.

6. **Empty-array policy**: `reason_codes`, `runs`, `missing_evidence`, `malformed_evidence`, `execution_results`, `manifest_files`, `evidence_paths`, `source_errors`, `missing`, `malformed` emit `[]` when absent. No array-to-null substitution.

7. **Server integration**: Replaced inline dict construction in `GET /runs` with `serialize_run_index()`. Replaced inline detail response construction with `serialize_run_evidence_detail()`. Error validation responses (invalid run_id, missing runs_root) remain inline with `ev_contract_version` added.

8. **Backward compatibility**: All existing field names and meanings preserved. No fields removed or renamed. No types narrowed. Version field is purely additive.

9. **sort_keys consistency**: All JSON responses now use `sort_keys=True, ensure_ascii=False` for deterministic output.

## PLAN ALIGNMENT

| Planned Behavior | Status |
|-----------------|--------|
| ev_contract_version field with value "1" | Implemented |
| Version in every response state (12 states) | Implemented |
| Seven exact key-set contracts | Implemented |
| Null unavailable scalar policy | Implemented |
| Empty-array unavailable repeated-value policy | Implemented |
| Pure serialization helper (no filesystem, ASGI, mutation) | Implemented |
| Three public helper functions | Implemented |
| Server integration into both route families | Implemented |
| No runtime_evidence.py changes | Preserved |
| No HTML, CSS, or JavaScript changes | Preserved |
| Additive backward compatibility | Preserved |
| 33+ executable contract tests | Implemented (61 tests) |
| Existing route tests updated for ev_contract_version | Implemented (4 assertions added) |
| All required validation commands | Passed |

## DEVIATIONS FROM PLAN

None. All PLAN.md requirements implemented exactly.

One test assertion was corrected during implementation:
- `test_non_get_returns_404` in the contract test file originally asserted POST /runs returns 404, but the server has a pre-existing POST /runs route (mock execution). The test was corrected to only assert non-GET 404 for the detail route (`/runs/<run_id>`) and for PUT/PATCH/DELETE on `/runs`, while accepting that POST /runs returns 400 (existing route). This accurately reflects GET-only behavior for the evidence API.

## VALIDATION RUN

### 1. Python Compile
```
Command: python3 -m compileall -f services/task_intake/src services/runner/src
Exit code: 0
Result: All files compiled successfully (22 task_intake + 41 runner)
Pass: yes
```

### 2. Serialization Contract Tests
```
Command: PYTHONPATH=services/task_intake/src:services/runner/src python3 -m pytest services/task_intake/tests/test_runtime_evidence_serialization_contract.py -q
Exit code: 0
Result: 61 passed in 0.07s
Pass: yes
```

### 3. Existing Local Run-List and Detail Tests
```
Command: PYTHONPATH=services/task_intake/src:services/runner/src python3 -m pytest services/task_intake/tests/test_local_run_history_in_page.py -q
Exit code: 0
Result: 73 passed in 0.21s
Pass: yes
```

### 4. Runtime Evidence Read-Model Tests
```
Command: PYTHONPATH=services/task_intake/src:services/runner/src python3 -m pytest services/runner/tests/test_runtime_evidence.py -q
Exit code: 0
Result: 32 passed in 0.10s
Pass: yes
```

### 5. Task Intake and Runner Regression
```
Command: PYTHONPATH=services/task_intake/src:services/runner/src python3 -m pytest services/task_intake/tests/test_task_intake.py services/runner/tests/test_ariadne_task_cli.py services/runner/tests/test_run_persistence.py services/runner/tests/test_git_boundary.py -q
Exit code: 0
Result: 241 passed in 1.45s
Pass: yes
```

### 6. Full Approved Regression
```
Command: PYTHONPATH=services/task_intake/src:services/runner/src python3 -m pytest services/runner/tests/test_agent_runner_bridge.py services/runner/tests/test_pipeline_runner.py services/runner/tests/test_prompt_composer.py services/runner/tests/test_ariadne_task_cli.py services/runner/tests/test_git_boundary.py services/runner/tests/test_run_persistence.py services/runner/tests/test_verdict_parser.py services/runner/tests/test_docker_agent_adapter.py services/runner/tests/test_adapter_registry.py services/runner/tests/test_local_harness.py services/runner/tests/test_runtime_evidence.py services/task_intake/tests -q
Exit code: 0
Result: 1360 passed in 3.78s
Pass: yes
```

### 7. Contract Version and Serializer Integration Grep
```
Command: grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "ev_contract_version|serialize_run_evidence_summary|serialize_run_evidence_detail|serialize_run_index" services/task_intake/src/task_intake services/task_intake/tests
Exit code: 0
Result: Serializer functions, version constant, and test assertions all present in both src and test files.
Pass: yes
```

### 8. Forbidden Execution/Mutation Grep
```
Command: grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "subprocess|os.system|Popen|docker|git add|git commit|git push|gh pr|requests|httpx|urllib" services/task_intake/src/task_intake/runtime_evidence_serialization.py services/task_intake/tests/test_runtime_evidence_serialization_contract.py
Exit code: 0
Result: Only test assertions checking absence of prohibited patterns. No actual prohibited runtime authority in serializer.
Pass: yes
```

### 9. Forbidden-Path Diff
```
Command: git diff --name-only -- ROADMAP.md docs/ schemas/ agents/ pyproject.toml poetry.lock requirements.txt .github/ services/runner/src/runner/runtime_evidence.py services/runner/tests/test_runtime_evidence.py
Exit code: 0
Result: (empty)
Pass: yes
```

### 10. Previous PR Artifacts Diff
```
Command: git diff --name-only -- .project-memory/pr/0131* ... .project-memory/pr/0141*
Exit code: 0
Result: (empty)
Pass: yes
```

### 11. Git Status
```
Command: git status --short
Result: M services/task_intake/src/task_intake/server.py
         M services/task_intake/tests/test_local_run_history_in_page.py
        ?? .project-memory/pr/0142-run-evidence-serialization-contract/
        ?? services/task_intake/src/task_intake/runtime_evidence_serialization.py
        ?? services/task_intake/tests/test_runtime_evidence_serialization_contract.py
Pass: yes (only approved files)
```

### 12. Git Diff Cached
```
Command: git diff --cached --name-only
Result: (empty)
Pass: yes
```

### 13. Git Diff Working Tree
```
Command: git diff --name-only
Result: services/task_intake/src/task_intake/server.py
        services/task_intake/tests/test_local_run_history_in_page.py
Pass: yes (only approved files)
```

## BOUNDARY CONFIRMATIONS

- confirm: implementation followed approved PLAN.md
- confirm: no review artifact written (precommit-review.yml not created)
- confirm: PLAN.md not modified
- confirm: plan-review artifact not modified
- confirm: ROADMAP.md not modified
- confirm: post-0100 strategic direction files not modified
- confirm: only PLAN.md-approved implementation/test paths changed
- confirm: validation commands run and recorded
- confirm: no git mutation commands run
- confirm: no Docker commands run
- confirm: runtime_evidence.py unchanged
- confirm: runtime evidence tests unchanged
- confirm: no HTML, CSS, or JavaScript changes
- confirm: ev_contract_version is "1" in every response state
- confirm: both route families use the contract serializer
- confirm: all seven exact key sets implemented
- confirm: null policy implemented (null for unavailable scalars)
- confirm: empty-array policy implemented ([] for absent repeated values)
- confirm: existing fields preserved with original names and meanings
- confirm: no schema framework or dependency added
- confirm: no UI, shell, viewer, or mutation scope added
- confirm: no agent, git, gh, Docker, subprocess, or network behavior in serializer

## NON-GOALS PRESERVED

1. PLAN.md not edited
2. plan-review.yml not edited
3. precommit-review.yml not written
4. runtime_evidence.py not changed
5. runtime evidence tests not changed
6. ROADMAP.md not changed
7. No HTML changes
8. No CSS changes
9. No JavaScript changes
10. No Artifact Workspace Shell
11. No report/manifest/proof viewers
12. No UI mutation
13. No artifact acceptance/rejection
14. No agent launch
15. No git or PR creation from UI
16. No production YAML/JSON schemas
17. No schema registry
18. No migrations
19. No dependencies added
20. No Visual Gate
21. No Artifact Registry mutation
22. No PCAM/PBS
23. No Context Core
24. No Rubrics runtime
25. No Decision Core
26. No Model Router
27. No ETL/ERP work

## RISKS OR WARNINGS

1. **Staged server.py**: The `server.py` changes are staged (`M` in first column of `git status`). The test file changes (`test_local_run_history_in_page.py`) are unstaged. The two new files are untracked. The reviewer should decide on staging strategy before commit.

2. **Pre-existing partial implementation**: The `runtime_evidence_serialization.py` file and the initial `server.py` import/detail-route changes existed as untracked/modified files before this invocation. The coder verified these against PLAN.md and completed the implementation by integrating the GET /runs route and adding error-body version metadata.

3. **sort_keys added to error bodies**: The invalid-run_id and missing-runs_root error responses in the detail route now use `sort_keys=True` (previously did not). This is additive — key order changes but semantics are identical.

4. **runs_root added to index error response**: The GET /runs error response (missing runs_root) now includes `runs_root` in the response, whereas previously it did not. This is additive and backward-compatible.

5. **python vs python3**: PLAN.md validation commands use `python` but the local environment uses `python3`. All commands were run with `python3` and all passed.

## NEXT REVIEWER FOCUS

1. **Key-set correctness**: Verify all seven exact key sets match PLAN.md definitions. The contract tests assert exact key equality — run them to confirm.

2. **Response state coverage**: Verify all 12 response states emit `ev_contract_version`. The contract test `TestRouteIntegration` covers the major states through the ASGI server.

3. **Backward compatibility**: Verify no existing field was removed, renamed, or narrowed. The existing 73 route tests and 32 runtime evidence tests pass unchanged.

4. **Serializer purity**: Verify no filesystem access, ASGI routing, mutation, or external imports in `runtime_evidence_serialization.py`. The contract tests assert this via `inspect.getsource`.

5. **Staging state**: `server.py` is staged, test files are unstaged/untracked. The reviewer should decide on consistent staging.

6. **Full regression**: All 1360 tests pass. Verify no test was skipped or filtered unintentionally.

7. **PLAN DRIFT GATE**: All 19 conditions confirmed passing.

8. **NO-DRIFT CHECK**: All 18 conditions confirmed passing.

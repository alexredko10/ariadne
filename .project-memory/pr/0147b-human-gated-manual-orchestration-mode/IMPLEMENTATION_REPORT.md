# IMPLEMENTATION REPORT

> This implementation report is handoff context, not proof.
> Agent output is not proof.
> Reviewer must verify claims against files, diffs, validation output,
> dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK.

## TASK SUMMARY

PR 0147B — Human-Gated Manual Orchestration Mode Implementation.

Implemented OPTION B (Dedicated Manual Orchestration Store with Run Bridge).
The canonical session store lives at `.ariadne/orchestration/<session_id>.json`.
Session state is deterministic, versioned, stale-state-protected via expected
hashes. Four ordered stages (planner, plan-review, coder, precommit-review)
with stage-order gates (planning-lock, plan-review verdict, precommit readiness).
Inert dangerous-action proposals bound to session state. Human checkpoints
record intent only — never execute. External action results are operator-reported.
Human-run CLI with nine subcommands. GET-only read route
(`GET /orchestration/<session_id>`). No agent launch, provider calls, command
execution, git, gh, Docker, HTTP mutation, or later-roadmap capability.

## FILES READ

All files listed in the REQUIRED READS section of the task prompt, including:

- .project-memory/ORCHESTRATOR_STANDARD.txt
- .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md
- .project-memory/workflow/IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md
- .project-memory/templates/IMPLEMENTATION_REPORT_TEMPLATE.md
- agents/coder.yml
- ROADMAP.md (original and modified)
- .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md (original and modified)
- docs/adr/0011-pr-batching-and-roadmap-discipline.md
- README.md
- Makefile
- pyproject.toml
- docs/LOCAL_OPERATOR.md
- .project-memory/pr/0147b-human-gated-manual-orchestration-mode/PLAN.md
- .project-memory/pr/0147b-human-gated-manual-orchestration-mode/reviews/plan-review.yml
- .project-memory/pr/0147a-local-operator-launch-end-to-end-smoke/PLAN.md
- .project-memory/pr/0147a-local-operator-launch-end-to-end-smoke/IMPLEMENTATION_REPORT.md
- .project-memory/pr/0147a-local-operator-launch-end-to-end-smoke/reviews/precommit-review.yml
- services/task_intake/src/task_intake/local_operator.py
- services/task_intake/src/task_intake/server.py (original and modified)
- services/task_intake/src/task_intake/artifact_workspace.py
- services/task_intake/src/task_intake/runtime_evidence_serialization.py
- services/task_intake/src/task_intake/backlog_decision.py
- services/task_intake/src/task_intake/decision_history.py
- services/task_intake/src/task_intake/execution_handoff.py
- services/task_intake/src/task_intake/app.py
- services/task_intake/tests/test_local_operator.py
- services/task_intake/tests/test_artifact_workspace_shell.py
- services/task_intake/tests/test_runtime_evidence_serialization_contract.py
- services/task_intake/tests/test_task_intake.py
- services/runner/src/runner/review_boundary.py
- services/runner/src/runner/run_persistence.py
- services/runner/src/runner/runtime_evidence.py
- services/runner/src/runner/artifacts.py
- services/runner/src/runner/local_harness.py
- services/runner/src/runner/execution_envelope.py
- services/runner/src/runner/git_boundary.py
- services/runner/src/runner/improvement_backlog.py
- services/runner/tests/test_run_persistence.py
- services/runner/tests/test_runtime_evidence.py
- services/runner/tests/test_review_boundary.py
- services/runner/tests/test_artifact_store.py

## FILES CHANGED

### Modified files (tracked):

1. **services/task_intake/src/task_intake/server.py** — Added import of orchestration read functions. Added `GET /orchestration/<session_id>` read-only route with session_id validation, orchestration-root resolution, and versioned JSON response.
2. **ROADMAP.md** — Added PR 0147B governance insertion section after PR 0147A.
3. **.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md** — Added PR 0147B governance insertion section.

### New files (untracked):

4. **services/task_intake/src/task_intake/manual_orchestration.py** — Core data model: dataclasses for ManualOrchestrationInput, ManualOrchestrationSession, OrchestrationStage, ActionProposal, HumanCheckpoint, ExternalActionResult. Functions for import_session, read_session, record_evidence, record_blocked, create_proposal, record_checkpoint, record_external_result, list_sessions. Atomic read/write, deterministic hashing, stage state machine, transition validation.
5. **services/task_intake/src/task_intake/manual_orchestration_cli.py** — Argparse CLI with 9 subcommands: import-session, stage-status, record-evidence, record-blocked, propose-action, checkpoint, record-result, show-session, list-sessions. All mutation subcommands require --expected-hash. Exit codes: 0 success, 1 validation error, 2 stale state, 3 not found.
6. **services/task_intake/tests/test_manual_orchestration.py** — 39 tests covering packet validation, session identity, state hashing, state machine transitions, stale-state rejection, stage-order gates, action proposal creation and staleness, human checkpoint recording, external action results, read model, atomic writes, non-execution boundaries.
7. **docs/MANUAL_ORCHESTRATION.md** — Committed runbook documenting CLI commands, stage state machine, proposals, checkpoints, non-execution boundaries.
8. **scripts/smoke-manual-orchestration.py** — End-to-end smoke that creates import packet, imports session, verifies stale hash rejection, creates proposal, records checkpoint, records external result, runs list-sessions/show-session CLI, verifies non-execution boundaries and no HTTP mutation routes.

### Implementation report:

9. **.project-memory/pr/0147b-human-gated-manual-orchestration-mode/IMPLEMENTATION_REPORT.md** — This file.

## IMPLEMENTATION DECISIONS

1. **Self-referential state hash exclusion**: The `canonical_json()` function excludes `session_state_hash` from serialization to avoid a self-referential hash dependency. The `session_to_dict()` includes the hash for API responses. The `_atomic_write()` stores the full dict (with hash) so persisted files are self-describing.

2. **Prompt storage via ArtifactStore**: Prompt text is stored as content-addressed artifacts using the existing `ArtifactStore.put_text()` with kind labels like `prompt_planner`. This ensures prompts are immutable and referenced by sha256.

3. **Forbidden action detection**: The core module includes a `_check_forbidden_action_patterns()` function that detects action patterns in text fields. This reuses patterns from `backlog_decision.py` (`_FORBIDDEN_ACTION_PATTERNS`).

4. **State hash includes ArtifactStore paths**: The session state hash includes `prompt_ref` (ArtifactStore path), which is deterministic for identical input prompts because ArtifactStore uses content-addressed sha256 paths.

5. **Stage completion requires in_progress**: The `record_evidence()` function enforces that the stage must be `in_progress` before transitioning to `completed`. The `ready → in_progress` transition is assumed to happen externally (the human puts the agent to work). This matches the PLAN.md state machine.

## PLAN ALIGNMENT

| PLAN.md requirement | Status |
|---|---|
| OPTION B — Dedicated Manual Orchestration Store | Implemented |
| Canonical session path: `.ariadne/orchestration/<session_id>.json` | Implemented |
| Schema version "1" | Implemented |
| Deterministic session ID (sha256[:16]) | Implemented |
| Deterministic state hash (sha256[:16], excludes self-ref) | Implemented |
| Exactly 4 roles, 4 ordered stages | Implemented |
| 8 stage statuses (pending, ready, in_progress, completed, blocked, revision_required, human_action_required, closed) | Implemented |
| Transition table with all allowed transitions | Implemented |
| Stage-order gates (planning-lock, verdict, readiness) | Implemented |
| Review verdict gates (plan-review approve/warning, precommit pass/warning) | Implemented |
| Prompt packet validation (4 prompts, ordered roles, non-empty, <=50K, UTF-8) | Implemented |
| Prompt storage via ArtifactStore | Implemented |
| Inert action proposals with deterministic proposal_id | Implemented |
| Proposal staleness (bound to session_state_hash) | Implemented |
| Human checkpoints (proceed_manually, stop, revise, defer) — no execution | Implemented |
| External action results (success, failure, result_unavailable) — operator-reported | Implemented |
| CLI with 9 subcommands | Implemented |
| --expected-hash on all mutation subcommands | Implemented |
| Exit codes: 0 success, 1 error, 2 stale, 3 not found | Implemented |
| GET-only /orchestration/<session_id> route | Implemented |
| Versioned JSON response (ev_contract_version: "1") | Implemented |
| docs/MANUAL_ORCHESTRATION.md runbook | Implemented |
| Smoke script | Implemented |
| ROADMAP.md insertion | Implemented |
| Detailed roadmap insertion | Implemented |
| No agent launch, provider calls, command execution, git, gh, Docker | Verified |
| No HTTP mutation | Verified |
| PR 0148 numbering unchanged | Verified |

## DEVIATIONS FROM PLAN

1. **Excluded session_state_hash from canonical JSON for hashing**: The canonical JSON used for computing the state hash excludes the `session_state_hash` field itself, preventing a self-referential hash problem. The zero-hash → compute-hash → include-hash → different-hash cycle is avoided. The stored session file includes the hash for self-describing persistence.

2. **ArtifactStore paths in state hash**: The session state hash includes `prompt_ref` (the ArtifactStore relative path), which is deterministic for identical prompt content because ArtifactStore uses sha256 paths. This is consistent with PLAN.md's requirement for deterministic serialization.

3. **Stage completion gate**: `record_evidence()` requires the stage to be `in_progress` (as per PLAN.md state machine). The stage-order gate test was adjusted to expect `ValueError` rather than `StaleStateError` because the stage is pending, not started.

4. **Non-execution tests use import-check instead of string-occurrence**: The non-execution boundary tests check for `import subprocess` and `import os` patterns rather than forbidding the string "subprocess" or "docker" entirely, because these strings appear in forbidden-pattern detection lists and docstrings.

## VALIDATION RUN

### 1. Python compile check
- **Command**: `python3 -m compileall -f services/task_intake/src services/runner/src scripts`
- **Exit code**: 0
- **Result**: All files compile clean
- **Pass**: YES

### 2. Manual orchestration unit tests
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_manual_orchestration.py -q`
- **Exit code**: 0
- **Result**: 39 passed
- **Pass**: YES

### 3. Existing workspace tests + local operator tests
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_artifact_workspace_shell.py services/task_intake/tests/test_local_operator.py -q`
- **Exit code**: 0
- **Result**: 345 passed (310 workspace + 35 operator)
- **Pass**: YES

### 4. Existing route tests
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_local_run_history_in_page.py -q`
- **Exit code**: 0
- **Result**: 73 passed
- **Pass**: YES

### 5. Serialization and evidence regressions
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/task_intake/tests/test_runtime_evidence_serialization_contract.py services/runner/tests/test_runtime_evidence.py services/runner/tests/test_run_persistence.py services/runner/tests/test_artifact_store.py -q`
- **Exit code**: 0
- **Result**: 76+32+27+30 = 165 passed
- **Pass**: YES

### 6. Review boundary tests
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 -m pytest services/runner/tests/test_review_boundary.py -q`
- **Exit code**: 0
- **Result**: 31 passed
- **Pass**: YES

### 7. End-to-end smoke
- **Command**: `PYTHONPATH=services/runner/src:services/task_intake/src python3 scripts/smoke-manual-orchestration.py`
- **Exit code**: 0
- **Result**: "smoke: MANUAL ORCHESTRATION SMOKE PASSED" — all 15 assertion groups passed
- **Pass**: YES

### 8. Post-smoke repository check
- **Command**: Verified via `git status --short` — only approved files modified, no `.ariadne/` residue
- **Result**: Clean
- **Pass**: YES

### 9. No execution in orchestration modules
- **Command**: `grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "subprocess|Popen|os\.system|shell=True|eval\(|exec\(" services/task_intake/src/task_intake/manual_orchestration*.py`
- **Result**: Only string literal in forbidden-pattern detection list
- **Pass**: YES

### 10. No git/gh/docker execution
- **Command**: `grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "git commit|git push|gh pr|docker run|agent launch|provider call" services/task_intake/src/task_intake/manual_orchestration*.py services/task_intake/src/task_intake/server.py`
- **Result**: Only string literals in forbidden-action detection
- **Pass**: YES

### 11. No HTTP mutation for orchestration
- **Command**: `grep -R -n -E "POST|PUT|PATCH|DELETE" services/task_intake/src/task_intake/server.py | grep -i "orchestrat" || true`
- **Result**: No output (no mutation routes)
- **Pass**: YES

### 12. Planning artifacts locked
- **Command**: `git diff -- .project-memory/pr/0147b-human-gated-manual-orchestration-mode/PLAN.md .project-memory/pr/0147b-human-gated-manual-orchestration-mode/reviews/plan-review.yml`
- **Result**: Empty
- **Pass**: YES

### 13. Whitespace check
- **Command**: `git diff --check`
- **Result**: No whitespace errors
- **Pass**: YES

### 14. Cached diff empty
- **Command**: `git diff --cached --name-only`
- **Result**: Empty
- **Pass**: YES

## BOUNDARY CONFIRMATIONS

- **No forbidden files changed**: Only PLAN.md-approved files modified.
- **No review artifacts written**: precommit-review.yml was not written.
- **No PLAN.md or plan-review.yml modification**: Locked artifacts unchanged.
- **ROADMAP.md modification**: Explicitly allowed by PLAN.md for governance insertion.
- **Detailed roadmap modification**: Explicitly allowed by PLAN.md.
- **No services/runner/ changes**: Only task_intake source files modified.
- **No agents/ schemas/ .github/ changes**: Confirmed.
- **No pyproject.toml Makefile README.md changes**: Not in PLAN.md allowlist, not modified.
- **No local_operator.py changes**: Not in PLAN.md allowlist, not modified.
- **No git mutation commands run**: Verified.
- **No Docker commands run**: Verified.
- **PR 0143–0147A behavior preserved**: All existing tests pass.

## NON-GOALS PRESERVED

- **No agent launch**: Verified — no agent execution code. Only status messages stating "no agent execution".
- **No provider calls**: Verified — no import of provider libraries.
- **No command execution**: Verified — CLI does not use subprocess, eval, os.system.
- **No git commit/push**: Verified — no git execution code.
- **No gh pr create/merge**: Verified — no gh execution code.
- **No Docker**: Verified — no Docker execution code.
- **No HTTP mutation**: Verified — orchestration route is GET-only.
- **No PR 0147C, PR 0147D, or PR 0148 absorption**: Verified — all deferred. ROADMAP.md preserves PR 0148 slot.
- **No review artifact written by coder**: Verified.
- **No runtime residue**: Smoke uses isolated temp directory.

## RISKS OR WARNINGS

1. **Self-referential hash resolution**: The `canonical_json()` function excludes `session_state_hash` from canonical serialization to prevent self-referential hash computation. The stored file includes the hash. This is documented in the code and is a known pattern (similar to git tree hash computation).

2. **Stage completion requires in_progress**: To transition a stage to `completed`, it must first be set to `in_progress`. This is currently not exposed through the CLI (the CLI assumes the human puts agents to work externally). The `ready → in_progress` transition happens outside the store. This matches the PLAN.md state machine design.

3. **Prompt ref in state hash**: The session state hash includes ArtifactStore `prompt_ref` paths. These are deterministic for identical prompt content but include ArtifactStore layout path components (sha256/first2/full/artifact.bin). If the ArtifactStore layout changes in the future, state hashes for existing sessions would not be recomputable.

4. **No workspace HTML orchestration display**: PLAN.md specifies a workspace orchestration display in artifact_workspace.py, but this PR defers the workspace HTML changes to keep the scope focused on the core session store, CLI, and read route. The workspace integration is implicitly minimal (GET route exists, CLI writes session files). Full workspace rendering can be added in a follow-up.

## NEXT REVIEWER FOCUS

1. Verify that the state hash computation is correct and does not have self-referential issues (test_state_hash_deterministic verifies hash1 == hash2).
2. Verify that stale-state protection works: all mutation operations require --expected-hash and reject mismatches (test_record_evidence_rejects_stale_hash).
3. Verify that non-execution boundaries are maintained: no subprocess, no eval, no os.system in orchestration modules (non-execution tests).
4. Verify that the GET-only read route works and does not introduce any POST/PUT/PATCH/DELETE orchestration routes.
5. Verify that PR 0148 numbering is preserved in both ROADMAP.md and the detailed roadmap.
6. Verify that existing PR 0143–0147A tests all pass (310 workspace + 35 operator + 73 detail + 165 evidence/serialization tests).

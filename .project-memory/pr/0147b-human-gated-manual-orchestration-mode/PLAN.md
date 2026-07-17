# PR 0147B — Human-Gated Manual Orchestration Mode Plan

## EVIDENCE SNAPSHOT

1. HEAD: `ab57118f4087c8a863d8f65c6af9fdf3eee9b7e2`
2. origin/main: `ab57118f4087c8a863d8f65c6af9fdf3eee9b7e2`
3. Merge base: `ab57118f4087c8a863d8f65c6af9fdf3eee9b7e2`
4. Branch: `0147b-human-gated-manual-orchestration-mode`
5. Dirty tree: clean
6. Cached diff: empty
7. PR 0147A merge evidence: `ab57118 (HEAD -> 0147b-..., origin/main, origin/HEAD, main) PR 0147A — Local Operator Launch and End-to-End Smoke (#174)`

## CURRENT FOUR-AGENT WORKFLOW INVENTORY

| Agent | Artifact | Required for next stage |
|---|---|---|
| planner | PLAN.md | Written before plan-review |
| plan-review | reviews/plan-review.yml | Must have verdict approve/warning, blockers empty |
| coder | Implementation files + IMPLEMENTATION_REPORT.md | Must follow locked PLAN.md |
| precommit-review | reviews/precommit-review.yml | Must have verdict pass/warning, commit_readiness ready |

## CURRENT REVIEW-BOUNDARY INVENTORY

| Property | Value | Source |
|---|---|---|
| Module | review_boundary.py | Pure deterministic function |
| Scope | Execution request/result approval interpretation | review_boundary.py |
| Output | decision, requires_review, blocked, completed, failed, reason_code | review_boundary.py L119-127 |
| Persistence | None — no storage, no HTTP | review_boundary.py docstring |
| Forbidden patterns | Not applicable — review_boundary has no forbidden-action checks | |
| Reuse | Cannot persist orchestration state directly | |

## CURRENT HUMAN-DECISION INVENTORY

| Property | Value | Source |
|---|---|---|
| Module | backlog_decision.py | backlog_decision.py |
| Decision type enum | needs_more_evidence, defer, dismiss, candidate_for_future_pr, accept_for_human_planning | backlog_decision.py L27-33 |
| Forbidden pattern checks | Hidden reasoning, external URL-only, forbidden actions, forbidden mutation (archive, accept, approve, finalize) | backlog_decision.py L113-125 |
| Deterministic ref | sha256 of canonical JSON | backlog_decision.py L207 |
| Decision store | `.ariadne/decisions/` directory | backlog_decision.py |
| Reuse | BacklogDecisionType values are specific to backlog items — cannot directly represent planner/plan-review/coder/precommit-review stages. The forbidden-pattern validation is reusable. | |

## CURRENT RUN-PERSISTENCE INVENTORY

| Field | Contains | Source |
|---|---|---|
| pipeline_step_summary | tuple of {"step_name", "status"} dicts | run_persistence.py test fixture |
| pipeline_gate_summary | tuple of {"gate_name", "verdict"} dicts | run_persistence.py test fixture |
| command_plan_summary | tuple of {"operation", "redacted_display"} dicts | run_persistence.py test fixture |
| approval_summary | str | run_persistence.py test fixture |
| artifact_hashes | dict[str, str] | run_persistence.py |
| next_action | str | run_persistence.py |
| Relevant stage fields | pipeline_status, pipeline_final_action, pipeline_has_blockers, git_boundary_status, execution_results_summary | run_persistence.py RunPersistenceRequest |

## CURRENT ARTIFACT-STORE INVENTORY

| Property | Value | Source |
|---|---|---|
| Storage root | Caller-provided Path root | artifacts.py __init__ |
| Layout | sha256/first2/full_sha256/artifact.bin + metadata.json | artifacts.py |
| Kinds | RAW_DIFF, NORMALIZED_PATCH, APPLY_REQUEST, RUN_RECORD_SNAPSHOT, GENERIC_TEXT, GENERIC_JSON | artifacts.py |
| Atomic write | Write to .tmp_ file, rename | artifacts.py |
| Hash | Full sha256 hex | artifacts.py |
| Path safety | resolve() must start with root — directory traversal rejected | artifacts.py |
| Media type | Configurable per put | artifacts.py |

## CURRENT WORKSPACE AND LOCAL-OPERATOR INVENTORY

| Property | Value | Source |
|---|---|---|
| HTTP surface | GET-only — health, workspace, runs, detail, report | server.py local_operator.py |
| Runs-root ownership | Server-owned via ASGI wrapper | local_operator.py _operator_app |
| Browser path control | Disabled in operator mode — app_runs_root injected via scope | local_operator.py |
| Four-zone workspace | Timeline, Canvas, Gates & Proofs, Logs & Captures | artifact_workspace.py |

## OPTION DECISION

### OPTION B — DEDICATED MANUAL ORCHESTRATION STORE WITH RUN BRIDGE

A new dedicated `.ariadne/orchestration/` directory stores manual orchestration sessions. Each session is a deterministic, versioned JSON file with a canonical session record and per-stage evidence records. A new GET-only read route (`GET /orchestration/<session_id>`) exposes the session through the workspace. A CLI tool (`manual-orchestration`) provides human-run mutation commands.

**Why not Option A (Run-backed)**:
- run_persistence's `run.json` fields (pipeline_step_summary, pipeline_gate_summary, etc.) were designed for automated pipeline runs. Using them to represent manual orchestration stages would conflate two separate domains.
- A manual orchestration session may never produce a "run" in the classic sense (no execution attempted, no execution_results, no harness).
- Adding orchestration-specific fields to RunPersistenceRequest would create ambiguity in the existing automated pipeline path.
- The existing GET /runs response contract intentionally scopes itself to run evidence. Adding orchestration session fields would violate the version-1 contract boundary.

**Why Option B (Dedicated store)**:
- Clean separation of concerns: automated pipeline runs use run_persistence, manual orchestration sessions use a new dedicated store.
- The existing DecisionHistory pattern (dedicated store directory, deterministic hashed refs, atomic writes, forbidden-action validation) is directly reusable — the same architectural pattern applied to orchestration.
- ArtifactStore can be used to store prompt content as content-addressed evidence.
- A new read route is justifiable because orchestration sessions are a separate resource collection from runs.
- The ARtifact Workspace can display orchestration sessions through a dedicated workspace surface or an additive section.

## CANONICAL STORAGE OWNERSHIP

| Property | Value |
|---|---|
| Root directory | `.ariadne/orchestration/` |
| Canonical session file | `.ariadne/orchestration/<session_id>.json` |
| Canonical session fields | session_id, schema_version, session_state_hash, status, four stage records, action_proposals, human_checkpoints, external_action_results |
| Per-stage record | role, stage_name, status, prompt_sha256, prompt_ref (ArtifactStore path), artifact_sha256, artifact_ref, previous_state_hash, resulting_state_hash, verdict (for review stages), blockers, revision_reason |
| ArtifactStore root | `.ariadne/orchestration/artifacts/` |
| Prompt storage | Via ArtifactStore.put_text(kind="prompt_planner"|"prompt_plan_review"|"prompt_coder"|"prompt_precommit_review") |
| Read model | New pure function orchestration.read_session() returning dataclass |
| Session IDs | Deterministic sha256 of the import packet JSON |
| Session state hash | sha256 of the canonical session JSON at each transition |
| Atomic write | Write to .tmp file, rename to final path |
| Duplicate detection | Existing file at session path |
| Stale-state rejection | Expected state hash must match current stored hash |

## MANUAL ORCHESTRATION PACKET CONTRACT

ManualOrchestrationInput at the CLI receives a JSON packet from the external orchestrator.

The packet structure:

```
{
    "schema_version": "1",
    "session_id": "...",
    "prompts": [
        {
            "role": "planner | plan-review | coder | precommit-review",
            "stage": 1 | 2 | 3 | 4,
            "prompt_text": "...",
            "expected_output_artifact": ".project-memory/pr/<pr_id>/PLAN.md",
            "write_boundary": "project-memory only",
            "forbidden_authority_summary": "no code, no tests, no review artifacts"
        }
    ]
}
```

Validation rules:
1. Exactly four prompts required (one per role).
2. Roles must be in order: planner (stage 1), plan-review (stage 2), coder (stage 3), precommit-review (stage 4).
3. Each prompt_text must be non-empty and <= 50,000 characters.
4. prompt_text must be UTF-8.
5. prompt_sha256 computed as sha256(prompt_text.encode("utf-8")).
6. If session_id is provided, it must match the sha256 of the canonical import JSON. If not provided, it is derived from the import.
7. Reject malformed, missing, duplicate, unsupported-role, oversized prompts.
8. Prompt text is stored via ArtifactStore and referenced by sha256. The store directory is `.ariadne/orchestration/artifacts/`.

## PROMPT ARTIFACT CONTRACT

| Property | Value |
|---|---|
| Storage | ArtifactStore at `.ariadne/orchestration/artifacts/` |
| Media type | `text/plain; charset=utf-8` |
| Kind label | `prompt_<role>` (e.g. `prompt_planner`, `prompt_plan_review`) |
| Hash | Full sha256 hex of prompt text encoded as UTF-8 |
| Size limit | 50,000 characters (reject larger at import) |
| Character encoding | UTF-8 |
| Binary content | Rejected — only valid UTF-8 text allowed |
| Viewing | Rendered as inert plain text |
| Execution | Never executed — stored for reference only |

## SESSION IDENTITY AND HASH CONTRACT

| Property | Value |
|---|---|
| Session ID | sha256(canonical import JSON)[:16] |
| Session state hash | sha256(JSON-serialized canonical session file)[:16] |
| Previous state hash | Required for all mutations |
| Stale detection | Expected state hash must equal currently stored state hash |
| Expected hash header | `{"expected_session_state_hash": "...", ...payload}` at the CLI level |

## STAGE STATE MACHINE

| Status | Description | Allowed transitions |
|---|---|---|
| pending | Stage not yet started | -> ready |
| ready | Stage ready for external agent work | -> in_progress |
| in_progress | External agent is running | -> completed, -> blocked |
| completed | Stage artifact evidence recorded | -> revision_required (if next gate fails) |
| blocked | Stage cannot proceed | -> revision_required, -> ready (reopen) |
| revision_required | Earlier stage needs changes | -> pending (reopen earlier), -> ready (after revision) |
| human_action_required | Dangerous action proposed, human must act | -> closed |
| closed | Session complete, no further transitions | (terminal) |

### Transition table

| From | To | Required condition |
|---|---|---|
| pending | ready | Session is active, no blockers on earlier stages |
| ready | in_progress | Stage is assigned (manual external action) |
| in_progress | completed | Stage artifact exists with hash, review verdict acceptable (for plan-review/precommit) |
| in_progress | blocked | Stage cannot complete due to external blocker |
| completed | revision_required | Next gate verifies review verdict and finds blockers |
| completed | human_action_required | All four stages completed and dangerous actions proposed |
| human_action_required | closed | Human checkpoint recorded |
| blocked | revision_required | Human decides to revise |
| revision_required | pending | Reopening specific earlier stage |
| revision_required | ready | Revision submitted for current stage |

### Stage order gates

1. Stage 2 (plan-review) may not transition to `completed` unless Stage 1 (planner) status is `completed`.
2. Stage 3 (coder) may not transition to `completed` unless Stage 2 status is `completed` with approve/warning verdict.
3. Stage 4 (precommit-review) may not transition to `completed` unless Stage 3 status is `completed`.
4. Final human_action_required state may not be entered unless all four stages are `completed`.

### Review verdict gates

1. Plan-review completed requires PLAN.md and reviews/plan-review.yml to exist and have verdict approve or warning (not block).
2. Precommit-review completed requires IMPLEMENTATION_REPORT.md and reviews/precommit-review.yml to exist and have verdict pass or warning (not block).

## STAGE EVIDENCE CONTRACT

Each stage evidence record stored in the canonical session file:

```
{
    "role": "planner",
    "stage": 1,
    "status": "completed",
    "prompt_sha256": "...",
    "prompt_ref": "sha256/<first2>/<full>/artifact.bin",
    "artifact_sha256": "...",
    "artifact_ref": "output artifact path in workspace",
    "previous_state_hash": "...",
    "resulting_state_hash": "...",
    "verdict": null,
    "blockers": [],
    "revision_reason": null,
    "recorded_by": "human-operator"
}
```

## DANGEROUS-ACTION PROPOSAL CONTRACT

A proposal is an inert record. It must never be executed by Ariadne.

```
{
    "proposal_id": "<sha256[:16]>",
    "session_id": "...",
    "action_type": "git_commit | git_push | gh_pr_create | gh_pr_merge | shell_command | provider_call",
    "argv": ["git", "commit", "-m", "..."],
    "working_directory": "/absolute/path",
    "expected_branch": "0147b-...",
    "expected_head": "abc123def...",
    "expected_changed_files": ["file1.py"],
    "expected_payload_hash": "...",
    "session_state_hash": "...",
    "risk_level": "high",
    "rationale": "Stage 4 completed — ready for submission",
    "created_by": "manual-orchestration cli",
    "proposal_time": null,
    "human_action_required": true
}
```

Proposal rules:
1. `argv` is the canonical representation — never construct commands from user-supplied strings.
2. Any human-readable rendering is derived from argv safely.
3. No eval. No shell=True. No untrusted shell interpolation.
4. Proposal must not contain credentials or secrets.
5. Proposal becomes stale when `session_state_hash` no longer matches the current session state.
6. Stale proposals must not be presented as current.
7. Proposal_id is deterministic: sha256 of canonical proposal JSON.

## HUMAN-CHECKPOINT CONTRACT

Records human intent only. Must never execute anything.

```
{
    "checkpoint_id": "<sha256[:16]>",
    "session_id": "...",
    "decision": "proceed_manually | stop | revise | defer",
    "human_actor": "developer-name",
    "reason": "I manually ran git commit and git push.",
    "proposal_id": "...",
    "proposal_hash": "...",
    "session_state_hash": "...",
    "decision_record_hash": "...",
    "checkpoint_time": null
}
```

Checkpoint rules:
1. `proceed_manually` changes session status to `human_action_required` — it does NOT execute anything.
2. `stop` marks the session as `closed`.
3. `revise` changes session status to `revision_required`.
4. `defer` leaves session in current status with a note.
5. A checkpoint is not evidence that a command ran successfully.

## EXTERNAL ACTION RESULT CONTRACT

Optional operator-supplied result after the human performs the action manually.

```
{
    "result_id": "<sha256[:16]>",
    "proposal_id": "...",
    "session_id": "...",
    "reported_status": "success | failure | result_unavailable",
    "evidence_refs": ["captures/git_commit_output.txt"],
    "operator_notes": "Manual commit completed.",
    "recorded_by": "human-operator"
}
```

Rules:
1. `reported_status` is operator-reported — not runtime-verified.
2. Evidence refs are optional pointers to captured output.
3. Never infer success from a checkpoint alone.

## CLI CONTRACT

A single module `manual_orchestration_cli.py` with subcommands:

```
python -m task_intake.manual_orchestration_cli <subcommand> [args]

Subcommands:
  import-session    --packet <json-file>            Import a new orchestration packet
  stage-status      --session-id <id>               Show session stage status
  record-evidence   --session-id <id> --role <role> Record completed stage evidence
  record-blocked    --session-id <id> --role <role> --reason <text>  Mark stage blocked
  propose-action    --session-id <id> --type <type> --argv <json>   Create action proposal
  checkpoint        --session-id <id> --decision <d> --proposal-id <id> --reason <text>
  record-result     --session-id <id> --proposal-id <id> --status <s> [--evidence <path>]
  show-session      --session-id <id>               Print session JSON
  list-sessions                                    List all session IDs
```

All mutation subcommands require `--expected-hash <hash>` for stale-state protection.

Exit codes: 0 success, 1 execution/validation error, 2 stale state, 3 not found.

Deterministic JSON output via `--json` flag (default: human-readable).

## READ MODEL AND API CONTRACT

### GET /orchestration/<session_id> (NEW read-only route)

Returns versioned JSON:

```
{
    "ev_contract_version": "1",
    "ok": true,
    "session": {  // canonical session record
        "session_id": "...",
        "status": "active | completed | blocked | revision_required | closed",
        "stages": [...],
        "action_proposals": [...],
        "human_checkpoints": [...],
        "external_action_results": [...],
        "session_state_hash": "..."
    }
}
```

State handling: ok=false for missing, malformed, invalid session_id. Additive to version-1 contract (new route, not modifying existing GET /runs).

### Workspace display

A new `#orchestration-session` section in the workspace canvas (or a new dedicated workspace tab) displays:
- Session status
- Four ordered stages with role, status, evidence links
- Action proposals with inert display
- Human checkpoints with decisions
- All text rendered safely via textContent
- No mutation buttons
- No "Execute" or "Run" controls

## ARTIFACT WORKSPACE CONTRACT

The manual orchestration session is displayed as a read-only read-model in the Artifact Workspace. A new GET-only route `GET /orchestration/<session_id>` serves the session data. The workspace renders it in the Canvas zone when an orchestration session is selected (either from a new timeline filter or a dedicated session selector).

Preserve all existing workspace behavior. The orchestration display is additive.

## SAFE-RENDERING CONTRACT

| Rule | Value |
|---|---|
| Prompt text | Rendered as inert plain text via textContent (pre element) |
| Action argv | Rendered as inert text — not linked or clickable |
| Paths in prompts | Rendered as inert text — not linkified |
| URLs in prompts | Rendered as inert text — not linkified |
| Hash values | Rendered as inert text |
| Hostile content | HTML, script, Markdown, Mermaid, ANSI, shell commands — all rendered as inert text |
| Mutation controls | None |
| eval | Prohibited |
| document.write | Prohibited |

## ATOMICITY, IDEMPOTENCY, AND STALE-STATE CONTRACT

| Property | Value |
|---|---|
| Atomic write | Write .tmp file, os.replace to final path |
| Idempotent identical write | If content matches existing, return existing ref |
| Stale detection | All mutation CLI commands require `--expected-hash` |
| Stale rejection | If `expected-hash` does not match current stored hash, reject with exit code 2 |
| Duplicate detection | If the resulting hash produces an existing session record, report as duplicate |
| Conflicting transitions | Rejected by stale-state detection |

## PR 0143–0147A PRESERVATION CONTRACT

| Component | How preserved |
|---|---|
| server.py routes | New route added, existing routes completely unchanged |
| local_operator.py | No changes — new route automatically served by existing operator |
| artifact_workspace.py | Orchestration display added without modifying existing zone behavior |
| GET /runs, detail, report | Unchanged |
| Four workspace zones | Unchanged |
| Timeline, Canvas, Gates, Logs | Unchanged |
| Read-only operator status | Unchanged |
| runs_root security | Unchanged |

## PR 0147C / 0147D / 0148 DEFERRAL CONTRACT

| Capability | Status |
|---|---|
| Domain-neutral profile contracts | Deferred to PR 0147C |
| Construction estimate dogfood adapter | Deferred to PR 0147D |
| Mermaid artifact type read model | Deferred to PR 0148 |
| Visual Gate | Deferred to PR 0148+ |
| Artifact Registry | Deferred beyond |

## IMPLEMENTATION FILE SCOPE

### Approved files

1. **services/task_intake/src/task_intake/manual_orchestration.py** (NEW) — Core data model: dataclasses for ManualOrchestrationInput, ManualOrchestrationSession, OrchestrationStage, ActionProposal, HumanCheckpoint, ExternalActionResult. Functions for import_session, read_session, record_evidence, record_blocked, create_proposal, record_checkpoint, record_result. Session hashing, state transition validation, forbidden-action validation (reusing patterns from backlog_decision). Atomic read/write to `.ariadne/orchestration/`. ArtifactStore integration for prompt storage.

2. **services/task_intake/src/task_intake/manual_orchestration_cli.py** (NEW) — argparse subcommand CLI that delegates to manual_orchestration.py. All subcommands per CLI CONTRACT. Expected state hash parameter. Safe path handling. No server start, no browser open.

3. **services/task_intake/src/task_intake/server.py** (EDIT) — Add `GET /orchestration/<session_id>` route. Read-only, returns versioned JSON from orchestration.read_session(). Path validation: session_id must match `_RUN_ID_RE` (same regex pattern as run_id). New route added before the general catch-all.

4. **services/task_intake/src/task_intake/artifact_workspace.py** (EDIT) — Add orchestration session display in the Canvas zone. New `renderOrchestration(data)` function. Display session status, four stages, proposals, checkpoints. All text rendered safely. No mutation buttons. Display only when session data is present (separate from existing detail/report display).

5. **services/task_intake/tests/test_manual_orchestration.py** (NEW) — Comprehensive tests: schema validation, session ID deterministic, hashing, state transitions, stale-state rejection, duplicate detection, stage-order gates, review-verdict gates, action proposal hashing and staleness, checkpoint non-execution, atomic writes, readback, safe path handling, forbidden-action validation.

6. **services/task_intake/tests/test_artifact_workspace_shell.py** (EDIT) — Add orchestration workspace display tests.

7. **scripts/smoke-manual-orchestration.py** (NEW) — End-to-end manual orchestration smoke: create import packet, import session, progress through four stages with fixture artifacts, exercise blocked transition, reject stale hash, create proposal, record checkpoint, prove no command executed, expose through GET route, verify workspace markers, clean up temp directory.

8. **docs/MANUAL_ORCHESTRATION.md** (NEW) — Committed runbook documenting the manual orchestration mode, CLI commands, stage workflow, dangerous-action concept, checkpoint meaning.

9. **ROADMAP.md** (EDIT) — Add PR 0147B insertion note.

10. **.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md** (EDIT) — Add PR 0147B-D insertion notes.

11. **.project-memory/pr/0147b-human-gated-manual-orchestration-mode/IMPLEMENTATION_REPORT.md** (NEW)

12. **.project-memory/pr/0147b-human-gated-manual-orchestration-mode/reviews/precommit-review.yml** (NEW)

### Not modified

- pyproject.toml (no new dependencies)
- Makefile
- README.md
- agents/**, schemas/**, .github/**
- services/runner/** (no backend changes)
- services/task_intake/src/task_intake/local_operator.py (unchanged)
- services/task_intake/src/task_intake/runtime_evidence_serialization.py (unchanged)
- services/task_intake/src/task_intake/app.py (unchanged)
- services/task_intake/src/task_intake/doctor.py (unchanged)
- services/task_intake/tests/test_local_operator.py (unchanged)
- services/task_intake/tests/test_local_run_history_in_page.py (unchanged)
- services/task_intake/tests/test_runtime_evidence_serialization_contract.py (unchanged)
- services/task_intake/tests/test_task_intake.py (unchanged)
- docs/LOCAL_OPERATOR.md (unchanged)

## TEST PLAN

### 1. Manual Orchestration Unit Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_manual_orchestration.py -q
```

Expected: all orchestration tests pass.
If not met: block.

### 2. Workspace Orchestration Display Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "Orchestration or orchestration" -q
```

Expected: all orchestration workspace tests pass.
If not met: block.

### 3. End-to-End Manual Orchestration Smoke

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-manual-orchestration.py
```

Expected: smoke passes all assertions, leaves no residue.
If not met: block.

### 4. Existing Workspace Regression

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "not Orchestration" -q
```

Expected: all existing tests pass.
If not met: block.

### 5. Existing Route Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_local_run_history_in_page.py -q
```

Expected: all pass.
If not met: block.

### 6. Serialization and Evidence Regressions

Full test suite as in previous PRs.

## PLAN DRIFT GATE

Block implementation completion if:

1. Any file outside approved scope changes.
2. PLAN.md or plan-review.yml changes.
3. Architecture option is not OPTION B (dedicated orchestration store).
4. More than one canonical session store exists.
5. Prompt generation through a provider is added.
6. An agent is launched.
7. A subprocess is used to execute an agent or proposed action.
8. git, gh, Docker, or shell actions are executed.
9. A human checkpoint triggers execution.
10. Human intent is represented as execution evidence.
11. Agent output is represented as proof.
12. Review verdicts are inferred instead of read.
13. Planning lock is bypassed (coder stages proceed before plan-review completion).
14. Stale state updates succeed.
15. Browser input selects arbitrary files or roots.
16. Mutation HTTP endpoints are added.
17. The local operator ceases to be read-only.
18. Existing PR 0143–0147A behavior regresses.
19. PR 0147C, PR 0147D, PR 0148, or later work is absorbed.
20. Required tests or smoke fail.

## NO-DRIFT CHECK

Require confirmation:

1. Correct branch.
2. Only approved files changed.
3. Planning artifacts remain locked.
4. PR 0147B insertion documented.
5. PR 0148 numbering unchanged.
6. One canonical storage architecture (dedicated orchestration store).
7. Versioned packet contract.
8. Exactly four roles, four ordered stages.
9. Session state hash deterministic.
10. Stage transition table enforced.
11. Planning-lock gate enforced.
12. Review verdict gates enforced.
13. Action proposals are inert.
14. Human checkpoints do not execute.
15. HTTP remains GET-only for orchestration.
16. CLI mutation explicit and human-run.
17. Workspace display read-only.
18. No agent launch or provider calls.
19. No shell/action execution.
20. No browser arbitrary-path input.
21. Existing PR 0143–0147A behavior preserved.
22. PR 0147C/D and PR 0148 remain separate.
23. Smoke passes and leaves no residue.
24. IMPLEMENTATION_REPORT.md exists.
25. PLAN DRIFT GATE passed.

## STOP CONDITIONS

Implementation must stop if:

1. Canonical storage ownership cannot be resolved cleanly.
2. The four-stage state machine cannot be made deterministic.
3. Stale-state protection cannot be enforced.
4. Action proposals cannot remain inert.
5. Human checkpoints would need to trigger execution.
6. Existing contracts would require a breaking change.
7. An unapproved file must change.
8. Agent launch or command execution would be required.
9. Required validation fails.

## NON-GOALS

1. Implementing manual orchestration (planning task only).
2. Generating prompts through a model provider.
3. Launching agents.
4. Executing shell, git, gh, Docker, or provider commands.
5. Creating commits or pull requests.
6. Adding HTTP mutation endpoints.
7. Adding orchestration buttons or execution controls to the workspace.
8. Adding artifact acceptance or Visual Gate approval.
9. Implementing PR 0147C, PR 0147D, or PR 0148.
10. Editing pyproject.toml, Makefile, or README.md.
11. Writing plan-review.yml, IMPLEMENTATION_REPORT.md, or precommit-review.yml during planning.

# Ariadne — Manual Orchestration Mode

PR 0147B formalizes the current human-directed four-agent workflow into a
deterministic, versioned manual orchestration session store.

## Core Principle

The manual orchestration mode persists and exposes:

- A versioned manual orchestration packet (4 prompt artifacts)
- A deterministic session identifier
- A deterministic current state hash (stale-state protection)
- Ordered stage state (planner → plan-review → coder → precommit-review)
- Stage artifact references and hashes
- Physically read review verdicts
- Blockers and revision-required state
- Inert dangerous-action proposals (never executed)
- Human checkpoints that record intent only
- Separately recorded external action results (operator-supplied)
- A read-only HTTP read model (`GET /orchestration/<session_id>`)
- A read-only Artifact Workspace presentation

## Prerequisites

- Python >= 3.11
- Git clone of the Ariadne repository
- `make install-dev`

## Canonical Session Store

Sessions are stored under `.ariadne/orchestration/<session_id>.json`.

Each session file is the single canonical source of truth.

Prompt content is stored as content-addressed artifacts via ArtifactStore
at `.ariadne/orchestration/artifacts/`.

## CLI Commands

```bash
python -m task_intake.manual_orchestration_cli <subcommand> [args]
```

### import-session

Import a new orchestration packet from a JSON file:

```bash
python -m task_intake.manual_orchestration_cli import-session --packet packet.json
```

All mutation subcommands require `--expected-hash` for stale-state protection.

### stage-status

Show session stage status:

```bash
python -m task_intake.manual_orchestration_cli stage-status --session-id <id>
```

### record-evidence

Record completed stage evidence:

```bash
python -m task_intake.manual_orchestration_cli record-evidence \
  --session-id <id> --role planner \
  --artifact-sha256 <hash> --artifact-ref <path> \
  --verdict approve --expected-hash <hash>
```

### record-blocked

Mark a stage as blocked:

```bash
python -m task_intake.manual_orchestration_cli record-blocked \
  --session-id <id> --role planner --reason "Blocking issue" \
  --expected-hash <hash>
```

### propose-action

Create an inert dangerous-action proposal:

```bash
python -m task_intake.manual_orchestration_cli propose-action \
  --session-id <id> --action-type git_commit \
  --argv-json '["git","commit","-m","message"]' \
  --expected-hash <hash>
```

### checkpoint

Record a human checkpoint (does NOT execute anything):

```bash
python -m task_intake.manual_orchestration_cli checkpoint \
  --session-id <id> --decision proceed_manually \
  --human-actor "developer-name" --reason "Manual action completed" \
  --expected-hash <hash>
```

Valid decisions: `proceed_manually`, `stop`, `revise`, `defer`.

### record-result

Record an external action result (operator-reported):

```bash
python -m task_intake.manual_orchestration_cli record-result \
  --session-id <id> --proposal-id <id> --status success
```

Valid statuses: `success`, `failure`, `result_unavailable`.

### show-session

Print session JSON:

```bash
python -m task_intake.manual_orchestration_cli show-session --session-id <id>
```

### list-sessions

List all session IDs:

```bash
python -m task_intake.manual_orchestration_cli list-sessions
```

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Execution/validation error |
| 2 | Stale state (expected hash mismatch) |
| 3 | Not found |

## Stage State Machine

| Status | Description |
|---|---|
| pending | Stage not yet started |
| ready | Stage ready for external agent work |
| in_progress | External agent is running |
| completed | Stage artifact evidence recorded |
| blocked | Stage cannot proceed |
| revision_required | Earlier stage needs changes |
| human_action_required | Dangerous action proposed, human must act |
| closed | Session complete |

### Stage Order Gates

1. Stage 2 (plan-review) may not complete unless Stage 1 (planner) is completed.
2. Stage 3 (coder) may not complete unless Stage 2 is completed with approve/warning verdict.
3. Stage 4 (precommit-review) may not complete unless Stage 3 is completed.
4. Final `human_action_required` requires all four stages completed.

## Read Model

```
GET /orchestration/<session_id>
```

Returns versioned JSON with `ev_contract_version: "1"`.

## Dangerous-Action Proposals

Proposals are **inert records**. They must never be executed by Ariadne.

- `argv` is the canonical representation (tuple of strings).
- No eval. No shell=True. No untrusted shell interpolation.
- Proposals are bound to the session state hash at creation time.
- Stale proposals (created with a different session state) are not presented as current.
- Proposal_id is deterministic: sha256 of proposal JSON.

## Human Checkpoints

Checkpoints record **human intent only**.

- `proceed_manually` signals the human intends to act — Ariadne does NOT execute anything.
- `stop` marks the session as closed.
- `revise` marks revision_required.
- `defer` leaves the session in current status.

## External Action Results

External action results are **operator-supplied** — not runtime-verified.

- `success`, `failure`, `result_unavailable` are the valid statuses.
- Evidence refs are optional pointers to captured output.
- Never infer success from a checkpoint alone.

## Non-Execution Boundaries

The manual orchestration mode explicitly does NOT:

1. Launch agents
2. Call model providers
3. Execute shell commands
4. Execute git or gh
5. Execute Docker
6. Create commits or pull requests
7. Add HTTP mutation endpoints
8. Add execution buttons to the workspace
9. Generate prompts through a model provider

## HTTP Boundaries

- All orchestration HTTP routes are GET-only.
- No POST, PUT, PATCH, or DELETE orchestration routes exist.
- The local operator remains read-only.
- Existing run evidence routes (GET /runs, detail, report) are unchanged.

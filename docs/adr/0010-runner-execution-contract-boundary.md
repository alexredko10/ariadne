# ADR 0010: Runner Execution Contract Boundary

**Status:** Accepted

**Date:** 2026-06-26

## Context

The mock app loop (PR 0063–0067) creates and exposes deterministic task intake,
context preview, mock run, and mock run status.  However, there is no defined
contractual boundary between the application layer and a future runner adapter.

Without a runner execution contract:

- Each adapter would define its own request/result shape.
- The app layer would need adapter-specific routing knowledge.
- Adapters would be coupled to their consumers.
- No clear contract for dry-run/no-op support.
- No contractual evidence or artifact reporting structure.

## Decision

**A runner execution contract boundary is defined as schemas + ADR.**

### Contract architecture

```
RunnerExecutionRequest
  → Runner Adapter (replaceable)
    → RunnerExecutionResult
```

The runner is a replaceable execution adapter boundary, not part of the app
layer, not hardwired to Docker.

### Contract files

| File | Purpose |
|---|---|
| `schemas/runner-execution-request.schema.yml` | Request schema |
| `schemas/runner-execution-result.schema.yml` | Result schema |
| `docs/RUNNER_EXECUTION_CONTRACT.md` | Contract documentation |
| `docs/adr/0010-runner-execution-contract-boundary.md` | This ADR |

### Execution mode

The contract defines three execution modes:

- `dry_run` — return a result without executing.
- `execute` — full execution.
- `preview` — return a preview of what execution would do.

### Adapter replaceability

The `requested_adapter` field is a string identifier, not an import path.
The app layer does not need to know which adapter will handle a request.
Adapters are pluggable.

### Status states

Seven contract-level execution states: `accepted`, `running`, `completed`,
`failed`, `cancelled`, `blocked`, `requires_review`.

### Docker boundary

Docker agents are future runner adapters, not the contract itself.
No Docker files, commands, or assumptions in this PR.
A future Docker adapter must conform to this contract.

### No implementation

PR 0068 defines the contract boundary only. No adapter implementations,
no execution, no Docker, no queue, no persistence.

## Consequences

### Positive

- Adapter implementations can be developed independently (no-op, Docker,
  local process, remote sandbox) as long as they conform to the request/result
  schemas.
- The app layer does not need adapter-specific routing logic.
- Dry-run/no-op support is a first-class concept (`execution_mode`).
- Evidence and artifact reporting has a defined contractual shape.
- Human approval boundary is represented (`blocked`, `requires_review`,
  `review_required`).

### Negative

- Adapter implementations are deferred — the contract exists without
  an adapter to exercise it.
- The `inputs` dict is adapter-specific, which means cross-adapter
  input validation requires per-adapter step.
- Status values are more detailed than the current mock loop needs,
  but simpler than a full execution FSM.

## Relationship to existing contracts

- **Mock app loop (PR 0063–0067)**: The mock loop creates the run object.
  This contract defines what happens after the mock loop hands off to a
  real execution adapter.
- **Agent Execution Contract** (`schemas/agent-execution-contract.schema.yml`):
  This is a higher-level boundary (task → runner adapter). The agent execution
  contract is one level below, covering individual agent input/output.
- **Run Record** (`.project-memory/run-record.schema.yml`): Execution results
  may eventually be recorded in run records.
- **Apply Gate** (`.project-memory/apply-gate.schema.yml`): The runner
  execution contract does not bypass, replace, or modify the apply gate.
  Adapters must respect the apply gate.

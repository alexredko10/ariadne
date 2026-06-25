# Runner Execution Contract

The runner execution contract defines the boundary between the Ariadne application
layer and a replaceable runner adapter.

## Architecture

```
Task Intake (mock app loop)
  → RunnerExecutionRequest
    → Runner Adapter (replaceable)
      → RunnerExecutionResult
        → Task Intake / next step
```

The runner is a replaceable execution adapter boundary, not part of the mock app loop.

## Contract files

| File | Purpose |
|---|---|
| `schemas/runner-execution-request.schema.yml` | Execution request schema |
| `schemas/runner-execution-result.schema.yml` | Execution result schema |
| `docs/adr/0010-runner-execution-contract-boundary.md` | ADR establishing the boundary |

## Execution request

Defined in `schemas/runner-execution-request.schema.yml`.

Key fields:

- `execution_request_id` — unique request identifier.
- `run_id` — references the run this execution belongs to.
- `task_intake_id` — references the normalized task intake.
- `context_preview_id` — references the context preview.
- `requested_adapter` — string identifier (e.g., `"noop-v1"`, `"local-process-v1"`,
  `"docker-coder-v1"`). The app layer does not know what adapter will handle the
  request — it just names the kind.
- `execution_mode` — `"dry_run"`, `"execute"`, or `"preview"`. Supports no-op/dry-run
  testing without real execution.
- `inputs` — adapter-specific input dict. The contract is a wrapper; each adapter
  defines its own input structure.
- `constraints` — execution constraints.

## Execution result

Defined in `schemas/runner-execution-result.schema.yml`.

Key fields:

- `execution_result_id` — unique result identifier.
- `execution_request_id` — references the original request.
- `run_id` — references the run.
- `status` — one of: `accepted`, `running`, `completed`, `failed`, `cancelled`,
  `blocked`, `requires_review`.
- `adapter` — adapter kind that produced this result.
- `artifacts` — list of produced artifacts (artifact_id, artifact_kind, relative_path,
  digest, producing_step, summary).
- `evidence` — list of evidence records (evidence_id, evidence_kind, summary, status,
  validation_ref, artifact_ref).

## Status values

| Status | Description | Terminal |
|---|---|---|
| `accepted` | Adapter accepted the request but hasn't started | No |
| `running` | Execution is in progress | No |
| `completed` | Execution completed successfully | Yes |
| `failed` | Execution failed | Yes |
| `cancelled` | Execution was cancelled | Yes |
| `blocked` | Execution is blocked (e.g., pending approval) | No |
| `requires_review` | Execution completed but requires review | No |

These are future/runtime states produced by runner adapters. Not all are used
in the mock app loop.

## Human approval boundary

Human approval is represented through:

- `RunnerExecutionRequest.approval` — optional approval state in the request.
- `RunnerExecutionResult.status: "blocked"` — execution blocked pending approval.
- `RunnerExecutionResult.review_required: bool` — execution completed but needs review.
- `RunnerExecutionResult.status: "requires_review"` — execution completed with
  review-required result.

PR 0068 does NOT implement approval UI, notification behavior, policy engine,
approval workflow, or review routing.

## Dry-run / no-op support

The contract supports dry-run/no-op adapters through:

- `execution_mode: "dry_run"` — the adapter returns a result without executing.
- Evidence may be empty or contain a single note acknowledging the dry-run.
- Adapters can implement a no-op path by accepting the request and immediately
  returning a completed result.

## Adapter replaceability

The runner is a replaceable execution adapter. Future adapter implementations may
include:

- **No-op / dry-run adapter** — returns immediately without execution.
- **Local process adapter** — executes in a local subprocess.
- **Docker agent adapter** — executes in a Docker container.
- **Remote sandbox adapter** — executes on a remote sandbox.
- **Human-gated adapter** — pauses for human approval before execution.

PR 0068 does not implement any adapter.

## Docker agent boundary

- Docker agents are future runner adapters.
- Docker is not the execution contract.
- PR 0068 does not introduce Docker files or commands.
- PR 0068 does not assume Docker availability.
- A future Docker adapter must conform to this contract.
- The `requested_adapter` field allows adapter-specific identifiers like
  `"docker-coder-v1"` without the contract knowing about Docker.

## Relationship to existing contracts

- **Agent Execution Contract** (`schemas/agent-execution-contract.schema.yml`):
  Lower-level contract for individual agent input/output. The runner execution
  contract is a higher-level boundary (task intake → runner adapter).
- **Mock app loop** (PR 0063–0067): The mock loop creates the run object.
  The runner execution contract defines what happens after the mock loop
  hands off to a real execution adapter.
- **Run Record** (`.project-memory/run-record.schema.yml`): Execution results
  may eventually be recorded in run records, but that integration is future work.

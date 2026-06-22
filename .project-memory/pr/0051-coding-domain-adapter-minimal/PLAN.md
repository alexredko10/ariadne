# PR 0051 — Coding Domain Adapter Minimal Plan

## Goal

Add a minimal deterministic Coding Domain Adapter implementation.

The adapter should expose a stable contract-level shape for the coding domain:

* adapter identity
* supported domain
* supported capabilities
* input validation
* deterministic dry-run planning or preview output
* no side effects
* no model calls
* no filesystem writes
* no Git commands

## Architectural Thesis

Ariadne Core stays domain-agnostic.

Coding is a domain adapter, not Core.

The adapter translates coding-domain intent into contract-shaped data that conductor can later consume through a stable adapter boundary.

The model remains replaceable.
The substrate owns execution state.
The domain adapter owns domain-specific interpretation.

## Context Snapshot

- **current HEAD sha**: `e3c4207ba333f7466f1353c4b9dfb8bc9ef2bdd8`
- **current branch**: `0051-coding-domain-adapter-minimal`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `e3c4207` (main after PR 0050 merge — no delta since this is the first commit on this branch)
- **index_version**: `"0.16"` (from `.project-memory/context-bundles/contracts.yml`)
- **stale_snapshot**: false — HEAD is current with merged PR 0050, no pending changes
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `.project-memory/review-artifact.schema.yml`
- `.project-memory/domain-adapter.schema.yml`
- `ROADMAP_PHASE_0_PR_PLAN.md`
- `PHASE_0_DECOMPOSITION.md`
- `ARIADNE_ARCHITECTURE.md`
- `ROADMAP.md`
- `docs/DOMAIN_ADAPTER_CONTRACT.md`
- `docs/adr/0004-ariadne-is-domain-agnostic.md`
- `.project-memory/pr/0039-domain-adapter-contract/PLAN.md`
- `.project-memory/pr/0039-domain-adapter-contract/reviews/plan-review.yml`
- `.project-memory/pr/0039-domain-adapter-contract/reviews/precommit-review.yml`
- `.project-memory/pr/0044-runtime-substrate-skeleton/PLAN.md`
- `.project-memory/pr/0045-runtime-substrate-serialization/PLAN.md` — presumed
- `.project-memory/pr/0046-runtime-state-transitions/PLAN.md`
- `.project-memory/pr/0047-runtime-verification-evidence/PLAN.md`
- `.project-memory/pr/0048-runtime-in-memory-store/PLAN.md`
- `.project-memory/pr/0049-runner-runtime-smoke-demo/PLAN.md`
- `.project-memory/pr/0050-conductor-dry-run-pipeline/PLAN.md`
- `services/core/src/core/runtime_substrate.py`
- `services/core/src/core/runtime/store.py`
- `services/core/src/core/runtime/verification.py`
- `services/conductor/src/conductor/dry_run.py`
- `services/conductor/src/conductor/__main__.py`

## Domain Adapter Contract Snapshot

### Schema (`domain-adapter.schema.yml`)

The schema defines these types (all YAML schema, not runtime types):

| Type | Purpose |
|---|---|
| DomainAdapter | Root contract with schema_version, domain, adapter_id, description, capabilities, allowed_write_paths, forbidden_write_paths, validation_commands, execution_environment, artifact_types, apply_mechanism, rollback_mechanism, final_output_format, risks, stop_conditions, human_approval_policy |
| DomainCapability | id + description |
| DomainPolicy | allowed_write_paths + forbidden_write_paths |
| DomainValidation | validation_commands + validation_not_supported_explicit |
| DomainArtifact | type + description + path_pattern |
| DomainApplyMechanism | mechanism + description + git_based + requires_human_apply |
| DomainRollbackMechanism | mechanism + description + git_based + manual_rollback_required |
| DomainRisk | id + description + severity |
| DomainStopCondition | id + description + severity |
| DomainOutputFormat | format + description |
| DomainAdapterRegistry | adapters list |

### Coding domain responsibilities (from schema)

- create worktree
- apply patch
- normalize diff
- run tests
- detect generated artifacts
- map source files to tests
- preserve protected paths
- report validation evidence

### Coding adapter example (from schema)

```yaml
adapter_id: "coding-v1"
domain: "coding"
allowed_write_paths: ["services/**", "packages/**", "tests/**"]
forbidden_write_paths: [".git/**", ".env", "secrets/**"]
validation_commands: ["python -m pytest -q"]
execution_environment: "worktree"
apply_mechanism: { mechanism: "git_apply", requires_human_apply: true }
rollback_mechanism: { mechanism: "git_reset", git_based: true }
```

### Domain adapter contract boundary (from ADR 0004)

- Ariadne Core must not depend directly on Git, patches, pytest
- Domain Adapter supplies policy inputs to Conductor Prompt Contract
- Domain Adapter does not bypass Apply Gate
- Domain Adapter does not replace Run Record

## Current Conductor Snapshot

PR 0050 `run_conductor_dry_run()` proves a phase-driven pipeline:

- 12 deterministic phases
- Uses `InMemoryRuntimeStore`, transitions, verification
- CLI: `python -m conductor dry-run`
- No domain adapter integration

The coding adapter should not be wired into conductor yet. This PR is adapter implementation and tests only.

## Implementation Location Decision

**Decision: Use `services/domain_adapters/src/domain_adapters/coding.py`**

Rationale:
- No existing `domain_adapters` service or package exists.
- Creating `services/domain_adapters/` follows the existing project pattern (`services/runner/`, `services/core/`, `services/conductor/`).
- `packages/` exists but contains no domain-agnostic packages relevant to this adapter.
- `services/domain_adapters/tests/test_coding_adapter.py` is the corresponding test path.
- `services/domain_adapters/src/domain_adapters/__init__.py` is required as a package init.

Files to create:
1. `services/domain_adapters/src/domain_adapters/__init__.py` — package init docstring
2. `services/domain_adapters/src/domain_adapters/coding.py` — adapter implementation
3. `services/domain_adapters/tests/__init__.py` — test package init
4. `services/domain_adapters/tests/test_coding_adapter.py` — tests

**Rejected alternative: Packages path (`packages/domain_adapters/`).** The project consistently uses `services/` for runtime code. Domain adapters will eventually be runtime-loadable services. `packages/` is currently empty and inconsistent with project convention.

## Adapter Scope

The adapter is minimal and deterministic.

### Core class: `CodingDomainAdapter`

```python
from domain_adapters.coding import CodingDomainAdapter, CodingAdapterError

adapter = CodingDomainAdapter()
```

### Static metadata (no runtime I/O)

```python
adapter.adapter_id       # "coding-v1"
adapter.domain           # "coding"
adapter.description      # "Standard coding adapter for source code changes."
```

### Methods

**`describe() -> dict`**
Returns adapter identity:
```python
{
    "adapter_id": "coding-v1",
    "domain": "coding",
    "description": "Standard coding adapter for source code changes.",
}
```

**`describe_capabilities() -> list[dict]`**
Returns deterministic capability list:
```python
[
    {"id": "apply_patch", "description": "Apply normalized patches to the working tree."},
    {"id": "normalize_diff", "description": "Normalize raw diffs into runnable patches."},
    {"id": "run_tests", "description": "Execute domain-appropriate validation commands."},
    {"id": "detect_generated_artifacts", "description": "Identify generated/stale artifacts."},
]
```

**`validate_request(request: dict) -> dict`**
Validates the request shape against contract expectations.

Expected request shape:
```python
{
    "task_id": str,              # required
    "intent": str,               # required, one of: inspect, plan, implement, review
    "target_paths": list[str],   # required, at least one
    "constraints": list[str],    # optional, defaults to []
}
```

Returns:
```python
{
    "valid": True,
    "task_id": "coding-task-001",
    "intent": "inspect",
    "target_paths": ["services/example.py"],
    "constraints": ["no_git_mutation"],
}
```

Raises `CodingAdapterError` on invalid input.

**`plan_dry_run(request: dict) -> dict`**
Returns a deterministic preview of adapter behavior for the given request.

```python
adapter.plan_dry_run({
    "task_id": "coding-task-001",
    "intent": "inspect",
    "target_paths": ["services/example.py"],
    "constraints": ["no_git_mutation"],
})
```

Returns:
```python
{
    "adapter_id": "coding-v1",
    "domain": "coding",
    "task_id": "coding-task-001",
    "intent": "inspect",
    "target_paths": ["services/example.py"],
    "constraints": ["no_git_mutation"],
    "planned_actions": ["read_target_files", "analyze_structure", "report_findings"],
    "side_effects": [],
    "requires_human_approval": False,
    "model_required": False,
    "validation_commands": ["python -m pytest -q"],
}
```

`planned_actions` is deterministic based on intent:

| Intent | Planned actions |
|---|---|
| `inspect` | `["read_target_files", "analyze_structure", "report_findings"]` |
| `plan` | `["read_target_files", "analyze_structure", "design_changes", "propose_plan"]` |
| `implement` | `["read_target_files", "apply_changes", "run_validation", "report_results"]` |
| `review` | `["read_target_files", "analyze_changes", "check_quality", "report_review"]` |
| else | `["analyze_request", "determine_actions"]` |

### Contract-aligned policy data

The adapter exposes contract-aligned policy as class-level attributes:

```python
CodingDomainAdapter.ADAPTER_ID = "coding-v1"
CodingDomainAdapter.DOMAIN = "coding"
CodingDomainAdapter.ALLOWED_WRITE_PATHS = ["services/**", "packages/**", "tests/**"]
CodingDomainAdapter.FORBIDDEN_WRITE_PATHS = [".git/**", ".env", "secrets/**"]
CodingDomainAdapter.VALIDATION_COMMANDS = ["python -m pytest -q"]
CodingDomainAdapter.EXECUTION_ENVIRONMENT = "worktree"
CodingDomainAdapter.APPLY_MECHANISM = {
    "mechanism": "git_apply",
    "description": "Apply patch via git apply after human approval.",
    "git_based": True,
    "requires_human_apply": True,
}
CodingDomainAdapter.ROLLBACK_MECHANISM = {
    "mechanism": "git_reset",
    "description": "Reset worktree to snapshot.",
    "git_based": True,
    "manual_rollback_required": False,
}
CodingDomainAdapter.RISKS = [
    {"id": "uncommitted_changes_lost", "description": "Uncommitted changes may be lost on rollback.", "severity": "medium"},
]
CodingDomainAdapter.STOP_CONDITIONS = [
    {"id": "validation_failed", "description": "Validation must pass before apply.", "severity": "critical"},
]
CodingDomainAdapter.HUMAN_APPROVAL_POLICY = (
    "Apply requires explicit human approval. Rollback may be automatic for recoverable states."
)
```

These are for future contract/serialization use. The adapter methods that produce output dicts may reference these constants.

## Error Model

```python
class CodingAdapterError(Exception):
    """Raised when a coding adapter operation cannot be completed."""
    def __init__(self, operation: str, subject: str, reason: str) -> None:
        self.operation = operation
        self.subject = subject
        self.reason = reason
        super().__init__(f"Coding adapter error on {operation}({subject}): {reason}")
```

## Determinism Rules

- Stable output for the same input.
- Deterministic ordering (sorted `target_paths`, sorted `constraints`).
- No id generation.
- No timestamp generation.
- No filesystem inspection at import or instantiation.
- `validate_request` only checks data shape — does not resolve paths or access filesystem.
- No absolute local paths in output.
- No environment-specific values.

## Relationship to Core and Conductor

- Core remains unchanged.
- Conductor remains unchanged.
- Adapter output is contract-shaped data for future conductor integration.
- Adapter does not own runtime state.
- Adapter does not perform state transitions.
- Adapter does not attach evidence.
- Adapter does not build final reports.
- Adapter does not import any Core runtime module.
- Adapter does not import any runner or conductor module.

## Future Allowed Write Paths

- `services/domain_adapters/src/domain_adapters/__init__.py`
- `services/domain_adapters/src/domain_adapters/coding.py`
- `services/domain_adapters/tests/__init__.py`
- `services/domain_adapters/tests/test_coding_adapter.py`

Precommit review may later write only:
- `.project-memory/pr/0051-coding-domain-adapter-minimal/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0051-coding-domain-adapter-minimal/PLAN.md` (planner only)
- `.project-memory/pr/0051-coding-domain-adapter-minimal/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**` except PLAN.md by planner and precommit-review.yml by precommit-review
- `agents/**`
- `schemas/**`
- `docs/**`
- `services/core/**`
- `services/conductor/**`
- `services/runner/**`
- `services/task_intake/**`
- `services/model_gateway/**`
- `services/**` except exact allowed adapter files
- `packages/**`
- `apps/**`
- `.ariadne/**`
- `.github/**`
- `docker/**`
- `Dockerfile*`
- `pyproject.toml`
- `package.json`
- `Makefile`
- `ARIADNE_ARCHITECTURE.md`
- `ROADMAP.md`
- `PHASE_0_DECOMPOSITION.md`
- `ROADMAP_PHASE_0_PR_PLAN.md`

## Required Tests

### Adapter identity

- `adapter.adapter_id == "coding-v1"`
- `adapter.domain == "coding"`
- `adapter.description` is non-empty string

### describe()

- returns dict with adapter_id, domain, description
- values match constructor defaults
- repeated calls return equal output

### describe_capabilities()

- returns list of dicts
- each capability has id and description
- capabilities are deterministic order
- capabilities are JSON-serializable
- repeated calls return equal output

### Request validation

- accepts minimal valid request (task_id, intent, target_paths)
- rejects missing task_id (raises CodingAdapterError)
- rejects missing intent (raises CodingAdapterError)
- rejects missing target_paths (raises CodingAdapterError)
- rejects empty target_paths (raises CodingAdapterError)
- rejects invalid intent (raises CodingAdapterError)
- accepts optional constraints list
- error includes operation, subject, reason
- validated request returns dict with valid=True and normalized fields

### plan_dry_run()

- returns dict with expected key set
- includes adapter_id, domain, task_id, intent, target_paths, constraints
- includes planned_actions list
- includes side_effects as empty list
- includes requires_human_approval as False
- includes model_required as False
- includes validation_commands list
- target_paths are sorted
- constraints are sorted
- planned_actions vary by intent:
  - "inspect" produces inspection-related actions
  - "plan" produces planning-related actions
  - "implement" produces implementation-related actions
  - "review" produces review-related actions
- JSON serializable
- repeated calls with same input return equal output

### Policy data (class-level)

- ALLOWED_WRITE_PATHS contains expected paths
- FORBIDDEN_WRITE_PATHS contains expected paths
- VALIDATION_COMMANDS contains expected commands
- EXECUTION_ENVIRONMENT is "worktree"
- APPLY_MECHANISM includes git_based=True, requires_human_apply=True
- ROLLBACK_MECHANISM includes git_based=True
- RISKS is a non-empty list
- STOP_CONDITIONS is a non-empty list
- HUMAN_APPROVAL_POLICY is a non-empty string

### Safety

- no filesystem writes
- no Git commands
- no Docker commands
- no subprocess
- no network
- no LLM/provider calls
- no persistence
- no SQLite/Redis/distributed cache
- no absolute local paths in output
- does not import core.runtime, runner, or conductor modules
- no old names/examples

### Compatibility

- conductor dry-run tests still pass
- runner runtime smoke tests still pass
- Core runtime tests still pass

## Validation Commands

```bash
PYTHONPATH=services/domain_adapters/src python -m pytest services/domain_adapters/tests/test_coding_adapter.py -v
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_dry_run.py -q
PYTHONPATH=services/core/src:services/runner/src python -m pytest services/runner/tests/test_runtime_smoke.py -q
python -m pytest services/core/tests/test_runtime_store.py -q
python -m pytest services/core/tests/test_runtime_verification.py -q
python -m pytest services/core/tests/test_runtime_transitions.py -q
python -m pytest services/core/tests/test_runtime_substrate.py -q
python -m pytest -q
python -m compileall -f services packages
grep -R -n "subprocess\|requests\|urllib\|httpx\|redis\|sqlite\|open(\|Path(.*write\|docker\|git \|water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask" services/domain_adapters || true
git status --short
git diff --name-only
```

## Post-change Checks

```bash
grep -R -n "class CodingDomainAdapter\|class CodingAdapterError\|def describe\|def describe_capabilities\|def validate_request\|def plan_dry_run" services/domain_adapters
```

## Expected Changed Files

1. `services/domain_adapters/src/domain_adapters/__init__.py` — new package init
2. `services/domain_adapters/src/domain_adapters/coding.py` — new adapter module
3. `services/domain_adapters/tests/__init__.py` — new test package init
4. `services/domain_adapters/tests/test_coding_adapter.py` — new tests

Expected future review artifact:
- `.project-memory/pr/0051-coding-domain-adapter-minimal/reviews/precommit-review.yml`

## Non-goals

- no LLM integration
- no model-provider integration
- no real agent execution
- no code execution
- no repository mutation
- no Git operations
- no Docker
- no conductor integration
- no conductor or runner changes
- no Core runtime changes
- no persistence or database
- no SQLite
- no Redis
- no distributed cache
- no HTTP server
- no human approval UI
- no changes to `agents/**`
- no changes to `schemas/**`
- no changes to `docs/**`
- no changes to `.project-memory/**` except PLAN.md by planner and precommit-review.yml by precommit-review
- no `.ariadne/**` namespace creation
- no root dependency/build changes
- no old `.grace` namespace
- no water_meter / broken_clock / old Flask examples

## Review Requirements

- **plan-review.yml** must approve before implementation begins.
- **precommit-review.yml** must pass before commit.
- All review artifacts follow `.project-memory/review-artifact.schema.yml`.
- Reviewers must verify: no schema/docs/agents/core/conductor/runner changes.
- Reviewers must verify: stdlib-only, no LLM calls, no network, no persistence, no Git/Docker, no subprocess.
- Reviewers must verify: no old names/examples introduced.
- Reviewers must verify: adapter output is deterministic and contract-aligned.
- Reviewers must verify: `validate_request` validates shape only (no filesystem I/O).
- Reviewers must verify: `plan_dry_run` does not execute any action.
- Reviewers must verify: no import of Core runtime, runner, or conductor modules.

## Stop Conditions

- about to write to `agents/**` → stop
- about to write to `.project-memory/**` except PLAN.md by planner → stop
- about to write to `schemas/**` → stop
- about to write to `docs/**` → stop
- about to modify Core runtime internals → stop
- about to modify conductor internals → stop
- about to modify runner internals → stop
- about to modify any existing service or test file → stop
- implementation requires LLM SDK → stop
- implementation requires model-generated output → stop
- implementation requires real agent execution → stop
- implementation requires code execution → stop
- implementation requires subprocess or network → stop
- implementation requires Git or Docker → stop
- implementation requires third-party dependency → stop
- implementation requires persistence/storage → stop
- implementation requires SQLite/Redis/distributed cache → stop
- adapter requires filesystem writes → stop
- adapter reads outside its own input → stop
- adapter imports Core runtime, runner, or conductor modules → stop
- implementation path cannot be exactly scoped → stop
- old names/examples would be introduced → stop

## Open Questions

1. **Should the adapter have an `__init__.py` that re-exports CodingDomainAdapter?** **Decision:** Yes, standard pattern: `from domain_adapters import CodingDomainAdapter, CodingAdapterError`.
2. **Should the adapter be a class or a module with functions?** **Decision:** Class. The domain adapter contract defines a consistent interface. A class with methods allows the future conductor to call `describe()`, `validate_request()`, `plan_dry_run()` polymorphically across adapters.
3. **Should the adapter have mutable state?** **Decision:** No. All methods are pure or read-only. The class itself is state-free. All policy data is class-level constants.
4. **Should the adapter have an existing service/package `pyproject.toml`?** **Decision:** Not required. The existing `services/` services do not all have standalone `pyproject.toml` files. The adapters are loaded as sibling packages within the Python path. If a `pyproject.toml` is needed later, it can be added. For PR 0051, the adapter is imported via `PYTHONPATH` like all other services.

## Decisions Made

### adapter_location

```
services/domain_adapters/src/domain_adapters/__init__.py   (new package init)
services/domain_adapters/src/domain_adapters/coding.py     (new adapter module)
services/domain_adapters/tests/__init__.py                  (new test package init)
services/domain_adapters/tests/test_coding_adapter.py       (new tests)
```

### api_surface

```
CodingDomainAdapter:
  adapter_id: str (class constant)
  domain: str (class constant)
  description: str (class constant)
  describe() -> dict
  describe_capabilities() -> list[dict]
  validate_request(request: dict) -> dict
  plan_dry_run(request: dict) -> dict

CodingAdapterError(Exception):
  __init__(operation, subject, reason)
```

### request_shape

```
{
    "task_id": str,           # required
    "intent": str,            # required, one of: inspect, plan, implement, review
    "target_paths": list[str],# required, at least one
    "constraints": list[str], # optional, defaults to []
}
```

### preview_output_contract

```
{
    "adapter_id": "coding-v1",
    "domain": "coding",
    "task_id": str,
    "intent": str,
    "target_paths": list[str],
    "constraints": list[str],
    "planned_actions": list[str],
    "side_effects": [],
    "requires_human_approval": False,
    "model_required": False,
    "validation_commands": ["python -m pytest -q"],
}
```

### error_model

```
CodingAdapterError(Exception) with operation, subject, reason.
Domain-scoped. No broad cross-service error hierarchy.
```

### test_strategy

```
Pure in-memory tests. No I/O, no network, no subprocess.
Test classes:
- TestCodingDomainAdapterIdentity (adapter_id, domain, description)
- TestDescribe (describe method output)
- TestDescribeCapabilities (capabilities shape and determinism)
- TestValidateRequest (valid requests, invalid requests, error fields)
- TestPlanDryRun (output shape, intent-dependent actions, determinism)
- TestPolicyData (class-level contract constants)
- TestSafety (no forbidden imports, no I/O, no subprocess)
```

---

PLAN written: yes

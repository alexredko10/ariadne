# PR 0045 — Runtime Substrate Serialization Plan

## Goal

Add serialization and round-trip behavior to the runtime substrate skeleton created in PR 0044.

The runtime substrate entities must support conversion to plain Python dictionaries (`to_dict`) and reconstruction from dictionaries (`from_dict`) where appropriate. No persistence or model calls — pure data transformation.

## Architectural Thesis

```text
Ariadne is not a chatbot wrapper.
Ariadne is not a model-centered agent framework.
Ariadne is an execution substrate for agentic software production.

The model is replaceable.
The substrate is the product.
```

Serialization is a platform concern, not a developer convenience. Deterministic dictionary shapes enable checkpointing, audit tracing, prompt artifact population, and cross-service communication without coupling to internal dataclass layouts.

## Context Snapshot

```yaml
context_snapshot:
  base_sha: "b6a8696dec20aac8ee17b616b70e56a48a07662b"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.19"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "b6a8696dec20aac8ee17b616b70e56a48a07662b"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

## Inputs Read

- `.project-memory/memory_index.yml` — version 0.19
- `.project-memory/project_contract.yml` — version 0.1
- `.project-memory/context-bundles/contracts.yml` — version 0.17
- `.project-memory/anchors.yml`
- `ARIADNE_ARCHITECTURE.md`
- `ROADMAP.md`
- `.project-memory/pr/0044-runtime-substrate-skeleton/PLAN.md`
- `services/core/src/core/runtime_substrate.py`
- `services/core/tests/test_runtime_substrate.py`
- All 13 schemas under `schemas/`

## Current Runtime Substrate Snapshot

### Entities and reference types in `services/core/src/core/runtime_substrate.py`:

| Category | Name | Mutable? |
|----------|------|----------|
| Enum | `RunStatus` | — |
| Enum | `StepStatus` | — |
| Enum | `RubricVerdict` | — |
| Enum | `AgentRole` | — |
| Reference (frozen) | `ContextPackRef` | Frozen |
| Reference (frozen) | `StateModelRef` | Frozen |
| Reference (frozen) | `TransitionGraphRef` | Frozen |
| Reference (frozen) | `RubricPackRef` | Frozen |
| Reference (frozen) | `RubricJudgeResultRef` | Frozen |
| Reference (frozen) | `ModelCapabilityProfileRef` | Frozen |
| Reference (frozen) | `LongContextStressProfileRef` | Frozen |
| Entity | `StepBoundary` | Mutable |
| Entity (frozen) | `Checkpoint` | Frozen |
| Entity | `RunState` | Mutable |
| Entity | `AgentExecutionRecord` | Mutable |
| Entity | `FinalReportDraft` | Mutable |

### Helpers:

- `create_run_state(...)` → `RunState`
- `record_checkpoint(...)` → `Checkpoint`
- `record_agent_execution(...)` → `AgentExecutionRecord`
- `build_final_report_draft(...)` → `FinalReportDraft`

### Current test coverage (32 tests):

- RunState creation, append step, step ordering
- StepBoundary defaults
- Checkpoint immutability
- AgentExecutionRecord creation (no provider hardcoding)
- FinalReportDraft defaults
- Reference type hashability
- Enum value correctness
- Helper function behavior
- `dataclasses.asdict()` serialization for RunState, Checkpoint, FinalReportDraft

### Current serialization state:

`dataclasses.asdict()` works for all entities, but:
- Enum values remain as enum members, not plain strings
- `datetime` objects remain as `datetime`, not ISO8601 strings
- No `from_dict` reconstruction exists
- No explicit `to_dict` methods exist
- No schema validation on reconstruction

## Serialization Scope

**In scope for this PR:**

- `to_dict()` methods on primary entities (RunState, StepBoundary, Checkpoint, AgentExecutionRecord, FinalReportDraft)
- Enum → string conversion in dict output
- `datetime` → ISO8601 string conversion in dict output
- `from_dict()` classmethods for reconstructing entities from dicts
- Round-trip tests (to_dict → from_dict → verify equality)
- Reference types remain simple — their dict representation is `{"<field>": "<value>"}`

**Out of scope:**

- Full JSON schema validation (deferred to future PR)
- File persistence (belongs to storage PR)
- Network serialization (belongs to transport PR)
- Schema versioning/migration (deferred)

## Entity Serialization Plan

### RunState (serialize now: yes, deserialize now: yes)

- `to_dict()` → dict with string status, ISO8601 timestamps, and serialized steps list
- `from_dict(data)` → reconstruct RunState with enum/timestamp parsing
- Schema: direct alignment with `schemas/run-state.schema.yml`

### StepBoundary (serialize now: yes, deserialize now: yes)

- `to_dict()` → dict with string status, ISO8601 timestamps, string agent_role
- `from_dict(data)` → reconstruct StepBoundary
- Schema: direct alignment (embedded in run-state)

### Checkpoint (serialize now: yes, deserialize now: yes)

- `to_dict()` → dict with ISO8601 timestamps
- `from_dict(data)` → reconstruct Checkpoint (frozen — always recreate)
- Schema: direct alignment with `schemas/checkpoint.schema.yml`

### AgentExecutionRecord (serialize now: yes, deserialize now: yes)

- `to_dict()` → dict with string role, all list fields as lists
- `from_dict(data)` → reconstruct AgentExecutionRecord
- Schema: direct alignment with `schemas/agent-execution-contract.schema.yml`

### FinalReportDraft (serialize now: yes, deserialize now: yes)

- `to_dict()` → dict with ISO8601 timestamp, all list fields as lists
- `from_dict(data)` → reconstruct FinalReportDraft
- Schema: direct alignment with `schemas/final-report.schema.yml`

### Reference types (serialize now: no explicit method needed, deserialize now: yes)

- `dataclasses.asdict()` already works for frozen references
- `from_dict` classmethod for each reference type for consistency

### Enums

- No changes needed — `to_dict()` methods will convert `.value` automatically

## Schema Mapping

| Runtime key | Schema file | Alignment |
|-------------|-------------|-----------|
| `RunState` | `schemas/run-state.schema.yml` | Direct — fields map 1:1 |
| `StepBoundary` | `schemas/run-state.schema.yml` (StepRecord) | Direct — embedded in RunState |
| `Checkpoint` | `schemas/checkpoint.schema.yml` | Direct — fields map 1:1 |
| `AgentExecutionRecord` | `schemas/agent-execution-contract.schema.yml` | Direct — fields map 1:1 |
| `FinalReportDraft` | `schemas/final-report.schema.yml` | Direct — fields map 1:1 |
| `ContextPackRef` | `schemas/context-pack.schema.yml` | Reference-only — ID wrapper |
| `StateModelRef` | `schemas/state-model.schema.yml` | Reference-only — ID wrapper |
| `TransitionGraphRef` | `schemas/transition-graph.schema.yml` | Reference-only — ID wrapper |
| `RubricPackRef` | `schemas/rubric-pack.schema.yml` | Reference-only — ID wrapper |
| `RubricJudgeResultRef` | `schemas/rubric-judge-result.schema.yml` | Reference-only — ID wrapper |
| `ModelCapabilityProfileRef` | `schemas/model-capability-profile.schema.yml` | Reference-only — ID wrapper |
| `LongContextStressProfileRef` | `schemas/long-context-stress-profile.schema.yml` | Reference-only — ID wrapper |

**RFC 3339 / ISO8601 representation:** All `datetime` fields will be serialized to ISO8601 strings with timezone info (e.g. `"2026-06-20T12:00:00Z"`). JSON-compatible.

## Future Allowed Write Paths

```text
services/core/src/core/runtime_substrate.py
services/core/tests/test_runtime_substrate.py
```

Precommit review may later write:

```text
.project-memory/pr/0045-runtime-substrate-serialization/reviews/precommit-review.yml
```

## Future Forbidden Write Paths

```text
.project-memory/pr/0045-runtime-substrate-serialization/PLAN.md
.project-memory/pr/0045-runtime-substrate-serialization/reviews/plan-review.yml
.project-memory/**
schemas/**
docs/**
agents/**
apps/**
packages/**
.ariadne/**
.github/**
docker/**
Dockerfile*
pyproject.toml
package.json
Makefile
ARIADNE_ARCHITECTURE.md
ROADMAP.md
PHASE_0_DECOMPOSITION.md
ROADMAP_PHASE_0_PR_PLAN.md
services/** except:
  - services/core/src/core/runtime_substrate.py
  - services/core/tests/test_runtime_substrate.py
```

## Test Plan

Existing test file: `services/core/tests/test_runtime_substrate.py`

New/additional tests must cover:

1. **RunState to_dict** — includes all fields, status as string, timestamps as ISO8601
2. **RunState from_dict round-trip** — to_dict → from_dict → verify field equality
3. **StepBoundary to_dict** — ISO8601 timestamps, string status, string role
4. **StepBoundary from_dict** — reconstruct with correct defaults for unset optional fields
5. **Checkpoint to_dict** — ISO8601 timestamp, frozen fields
6. **Checkpoint from_dict round-trip** — reconstruct and verify
7. **AgentExecutionRecord to_dict** — all list fields as lists, role as string
8. **AgentExecutionRecord from_dict round-trip** — full round-trip
9. **FinalReportDraft to_dict** — human_approval_required as bool
10. **FinalReportDraft from_dict round-trip** — verify defaults
11. **ContextPackRef from_dict** — reconstruct from dict
12. **Reference types round-trip** — all 7 reference types to_dict/from_dict
13. **No provider hardcoding in serialized dict** — model_used is a generic string in dict output
14. **No raw repo dumps** — context references are ID strings only
15. **Deterministic round-trip** — serializing same data twice produces same dict

## Validation Commands

```bash
python -m pytest services/core/tests/test_runtime_substrate.py -q
python -m pytest -q
python -m compileall -f services/core
PYTHONPATH=services/runner/src python -m runner doctor
grep -R -n "water_meter|water-meter|Broken Clock|broken_clock|daily-consumption|.grace|@grace-|old Flask" services/core/src/core/runtime_substrate.py services/core/tests/test_runtime_substrate.py || true
git status --short
git diff --name-only
```

## Expected Changed Files

```text
services/core/src/core/runtime_substrate.py
services/core/tests/test_runtime_substrate.py
```

## Non-goals

```text
- no full orchestrator
- no persistence layer
- no repository storage
- no model calls
- no provider-specific routing
- no task intake changes
- no patch application
- no Apply Gate changes
- no Git/Docker-specific runtime behavior
- no domain-adapter implementation
- no schema rewrites
- no docs/ADR rewrites
- no project-memory changes by implementation
- no .ariadne namespace creation
- no old .grace namespace
- no water_meter / broken_clock / old Flask examples
```

## Review Requirements

- **Architect review** — required (serialization design affects all downstream consumers)
- **Precommit review** — required (importable code)
- **Human approval** — recommended before merge

## Stop Conditions

Stop if:

- serialization requires schema rewrites
- implementation path is not exactly scoped to the two allowed files
- runtime Core starts depending on provider-specific model fields
- runtime Core stores raw repository dumps
- persistence is introduced without approved plan
- Git/Docker/domain-adapter behavior is added
- unrelated dirty tree
- old names/examples are introduced
- tests cannot be run or fail without explanation

## Open Questions

1. Should `from_dict` accept `**extra` to ignore unknown fields (forward compatibility)? Yes — recommended to accept and ignore unknown top-level keys so adding schema fields later does not break existing deserialization.

2. Should reference types get `to_dict`/`from_dict` at all, or just rely on `dataclasses.asdict`? The PLAN recommends adding explicit `from_dict` classmethods for consistency, but reference types can use auto-generated dict from `dataclasses.asdict` for `to_dict`.

3. Should enum `to_dict` produce `"PENDING"` (UPPER) or `"pending"` (lower)? Lower — matching the schema `.value` conventions already established.

## Decisions Made

- **Serialization style**: Explicit `to_dict()` instance methods and `from_dict()` classmethods on all primary entities. Reference types use auto-generated dict from `dataclasses.asdict`.
- **Datetime format**: ISO8601 with `Z` suffix (RFC 3339 profile), JSON-compatible strings.
- **Enum format**: String `.value` (lowercase, matching schema conventions).
- **No validation in `from_dict`**: Accept and ignore unknown top-level fields for forward compatibility.
- **No persistence**: Pure in-memory data transformations only.
- **No provider hardcoding**: Model identifiers remain generic `provider:model` strings.
- **No raw repo dumps**: Context references remain ID strings only.

PLAN written: yes
open questions: None (all resolved in decisions)
decisions made:
- Serialization style: explicit to_dict/from_dict on primary entities; asdict for references
- Datetime: ISO8601 Z-suffix
- Enum: lowercase .value
- from_dict: accept and ignore unknown fields for forward compatibility
- No persistence, no model calls, no provider hardcoding, no raw repo dumps
context_snapshot:
  base_sha: b6a8696dec20aac8ee17b616b70e56a48a07662b
  base_sha_source: git rev-parse --verify HEAD at PLAN creation time
  index_version: "0.19"
  index_version_source: .project-memory/memory_index.yml
  current_head: b6a8696dec20aac8ee17b616b70e56a48a07662b
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: git introspection
files read:
- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `ARIADNE_ARCHITECTURE.md`
- `ROADMAP.md`
- `.project-memory/pr/0044-runtime-substrate-skeleton/PLAN.md`
- `services/core/src/core/runtime_substrate.py`
- `services/core/tests/test_runtime_substrate.py`
- All 13 schemas under schemas/
files written:
- `.project-memory/pr/0045-runtime-substrate-serialization/PLAN.md`
files intentionally ignored:
- `.project-memory/pr/0045-runtime-substrate-serialization/reviews/**` (not created by planner)
- `services/core/src/core/runtime_substrate.py` (not modified — PLAN-only)
- `services/core/tests/test_runtime_substrate.py` (not modified — PLAN-only)
- `schemas/**`, `docs/**`, `agents/**`, `packages/**`, `apps/**` (forbidden)
confirm: no implementation created
confirm: no review artifacts created by planner
confirm: no Docker commands run
confirm: no git mutation commands run

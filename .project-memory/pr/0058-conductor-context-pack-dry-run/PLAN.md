# PR 0058 — Conductor Context Pack Dry-Run Integration Plan

## Goal

Plan minimal integration of context-pack input generation and context compilation into conductor dry-run.

The dry-run flow should produce a compact context pack from explicit inputs.

This PR should make the previous executable layers visible in the conductor dry-run path.

## Architectural Thesis

Ariadne should expose context-pack assembly through conductor before adding broader workflow automation.

0056 created explicit context-pack inputs.
0057 compiled those inputs into context packs.
0058 wires that deterministic context-pack path into conductor dry-run.

The model is replaceable.
The conductor should orchestrate substrate contracts, not hide model-specific behavior.

## Context Snapshot

- **current HEAD sha**: `bcf3eadc503aa6d9fdff87d48bad55df586a7641`
- **current branch**: `0058-conductor-context-pack-dry-run`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `bcf3ead` (merge commit — no skew relative to main)
- **index_version**: `"0.24"` (from `.project-memory/context-bundles/contracts.yml` — PR 0057 bumped it)
- **stale_snapshot**: false — HEAD is current with merged PR 0057, no pending changes
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `services/conductor/src/conductor/dry_run.py`
- `services/conductor/src/conductor/context_pack_inputs.py`
- `services/conductor/src/conductor/context_compiler.py`
- `services/conductor/src/conductor/__main__.py`
- `services/conductor/tests/test_dry_run.py`
- `services/conductor/tests/test_context_pack_inputs.py`
- `services/conductor/tests/test_context_compiler.py`
- `schemas/context-pack-inputs.schema.yml`
- `schemas/context-pack.schema.yml`
- `docs/PR_WORKSPACE_MEMORY.md`
- `docs/CONTEXT_STEWARD.md`
- `docs/CONTEXT_STEWARD_PROMPTS.md`
- `docs/CACHE_CONTRACTS.md`
- `.project-memory/pr/0055-pr-workspace-memory-artifacts/PLAN.md`
- `.project-memory/pr/0056-context-pack-input-generator/PLAN.md`
- `.project-memory/pr/0057-minimal-context-compiler/PLAN.md`

## Existing Contract Snapshot

### Context Pack Input Generator (`conductor/context_pack_inputs.py`)

Exports: `build_context_pack_inputs(...)`, `normalize_context_pack_inputs(raw)`, `validate_context_pack_inputs(raw)`, `context_pack_inputs_error(field, reason)`.

Pure functions, no I/O.

### Minimal Context Compiler (`conductor/context_compiler.py`)

Exports: `compile_context_pack(...)`, `normalize_context_pack(raw)`, `validate_context_pack(raw)`.

Consumes `build_context_pack_inputs` output dict + explicit params (`repo_id`, `purpose_id`, `domain`, `risk_level`, `base_sha`, `index_version`, optional lists). Outputs compact context-pack dict.

### Conductor Dry-Run (`conductor/dry_run.py`)

- `_PhaseContext` with `store`, `run_id`, `report`.
- 12-phase pipeline registered in `_PHASES` as `list[tuple[str, callable]]`.
- `run_conductor_dry_run()` → `_build_output(ctx, events)` → dict.
- Output: dry_run, run_id, step/checkpoint/evidence counts, final_report fields, conductor_events.
- Deterministic timestamps `T0`–`T4`.
- CLI via `python -m conductor dry-run`.

### Tests (`conductor/tests/test_dry_run.py`)

Tests: output shape, event order, determinism, step/checkpoint/evidence counts, CLI subprocess.

## Implementation Location Decision

**Decision:** Modify existing dry-run module and test file only. No new files.

### Implementation file

**`services/conductor/src/conductor/dry_run.py`** — modify:

- Add deterministic dry-run constants for compiler params (`REPO_ID`, `PURPOSE_ID`, `DOMAIN`, `RISK_LEVEL`, `BASE_SHA`, `INDEX_VERSION`).
- Add `_phase_generate_context_pack_inputs` and `_phase_compile_context_pack` phase functions.
- Add these phases to the `_PHASES` list between `plan_steps` and `start_run`.
- Add `ctx.inputs` and `ctx.context_pack` to `_PhaseContext`.
- Update `_build_output` to include `context_pack_summary`.

### Test file

**`services/conductor/tests/test_dry_run.py`** — modify:

- Add `TestContextPackIntegration` class with:
  - `test_dry_run_output_includes_context_pack_summary`
  - `test_context_pack_key_fields`
  - `test_context_pack_deterministic`

### Not modified

- `services/core/**`, `services/runner/**`, `services/domain_adapters/**`
- `packages/`, `agents/`, `apps/`
- `schemas/`, `docs/`
- `.project-memory/templates/`, `.project-memory/anchors.yml`, `.project-memory/project_contract.yml`
- `pyproject.toml`
- `__main__.py` (no CLI changes needed)
- `context_pack_inputs.py`, `context_compiler.py`, `test_context_pack_inputs.py`, `test_context_compiler.py` (no changes)

## Integration Contract

### New phases added to `_PHASES`

**`generate_context_pack_inputs`** phase (after `plan_steps`, before `start_run`):

```python
def _phase_generate_context_pack_inputs(
    ctx: _PhaseContext,
    ts: dict[str, Any],
) -> None:
    from conductor.context_pack_inputs import build_context_pack_inputs

    ctx.inputs = build_context_pack_inputs(
        pr_id=ctx.run_id,
        task_goal="Dry-run context pack integration",
        source_contracts=["contract-a", "contract-b"],
        relevant_anchors=["anchor-001", "anchor-002"],
        allowed_paths=["services/**", "packages/**"],
        forbidden_paths=[".git/**", ".env"],
        cache_key_refs=[{"namespace": "context", "artifact_kind": "context_pack"}],
        known_risks=[
            {"id": "risk-001", "description": "Example risk", "severity": "low"},
        ],
        manual_checks_required=["Verify context pack fields"],
        context_freshness_status="fresh",
        context_freshness_last_verified="plan_steps",
        created_from_agent="conductor-dry-run",
        created_from_hook="before_plan",
        created_from_template="context-steward.before_plan.v1",
    )
```

**`compile_context_pack`** phase (after `generate_context_pack_inputs`, before `start_run`):

```python
def _phase_compile_context_pack(
    ctx: _PhaseContext,
    ts: dict[str, Any],
) -> None:
    from conductor.context_compiler import compile_context_pack

    ctx.context_pack = compile_context_pack(
        context_pack_inputs=ctx.inputs,
        repo_id=REPO_ID,
        purpose_id=PURPOSE_ID,
        domain=DOMAIN,
        risk_level=RISK_LEVEL,
        base_sha=BASE_SHA,
        index_version=INDEX_VERSION,
        task_subgraph=["services/conductor/src/conductor/dry_run.py"],
        relevant_files=["services/conductor/src/conductor/dry_run.py"],
    )
```

### Updated `_PHASES` list

```python
_PHASES = [
    ("initialize_run", _phase_initialize_run),
    ("plan_steps", _phase_plan_steps),
    ("generate_context_pack_inputs", _phase_generate_context_pack_inputs),
    ("compile_context_pack", _phase_compile_context_pack),
    ("start_run", _phase_start_run),
    ("start_step:step-001", _phase_start_step),
    ("complete_step:step-001", _phase_complete_step),
    ("checkpoint:step-001", _phase_checkpoint),
    ("start_step:step-002", _phase_start_step),
    ("complete_step:step-002", _phase_complete_step),
    ("checkpoint:step-002", _phase_checkpoint),
    ("attach_evidence", _phase_attach_evidence),
    ("build_final_report", _phase_build_report),
    ("complete_run", _phase_complete_run),
]
```

### Updated `_PhaseContext`

```python
class _PhaseContext:
    def __init__(self) -> None:
        from core.runtime.store import InMemoryRuntimeStore
        self.store = InMemoryRuntimeStore()
        self.run_id = "dry-run-001"
        self.report: Any = None
        self.inputs: dict[str, Any] | None = None  # NEW
        self.context_pack: dict[str, Any] | None = None  # NEW
```

## Output Shape

### Updated `_build_output`

Add to the existing output dict:

```python
return {
    # ... existing fields ...
    "context_pack_summary": {
        "present": ctx.context_pack is not None,
        "context_pack_id": ctx.context_pack.get("context_pack_id") if ctx.context_pack else None,
        "task": ctx.context_pack.get("task") if ctx.context_pack else None,
        "domain": ctx.context_pack.get("domain") if ctx.context_pack else None,
        "risk_level": ctx.context_pack.get("risk_level") if ctx.context_pack else None,
        "risks": ctx.context_pack.get("risks") if ctx.context_pack else [],
        "anchors": ctx.context_pack.get("anchors") if ctx.context_pack else [],
        "invariants": ctx.context_pack.get("invariants") if ctx.context_pack else [],
        "section_count": len(ctx.context_pack) if ctx.context_pack else 0,
    },
}
```

This is a summary, not the full context pack. The full `context_pack` dict is available via `ctx.context_pack` but is not printed to avoid cluttering dry-run output. Tests can access it directly.

### Deterministic constants

```python
REPO_ID = "ariadne"
PURPOSE_ID = "dry-run-purpose"
DOMAIN = "dry-run"
RISK_LEVEL = "low"
BASE_SHA = "dry-run-abc123"
INDEX_VERSION = "0.24"
```

## Determinism

- All compiler params are explicit constants or derived from deterministic inputs.
- No current-time generation.
- No random ids.
- Stable ordering via context_pack_inputs and context_compiler normalization.
- No absolute local paths (all paths are project-relative patterns).
- No machine-specific values.
- No old names/examples.
- No shell placeholders.

## Validation

- Dry-run still succeeds with the new phases.
- `context_pack_summary` is present in output with `present: true`.
- `context_pack_id` is deterministic: `f"cp-{run_id}-{REPO_ID}"` = `"cp-dry-run-001-ariadne"`.
- `task` matches the task_goal used.
- `risks` includes the risk description from `known_risks`.
- `anchors` includes the relevant anchors.
- `invariants` includes the source contracts.
- `section_count` is > 0.
- `conductor_events` includes the two new phase names.
- Existing dry-run output fields (run_status, step_count, checkpoint_count, evidence_summary, final_report) are unchanged.
- No filesystem writes occur.
- No subprocess calls occur.
- No network calls occur.
- Existing context_pack_inputs and context_compiler tests still pass.

## Tests

### In `services/conductor/tests/test_dry_run.py`

Add `TestContextPackIntegration` class:

```python
class TestContextPackIntegration:
    """Context pack integration in conductor dry-run."""

    def test_dry_run_output_includes_context_pack_summary(self):
        result = run_conductor_dry_run()
        assert "context_pack_summary" in result
        assert result["context_pack_summary"]["present"] is True

    def test_context_pack_key_fields(self):
        result = run_conductor_dry_run()
        summary = result["context_pack_summary"]
        assert summary["context_pack_id"] == "cp-dry-run-001-ariadne"
        assert summary["domain"] == "dry-run"
        assert summary["risk_level"] == "low"
        assert len(summary["risks"]) > 0
        assert len(summary["anchors"]) > 0
        assert len(summary["invariants"]) > 0
        assert summary["section_count"] > 0

    def test_context_pack_deterministic(self):
        result1 = run_conductor_dry_run()
        result2 = run_conductor_dry_run()
        assert result1["context_pack_summary"] == result2["context_pack_summary"]

    def test_conductor_events_include_context_phases(self):
        result = run_conductor_dry_run()
        events = result["conductor_events"]
        assert "generate_context_pack_inputs" in events
        assert "compile_context_pack" in events

    def test_existing_output_fields_preserved(self):
        result = run_conductor_dry_run()
        assert result["dry_run"] == "conductor"
        assert result["run_status"] == "completed"
        assert result["step_count"] == 2
        assert result["checkpoint_count"] == 2
        assert result["final_report_present"] is True
```

### Compatibility

- All existing dry-run tests pass (existing assertion about `conductor_events` count may need updating from 12 to 14).
- Context pack input generator tests pass.
- Context compiler tests pass.

## Future Allowed Write Paths

- `services/conductor/src/conductor/dry_run.py` — modify
- `services/conductor/tests/test_dry_run.py` — modify

Precommit review may later write only:
- `.project-memory/pr/0058-conductor-context-pack-dry-run/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0058-conductor-context-pack-dry-run/PLAN.md` (planner only)
- `.project-memory/pr/0058-conductor-context-pack-dry-run/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**`
- `services/core/**`
- `services/runner/**`
- `services/domain_adapters/**`
- `packages/**`
- `agents/**`
- `apps/**`
- `.ariadne/**`
- `.github/**`
- `docker/**`
- `Dockerfile*`
- `pyproject.toml`
- `package.json`
- `Makefile`
- `.project-memory/anchors.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/templates/**`
- `.grace/**`
- `services/conductor/src/conductor/context_pack_inputs.py` (no direct changes)
- `services/conductor/src/conductor/context_compiler.py` (no direct changes)
- `services/conductor/tests/test_context_pack_inputs.py` (no changes)
- `services/conductor/tests/test_context_compiler.py` (no changes)
- `services/conductor/src/conductor/__main__.py` (no CLI changes)

## Required Tests / Validation

### Focused tests

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_dry_run.py -v
```

### Compatibility

```bash
PYTHONPATH=services/conductor/src python -m pytest services/conductor/tests/test_context_pack_inputs.py -q
PYTHONPATH=services/conductor/src python -m pytest services/conductor/tests/test_context_compiler.py -q
```

### Broader checks

```bash
python -m compileall -f services packages
python -m pytest -q
```

### Forbidden pattern guard

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/conductor/src/conductor/dry_run.py || true
```

### Shell placeholder guard

```bash
grep -R -n "\$(" services/conductor/src/conductor/dry_run.py services/conductor/tests/test_dry_run.py || true
```

### Git status

```bash
git status --short
git diff --name-only
```

## Post-change Checks

```bash
grep -n "_phase_generate_context_pack_inputs\|_phase_compile_context_pack\|REPO_ID\|PURPOSE_ID\|DOMAIN\|RISK_LEVEL\|BASE_SHA\|INDEX_VERSION\|context_pack_summary" services/conductor/src/conductor/dry_run.py
grep -n "TestContextPackIntegration" services/conductor/tests/test_dry_run.py
```

## Expected Changed Files

1. `services/conductor/src/conductor/dry_run.py` — add context pack phases, constants, and output summary
2. `services/conductor/tests/test_dry_run.py` — add context pack integration tests

Expected future review artifact:
- `.project-memory/pr/0058-conductor-context-pack-dry-run/reviews/precommit-review.yml`

## Non-goals

- no repository scanner
- no repository graph computation
- no RAG/vector search
- no cache backend
- no distributed cache
- no GitHub integration
- no UI product loop
- no model calls
- no provider integration
- no network
- no subprocess
- no Docker
- no dependency changes
- no filesystem writes to project memory
- no schema changes
- no docs changes
- no new modules
- no CLI changes
- no changes to existing generator/compiler modules
- no `.ariadne/**`
- no `.grace/**`

## Stop Conditions

- about to write `services/core/**` → stop
- about to write `services/runner/**` → stop
- about to write `services/domain_adapters/**` → stop
- about to write `packages/**` → stop
- about to write `agents/**` → stop
- about to write `apps/**` → stop
- about to write `schemas/**` → stop
- about to write `docs/**` → stop
- about to write project-memory templates → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- about to modify `.project-memory/anchors.yml` → stop
- about to modify `.project-memory/project_contract.yml` → stop
- about to modify `context_pack_inputs.py` or `context_compiler.py` → stop
- about to implement repository scanning → stop
- about to implement RAG/vector search → stop
- about to implement cache backend → stop
- about to add dependency/build config → stop
- about to add network/subprocess/model/provider behavior → stop
- old names/examples would be introduced → stop
- shell placeholders would be introduced → stop

## Open Questions

1. **Should the context pack summary include the full context pack or a summary?** **Decision:** Summary. The full context pack is available via `ctx.context_pack` for tests, but the dry-run output keeps a compact summary (`present`, `context_pack_id`, `task`, `domain`, `risk_level`, `risks`, `anchors`, `invariants`, `section_count`). This keeps the output readable while proving the compilation works.

2. **Should the new phases go before or after `plan_steps`?** **Decision:** After `plan_steps`, before `start_run`. The context pack should be ready before the run starts, since it provides context for step execution. The `plan_steps` phase establishes the step structure, then context inputs are generated and compiled.

3. **Should `conductor_events` count break existing tests?** **Decision:** Yes — existing tests assert a specific event count (12). The new phases add 2 events, making it 14. Existing tests must be updated to expect 14 events. This is a planned change in the test file.

4. **Should `REPO_ID`, `PURPOSE_ID` etc. be module-level constants or inline in the phase function?** **Decision:** Module-level constants. This follows the existing pattern of `T0`–`T4` timestamps. Clean, deterministic, and self-documenting.

## Decisions Made

### implementation_files

```
services/conductor/src/conductor/dry_run.py (modify)
```

### test_files

```
services/conductor/tests/test_dry_run.py (modify)
```

### output_shape

```
context_pack_summary dict added to dry-run output with:
  present, context_pack_id, task, domain, risk_level,
  risks (list), anchors (list), invariants (list), section_count (int)
```

### integration_api

```
Two new phase functions added to _PHASES:
  _phase_generate_context_pack_inputs  → calls build_context_pack_inputs(...)
  _phase_compile_context_pack          → calls compile_context_pack(...)

Five deterministic module-level constants:
  REPO_ID, PURPOSE_ID, DOMAIN, RISK_LEVEL, BASE_SHA, INDEX_VERSION
```

### validation_rules

- Dry-run succeeds with context pack phases.
- Output includes context_pack_summary with present=true.
- context_pack_id is deterministic.
- Risks/anchors/invariants are non-empty.
- section_count > 0.
- Existing output fields preserved.
- Events list includes new phase names.
- No filesystem writes, no subprocess, no network.

### deterministic_policy

- All compiler params are explicit constants or derived from deterministic inputs.
- No current-time, no random ids, no absolute paths, no machine-specific values.
- Stable ordering via generator/compiler normalization.
- No old names/examples, no shell placeholders.

### validation_strategy

```
Focused tests for context pack integration in dry_run.py.
Existing compatibility tests for generator, compiler, and dry-run.
Forbidden pattern grep.
Shell placeholder grep.
compileall + global pytest.
```

---

PLAN written: yes

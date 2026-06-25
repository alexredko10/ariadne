# PR 0057 — Minimal Context Compiler Plan

## Goal

Plan a minimal deterministic context compiler.

The compiler should convert explicit context-pack inputs into a compact context-pack object compatible with:

```
schemas/context-pack.schema.yml
```

This is the first context-pack assembly layer after the context-pack input generator.

## Architectural Thesis

Ariadne should compile context from explicit inputs, not from hidden repository scanning.

Context Steward records workspace memory.
Context Pack Input Generator normalizes explicit inputs.
Minimal Context Compiler assembles those inputs into a compact context pack.

The model is replaceable.
The context-pack contract is durable.

This PR adds deterministic context-pack assembly only.
It does not implement repository discovery, RAG, model calls, or runtime integration.

## Context Snapshot

- **current HEAD sha**: `94f26aa6384aca758d7ee9e982bc3a6836fac535`
- **current branch**: `0057-minimal-context-compiler`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `94f26aa` (merge commit — no skew relative to main)
- **index_version**: `"0.23"` (from `.project-memory/context-bundles/contracts.yml` — PR 0056 bumped it)
- **stale_snapshot**: false — HEAD is current with merged PR 0056, no pending changes
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
- `schemas/context-pack-inputs.schema.yml`
- `schemas/context-pack.schema.yml`
- `schemas/context-steward.schema.yml`
- `schemas/feature-workspace-memory.schema.yml`
- `schemas/qa-evidence-record.schema.yml`
- `schemas/cache-key.schema.yml`
- `docs/PR_WORKSPACE_MEMORY.md`
- `docs/CONTEXT_COMPILER.md`
- `docs/CONTEXT_STEWARD.md`
- `docs/CONTEXT_STEWARD_PROMPTS.md`
- `docs/CACHE_CONTRACTS.md`
- `.project-memory/templates/context-pack-inputs.yml`
- `services/conductor/src/conductor/context_pack_inputs.py`
- `services/conductor/tests/test_context_pack_inputs.py`
- `services/conductor/src/conductor/dry_run.py`
- `services/conductor/src/conductor/__init__.py`
- `services/conductor/src/conductor/__main__.py`
- `services/conductor/tests/test_dry_run.py`
- `.project-memory/pr/0052-cache-contracts-and-keys/PLAN.md`
- `.project-memory/pr/0053-context-steward-contract/PLAN.md`
- `.project-memory/pr/0054-context-steward-prompt-templates/PLAN.md`
- `.project-memory/pr/0055-pr-workspace-memory-artifacts/PLAN.md`
- `.project-memory/pr/0056-context-pack-input-generator/PLAN.md`

## Existing Contract Snapshot

### Context Pack Input Schema (`schemas/context-pack-inputs.schema.yml`)

20 fields: pr_id, feature_id, task_goal, source_contracts, relevant_anchors, allowed_paths, forbidden_paths, cache_key_refs, prior_pr_refs, qa_evidence_refs, known_risks, manual_checks_required, context_freshness (status + last_verified_hook), invalidation_inputs, requested_context_sections, output_preferences, created_from, updated_by.

### Context Pack Input Generator (`services/conductor/src/conductor/context_pack_inputs.py`)

Exports: `build_context_pack_inputs(...)`, `normalize_context_pack_inputs(raw)`, `validate_context_pack_inputs(raw)`, `context_pack_inputs_error(field, reason)`.

Pure functions, no I/O, no subprocess, no network, no models.

### Context Pack Schema (`schemas/context-pack.schema.yml`)

Blueprint with 20 fields. Required: context_pack_id, repo_id, task, purpose_id, domain, risk_level, base_sha, index_version, task_subgraph, relevant_files, relevant_symbols, related_tests, configs, invariants, risks, recent_changes, suggested_entry_points, stable_prompt_blocks, state_first_context, anchors.

Key gap: Context-pack-inputs does not include many fields the context pack requires:
- `repo_id` — not in inputs (must be caller-provided)
- `purpose_id` — not in inputs (must be caller-provided)
- `domain` — not in inputs (must be caller-provided)
- `risk_level` — not in inputs (must be caller-provided)
- `base_sha` — not in inputs (must be caller-provided)
- `index_version` — not in inputs (must be caller-provided)
- `task_subgraph` — not in inputs (must be caller-provided or empty)
- `relevant_files` — not in inputs (must be caller-provided or empty)
- `relevant_symbols` — not in inputs (must be caller-provided or empty)
- `related_tests` — not in inputs (must be caller-provided or empty)
- `configs` — not in inputs (must be caller-provided or empty)
- `invariants` — not in inputs (must be caller-provided or empty)
- `recent_changes` — not in inputs (must be caller-provided or empty)
- `suggested_entry_points` — not in inputs (must be caller-provided or empty)
- `stable_prompt_blocks` — not in inputs (empty by default)
- `state_first_context` — not in inputs (null by default)

This means the minimal compiler must accept additional explicit parameters beyond context-pack-inputs.

### Conductor Package

```
services/conductor/src/conductor/
    __init__.py
    __main__.py
    dry_run.py
    context_pack_inputs.py   (PR 0056)
tests/
    __init__.py
    test_conductor_smoke.py
    test_dry_run.py
    test_context_pack_inputs.py  (PR 0056)
```

## Implementation Location Decision

**Decision: Two files to create in the conductor package.**

### Implementation

1. **`services/conductor/src/conductor/context_compiler.py`** — compiler module.

### Tests

2. **`services/conductor/tests/test_context_compiler.py`** — focused tests.

### No CLI/docs integration

- No `__main__.py` modification — the compiler is a library function, not a CLI command.
- No modification to `dry_run.py` — conductor integration is a future PR.
- No modification to `CONTEXT_COMPILER.md` — docs already describe the intended architecture. The minimal compiler boundary is compatible.

### No changes to:

- `schemas/` — no schema changes in this PR.
- `services/core/`, `services/runner/`, `services/domain_adapters/`
- `packages/`, `agents/`, `apps/`
- `.project-memory/templates/`, `.project-memory/anchors.yml`, `.project-memory/project_contract.yml`
- `pyproject.toml`

## Compiler Contract

### Pure function API

```python
def compile_context_pack(
    *,
    context_pack_inputs: dict,
    repo_id: str,
    purpose_id: str,
    domain: str,
    risk_level: str,
    base_sha: str,
    index_version: str,
    task_subgraph: list[str] | None = None,
    relevant_files: list[str] | None = None,
    relevant_symbols: list[str] | None = None,
    related_tests: list[str] | None = None,
    configs: list[str] | None = None,
    invariants: list[str] | None = None,
    recent_changes: list[str] | None = None,
    suggested_entry_points: list[str] | None = None,
) -> dict:
    """Compile a context-pack from explicit inputs.

    Parameters
    ----------
    context_pack_inputs
        A validated context-pack-inputs dict (from build_context_pack_inputs).
    repo_id
        Repository identifier.
    purpose_id
        Purpose identifier.
    domain
        Domain name (e.g. "coding").
    risk_level
        Risk level string.
    base_sha
        Git base SHA at pack creation time.
    index_version
        Memory index version at pack creation time.
    task_subgraph
        Relevant dependency subgraph.
    relevant_files
        Relevant file paths.
    relevant_symbols
        Relevant symbol names.
    related_tests
        Related test file paths.
    configs
        Configuration file paths.
    invariants
        Invariant identifiers.
    recent_changes
        Recent commit descriptions.
    suggested_entry_points
        Entry point suggestions.

    Returns
    -------
    dict
        A compact context-pack dict compatible with schemas/context-pack.schema.yml.

    Raises
    ------
    ValueError
        If required fields are missing.
    """
```

### Helper functions

```python
def normalize_context_pack(raw: dict) -> dict:
    """Normalize a context-pack dict to canonical form."""

def validate_context_pack(raw: dict) -> None:
    """Validate a context-pack dict."""
```

### Error model

Reuse `ValueError` as established by the context-pack input generator. No custom exception needed.

### Input-to-output mapping

The compiler maps from context-pack-inputs fields to context-pack fields. Additional parameters are passed as explicit function arguments (not inferred from repository or environment).

| Context pack field | Source |
|---|---|
| `context_pack_id` | Generated deterministically from `pr_id`, `repo_id`, `purpose_id`, `base_sha` — `f"cp-{pr_id}-{repo_id}"` |
| `repo_id` | Explicit parameter |
| `task` | From `context_pack_inputs.task_goal` |
| `purpose_id` | Explicit parameter |
| `domain` | Explicit parameter |
| `risk_level` | Explicit parameter |
| `base_sha` | Explicit parameter |
| `index_version` | Explicit parameter |
| `task_subgraph` | Explicit parameter (optional) |
| `relevant_files` | Explicit parameter (optional) |
| `relevant_symbols` | Explicit parameter (optional) |
| `related_tests` | Explicit parameter (optional) |
| `configs` | Explicit parameter (optional) |
| `invariants` | From `context_pack_inputs.source_contracts` (selected as invariants) |
| `risks` | From `context_pack_inputs.known_risks` (extracted descriptions) |
| `recent_changes` | Explicit parameter (optional) |
| `suggested_entry_points` | Explicit parameter (optional) |
| `stable_prompt_blocks` | Empty list (not yet supported) |
| `state_first_context` | `None` (not yet supported) |
| `anchors` | From `context_pack_inputs.relevant_anchors` |

### Section model (logical)

The compiler produces a compact dict. If a future version needs nested sections, it can build them. For this PR, the output is a flat dict with the required context-pack fields.

### Determinism

- `context_pack_id` is deterministic: `f"cp-{pr_id}-{repo_id}"` — no randomness.
- Lists are sorted for deterministic output (following the same pattern as context_pack_inputs.py).
- No current-time generation.
- No random ids.
- No absolute local paths.
- No machine-specific values.
- No shell placeholders.
- No old names/examples.

### Validation

- `context_pack_inputs` is validated by the caller (the compiler assumes it's already validated by `validate_context_pack_inputs`).
- Compiler validates additional explicit parameters:
  - `repo_id`, `purpose_id`, `domain`, `risk_level`, `base_sha`, `index_version` — all required, non-empty.
  - `context_pack_inputs` — required, must be a dict.
  - `context_pack_inputs.pr_id` — must be present and non-empty (for context_pack_id generation).
  - Optional lists: each entry must be a non-empty string.

### Serialization

The compiler returns plain Python dicts. No YAML/JSON dependency. No filesystem writing. Dicts are serializable with `json.dumps(sort_keys=True)`.

## Tests

### Test module: `services/conductor/tests/test_context_compiler.py`

### Test coverage

**`compile_context_pack`** (primary function):

- minimal valid input: only required explicit params + minimal inputs — produces a valid context-pack dict with all fields.
- full input: all optional fields provided — preserves all values.
- defaults: empty lists for optional fields.
- `context_pack_id` is deterministic: same inputs → same id.
- required `repo_id`: empty string raises `ValueError`.
- required `purpose_id`: empty string raises `ValueError`.
- required `domain`: empty string raises `ValueError`.
- required `risk_level`: empty string raises `ValueError`.
- required `base_sha`: empty string raises `ValueError`.
- required `index_version`: empty string raises `ValueError`.
- invalid `context_pack_inputs` (not a dict): raises `ValueError`.
- `context_pack_inputs` without `pr_id`: raises `ValueError`.
- determinism: repeated calls with same inputs produce equal output dicts.
- determinism: lists are sorted in output.
- no I/O: function does not read filesystem.
- no subprocess: function does not call subprocess.
- output dict keys match `schemas/context-pack.schema.yml` field names.
- output dict has all required context-pack fields present.
- `invariants` mapped from `source_contracts`.
- `risks` mapped from `known_risks` descriptions.
- `anchors` mapped from `relevant_anchors`.
- Non-empty `stable_prompt_blocks` is empty (not yet supported).
- `state_first_context` is `None`.

**`normalize_context_pack`**:

- already-normalized input returns same structure.
- unsorted lists are sorted.
- empty lists are removed.
- empty strings are removed.
- `None` values are removed.

**`validate_context_pack`**:

- valid dict passes without exception.
- invalid dict (missing `task`) raises `ValueError`.
- invalid dict (missing `context_pack_id`) raises `ValueError`.

### Compatibility

- Context pack input generator tests still pass.
- Conductor dry-run tests still pass.

### Forbidden pattern guard

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/conductor/src/conductor/context_compiler.py services/conductor/tests/test_context_compiler.py || true
```

Expect zero matches.

## Future Allowed Write Paths

- `services/conductor/src/conductor/context_compiler.py`
- `services/conductor/tests/test_context_compiler.py`

Precommit review may later write only:
- `.project-memory/pr/0057-minimal-context-compiler/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0057-minimal-context-compiler/PLAN.md` (planner only)
- `.project-memory/pr/0057-minimal-context-compiler/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**` — no registry or template changes
- `.project-memory/anchors.yml` — deferred
- `.project-memory/project_contract.yml` — deferred
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

## Required Tests / Validation

### Implementation tests

```bash
PYTHONPATH=services/conductor/src python -m pytest services/conductor/tests/test_context_compiler.py -v
```

### Compatibility

```bash
PYTHONPATH=services/conductor/src python -m pytest services/conductor/tests/test_context_pack_inputs.py -q
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_dry_run.py -q
```

### Broader checks

```bash
python -m compileall -f services packages
python -m pytest -q
git status --short
git diff --name-only
```

### Forbidden pattern guard

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/conductor/src/conductor/context_compiler.py services/conductor/tests/test_context_compiler.py || true
```

### Shell placeholder guard

```bash
grep -R -n "\$(" services/conductor/src/conductor/context_compiler.py services/conductor/tests/test_context_compiler.py || true
```

## Post-change Checks

```bash
grep -n "def compile_context_pack\|def normalize_context_pack\|def validate_context_pack" services/conductor/src/conductor/context_compiler.py
grep -n "class TestCompileContextPack\|class TestNormalizeContextPack\|class TestValidateContextPack" services/conductor/tests/test_context_compiler.py
```

## Expected Changed Files

1. `services/conductor/src/conductor/context_compiler.py` — compiler module
2. `services/conductor/tests/test_context_compiler.py` — tests

Expected future review artifact:
- `.project-memory/pr/0057-minimal-context-compiler/reviews/precommit-review.yml`

## Non-goals

- no repository scanner
- no repository graph computation
- no RAG/vector search
- no cache backend
- no distributed cache
- no GitHub integration
- no UI/CLI product loop
- no model calls
- no provider integration
- no network
- no subprocess
- no Docker
- no dependency changes
- no runtime integration into conductor pipeline
- no filesystem writes to project memory
- no read of filesystem to infer inputs
- no `.ariadne/**`
- no `.grace/**`
- no schemas changes
- no docs changes

## Stop Conditions

- about to write `services/core/**` → stop
- about to write `services/runner/**` → stop
- about to write `services/domain_adapters/**` → stop
- about to write `packages/**` → stop
- about to write `agents/**` → stop
- about to write `apps/**` → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- about to modify `schemas/**` → stop (no schema changes)
- about to modify `docs/**` → stop (no docs changes)
- about to modify project memory templates → stop
- about to modify `.project-memory/anchors.yml` → stop
- about to modify `.project-memory/project_contract.yml` → stop
- about to implement repository scanning → stop
- about to implement RAG/vector search → stop
- about to implement cache backend → stop
- about to read filesystem or environment to infer inputs → stop
- about to add dependency/build config → stop
- about to add network/subprocess/model/provider behavior → stop
- shared mutable state → stop
- old names/examples would be introduced → stop
- shell placeholders would be introduced → stop

## Open Questions

1. **Should `context_pack_id` include a hash or be a readable string?** **Decision:** Readable string: `f"cp-{pr_id}-{repo_id}"`. This is deterministic and traceable. If uniqueness is needed later, a hash suffix can be appended.

2. **Should the compiler accept `context_pack_inputs` as a dict or as individual parameters?** **Decision:** Dict. The compiler accepts a validated `context_pack_inputs` dict (from `build_context_pack_inputs`). Additional parameters that the schema requires but inputs don't provide are explicit function params. This keeps the API clean: "give me your inputs dict, plus these required extra fields."

3. **Should the compiler populate `stable_prompt_blocks` or leave it empty?** **Decision:** Empty list. Stable prompt blocks are not yet supported by any generator. The compiler correctly leaves them empty.

4. **Should the compiler read `schemas/cache-key.schema.yml` at runtime to validate cache key refs?** **Decision:** No. Cache key refs are already validated by `build_context_pack_inputs`. The compiler trusts the validated inputs dict and passes refs through as-is.

## Decisions Made

### implementation_files

```
services/conductor/src/conductor/context_compiler.py
```

### test_files

```
services/conductor/tests/test_context_compiler.py
```

### optional_docs_updates

None.

### optional_integration_updates

None. No CLI, no dry_run modification, no conductor pipeline integration.

### compiler_api

```
compile_context_pack(
    context_pack_inputs: dict,     # from build_context_pack_inputs()
    repo_id: str,
    purpose_id: str,
    domain: str,
    risk_level: str,
    base_sha: str,
    index_version: str,
    task_subgraph: list[str] | None = None,
    relevant_files: list[str] | None = None,
    relevant_symbols: list[str] | None = None,
    related_tests: list[str] | None = None,
    configs: list[str] | None = None,
    invariants: list[str] | None = None,
    recent_changes: list[str] | None = None,
    suggested_entry_points: list[str] | None = None,
) -> dict

normalize_context_pack(raw: dict) -> dict
validate_context_pack(raw: dict) -> None
```

### input_to_output_mapping

```
context_pack_id  → f"cp-{inputs.pr_id}-{repo_id}"
task             → inputs.task_goal
risks            → inputs.known_risks descriptions
invariants       → inputs.source_contracts (selected as invariants)
anchors          → inputs.relevant_anchors
repo_id, purpose_id, domain, risk_level, base_sha, index_version,
task_subgraph, relevant_files, relevant_symbols, related_tests,
configs, recent_changes, suggested_entry_points  → explicit params
stable_prompt_blocks  → []
state_first_context   → None
```

### section_model

Flat dict. No nested sections. All context-pack fields are top-level keys.

### validation_rules

- All 6 required explicit params: non-empty strings.
- `context_pack_inputs`: must be a dict with non-empty `pr_id`.
- Optional lists: each entry non-empty string.
- Validation is deterministic and in-process.

### serialization_policy

Plain Python dicts. No YAML/JSON dependency. No file writing. JSON-serializable with `sort_keys=True`.

### deterministic_policy

- `context_pack_id` deterministic from inputs.
- Sorted lists for non-semantic ordering.
- No current-time generation.
- No random ids.
- No path normalization beyond existing patterns.
- No old names/examples.

### validation_strategy

```
Focused tests via pytest.
Compatibility tests (input generator + dry_run still pass).
Forbidden pattern grep.
Shell placeholder grep.
compileall + global pytest.
```

---

PLAN written: yes

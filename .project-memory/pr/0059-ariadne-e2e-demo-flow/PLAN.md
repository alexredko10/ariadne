# PR 0059 — Ariadne E2E Demo Flow Plan

## Goal

Plan a small deterministic end-to-end demo flow for Ariadne.

The demo should show the current substrate path working together:

1. explicit demo input
2. context-pack input generator
3. minimal context compiler
4. conductor dry-run integration
5. deterministic output assertion

## Architectural Thesis

Ariadne should show an end-to-end substrate path before adding broader automation.

0056 created context-pack inputs.
0057 compiled context packs.
0058 exposed context packs through conductor dry-run.
0059 should make this path visible and testable as a demo flow.

The model is replaceable.
The substrate path is durable.

## Context Snapshot

- **current HEAD sha**: `cac78559b48866d7bf31aa779a2af8cc5aa01ffe`
- **current branch**: `0059-ariadne-e2e-demo-flow`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `cac7855` (merge commit — no skew relative to main)
- **index_version**: `"0.25"` (from `.project-memory/context-bundles/contracts.yml` — PR 0058 bumped it)
- **stale_snapshot**: false — HEAD is current with merged PR 0058, no pending changes
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
- `services/conductor/tests/test_dry_run.py`
- `services/conductor/src/conductor/context_pack_inputs.py`
- `services/conductor/tests/test_context_pack_inputs.py`
- `services/conductor/src/conductor/context_compiler.py`
- `services/conductor/tests/test_context_compiler.py`
- `schemas/context-pack-inputs.schema.yml`
- `schemas/context-pack.schema.yml`
- `docs/PR_WORKSPACE_MEMORY.md`
- `docs/CONTEXT_STEWARD.md`
- `docs/CONTEXT_STEWARD_PROMPTS.md`
- `.project-memory/pr/0055-pr-workspace-memory-artifacts/PLAN.md`
- `.project-memory/pr/0056-context-pack-input-generator/PLAN.md`
- `.project-memory/pr/0057-minimal-context-compiler/PLAN.md`
- `.project-memory/pr/0058-conductor-context-pack-dry-run/PLAN.md`

## Existing Contract Snapshot

### Context Pack Input Generator (`conductor/context_pack_inputs.py`)

`build_context_pack_inputs(...)` → normalized dict. Pure function, no I/O.

### Minimal Context Compiler (`conductor/context_compiler.py`)

`compile_context_pack(context_pack_inputs, repo_id, purpose_id, ...)` → compact context pack dict. Pure function, no I/O.

### Conductor Dry-Run (`conductor/dry_run.py`)

14-phase pipeline. Includes `generate_context_pack_inputs` and `compile_context_pack` phases (PR 0058). Output includes `context_pack_summary` with context_pack_id, task, domain, risk_level, risks, anchors, invariants, section_count.

### Conductor Dry-Run Tests (`tests/test_dry_run.py`)

Includes `TestContextPackIntegration` with 5 tests (PR 0058). Tests: output summary present, key fields deterministic, determinism across calls, events include context phases, existing fields preserved.

### Existing test infrastructure

- `test_context_pack_inputs.py` — pure function tests for input generator.
- `test_context_compiler.py` — pure function tests for context compiler.
- `test_dry_run.py` — integration tests for full dry-run pipeline.

### No examples directory

The repository has no `examples/` directory. All demo/test code lives in `services/conductor/tests/`.

## Implementation Location Decision

**Decision: Two files to create.**

### Test file

1. **`services/conductor/tests/test_ariadne_e2e_demo_flow.py`** — focused E2E demo test.

### Documentation file

2. **`docs/ARIADNE_E2E_DEMO_FLOW.md`** — short demo flow documentation.

**Rationale for test file path:** `services/conductor/tests/` is the established test location for conductor code. The E2E demo test exercises conductor dry-run + context-pack input generator + context compiler — all of which live under the conductor package. No new service or package needed.

**Rationale for docs file path:** `docs/` is the established documentation location. The demo flow doc explains the substrate path in user-facing terms.

**Rejected alternatives:**
- `examples/` — no such directory exists. Creating one would be inconsistent with the project pattern (all runnable code is in `services/`).
- `services/conductor/src/conductor/demo_e2e.py` — a standalone module would be redundant since the test provides the same deterministic output. Tests are the canonical demo.
- CLI integration in `__main__.py` — unnecessary. The demo is exercised via pytest.

**Not modified:**
- `services/core/**`, `services/runner/**`, `services/domain_adapters/**`
- `packages/`, `agents/`, `apps/`
- `schemas/`, `.project-memory/templates/`
- `.project-memory/anchors.yml`, `.project-memory/project_contract.yml`
- `pyproject.toml`
- No changes to existing files.

## Demo Flow Contract

### Callable: `run_ariadne_e2e_demo() -> dict`

The demo exercise is a test-level callable, not a standalone module. It is imported and run by the test.

```python
def run_ariadne_e2e_demo() -> dict:
    """Execute a deterministic Ariadne E2E demo flow.

    Exercises:
    1. Context pack input generation
    2. Context compilation
    3. Conductor dry-run pipeline

    Returns a dict with all intermediate and final outputs.
    """
```

### Flow steps

1. Build explicit demo inputs using `build_context_pack_inputs`.
2. Compile context pack using `compile_context_pack` with explicit params.
3. Run `run_conductor_dry_run()` which internally calls both generator and compiler.
4. Assert all intermediate outputs are deterministic.
5. Return a comprehensive output dict.

### Output dict shape

```python
{
    "demo_name": "Ariadne E2E Substrate Demo",
    "demo_version": "0.1",
    "pr_id": "demo-0059",
    "feature_id": "demo-context-pack-flow",
    "task_goal": "Demonstrate deterministic context-pack dry-run flow",

    # Step 1: context-pack inputs
    "context_pack_inputs": {
        "pr_id": "demo-0059",
        "task_goal": "Demonstrate deterministic context-pack dry-run flow",
        "source_contracts": ["context-pack.schema", "context-pack-inputs.schema"],
        "relevant_anchors": ["@ariadne-domain demo"],
        "allowed_paths": ["services/**", "docs/**"],
        "forbidden_paths": [".git/**", ".env"],
        "cache_key_refs": [{"namespace": "context", "artifact_kind": "context_pack"}],
        "prior_pr_refs": [{"pr_id": "0058", "title": "Conductor context-pack dry-run"}],
        "qa_evidence_refs": ["ev-pass-001"],
        "known_risks": [{"id": "demo-risk", "description": "Demo risk for demonstration", "severity": "low"}],
        "manual_checks_required": ["Verify demo output determinism"],
        "context_freshness": {"status": "fresh", "last_verified_hook": "demo"},
        "requested_context_sections": ["task", "scope", "risks"],
        "output_preferences": {"format": "compact", "include_anchors": True},
    },

    # Step 2: compiled context pack
    "context_pack": {
        "context_pack_id": "cp-demo-0059-ariadne",
        "repo_id": "ariadne",
        "task": "Demonstrate deterministic context-pack dry-run flow",
        "domain": "demo",
        "risk_level": "low",
        "invariants": ["context-pack.schema", "context-pack-inputs.schema"],
        "risks": ["Demo risk for demonstration"],
        "anchors": ["@ariadne-domain demo"],
    },

    # Step 3: conductor dry-run output (summary)
    "conductor_dry_run_summary": {
        "run_id": "dry-run-001",
        "run_status": "completed",
        "step_count": 2,
        "checkpoint_count": 2,
        "evidence_count": 2,
        "final_report_present": True,
        "context_pack_summary": {
            "present": True,
            "context_pack_id": "cp-dry-run-001-ariadne",
        },
    },

    # Proof markers
    "deterministic": True,
    "model_free": True,
    "repository_scan_free": True,
}
```

## Demo Input Shape

### Input constants

```python
DEMO_PR_ID = "demo-0059"
DEMO_FEATURE_ID = "demo-context-pack-flow"
DEMO_TASK_GOAL = "Demonstrate deterministic context-pack dry-run flow"
DEMO_DOMAIN = "demo"
DEMO_REPO_ID = "ariadne"
DEMO_PURPOSE_ID = "demo-purpose"
DEMO_RISK_LEVEL = "low"
DEMO_BASE_SHA = "demo-abc123"
DEMO_INDEX_VERSION = "0.25"
```

### Input contracts and anchors

```python
DEMO_SOURCE_CONTRACTS = [
    "context-pack.schema",
    "context-pack-inputs.schema",
]
DEMO_RELEVANT_ANCHORS = [
    "@ariadne-domain demo",
    "@ariadne-risk low",
]
```

### Paths

```python
DEMO_ALLOWED_PATHS = ["services/**", "docs/**"]
DEMO_FORBIDDEN_PATHS = [".git/**", ".env", "secrets/**"]
```

### Cache, prior PR, and QA refs

```python
DEMO_CACHE_KEY_REFS = [
    {"namespace": "context", "artifact_kind": "context_pack"},
    {"namespace": "context", "artifact_kind": "repository_snapshot_summary"},
]
DEMO_PRIOR_PR_REFS = [
    {"pr_id": "0058", "title": "Conductor context-pack dry-run"},
    {"pr_id": "0057", "title": "Minimal context compiler"},
]
DEMO_QA_EVIDENCE_REFS = ["ev-pass-001", "ev-pass-002"]
```

### Risks and manual checks

```python
DEMO_KNOWN_RISKS = [
    {"id": "demo-risk-001", "description": "Demo risk for demonstration purposes", "severity": "low"},
]
DEMO_MANUAL_CHECKS = [
    "Verify demo output determinism",
    "Verify no repository scan occurred",
    "Verify no model calls occurred",
]
```

### Freshness and preferences

```python
DEMO_CONTEXT_FRESHNESS_STATUS = "fresh"
DEMO_CONTEXT_FRESHNESS_LAST_VERIFIED = "demo"
DEMO_REQUESTED_SECTIONS = ["task", "scope", "risks", "anchors"]
DEMO_OUTPUT_PREFERENCES = {"format": "compact", "include_anchors": True}
```

### No old names/examples

All demo terminology uses Ariadne-native names. No `water_meter`, `Broken Clock`, `.grace`, `@grace-*`, or old Flask examples.

## Output Assertions

The E2E demo test must assert:

1. **Context-pack inputs** — `inputs["pr_id"] == "demo-0059"`, non-empty `source_contracts`, `relevant_anchors`, `allowed_paths`, `forbidden_paths`, `cache_key_refs`, `known_risks`, `manual_checks_required`.
2. **Context pack** — `pack["context_pack_id"] == "cp-demo-0059-ariadne"`, non-empty `task`, `domain`, `invariants`, `risks`, `anchors`.
3. **Conductor dry-run** — `summary["dry_run"] == "conductor"`, `summary["run_status"] == "completed"`, `summary["step_count"] == 2`, `summary["context_pack_summary"]["present"]` is `True`.
4. **Determinism** — Two consecutive calls produce identical output dicts (via `json.dumps(sort_keys=True)` or recursive equality).
5. **No I/O** — The demo function does not write files, call subprocess, or make network calls. Verified by review, not by runtime check.
6. **Serializable** — Output can be serialized with `json.dumps(sort_keys=True)`.

## Documentation

**Path:** `docs/ARIADNE_E2E_DEMO_FLOW.md`

The doc must be concise — 2–3 paragraphs maximum. Content:

- **What this is:** A deterministic end-to-end substrate demo for Ariadne.
- **What it exercises:** Context pack input generation, minimal context compilation, conductor dry-run integration.
- **How to run:** `PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_ariadne_e2e_demo_flow.py -v`
- **What it proves:** Deterministic output, no model calls, no repository scanning, no cache backend, no filesystem writes — entirely explicit-input-driven.
- **Next step:** After this demo, the substrate path is complete enough for broader automation design.

No product pitch. No GitHub workflow claims. No UI/CLI claims. No long list of things not modified.

## Tests

### Test module: `services/conductor/tests/test_ariadne_e2e_demo_flow.py`

```python
"""Ariadne E2E deterministic substrate demo."""

from __future__ import annotations

import json

from conductor.dry_run import run_conductor_dry_run
from conductor.context_pack_inputs import build_context_pack_inputs, validate_context_pack_inputs
from conductor.context_compiler import compile_context_pack, validate_context_pack


# ---------------------------------------------------------------------------
# Demo constants
# ---------------------------------------------------------------------------

DEMO_PR_ID = "demo-0059"
DEMO_FEATURE_ID = "demo-context-pack-flow"
DEMO_TASK_GOAL = "Demonstrate deterministic context-pack dry-run flow"
DEMO_DOMAIN = "demo"
DEMO_REPO_ID = "ariadne"
DEMO_PURPOSE_ID = "demo-purpose"
DEMO_RISK_LEVEL = "low"
DEMO_BASE_SHA = "demo-abc123"
DEMO_INDEX_VERSION = "0.25"

DEMO_SOURCE_CONTRACTS = [
    "context-pack.schema",
    "context-pack-inputs.schema",
]
DEMO_RELEVANT_ANCHORS = ["@ariadne-domain demo", "@ariadne-risk low"]
DEMO_ALLOWED_PATHS = ["services/**", "docs/**"]
DEMO_FORBIDDEN_PATHS = [".git/**", ".env", "secrets/**"]
DEMO_CACHE_KEY_REFS = [
    {"namespace": "context", "artifact_kind": "context_pack"},
    {"namespace": "context", "artifact_kind": "repository_snapshot_summary"},
]
DEMO_PRIOR_PR_REFS = [
    {"pr_id": "0058", "title": "Conductor context-pack dry-run"},
    {"pr_id": "0057", "title": "Minimal context compiler"},
]
DEMO_QA_EVIDENCE_REFS = ["ev-pass-001", "ev-pass-002"]
DEMO_KNOWN_RISKS = [
    {"id": "demo-risk-001", "description": "Demo risk for demonstration purposes", "severity": "low"},
]
DEMO_MANUAL_CHECKS = [
    "Verify demo output determinism",
    "Verify no repository scan occurred",
    "Verify no model calls occurred",
]
DEMO_CONTEXT_FRESHNESS_STATUS = "fresh"
DEMO_CONTEXT_FRESHNESS_LAST_VERIFIED = "demo"
DEMO_REQUESTED_SECTIONS = ["task", "scope", "risks", "anchors"]
DEMO_OUTPUT_PREFERENCES = {"format": "compact", "include_anchors": True}


# ---------------------------------------------------------------------------
# Demo callable
# ---------------------------------------------------------------------------


def run_ariadne_e2e_demo() -> dict:
    """Execute a deterministic Ariadne E2E demo flow."""
    # Step 1: context-pack inputs
    inputs = build_context_pack_inputs(
        pr_id=DEMO_PR_ID,
        task_goal=DEMO_TASK_GOAL,
        feature_id=DEMO_FEATURE_ID,
        source_contracts=DEMO_SOURCE_CONTRACTS,
        relevant_anchors=DEMO_RELEVANT_ANCHORS,
        allowed_paths=DEMO_ALLOWED_PATHS,
        forbidden_paths=DEMO_FORBIDDEN_PATHS,
        cache_key_refs=DEMO_CACHE_KEY_REFS,
        prior_pr_refs=DEMO_PRIOR_PR_REFS,
        qa_evidence_refs=DEMO_QA_EVIDENCE_REFS,
        known_risks=DEMO_KNOWN_RISKS,
        manual_checks_required=DEMO_MANUAL_CHECKS,
        context_freshness_status=DEMO_CONTEXT_FRESHNESS_STATUS,
        context_freshness_last_verified=DEMO_CONTEXT_FRESHNESS_LAST_VERIFIED,
        requested_context_sections=DEMO_REQUESTED_SECTIONS,
        output_preferences=DEMO_OUTPUT_PREFERENCES,
        created_from_agent="e2e-demo",
        created_from_hook="demo",
        created_from_template="context-steward.before_plan.v1",
    )

    # Step 2: context compilation
    pack = compile_context_pack(
        context_pack_inputs=inputs,
        repo_id=DEMO_REPO_ID,
        purpose_id=DEMO_PURPOSE_ID,
        domain=DEMO_DOMAIN,
        risk_level=DEMO_RISK_LEVEL,
        base_sha=DEMO_BASE_SHA,
        index_version=DEMO_INDEX_VERSION,
    )

    # Step 3: conductor dry-run
    dry_run_output = run_conductor_dry_run()

    # Step 4: build comprehensive output
    return {
        "demo_name": "Ariadne E2E Substrate Demo",
        "demo_version": "0.1",
        "pr_id": DEMO_PR_ID,
        "feature_id": DEMO_FEATURE_ID,
        "task_goal": DEMO_TASK_GOAL,
        "context_pack_inputs": inputs,
        "context_pack": pack,
        "conductor_dry_run_summary": {
            "dry_run": dry_run_output.get("dry_run"),
            "run_id": dry_run_output.get("run_id"),
            "run_status": dry_run_output.get("run_status"),
            "step_count": dry_run_output.get("step_count"),
            "checkpoint_count": dry_run_output.get("checkpoint_count"),
            "evidence_summary": dry_run_output.get("evidence_summary"),
            "final_report_present": dry_run_output.get("final_report_present"),
            "context_pack_summary": dry_run_output.get("context_pack_summary"),
        },
        "deterministic": True,
        "model_free": True,
        "repository_scan_free": True,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAriadneE2EDemoFlow:
    """Deterministic E2E demo flow tests."""

    def test_demo_output_shape(self):
        result = run_ariadne_e2e_demo()
        assert result["demo_name"] == "Ariadne E2E Substrate Demo"
        assert result["pr_id"] == DEMO_PR_ID
        assert result["deterministic"] is True
        assert result["model_free"] is True
        assert result["repository_scan_free"] is True

    def test_demo_context_pack_inputs(self):
        result = run_ariadne_e2e_demo()
        inputs = result["context_pack_inputs"]
        assert inputs["pr_id"] == DEMO_PR_ID
        assert len(inputs["source_contracts"]) > 0
        assert len(inputs["relevant_anchors"]) > 0
        assert len(inputs["allowed_paths"]) > 0
        assert len(inputs["forbidden_paths"]) > 0
        assert len(inputs["cache_key_refs"]) > 0
        assert len(inputs["known_risks"]) > 0

    def test_demo_context_pack(self):
        result = run_ariadne_e2e_demo()
        pack = result["context_pack"]
        assert pack["context_pack_id"] == f"cp-{DEMO_PR_ID}-{DEMO_REPO_ID}"
        assert pack["task"] == DEMO_TASK_GOAL
        assert pack["domain"] == DEMO_DOMAIN
        assert len(pack["invariants"]) > 0
        assert len(pack["risks"]) > 0
        assert len(pack["anchors"]) > 0

    def test_demo_conductor_dry_run(self):
        result = run_ariadne_e2e_demo()
        summary = result["conductor_dry_run_summary"]
        assert summary["dry_run"] == "conductor"
        assert summary["run_status"] == "completed"
        assert summary["step_count"] == 2
        assert summary["context_pack_summary"]["present"] is True

    def test_demo_deterministic(self):
        result1 = run_ariadne_e2e_demo()
        result2 = run_ariadne_e2e_demo()
        assert result1 == result2

    def test_demo_json_serializable(self):
        result = run_ariadne_e2e_demo()
        dumped = json.dumps(result, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == result

    def test_demo_inputs_validate(self):
        inputs = build_context_pack_inputs(
            pr_id=DEMO_PR_ID,
            task_goal=DEMO_TASK_GOAL,
        )
        validate_context_pack_inputs(inputs)  # should not raise

    def test_demo_pack_validates(self):
        inputs = build_context_pack_inputs(
            pr_id=DEMO_PR_ID,
            task_goal=DEMO_TASK_GOAL,
        )
        pack = compile_context_pack(
            context_pack_inputs=inputs,
            repo_id=DEMO_REPO_ID,
            purpose_id=DEMO_PURPOSE_ID,
            domain=DEMO_DOMAIN,
            risk_level=DEMO_RISK_LEVEL,
            base_sha=DEMO_BASE_SHA,
            index_version=DEMO_INDEX_VERSION,
        )
        validate_context_pack(pack)  # should not raise
```

### Compatibility

- Existing dry-run tests pass (no changes to test_dry_run.py).
- Existing context-pack input tests pass.
- Existing context compiler tests pass.

### Forbidden pattern guard

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/conductor/tests/test_ariadne_e2e_demo_flow.py docs/ARIADNE_E2E_DEMO_FLOW.md || true
```

Expect zero matches.

## Future Allowed Write Paths

- `services/conductor/tests/test_ariadne_e2e_demo_flow.py`
- `docs/ARIADNE_E2E_DEMO_FLOW.md`

Precommit review may later write only:
- `.project-memory/pr/0059-ariadne-e2e-demo-flow/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0059-ariadne-e2e-demo-flow/PLAN.md` (planner only)
- `.project-memory/pr/0059-ariadne-e2e-demo-flow/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**` except exact allowed ARIADNE_E2E_DEMO_FLOW.md
- `services/core/**`
- `services/runner/**`
- `services/domain_adapters/**`
- `services/conductor/**` except exact allowed test file
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

## Required Tests / Validation

### Focused tests

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_ariadne_e2e_demo_flow.py -v
```

### Compatibility

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_dry_run.py -q
PYTHONPATH=services/conductor/src python -m pytest services/conductor/tests/test_context_pack_inputs.py -q
PYTHONPATH=services/conductor/src python -m pytest services/conductor/tests/test_context_compiler.py -q
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
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/conductor/tests/test_ariadne_e2e_demo_flow.py docs/ARIADNE_E2E_DEMO_FLOW.md || true
```

### Shell placeholder guard

```bash
grep -R -n "\$(" services/conductor/tests/test_ariadne_e2e_demo_flow.py docs/ARIADNE_E2E_DEMO_FLOW.md || true
```

## Post-change Checks

```bash
grep -n "def run_ariadne_e2e_demo\|class TestAriadneE2EDemoFlow" services/conductor/tests/test_ariadne_e2e_demo_flow.py
```

## Expected Changed Files

1. `services/conductor/tests/test_ariadne_e2e_demo_flow.py` — new E2E demo test
2. `docs/ARIADNE_E2E_DEMO_FLOW.md` — new demo documentation

Expected future review artifact:
- `.project-memory/pr/0059-ariadne-e2e-demo-flow/reviews/precommit-review.yml`

## Non-goals

- no UI
- no CLI product loop
- no agent runner
- no GitHub integration
- no repository scanner
- no repository graph computation
- no RAG/vector search
- no cache backend
- no distributed cache
- no model calls
- no provider integration
- no network
- no subprocess
- no Docker
- no dependency changes
- no filesystem writes to project memory
- no schema changes
- no changes to existing files

## Stop Conditions

- about to write `services/core/**` → stop
- about to write `services/runner/**` → stop
- about to write `services/domain_adapters/**` → stop
- about to write `packages/**` → stop
- about to write `agents/**` → stop
- about to write `apps/**` → stop
- about to write `schemas/**` → stop
- about to write project-memory templates → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- about to modify `.project-memory/anchors.yml` → stop
- about to modify `.project-memory/project_contract.yml` → stop
- about to modify existing conductor files (dry_run.py, context_pack_inputs.py, context_compiler.py) → stop
- about to implement repository scanning → stop
- about to implement RAG/vector search → stop
- about to implement cache backend → stop
- about to add dependency/build config → stop
- about to add network/subprocess/model/provider behavior → stop
- old names/examples would be introduced → stop
- shell placeholders would be introduced → stop

## Open Questions

1. **Should the E2E demo be a standalone module or a test with a callable?** **Decision:** Test with a callable (`run_ariadne_e2e_demo()`). The callable is defined in the test module and imported by the test class. This keeps the demo self-contained and testable. A standalone module would require creating a new service file, which is unnecessary.

2. **Should the demo include an invalid-input error test?** **Decision:** Yes, two tests: `test_demo_inputs_validate` (valid inputs pass `validate_context_pack_inputs`) and `test_demo_pack_validates` (valid pack passes `validate_context_pack`). These prove the demo inputs are valid according to the schema contracts. An explicit invalid-input test belongs in the generator/compiler test files, not the E2E demo.

3. **Should the conductor dry-run summary include the full dry-run output or just selected fields?** **Decision:** Selected fields (`dry_run`, `run_id`, `run_status`, `step_count`, `checkpoint_count`, `evidence_summary`, `context_pack_summary`). The full dry-run output is available via `run_conductor_dry_run()` for tests. The demo output keeps a compact summary.

## Decisions Made

### implementation_files

```
services/conductor/tests/test_ariadne_e2e_demo_flow.py
```

### test_files

Same as implementation — the test file is the implementation.

### docs_files

```
docs/ARIADNE_E2E_DEMO_FLOW.md
```

### demo_input_shape

```
Demo uses Ariadne-native terminology:
  pr_id: "demo-0059"
  feature_id: "demo-context-pack-flow"
  task_goal: "Demonstrate deterministic context-pack dry-run flow"
  domain: "demo"
  repo_id: "ariadne"

With: source_contracts, relevant_anchors, allowed/forbidden paths,
cache_key_refs, prior_pr_refs, qa_evidence_refs, known_risks,
manual_checks_required, context_freshness, requested_context_sections,
output_preferences.

No old names/examples.
```

### output_assertions

```
1. Demo output has expected shape (demo_name, pr_id, deterministic flags).
2. Context-pack inputs contain all expected fields.
3. Context pack has expected deterministic id and non-empty mappings.
4. Conductor dry-run summary shows completed run with context pack.
5. Repeated calls produce identical output.
6. Output is JSON-serializable.
7. Valid inputs pass schema validation.
```

### integration_path

```
run_ariadne_e2e_demo() calls:
  build_context_pack_inputs(...)   from context_pack_inputs.py
  compile_context_pack(...)        from context_compiler.py
  run_conductor_dry_run()          from dry_run.py

All pure functions. No I/O, no subprocess, no network, no models.
```

### validation_rules

- Demo output has all expected keys.
- Context pack id is deterministic (f"cp-{pr_id}-{repo_id}").
- Repeated calls produce identical output.
- Output is JSON-serializable.
- Valid inputs pass schema validators.
- No filesystem writes, no subprocess, no network.

### deterministic_policy

- All inputs are explicit constants.
- No current-time, no random ids, no absolute paths, no machine-specific values.
- Stable ordering via generator/compiler normalization.
- No old names/examples, no shell placeholders.

### validation_strategy

```
Focused E2E tests via pytest.
Compatibility tests for dry-run, generator, compiler.
Forbidden pattern grep.
Shell placeholder grep.
compileall + global pytest.
```

---

PLAN written: yes

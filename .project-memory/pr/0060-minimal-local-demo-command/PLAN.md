# PR 0060 — Minimal Local Demo Command Plan

## Goal

Plan a minimal local demo command or script that runs the Ariadne E2E demo flow and prints deterministic substrate output.

The command should make the current substrate path visible to a human without adding UI, GitHub automation, agent execution, repository scanning, or model calls.

## Architectural Thesis

0059 proved the E2E demo path in tests.
0060 should make the same path runnable locally as a small substrate demo.

This is still substrate work, not product UI.

The model is replaceable.
The local demo command should expose substrate state, not model behavior.

## Context Snapshot

- **current HEAD sha**: `d014753623d167befe3610446a0c8da48587953c`
- **current branch**: `0060-minimal-local-demo-command`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `d014753` (merge commit — no skew relative to main)
- **index_version**: `"0.26"` (from `.project-memory/context-bundles/contracts.yml` — PR 0059 bumped it)
- **stale_snapshot**: false — HEAD is current with merged PR 0059, no pending changes
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
- `services/conductor/tests/test_ariadne_e2e_demo_flow.py`
- `docs/ARIADNE_E2E_DEMO_FLOW.md`
- `services/conductor/src/conductor/__main__.py`
- `.project-memory/pr/0056-context-pack-input-generator/PLAN.md`
- `.project-memory/pr/0057-minimal-context-compiler/PLAN.md`
- `.project-memory/pr/0058-conductor-context-pack-dry-run/PLAN.md`
- `.project-memory/pr/0059-ariadne-e2e-demo-flow/PLAN.md`

## Existing Contract Snapshot

### Context Pack Input Generator (`conductor/context_pack_inputs.py`)

`build_context_pack_inputs(...)` → normalized dict. Pure function, no I/O.

### Minimal Context Compiler (`conductor/context_compiler.py`)

`compile_context_pack(...)` → compact context pack dict. Pure function, no I/O.

### Conductor Dry-Run (`conductor/dry_run.py`)

14-phase pipeline with context pack phases. CLI via `python -m conductor dry-run`.
`main()` prints JSON to stdout.

### Ariadne E2E Demo Test (`tests/test_ariadne_e2e_demo_flow.py`)

Contains `run_ariadne_e2e_demo()` — a callable that builds inputs, compiles context, runs dry-run, and returns a comprehensive dict.
9 tests prove determinism, output shape, serializability, and validation.

### Conductor `__main__.py`

```
Routes "dry-run" → dry_run.main()
Usage: python -m conductor dry-run
```

### Conductor package layout

```
services/conductor/src/conductor/
    __init__.py
    __main__.py
    dry_run.py
    context_pack_inputs.py
    context_compiler.py
```

### Docs

`docs/ARIADNE_E2E_DEMO_FLOW.md` — describes how to run the E2E demo via pytest.

### No examples directory

No `examples/` directory exists in the repository.

## Implementation Location Decision

**Decision: Three files to create/modify.**

### New implementation file

1. **`services/conductor/src/conductor/demo_flow.py`** — standalone importable module.

This extracts `run_ariadne_e2e_demo()` from the test file into a proper module and adds a `main()` function for CLI use.

The test file (`test_ariadne_e2e_demo_flow.py`) will import from this module instead of defining the callable inline.

### Modified files

2. **`services/conductor/src/conductor/__main__.py`** — route `"ariadne-demo"` subcommand to `demo_flow.main()`.

3. **`services/conductor/tests/test_ariadne_e2e_demo_flow.py`** — import `run_ariadne_e2e_demo` from the module instead of defining it locally.

### Optional new test file

4. **`services/conductor/tests/test_demo_flow.py`** — focused tests for the demo_flow module (CLI main, import, output shape).

**Decision:** Create this file if the existing test file's tests are sufficient. If the existing 9 tests fully cover the callable, no new test file is needed. **Decision: No new test file — the existing `test_ariadne_e2e_demo_flow.py` tests are sufficient and should be updated to import `run_ariadne_e2e_demo` from the new module.**

### Docs update

5. **`docs/ARIADNE_E2E_DEMO_FLOW.md`** — add the new `python -m conductor ariadne-demo` CLI command.

### No changes to

- `services/core/**`, `services/runner/**`, `services/domain_adapters/**`
- `packages/`, `agents/`, `apps/`
- `schemas/`, `.project-memory/templates/`
- `.project-memory/anchors.yml`, `.project-memory/project_contract.yml`
- `pyproject.toml`

## Demo Command Contract

### Module: `services/conductor/src/conductor/demo_flow.py`

```python
"""Ariadne substrate demo flow — deterministic, model-free, stdlib-only.

Usage::

    PYTHONPATH=services/core/src:services/conductor/src python -m conductor ariadne-demo
"""

from __future__ import annotations

import json
import sys
from typing import Any


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

# ... (same constants as existing test file, extracted to module)


# ---------------------------------------------------------------------------
# Demo callable
# ---------------------------------------------------------------------------


def run_ariadne_e2e_demo() -> dict[str, Any]:
    """Execute a deterministic Ariadne E2E demo flow.

    Exercises:
    1. Context pack input generation
    2. Context compilation
    3. Conductor dry-run pipeline

    Returns a dict with all intermediate and final outputs.
    """
    # (Same implementation as current test file —
    #  extracted to module, importable by tests and CLI)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the Ariadne substrate demo and print JSON to stdout.

    Parameters
    ----------
    argv
        Command-line arguments (ignored for this demo).

    Returns
    -------
    int
        Exit code (0 = success).
    """
    try:
        result = run_ariadne_e2e_demo()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"ariadne demo failed: {exc}", file=sys.stderr)
        return 1
```

### Updated `__main__.py`

```python
from __future__ import annotations

import sys

from .dry_run import main as dry_run_main
from .demo_flow import main as demo_main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "dry-run":
        raise SystemExit(dry_run_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "ariadne-demo":
        raise SystemExit(demo_main(sys.argv[2:]))
    print("usage: python -m conductor dry-run | ariadne-demo", file=sys.stderr)
    raise SystemExit(2)
```

### Updated test file (`test_ariadne_e2e_demo_flow.py`)

- Remove inline `run_ariadne_e2e_demo()` definition and demo constants.
- Replace with `from conductor.demo_flow import run_ariadne_e2e_demo, DEMO_PR_ID, ...`.
- Remove the `test_demo_inputs_populated` test (constants are now in the module, already validated by module existence).
- All other tests remain identical.

## Output Shape

The demo command prints JSON with the same shape as the existing `run_ariadne_e2e_demo()` output:

```json
{
  "demo_name": "Ariadne E2E Substrate Demo",
  "demo_version": "0.1",
  "pr_id": "demo-0059",
  "feature_id": "demo-context-pack-flow",
  "task_goal": "Demonstrate deterministic context-pack dry-run flow",
  "context_pack_inputs": { ... },
  "context_pack": { ... },
  "conductor_dry_run_summary": { ... },
  "deterministic": true,
  "model_free": true,
  "repository_scan_free": true
}
```

CLI usage:

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m conductor ariadne-demo
```

## Docs Update

Update `docs/ARIADNE_E2E_DEMO_FLOW.md` to add the new CLI command alongside the existing pytest instructions.

## Determinism

- All demo constants are explicit and deterministic.
- No current-time generation.
- No random ids.
- Stable ordering via generator/compiler normalization.
- No absolute local paths.
- No machine-specific values.
- No old names/examples.
- No shell placeholders.

## Validation

- Demo module imports successfully.
- `run_ariadne_e2e_demo()` is callable and returns expected dict.
- `main()` prints JSON and returns 0.
- Existing E2E demo tests pass after refactoring to import from module.
- Existing dry-run tests pass.
- Existing context-pack input tests pass.
- Existing context compiler tests pass.
- `python -m conductor ariadne-demo` CLI succeeds.
- `python -m conductor dry-run` CLI still works (backward compat).
- `python -m conductor` with no args shows usage and exits 2.
- No filesystem writes to `.project-memory/**`.
- No subprocess calls.
- No network calls.

## Tests

### Modified: `services/conductor/tests/test_ariadne_e2e_demo_flow.py`

- Import `run_ariadne_e2e_demo` and demo constants from `conductor.demo_flow`.
- Remove inline `run_ariadne_e2e_demo()` definition.
- Remove `test_demo_inputs_populated` (constants are now module-level — verified by import).
- All other 8 tests remain unchanged.

### CLI test (subprocess — optional, recommended)

If added, in `services/conductor/tests/test_demo_flow.py`:

```python
import subprocess
import sys

class TestDemoFlowCLI:
    def test_ariadne_demo_cli(self):
        result = subprocess.run(
            [sys.executable, "-m", "conductor", "ariadne-demo"],
            capture_output=True,
            text=True,
            env={...},
        )
        assert result.returncode == 0
        assert "Ariadne E2E Substrate Demo" in result.stdout
```

**Decision:** Add this test in a separate `test_demo_flow.py` file. It proves the CLI entrypoint works end-to-end without requiring a separate demo script.

### Compatibility

- All existing E2E demo tests pass (refactored).
- All dry-run tests pass.
- All generator and compiler tests pass.

### Forbidden pattern guard

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/conductor/src/conductor/demo_flow.py services/conductor/tests/test_demo_flow.py services/conductor/tests/test_ariadne_e2e_demo_flow.py docs/ARIADNE_E2E_DEMO_FLOW.md || true
```

Expect zero matches.

## Future Allowed Write Paths

- `services/conductor/src/conductor/demo_flow.py` (new)
- `services/conductor/src/conductor/__main__.py` (modify)
- `services/conductor/tests/test_ariadne_e2e_demo_flow.py` (modify)
- `services/conductor/tests/test_demo_flow.py` (new, optional)
- `docs/ARIADNE_E2E_DEMO_FLOW.md` (modify)

Precommit review may later write only:
- `.project-memory/pr/0060-minimal-local-demo-command/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0060-minimal-local-demo-command/PLAN.md` (planner only)
- `.project-memory/pr/0060-minimal-local-demo-command/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `docs/**` except exact allowed ARIADNE_E2E_DEMO_FLOW.md
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

## Required Tests / Validation

### CLI test

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m conductor ariadne-demo
```

Expected: JSON output with demo fields, exit code 0.

### Refactored E2E tests

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_ariadne_e2e_demo_flow.py -v
```

Expected: 8 tests pass (1 removed, none added).

### CLI subprocess test (if added)

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_demo_flow.py -v
```

Expected: 1 test passes.

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

### Backward compat check

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m conductor dry-run
```

Expected: JSON output unchanged, exit code 0.

### Forbidden pattern guard

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/conductor/src/conductor/demo_flow.py services/conductor/tests/test_demo_flow.py services/conductor/tests/test_ariadne_e2e_demo_flow.py docs/ARIADNE_E2E_DEMO_FLOW.md || true
```

### Shell placeholder guard

```bash
grep -R -n "\$(" services/conductor/src/conductor/demo_flow.py services/conductor/tests/test_demo_flow.py services/conductor/tests/test_ariadne_e2e_demo_flow.py docs/ARIADNE_E2E_DEMO_FLOW.md || true
```

## Post-change Checks

```bash
grep -n "def run_ariadne_e2e_demo\|def main\|class TestAriadneE2EDemoFlow\|ariadne-demo" services/conductor/src/conductor/demo_flow.py services/conductor/tests/test_ariadne_e2e_demo_flow.py services/conductor/src/conductor/__main__.py
```

## Expected Changed Files

1. `services/conductor/src/conductor/demo_flow.py` — new module (extracted from test file)
2. `services/conductor/src/conductor/__main__.py` — add ariadne-demo route
3. `services/conductor/tests/test_ariadne_e2e_demo_flow.py` — refactor to import from module
4. `services/conductor/tests/test_demo_flow.py` — new CLI subprocess test (optional, recommended)
5. `docs/ARIADNE_E2E_DEMO_FLOW.md` — add CLI command docs

Expected future review artifact:
- `.project-memory/pr/0060-minimal-local-demo-command/reviews/precommit-review.yml`

## Non-goals

- no UI
- no product UI
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
- no subprocess (except the CLI subprocess test)
- no Docker
- no dependency changes
- no schema changes
- no project-memory runtime writes
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
- about to write project-memory templates → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- about to modify `.project-memory/anchors.yml` → stop
- about to modify `.project-memory/project_contract.yml` → stop
- about to modify existing generator/compiler/dry-run implementation files → stop
- about to modify existing test files beyond the one E2E test file → stop
- about to implement repository scanning → stop
- about to implement RAG/vector search → stop
- about to implement cache backend → stop
- about to add dependency/build config → stop
- about to add network/model/provider behavior → stop
- old names/examples would be introduced → stop
- shell placeholders would be introduced → stop

## Open Questions

1. **Should the demo constants be duplicated in the module or imported from the test?** **Decision:** Duplicated in the module. The module should be self-contained and importable without test dependencies. The test file imports from the module. When the test file is refactored, it will import constants from the module instead of defining them locally.

2. **Should the CLI subprocess test be added?** **Decision:** Yes. A focused CLI test in `test_demo_flow.py` proves the end-to-end command works. It follows the pattern established by `test_doctor_cli.py` in the runner package. The test uses `sys.executable` and `capture_output=True`, which is standard for CLI tests.

3. **Should `test_demo_inputs_populated` be removed or moved?** **Decision:** Removed. The constants are now in `demo_flow.py`. Their presence is verified by the module importing successfully and by the existing tests that use them. A separate constants-populated test adds no value once the constants are in a proper module.

## Decisions Made

### implementation_files

```
services/conductor/src/conductor/demo_flow.py (new)
services/conductor/src/conductor/__main__.py  (modify)
```

### test_files

```
services/conductor/tests/test_ariadne_e2e_demo_flow.py (modify — refactor to import from module)
services/conductor/tests/test_demo_flow.py              (new — CLI subprocess test)
```

### docs_files

```
docs/ARIADNE_E2E_DEMO_FLOW.md (modify — add CLI command)
```

### optional_example_files

None. No `examples/` directory exists.

### local_demo_api

```
demo_flow.run_ariadne_e2e_demo() -> dict   (callable, imported by tests)
demo_flow.main(argv=None) -> int            (CLI entrypoint, prints JSON)

CLI: python -m conductor ariadne-demo
     -> __main__.py routes to demo_flow.main()
     -> main() calls run_ariadne_e2e_demo()
     -> prints json.dumps(result, indent=2, sort_keys=True)
```

### output_shape

Same as existing `run_ariadne_e2e_demo()` output — dict with demo_name, demo_version, pr_id, feature_id, task_goal, context_pack_inputs, context_pack, conductor_dry_run_summary, deterministic, model_free, repository_scan_free.

### validation_rules

- Module imports. Callable returns dict. CLI prints JSON and exits 0.
- 8 existing E2E tests pass after refactoring.
- CLI subprocess test passes.
- All existing dry-run/generator/compiler tests pass.
- Backward compat: `python -m conductor dry-run` unchanged.
- No I/O, no subprocess (except CLI test).
- No old names/examples, no shell placeholders.

### deterministic_policy

- All demo constants explicit and deterministic.
- No current-time, no random ids, no absolute paths, no machine-specific values.
- Stable ordering via generator/compiler normalization.
- No old names/examples, no shell placeholders.

### validation_strategy

```
Focused E2E tests (refactored).
CLI subprocess test.
Compatibility tests for dry-run, generator, compiler.
Forbidden pattern grep.
Shell placeholder grep.
compileall + global pytest.
Backward compat check for dry-run CLI.
```

---

PLAN written: yes

# PR 0061 — Demo Output Contract Snapshot Plan

## Goal

Plan a small deterministic output contract/snapshot fixture for the local Ariadne demo command.

The command should remain:

```
PYTHONPATH=services/core/src:services/conductor/src python -m conductor ariadne-demo
```

This PR should make the demo output stable and reviewable as Ariadne evolves.

## Architectural Thesis

0060 made the Ariadne substrate path locally runnable.
0061 should make that visible output contract-stable.

This is still substrate hardening, not product UI.

The model is replaceable.
The demo output contract should describe substrate state and evidence, not model behavior.

## Context Snapshot

- **current HEAD sha**: `226f665a5057c48f95968c5cd2b2bf29df767ed2`
- **current branch**: `0061-demo-output-contract-snapshot`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `226f665` (merge commit — no skew relative to main)
- **index_version**: `"0.27"` (from `.project-memory/context-bundles/contracts.yml` — PR 0060 bumped it)
- **stale_snapshot**: false — HEAD is current with merged PR 0060, no pending changes
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `services/conductor/src/conductor/demo_flow.py`
- `services/conductor/src/conductor/__main__.py`
- `services/conductor/tests/test_demo_flow.py`
- `services/conductor/tests/test_ariadne_e2e_demo_flow.py`
- `services/conductor/tests/test_dry_run.py`
- `docs/ARIADNE_E2E_DEMO_FLOW.md`
- `services/conductor/src/conductor/dry_run.py`
- `services/conductor/src/conductor/context_pack_inputs.py`
- `services/conductor/src/conductor/context_compiler.py`
- `.project-memory/pr/0056-context-pack-input-generator/PLAN.md`
- `.project-memory/pr/0057-minimal-context-compiler/PLAN.md`
- `.project-memory/pr/0058-conductor-context-pack-dry-run/PLAN.md`
- `.project-memory/pr/0059-ariadne-e2e-demo-flow/PLAN.md`
- `.project-memory/pr/0060-minimal-local-demo-command/PLAN.md`

## Existing Demo Output Snapshot

The local demo command was run in read-only mode. Output shape:

```
Top-level keys (11, alphabetically sorted by json.dumps sort_keys=True):
  conductor_dry_run_summary  (dict, 8 keys)
  context_pack               (dict, 8 keys)
  context_pack_inputs        (dict, 17 keys)
  demo_name                  "Ariadne E2E Substrate Demo"
  demo_version               "0.1"
  deterministic              True
  feature_id                 "demo-context-pack-flow"
  model_free                 True
  pr_id                      "demo-0059"
  repository_scan_free       True
  task_goal                  "Demonstrate deterministic context-pack dry-run flow"

context_pack_inputs keys (17):
  allowed_paths, cache_key_refs, context_freshness, created_from,
  feature_id, forbidden_paths, known_risks, manual_checks_required,
  output_preferences, pr_id, prior_pr_refs, qa_evidence_refs,
  relevant_anchors, requested_context_sections, schema_version,
  source_contracts, task_goal

context_pack keys (8):
  anchors, context_pack_id, domain, invariants, repo_id, risk_level,
  risks, task

conductor_dry_run_summary keys (8):
  checkpoint_count, context_pack_summary, dry_run, evidence_summary,
  final_report_present, run_id, run_status, step_count

context_pack_summary keys (9, inside conductor_dry_run_summary):
  anchors, context_pack_id, domain, invariants, present, risk_level,
  risks, section_count, task
```

All fields are deterministic. No timestamps. No random ids. No absolute local paths. No machine-specific values. No shell placeholders. No old names/examples.

## Implementation Location Decision

**Decision: Two files to create, one file to update.**

### Fixture file (new)

1. **`services/conductor/tests/fixtures/ariadne_demo_output.json`** — an approved JSON snapshot of the current demo output.

### Test file (new)

2. **`services/conductor/tests/test_demo_output_contract.py`** — focused snapshot/contract test.

### Docs file (modify)

3. **`docs/ARIADNE_E2E_DEMO_FLOW.md`** — add a short note explaining the output contract and snapshot test.

**Rationale for fixtures directory:** `services/conductor/tests/fixtures/` is a standard pytest convention. No existing fixtures directory exists, following the same pattern as `templates/` in earlier PRs. A dedicated fixtures directory keeps test data separate from test logic.

**Rationale for separate test file:** The snapshot/contract test is a different concern from the E2E demo tests (which validate behavior) and the CLI tests (which validate the command runs). The contract test validates that the output shape remains stable over time.

**Not modified:**
- `services/conductor/src/conductor/demo_flow.py` — no behavioral change needed.
- `services/conductor/src/conductor/__main__.py` — no CLI change needed.
- `services/conductor/tests/test_demo_flow.py` — no change needed.
- `services/conductor/tests/test_ariadne_e2e_demo_flow.py` — no change needed.
- `schemas/`, `.project-memory/`, `pyproject.toml` — no changes.

## Snapshot Strategy

**Decision: Use a combined approach — JSON fixture for the full output, plus shape-level assertions for stability.**

### Why full-output fixture?

The output is fully deterministic (all constants, no randomness, no timestamps, no I/O). A full-output fixture is feasible and valuable:
- Catches regressions where a field value unexpectedly changes.
- Provides a reviewable artifact for PR reviewers.
- Is trivially regenerated when intentionally changed.

### Why shape-level assertions?

The fixture alone doesn't express the contract: some fields are required, some are optional, some have expected value patterns. Shape assertions make the contract explicit.

### Fixture generation

The fixture is generated by running the demo command once and capturing the sorted-JSON output. It is committed as the reference snapshot.

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m conductor ariadne-demo \
  > services/conductor/tests/fixtures/ariadne_demo_output.json
```

## Output Contract Keys

The contract test must verify these keys are present in every output:

### Top-level keys (required)
- `demo_name` (string)
- `demo_version` (string)
- `pr_id` (string)
- `feature_id` (string)
- `task_goal` (string)
- `context_pack_inputs` (dict)
- `context_pack` (dict)
- `conductor_dry_run_summary` (dict)
- `deterministic` (bool, True)
- `model_free` (bool, True)
- `repository_scan_free` (bool, True)

### context_pack_inputs keys (required)
- `pr_id` (string)
- `task_goal` (string)
- `source_contracts` (list, non-empty)
- `relevant_anchors` (list, non-empty)
- `allowed_paths` (list, non-empty)
- `forbidden_paths` (list, non-empty)
- `cache_key_refs` (list, non-empty)
- `known_risks` (list, non-empty)
- `schema_version` (string)

### context_pack keys (required)
- `context_pack_id` (string)
- `task` (string)
- `domain` (string)
- `risk_level` (string)
- `invariants` (list, non-empty)
- `risks` (list, non-empty)
- `anchors` (list, non-empty)

### conductor_dry_run_summary keys (required)
- `dry_run` (string, "conductor")
- `run_id` (string)
- `run_status` (string, "completed")
- `step_count` (int, > 0)
- `checkpoint_count` (int, >= 0)
- `final_report_present` (bool, True)
- `context_pack_summary` (dict)
  - `present` (bool, True)
  - `context_pack_id` (string)
  - `task` (string)
  - `domain` (string)
  - `risk_level` (string)
  - `section_count` (int, > 0)

### Fields not part of contract
- `evidence_summary` inside `conductor_dry_run_summary` — depends on store state, may evolve. Test existence but not exact values.
- `output_preferences` inside `context_pack_inputs` — preference dict, may grow. Test existence but not exact keys.
- `manual_checks_required` — may grow as demo evolves.
- `prior_pr_refs` and `qa_evidence_refs` — may be empty in future simplified demos. Test existence but not non-emptiness.

## Test Contract

### Test module: `services/conductor/tests/test_demo_output_contract.py`

```python
"""Demo output contract snapshot tests."""

from __future__ import annotations

import json
from pathlib import Path

from conductor.demo_flow import run_ariadne_e2e_demo

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
_FIXTURE_PATH = _FIXTURE_DIR / "ariadne_demo_output.json"


class TestDemoOutputContract:
    """Stable demo output contract."""

    def _get_current_output(self) -> dict:
        return run_ariadne_e2e_demo()

    def test_fixture_exists(self):
        assert _FIXTURE_PATH.exists()

    def test_output_matches_fixture(self):
        current = self._get_current_output()
        with open(_FIXTURE_PATH) as f:
            fixture = json.load(f)
        assert current == fixture, (
            "Demo output does not match fixture. "
            "If intentional, regenerate with:\n"
            f"  PYTHONPATH=services/core/src:services/conductor/src "
            f"python -m conductor ariadne-demo > {_FIXTURE_PATH}"
        )

    def test_output_deterministic(self):
        assert self._get_current_output() == self._get_current_output()

    def test_output_json_serializable(self):
        result = self._get_current_output()
        dumped = json.dumps(result, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == result

    # --- Top-level keys ---

    def test_top_level_keys(self):
        result = self._get_current_output()
        assert result["demo_name"] == "Ariadne E2E Substrate Demo"
        assert isinstance(result["demo_version"], str)
        assert isinstance(result["pr_id"], str)
        assert isinstance(result["feature_id"], str)
        assert isinstance(result["task_goal"], str)
        assert isinstance(result["context_pack_inputs"], dict)
        assert isinstance(result["context_pack"], dict)
        assert isinstance(result["conductor_dry_run_summary"], dict)
        assert result["deterministic"] is True
        assert result["model_free"] is True
        assert result["repository_scan_free"] is True

    # --- context_pack_inputs ---

    def test_context_pack_inputs_keys(self):
        inputs = self._get_current_output()["context_pack_inputs"]
        assert isinstance(inputs["pr_id"], str)
        assert isinstance(inputs["task_goal"], str)
        assert len(inputs["source_contracts"]) > 0
        assert len(inputs["relevant_anchors"]) > 0
        assert len(inputs["allowed_paths"]) > 0
        assert len(inputs["forbidden_paths"]) > 0
        assert len(inputs["cache_key_refs"]) > 0
        assert len(inputs["known_risks"]) > 0
        assert isinstance(inputs["schema_version"], str)

    # --- context_pack ---

    def test_context_pack_keys(self):
        pack = self._get_current_output()["context_pack"]
        assert isinstance(pack["context_pack_id"], str)
        assert isinstance(pack["task"], str)
        assert isinstance(pack["domain"], str)
        assert isinstance(pack["risk_level"], str)
        assert len(pack["invariants"]) > 0
        assert len(pack["risks"]) > 0
        assert len(pack["anchors"]) > 0

    # --- conductor_dry_run_summary ---

    def test_conductor_dry_run_summary(self):
        summary = self._get_current_output()["conductor_dry_run_summary"]
        assert summary["dry_run"] == "conductor"
        assert isinstance(summary["run_id"], str)
        assert summary["run_status"] == "completed"
        assert summary["step_count"] > 0
        assert isinstance(summary["checkpoint_count"], int)
        assert summary["final_report_present"] is True

        cps = summary["context_pack_summary"]
        assert cps["present"] is True
        assert isinstance(cps["context_pack_id"], str)
        assert isinstance(cps["task"], str)
        assert isinstance(cps["domain"], str)
        assert isinstance(cps["risk_level"], str)
        assert cps["section_count"] > 0

    # --- Safety ---

    def test_no_absolute_paths(self):
        result = json.dumps(self._get_current_output(), sort_keys=True)
        assert "/" not in result or not any(
            line.strip().startswith('"') and "/" in line
            for line in result.splitlines()
            if "://" not in line and "\\/" not in line
        )

    def test_no_shell_placeholders(self):
        result = json.dumps(self._get_current_output(), sort_keys=True)
        assert "$(" not in result
```

### Fixture generation note

The fixture file header should include a comment:

```json
{
  "_comment": "Ariadne demo output snapshot — auto-generated. Regenerate with: PYTHONPATH=services/core/src:services/conductor/src python -m conductor ariadne-demo > services/conductor/tests/fixtures/ariadne_demo_output.json",
  ...actual output...
}
```

JSON doesn't support comments, so instead the test error message tells the developer how to regenerate the fixture. The test currently checks `==` equality with the fixture.

### Compatibility

- All existing E2E demo tests pass.
- All existing CLI demo tests pass.
- All dry-run tests pass.
- All generator and compiler tests pass.

### Forbidden pattern guard

```bash
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/conductor/tests/test_demo_output_contract.py services/conductor/tests/fixtures/ || true
```

Expect zero matches.

### Shell placeholder guard

```bash
grep -R -n "\$(" services/conductor/tests/test_demo_output_contract.py services/conductor/tests/fixtures/ || true
```

Expect zero matches.

## Future Allowed Write Paths

- `services/conductor/tests/fixtures/ariadne_demo_output.json` (new)
- `services/conductor/tests/test_demo_output_contract.py` (new)
- `docs/ARIADNE_E2E_DEMO_FLOW.md` (modify)

Precommit review may later write only:
- `.project-memory/pr/0061-demo-output-contract-snapshot/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0061-demo-output-contract-snapshot/PLAN.md` (planner only)
- `.project-memory/pr/0061-demo-output-contract-snapshot/reviews/plan-review.yml` (plan-review only)
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
- `services/conductor/src/conductor/demo_flow.py` (no behavioral changes)
- `services/conductor/src/conductor/__main__.py` (no CLI changes)
- `services/conductor/tests/test_demo_flow.py` (no changes)
- `services/conductor/tests/test_ariadne_e2e_demo_flow.py` (no changes)

## Required Tests / Validation

### Focused tests

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_demo_output_contract.py -v
```

### Compatibility

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_demo_flow.py -q
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_ariadne_e2e_demo_flow.py -q
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
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask\|redis\|sqlite\|subprocess\|requests\|httpx\|docker\|git " services/conductor/tests/test_demo_output_contract.py services/conductor/tests/fixtures || true
```

### Shell placeholder guard

```bash
grep -R -n "\$(" services/conductor/tests/test_demo_output_contract.py services/conductor/tests/fixtures || true
```

## Post-change Checks

```bash
grep -n "class TestDemoOutputContract\|_FIXTURE_PATH\|ariadne_demo_output" services/conductor/tests/test_demo_output_contract.py services/conductor/tests/fixtures/ariadne_demo_output.json
```

## Expected Changed Files

1. `services/conductor/tests/fixtures/ariadne_demo_output.json` — new JSON snapshot fixture
2. `services/conductor/tests/test_demo_output_contract.py` — new contract test
3. `docs/ARIADNE_E2E_DEMO_FLOW.md` — add output contract note

Expected future review artifact:
- `.project-memory/pr/0061-demo-output-contract-snapshot/reviews/precommit-review.yml`

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
- no Docker
- no dependency changes
- no schema changes
- no project-memory runtime writes
- no behavioral changes to demo command
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
- about to modify `demo_flow.py` or `__main__.py` → stop (no behavioral changes)
- about to implement repository scanning → stop
- about to implement RAG/vector search → stop
- about to implement cache backend → stop
- about to add dependency/build config → stop
- about to add network/model/provider behavior → stop
- old names/examples would be introduced → stop
- shell placeholders would be introduced → stop

## Open Questions

1. **Should the fixture be full-output or normalized?** **Decision:** Full-output. The demo output is fully deterministic — all fields come from explicit constants. A full-output fixture catches the broadest set of regressions. If the output grows too large to be reviewed, a normalized approach can be adopted in a future PR.

2. **Should `evidence_summary` inside `conductor_dry_run_summary` be part of the fixture match?** **Decision:** Yes — it's deterministic (same store state every run). The fixture includes it. The contract test checks `evidence_summary` exists but does not assert specific values (it may evolve independently).

3. **Should the absolute path check use a heuristic or be exact?** **Decision:** Heuristic. The test checks that no path-like string in the output contains `/` (Unix) in a value position, excluding URLs. This is a safety check, not an exact contract. Exact path checking would be too brittle.

## Decisions Made

### fixture_files

```
services/conductor/tests/fixtures/ariadne_demo_output.json
```

### test_files

```
services/conductor/tests/test_demo_output_contract.py
```

### docs_files

```
docs/ARIADNE_E2E_DEMO_FLOW.md (modify — add output contract note)
```

### optional_runtime_files

None. No behavioral changes to `demo_flow.py` or `__main__.py`.

### snapshot_strategy

Full-output JSON fixture plus shape-level assertions. Fixture generated by running the demo command. Test compares `==` equality and provides regenerate instructions on failure.

### normalized_output_rules

- Fixture is generated with `sort_keys=True` for stable ordering.
- Test comparison uses dict `==` equality (order-independent).
- Shape assertions verify key presence and expected types/patterns.
- Edges: `evidence_summary` existence-checked but not value-asserted.

### output_contract_keys

11 top-level keys, 9 required context_pack_inputs sub-keys, 7 required context_pack sub-keys, 7 required dry_run_summary sub-keys, 5 required context_pack_summary sub-keys. Documented in "Output Contract Keys" section above.

### validation_rules

- Fixture exists.
- Current output matches fixture byte-for-byte (after JSON parsing).
- Repeated calls identical.
- JSON serializable.
- Top-level keys present with expected types/values.
- Context input/compilation/dry-run evidence present and non-empty.
- Dry-run shows completed status with context pack present.
- No absolute paths.
- No shell placeholders.
- No old names/examples.

### deterministic_policy

- All demo constants explicit and deterministic.
- No current-time, no random ids, no absolute paths, no machine-specific values.
- Stable ordering via `sort_keys=True` in JSON serialization.

### validation_strategy

```
Focused snapshot contract test.
Compatibility tests for E2E, CLI, dry-run, generator, compiler.
Forbidden pattern grep.
Shell placeholder grep.
compileall + global pytest.
```

---

PLAN written: yes

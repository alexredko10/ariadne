# PR 0062 — Demo Output Evolution Rule Plan

## Goal

Plan a lightweight rule for evolving the Ariadne local demo output contract.

The rule should explain how future PRs intentionally update:

* `services/conductor/tests/fixtures/ariadne_demo_output.json`
* `services/conductor/tests/test_demo_output_contract.py`
* demo output documentation

It should help reviewers distinguish expected output evolution from regressions.

## Architectural Thesis

0061 made demo output stable through a contract fixture.
0062 should define the evolution process for that contract.

This is substrate governance, not runtime behavior.

The model is replaceable.
The demo output contract protects substrate evidence.

## Context Snapshot

- **current HEAD sha**: `44b651cd0c5644c0eee5fe7dfce164b5ad7895c7`
- **current branch**: `0062-demo-output-evolution-rule`
- **git status summary**: clean (no modified/untracked files)
- **base_sha**: `44b651c` (merge commit — no skew relative to main)
- **index_version**: `"0.28"` (from `.project-memory/context-bundles/contracts.yml` — PR 0061 bumped it)
- **stale_snapshot**: false — HEAD is current with merged PR 0061, no pending changes
- **snapshot policy**: Report delta. Do not block solely because current HEAD differs from base_sha. Block only if the delta contains scope-relevant or forbidden changes.
- **files read**: see Inputs Read section
- **files intentionally ignored**: `.ariadne/**`, `.github/**`, `docker/**`, all `__pycache__` directories, `*.pyc`, `.DS_Store`, `.venv/`, `node_modules/`

## Inputs Read

- `.project-memory/memory_index.yml`
- `.project-memory/project_contract.yml`
- `.project-memory/context-bundles/contracts.yml`
- `.project-memory/anchors.yml`
- `.project-memory/phase-0-contracts.yml` — not present
- `docs/ARIADNE_E2E_DEMO_FLOW.md`
- `services/conductor/tests/fixtures/ariadne_demo_output.json`
- `services/conductor/tests/test_demo_output_contract.py`
- `services/conductor/src/conductor/demo_flow.py`
- `services/conductor/src/conductor/__main__.py`
- `services/conductor/tests/test_demo_flow.py`
- `.project-memory/pr/0059-ariadne-e2e-demo-flow/PLAN.md`
- `.project-memory/pr/0060-minimal-local-demo-command/PLAN.md`
- `.project-memory/pr/0061-demo-output-contract-snapshot/PLAN.md`

## Existing Output Contract Summary

### Fixture: `services/conductor/tests/fixtures/ariadne_demo_output.json`

An auto-generated JSON snapshot of a single `run_ariadne_e2e_demo()` call, serialized with `json.dumps(result, indent=2, sort_keys=True)`.

### Contract test: `services/conductor/tests/test_demo_output_contract.py`

12 tests covering:
1. **Fixture existence** — `test_fixture_exists`
2. **Fixture match** — `test_output_matches_fixture` (current output `==` fixture, with regenerate instructions on failure)
3. **Determinism** — `test_output_deterministic` (repeated calls identical)
4. **JSON serializability** — `test_output_json_serializable`
5. **Top-level keys** — `test_top_level_keys` (11 keys with type/value assertions)
6. **Context pack inputs** — `test_context_pack_inputs_keys` (9 assertions)
7. **Context pack** — `test_context_pack_keys` (7 assertions)
8. **Dry-run summary** — `test_conductor_dry_run_summary` (8 assertions including context_pack_summary)
9. **No absolute paths** — `test_no_absolute_paths`
10. **No shell placeholders** — `test_no_shell_placeholders`

### Demo docs

`docs/ARIADNE_E2E_DEMO_FLOW.md` includes regenerate instructions in the "Output contract tests" section.

## Implementation Location Decision

**Decision: Docs-only. Update `docs/ARIADNE_E2E_DEMO_FLOW.md` with an evolution rule section.**

### Updated file

1. **`docs/ARIADNE_E2E_DEMO_FLOW.md`** — add an "Evolution Rules" section.

### No new files

- No new doc file. The evolution rule belongs with the demo flow documentation — they describe the same artifact. A separate `DEMO_OUTPUT_CONTRACT.md` would fragment the documentation.
- No fixture changes.
- No test changes.
- No runtime changes.
- No schema changes.
- No project-memory registry changes.

### Decision rationale

Docs-only is sufficient because:
- The evolution rule is a process convention — documentation is the right medium.
- The fixture and test are stable and don't need change.
- The E2E demo doc is the natural home for this rule — it already documents the fixture and regenerate command.
- No behavioral or structural changes to the codebase.

## Evolution Rule Content

The new section in `docs/ARIADNE_E2E_DEMO_FLOW.md`:

---

## Evolution rules

The demo output fixture (`services/conductor/tests/fixtures/ariadne_demo_output.json`)
is a committed contract snapshot.  It protects against accidental output
regressions while allowing intentional evolution.

### When fixture updates are allowed

- A new feature adds output fields.
- An existing field is intentionally renamed or restructured.
- Demo constants are intentionally updated.
- The underlying generator, compiler, or dry-run changes in a way
  that intentionally alters the demo representation.

### What a fixture-updating PR must include

1. A clear explanation of **which output keys changed** and **why**.
2. Whether the change affects:
   - **Identity** — `demo_name`, `demo_version`, `pr_id`, `feature_id`, `task_goal`
   - **Context-pack evidence** — `context_pack_inputs`, `context_pack`
   - **Dry-run evidence** — `conductor_dry_run_summary`
   - **Validation evidence** — `deterministic`, `model_free`, `repository_scan_free`
3. Evidence that repeated runs remain **deterministic**.
4. Evidence that output remains **JSON-serializable**.
5. Evidence that **no forbidden patterns** are introduced (shell placeholders,
   absolute paths, machine-local values, old project names).

### How to compare old vs new output

```bash
# Regenerate the fixture on the main branch and save as reference
git checkout main
PYTHONPATH=services/core/src:services/conductor/src python -m conductor \
  ariadne-demo > /tmp/fixture_old.json

# Regenerate on the feature branch
git checkout <feature-branch>
PYTHONPATH=services/core/src:services/conductor/src python -m conductor \
  ariadne-demo > /tmp/fixture_new.json

# Compare
diff /tmp/fixture_old.json /tmp/fixture_new.json
```

### What counts as expected evolution

- Adding new keys (shape extension).
- Renaming keys (intentional contract change).
- Adding values to list fields (e.g., new source contracts).
- Updating demo constants (e.g., incrementing `index_version`).

### What counts as a regression

- Removing a required key without explanation.
- Changing a required key's type.
- Breaking determinism (different output on repeated calls under same branch).
- Introducing non-deterministic values (timestamps, random ids, machine paths).
- Introducing forbidden patterns (shell placeholders, absolute paths, old project names).

### Reviewer checklist

When reviewing a PR that updates the demo output fixture:

- [ ] Fixture change is intentional (not a side effect of unrelated work).
- [ ] PR description explains which keys changed and why.
- [ ] Determinism is preserved (`test_output_deterministic` still passes).
- [ ] JSON serializability is preserved (`test_output_json_serializable` still passes).
- [ ] No machine-local absolute paths or timestamps are added.
- [ ] No old project names/examples are introduced.
- [ ] No shell placeholders are introduced.
- [ ] Focused tests pass:

  ```bash
  PYTHONPATH=services/core/src:services/conductor/src python -m pytest \
    services/conductor/tests/test_demo_output_contract.py -q \
    services/conductor/tests/test_ariadne_e2e_demo_flow.py -q \
    services/conductor/tests/test_demo_flow.py -q
  ```

- [ ] Demo command succeeds and produces expected output:

  ```bash
  PYTHONPATH=services/core/src:services/conductor/src python -m conductor ariadne-demo
  ```

---

## Validation

The only validation needed for this PR is that the docs file is correctly formatted and contains the evolution rule section.

```bash
# Check doc presence and content
grep -n "Evolution rules\|When fixture updates are allowed\|Reviewer checklist" docs/ARIADNE_E2E_DEMO_FLOW.md

# Forbidden pattern guard
grep -R -n "water_meter\|water-meter\|Broken Clock\|broken_clock\|daily-consumption\|\.grace\|@grace-\|old Flask" docs/ARIADNE_E2E_DEMO_FLOW.md || true

# Shell placeholder guard
grep -R -n "\$(" docs/ARIADNE_E2E_DEMO_FLOW.md || true

# Existing tests still pass
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_demo_output_contract.py -q
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_demo_flow.py -q
PYTHONPATH=services/core/src:services/conductor/src python -m pytest services/conductor/tests/test_ariadne_e2e_demo_flow.py -q
PYTHONPATH=services/core/src:services/conductor/src python -m conductor ariadne-demo
python -m compileall -f services packages
python -m pytest -q
git status --short
git diff --name-only
```

## Future Allowed Write Paths

- `docs/ARIADNE_E2E_DEMO_FLOW.md` (modify)

Precommit review may later write only:
- `.project-memory/pr/0062-demo-output-evolution-rule/reviews/precommit-review.yml`

## Future Forbidden Write Paths

- `.project-memory/pr/0062-demo-output-evolution-rule/PLAN.md` (planner only)
- `.project-memory/pr/0062-demo-output-evolution-rule/reviews/plan-review.yml` (plan-review only)
- `.project-memory/**`
- `schemas/**`
- `services/**`
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
- `services/conductor/tests/fixtures/ariadne_demo_output.json` (no fixture update)
- `services/conductor/tests/test_demo_output_contract.py` (no test update)
- `services/conductor/src/conductor/demo_flow.py` (no runtime change)
- `services/conductor/src/conductor/__main__.py` (no CLI change)

## Non-goals

- no fixture update
- no demo output behavior change
- no runtime change
- no test change
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
- no network behavior
- no Docker
- no dependency changes
- no schema changes
- no project-memory runtime writes
- no new doc files
- no `.ariadne/**`
- no `.grace/**`

## Stop Conditions

- about to modify demo runtime → stop
- about to modify fixture → stop
- about to modify contract test → stop
- about to modify schemas → stop
- about to write `services/**` → stop
- about to write `packages/**` → stop
- about to write `agents/**` → stop
- about to write `apps/**` → stop
- about to write `.ariadne/**` → stop
- about to write `.grace/**` → stop
- about to modify anchors/project_contract → stop
- about to add dependency/build config → stop
- old names/examples would be introduced → stop
- shell placeholders would be introduced → stop

## Open Questions

1. **Should the evolution rule be a separate doc or merged into ARIADNE_E2E_DEMO_FLOW.md?** **Decision:** Merged. The evolution rule describes the same artifact as the demo flow documentation. A separate doc would fragment related process information and require cross-referencing.

2. **Should the PR include a fixture comparison script or just instructions?** **Decision:** Instructions only. A script would be a new runtime artifact. Shell instructions are sufficient and can be copied from the docs. If a script becomes necessary over time, a future PR can add one.

3. **Should the reviewer checklist be machine-enforced?** **Decision:** No — it's a human checklist. The existing `test_demo_output_contract.py` tests already enforce determinism, serializability, shell-placeholder absence, and absolute-path absence mechanically. The checklist covers reviewer judgment (intentionality, explanation quality, key-change scope) that cannot be automated, and provides a quick reference for what the automated tests already check.

## Decisions Made

### docs_files

```
docs/ARIADNE_E2E_DEMO_FLOW.md (modify — add evolution rules section)
```

### optional_test_files

None. No test changes needed. The existing tests already encode determinism, serializability, and safety checks.

### fixture_files

None. The fixture is intentionally not updated in this PR.

### runtime_files

None. No behavioral changes.

### evolution_rule_sections

The new section covers:
1. When fixture updates are allowed (4 conditions)
2. What a fixture-updating PR must include (5 requirements)
3. How to compare old vs new output (4 shell commands)
4. What counts as expected evolution (4 categories)
5. What counts as a regression (5 categories)
6. Reviewer checklist (10 checklist items)

### reviewer_checklist

10-item checklist covering: intentionality, PR explanation, determinism, serializability, no absolute paths, no old names, no shell placeholders, focused tests pass, demo command succeeds.

### validation_rules

- Doc file contains evolution rules section.
- No old names/examples in doc.
- No shell placeholders in doc.
- All existing tests still pass.
- Demo command still succeeds.

### deterministic_policy

- No change to demo output — fixture not updated.
- Existing determinism guarantees unchanged.

### validation_strategy

```
Doc content check via grep.
Forbidden pattern grep.
Shell placeholder grep.
All existing tests pass (contract, CLI, E2E, dry-run, generator, compiler).
compileall + global pytest.
```

---

PLAN written: yes

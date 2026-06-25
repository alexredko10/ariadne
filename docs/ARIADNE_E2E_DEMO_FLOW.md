# Ariadne E2E Demo Flow

A deterministic end-to-end substrate demo for Ariadne.

## What it exercises

1. **Context pack input generation** — `build_context_pack_inputs()` from `conductor/context_pack_inputs.py`
2. **Minimal context compilation** — `compile_context_pack()` from `conductor/context_compiler.py`
3. **Conductor dry-run integration** — `run_conductor_dry_run()` from `conductor/dry_run.py`

All three steps are pure functions. No model calls. No repository scanning.
No cache backend. No filesystem writes. No subprocess. No network.

## How to run

### Local demo command

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m conductor ariadne-demo
```

Expected: deterministic JSON output on stdout, exit code 0.

### E2E tests

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m pytest \
  services/conductor/tests/test_ariadne_e2e_demo_flow.py -v
```

Expected: 8 tests pass.

### CLI integration tests

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m pytest \
  services/conductor/tests/test_demo_flow.py -v
```

Expected: 8 tests pass.

### Output contract tests

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m pytest \
  services/conductor/tests/test_demo_output_contract.py -v
```

Expected: 12 tests pass.

This test validates that the demo output matches a committed JSON snapshot
at `services/conductor/tests/fixtures/ariadne_demo_output.json`.  If the
output intentionally changes (e.g. new features add fields), regenerate:

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m conductor ariadne-demo \
  > services/conductor/tests/fixtures/ariadne_demo_output.json
```

## What it proves

- The substrate path works end-to-end: explicit inputs → context-pack inputs
  → context pack → conductor dry-run output.
- Output is deterministic — repeated calls produce identical results.
- Output is JSON-serializable.
- No model calls, no repository scanning, no cache backend, no filesystem
  writes — entirely explicit-input-driven.

## Next step

After this demo, the substrate path is complete enough for broader
automation design.  The conductor dry-run pipeline can be extended to
drive a wider set of substrate steps beyond runtime lifecycle and
context compilation.

## Evolution rules

The demo output fixture (`services/conductor/tests/fixtures/ariadne_demo_output.json`)
is a committed contract snapshot.  It protects against accidental output
regressions while allowing intentional evolution.

### When fixture updates are allowed

- A new feature adds output fields.
- An existing field is intentionally renamed or restructured.
- Demo constants are intentionally updated.
- The underlying generator, compiler, or dry-run changes in a way that
  intentionally alters the demo representation.

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

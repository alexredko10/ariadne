# Ariadne E2E Demo Flow

A deterministic end-to-end substrate demo for Ariadne.

## What it exercises

1. **Context pack input generation** — `build_context_pack_inputs()` from `conductor/context_pack_inputs.py`
2. **Minimal context compilation** — `compile_context_pack()` from `conductor/context_compiler.py`
3. **Conductor dry-run integration** — `run_conductor_dry_run()` from `conductor/dry_run.py`

All three steps are pure functions. No model calls. No repository scanning.
No cache backend. No filesystem writes. No subprocess. No network.

## How to run

```bash
PYTHONPATH=services/core/src:services/conductor/src python -m pytest \
  services/conductor/tests/test_ariadne_e2e_demo_flow.py -v
```

Expected output: 9 tests pass.

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

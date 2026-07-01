# PR 0103 — ariadna CLI Skeleton

## Purpose

Add a minimal local `ariadna` CLI skeleton that bridges the Proof-First Runtime objects (proof refs, gate-ready handoff packets) into a stable command surface, using the existing `__main__.py` entrypoint pattern.

## Roadmap alignment

* roadmap track: post-0100 Proof-First Runtime
* expected PR slot: 0103 — ariadna CLI Skeleton
* why this PR is next: PR 0101 defined admissible proof refs. PR 0102 defined gate-ready handoff packets. PR 0103 adds the local command surface that future proof capture, spec freeze, and finalize commands will extend.
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md (Section 10 — Stream 1: Proof-First Runtime, PR 0103 listed as third PR)
* batching policy check: CLI skeleton + deterministic `validate` command wrappers + focused tests form one coherent executable-first PR. ADR 0011 allows batching related runtime object wrappers into one PR slot.
* anti-committee-mode check: executable Python code and focused pytest tests required; no docs-only, schema-only, or packaging-only output.
* architect sign-off required: no — ROADMAP.md and PR 0102 status are established, post-0100 strategic direction manifest explicitly lists PR 0103 as the next step after 0102.
* architect sign-off reference if required: n/a

## Strategic direction source

* .project-memory/post-0100/strategic-direction/agent-manifest.md — Section 10, Stream 1 Proof-First Runtime, PR 0103 listed as third PR.
* ROADMAP.md — roadmap track confirmed; post-0100 Proof-First Runtime is the active track.
* PR 0102 precommit-review.yml — confirms handoff_packet runtime object is implemented, tested, and merged.

## Required reads

* .project-memory/post-0100/strategic-direction/agent-manifest.md
* ROADMAP.md
* ARIADNE_ARCHITECTURE.md
* .project-memory/project_contract.yml
* .project-memory/context-bundles/contracts.yml
* .project-memory/memory_index.yml
* .project-memory/anchors.yml
* .project-memory/review-artifact.schema.yml
* docs/adr/0011-pr-batching-and-roadmap-discipline.md
* docs/adr/0010-runner-execution-contract-boundary.md
* .project-memory/pr/0101-admissible-proof-ref-runtime-object/PLAN.md
* .project-memory/pr/0101-admissible-proof-ref-runtime-object/reviews/precommit-review.yml
* .project-memory/pr/0102-gate-ready-handoff-packet/PLAN.md
* .project-memory/pr/0102-gate-ready-handoff-packet/reviews/precommit-review.yml
* services/runner/src/runner/proof_ref.py
* services/runner/tests/test_proof_ref.py
* services/runner/src/runner/handoff_packet.py
* services/runner/tests/test_handoff_packet.py
* services/runner/src/runner/__main__.py
* services/runner/tests/test_doctor_cli.py
* services/runner/src/runner/doctor.py
* services/runner/src/runner/runtime_smoke.py
* services/runner/tests/test_runner_smoke.py
* pyproject.toml
* services/task_intake/src/task_intake/app.py
* services/task_intake/src/task_intake/execution_handoff.py

## Architecture context

The existing CLI surface already provides:

| Entrypoint | Implementation | File |
|------------|---------------|------|
| `python -m runner` | `__main__.main()` | `services/runner/src/runner/__main__.py` |
| `python -m runner --version` | `__main__._main()` with `add_version_flag` | `services/runner/src/runner/__main__.py` |
| `python -m runner doctor` | `doctor_main()` in `__main__._main()` | `services/runner/src/runner/doctor.py` |
| `python -m runner check` | `check_main()` (delegates to `doctor_main`) | `services/runner/src/runner/__main__.py` |
| `python -m runner runtime-smoke` | `runtime_smoke_main()` | `services/runner/src/runner/runtime_smoke.py` |

Key finding — the CLI already uses:

* `argparse.ArgumentParser` (stdlib) — no external CLI framework
* `def _main(argv: list[str] | None = None) -> int` — testable entrypoint
* `def main() -> None` — module entrypoint for `__main__` block
* `add_version_flag` utility for `--version`
* Exit codes: 0 success, 1 error

Also found: `doctor.py` has `def doctor_main(argv: list[str] | None = None) -> int` with existing test coverage in `test_doctor_cli.py` (covers `python -m runner doctor`, `--version`, and direct `doctor_main(argv)` calls).

No existing subcommand references `proof_ref` or `handoff_packet`.

## Scope

### Implementation files

* `services/runner/src/runner/__main__.py` — **modified** to add `validate proof` and `validate handoff` subcommands
* `services/runner/src/runner/doctor.py` — **modified** to add a `validate` subcommand group entry that dispatches to proof_ref and handoff_packet validation

### No new files

No new source files are required. The existing `__main__.py` + `doctor.py` structure is sufficient. The PR adds the `validate` subcommand group to the existing `__main__.py` argparse parser, and the validation dispatch logic to `doctor.py`.

### Test files

* `services/runner/tests/test_doctor_cli.py` — **modified** to add tests for validate subcommands

### Not in scope

* ROADMAP.md — not modified
* Schema files — unchanged in this PR
* docs/ — not modified
* `.project-memory/` — only PLAN.md written; no reviews
* pyproject.toml — not modified (no dependency changes, no entrypoint changes needed)
* setup.cfg / setup.py — not present, not needed
* Any file outside the three target files above
* No proof capture implementation
* No spec freeze implementation
* No finalization implementation
* No provider/model integration
* No network calls
* No Docker calls

## Design

### Subcommand structure

```
python -m runner validate proof <path>
  → validates a JSON file containing ProofRef data
  → uses runner.proof_ref.validate_proof_ref()
  → output: JSON with status, admissible verdict, reason_code

python -m runner validate handoff <path>
  → validates a JSON file containing GateReadyHandoffPacket data
  → uses runner.handoff_packet.validate_handoff_packet()
  → output: JSON with status, gate_ready/not_gate_ready verdict, reason_codes
```

### Changes to `__main__.py`

1. Add `validate` subcommand parser group with subparsers for `proof` and `handoff`.
2. `validate proof <path>` — reads file, parses JSON, calls `validate_proof_ref()`, prints JSON result.
3. `validate handoff <path>` — reads file, parses JSON, calls `validate_handoff_packet()`, prints JSON result.
4. Both subcommands accept `--current-product-state-ref` and `--admissible-ref-ids` flags for the handoff subcommand (optional; file may embed all context).
5. No network, no Docker, no LLM, no provider calls.
6. No filesystem mutation (reads only).
7. JSON output uses `json.dumps` with `sort_keys=True, indent=2` for deterministic output.

### Changes to `doctor.py`

1. Add `validate_proof_file(path: str) -> dict` helper that reads, parses, validates, returns result dict.
2. Add `validate_handoff_file(path: str, current_product_state_ref: str | None, admissible_ref_ids: list[str] | None) -> dict` helper.
3. These are thin wrappers — no business logic duplication.
4. Both handle `FileNotFoundError`, `json.JSONDecodeError`, and `ValueError` cleanly with structured error output.

### Stable exit codes

| Condition | Exit code |
|-----------|-----------|
| Success | 0 |
| Invalid command or arguments | 1 |
| File not found | 1 |
| JSON parse error | 1 |
| Validation failed (packet not gate-ready, proof not admissible) | 1 |

### Stable output format

```json
{
  "status": "ok" | "error",
  "command": "validate proof" | "validate handoff",
  "result": { ... },
  "error": null | "error message"
}
```

### Invocation modes

* Direct function: `_main(["validate", "proof", "path.json"])` returns int
* Module: `python -m runner validate proof path.json`
* (No package entrypoint — pyproject.toml unchanged)

### Commands planned

| Command | Behavior |
|---------|----------|
| `validate proof <path>` | Reads file, validates via PR 0101 `validate_proof_ref()`, prints JSON |
| `validate handoff <path>` | Reads file, validates via PR 0102 `validate_handoff_packet()`, prints JSON |
| `--version` (existing) | Prints "Ariadne 0.1.0" (already implemented) |
| `doctor` (existing) | Prints system check info (already implemented) |

### Explicitly deferred commands

| Deferred command | Planned PR |
|-----------------|------------|
| `proof capture` | Future (post-0103) |
| `spec freeze` | Future (post-0103) |
| `finalize` | Future (post-0103) |
| `run` / `execute` | Future (post-0103) |
| `model` / `provider` commands | Future (post-0103) |

### Dependency/packaging decision

No changes to pyproject.toml, setup.cfg, or setup.py. The existing `python -m runner` entrypoint is sufficient for the validate subcommands. No new dependencies are required.

## Validation strategy

### Primary validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_doctor_cli.py -q
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/runner/tests/test_doctor_cli.py \
  services/runner/tests/test_proof_ref.py \
  services/runner/tests/test_handoff_packet.py \
  services/runner/tests/test_readiness_gate.py \
  services/runner/tests/test_execution_smoke.py \
  services/runner/tests/test_execution_substrate_audit.py \
  -q
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json
```

All prerequisite test files are present:
* `services/runner/tests/test_proof_ref.py` — exists (PR 0101)
* `services/runner/tests/test_handoff_packet.py` — exists (PR 0102)
* `services/runner/tests/test_readiness_gate.py` — exists (PR 0100)
* `services/runner/tests/test_execution_smoke.py` — exists (PR 0100)
* `services/runner/tests/test_execution_substrate_audit.py` — exists (PR 0100)

## Required test coverage

### Existing test file to extend

`services/runner/tests/test_doctor_cli.py` — already tests `doctor_main` and `python -m runner doctor`. Extend with:

1. `test_validate_proof_help` — `--help` output for `validate proof` subcommand.
2. `test_validate_proof_valid_file` — valid proof ref JSON file → exit 0, JSON output with admissible=true.
3. `test_validate_proof_invalid_file` — JSON with missing required field → exit 1, JSON error output.
4. `test_validate_proof_file_not_found` — nonexistent path → exit 1, JSON error output.
5. `test_validate_proof_invalid_json` — malformed JSON → exit 1, JSON error output.
6. `test_validate_handoff_help` — `--help` output for `validate handoff` subcommand.
7. `test_validate_handoff_valid_file` — valid handoff packet JSON + admissible refs → exit 0, gate_ready.
8. `test_validate_handoff_invalid_file` — packet missing fields → exit 1, not_gate_ready.
9. `test_validate_handoff_file_not_found` — nonexistent path → exit 1.
10. `test_validate_handoff_invalid_json` — malformed JSON → exit 1.
11. `test_cli_no_subcommand` — `python -m runner` with no args → help output, exit 0.
12. `test_cli_unknown_command` — unknown subcommand → exit 1, deterministic error.
13. `test_cli_no_network_import` — test that CLI does not import network/Docker/LLM modules.
14. `test_cli_no_filesystem_mutation` — mock filesystem or verify no write operations.
15. `test_product_name_ariadne` — output contains "Ariadne".
16. `test_no_forbidden_legacy_names` — source contains no legacy terms.

## Stop conditions

* Block if PR/commit 0102 cannot be established — VERIFIED: handoff_packet.py and test_handoff_packet.py exist; PR 0102 precommit-review.yml verdict is `pass`
* Block if post-0100 strategic direction manifest is missing — VERIFIED: agent-manifest.md exists and read
* Block if PR 0101 proof_ref implementation or precommit evidence is missing — VERIFIED: both exist
* Block if PR 0102 handoff_packet implementation or precommit evidence is missing — VERIFIED: both exist
* Block if implementation would be docs-only, schemas-only, review-artifact-only, frontend-only, or packaging-only — PASS: executable Python + tests planned
* Block if implementation requires external provider integration — PASS: pure Python, no providers
* Block if implementation requires network — PASS: no network
* Block if implementation requires Docker daemon/CLI or Docker SDK — PASS: no Docker
* Block if implementation requires LLM calls — PASS: no LLM
* Block if implementation requires large datasets — PASS: no datasets
* Block if implementation requires hidden chain-of-thought logging — PASS: no CoT logging
* Block if implementation copies third-party code — PASS: original code, stdlib only
* Block if implementation modifies ROADMAP.md — PASS: not modified
* Block if implementation changes schemas before runtime behavior exists — PASS: no schema changes
* Block if implementation changes dependencies or packaging without explicit evidence — PASS: no dependency/packaging changes
* Block if exact implementation/test paths cannot be selected — PASS: selected (existing files modified)
* Block if forbidden legacy names/examples would be introduced — PASS: none introduced

## Boundaries

* This PR does NOT add `console_scripts` or package entrypoint to pyproject.toml — the existing `python -m runner` invocation suffices.
* This PR does NOT implement proof capture, spec freeze, or finalization — those are separate PRs.
* This PR does NOT modify schemas, ROADMAP.md, or any file outside the three target files.
* This PR does NOT add dependencies.
* This PR does NOT create new source files — it modifies existing `__main__.py`, `doctor.py`, and `test_doctor_cli.py`.

## Review artifact readiness rule

The precommit-review.yml for PR 0103 must:
* Record full validation results including all four command strings, exit codes, and short output snippets
* Not claim pass with validation skipped/not_run
* Enforce diff completeness using `git status --short` and `git diff --name-only`
* Enforce evidence completeness: files not in FILES READ = not observed = cannot be claimed
* Enforce claim-to-evidence consistency for all confirmations

## Decisions made

* implementation files: `services/runner/src/runner/__main__.py` (modified), `services/runner/src/runner/doctor.py` (modified)
* test files: `services/runner/tests/test_doctor_cli.py` (modified)
* CLI entrypoint shape: uses existing `_main(argv)` pattern with argparse subcommand group `validate`
* selected invocation mode: `python -m runner validate proof <path>` and `python -m runner validate handoff <path>`
* commands planned: `validate proof`, `validate handoff`; existing `--version`, `doctor`, `check`, `runtime-smoke` preserved
* stable exit codes: 0 success, 1 failure (all error types)
* stable output requirements: JSON with `status`, `command`, `result`, `error` fields; `json.dumps(sort_keys=True, indent=2)`
* dependency/packaging decision: no changes — stdlib only, no pyproject.toml modifications
* explicitly deferred commands: proof capture, spec freeze, finalize, run, model/provider
* validation commands: compileall + focused pytest + regression pytest + task_intake check
* blockers: none — all prerequisite conditions met
* warnings: none
* behavior planned: add `validate proof` and `validate handoff` subcommands to existing `__main__.py`; add thin validation wrappers to `doctor.py`; extend `test_doctor_cli.py` with 16 test cases
* boundaries: no new files, no dependency changes, no packaging changes, no new commands beyond validate

## Context snapshot

* current_head: d5031886df33d070c0d97029d0eec35bfe98b426
* git_status_short: clean (no modified files)
* post_0100_manifest_status: .project-memory/post-0100/strategic-direction/agent-manifest.md exists and read
* pr_0101_status_evidence: services/runner/src/runner/proof_ref.py exists, services/runner/tests/test_proof_ref.py exists, precommit-review.yml verdict=pass
* pr_0102_status_evidence: services/runner/src/runner/handoff_packet.py exists, services/runner/tests/test_handoff_packet.py exists, precommit-review.yml verdict=pass
* stale_snapshot_policy: clean tree, current HEAD verified, no stale snapshot issues

## Files read

* .project-memory/post-0100/strategic-direction/agent-manifest.md
* ROADMAP.md
* ARIADNE_ARCHITECTURE.md
* .project-memory/project_contract.yml
* .project-memory/context-bundles/contracts.yml
* .project-memory/memory_index.yml
* .project-memory/anchors.yml
* .project-memory/review-artifact.schema.yml
* docs/adr/0011-pr-batching-and-roadmap-discipline.md
* docs/adr/0010-runner-execution-contract-boundary.md
* .project-memory/pr/0101-admissible-proof-ref-runtime-object/PLAN.md
* .project-memory/pr/0101-admissible-proof-ref-runtime-object/reviews/plan-review.yml
* .project-memory/pr/0101-admissible-proof-ref-runtime-object/reviews/precommit-review.yml
* .project-memory/pr/0102-gate-ready-handoff-packet/PLAN.md
* .project-memory/pr/0102-gate-ready-handoff-packet/reviews/precommit-review.yml
* services/runner/src/runner/proof_ref.py
* services/runner/tests/test_proof_ref.py
* services/runner/src/runner/handoff_packet.py
* services/runner/tests/test_handoff_packet.py
* services/runner/src/runner/__main__.py
* services/runner/src/runner/__init__.py
* services/runner/src/runner/doctor.py
* services/runner/src/runner/runtime_smoke.py
* services/runner/tests/test_doctor_cli.py
* services/runner/tests/test_runner_smoke.py
* services/runner/tests/test_readiness_gate.py
* services/runner/src/runner/readiness_gate.py
* services/runner/src/runner/execution_smoke.py
* services/runner/src/runner/execution_substrate_audit.py
* services/runner/src/runner/artifacts.py
* services/runner/src/runner/execution_envelope.py
* services/runner/src/runner/local_harness.py
* services/task_intake/src/task_intake/app.py
* services/task_intake/src/task_intake/execution_handoff.py
* pyproject.toml

## Files written

* .project-memory/pr/0103-ariadna-cli-skeleton/PLAN.md

## Files intentionally ignored

* agents/ — not relevant for planning; agent configs not modified
* docs/ — not modified
* schemas/ — not modified
* setup.cfg / setup.py — not present (checked)
* .git/ — excluded by policy
* .venv/ — excluded by policy
* node_modules/ — not present
* __pycache__/ — excluded by policy

## Boundary confirmations

* confirm: only PLAN.md written
* confirm: no code written
* confirm: no tests written
* confirm: no review artifact written
* confirm: ROADMAP.md not modified
* confirm: post-0100 strategic direction manifest read
* confirm: PR/commit 0102 status checked and established
* confirm: PR 0101 proof_ref evidence read (source + tests + precommit-review)
* confirm: PR 0102 handoff_packet evidence read (source + tests + precommit-review)
* confirm: Roadmap Alignment Gate applied — roadmap track, PR slot, and strategic direction match
* confirm: PR is executable-first — Python implementation + pytest tests planned
* confirm: PR is not docs-only — implementation file + test file required
* confirm: PR is not schemas-only — no schema changes planned
* confirm: PR is not packaging-only — no pyproject.toml/setup.cfg/setup.py changes planned
* confirm: PR is not frontend-only — pure backend CLI
* confirm: CLI skeleton planned — `validate proof` and `validate handoff` subcommands added to existing CLI
* confirm: deterministic local behavior planned — JSON output with sort_keys
* confirm: focused tests planned (16 test cases)
* confirm: proof capture deferred — explicitly excluded
* confirm: spec freeze deferred — explicitly excluded
* confirm: finalization deferred — explicitly excluded
* confirm: no provider integration planned
* confirm: no network planned
* confirm: no Docker daemon/CLI planned
* confirm: no Docker SDK planned
* confirm: no LLM calls planned
* confirm: no large datasets planned
* confirm: no dependency changes planned — justified by existing stdlib-only argparse pattern
* confirm: no third-party code copying planned
* confirm: product name remains Ariadne
* confirm: forbidden legacy names/examples excluded
* confirm: evidence completeness rule preserved
* confirm: claim-to-evidence consistency rule preserved
* confirm: no git mutation commands run
* confirm: no Docker commands run

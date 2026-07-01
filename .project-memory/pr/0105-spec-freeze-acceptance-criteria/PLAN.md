# PR 0105 — Spec Freeze / Acceptance Criteria Runtime Object

## Purpose

Add a deterministic acceptance criteria freeze runtime object for Ariadne: a function and CLI command that takes a set of acceptance criteria, writes a bounded frozen artifact, and returns an `acceptance_criteria_ref`-compatible result. This gives captured proofs (PR 0104) stable criteria references instead of mutable prompt text.

## Roadmap alignment

* roadmap track: post-0100 Proof-First Runtime
* expected PR slot: 0105 — Spec Freeze / Acceptance Criteria Runtime Object
* why this PR is next: PR 0101 defined proof ref validation, PR 0102 defined gate-ready handoff packets, PR 0103 added the CLI skeleton, PR 0104 added proof capture. PR 0105 provides the stable acceptance criteria reference that all of these depend on — without it, `acceptance_criteria_ref` is a string placeholder with no freeze backing.
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md (Section 10 — Stream 1: Proof-First Runtime, PR 0105 listed as fifth PR)
* batching policy check: acceptance criteria freeze runtime object + deterministic validation + CLI integration + focused tests form one coherent executable-first PR. ADR 0011 allows batching related runtime operations and their CLI wrappers into one PR slot.
* anti-committee-mode check: executable Python code and focused pytest tests required; no docs-only, schema-only, or packaging-only output.
* architect sign-off required: no — ROADMAP.md and PR 0104 status are established, post-0100 strategic direction manifest explicitly lists PR 0105 as the next step after 0104.
* architect sign-off reference if required: n/a

## Strategic direction source

* .project-memory/post-0100/strategic-direction/agent-manifest.md — Section 10, Stream 1 Proof-First Runtime, PR 0105 listed as fifth PR.
* ROADMAP.md — roadmap track confirmed; post-0100 Proof-First Runtime is the active track.
* PR 0104 precommit-review.yml — confirms proof_capture is implemented, tested, and merged.

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
* .project-memory/pr/0103-ariadna-cli-skeleton/PLAN.md
* .project-memory/pr/0103-ariadna-cli-skeleton/reviews/precommit-review.yml
* .project-memory/pr/0104-proof-capture-command/PLAN.md
* .project-memory/pr/0104-proof-capture-command/reviews/precommit-review.yml
* services/runner/src/runner/proof_ref.py
* services/runner/tests/test_proof_ref.py
* services/runner/src/runner/handoff_packet.py
* services/runner/tests/test_handoff_packet.py
* services/runner/src/runner/proof_capture.py
* services/runner/tests/test_proof_capture.py
* services/runner/src/runner/doctor.py
* services/runner/src/runner/__main__.py
* services/runner/tests/test_doctor_cli.py
* services/runner/src/runner/readiness_gate.py
* services/runner/tests/test_readiness_gate.py
* services/runner/src/runner/execution_smoke.py
* services/runner/src/runner/execution_substrate_audit.py
* services/task_intake/src/task_intake/app.py
* services/task_intake/src/task_intake/execution_handoff.py

## Architecture context

The existing proof lifecycle has these components:

| Component | File | PR | Role |
|-----------|------|----|------|
| `ProofRef` + `validate_proof_ref()` | `proof_ref.py` | 0101 | Validates proof refs (checks `acceptance_criteria_ref` as a field — no freeze backing) |
| `GateReadyHandoffPacket` + `validate_handoff_packet()` | `handoff_packet.py` | 0102 | Carries `acceptance_criteria_ref` as a field |
| CLI wrappers (`validate proof`, `validate handoff`) | `doctor.py`, `__main__.py` | 0103 | CLI validation commands |
| `ProofCaptureInput` + `capture_proof()` | `proof_capture.py` | 0104 | Captures proof; `acceptance_criteria_ref` is an input field |

Key observation across all four PRs: `acceptance_criteria_ref` is used as a string field everywhere, but no runtime object *produces* a frozen acceptance criteria reference. PR 0105 fills this gap.

The existing CLI entrypoint pattern (`__main__.py` → `doctor.py` → runtime objects) is stable and verified. PR 0105 will follow the same pattern.

## Scope

### Implementation files

* `services/runner/src/runner/acceptance_criteria.py` — new: `AcceptanceCriterion`, `AcceptanceCriteriaFreezeInput`, `AcceptanceCriteriaFreezeResult`, `AcceptanceCriteriaFreezeStatus`, stable reason codes, `freeze_acceptance_criteria()` function
* `services/runner/src/runner/doctor.py` — modified: add `freeze_acceptance_criteria_file()` helper and wire into CLI
* `services/runner/src/runner/__main__.py` — modified: add `freeze criteria <path>` subcommand

### Test files

* `services/runner/tests/test_acceptance_criteria.py` — new: 20+ test cases covering `freeze_acceptance_criteria()` directly
* `services/runner/tests/test_doctor_cli.py` — modified: add CLI-level tests for `freeze criteria <path>`

### Not in scope

* ROADMAP.md — not modified
* Schema files — unchanged in this PR
* docs/ — not modified
* `.project-memory/` — only PLAN.md written; no reviews
* pyproject.toml — not modified
* Any file outside the five target files above
* No proof evaluation implementation
* No finalization implementation
* No benchmark runner
* No model switching
* No provider/model integration
* No network calls
* No Docker calls
* No LLM calls

## Design

### AcceptanceCriterion (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class AcceptanceCriterion:
    """A single frozen acceptance criterion."""
    criterion_id: str      # Stable identifier, e.g. "AC-001"
    description: str       # Human-readable criterion text
```

Constraints:
* `criterion_id`: non-empty, max 64 chars, alphanumeric + hyphens only
* `description`: non-empty, max 4096 chars; must not contain hidden reasoning patterns or be URL-only

### AcceptanceCriteriaFreezeInput (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class AcceptanceCriteriaFreezeInput:
    """Input parameters for freezing acceptance criteria."""
    product_state_ref: str
    criteria: tuple[AcceptanceCriterion, ...]   # At least one
    phase_id: str
    run_id: str
    output_path: str                             # Bounded local file path
    title: str = ""                              # Optional title for the criteria set
```

Constraints:
* `product_state_ref`: non-empty, max 256 chars
* `criteria`: 1 to 100 entries; no duplicate `criterion_id`; each passes its own constraints
* `phase_id`: non-empty, max 128 chars
* `run_id`: non-empty, max 128 chars
* `output_path`: non-empty, max 255 chars, no `..`, no leading `/`
* `title`: max 256 chars

### AcceptanceCriteriaFreezeStatus (enum)

```python
class AcceptanceCriteriaFreezeStatus(str, enum.Enum):
    FROZEN = "frozen"
    REJECTED = "rejected"
```

### AcceptanceCriteriaFreezeResult (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class AcceptanceCriteriaFreezeResult:
    status: AcceptanceCriteriaFreezeStatus
    reason_codes: tuple[str, ...]           # empty if frozen
    artifact_path: str | None = None        # set only when frozen
    acceptance_criteria_ref: str | None = None  # deterministic ref; set only when frozen
    criteria_count: int | None = None       # set only when frozen
    criterion_ids: tuple[str, ...] | None = None  # sorted; set only when frozen
    details: str | None = None
```

### Stable rejection reason codes

| Constant | Value |
|----------|-------|
| `REASON_MISSING_PRODUCT_STATE_REF` | `"missing_product_state_ref"` |
| `REASON_MISSING_CRITERIA` | `"missing_criteria"` |
| `REASON_MISSING_CRITERION_ID` | `"missing_criterion_id"` |
| `REASON_MISSING_CRITERION_TEXT` | `"missing_criterion_text"` |
| `REASON_DUPLICATE_CRITERION_ID` | `"duplicate_criterion_id"` |
| `REASON_UNBOUNDED_CRITERION_TEXT` | `"unbounded_criterion_text"` |
| `REASON_OVERSIZED_CRITERIA_SET` | `"oversized_criteria_set"` |
| `REASON_MISSING_OUTPUT_PATH` | `"missing_output_path"` |
| `REASON_UNBOUNDED_OUTPUT_PATH` | `"unbounded_output_path"` |
| `REASON_HIDDEN_REASONING_NOT_ALLOWED` | `"hidden_reasoning_not_allowed"` |
| `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED` | `"external_url_only_not_allowed"` |
| `REASON_MUTABLE_CRITERIA_NOT_ALLOWED` | `"mutable_criteria_not_allowed"` |

Note: `REASON_MUTABLE_CRITERIA_NOT_ALLOWED` is reserved for the case where the implementation detects that the criteria input references mutable state (e.g. a file path instead of inline data). In PR 0105 the input is always inline JSON, so this code may not be triggered in initial implementation but is defined for future use.

### `freeze_acceptance_criteria()` function

```python
def freeze_acceptance_criteria(
    input_data: AcceptanceCriteriaFreezeInput,
    output_dir: str = ".",
) -> AcceptanceCriteriaFreezeResult:
```

Deterministic algorithm:
1. Validate `product_state_ref` non-empty.
2. Validate `phase_id` and `run_id` non-empty.
3. Validate `criteria` tuple: non-empty, max 100 entries.
4. For each criterion: validate `criterion_id` and `description` presence, bounds, forbidden patterns.
5. Check for duplicate `criterion_id` values.
6. Validate `output_path` boundedness.
7. Build canonical artifact JSON:
   - Fields: `ariadne_acceptance_criteria_version: "1"`, `product_state_ref`, `title`, `phase_id`, `run_id`, `criteria` (sorted by criterion_id), `frozen_at: null` (deterministic, no wall-clock time).
8. Derive `acceptance_criteria_ref` as the first 16 hex chars of SHA256 of the canonical artifact JSON.
9. Write artifact JSON to `output_dir / output_path` using `json.dumps(sort_keys=True, indent=2)`.
10. Return `FROZEN` with ref, artifact_path, criteria_count, criterion_ids.

### Artifact JSON format (deterministic)

```json
{
    "ariadne_acceptance_criteria_version": "1",
    "product_state_ref": "abc123",
    "title": "PR 0105 acceptance criteria",
    "phase_id": "phase-1",
    "run_id": "run-001",
    "criteria": [
        {"criterion_id": "AC-001", "description": "..."},
        {"criterion_id": "AC-002", "description": "..."}
    ],
    "frozen_at": null
}
```

`frozen_at` is always `null` in PR 0105 — no wall-clock time, fully deterministic.

### Reference derivation

The `acceptance_criteria_ref` is the first 16 hex characters of SHA256(artifact JSON). This means:
- Same criteria → same ref (deterministic)
- Changing any criterion text changes the ref
- Changing criterion order does NOT change the ref (criteria are sorted by criterion_id before hashing)

### Rejected freeze types

| Rejected type | Detection |
|---------------|-----------|
| Empty criteria list | `criteria` empty → `REASON_MISSING_CRITERIA` |
| Criterion without stable id | `criterion_id` empty → `REASON_MISSING_CRITERION_ID` |
| Criterion without text | `description` empty → `REASON_MISSING_CRITERION_TEXT` |
| Duplicate criterion id | Two criteria with same `criterion_id` → `REASON_DUPLICATE_CRITERION_ID` |
| Unbounded criterion text | `description` > 4096 chars → `REASON_UNBOUNDED_CRITERION_TEXT` |
| Oversized criteria set | More than 100 criteria → `REASON_OVERSIZED_CRITERIA_SET` |
| Hidden chain-of-thought | `description` contains forbidden patterns → `REASON_HIDDEN_REASONING_NOT_ALLOWED` |
| External URL-only criteria | `description` is only a URL → `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED` |
| Missing output path | `output_path` empty → `REASON_MISSING_OUTPUT_PATH` |
| Unbounded output path | `..`, leading `/`, or > 255 chars → `REASON_UNBOUNDED_OUTPUT_PATH` |
| Missing product state | `product_state_ref` empty → `REASON_MISSING_PRODUCT_STATE_REF` |
| Missing phase/run identity | `phase_id` or `run_id` empty → `REASON_MISSING_CRITERIA` / `REASON_MISSING_CRITERION_ID` (distinct codes per field type) |

### CLI command shape

```
python -m runner freeze criteria <path>
```

Where `<path>` is a JSON file containing `AcceptanceCriteriaFreezeInput` fields (with `criteria` as a list of dicts). The CLI:
1. Reads the file.
2. Parses JSON: converts `criteria` list to `tuple[AcceptanceCriterion, ...]`.
3. Calls `freeze_acceptance_criteria()`.
4. Prints JSON result with `status`, `command`, `result`, `error`.
5. Exit code: 0 if frozen, 1 if rejected or error.

Implementation: add to `doctor.py` as `freeze_acceptance_criteria_file(path: str, output_dir: str = ".") -> dict` and wire into `__main__.py` under a `freeze` subcommand group.

### Integration with proof capture

After PR 0105, a proof capture workflow can:
1. `python -m runner freeze criteria criteria.json` → produces `acceptance_criteria_ref`
2. Construct proof capture input with that ref
3. `python -m runner capture proof proof_input.json`

The `acceptance_criteria_ref` derived by `freeze_acceptance_criteria()` can be verified by:
1. Freezing the criteria
2. Computing SHA256 of the frozen artifact
3. Checking that the first 16 hex chars match the ref

## Required test coverage

### Unit tests for `freeze_acceptance_criteria()` (in `test_acceptance_criteria.py`)

1. `test_valid_freeze_writes_deterministic_artifact` — valid input writes artifact JSON and returns FROZEN.
2. `test_valid_freeze_returns_acceptance_criteria_ref` — ref is non-empty and starts with hex chars.
3. `test_frozen_artifact_deterministic_key_ordering` — `sort_keys=True` ensures consistent key order.
4. `test_same_input_same_reference` — freezing same input twice produces same `acceptance_criteria_ref`.
5. `test_changing_criterion_text_changes_reference` — different description produces different ref.
6. `test_missing_product_state_ref_fails` — empty product_state_ref → REJECTED.
7. `test_missing_criteria_fails` — empty criteria tuple → REJECTED.
8. `test_missing_criterion_id_fails` — criterion with empty `criterion_id` → REJECTED.
9. `test_missing_criterion_text_fails` — criterion with empty `description` → REJECTED.
10. `test_duplicate_criterion_id_fails` — two criteria with same `criterion_id` → REJECTED.
11. `test_unbounded_criterion_text_fails` — description > 4096 chars → REJECTED.
12. `test_oversized_criteria_set_fails` — more than 100 criteria → REJECTED.
13. `test_hidden_reasoning_not_allowed_fails` — description with `<cot>` → REJECTED.
14. `test_external_url_only_fails` — description is only a URL → REJECTED.
15. `test_missing_output_path_fails` — empty output_path → REJECTED.
16. `test_unbounded_output_path_fails` — output_path with `..` → REJECTED.
17. `test_no_filesystem_write_when_rejected` — rejected freeze does not write any file.
18. `test_oversized_criteria_set_boundary` — 100 criteria passes, 101 fails.
19. `test_criteria_sorted_by_id_in_artifact` — criteria in artifact JSON sorted by criterion_id.
20. `test_artifact_has_no_placeholder_strings` — no non-semantic placeholders in artifact.
21. `test_product_name_ariadne` — source contains "Ariadne".
22. `test_no_forbidden_legacy_names` — source contains no forbidden legacy terms.

### CLI tests (in `test_doctor_cli.py`)

23. `test_freeze_criteria_help` — `--help` output for `freeze criteria` subcommand.
24. `test_freeze_criteria_valid_file` — valid JSON file → exit 0, frozen.
25. `test_freeze_criteria_invalid_file` — JSON with missing fields → exit 1, rejected.
26. `test_freeze_criteria_file_not_found` — nonexistent path → exit 1.
27. `test_freeze_criteria_invalid_json` — malformed JSON → exit 1.
28. `test_freeze_no_network_import` — CLI does not import network/Docker/LLM modules.

### Integration test (in `test_acceptance_criteria.py`)

29. `test_proof_capture_can_consume_ref_shape` — freeze criteria, then construct a `ProofCaptureInput` using the `acceptance_criteria_ref` and verify `capture_proof()` accepts it.

## Validation strategy

### Primary validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_acceptance_criteria.py -q
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_doctor_cli.py -q
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/runner/tests/test_acceptance_criteria.py \
  services/runner/tests/test_proof_capture.py \
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
* `services/runner/tests/test_proof_capture.py` — exists (PR 0104)
* `services/runner/tests/test_doctor_cli.py` — exists (PR 0103, will be modified)
* `services/runner/tests/test_readiness_gate.py` — exists (PR 0100)
* `services/runner/tests/test_execution_smoke.py` — exists (PR 0100)
* `services/runner/tests/test_execution_substrate_audit.py` — exists (PR 0100)

## Stop conditions

* Block if PR/commit 0104 cannot be established — VERIFIED: proof_capture.py, test_proof_capture.py, and precommit-review.yml exist with pass verdict
* Block if PR 0101 proof_ref implementation or precommit evidence is missing — VERIFIED
* Block if PR 0102 handoff_packet implementation or precommit evidence is missing — VERIFIED
* Block if PR 0103 CLI skeleton implementation or precommit evidence is missing — VERIFIED
* Block if PR 0104 proof_capture implementation or precommit evidence is missing — VERIFIED: precommit-review.yml verdict=pass, 198 tests passed
* Block if implementation would be docs-only, schemas-only, review-artifact-only, frontend-only, or packaging-only — PASS
* Block if implementation would execute arbitrary shell commands — PASS: no command execution
* Block if implementation would run user-provided commands — PASS: only JSON input parsing
* Block if implementation requires external provider integration — PASS: pure Python, no providers
* Block if implementation requires network — PASS: no network
* Block if implementation requires Docker daemon/CLI or Docker SDK — PASS: no Docker
* Block if implementation requires LLM calls — PASS: no LLM
* Block if implementation requires large datasets — PASS: no datasets
* Block if implementation requires hidden chain-of-thought logging — PASS: explicitly rejected
* Block if implementation copies third-party code — PASS: original code, stdlib only
* Block if implementation modifies ROADMAP.md — PASS: not modified
* Block if implementation changes schemas before runtime behavior exists — PASS: no schema changes
* Block if implementation changes dependencies or packaging — PASS: no changes
* Block if exact implementation/test paths cannot be selected — PASS: selected
* Block if forbidden legacy names/examples would be introduced — PASS: none introduced
* Block if non-semantic placeholder strings are required — PASS: `frozen_at` uses `null` (None), which is not a non-semantic placeholder string — it has semantic meaning (no wall-clock time injected)

## Boundaries

* This PR does NOT implement proof evaluation — that is a separate PR after spec freeze and proof capture exist.
* This PR does NOT implement finalization — deferred.
* This PR does NOT use wall-clock time in the artifact output (uses `null` / None).
* This PR does NOT introduce non-semantic placeholder strings — `frozen_at: null` is semantically meaningful (indicates deterministic mode without wall-clock time).
* This PR does NOT modify schemas, ROADMAP.md, pyproject.toml, or any file outside the five target files.
* This PR does NOT add dependencies.

## Review artifact readiness rule

The precommit-review.yml for PR 0105 must:
* Record full validation results including all four command strings, exit codes, and short output snippets
* Not claim pass with validation skipped/not_run
* Enforce diff completeness using `git status --short` and `git diff --name-only`
* Enforce evidence completeness: files not in FILES READ = not observed = cannot be claimed
* Enforce claim-to-evidence consistency for all confirmations

## Decisions made

* implementation files: `services/runner/src/runner/acceptance_criteria.py` (new), `services/runner/src/runner/doctor.py` (modified), `services/runner/src/runner/__main__.py` (modified)
* test files: `services/runner/tests/test_acceptance_criteria.py` (new), `services/runner/tests/test_doctor_cli.py` (modified)
* freeze object shape: `AcceptanceCriterion` (frozen, criterion_id + description), `AcceptanceCriteriaFreezeInput` (frozen, product_state_ref + criteria tuple + phase_id + run_id + output_path + optional title)
* freeze result shape: `AcceptanceCriteriaFreezeResult` — frozen dataclass with status, reason_codes, artifact_path, acceptance_criteria_ref (SHA256 prefix), criteria_count, criterion_ids, details
* acceptance_criteria_ref fields: derived from SHA256 of canonical artifact JSON (first 16 hex chars); criteria sorted by criterion_id before hashing
* CLI command shape: `python -m runner freeze criteria <path>` via `freeze_acceptance_criteria_file()` in doctor.py and `freeze` subcommand group in `__main__.py`
* criteria source allowed: explicit JSON criteria payload (inline in input file)
* rejected criteria types: empty list, missing criterion_id, missing description, duplicate ID, unbounded text, oversized set, hidden reasoning, URL-only criteria, missing product state, missing phase/run, bounded output path violations
* stable reason codes: 12 constants as defined above
* artifact format: JSON with `ariadne_acceptance_criteria_version: "1"`, sorted criteria, `frozen_at: null`
* reference derivation: first 16 hex chars of SHA256(canonical artifact JSON)
* output path constraints: no `..`, no leading `/`, max 255 chars
* validation commands: compileall + focused pytest (acceptance_criteria) + focused pytest (test_doctor_cli) + regression pytest (all 8 test files) + task_intake check
* blockers: none — all prerequisite conditions met
* warnings: none
* behavior planned: new `acceptance_criteria.py` with `freeze_acceptance_criteria()` function; extend `doctor.py` with `freeze_acceptance_criteria_file()` helper; extend `__main__.py` with `freeze criteria <path>` subcommand; 29 test cases across two test files including integration with proof capture
* boundaries: no proof evaluation, no finalization, no wall-clock time, no non-semantic placeholders, no network, no Docker, no LLM, no providers, no dependency changes, no schema changes, no ROADMAP.md changes

## Context snapshot

* current_head: 92293191c55292c46c61809b3312905959eb890e
* git_status_short: clean (no modified files)
* post_0100_manifest_status: .project-memory/post-0100/strategic-direction/agent-manifest.md exists and read
* pr_0101_status_evidence: services/runner/src/runner/proof_ref.py exists, tests exist, precommit-review verdict=pass
* pr_0102_status_evidence: services/runner/src/runner/handoff_packet.py exists, tests exist, precommit-review verdict=pass
* pr_0103_status_evidence: services/runner/src/runner/doctor.py, __main__.py, test_doctor_cli.py exist; precommit-review verdict=pass
* pr_0104_status_evidence: services/runner/src/runner/proof_capture.py exists, test_proof_capture.py exists; precommit-review.yml verdict=pass, 198 tests passed
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
* .project-memory/pr/0103-ariadna-cli-skeleton/PLAN.md
* .project-memory/pr/0103-ariadna-cli-skeleton/reviews/plan-review.yml
* .project-memory/pr/0103-ariadna-cli-skeleton/reviews/precommit-review.yml
* .project-memory/pr/0104-proof-capture-command/PLAN.md
* .project-memory/pr/0104-proof-capture-command/reviews/plan-review.yml
* .project-memory/pr/0104-proof-capture-command/reviews/precommit-review.yml
* services/runner/src/runner/proof_ref.py
* services/runner/tests/test_proof_ref.py
* services/runner/src/runner/handoff_packet.py
* services/runner/tests/test_handoff_packet.py
* services/runner/src/runner/proof_capture.py
* services/runner/tests/test_proof_capture.py
* services/runner/src/runner/doctor.py
* services/runner/src/runner/__main__.py
* services/runner/tests/test_doctor_cli.py
* services/runner/src/runner/readiness_gate.py
* services/runner/tests/test_readiness_gate.py
* services/runner/src/runner/execution_smoke.py
* services/runner/src/runner/execution_substrate_audit.py
* services/runner/src/runner/execution_envelope.py
* services/task_intake/src/task_intake/app.py
* services/task_intake/src/task_intake/execution_handoff.py

## Files written

* .project-memory/pr/0105-spec-freeze-acceptance-criteria/PLAN.md

## Files intentionally ignored

* agents/ — not relevant; agent configs not modified
* docs/ — not modified
* schemas/ — not modified
* pyproject.toml — not modified; no dependency changes needed
* setup.cfg / setup.py — not present
* .git/ — excluded by policy
* .venv/ — excluded by policy
* __pycache__/ — excluded by policy

## Boundary confirmations

* confirm: only PLAN.md written
* confirm: no code written
* confirm: no tests written
* confirm: no review artifact written
* confirm: ROADMAP.md not modified
* confirm: post-0100 strategic direction manifest read
* confirm: PR/commit 0104 status checked and established
* confirm: PR 0101 proof_ref evidence read (source + tests + precommit-review)
* confirm: PR 0102 handoff_packet evidence read (source + tests + precommit-review)
* confirm: PR 0103 CLI skeleton evidence read (source + tests + precommit-review)
* confirm: PR 0104 proof_capture evidence read (source + tests + precommit-review)
* confirm: Roadmap Alignment Gate applied — roadmap track, PR slot, and strategic direction match
* confirm: PR is executable-first — Python implementation + pytest tests planned
* confirm: PR is not docs-only — implementation files + test files required
* confirm: PR is not schemas-only — no schema changes planned
* confirm: PR is not packaging-only — no pyproject.toml/setup.cfg/setup.py changes planned
* confirm: PR is not frontend-only — pure backend runtime object + CLI
* confirm: acceptance criteria freeze planned — `freeze criteria <path>` subcommand
* confirm: deterministic local freeze planned — SHA256-derived ref, null timestamp
* confirm: bounded artifact output planned — max 255 char path, max 100 criteria
* confirm: acceptance_criteria_ref-compatible output planned — ref direct from SHA256 of canonical artifact
* confirm: focused tests planned (29 test cases across two test files)
* confirm: arbitrary command execution rejected — no command execution in this PR
* confirm: hidden chain-of-thought logging rejected — `REASON_HIDDEN_REASONING_NOT_ALLOWED`
* confirm: external URL-only criteria rejected — `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED`
* confirm: proof evaluation deferred — explicitly excluded
* confirm: finalization deferred — explicitly excluded
* confirm: benchmark runner deferred — explicitly excluded
* confirm: model switching deferred — explicitly excluded
* confirm: external capability integration deferred — explicitly excluded
* confirm: no provider integration planned
* confirm: no network planned
* confirm: no Docker daemon/CLI planned
* confirm: no Docker SDK planned
* confirm: no LLM calls planned
* confirm: no large datasets planned
* confirm: no dependency changes planned
* confirm: no third-party code copying planned
* confirm: no non-semantic placeholders planned — `frozen_at: null` is semantically meaningful (deterministic mode indicator)
* confirm: product name remains Ariadne
* confirm: forbidden legacy names/examples excluded
* confirm: evidence completeness rule preserved
* confirm: claim-to-evidence consistency rule preserved
* confirm: no git mutation commands run
* confirm: no Docker commands run

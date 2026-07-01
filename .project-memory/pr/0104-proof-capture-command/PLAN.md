# PR 0104 — Proof Capture Command

## Purpose

Add the first runtime proof capture behavior for Ariadne: a deterministic local command and function that writes a bounded captured proof artifact and returns a proof_ref-compatible result. This is the first executable proof-factory in the Proof-First Runtime.

## Roadmap alignment

* roadmap track: post-0100 Proof-First Runtime
* expected PR slot: 0104 — Proof Capture Command
* why this PR is next: PR 0101 defined proof ref validation, PR 0102 defined gate-ready handoff packets, PR 0103 added the CLI skeleton that validates existing proof/handoff objects. PR 0104 adds the first runtime behavior that *creates* a bounded proof artifact — the producer side of the proof-ref lifecycle.
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md (Section 10 — Stream 1: Proof-First Runtime, PR 0104 listed as fourth PR)
* batching policy check: proof capture runtime object + deterministic validation + CLI integration + focused tests form one coherent executable-first PR. ADR 0011 allows batching related runtime operations and their CLI wrappers into one PR slot.
* anti-committee-mode check: executable Python code and focused pytest tests required; no docs-only, schema-only, or packaging-only output.
* architect sign-off required: no — ROADMAP.md and PR 0103 status are established, post-0100 strategic direction manifest explicitly lists PR 0104 as the next step after 0103.
* architect sign-off reference if required: n/a

## Strategic direction source

* .project-memory/post-0100/strategic-direction/agent-manifest.md — Section 10, Stream 1 Proof-First Runtime, PR 0104 listed as fourth PR.
* ROADMAP.md — roadmap track confirmed; post-0100 Proof-First Runtime is the active track.
* PR 0103 precommit-review.yml — confirms CLI skeleton is implemented, tested, and merged with `validate proof` and `validate handoff` subcommands.

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
* services/runner/src/runner/proof_ref.py
* services/runner/tests/test_proof_ref.py
* services/runner/src/runner/handoff_packet.py
* services/runner/tests/test_handoff_packet.py
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

The existing proof lifecycle has two phases completed:

| Phase | Component | File | Status |
|-------|-----------|------|--------|
| Validation | `ProofRef` + `validate_proof_ref()` | `proof_ref.py` | PR 0101 — done |
| Validation | `GateReadyHandoffPacket` + `validate_handoff_packet()` | `handoff_packet.py` | PR 0102 — done |
| CLI wrappers | `validate proof <path>`, `validate handoff <path>` | `doctor.py`, `__main__.py` | PR 0103 — done |

Missing — the producer side: a function that accepts input, validates it, writes a bounded JSON artifact to a local path, and returns a `ProofRef`-compatible result.

The existing CLI entrypoint pattern (`__main__.py` → `doctor.py` → runtime objects) is stable and verified. PR 0104 will follow the same pattern.

## Scope

### Implementation files

* `services/runner/src/runner/proof_capture.py` — new: `ProofCaptureInput`, `ProofCaptureResult`, `ProofCaptureStatus`, stable reason codes, `capture_proof()` function
* `services/runner/src/runner/doctor.py` — modified: add `capture_proof_file()` helper and wire into CLI
* `services/runner/src/runner/__main__.py` — modified: add `capture proof <path>` subcommand

### Test files

* `services/runner/tests/test_proof_capture.py` — new: 20+ test cases covering `capture_proof()` directly
* `services/runner/tests/test_doctor_cli.py` — modified: add CLI-level tests for `capture proof <path>`

### Not in scope

* ROADMAP.md — not modified
* Schema files — unchanged in this PR
* docs/ — not modified
* `.project-memory/` — only PLAN.md written; no reviews
* pyproject.toml — not modified
* Any file outside the five target files above
* No spec freeze implementation
* No finalization implementation
* No benchmark runner
* No model switching
* No provider/model integration
* No network calls
* No Docker calls
* No command execution capture (deferred to future PR)

## Design

### ProofCaptureInput (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class ProofCaptureInput:
    """Input parameters for a deterministic local proof capture."""
    product_state_ref: str
    acceptance_criteria_ref: str
    runtime_capture_kind: str        # e.g. "text", "json"
    phase_id: str
    run_id: str
    payload: str                      # The captured evidence content
    output_path: str                  # Bounded local file path for the artifact
    summary: str = ""                 # Optional human-readable summary
    tags: frozenset[str] = dataclasses.field(default_factory=frozenset)
```

Constraints:
* `product_state_ref`: non-empty, max 256 chars
* `acceptance_criteria_ref`: non-empty, max 256 chars
* `runtime_capture_kind`: non-empty, max 64 chars; must not be `"command_execution"` (deferred)
* `phase_id`: non-empty, max 128 chars
* `run_id`: non-empty, max 128 chars
* `payload`: non-empty, max 65536 chars; must not contain hidden reasoning patterns
* `output_path`: non-empty, max 255 chars, no `..`, no leading `/`; writeable parent directory check
* `summary`: max 1024 chars
* `tags`: max 64 entries; each tag non-empty, max 64 chars

### ProofCaptureStatus (enum)

```python
class ProofCaptureStatus(str, enum.Enum):
    """Final verdict for a proof capture operation."""
    CAPTURED = "captured"
    REJECTED = "rejected"
```

### ProofCaptureResult (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class ProofCaptureResult:
    """Result of a proof capture operation."""
    status: ProofCaptureStatus
    reason_codes: tuple[str, ...]   # empty if captured
    artifact_path: str | None = None  # set only when captured
    proof_ref_fields: dict | None = None  # proof_ref-compatible dict; set only when captured
    details: str | None = None
```

### ProofCaptureResult — fields when captured

When `status == CAPTURED`, `proof_ref_fields` contains:

| Field | Source |
|-------|--------|
| `product_state_ref` | from input |
| `acceptance_criteria_ref` | from input |
| `runtime_capture_ref` | derived: `f"capture-{capture_kind}-{short_hash}"` |
| `artifact_path` | normalized output path (relative to capture root) |
| `phase_id` | from input |
| `run_id` | from input |
| `summary` | from input |
| `tags` | from input |

This dict is directly compatible with `ProofRef(**fields)`, meaning the output of `capture_proof()` can be immediately validated via `validate_proof_ref()` — the PR 0101 pipeline.

### Stable rejection reason codes

| Constant | Value |
|----------|-------|
| `REASON_MISSING_PRODUCT_STATE_REF` | `"missing_product_state_ref"` |
| `REASON_MISSING_ACCEPTANCE_CRITERIA_REF` | `"missing_acceptance_criteria_ref"` |
| `REASON_MISSING_RUNTIME_CAPTURE_KIND` | `"missing_runtime_capture_kind"` |
| `REASON_MISSING_PHASE_IDENTITY` | `"missing_phase_identity"` |
| `REASON_MISSING_RUN_IDENTITY` | `"missing_run_identity"` |
| `REASON_MISSING_OUTPUT_PATH` | `"missing_output_path"` |
| `REASON_UNBOUNDED_OUTPUT_PATH` | `"unbounded_output_path"` |
| `REASON_OVERSIZED_CAPTURE` | `"oversized_capture"` |
| `REASON_HIDDEN_REASONING_NOT_ALLOWED` | `"hidden_reasoning_not_allowed"` |
| `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED` | `"external_url_only_not_allowed"` |
| `REASON_ARBITRARY_COMMAND_EXECUTION_NOT_ALLOWED` | `"arbitrary_command_execution_not_allowed"` |

### `capture_proof()` function

```python
def capture_proof(
    input_data: ProofCaptureInput,
    output_dir: str = ".",
) -> ProofCaptureResult:
```

Deterministic algorithm:
1. Validate all input fields (empty strings, bounds, forbidden patterns).
2. If `runtime_capture_kind == "command_execution"` → reject with `REASON_ARBITRARY_COMMAND_EXECUTION_NOT_ALLOWED`.
3. If payload is only a URL (starts with `http://` or `https://` with no other content) → reject with `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED`.
4. Check `output_path` for boundedness (no `..`, no leading `/`, max 255 chars, parent dir exists).
5. Build the artifact JSON:
   - Contains the `product_state_ref`, `acceptance_criteria_ref`, `runtime_capture_kind`, `phase_id`, `run_id`, `payload`, `summary`, `tags`, `captured_at` (always a fixed placeholder string — no wall-clock time).
6. Write artifact JSON to `output_dir / output_path` using `json.dumps(sort_keys=True, indent=2)`.
7. Derive `runtime_capture_ref` as `f"capture-{runtime_capture_kind}-{short_hash}"` where `short_hash` is the first 12 hex chars of SHA256 of the artifact JSON content.
8. Return `CAPTURED` with `artifact_path`, `proof_ref_fields`, and `reason_codes=()`.

### Artifact JSON format (deterministic)

```json
{
    "ariadne_capture_version": "1",
    "product_state_ref": "...",
    "acceptance_criteria_ref": "...",
    "runtime_capture_kind": "text",
    "phase_id": "...",
    "run_id": "...",
    "payload": "...",
    "summary": "...",
    "tags": [...],
    "captured_at": "PLACEHOLDER"
}
```

`captured_at` is always `"PLACEHOLDER"` in PR 0104. A timestamp injection mechanism (if needed) would be added in a later PR. This keeps the function fully deterministic.

### Rejected capture types

| Rejected type | Detection |
|---------------|-----------|
| Agent claim ("tests pass") without payload | Removed when input has no payload → `REASON_OVERSIZED_CAPTURE` (empty payload) |
| Hidden chain-of-thought | Substring check on payload |
| External URL-only proof | Payload is only a URL → `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED` |
| Arbitrary command execution request | `runtime_capture_kind == "command_execution"` → `REASON_ARBITRARY_COMMAND_EXECUTION_NOT_ALLOWED` |
| Unbounded output path | `..`, leading `/`, or length > 255 → `REASON_UNBOUNDED_OUTPUT_PATH` |
| Oversized payload | Length > 65536 → `REASON_OVERSIZED_CAPTURE` |
| Missing product state / acceptance criteria / phase / run | Empty string checks |

### CLI command shape

```
python -m runner capture proof <path>
```

Where `<path>` is a JSON file containing `ProofCaptureInput` fields. The CLI:
1. Reads the file.
2. Parses JSON into `ProofCaptureInput`.
3. Calls `capture_proof()`.
4. Prints JSON result with `status`, `command`, `result`, `error`.
5. Exit code: 0 if captured, 1 if rejected or error.

Implementation: add to `doctor.py` as `capture_proof_file(path: str, output_dir: str = ".") -> dict` and wire into `__main__.py` under a `capture` subcommand group.

## Required test coverage

### Unit tests for `capture_proof()` (in `test_proof_capture.py`)

1. `test_valid_text_capture` — valid input with text payload writes artifact and returns CAPTURED.
2. `test_valid_json_capture` — valid input with JSON payload writes artifact and returns CAPTURED.
3. `test_captured_proof_ref_compatible` — `proof_ref_fields` can construct a `ProofRef` that passes `validate_proof_ref()`.
4. `test_artifact_json_deterministic` — same input produces identical artifact JSON.
5. `test_runtime_capture_ref_derived` — `runtime_capture_ref` matches `capture-{kind}-{sha256_prefix}` format.
6. `test_missing_product_state_ref` — empty product_state_ref → REJECTED.
7. `test_missing_acceptance_criteria_ref` — empty acceptance_criteria_ref → REJECTED.
8. `test_missing_runtime_capture_kind` — empty runtime_capture_kind → REJECTED.
9. `test_missing_phase_identity` — empty phase_id → REJECTED.
10. `test_missing_run_identity` — empty run_id → REJECTED.
11. `test_missing_output_path` — empty output_path → REJECTED.
12. `test_unbounded_output_path_parent_dotdot` — `output_path` containing `..` → REJECTED.
13. `test_unbounded_output_path_leading_slash` — `output_path` starting with `/` → REJECTED.
14. `test_unbounded_output_path_too_long` — `output_path` > 255 chars → REJECTED.
15. `test_oversized_payload` — payload > 65536 chars → REJECTED.
16. `test_hidden_reasoning_not_allowed` — payload containing hidden reasoning patterns → REJECTED.
17. `test_external_url_only_not_allowed` — payload is only a URL → REJECTED.
18. `test_command_execution_not_allowed` — `runtime_capture_kind == "command_execution"` → REJECTED.
19. `test_no_filesystem_write_when_rejected` — rejected capture does not write any file.
20. `test_output_path_includes_output_dir` — artifact written to `{output_dir}/{output_path}`.
21. `test_product_name_ariadne` — source contains "Ariadne".
22. `test_no_forbidden_legacy_names` — source contains no forbidden legacy terms.

### CLI tests (in `test_doctor_cli.py`)

23. `test_capture_proof_help` — `--help` output for `capture proof` subcommand.
24. `test_capture_proof_valid_file` — valid JSON file → exit 0, captured.
25. `test_capture_proof_invalid_file` — JSON with missing fields → exit 1, rejected.
26. `test_capture_proof_file_not_found` — nonexistent path → exit 1.
27. `test_capture_proof_invalid_json` — malformed JSON → exit 1.
28. `test_capture_no_network_import` — CLI does not import network/Docker/LLM modules.

## Validation strategy

### Primary validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_proof_capture.py -q
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_doctor_cli.py -q
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
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
* `services/runner/tests/test_doctor_cli.py` — exists (PR 0103, will be modified)
* `services/runner/tests/test_readiness_gate.py` — exists (PR 0100)
* `services/runner/tests/test_execution_smoke.py` — exists (PR 0100)
* `services/runner/tests/test_execution_substrate_audit.py` — exists (PR 0100)

## Stop conditions

* Block if PR/commit 0103 cannot be established — VERIFIED: doctor.py, __main__.py, and precommit-review.yml exist with pass verdict
* Block if PR 0101 proof_ref implementation or precommit evidence is missing — VERIFIED
* Block if PR 0102 handoff_packet implementation or precommit evidence is missing — VERIFIED
* Block if PR 0103 CLI skeleton implementation or precommit evidence is missing — VERIFIED: precommit-review.yml verdict=pass, 18 + 163 tests passed
* Block if implementation would be docs-only, schemas-only, review-artifact-only, frontend-only, or packaging-only — PASS
* Block if implementation would execute arbitrary shell commands — PASS: explicitly rejected via `REASON_ARBITRARY_COMMAND_EXECUTION_NOT_ALLOWED`
* Block if implementation would run user-provided commands — PASS: only text/json capture
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

## Boundaries

* This PR does NOT implement command execution capture — explicitly rejected and deferred.
* This PR does NOT implement spec freeze or finalization — those are separate PRs.
* This PR does NOT use wall-clock time in the artifact output (uses `"PLACEHOLDER"` string).
* This PR does NOT modify schemas, ROADMAP.md, pyproject.toml, or any file outside the five target files.
* This PR does NOT add dependencies.

## Review artifact readiness rule

The precommit-review.yml for PR 0104 must:
* Record full validation results including all four command strings, exit codes, and short output snippets
* Not claim pass with validation skipped/not_run
* Enforce diff completeness using `git status --short` and `git diff --name-only`
* Enforce evidence completeness: files not in FILES READ = not observed = cannot be claimed
* Enforce claim-to-evidence consistency for all confirmations

## Decisions made

* implementation files: `services/runner/src/runner/proof_capture.py` (new), `services/runner/src/runner/doctor.py` (modified), `services/runner/src/runner/__main__.py` (modified)
* test files: `services/runner/tests/test_proof_capture.py` (new), `services/runner/tests/test_doctor_cli.py` (modified)
* capture object shape: `ProofCaptureInput` — frozen dataclass with product_state_ref, acceptance_criteria_ref, runtime_capture_kind, phase_id, run_id, payload, output_path, summary (optional), tags (optional frozenset)
* capture result shape: `ProofCaptureResult` — frozen dataclass with status, reason_codes, artifact_path (optional), proof_ref_fields (optional), details (optional)
* proof_ref-compatible fields: product_state_ref, acceptance_criteria_ref, runtime_capture_ref (derived), artifact_path, phase_id, run_id, summary, tags
* CLI command shape: `python -m runner capture proof <path>`; implement via `capture_proof_file()` in doctor.py and `capture` subcommand group in `__main__.py`
* capture source allowed: explicit text/json payload from file (no command execution)
* rejected capture types: agent claim without payload, hidden chain-of-thought, external URL-only, arbitrary command execution, unbounded output path, oversized payload, missing identity fields
* stable reason codes: 11 constants as defined above
* artifact format: JSON with ariadne_capture_version, all input fields, and `captured_at: "PLACEHOLDER"`
* output path constraints: no `..`, no leading `/`, max 255 chars, parent directory must exist
* validation commands: compileall + focused pytest (proof_capture) + focused pytest (test_doctor_cli) + regression pytest + task_intake check
* blockers: none — all prerequisite conditions met
* warnings: none
* behavior planned: new `proof_capture.py` with `capture_proof()` function; extend `doctor.py` with `capture_proof_file()` helper; extend `__main__.py` with `capture proof <path>` subcommand; 28 test cases across two test files
* boundaries: no command execution, no wall-clock time (PLACEHOLDER), no network, no Docker, no LLM, no providers, no dependency changes, no schema changes, no ROADMAP.md changes

## Context snapshot

* current_head: b1e21b4a5266c241d0809d49bff2af32cdb4f1f9
* git_status_short: clean (no modified files)
* post_0100_manifest_status: .project-memory/post-0100/strategic-direction/agent-manifest.md exists and read
* pr_0101_status_evidence: services/runner/src/runner/proof_ref.py exists, services/runner/tests/test_proof_ref.py exists, precommit-review.yml verdict=pass
* pr_0102_status_evidence: services/runner/src/runner/handoff_packet.py exists, services/runner/tests/test_handoff_packet.py exists, precommit-review.yml verdict=pass
* pr_0103_status_evidence: services/runner/src/runner/doctor.py, __main__.py, test_doctor_cli.py exist; precommit-review.yml verdict=pass; 18 + 163 tests passed
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
* services/runner/src/runner/proof_ref.py
* services/runner/tests/test_proof_ref.py
* services/runner/src/runner/handoff_packet.py
* services/runner/tests/test_handoff_packet.py
* services/runner/src/runner/doctor.py
* services/runner/src/runner/__main__.py
* services/runner/tests/test_doctor_cli.py
* services/runner/src/runner/readiness_gate.py
* services/runner/tests/test_readiness_gate.py
* services/runner/src/runner/execution_smoke.py
* services/runner/src/runner/execution_substrate_audit.py
* services/runner/src/runner/artifacts.py
* services/runner/src/runner/execution_envelope.py
* services/task_intake/src/task_intake/app.py
* services/task_intake/src/task_intake/execution_handoff.py

## Files written

* .project-memory/pr/0104-proof-capture-command/PLAN.md

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
* confirm: PR/commit 0103 status checked and established
* confirm: PR 0101 proof_ref evidence read (source + tests + precommit-review)
* confirm: PR 0102 handoff_packet evidence read (source + tests + precommit-review)
* confirm: PR 0103 CLI skeleton evidence read (source + tests + precommit-review)
* confirm: Roadmap Alignment Gate applied — roadmap track, PR slot, and strategic direction match
* confirm: PR is executable-first — Python implementation + pytest tests planned
* confirm: PR is not docs-only — implementation files + test files required
* confirm: PR is not schemas-only — no schema changes planned
* confirm: PR is not packaging-only — no pyproject.toml/setup.cfg/setup.py changes planned
* confirm: PR is not frontend-only — pure backend runtime object + CLI
* confirm: proof capture command planned — `capture proof <path>` subcommand
* confirm: deterministic local capture planned — SHA256-derived capture ref, PLACEHOLDER timestamp
* confirm: proof_ref-compatible output planned — `proof_ref_fields` dict directly compatible with `ProofRef`
* confirm: focused tests planned (28 test cases across two test files)
* confirm: arbitrary command execution rejected — `REASON_ARBITRARY_COMMAND_EXECUTION_NOT_ALLOWED`
* confirm: hidden chain-of-thought logging rejected — `REASON_HIDDEN_REASONING_NOT_ALLOWED`
* confirm: external URL-only proof rejected — `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED`
* confirm: spec freeze deferred — explicitly excluded
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
* confirm: product name remains Ariadne
* confirm: forbidden legacy names/examples excluded
* confirm: evidence completeness rule preserved
* confirm: claim-to-evidence consistency rule preserved
* confirm: no git mutation commands run
* confirm: no Docker commands run

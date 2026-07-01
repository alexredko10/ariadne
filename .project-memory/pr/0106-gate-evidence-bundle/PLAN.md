# PR 0106 — Gate Evidence Bundle Runtime Object

## Purpose

Add a deterministic local Gate Evidence Bundle runtime object for Ariadne: a function and CLI command that takes frozen acceptance criteria artifacts, captured proof artifacts, and a gate-ready handoff packet, and verifies internal consistency across all of them. The bundle does not evaluate criteria or approve gates — it only validates that all references are linked and consistent.

## Roadmap alignment

* roadmap track: post-0100 Proof-First Runtime
* expected PR slot: 0106 — Gate Evidence Bundle Runtime Object
* why this PR is next: PRs 0101–0105 have established proof ref validation, handoff packets, CLI skeleton, proof capture, and acceptance criteria freeze. PR 0106 connects these into a single consistent bundle that can verify cross-artifact integrity — the last piece before the Proof-First Runtime can prove gate readiness.
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md (Section 10 — Stream 1: Proof-First Runtime, PR 0106 listed as sixth PR)
* batching policy check: gate evidence bundle runtime object + CLI integration + focused tests form one coherent executable-first PR. ADR 0011 allows batching related runtime operations and their CLI wrappers into one PR slot.
* anti-committee-mode check: executable Python code and focused pytest tests required; no docs-only, schema-only, or packaging-only output.
* architect sign-off required: no — ROADMAP.md and PR 0105 status are established, post-0100 strategic direction manifest explicitly lists PR 0106 as the next step after 0105.
* architect sign-off reference if required: n/a

## Strategic direction source

* .project-memory/post-0100/strategic-direction/agent-manifest.md — Section 10, Stream 1 Proof-First Runtime, PR 0106 listed as sixth PR.
* ROADMAP.md — roadmap track confirmed; post-0100 Proof-First Runtime is the active track.
* PR 0105 precommit-review.yml — confirms acceptance_criteria freeze is implemented, tested, and merged (30 tests, 233 regression).

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
* .project-memory/pr/0105-spec-freeze-acceptance-criteria/PLAN.md
* .project-memory/pr/0105-spec-freeze-acceptance-criteria/reviews/precommit-review.yml
* services/runner/src/runner/proof_ref.py
* services/runner/tests/test_proof_ref.py
* services/runner/src/runner/handoff_packet.py
* services/runner/tests/test_handoff_packet.py
* services/runner/src/runner/proof_capture.py
* services/runner/tests/test_proof_capture.py
* services/runner/src/runner/acceptance_criteria.py
* services/runner/tests/test_acceptance_criteria.py
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

The existing Proof-First Runtime has five complete components:

| Component | File | PR | Role |
|-----------|------|----|------|
| `ProofRef` + `validate_proof_ref()` | `proof_ref.py` | 0101 | Validates a single proof ref |
| `GateReadyHandoffPacket` + `validate_handoff_packet()` | `handoff_packet.py` | 0102 | Validates handoff readiness |
| CLI wrappers | `doctor.py`, `__main__.py` | 0103 | All subcommands (validate, capture, freeze) |
| `ProofCaptureInput` + `capture_proof()` | `proof_capture.py` | 0104 | Captures proof to artifact file |
| `AcceptanceCriterion` + `freeze_acceptance_criteria()` | `acceptance_criteria.py` | 0105 | Freezes criteria to artifact file |

Each component works independently. None verifies that references across components are internally consistent (e.g., that a handoff packet's `acceptance_criteria_ref` matches a frozen criteria artifact on disk). PR 0106 fills this gap.

## Scope

### Implementation files

* `services/runner/src/runner/gate_evidence.py` — new: `GateEvidenceBundleInput`, `GateEvidenceBundleResult`, `GateEvidenceBundleStatus`, stable reason codes, `build_gate_evidence_bundle()` function
* `services/runner/src/runner/doctor.py` — modified: add `build_gate_evidence_bundle_file()` helper and wire into CLI
* `services/runner/src/runner/__main__.py` — modified: add `bundle evidence <path>` subcommand

### Test files

* `services/runner/tests/test_gate_evidence.py` — new: 25+ test cases covering `build_gate_evidence_bundle()` directly
* `services/runner/tests/test_doctor_cli.py` — modified: add CLI-level tests for `bundle evidence <path>`

### Not in scope

* ROADMAP.md — not modified
* Schema files — unchanged in this PR
* docs/ — not modified
* `.project-memory/` — only PLAN.md written; no reviews
* pyproject.toml — not modified
* Any file outside the five target files above
* No acceptance criteria pass/fail evaluation
* No gate approval or finalization
* No benchmark runner
* No model switching
* No provider/model integration
* No network calls
* No Docker calls

## Design

### GateEvidenceBundleInput (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class GateEvidenceBundleInput:
    """Input parameters for building a gate evidence bundle."""
    product_state_ref: str
    acceptance_criteria_ref: str
    phase_id: str
    run_id: str
    proof_ref_ids: tuple[str, ...]       # Admissible proof ref IDs
    runtime_capture_refs: tuple[str, ...] # Proof capture refs from proof_capture output
    handoff_packet_path: str             # Path to handoff packet JSON file (for field check)
    acceptance_criteria_path: str        # Path to frozen acceptance criteria artifact
    output_path: str                     # Bounded local file path for bundle artifact
    capture_artifact_paths: tuple[str, ...]  # Paths to proof capture artifacts (for ref verification)
    gate_id: str = ""                    # From handoff packet (for consistency check)
    actor_or_role: str = ""              # From handoff packet (for consistency check)
```

Constraints:
* `product_state_ref`: non-empty, max 256 chars
* `acceptance_criteria_ref`: non-empty, max 256 chars
* `phase_id`: non-empty, max 128 chars
* `run_id`: non-empty, max 128 chars
* `proof_ref_ids`: at least one entry; each non-empty, max 256 chars
* `runtime_capture_refs`: may be empty (no captures yet), each max 256 chars
* `handoff_packet_path`: non-empty, max 255 chars, no `..`, no leading `/`
* `acceptance_criteria_path`: non-empty, max 255 chars, no `..`, no leading `/`
* `output_path`: non-empty, max 255 chars, no `..`, no leading `/`
* `capture_artifact_paths`: each max 255 chars, no `..`, no leading `/`
* `gate_id`: max 128 chars
* `actor_or_role`: max 128 chars

### GateEvidenceBundleStatus (enum)

```python
class GateEvidenceBundleStatus(str, enum.Enum):
    BUNDLED = "bundled"
    REJECTED = "rejected"
```

### GateEvidenceBundleResult (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class GateEvidenceBundleResult:
    status: GateEvidenceBundleStatus
    reason_codes: tuple[str, ...]       # empty if bundled
    artifact_path: str | None = None    # set only when bundled
    bundle_ref: str | None = None       # SHA256 of bundle artifact; set only when bundled
    consistency_summary: str | None = None  # human-readable summary; set only when bundled
    details: str | None = None
```

### Stable rejection reason codes

| Constant | Value |
|----------|-------|
| `REASON_MISSING_PRODUCT_STATE_REF` | `"missing_product_state_ref"` |
| `REASON_MISSING_ACCEPTANCE_CRITERIA_REF` | `"missing_acceptance_criteria_ref"` |
| `REASON_MISSING_HANDOFF_PACKET` | `"missing_handoff_packet"` |
| `REASON_MISSING_PROOF_REFS` | `"missing_proof_refs"` |
| `REASON_MISSING_CAPTURE_REFS` | `"missing_capture_refs"` |
| `REASON_MISSING_PHASE_IDENTITY` | `"missing_phase_identity"` |
| `REASON_MISSING_RUN_IDENTITY` | `"missing_run_identity"` |
| `REASON_INCONSISTENT_PRODUCT_STATE_REF` | `"inconsistent_product_state_ref"` |
| `REASON_INCONSISTENT_ACCEPTANCE_CRITERIA_REF` | `"inconsistent_acceptance_criteria_ref"` |
| `REASON_INCONSISTENT_PHASE_IDENTITY` | `"inconsistent_phase_identity"` |
| `REASON_INCONSISTENT_RUN_IDENTITY` | `"inconsistent_run_identity"` |
| `REASON_INADMISSIBLE_PROOF_REF` | `"inadmissible_proof_ref"` |
| `REASON_UNKNOWN_CAPTURE_REF` | `"unknown_capture_ref"` |
| `REASON_UNBOUNDED_BUNDLE_OUTPUT_PATH` | `"unbounded_bundle_output_path"` |
| `REASON_OVERSIZED_BUNDLE` | `"oversized_bundle"` |
| `REASON_HIDDEN_REASONING_NOT_ALLOWED` | `"hidden_reasoning_not_allowed"` |
| `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED` | `"external_url_only_not_allowed"` |

### `build_gate_evidence_bundle()` function

```python
def build_gate_evidence_bundle(
    input_data: GateEvidenceBundleInput,
    output_dir: str = ".",
) -> GateEvidenceBundleResult:
```

Deterministic algorithm:
1. Validate all basic input fields (empty strings, bounds, path safety).
2. Read the handoff packet file. Parse as `GateReadyHandoffPacket`. Check:
   - `product_state_ref` matches `input_data.product_state_ref`
   - `acceptance_criteria_ref` matches `input_data.acceptance_criteria_ref`
   - `phase_id` matches `input_data.phase_id`
   - `run_id` matches `input_data.run_id`
   - `gate_id` is non-empty
   - `proof_ref_ids` are a superset of `input_data.proof_ref_ids`
3. Read the acceptance criteria artifact file. Verify that its SHA256 first-16-hex-chars equals `input_data.acceptance_criteria_ref`.
4. Read each proof capture artifact file at `capture_artifact_paths`. Extract `runtime_capture_ref` from each. Verify that each `runtime_capture_ref` exists in `input_data.runtime_capture_refs`.
5. Verify that each `runtime_capture_ref` in `input_data.runtime_capture_refs` maps to at least one proof capture artifact.
6. Build canonical bundle artifact JSON:
   - Fields: `ariadne_bundle_version: "1"`, `product_state_ref`, `acceptance_criteria_ref`, `phase_id`, `run_id`, `handoff_gate_id`, `proof_ref_ids` (sorted), `runtime_capture_refs` (sorted), `criterion_ids` (from reading acceptance criteria artifact), `bundled_at: null` (deterministic, no wall-clock time).
7. Derive `bundle_ref` as the first 16 hex chars of SHA256 of the canonical bundle JSON.
8. Write artifact JSON to `output_dir / output_path` using `json.dumps(sort_keys=True, indent=2)`.
9. Return `BUNDLED` with ref, artifact_path, consistency_summary.

### Consistency checks in detail

| Check | What it verifies | Reason code if fails |
|-------|------------------|---------------------|
| Handoff packet exists and parses | `handoff_packet_path` readable as `GateReadyHandoffPacket` | `REASON_MISSING_HANDOFF_PACKET` |
| Handoff product_state_ref matches | `packet.product_state_ref == input_data.product_state_ref` | `REASON_INCONSISTENT_PRODUCT_STATE_REF` |
| Handoff acceptance_criteria_ref matches | `packet.acceptance_criteria_ref == input_data.acceptance_criteria_ref` | `REASON_INCONSISTENT_ACCEPTANCE_CRITERIA_REF` |
| Handoff phase_id matches | `packet.phase_id == input_data.phase_id` | `REASON_INCONSISTENT_PHASE_IDENTITY` |
| Handoff run_id matches | `packet.run_id == input_data.run_id` | `REASON_INCONSISTENT_RUN_IDENTITY` |
| Acceptance criteria artifact exists | `acceptance_criteria_path` readable; SHA256 of content matches `acceptance_criteria_ref` | `REASON_INCONSISTENT_ACCEPTANCE_CRITERIA_REF` |
| Capture artifacts exist | Each path in `capture_artifact_paths` is readable | `REASON_UNKNOWN_CAPTURE_REF` |
| Capture artifacts contain expected refs | Each artifact's `runtime_capture_ref` field matches`input_data.runtime_capture_refs` | `REASON_UNKNOWN_CAPTURE_REF` |
| Handoff proof_ref_ids include all input proof_ref_ids | `set(packet.proof_ref_ids) >= set(input_data.proof_ref_ids)` | `REASON_INADMISSIBLE_PROOF_REF` |

### Artifact JSON format (deterministic)

```json
{
    "ariadne_bundle_version": "1",
    "product_state_ref": "abc123",
    "acceptance_criteria_ref": "def456",
    "phase_id": "phase-1",
    "run_id": "run-001",
    "handoff_gate_id": "human_review_gate",
    "proof_ref_ids": ["pr-001", "pr-002"],
    "runtime_capture_refs": ["capture-text-abc123def456"],
    "criterion_ids": ["AC-001", "AC-002"],
    "capture_count": 1,
    "criteria_canonical_ref": "def456",
    "bundled_at": null
}
```

`bundled_at` is always `null` — no wall-clock time, fully deterministic.

### Rejected bundle types

| Rejected type | Detection |
|---------------|-----------|
| Missing product state | Empty `product_state_ref` |
| Missing acceptance criteria ref | Empty `acceptance_criteria_ref` |
| Missing handoff packet | Empty/readable `handoff_packet_path` |
| Missing proof refs | Empty `proof_ref_ids` |
| Missing capture refs | Provided but ref doesn't match any capture artifact |
| Inconsistent product state | Handoff packet has different ref |
| Inconsistent acceptance criteria ref | Handoff packet or criteria artifact has different ref |
| Inconsistent phase identity | Handoff packet has different phase_id |
| Inconsistent run identity | Handoff packet has different run_id |
| Inadmissible proof ref | Handoff packet missing a proof ref from input |
| Unknown capture ref | runtime_capture_ref not found in any capture artifact |
| Hidden chain-of-thought | In any artifact read |
| External URL-only evidence | In any artifact read |
| Unbounded output path | `..`, leading `/`, or > 255 chars |
| Oversized bundle | Bundle artifact > 1MB |

### CLI command shape

```
python -m runner bundle evidence <path>
```

Where `<path>` is a JSON file containing `GateEvidenceBundleInput` fields. The CLI:
1. Reads the file.
2. Parses JSON into `GateEvidenceBundleInput`.
3. Calls `build_gate_evidence_bundle()`.
4. Prints JSON result with `status`, `command`, `result`, `error`.
5. Exit code: 0 if bundled, 1 if rejected or error.

Implementation: add to `doctor.py` as `build_gate_evidence_bundle_file(path: str, output_dir: str = ".") -> dict` and wire into `__main__.py` under a `bundle` subcommand group.

### Bundle not an execution authorization

The gate evidence bundle:
- Does NOT evaluate whether criteria passed or failed
- Does NOT mark a gate as approved
- Does NOT implement finalization
- Does NOT execute any commands
- Does NOT call any external system

It is a pure consistency-verification object. Its purpose is to prove that all artifacts in the gate workflow are internally consistent and reference the same product state, acceptance criteria, phase, and run.

## Required test coverage

### Unit tests for `build_gate_evidence_bundle()` (in `test_gate_evidence.py`)

1. `test_valid_bundle_succeeds` — consistent input with real artifact files → BUNDLED.
2. `test_valid_bundle_deterministic_output_fields` — bundle includes deterministic fields.
3. `test_bundle_artifact_json_deterministic` — same input produces identical JSON.
4. `test_same_input_same_bundle_ref` — same input twice produces same bundle_ref.
5. `test_changed_proof_refs_changes_bundle_ref` — different proof_ref_ids changes ref.
6. `test_missing_product_state_ref` — empty → REJECTED.
7. `test_missing_acceptance_criteria_ref` — empty → REJECTED.
8. `test_missing_handoff_packet` — path to nonexistent file → REJECTED.
9. `test_missing_proof_refs` — empty proof_ref_ids → REJECTED.
10. `test_missing_phase_identity` — empty phase_id → REJECTED.
11. `test_missing_run_identity` — empty run_id → REJECTED.
12. `test_inconsistent_product_state_ref` — handoff packet has different ref → REJECTED.
13. `test_inconsistent_acceptance_criteria_ref` — handoff packet has different ref → REJECTED.
14. `test_inconsistent_phase_identity` — handoff packet has different phase_id → REJECTED.
15. `test_inconsistent_run_identity` — handoff packet has different run_id → REJECTED.
16. `test_inadmissible_proof_ref` — handoff packet missing a proof ref from input → REJECTED.
17. `test_unknown_capture_ref` — runtime_capture_ref not in any capture artifact → REJECTED.
18. `test_unbounded_output_path` — path with `..` → REJECTED.
19. `test_hidden_reasoning_in_capture_artifact` — payload contains `<cot>` → REJECTED.
20. `test_no_filesystem_write_when_rejected` — rejected bundle writes no files.
21. `test_consistency_summary_includes_counts` — bundled result includes summary string with counts.
22. `test_criteria_artifact_sha256_ref_match` — bundle verifies criteria SHA256 against ref.
23. `test_product_name_ariadne` — source contains "Ariadne".
24. `test_no_forbidden_legacy_names` — source contains no forbidden legacy terms.

### CLI tests (in `test_doctor_cli.py`)

25. `test_bundle_evidence_help` — `--help` output for `bundle evidence` subcommand.
26. `test_bundle_evidence_valid_file` — valid JSON input with real artifacts → exit 0, bundled.
27. `test_bundle_evidence_inconsistent_file` — mismatched refs → exit 1, rejected.
28. `test_bundle_evidence_file_not_found` — nonexistent path → exit 1.
29. `test_bundle_evidence_invalid_json` — malformed JSON → exit 1.
30. `test_bundle_no_network_import` — CLI does not import network/Docker/LLM modules.

### Integration test

31. `test_end_to_end_bundle_workflow` — freeze criteria → capture proof → build handoff packet → build bundle → BUNDLED.

## Validation strategy

### Primary validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_gate_evidence.py -q
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_doctor_cli.py -q
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/runner/tests/test_gate_evidence.py \
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
* `services/runner/tests/test_acceptance_criteria.py` — exists (PR 0105)
* `services/runner/tests/test_doctor_cli.py` — exists (PR 0103, will be modified)
* `services/runner/tests/test_readiness_gate.py` — exists (PR 0100)
* `services/runner/tests/test_execution_smoke.py` — exists (PR 0100)
* `services/runner/tests/test_execution_substrate_audit.py` — exists (PR 0100)

## Stop conditions

* Block if PR/commit 0105 cannot be established — VERIFIED: acceptance_criteria.py, test_acceptance_criteria.py, and precommit-review.yml exist with pass verdict (30 tests, 233 regression)
* Block if PR 0101 proof_ref implementation or precommit evidence is missing — VERIFIED
* Block if PR 0102 handoff_packet implementation or precommit evidence is missing — VERIFIED
* Block if PR 0103 CLI skeleton implementation or precommit evidence is missing — VERIFIED
* Block if PR 0104 proof_capture implementation or precommit evidence is missing — VERIFIED
* Block if PR 0105 acceptance_criteria freeze implementation or precommit evidence is missing — VERIFIED
* Block if implementation would be docs-only, schemas-only, review-artifact-only, frontend-only, or packaging-only — PASS
* Block if implementation would execute arbitrary shell commands — PASS: no command execution
* Block if implementation would run user-provided commands — PASS: only JSON file reads
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
* Block if non-semantic placeholder strings are required — PASS: `bundled_at: null` is semantically meaningful
* Block if implementation would evaluate criteria pass/fail or finalize a gate — PASS: explicitly excluded

## Boundaries

* This PR does NOT evaluate acceptance criteria pass/fail — deferred to future PR.
* This PR does NOT approve or finalize a gate — deferred to future PR.
* This PR does NOT implement benchmark runner, model switching, or provider integration.
* This PR does NOT use wall-clock time in the artifact output (uses `null` / None).
* This PR does NOT modify schemas, ROADMAP.md, pyproject.toml, or any file outside the five target files.
* This PR does NOT add dependencies.

## Review artifact readiness rule

The precommit-review.yml for PR 0106 must:
* Record full validation results including all four command strings, exit codes, and short output snippets
* Not claim pass with validation skipped/not_run
* Enforce diff completeness using `git status --short` and `git diff --name-only`
* Enforce evidence completeness: files not in FILES READ = not observed = cannot be claimed
* Enforce claim-to-evidence consistency for all confirmations
* Include a first-class Plan Drift Gate section

### Required Plan Drift Gate in future precommit-review

```
PLAN DRIFT GATE

* verdict: pass | warning | block
* file drift:
* behavior drift:
* object-shape drift:
* CLI drift:
* validation drift:
* semantic drift:
* future-scope drift:
* accepted deviations:
* blockers:
```

## Decisions made

* implementation files: `services/runner/src/runner/gate_evidence.py` (new), `services/runner/src/runner/doctor.py` (modified), `services/runner/src/runner/__main__.py` (modified)
* test files: `services/runner/tests/test_gate_evidence.py` (new), `services/runner/tests/test_doctor_cli.py` (modified)
* bundle object shape: `GateEvidenceBundleInput` — frozen dataclass with product_state_ref, acceptance_criteria_ref, phase_id, run_id, proof_ref_ids, runtime_capture_refs, handoff_packet_path, acceptance_criteria_path, output_path, capture_artifact_paths, gate_id (optional), actor_or_role (optional)
* bundle result shape: `GateEvidenceBundleResult` — frozen dataclass with status (BUNDLED/REJECTED), reason_codes, artifact_path, bundle_ref (SHA256 of bundle artifact), consistency_summary, details
* bundle reference fields: bundle_ref = first 16 hex chars of SHA256 of canonical bundle JSON
* CLI command shape: `python -m runner bundle evidence <path>` via `build_gate_evidence_bundle_file()` in doctor.py and `bundle` subcommand group in `__main__.py`
* bundle input source allowed: explicit JSON input file referencing paths to existing artifacts on disk
* consistency checks: product_state_ref, acceptance_criteria_ref (with SHA256 verification), phase_id, run_id, proof_ref_ids (including handoff packet superset check), runtime_capture_refs (verified against capture artifact files)
* rejected bundle types: missing required fields, inconsistent refs across artifacts, hidden reasoning, URL-only evidence, unbounded path, oversized output
* stable reason codes: 17 constants as defined above
* artifact format: JSON with `ariadne_bundle_version`, all identity fields, sorted arrays, `bundled_at: null`
* reference derivation: first 16 hex chars of SHA256(canonical bundle JSON)
* output path constraints: no `..`, no leading `/`, max 255 chars
* validation commands: compileall + focused pytest (gate_evidence) + focused pytest (test_doctor_cli) + regression pytest (9 files) + task_intake check
* Plan Drift Gate requirements: verdict + file/behavior/object-shape/CLI/validation/semantic/future-scope drift fields + accepted deviations + blockers
* blockers: none — all prerequisite conditions met
* warnings: none
* behavior planned: new `gate_evidence.py` with `build_gate_evidence_bundle()`; extend `doctor.py` with `build_gate_evidence_bundle_file()` helper; extend `__main__.py` with `bundle evidence <path>` subcommand; 31 test cases including end-to-end integration; artifact-file-based consistency validation
* boundaries: no criteria evaluation, no gate approval, no finalization, no wall-clock time, no placeholders, no network, no Docker, no LLM, no providers, no dependency changes, no schema changes, no ROADMAP.md changes

## Context snapshot

* current_head: 05e24728abaf1ec713c301d8e4d846fe8553310d
* git_status_short: clean (no modified files)
* post_0100_manifest_status: .project-memory/post-0100/strategic-direction/agent-manifest.md exists and read
* pr_0101_status_evidence: services/runner/src/runner/proof_ref.py exists, tests exist, precommit-review verdict=pass
* pr_0102_status_evidence: services/runner/src/runner/handoff_packet.py exists, tests exist, precommit-review verdict=pass
* pr_0103_status_evidence: services/runner/src/runner/doctor.py, __main__.py, test_doctor_cli.py exist; precommit-review verdict=pass
* pr_0104_status_evidence: services/runner/src/runner/proof_capture.py, test_proof_capture.py exist; precommit-review verdict=pass (198 tests)
* pr_0105_status_evidence: services/runner/src/runner/acceptance_criteria.py, test_acceptance_criteria.py exist; precommit-review.yml verdict=pass (30 + 233 tests)
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
* .project-memory/pr/0105-spec-freeze-acceptance-criteria/PLAN.md
* .project-memory/pr/0105-spec-freeze-acceptance-criteria/reviews/plan-review.yml
* .project-memory/pr/0105-spec-freeze-acceptance-criteria/reviews/precommit-review.yml
* services/runner/src/runner/proof_ref.py
* services/runner/tests/test_proof_ref.py
* services/runner/src/runner/handoff_packet.py
* services/runner/tests/test_handoff_packet.py
* services/runner/src/runner/proof_capture.py
* services/runner/tests/test_proof_capture.py
* services/runner/src/runner/acceptance_criteria.py
* services/runner/tests/test_acceptance_criteria.py
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

* .project-memory/pr/0106-gate-evidence-bundle/PLAN.md

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
* confirm: PR/commit 0105 status checked and established
* confirm: PR 0101 proof_ref evidence read (source + tests + precommit-review)
* confirm: PR 0102 handoff_packet evidence read (source + tests + precommit-review)
* confirm: PR 0103 CLI skeleton evidence read (source + tests + precommit-review)
* confirm: PR 0104 proof_capture evidence read (source + tests + precommit-review)
* confirm: PR 0105 acceptance_criteria evidence read (source + tests + precommit-review)
* confirm: Roadmap Alignment Gate applied — roadmap track, PR slot, and strategic direction match
* confirm: PR is executable-first — Python implementation + pytest tests planned
* confirm: PR is not docs-only — implementation files + test files required
* confirm: PR is not schemas-only — no schema changes planned
* confirm: PR is not packaging-only — no pyproject.toml/setup.cfg/setup.py changes planned
* confirm: PR is not frontend-only — pure backend runtime object + CLI
* confirm: gate evidence bundle planned — `bundle evidence <path>` subcommand
* confirm: deterministic local bundle planned — SHA256-derived bundle_ref, null timestamp
* confirm: consistency validation planned — product_state_ref, acceptance_criteria_ref, phase_id, run_id, proof_ref_ids, runtime_capture_refs all cross-checked
* confirm: bounded artifact output planned — max 255 char path
* confirm: bundle_ref derivation planned — from SHA256 of canonical bundle JSON
* confirm: focused tests planned (31 test cases across two test files)
* confirm: Plan Drift Gate required — in precommit-review.yml
* confirm: arbitrary command execution rejected — no command execution in this PR
* confirm: hidden chain-of-thought logging rejected — `REASON_HIDDEN_REASONING_NOT_ALLOWED`
* confirm: external URL-only evidence rejected — `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED`
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
* confirm: no non-semantic placeholders planned — `bundled_at: null` is semantically meaningful (deterministic mode indicator)
* confirm: product name remains Ariadne
* confirm: forbidden legacy names/examples excluded
* confirm: evidence completeness rule preserved
* confirm: claim-to-evidence consistency rule preserved
* confirm: no git mutation commands run
* confirm: no Docker commands run

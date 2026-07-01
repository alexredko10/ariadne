# PR 0107 — Evidence-Backed Self-Improvement Candidate

## Purpose

Add a deterministic local self-improvement candidate runtime object for Ariadne: a function and CLI command that consumes gate evidence bundle output (PR 0106) and stable rejection reason codes, then produces bounded, evidence-backed improvement candidate artifacts. The candidate does NOT edit code, commit changes, call models, or approve itself — it is a bounded proposal object that humans or future automation can review.

## Roadmap alignment

* roadmap track: post-0100 Proof-First Runtime / Self-Improvement Loop
* expected PR slot: 0107 — Evidence-Backed Self-Improvement Candidate
* why this PR is next: PRs 0101–0106 have established proof refs, handoff packets, CLI skeleton, proof capture, acceptance criteria freeze, and gate evidence bundles. PR 0107 starts Ariadne's internal self-improvement loop by converting observed gate evidence into bounded, categorized improvement candidates that can guide future work.
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md (Section 10 — Stream 1: Proof-First Runtime, PR 0107 listed as seventh PR)
* batching policy check: self-improvement candidate runtime object + deterministic category mapping + focused tests form one coherent executable-first PR. ADR 0011 allows batching related runtime objects and their CLI wrappers into one PR slot.
* anti-committee-mode check: executable Python code and focused pytest tests required; no docs-only, schema-only, or packaging-only output.
* frontend repair note: frontend/browser visibility is deferred to a follow-up PR. This PR creates the runtime object that frontend can later display. The `frontend_visibility_gap` improvement category is defined so candidates can represent frontend gaps without modifying frontend code.
* architect sign-off required: no — ROADMAP.md and PR 0106 status are established, post-0100 strategic direction manifest explicitly lists PR 0107 as the next step after 0106.
* architect sign-off reference if required: n/a

## Strategic direction source

* .project-memory/post-0100/strategic-direction/agent-manifest.md — Section 10, Stream 1 Proof-First Runtime, PR 0107 listed as seventh PR.
* ROADMAP.md — roadmap track confirmed; post-0100 Proof-First Runtime / Self-Improvement Loop is the active track.
* PR 0106 precommit-review.yml — confirms gate_evidence bundle is implemented, tested, and merged (26 + 33 = 59 tests, 264 regression).

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
* .project-memory/pr/0106-gate-evidence-bundle/PLAN.md
* .project-memory/pr/0106-gate-evidence-bundle/reviews/precommit-review.yml
* services/runner/src/runner/proof_ref.py
* services/runner/tests/test_proof_ref.py
* services/runner/src/runner/handoff_packet.py
* services/runner/tests/test_handoff_packet.py
* services/runner/src/runner/proof_capture.py
* services/runner/tests/test_proof_capture.py
* services/runner/src/runner/acceptance_criteria.py
* services/runner/tests/test_acceptance_criteria.py
* services/runner/src/runner/gate_evidence.py
* services/runner/tests/test_gate_evidence.py
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

The existing Proof-First Runtime has six complete components:

| Component | File | PR | Role |
|-----------|------|----|------|
| `ProofRef` + `validate_proof_ref()` | `proof_ref.py` | 0101 | Validates a single proof ref |
| `GateReadyHandoffPacket` + `validate_handoff_packet()` | `handoff_packet.py` | 0102 | Validates handoff readiness |
| CLI wrappers | `doctor.py`, `__main__.py` | 0103 | All subcommands (validate, capture, freeze, bundle) |
| `ProofCaptureInput` + `capture_proof()` | `proof_capture.py` | 0104 | Captures proof to artifact file |
| `AcceptanceCriterion` + `freeze_acceptance_criteria()` | `acceptance_criteria.py` | 0105 | Freezes criteria to artifact file |
| `GateEvidenceBundleInput` + `build_gate_evidence_bundle()` | `gate_evidence.py` | 0106 | Validates cross-artifact consistency |

The gate evidence bundle (PR 0106) produces `bundle_ref`, `consistency_summary`, and stable `reason_codes`. PR 0107 consumes these to generate improvement candidates.

## Scope

### Implementation files

* `services/runner/src/runner/improvement_candidate.py` — new: `ImprovementCandidateInput`, `ImprovementCandidate`, `ImprovementCandidateResult`, `ImprovementCandidateStatus`, stable reason codes, improvement category enum, `propose_improvement_candidate()` function
* `services/runner/src/runner/doctor.py` — modified: add `propose_improvement_candidate_file()` helper and wire into CLI
* `services/runner/src/runner/__main__.py` — modified: add `improve propose <path>` subcommand

### Test files

* `services/runner/tests/test_improvement_candidate.py` — new: 25+ test cases covering `propose_improvement_candidate()` directly
* `services/runner/tests/test_doctor_cli.py` — modified: add CLI-level tests for `improve propose <path>`

### Not in scope

* ROADMAP.md — not modified
* Schema files — unchanged in this PR
* docs/ — not modified
* `.project-memory/` — only PLAN.md written; no reviews
* pyproject.toml — not modified
* Any file outside the five target files above
* No automatic code edits
* No automatic commits or PRs
* No autonomous repair
* No provider/model integration
* No network calls
* No Docker calls
* No frontend changes (frontend visibility gap is a category, not frontend code)

## Design

### ImprovementCategory (enum)

```python
class ImprovementCategory(str, enum.Enum):
    """Deterministic improvement category mapping from evidence reason codes."""
    VALIDATION_GAP = "validation_gap"
    EVIDENCE_GAP = "evidence_gap"
    CONSISTENCY_GAP = "consistency_gap"
    SCOPE_DRIFT = "scope_drift"
    MISSING_RUNTIME_ARTIFACT = "missing_runtime_artifact"
    CLI_SURFACE_GAP = "cli_surface_gap"
    FRONTEND_VISIBILITY_GAP = "frontend_visibility_gap"
```

Category mapping rules (deterministic):

| Source reason code pattern | ImprovementCategory |
|---------------------------|---------------------|
| `missing_*_ref`, `missing_*_identity`, `missing_*_path` | `VALIDATION_GAP` |
| `missing_proof_refs`, `missing_capture_refs`, `unknown_capture_ref` | `EVIDENCE_GAP` |
| `inconsistent_*`, `inadmissible_*` | `CONSISTENCY_GAP` |
| `hidden_reasoning_not_allowed`, `external_url_only_not_allowed` | `SCOPE_DRIFT` |
| `unbounded_*`, `oversized_*` | `MISSING_RUNTIME_ARTIFACT` |
| Any code from CLI validation context (reserved for future) | `CLI_SURFACE_GAP` |
| Any code from frontend context (reserved for future) | `FRONTEND_VISIBILITY_GAP` |

If a reason code matches none of the above patterns, fall back to `VALIDATION_GAP`.

### ImprovementCandidateInput (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class ImprovementCandidateInput:
    """Input parameters for proposing an improvement candidate from evidence."""
    product_state_ref: str
    acceptance_criteria_ref: str
    phase_id: str
    run_id: str
    source_bundle_ref: str           # bundle_ref from PR 0106 gate evidence bundle
    source_reason_codes: tuple[str, ...]  # reason_codes from gate evidence or validation
    output_path: str                 # Bounded local file path for candidate artifact
    evidence_refs: tuple[str, ...]   # Ref IDs from evidence that triggered the candidate
    proposed_next_action: str = ""   # Human-readable suggested action (max 4096 chars)
    affected_runtime_area: str = ""  # Area name (max 256 chars)
    requires_human_review: bool = True  # Default True — candidates are proposals, not actions
```

Constraints:
* `product_state_ref`: non-empty, max 256 chars
* `acceptance_criteria_ref`: non-empty, max 256 chars
* `phase_id`: non-empty, max 128 chars
* `run_id`: non-empty, max 128 chars
* `source_bundle_ref`: non-empty, max 64 chars
* `source_reason_codes`: at least one entry; each non-empty, max 128 chars
* `output_path`: non-empty, max 255 chars, no `..`, no leading `/`
* `evidence_refs`: at least one entry; each non-empty, max 256 chars
* `proposed_next_action`: max 4096 chars; no hidden reasoning patterns
* `affected_runtime_area`: max 256 chars

### ImprovementCandidateStatus (enum)

```python
class ImprovementCandidateStatus(str, enum.Enum):
    PROPOSED = "proposed"
    REJECTED = "rejected"
```

### ImprovementCandidate (dataclass, frozen)

The output candidate object (embedded in the result) — not the input, but the structured proposal:

```python
@dataclasses.dataclass(frozen=True)
class ImprovementCandidate:
    """A bounded, evidence-backed improvement candidate proposal."""
    candidate_id: str               # first 16 hex chars of SHA256(candidate JSON)
    product_state_ref: str
    acceptance_criteria_ref: str
    source_bundle_ref: str
    source_reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    improvement_category: str       # ImprovementCategory value
    proposed_next_action: str
    affected_runtime_area: str
    phase_id: str
    run_id: str
    requires_human_review: bool
```

### ImprovementCandidateResult (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class ImprovementCandidateResult:
    status: ImprovementCandidateStatus
    reason_codes: tuple[str, ...]       # empty if proposed
    candidate: ImprovementCandidate | None = None  # set only when proposed
    artifact_path: str | None = None     # set only when proposed
    details: str | None = None
```

### Stable rejection reason codes

| Constant | Value |
|----------|-------|
| `REASON_MISSING_GATE_EVIDENCE` | `"missing_gate_evidence"` |
| `REASON_MISSING_PRODUCT_STATE_REF` | `"missing_product_state_ref"` |
| `REASON_MISSING_ACCEPTANCE_CRITERIA_REF` | `"missing_acceptance_criteria_ref"` |
| `REASON_MISSING_REASON_CODE` | `"missing_reason_code"` |
| `REASON_MISSING_EVIDENCE_REF` | `"missing_evidence_ref"` |
| `REASON_UNSUPPORTED_REASON_CODE` | `"unsupported_reason_code"` |
| `REASON_HIDDEN_REASONING_NOT_ALLOWED` | `"hidden_reasoning_not_allowed"` |
| `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED` | `"external_url_only_not_allowed"` |
| `REASON_UNBOUNDED_CANDIDATE_OUTPUT_PATH` | `"unbounded_candidate_output_path"` |
| `REASON_OVERSIZED_CANDIDATE` | `"oversized_candidate"` |
| `REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED` | `"autonomous_code_change_not_allowed"` |
| `REASON_GIT_MUTATION_NOT_ALLOWED` | `"git_mutation_not_allowed"` |
| `REASON_PROVIDER_CALL_NOT_ALLOWED` | `"provider_call_not_allowed"` |

### `propose_improvement_candidate()` function

```python
def propose_improvement_candidate(
    input_data: ImprovementCandidateInput,
    output_dir: str = ".",
) -> ImprovementCandidateResult:
```

Deterministic algorithm:
1. Validate all basic input fields (empty strings, bounds, path safety).
2. Validate `source_reason_codes`: at least one, each non-empty.
3. Validate that no reason code indicates an autonomous/git/provider action attempt (reserved for future use — if `proposed_next_action` contains strings like `"git commit"`, `"git push"`, `"pip install"`, `"import openai"` → reject with appropriate code).
4. Map each `source_reason_code` to `ImprovementCategory` using the deterministic mapping table.
5. Determine `improvement_category`:
   - If all mapped categories are the same, use that category.
   - If multiple categories, use the first mapped category from the sort order (validation_gap < evidence_gap < consistency_gap < scope_drift < missing_runtime_artifact < cli_surface_gap < frontend_visibility_gap) to keep it deterministic.
6. Build canonical candidate JSON:
   - Fields: `ariadne_candidate_version: "1"`, `candidate_id`, `product_state_ref`, `acceptance_criteria_ref`, `source_bundle_ref`, `source_reason_codes` (sorted), `evidence_refs` (sorted), `improvement_category`, `proposed_next_action`, `affected_runtime_area`, `phase_id`, `run_id`, `requires_human_review`, `proposed_at: null` (deterministic, no wall-clock time).
7. Derive `candidate_id` as the first 16 hex chars of SHA256 of the canonical candidate JSON.
8. Build `ImprovementCandidate` object with the derived `candidate_id`.
9. Write artifact JSON to `output_dir / output_path` using `json.dumps(sort_keys=True, indent=2)`.
10. Return `PROPOSED` with candidate, artifact_path.

### Artifact JSON format (deterministic)

```json
{
    "ariadne_candidate_version": "1",
    "candidate_id": "a1b2c3d4e5f67890",
    "product_state_ref": "abc123",
    "acceptance_criteria_ref": "def456",
    "source_bundle_ref": "deadbeef12345678",
    "source_reason_codes": ["missing_proof_refs", "inconsistent_product_state_ref"],
    "evidence_refs": ["pr-001", "capture-text-abc123def456"],
    "improvement_category": "evidence_gap",
    "proposed_next_action": "Add proof capture before creating handoff packet",
    "affected_runtime_area": "runner/proof_capture",
    "phase_id": "phase-1",
    "run_id": "run-001",
    "requires_human_review": true,
    "proposed_at": null
}
```

`proposed_at` is always `null` — no wall-clock time, fully deterministic.

### Rejected candidate types

| Rejected type | Detection |
|---------------|-----------|
| No gate evidence source | Empty `source_bundle_ref` |
| No reason code | Empty `source_reason_codes` |
| Unsupported reason code | Not used — all reason codes are mapped to a category | 
| Missing product state | Empty `product_state_ref` |
| Missing acceptance criteria ref | Empty `acceptance_criteria_ref` |
| Hidden chain-of-thought | In `proposed_next_action` |
| External URL-only evidence | In `source_reason_codes` or `evidence_refs` |
| Candidate requesting code edit | `proposed_next_action` contains `"git commit"`, `"git push"`, `"import "`, `"pip install"`, `"npm install"`, `"openai"`, `"anthropic"` → `REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED` or `REASON_GIT_MUTATION_NOT_ALLOWED` or `REASON_PROVIDER_CALL_NOT_ALLOWED` |
| Unbounded output path | `..`, leading `/`, > 255 chars |
| Oversized candidate | `proposed_next_action` > 4096 chars |

### CLI command shape

```
python -m runner improve propose <path>
```

Where `<path>` is a JSON file containing `ImprovementCandidateInput` fields. The CLI:
1. Reads the file.
2. Parses JSON into `ImprovementCandidateInput`.
3. Calls `propose_improvement_candidate()`.
4. Prints JSON result with `status`, `command`, `result`, `error`.
5. Exit code: 0 if proposed, 1 if rejected or error.

Implementation: add to `doctor.py` as `propose_improvement_candidate_file(path: str, output_dir: str = ".") -> dict` and wire into `__main__.py` under an `improve` subcommand group.

### What this PR does NOT do

| Behavior | Status |
|----------|--------|
| Edit source code | Rejected via reason code + action filter |
| Create git commits | Rejected via reason code |
| Create pull requests | Rejected (no network, no git) |
| Call LLMs or providers | Rejected via reason code |
| Execute shell commands | Rejected (no subprocess, no os.system) |
| Approve gates | Deferred to future PR |
| Evaluate criteria pass/fail | Deferred to future PR |
| Autonomous repair | Deferred to future PR |
| Modify frontend code | Deferred — `frontend_visibility_gap` category defined for representation |

## Required test coverage

### Unit tests for `propose_improvement_candidate()` (in `test_improvement_candidate.py`)

1. `test_valid_candidate_proposed` — valid input from gate evidence → PROPOSED.
2. `test_candidate_deterministic_output_fields` — candidate includes all required fields.
3. `test_same_input_same_candidate_id` — same input twice produces same candidate_id.
4. `test_changed_reason_code_changes_candidate_id` — different reason code changes candidate_id.
5. `test_changed_evidence_ref_changes_candidate_id` — different evidence refs change candidate_id.
6. `test_missing_gate_evidence_fails` — empty source_bundle_ref → REJECTED.
7. `test_missing_product_state_ref_fails` — empty → REJECTED.
8. `test_missing_acceptance_criteria_ref_fails` — empty → REJECTED.
9. `test_missing_reason_code_fails` — empty source_reason_codes → REJECTED.
10. `test_missing_evidence_ref_fails` — empty evidence_refs → REJECTED.
11. `test_hidden_reasoning_not_allowed` — proposed_next_action with `<cot>` → REJECTED.
12. `test_external_url_only_evidence_fails` — evidence_refs with URL-only → REJECTED.
13. `test_autonomous_code_change_rejected` — proposed_next_action requesting git commit → REJECTED.
14. `test_git_mutation_rejected` — proposed_next_action requesting git push → REJECTED.
15. `test_provider_call_rejected` — proposed_next_action requesting model import → REJECTED.
16. `test_unbounded_output_path_fails` — path with `..` → REJECTED.
17. `test_oversized_candidate_fails` — proposed_next_action > 4096 chars → REJECTED.
18. `test_no_filesystem_write_when_rejected` — rejected candidate writes no files.
19. `test_category_mapping_validation_gap` — `missing_product_state_ref` → `VALIDATION_GAP`.
20. `test_category_mapping_evidence_gap` — `missing_proof_refs` → `EVIDENCE_GAP`.
21. `test_category_mapping_consistency_gap` — `inconsistent_product_state_ref` → `CONSISTENCY_GAP`.
22. `test_category_mapping_scope_drift` — `hidden_reasoning_not_allowed` → `SCOPE_DRIFT`.
23. `test_category_mapping_frontend_gap` — future code `frontend_missing_button` → `FRONTEND_VISIBILITY_GAP` (if category reserved; otherwise fallback to `VALIDATION_GAP`).
24. `test_category_mapping_multiple_codes` — multiple codes produce deterministic single category.
25. `test_artifact_json_deterministic` — same input produces identical JSON.
26. `test_product_name_ariadne` — source contains "Ariadne".
27. `test_no_forbidden_legacy_names` — source contains no forbidden legacy terms.

### CLI tests (in `test_doctor_cli.py`)

28. `test_improve_propose_help` — `--help` output for `improve propose` subcommand.
29. `test_improve_propose_valid_file` — valid JSON input → exit 0, proposed.
30. `test_improve_propose_invalid_file` — missing fields → exit 1, rejected.
31. `test_improve_propose_file_not_found` — nonexistent path → exit 1.
32. `test_improve_propose_invalid_json` — malformed JSON → exit 1.
33. `test_improve_no_network_import` — CLI does not import network/Docker/LLM modules.

## Validation strategy

### Primary validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_improvement_candidate.py -q
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_doctor_cli.py -q
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/runner/tests/test_improvement_candidate.py \
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
* `services/runner/tests/test_gate_evidence.py` — exists (PR 0106)
* `services/runner/tests/test_doctor_cli.py` — exists (PR 0103–0106, will be modified)
* `services/runner/tests/test_readiness_gate.py` — exists (PR 0100)
* `services/runner/tests/test_execution_smoke.py` — exists (PR 0100)
* `services/runner/tests/test_execution_substrate_audit.py` — exists (PR 0100)

## Stop conditions

* Block if PR/commit 0106 cannot be established — VERIFIED: gate_evidence.py, test_gate_evidence.py, and precommit-review.yml exist with pass verdict (26 tests, 264 regression)
* Block if PR 0101 proof_ref implementation or precommit evidence is missing — VERIFIED
* Block if PR 0102 handoff_packet implementation or precommit evidence is missing — VERIFIED
* Block if PR 0103 CLI skeleton implementation or precommit evidence is missing — VERIFIED
* Block if PR 0104 proof_capture implementation or precommit evidence is missing — VERIFIED
* Block if PR 0105 acceptance_criteria freeze implementation or precommit evidence is missing — VERIFIED
* Block if PR 0106 gate_evidence implementation or precommit evidence is missing — VERIFIED
* Block if implementation would be docs-only, schemas-only, review-artifact-only, frontend-only, or packaging-only — PASS
* Block if implementation would execute arbitrary shell commands — PASS: no command execution
* Block if implementation would run user-provided commands — PASS: only JSON parsing
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
* Block if non-semantic placeholder strings are required — PASS: `proposed_at: null` is semantically meaningful
* Block if implementation would automatically edit code, commit, push, create PRs, approve gates, or finalize gates — PASS: explicitly rejected by reason codes and action filters; requires_human_review defaults to True

## Boundaries

* This PR does NOT edit source code, create commits, create PRs, or approve gates.
* This PR does NOT call LLMs, providers, or any external system.
* This PR does NOT implement autonomous repair — candidates are proposals requiring human review.
* This PR does NOT modify frontend code — `frontend_visibility_gap` is a category, not frontend code.
* This PR does NOT use wall-clock time in the artifact output (uses `null` / None).
* This PR does NOT modify schemas, ROADMAP.md, pyproject.toml, or any file outside the five target files.
* This PR does NOT add dependencies.

## Review artifact readiness rule

The precommit-review.yml for PR 0107 must:
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

* implementation files: `services/runner/src/runner/improvement_candidate.py` (new), `services/runner/src/runner/doctor.py` (modified), `services/runner/src/runner/__main__.py` (modified)
* test files: `services/runner/tests/test_improvement_candidate.py` (new), `services/runner/tests/test_doctor_cli.py` (modified)
* candidate object shape: `ImprovementCandidateInput` (frozen input), `ImprovementCandidate` (frozen output with candidate_id, source_evidence, category, next_action, requires_human_review), `ImprovementCandidateResult` (status + candidate or reason_codes)
* candidate result shape: `ImprovementCandidateResult` with status enum (PROPOSED/REJECTED), candidate, artifact_path, details
* candidate_id derivation: first 16 hex chars of SHA256 of canonical candidate JSON
* source evidence requirements: source_bundle_ref (required), source_reason_codes (1+), evidence_refs (1+)
* improvement category mapping: deterministic mapping table from reason code patterns to 7 categories
* CLI command shape: `python -m runner improve propose <path>` via `propose_improvement_candidate_file()` in doctor.py and `improve` subcommand group in `__main__.py`
* frontend repair decision: deferred — `frontend_visibility_gap` category defined but no frontend code modified
* rejected candidate types: missing source evidence, missing identity fields, hidden reasoning, URL-only, autonomous code change/git mutation/provider call attempts, unbounded path, oversized
* stable reason codes: 13 constants as defined above
* artifact format: JSON with `ariadne_candidate_version: "1"`, sorted arrays, `proposed_at: null`
* output path constraints: no `..`, no leading `/`, max 255 chars
* validation commands: compileall + focused pytest (improvement_candidate) + focused pytest (test_doctor_cli) + regression pytest (10 files) + task_intake check
* Plan Drift Gate requirements: verdict + file/behavior/object-shape/CLI/validation/semantic/future-scope drift fields + accepted deviations + blockers
* blockers: none — all prerequisite conditions met
* warnings: none
* behavior planned: new `improvement_candidate.py` with `propose_improvement_candidate()`; extend `doctor.py` with `propose_improvement_candidate_file()` helper; extend `__main__.py` with `improve propose <path>` subcommand; 33 test cases; deterministic category mapping; autonomous code change/git mutation/provider call rejection
* boundaries: no code edits, no commits, no PRs, no autonomous repair, no frontend code, no LLMs, no providers, no network, no Docker, no wall-clock time, no placeholders, no dependency changes, no schema changes, no ROADMAP.md changes

## Context snapshot

* current_head: 0f2f8063fb984b25b8a8a75e8b7e56339c1947ae
* git_status_short: clean (no modified files)
* post_0100_manifest_status: .project-memory/post-0100/strategic-direction/agent-manifest.md exists and read
* pr_0101_status_evidence: services/runner/src/runner/proof_ref.py exists, tests exist, precommit-review verdict=pass
* pr_0102_status_evidence: services/runner/src/runner/handoff_packet.py exists, tests exist, precommit-review verdict=pass
* pr_0103_status_evidence: services/runner/src/runner/doctor.py, __main__.py, test_doctor_cli.py exist; precommit-review verdict=pass
* pr_0104_status_evidence: services/runner/src/runner/proof_capture.py, test_proof_capture.py exist; precommit-review verdict=pass
* pr_0105_status_evidence: services/runner/src/runner/acceptance_criteria.py, test_acceptance_criteria.py exist; precommit-review verdict=pass (30 + 233 tests)
* pr_0106_status_evidence: services/runner/src/runner/gate_evidence.py, test_gate_evidence.py exist; precommit-review.yml verdict=pass (26 + 33 = 59 tests, 264 regression)
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
* .project-memory/pr/0106-gate-evidence-bundle/PLAN.md
* .project-memory/pr/0106-gate-evidence-bundle/reviews/plan-review.yml
* .project-memory/pr/0106-gate-evidence-bundle/reviews/precommit-review.yml
* services/runner/src/runner/proof_ref.py
* services/runner/tests/test_proof_ref.py
* services/runner/src/runner/handoff_packet.py
* services/runner/tests/test_handoff_packet.py
* services/runner/src/runner/proof_capture.py
* services/runner/tests/test_proof_capture.py
* services/runner/src/runner/acceptance_criteria.py
* services/runner/tests/test_acceptance_criteria.py
* services/runner/src/runner/gate_evidence.py
* services/runner/tests/test_gate_evidence.py
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

* .project-memory/pr/0107-evidence-backed-self-improvement-candidate/PLAN.md

## Files intentionally ignored

* agents/ — not relevant; agent configs not modified
* docs/ — not modified
* schemas/ — not modified
* pyproject.toml — not modified; no dependency changes needed
* setup.cfg / setup.py — not present
* apps/ — frontend code deferred; not touched
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
* confirm: PR/commit 0106 status checked and established
* confirm: PR 0101 proof_ref evidence read (source + tests + precommit-review)
* confirm: PR 0102 handoff_packet evidence read (source + tests + precommit-review)
* confirm: PR 0103 CLI skeleton evidence read (source + tests + precommit-review)
* confirm: PR 0104 proof_capture evidence read (source + tests + precommit-review)
* confirm: PR 0105 acceptance_criteria evidence read (source + tests + precommit-review)
* confirm: PR 0106 gate_evidence evidence read (source + tests + precommit-review)
* confirm: Roadmap Alignment Gate applied — roadmap track, PR slot, and strategic direction match
* confirm: PR is executable-first — Python implementation + pytest tests planned
* confirm: PR is not docs-only — implementation files + test files required
* confirm: PR is not schemas-only — no schema changes planned
* confirm: PR is not packaging-only — no pyproject.toml/setup.cfg/setup.py changes planned
* confirm: PR is not frontend-only — pure backend runtime object + CLI; frontend code deferred
* confirm: self-improvement candidate planned — `improve propose <path>` subcommand
* confirm: deterministic local candidate generation planned — SHA256-derived candidate_id, null timestamp
* confirm: evidence-backed source requirements planned — source_bundle_ref required, reason codes mapped deterministically
* confirm: autonomous code changes rejected — `REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED`
* confirm: git mutation rejected — `REASON_GIT_MUTATION_NOT_ALLOWED`
* confirm: provider/LLM calls rejected — `REASON_PROVIDER_CALL_NOT_ALLOWED`
* confirm: frontend repair deferred — `frontend_visibility_gap` category defined but no frontend code touched
* confirm: focused tests planned (33 test cases across two test files)
* confirm: Plan Drift Gate required — in precommit-review.yml
* confirm: arbitrary command execution rejected — no command execution in this PR
* confirm: hidden chain-of-thought logging rejected — `REASON_HIDDEN_REASONING_NOT_ALLOWED`
* confirm: external URL-only evidence rejected — `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED`
* confirm: proof evaluation deferred — explicitly excluded
* confirm: gate approval/finalization deferred — explicitly excluded
* confirm: autonomous repair deferred — explicitly excluded (requires_human_review defaults to True)
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
* confirm: no non-semantic placeholders planned — `proposed_at: null` is semantically meaningful (deterministic mode indicator)
* confirm: product name remains Ariadne
* confirm: forbidden legacy names/examples excluded
* confirm: evidence completeness rule preserved
* confirm: claim-to-evidence consistency rule preserved
* confirm: no git mutation commands run
* confirm: no Docker commands run

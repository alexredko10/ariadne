# PR 0102 — Gate-Ready Handoff Packet

## Purpose

Define the second post-0100 Proof-First Runtime capability: a deterministic, JSON-serializable gate-ready handoff packet that composes with PR 0101 proof references and carries all context required to transfer frozen gate state between workflow phases.

## Roadmap alignment

* roadmap track: post-0100 Proof-First Runtime
* expected PR slot: 0102 — Gate-Ready Handoff Packet
* why this PR is next: PR 0101 defined admissible proof refs. PR 0102 defines the packet that carries gate context, product state identity, phase/run identity, and admissible proof refs between phases. Without this packet, proof refs cannot be handed off across phases.
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md (Section 10 — Stream 1: Proof-First Runtime, PR 0102 listed as second PR)
* batching policy check: handoff packet runtime object + deterministic validator + focused tests form one coherent executable-first PR. No docs-only, schema-only, or review-artifact-only output. ADR 0011 allows batching related runtime objects and their tests into one PR slot.
* anti-committee-mode check: executable Python code and focused pytest tests required. No docs-only, schemas-only, or review-artifact-only output.
* architect sign-off required: no — ROADMAP.md and PR 0101 status are established, post-0100 strategic direction manifest explicitly lists PR 0102 as the next step after 0101.
* architect sign-off reference if required: n/a

## Strategic direction source

* .project-memory/post-0100/strategic-direction/agent-manifest.md — Section 10, Stream 1 Proof-First Runtime, PR 0102 listed as second PR.
* ROADMAP.md — roadmap track confirmed; post-0100 Proof-First Runtime is the active track.
* PR 0101 precommit-review.yml — confirms proof_ref runtime object is implemented, tested, and merged.

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
* .project-memory/pr/0100-execution-substrate-freeze-release-gate/PLAN.md
* .project-memory/pr/0100-execution-substrate-freeze-release-gate/reviews/precommit-review.yml
* .project-memory/pr/0101-admissible-proof-ref-runtime-object/PLAN.md
* .project-memory/pr/0101-admissible-proof-ref-runtime-object/reviews/precommit-review.yml
* services/runner/src/runner/proof_ref.py
* services/runner/tests/test_proof_ref.py
* services/runner/src/runner/readiness_gate.py
* services/runner/tests/test_readiness_gate.py
* services/runner/src/runner/execution_smoke.py
* services/runner/src/runner/execution_substrate_audit.py
* services/runner/src/runner/artifacts.py
* services/runner/src/runner/execution_envelope.py
* services/runner/src/runner/local_harness.py
* services/task_intake/src/task_intake/app.py
* services/task_intake/src/task_intake/execution_handoff.py

## Scope

### Implementation files

* `services/runner/src/runner/handoff_packet.py`

### Test files

* `services/runner/tests/test_handoff_packet.py`

### Not in scope

* ROADMAP.md — not modified
* Schema files — unchanged in this PR
* docs/ — not modified
* `.project-memory/` — only PLAN.md written; no reviews
* Any file outside the two target files above
* No CLI, no API endpoint, no schema changes, no dependency changes

## Architecture context

The existing `services/runner/src/runner/` module contains:
* `proof_ref.py` — `ProofRef` dataclass, `ProofRefValidation`, `validate_proof_ref()`, stable reason codes
* `readiness_gate.py` — multi-gate release readiness composed from smoke + audit
* `execution_envelope.py` — deterministic artifact/evidence envelope builder
* `execution_smoke.py` — end-to-end smoke harness
* `execution_substrate_audit.py` — execution substrate static audit
* `artifacts.py` — content-addressed artifact store
* `local_harness.py` — local execution harness composing dispatcher → envelope → review boundary

No existing handoff or gate-ready packet module exists. This PR creates one.

## Design

### HandoffPacketStatus (enum)

```python
class HandoffPacketStatus(str, enum.Enum):
    """Final verdict for a gate-ready handoff packet validation."""
    GATE_READY = "gate_ready"
    NOT_GATE_READY = "not_gate_ready"
```

### HandoffPacketValidation (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class HandoffPacketValidation:
    """Result of validating a GateReadyHandoffPacket."""
    status: HandoffPacketStatus
    reason_codes: tuple[str, ...]  # sorted, stable
    details: str | None = None
```

### Stable reason codes (constants)

| Constant | Value |
|----------|-------|
| `REASON_MISSING_PRODUCT_STATE_REF` | `"missing_product_state_ref"` |
| `REASON_MISSING_ACCEPTANCE_CRITERIA_REF` | `"missing_acceptance_criteria_ref"` |
| `REASON_MISSING_PHASE_IDENTITY` | `"missing_phase_identity"` |
| `REASON_MISSING_RUN_IDENTITY` | `"missing_run_identity"` |
| `REASON_MISSING_GATE` | `"missing_gate"` |
| `REASON_MISSING_ACTOR_OR_ROLE` | `"missing_actor_or_role"` |
| `REASON_MISSING_PROOF_REFS` | `"missing_proof_refs"` |
| `REASON_INADMISSIBLE_PROOF_REF` | `"inadmissible_proof_ref"` |
| `REASON_STALE_OR_UNLINKED_STATE` | `"stale_or_unlinked_state"` |
| `REASON_HIDDEN_REASONING_NOT_ALLOWED` | `"hidden_reasoning_not_allowed"` |
| `REASON_UNBOUNDED_PAYLOAD` | `"unbounded_payload"` |

### GateReadyHandoffPacket (dataclass, frozen)

Essential fields — all required unless tagged optional:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `product_state_ref` | `str` | yes | Hash or identity of the current product state |
| `acceptance_criteria_ref` | `str` | yes | Frozen acceptance criteria reference |
| `phase_id` | `str` | yes | Phase/step identity (e.g. "phase-1", "review") |
| `run_id` | `str` | yes | Unique run/execution identity |
| `gate_id` | `str` | yes | Target gate or action identity |
| `actor_or_role` | `str` | yes | Actor identity or role name |
| `proof_ref_ids` | `tuple[str, ...]` | yes | Admissible proof ref IDs (validated via PR 0101) |
| `payload` | `str` | yes | Bounded plain-text payload (max 65536 chars) |
| `metadata` | `tuple[tuple[str, str], ...]` | no | Ordered key-value metadata pairs for extensibility |

Constraints:
* `product_state_ref`: non-empty, stripped, max 256 chars
* `acceptance_criteria_ref`: non-empty, stripped, max 256 chars
* `phase_id`: non-empty, stripped, max 128 chars
* `run_id`: non-empty, stripped, max 128 chars
* `gate_id`: non-empty, stripped, max 128 chars
* `actor_or_role`: non-empty, stripped, max 128 chars
* `proof_ref_ids`: at least one entry; each ID non-empty, stripped, max 256 chars
* `payload`: non-empty, max 65536 chars; must not contain substring indicating hidden chain-of-thought (e.g. `"<cot>"`, `"<chain_of_thought>"`, `"hidden_reasoning"`)
* `metadata`: optional, max 64 pairs; each key non-empty max 128 chars; each value max 4096 chars

### Public API

```python
def validate_handoff_packet(
    packet: GateReadyHandoffPacket,
    current_product_state_ref: str,
    admissible_ref_ids: frozenset[str],
) -> HandoffPacketValidation:
```

This is the sole validation function. It:
1. Checks all required fields for emptiness.
2. Checks `current_product_state_ref` match.
3. Checks that all `proof_ref_ids` are in `admissible_ref_ids`.
4. Checks payload bound and hidden reasoning exclusion.
5. Returns `GATE_READY` with empty reason_codes if all pass; `NOT_GATE_READY` with sorted stable reason codes otherwise.

### Rejected packet types

| Rejected type | Detection mechanism |
|---------------|---------------------|
| Agent claim as proof | Must pass through PR 0101 `validate_proof_ref` agent-claim-only check; `proof_ref_ids` cannot include refs that would fail admissibility |
| No admissible proof refs | `proof_ref_ids` empty → `REASON_MISSING_PROOF_REFS` |
| Hidden chain-of-thought content | Payload substring check for forbidden patterns |
| External URL-only proof | Must be caught by PR 0101 `validate_proof_ref` (artifact_path unbounded check) |
| Stale/mismatched product state | `current_product_state_ref` mismatch → `REASON_STALE_OR_UNLINKED_STATE` |
| Unbounded payload | Payload length > 65536 → `REASON_UNBOUNDED_PAYLOAD` |
| Missing phase/run identity | Empty `phase_id` or `run_id` |
| Non-JSON-serializable | All types are str/tuple → always JSON-serializable |

### JSON determinism

`GateReadyHandoffPacket` is a frozen dataclass with `to_dict()` and `to_json()` methods using `sort_keys=True`. Tuple fields serialize as sorted lists.

### Proof ref integration

`validate_handoff_packet` does NOT re-run `validate_proof_ref`. It accepts an `admissible_ref_ids: frozenset[str]` parameter. The caller (the orchestrator/phase gate) is responsible for:
1. Collecting `ProofRef` objects.
2. Validating each via `validate_proof_ref()` (PR 0101).
3. Building the set of admissible ref IDs.
4. Passing that set to `validate_handoff_packet()`.

The handoff packet tracks `proof_ref_ids` (strings), not full `ProofRef` objects. This keeps the packet compact and prevents duplication of proof data across phases.

## Validation strategy

### Primary validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_handoff_packet.py -q
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/runner/tests/test_proof_ref.py \
  services/runner/tests/test_handoff_packet.py \
  services/runner/tests/test_readiness_gate.py \
  services/runner/tests/test_execution_smoke.py \
  services/runner/tests/test_execution_substrate_audit.py \
  -q
PYTHONPATH=services/task_intake/src:services/runner/src python -m task_intake.app --check --json
```

All prerequisite files are present in the repository:
* `services/runner/tests/test_proof_ref.py` — exists (PR 0101)
* `services/runner/tests/test_readiness_gate.py` — exists (PR 0100)
* `services/runner/tests/test_execution_smoke.py` — exists (PR 0100)
* `services/runner/tests/test_execution_substrate_audit.py` — exists (PR 0100)

The second command runs only the new test file for focused feedback. The third command runs the full regression suite including proof_ref, handoff_packet, and the readiness/smoke/audit tests.

## Required test coverage

### Unit tests

1. `test_valid_gate_ready_packet`: all required fields + admissible proof refs present → `GATE_READY`
2. `test_missing_product_state_ref`: empty product_state_ref → `NOT_GATE_READY`
3. `test_missing_acceptance_criteria_ref`: empty acceptance_criteria_ref → `NOT_GATE_READY`
4. `test_missing_phase_identity`: empty phase_id → `NOT_GATE_READY`
5. `test_missing_run_identity`: empty run_id → `NOT_GATE_READY`
6. `test_missing_gate`: empty gate_id → `NOT_GATE_READY`
7. `test_missing_actor_or_role`: empty actor_or_role → `NOT_GATE_READY`
8. `test_missing_proof_refs`: empty proof_ref_ids tuple → `NOT_GATE_READY`
9. `test_inadmissible_proof_ref`: proof_ref_id not in admissible set → `NOT_GATE_READY`, preserves reason code
10. `test_hidden_reasoning_not_allowed`: payload contains forbidden substring → `NOT_GATE_READY`
11. `test_unbounded_payload`: payload exceeds limit → `NOT_GATE_READY`
12. `test_stale_state`: product_state_ref mismatch → `NOT_GATE_READY`
13. `test_json_determinism`: two identical packets produce identical JSON
14. `test_reason_codes_sorted`: multiple failures produce sorted reason codes
15. `test_no_side_effects`: validation does not mutate packet
16. `test_packet_is_frozen`: cannot reassign attributes after construction
17. `test_product_name_ariadne`: module docstring contains "Ariadne"
18. `test_no_forbidden_legacy_names`: source contains no legacy terms
19. `test_no_filesystem_or_network`: validation does not read files, call network, call Docker, call LLM, or depend on wall-clock time

### Test structure

```python
# Helper
def _valid_packet(**overrides) -> GateReadyHandoffPacket:
    kwargs = {
        "product_state_ref": "abc123",
        "acceptance_criteria_ref": "def456",
        "phase_id": "phase-1",
        "run_id": "run-001",
        "gate_id": "human_review_gate",
        "actor_or_role": "reviewer",
        "proof_ref_ids": ("pr-001", "pr-002"),
        "payload": "All automated checks passed.",
    }
    kwargs.update(overrides)
    return GateReadyHandoffPacket(**kwargs)

# Test classes
class TestValidPacket:
class TestMissingProductStateRef:
class TestMissingAcceptanceCriteriaRef:
class TestMissingPhaseIdentity:
class TestMissingRunIdentity:
class TestMissingGate:
class TestMissingActorOrRole:
class TestMissingProofRefs:
class TestInadmissibleProofRef:
class TestHiddenReasoning:
class TestUnboundedPayload:
class TestStaleState:
class TestJsonDeterminism:
class TestStableReasonCodes:
class TestNoSideEffects:
class TestProductName:
class TestNoForbiddenNames:
class TestNoFilesystemOrNetwork:
```

## Stop conditions

* Block if PR/commit 0101 cannot be established — VERIFIED: proof_ref.py and test_proof_ref.py exist; PR 0101 precommit-review.yml verdict is `pass`
* Block if post-0100 strategic direction manifest is missing — VERIFIED: agent-manifest.md exists and read
* Block if PR 0101 proof_ref implementation or precommit evidence is missing — VERIFIED: both exist
* Block if implementation would be docs-only, schemas-only, review-artifact-only, or frontend-only — PASS: executable Python + tests planned
* Block if implementation requires external provider integration — PASS: pure Python, no providers
* Block if implementation requires network — PASS: no network
* Block if implementation requires Docker daemon/CLI or Docker SDK — PASS: no Docker
* Block if implementation requires LLM calls — PASS: no LLM
* Block if implementation requires large datasets — PASS: no datasets
* Block if implementation requires hidden chain-of-thought logging — PASS: anti-cot checking is in validation
* Block if implementation copies third-party code — PASS: original code
* Block if implementation modifies ROADMAP.md — PASS: not modified
* Block if implementation changes schemas before runtime behavior exists — PASS: no schema changes
* Block if exact implementation/test paths cannot be selected — PASS: selected
* Block if forbidden legacy names/examples would be introduced — PASS: none introduced

## Boundaries

* This PR does not implement the orchestration layer that calls `validate_handoff_packet` — that belongs in a later PR (e.g., 0103 CLI or 0105 acceptance criteria runtime object).
* This PR does not implement proof collection or proof indexing — those are separate PRs.
* This PR does not modify schemas, ROADMAP.md, or any file outside `services/runner/src/runner/handoff_packet.py` and `services/runner/tests/test_handoff_packet.py`.
* The handoff packet is evidence of gate readiness, not an execution authorization. It does not bypass the Apply Gate or human review boundary.

## Review artifact readiness rule

The precommit-review.yml for PR 0102 must:
* Record full validation results including all four command strings, exit codes, and short output snippets
* Not claim pass with validation skipped/not_run
* Enforce diff completeness using `git status --short` and `git diff --name-only`
* Enforce evidence completeness: files not in FILES READ = not observed = cannot be claimed
* Enforce claim-to-evidence consistency for all confirmations

## Decisions made

* implementation files: `services/runner/src/runner/handoff_packet.py`
* test files: `services/runner/tests/test_handoff_packet.py`
* handoff packet object shape: `GateReadyHandoffPacket` — frozen dataclass with product_state_ref, acceptance_criteria_ref, phase_id, run_id, gate_id, actor_or_role, proof_ref_ids (tuple of str), payload (str, max 65536), metadata (optional tuple of key-value pairs)
* validation result shape: `HandoffPacketValidation` — frozen dataclass with status (enum), reason_codes (sorted tuple of str), details (optional str)
* gate-ready requirements: all required fields non-empty, product_state_ref matches current, all proof_ref_ids in admissible set, payload within bound and no forbidden hidden reasoning patterns
* not-gate-ready reason codes: 11 stable constants as defined above
* proof_ref integration: handoff packet carries `proof_ref_ids` (strings), not full ProofRef objects; validation accepts `admissible_ref_ids: frozenset[str]`; caller must pre-validate proof refs via PR 0101 `validate_proof_ref`
* rejected packet types: agent claim as proof, no admissible proof refs, hidden chain-of-thought, external URL-only proof, stale/mismatched state, unbounded payload, missing phase/run identity, non-JSON-serializable
* JSON/determinism requirements: `to_dict()` and `to_json()` methods; `sort_keys=True`; tuple fields serialize as sorted lists; frozen dataclass prevents mutation
* validation commands: compileall + focused pytest + regression pytest + task_intake check
* blockers: none — all prerequisite conditions met
* warnings: none
* behavior planned: create frozen dataclass `GateReadyHandoffPacket`, frozen dataclass `HandoffPacketValidation`, enum `HandoffPacketStatus`, constants for 11 reason codes, function `validate_handoff_packet()`, helper `to_dict()`/`to_json()` methods, 19 test classes covering all validation paths
* boundaries: no orchestration layer, no CLI, no schema changes, no ROADMAP.md changes, no docs changes

## Roadmap alignment

* roadmap track: post-0100 Proof-First Runtime
* expected PR slot: 0102 — Gate-Ready Handoff Packet
* why this PR is next: follows PR 0101 admissible proof refs and creates the packet that carries gate context and proof refs between phases
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md
* batching policy check: handoff packet runtime object + validator + focused tests form one coherent executable-first PR
* anti-committee-mode check: executable code and tests required; no docs-only or schema-only output
* architect sign-off required: no unless ROADMAP contradicts PR 0102 or PR 0101 status is not established
* architect sign-off reference if required: n/a

## Context snapshot

* current_head: d5031886df33d070c0d97029d0eec35bfe98b426
* git_status_short: clean (no modified files)
* post_0100_manifest_status: .project-memory/post-0100/strategic-direction/agent-manifest.md exists and read
* pr_0101_status_evidence: services/runner/src/runner/proof_ref.py exists, services/runner/tests/test_proof_ref.py exists, precommit-review.yml verdict=pass
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
* .project-memory/pr/0100-execution-substrate-freeze-release-gate/PLAN.md
* .project-memory/pr/0100-execution-substrate-freeze-release-gate/reviews/precommit-review.yml
* .project-memory/pr/0101-admissible-proof-ref-runtime-object/PLAN.md
* .project-memory/pr/0101-admissible-proof-ref-runtime-object/reviews/plan-review.yml
* .project-memory/pr/0101-admissible-proof-ref-runtime-object/reviews/precommit-review.yml
* services/runner/src/runner/proof_ref.py
* services/runner/tests/test_proof_ref.py
* services/runner/src/runner/readiness_gate.py
* services/runner/tests/test_readiness_gate.py
* services/runner/src/runner/execution_smoke.py
* services/runner/src/runner/execution_substrate_audit.py
* services/runner/src/runner/artifacts.py
* services/runner/src/runner/execution_envelope.py
* services/runner/src/runner/local_harness.py
* services/task_intake/src/task_intake/app.py
* services/task_intake/src/task_intake/execution_handoff.py

## Files written

* .project-memory/pr/0102-gate-ready-handoff-packet/PLAN.md

## Files intentionally ignored

* agents/ — not relevant for planning; agent configs not modified
* docs/ — not modified
* schemas/ — not modified
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
* confirm: PR/commit 0101 status checked and established
* confirm: PR 0101 proof_ref evidence read (source + tests + precommit-review)
* confirm: Roadmap Alignment Gate applied — roadmap track, PR slot, and strategic direction match
* confirm: PR is executable-first — Python implementation + focused tests planned
* confirm: PR is not docs-only — implementation file + test file required
* confirm: PR is not schemas-only — no schema changes planned
* confirm: PR is not frontend-only — pure backend runtime object
* confirm: gate-ready handoff packet runtime object planned
* confirm: deterministic validator planned
* confirm: proof_ref integration planned (via admissible_ref_ids parameter)
* confirm: focused tests planned (19 test classes)
* confirm: invalid packet types rejected (11 reason codes + explicit blocked types)
* confirm: hidden chain-of-thought logging rejected (REASON_HIDDEN_REASONING_NOT_ALLOWED + payload filtering)
* confirm: no provider integration planned
* confirm: no network planned
* confirm: no Docker daemon/CLI planned
* confirm: no Docker SDK planned
* confirm: no LLM calls planned
* confirm: no large datasets planned
* confirm: no third-party code copying planned
* confirm: product name remains Ariadne
* confirm: forbidden legacy names/examples excluded
* confirm: evidence completeness rule preserved
* confirm: claim-to-evidence consistency rule preserved
* confirm: no git mutation commands run
* confirm: no Docker commands run

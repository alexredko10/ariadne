# PR 0101 — Admissible Proof Ref Runtime Object Plan

## Goal

Plan the first post-0100 executable Ariadne capability: an admissible proof reference runtime object. This PR starts the Proof-First Runtime stream after the execution-substrate milestone reached PR/commit 0100.

The core principle: **Agent output is not proof. Runtime-captured proof is evidence.** Агент может быть исполнителем, но не нотариусом собственной работы. (The agent may be an executor, but not the notary of its own work.)

Define a deterministic `ProofRef` runtime object — a reference to runtime-captured evidence that is _admissible_ only when tied to current product state, frozen acceptance criteria, runtime capture, bounded artifact path, and phase/run identity. Define a validator that distinguishes admissible proof from agent claims.

---

## Files

### New implementation files

- `services/runner/src/runner/proof_ref.py`

### New test files

- `services/runner/tests/test_proof_ref.py`

### Immutable files (must not be modified by this PR)

- All existing `services/runner/src/runner/*.py` files — no modifications; new module only
- All `services/task_intake/` files — untouched
- `ROADMAP.md` — untouched
- `docs/adr/` — untouched
- `schemas/` — untouched; schema changes are deferred until runtime behavior exists
- `pyproject.toml`, `package.json`, `Makefile`, `Dockerfile*` — untouched

### Forbidden implementation write paths

Any file outside `services/runner/src/runner/proof_ref.py` and `services/runner/tests/test_proof_ref.py`.

---

## Phase 1: `proof_ref.py` — proof reference runtime object

**Location:** `services/runner/src/runner/proof_ref.py`

**Purpose:** Pure Python, deterministic, JSON-serializable, local. Defines the `ProofRef` object, `ProofRefValidation` result, and `validate_proof_ref` function. No filesystem reads, no network, no Docker, no LLM calls, no hidden chain-of-thought, no random IDs, no wall-clock time.

### Object shapes

```python
@dataclasses.dataclass(frozen=True)
class ProofRef:
    """A reference to runtime-captured evidence that may be admissible proof.

    A ProofRef is a claim that a particular runtime artifact constitutes
    admissible evidence for a specific claim about the system state.
    The validation function determines admissibility.
    """
    # Identity — ties proof to a specific phase/run
    run_id: str
    phase_id: str | None

    # Product state reference — what the system state was at time of capture
    product_state_ref: str       # e.g. sha256 of frozen acceptance criteria + source snapshot

    # Acceptance criteria reference — what was being verified
    acceptance_criteria_ref: str # e.g. sha256 of a rubric pack or acceptance checklist

    # Runtime capture — how the evidence was produced
    runtime_capture_ref: str     # e.g. execution_result_id or envelope_id from the execution substrate

    # Artifact path — where the evidence lives within the bounded store
    artifact_path: str           # relative path within artifact store (no absolute paths, no "..")

    # Optional metadata
    summary: str = ""
    tags: frozenset[str] = frozenset()


@dataclasses.dataclass(frozen=True)
class ProofRefValidation:
    """Result of validating a ProofRef for admissibility."""
    admissible: bool
    reason_codes: tuple[str, ...]   # empty if admissible, one or more if inadmissible
    details: str | None = None
```

### Validation function

```python
def validate_proof_ref(
    proof_ref: ProofRef,
    current_product_state_ref: str,
) -> ProofRefValidation:
    """Validate a ProofRef for admissibility.

    Parameters
    ----------
    proof_ref:
        The ProofRef to validate.
    current_product_state_ref:
        The current system state reference (e.g. sha256 of latest frozen
        acceptance criteria + source tree hash).

    Returns
    -------
    ProofRefValidation
        admissible=True only if ALL required fields are present and valid.
    """
```

### Admissibility requirements

A ProofRef is admissible (`admissible=True`, `reason_codes=()`) only when ALL of the following are true:

1. `product_state_ref` is non-empty and matches `current_product_state_ref` (passed as parameter)
2. `acceptance_criteria_ref` is non-empty
3. `runtime_capture_ref` is non-empty
4. `artifact_path` is non-empty and is a **bounded** path (no leading `/`, no `..` segments, no path separators that escape a single depth level, length ≤ 255 characters)
5. `run_id` is non-empty
6. `artifact_path` is not an unbounded wildcard or directory — it must reference a concrete artifact file name (basename length ≥ 3 characters)

**Current product state matching rule:** The `current_product_state_ref` parameter is provided by the caller (typically the runtime layer that knows the current state). The validator does not compute or discover it — it only checks equality. This keeps the validator deterministic, stateless, and independent of filesystem access.

### Inadmissibility reason codes

| `reason_codes` value | Condition |
|---|---|
| `missing_product_state_ref` | `product_state_ref` is empty or whitespace-only |
| `missing_acceptance_criteria_ref` | `acceptance_criteria_ref` is empty or whitespace-only |
| `missing_runtime_capture_ref` | `runtime_capture_ref` is empty or whitespace-only |
| `missing_artifact_path` | `artifact_path` is empty or whitespace-only |
| `unbounded_artifact_path` | `artifact_path` starts with `/`, contains `..`, or exceeds 255 chars |
| `missing_phase_or_run_identity` | both `run_id` and `phase_id` are empty/None |
| `agent_claim_only` | `artifact_path` is present but has a basename shorter than 3 characters (e.g. a bare `/` or single-char reference meaning "the agent says, no specific artifact") |
| `stale_or_unlinked_state` | `product_state_ref` is non-empty, valid format, but does not match `current_product_state_ref` |
| `unsupported_proof_type` | reserved for future proof type classifiers (not triggered in this PR) |

Multiple reason codes may be returned simultaneously (e.g. both `missing_product_state_ref` and `missing_artifact_path` if both fields are empty).

### Rejected proof types (non-exhaustive — reflected in reason codes)

| What is rejected | How it is caught |
|---|---|
| Agent says tests pass without runtime capture ref | `missing_runtime_capture_ref` |
| Agent summarizes output without runtime capture | `missing_runtime_capture_ref` |
| Uncaptured terminal output | `missing_runtime_capture_ref` |
| Stale cache summaries not tied to current state | `stale_or_unlinked_state` |
| Unbounded search claims | `missing_artifact_path` or `unbounded_artifact_path` |
| References not tied to current product state | `stale_or_unlinked_state` |
| Hidden chain-of-thought logs | `agent_claim_only` (chain-of-thought is agent output, not runtime-captured evidence) or `missing_runtime_capture_ref` |
| External URLs as proof without local runtime capture | `missing_runtime_capture_ref` + `stale_or_unlinked_state` (URL has no product state ref) |

### Determinism and JSON requirements

- `validate_proof_ref` is a pure function: same inputs → same outputs.
- No filesystem reads, no network, no wall-clock time, no random values.
- `ProofRef` is frozen (immutable).
- `ProofRef` is JSON-serializable via `dataclasses.asdict()`.
- Reason codes are returned in sorted order for deterministic comparison.
- `tags` is `frozenset` for hashability; serialized as sorted list.

### No schema changes

The ProofRef object is defined in Python code only. Schema changes are deferred until runtime behavior exists and is validated. This PR is executable-first.

---

## Phase 2: Tests

### `test_proof_ref.py` (new file)

- **Valid proof_ref passes:** Create a `ProofRef` with all required fields populated and matching `current_product_state_ref` — assert `admissible=True`, `reason_codes=()`.
- **Missing product_state_ref fails:** Set `product_state_ref=""` — assert `missing_product_state_ref` in `reason_codes`.
- **Missing acceptance_criteria_ref fails:** Set `acceptance_criteria_ref=""` — assert `missing_acceptance_criteria_ref` in `reason_codes`.
- **Missing runtime_capture_ref fails:** Set `runtime_capture_ref=""` — assert `missing_runtime_capture_ref` in `reason_codes`.
- **Missing artifact_path fails:** Set `artifact_path=""` — assert `missing_artifact_path` in `reason_codes`.
- **Unbounded artifact path (absolute) fails:** Set `artifact_path="/absolute/path"` — assert `unbounded_artifact_path` in `reason_codes`.
- **Unbounded artifact path (..) fails:** Set `artifact_path="../../escape"` — assert `unbounded_artifact_path` in `reason_codes`.
- **Unbounded artifact path (too long) fails:** Set `artifact_path` to a 300-character string — assert `unbounded_artifact_path` in `reason_codes`.
- **Missing run_id and phase_id fails:** Set both `run_id=""` and `phase_id=None` — assert `missing_phase_or_run_identity` in `reason_codes`.
- **phase_id present but run_id empty fails:** Set `run_id=""`, `phase_id="phase-1"` — assert `missing_phase_or_run_identity` in `reason_codes` (run_id is required even if phase_id is present).
- **Agent-claim-only (short basename) fails:** Set `artifact_path="a"` (single char basename) — assert `agent_claim_only` in `reason_codes`.
- **Stale/unlinked product_state_ref fails:** Set `product_state_ref="abc"`, pass `current_product_state_ref="xyz"` — assert `stale_or_unlinked_state` in `reason_codes`.
- **Multiple failures simultaneously:** Empty all required fields — assert all of `missing_product_state_ref`, `missing_acceptance_criteria_ref`, `missing_runtime_capture_ref`, `missing_artifact_path`, `missing_phase_or_run_identity` are present in `reason_codes`.
- **JSON serializable:** Call `dataclasses.asdict(proof_ref)` — result passes `json.dumps`.
- **Deterministic:** Two calls with same inputs produce identical `ProofRefValidation`.
- **No side effects:** Call `validate_proof_ref` — assert no filesystem, network, or time calls (verified by the test environment having no mock side-effect targets).
- **Reason codes sorted:** Assert `reason_codes` is sorted — the output order is deterministic.
- **Product name is Ariadne:** ProofRef docstring contains "Ariadne" — a simple grep or string check in the test source is acceptable.

---

## Validation commands

```bash
# 1. Compile check
python -m compileall -f services/runner/src services/task_intake/src

# 2. New proof_ref tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_proof_ref.py -v

# 3. Combined new + existing milestone tests (confirms no regression)
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest \
    services/runner/tests/test_proof_ref.py \
    services/runner/tests/test_readiness_gate.py \
    services/runner/tests/test_execution_smoke.py \
    services/runner/tests/test_execution_substrate_audit.py \
    -q

# 4. Task intake app check
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m task_intake.app --check --json

# 5. Full runner test suite (optional)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/ -q --timeout=30
```

---

## Review artifact readiness rule

The final precommit-review.yml for this PR must:

1. Record full validation results — all validation commands run, not skipped.
2. Include command strings, exit codes, and short output snippets for each validation command.
3. Not claim pass with validation skipped/not_run.
4. Enforce current-review diff completeness using `git status --short` and `git diff --name-only`.
5. Enforce evidence completeness: a file not listed in FILES READ was not observed and cannot be claimed.
6. Enforce claim-to-evidence consistency: every confirmation in the review artifact must trace to a specific file read or validation command output.

---

## Roadmap alignment

- **roadmap track:** post-0100 Proof-First Runtime
- **expected PR slot:** 0101 — Admissible Proof Ref Runtime Object
- **why this PR is next:** It is the first executable Proof-First Runtime object after the execution-substrate freeze gate at PR 0100. The post-0100 strategic direction manifest (`.project-memory/post-0100/strategic-direction/agent-manifest.md`) identifies proof-first as the lead capability. The execution substrate (PR 0094-0100) provides the foundation: artifact store, envelope, review boundary, smoke/audit/readiness gates. ProofRef builds on these by defining what constitutes admissible runtime-captured evidence.
- **strategic direction source:** `.project-memory/post-0100/strategic-direction/agent-manifest.md`
- **batching policy check:** `proof_ref.py` runtime object + deterministic validator + focused tests form one coherent executable-first PR. Satisfies the batching policy.
- **anti-committee-mode check:** Executable code and tests required. No docs-only or schema-only output. The PR delivers a callable `validate_proof_ref` function with 15+ unit tests.
- **architect sign-off required:** no
- **architect sign-off reference if required:** n/a

---

## Blockers

1. PR/commit 0100 cannot be established — the execution-substrate freeze gate must have reached closure.
2. Post-0100 strategic direction manifest is missing.
3. Implementation is docs-only, schemas-only, review-artifact-only, or frontend-only.
4. Implementation requires external provider integration.
5. Implementation requires network access.
6. Implementation requires Docker daemon/CLI or Docker SDK.
7. Implementation requires LLM calls.
8. Implementation requires large datasets.
9. Implementation requires hidden chain-of-thought logging.
10. Implementation copies third-party code.
11. Implementation modifies ROADMAP.md.
12. Implementation changes schemas before runtime behavior exists.
13. Exact implementation/test paths cannot be selected — they are selected above as `proof_ref.py` and `test_proof_ref.py`.
14. Forbidden legacy names/examples are introduced.

---

## Warnings

- Schema changes are explicitly deferred. The first post-0100 PR should validate the runtime object before defining its schema.
- No integration with existing artifact store or execution envelope yet. This PR defines the standalone proof reference object; wiring into the execution pipeline is deferred to a subsequent PR.

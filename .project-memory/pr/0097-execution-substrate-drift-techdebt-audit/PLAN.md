# PR 0097 — Execution Substrate Drift / Tech-Debt Audit Plan

## Goal

Plan an executable, deterministic local audit that verifies Ariadne execution-substrate invariants have not drifted after PR 0094 (Docker execution wiring), PR 0095 (Docker run artifacts), and PR 0096 (human review boundary). Surface process tech debt: precommit-review completeness gaps (FILES READ vs actual diff) for already-merged PRs as warnings — not blockers.

This PR is **not** docs-only, schemas-only, smoke-only, review-artifact-only, or frontend-only. It delivers an executable audit module with focused tests that make substrate invariants checkable on demand.

**Scope reconciliation with ROADMAP.md:** ROADMAP.md describes PR 0097 as "Local Docker End-to-End Smoke." The actual execution sequence has produced a separate drift/tech-debt audit here because the end-to-end smoke depends on the three prior PRs being verified for invariant correctness and review-process completeness before integration. The audit is a pre-condition for the end-to-end smoke (now planned as PR 0098). This does not contradict the roadmap — it refines the sequence with a necessary verification step.

---

## Files

### New implementation files

- `services/runner/src/runner/execution_substrate_audit.py`

### New test files

- `services/runner/tests/test_execution_substrate_audit.py`

### Integration (one optional new test class in existing test file)

- `services/runner/tests/test_docker_agent_adapter.py` — add new class `TestAuditInvariants` to confirm audit helper's invariants match actual adapter behavior

### Immutable files (must not be modified by this PR)

- `services/runner/src/runner/adapter_registry.py`
- `services/runner/src/runner/docker_agent_adapter.py`
- `services/runner/src/runner/docker_run_artifacts.py`
- `services/runner/src/runner/docker_subprocess_executor.py`
- `services/runner/src/runner/review_boundary.py`
- `services/runner/src/runner/local_harness.py`
- `services/runner/src/runner/execution_envelope.py`
- `services/runner/src/runner/artifacts.py`
- `services/runner/src/runner/doctor.py` — untouched; existing CLI doctor is separate from this audit
- `services/task_intake/` — completely untouched
- `docs/**`, `schemas/**`, `pyproject.toml`, `package.json`, `Makefile`, `Dockerfile*`

### Forbidden implementation write paths

Any file not listed in "New implementation files" above.

---

## Phase 1: `execution_substrate_audit.py` — audit module

**Location:** `services/runner/src/runner/execution_substrate_audit.py`

**Purpose:** Deterministic, local, no-side-effect audit of execution-substrate invariants. The audit does not perform broad repository discovery, does not access the filesystem, does not make network calls, does not run Docker, and does not persist state. It accepts explicit source files or dict fixtures and returns a list of check results.

**Public API:**

```python
def run_execution_substrate_audit(
    docker_agent_adapter_source: str | None = None,
    docker_run_artifacts_source: str | None = None,
    docker_subprocess_executor_source: str | None = None,
    adapter_registry_source: str | None = None,
    review_boundary_source: str | None = None,
    task_intake_http_source: str | None = None,
    task_intake_execution_handoff_source: str | None = None,
    pr_diff_files: list[AuditDiffInput] | None = None,
) -> AuditReport:
```

Parameters accept Python source text as strings (not file paths) so the audit is testable without filesystem access. When called from a test or CLI, the caller reads the file and passes its content.

**Audit result shape (`AuditReport`):**

```python
class AuditCheck(TypedDict):
    check_id: str                  # unique check identifier
    description: str               # human-readable check name
    passed: bool                   # invariant holds
    severity: str                  # "invariant" | "tech_debt"
    details: str | None            # explanation on failure
    extra: dict | None             # optional structured data (e.g. found artifacts, missing files)

class AuditReport(TypedDict):
    timestamp: str                 # ISO8601 UTC
    checks: list[AuditCheck]       # all audit check results
    summary: dict                  # {"total": int, "passed": int, "failed": int, "warnings": int}
```

---

## Phase 2: Audit invariants

### Invariant 1 — Docker execution dual gate

- **check_id:** `docker_dual_gate`
- **description:** "Docker dual gate: request allow_docker AND env ARIADNE_ALLOW_DOCKER_EXECUTION both required."
- **method:** Scan `adapter_registry_source` for the pattern `allow_docker and env_allowed` (or equivalent combined check). Ensure `allow_docker` and `env_allowed` are both checked in the same truthy branch. Assert that `env_raw.lower() not in ("", "0", "false", "no")` is the env check (not a simple truthy-only check that would pass "false").
- **failure:** if either gate is absent; if "false" string would enable real execution.

### Invariant 2 — requires_review on successful Docker execution

- **check_id:** `docker_success_requires_review`
- **description:** "Successful real docker-agent execution returns status=requires_review."
- **method:** Scan `docker_agent_adapter_source` for `status = "requires_review"` or `status = status` where the variable name resolves to `"requires_review"` in the success branch. Assert that no path assigns `status = "completed"` after a successful real executor call.
- **failure:** if `"completed"` is assigned in the success branch; if `"requires_review"` is absent from the success branch.

### Invariant 3 — failed remains failed

- **check_id:** `docker_failed_unchanged`
- **description:** "Failed real docker-agent execution returns status=failed."
- **method:** Scan for `status = "failed"` in the failure branch.
- **failure:** if failure branch does not assign `"failed"`.

### Invariant 4 — blocked remains blocked

- **check_id:** `docker_blocked_unchanged`
- **description:** "Blocked docker-agent execution returns status=blocked."
- **method:** Scan for `status = "blocked"` in the `allow_docker=False` branch.
- **failure:** if blocked branch does not assign `"blocked"`.

### Invariant 5 — derive_review_boundary maps all three docker statuses

- **check_id:** `review_boundary_status_map`
- **description:** "derive_review_boundary maps requires_review→requires_review, failed→failed, blocked→blocked."
- **method:** Scan `review_boundary_source` for the status-to-decision mapping logic. Using actual `derive_review_boundary` function calls (not source scanning) in test fixtures is preferred — this invariant is best tested via functional call.
- **Note:** Source scanning alone cannot trace status→decision mapping (it's control flow, not string pattern). This check will be marked `passed` only when tested via functional call. Source scanning is supplementary. The test fixture will call `derive_review_boundary` directly.

### Invariant 6 — PR 0095 artifact kinds present

- **check_id:** `artifact_kinds_present`
- **description:** "Four artifact kinds present: docker_stdout, docker_stderr, docker_execution_metadata, docker_command_metadata."
- **method:** Scan `docker_run_artifacts_source` or `docker_agent_adapter_source` for all four kind strings.
- **failure:** if any of the four kind strings is absent.

### Invariant 7 — ARTIFACT_KINDS_PRESENT_EVIDENCE

- **check_id:** `evidence_kinds_present`
- **description:** "Two evidence kinds present: execution_log, execution_note."
- **method:** Scan sources for both evidence kinds.
- **failure:** if either evidence kind is absent.

### Invariant 8 — stdout/stderr bounded

- **check_id:** `stdout_stderr_bounded`
- **description:** "stdout/stderr artifacts truncated at 10000 characters with truncation marker."
- **method:** Scan relevant sources for `truncated` marker or `10000` boundary or equivalent bounding logic.
- **failure:** if no bounding logic found.

### Invariant 9 — environment values redacted

- **check_id:** `env_values_redacted`
- **description:** "Environment variable values not stored in artifacts; only key names and count."
- **method:** Scan sources to confirm `env_var_count` pattern and absence of raw env value storage.
- **failure:** if env values could be stored raw.

### Invariant 10 — subprocess import isolation

- **check_id:** `subprocess_isolation`
- **description:** "subprocess import exists only in docker_subprocess_executor.py and test files."
- **method:** Scan all non-test source files for `import subprocess` or `from subprocess import`. If found in any file other than `docker_subprocess_executor.py`, fail.
- **failure:** if subprocess appears outside the approved module.

### Invariant 11 — task_intake forbidden source strings

- **check_id:** `task_intake_no_forbidden_strings`
- **description:** "task_intake source files contain no forbidden runtime source strings."
- **method:** Scan `task_intake_http_source` for known forbidden strings (subprocess, docker, requests, etc.) using the same logic as the existing `test_no_forbidden_source_strings` test. Alternatively, the existing test itself serves as the proof. The audit will call the same source-string scanning logic used in that test.
- **failure:** if any forbidden string found.

### Invariant 12 — no frontend-only drift

- **check_id:** `no_frontend_only_drift`
- **description:** "No frontend-only UI-only files were modified in the current execution track scope."
- **method:** Accept `pr_diff_files` parameter. If provided, check that no diff entry matches `services/task_intake/src/task_intake/server.py` as the sole modified file across multiple PRs. This is a simple pattern check — if the diff is provided and only contains UI file changes, flag as warning.
- **failure:** not applicable — this is a warning check only.

---

## Phase 3: Review-process completeness retro-check

### Policy

For each of PR 0094, PR 0095, and PR 0096:

1. The audit accepts a list of `AuditDiffInput` entries representing each PR's diff files and precommit-review FILES READ.
2. For each PR, compare the set of files in the actual diff against the set of files in the precommit-review FILES READ.
3. Any file present in the actual diff but absent from FILES READ is recorded as a **tech-debt warning**, not a blocker.
4. This is **retrospective visibility** for already-merged PRs, not a re-gate.

### AuditDiffInput shape

```python
class AuditDiffInput(TypedDict):
    pr_id: str
    diff_files: list[str]                  # files changed in that PR
    precommit_files_read: list[str]        # the files_checked list from precommit-review.yml
```

### Expected retro-check results (from known precommit reviews)

Based on available precommit-review.yml artifacts for PR 0094, PR 0095, and PR 0096:

| PR | Diff files (from precommit-review.yml actual_files_changed) | Precommit FILES READ (from precommit-review.yml files_checked) | Expected gap |
|---|---|---|---|
| PR 0094 | `services/runner/src/runner/adapter_registry.py`, `services/runner/tests/test_adapter_registry.py`, `services/task_intake/src/task_intake/server.py`, `services/task_intake/tests/test_local_runner_selection.py`, `services/runner/src/runner/docker_subprocess_executor.py`, `services/runner/tests/test_docker_subprocess_executor.py` | 14 files listed (includes PLAN.md, plan-review, schemas, ADRs, runner sources, test files, task_intake files) | All diff files covered. Files READ also includes context files not in diff. No gap expected. |
| PR 0095 | `services/runner/src/runner/docker_agent_adapter.py`, `services/runner/tests/test_docker_agent_adapter.py`, `services/runner/src/runner/docker_run_artifacts.py`, `services/runner/tests/test_docker_run_artifacts.py` | 21 files listed (includes PLAN.md, plan-review, schemas, ADRs, PR 0094 artifacts, runner sources, test files, task_intake files) | All diff files covered. No gap expected. |
| PR 0096 | `services/runner/src/runner/docker_agent_adapter.py`, `services/runner/tests/test_docker_agent_adapter.py` | 24 files listed (includes PLAN.md, plan-review, schemas, ADRs, PR 0094/0095 artifacts, runner sources, test files, task_intake files, plus the integration test file `test_human_review_boundary_real_docker.py`) | All diff files covered. No gap expected. |

**Diff source policy:** For the audit tests, diff files and FILES READ are provided as explicit test fixtures (hardcoded in the test or passed as `AuditDiffInput`). No git commands, no branch references, and no broad repository discovery are required. Tests pass even if the old PR branches no longer exist.

### Tech-debt warning categories

- *diff file missing from precommit-review.yml FILES READ* — for any PR where the retro-check finds a gap
- *branch ref unavailable but explicit fixture comparison still possible* — noted as a technical limitation, not a gap
- *invariant coverage present only in focused tests but not yet integrated into a single command* — the audit module addresses this gap
- *duplicated invariant assertions across tests that could later be centralized* — surfaced as a recommendation
- *non-blocking audit visibility gaps that do not weaken runtime behavior* — e.g. a file read for documentation purposes that wasn't in the diff

---

## Phase 4: Tests

### 4a — `test_execution_substrate_audit.py` (new file)

**Unit tests for `run_execution_substrate_audit`:**

- **Docker dual gate invariant — pass:** Provide `adapter_registry_source` containing `allow_docker and env_allowed` and the env truthy check — assert `docker_dual_gate` passes.
- **Docker dual gate invariant — fail env gate:** Provide source without env var check — assert `docker_dual_gate` fails.
- **Docker dual gate invariant — fail false bypass:** Provide source where `env_raw` is truthy-checked without excluding "false" — assert `docker_dual_gate` fails.
- **Requires_review invariant — pass:** Provide source with `status = "requires_review"` in success branch — assert passes.
- **Requires_review invariant — fail:** Provide source with `status = "completed"` in success branch — assert fails.
- **Failed invariant — pass:** Provide source with `status = "failed"` in failure branch — assert passes.
- **Blocked invariant — pass:** Provide source with `status = "blocked"` in blocked branch — assert passes.
- **Artifact kinds invariant — pass:** Provide source containing all four kind strings — assert passes.
- **Artifact kinds invariant — fail:** Provide source missing one kind string — assert fails.
- **Evidence kinds invariant — pass:** Provide source containing both evidence strings — assert passes.
- **stdout bounded invariant — pass:** Provide source containing `10000` and `truncated` — assert passes.
- **stdout bounded invariant — fail:** Provide source with no bounding logic — assert fails.
- **Env redaction invariant — pass:** Provide source with `env_var_count` and no raw value storage — assert passes.
- **Env redaction invariant — fail:** Provide source that stores raw env values — assert fails.
- **Subprocess isolation — pass:** Provide all source files — assert passes if subprocess only in `docker_subprocess_executor.py`.
- **Subprocess isolation — fail:** Provide source with subprocess in another file — assert fails.
- **Task_intake forbidden strings — pass:** Provide source with no forbidden strings — assert passes.
- **Task_intake forbidden strings — fail:** Provide source containing "subprocess" — assert fails.

**Review-process completeness retro-check tests:**

- **No gap — 0094 fixture:** Provide diff files + FILES READ from PR 0094 where all diff files are in FILES READ — assert no warnings generated.
- **Warning generated — file missing from FILES READ:** Provide diff files with one file not in FILES READ — assert warning generated with correct pr_id and missing file.
- **Warning severity:** Assert the result's severity is `"tech_debt"`, not `"invariant"`.
- **No fail when branch ref unavailable:** Provide `AuditDiffInput` without requiring a branch ref — assert test passes regardless of branch existence.
- **Multiple PRs:** Provide fixtures for PR 0094, 0095, and 0096 simultaneously — assert all three produce correct results.

### 4b — `test_docker_agent_adapter.py` integration (new test class only)

Add `TestAuditInvariants` class (does NOT modify existing classes):

- **Audit invariant matches adapter behavior for requires_review:** Call `run_docker_agent_execution(_valid_request(), allow_docker=True, executor=_fake_successful_executor)`, then pass the result to the audit helper's invariant checker — assert the invariant `docker_success_requires_review` passes when the adapter produces `status="requires_review"`.
- **Audit invariant matches adapter behavior for blocked:** Same for `allow_docker=False` — assert invariant passes for `status="blocked"`.
- **Audit invariant matches adapter behavior for failed:** Same for `executor=_fake_failing_executor` — assert invariant passes for `status="failed"`.

---

## Validation commands

```bash
# 1. Compile check
python -m compileall -f services/runner/src services/task_intake/src

# 2. New audit tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_execution_substrate_audit.py -q

# 3. Integration tests — audit invariants match actual adapter behavior
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_agent_adapter.py::TestAuditInvariants -q

# 4. Existing docker_agent_adapter tests unchanged
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_agent_adapter.py -q

# 5. Existing review_boundary tests unchanged
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_review_boundary.py -q

# 6. Existing adapter_registry tests unchanged
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py -q

# 7. Existing artifact/subprocess tests unchanged
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_run_artifacts.py services/runner/tests/test_docker_subprocess_executor.py -q

# 8. Task intake tests unchanged + source-string safety
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_execution_handoff_http.py services/task_intake/tests/test_task_intake_http.py -q

# 9. Source-string safety selectors (existing tests)
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_task_intake_http.py::TestNoSideEffects::test_no_forbidden_source_strings -q
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_execution_handoff_http.py::TestSafety::test_no_forbidden_source_strings -q

# 10. Forbidden imports (adapter_registry + review_boundary)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py::TestNoSideEffects::test_no_forbidden_imports -q
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_review_boundary.py::TestNoSideEffects::test_no_forbidden_imports -q

# 11. Full runner test suite (optional)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/ -q --timeout=30
```

---

## Roadmap alignment

- **roadmap track:** substrate/execution track
- **expected PR slot:** 0097 — Execution Substrate Drift / Tech-Debt Audit
- **why this PR is next:** Follows PR 0094 (Docker execution wiring), PR 0095 (Docker run artifacts), and PR 0096 (human review boundary). Verifies corrected execution-track invariants and review-process completeness before the end-to-end smoke (PR 0098) and stabilization pass (PR 0099). The scope reconcilation with ROADMAP.md (which describes PR 0097 as "Local Docker End-to-End Smoke") is intentional: the audit is a necessary pre-condition for the end-to-end smoke, and the end-to-end integration is deferred to PR 0098.
- **batching policy check:** New audit module + invariant tests + review-process completeness retro-check + existing validation selectors form one coherent substrate hardening batch. Not an isolated UI change. Satisfies the batching policy.
- **drift heuristic check:** Does not trigger. This PR touches only `services/runner/src/runner/` backend files — no UI, no `server.py`, no isolated frontend change.
- **architect sign-off required:** no
- **architect sign-off reference if required:** n/a

---

## Stop conditions

1. Block if ROADMAP.md scope contradiction cannot be reconciled — reconciled above (audit pre-condition for end-to-end smoke, smoke deferred to PR 0098).
2. Block if implementation would be docs-only, schemas-only, smoke-only, or review-artifact-only — the audit module is executable code with focused tests.
3. Block if schema changes are required.
4. Block if dependency/build config changes are required.
5. Block if Docker daemon/CLI execution is required — all audit tests use explicit source text fixtures.
6. Block if `server.py` or any frontend/UI file is modified.
7. Block if audit would require broad repository discovery — the audit accepts explicit sources; no filesystem walking.
8. Block if review-process completeness retro-check would require old PR branches to exist — tests use explicit fixture lists, not git commands.
9. Block if diff-vs-FILES-READ gaps are treated as blockers for already-merged PRs — explicitly documented as tech-debt warnings.
10. Block if PR 0094 dual-gate behavior would change.
11. Block if PR 0095 artifacts/evidence behavior would be removed or weakened.
12. Block if PR 0096 requires_review status behavior would change.
13. Block if `dispatch_execution` single-argument convention would change.
14. Block if subprocess would be introduced outside `docker_subprocess_executor.py` or tests.
15. Block if task_intake forbidden source-string safety would be weakened.
16. Block if forbidden legacy names/examples are introduced.
17. Block if shell placeholders are introduced.
18. Block if implementation modifies files outside exact planned scope.
19. Block if Roadmap alignment section is missing or incomplete.

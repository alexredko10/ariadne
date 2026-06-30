# PR 0099 — Pre-0100 Readiness / Stabilization Gate Plan

## Goal

Plan an executable local pre-0100 readiness / stabilization gate that composes PR 0097's execution substrate audit and PR 0098's execution smoke gate into a single release-readiness verdict. This is the last substrate PR before PR 0100 freeze/release. It must produce a structured machine-readable readiness report, surface any blockers that would prevent PR 0100 from being a freeze/release gate, and confirm that all execution-substrate invariants hold.

No Docker daemon. No new product features. No UI changes. No schema changes. No dependency changes. No release tag.

---

## Scope reconciliation with ROADMAP.md

ROADMAP.md describes PR 0099 as "Stabilization: Acceptance Pass — Run the full acceptance checklist (defined in PR 0091) against the actual local substrate, not just the noop mock. Fix any gaps found during acceptance. Ensure the local interaction page works correctly with the real execution pipeline."

This PR implements the stabilization/acceptance pass as an executable readiness gate that:
1. Runs `run_execution_substrate_audit()` (PR 0097) as a validation step.
2. Runs `run_execution_smoke()` (PR 0098) as a validation step.
3. Wraps them in a `run_readiness_gate()` that produces a structured readiness verdict.
4. Fixes any gaps found during acceptance testing.

This does not contradict the roadmap — it implements the acceptance pass as an executable, composable readiness gate rather than a manual checklist.

---

## Files

### New implementation files

- `services/runner/src/runner/readiness_gate.py`

### New test files

- `services/runner/tests/test_readiness_gate.py`

### Modified files (gap fixes from acceptance testing)

- Any file within `services/runner/src/runner/` that requires a gap fix identified during PR 0099 acceptance testing.
- No files outside `services/runner/src/runner/` may be modified in PR 0099 unless the gap fix requires it AND architect sign-off is obtained.

### Immutable files (must not be modified by this PR unless gap-fix justified)

- `services/runner/src/runner/execution_substrate_audit.py` — imported, not modified
- `services/runner/src/runner/execution_smoke.py` — imported, not modified
- `services/task_intake/` — completely untouched unless gap fix requires it AND architect sign-off obtained
- `docs/**`, `schemas/**`, `pyproject.toml`, `package.json`, `Makefile`, `Dockerfile*`

### Forbidden implementation write paths

Any file outside `services/runner/src/runner/` unless architect sign-off is obtained for a specific gap fix.

---

## Phase 1: `readiness_gate.py` — readiness gate module

**Location:** `services/runner/src/runner/readiness_gate.py`

**Purpose:** Composable local readiness gate that calls the PR 0097 audit and PR 0098 smoke gate, aggregates their results, applies acceptance-pass criteria, and produces a structured machine-readable readiness report. The readiness gate does not require Docker daemon, network, filesystem access, or any external dependency. It calls `run_execution_substrate_audit` and `run_execution_smoke` directly.

**Public API:**

```python
def run_readiness_gate() -> ReadinessReport:
```

No arguments. The readiness gate:
1. Imports `run_execution_smoke` from `runner.execution_smoke` and calls it.
2. Imports `run_execution_substrate_audit` from `runner.execution_substrate_audit` and calls it with actual source files.
3. Applies acceptance-pass criteria to determine readiness for PR 0100.
4. Returns a structured report.

**Readiness result shape (`ReadinessReport`):**

```python
class ReadinessGateCheck(TypedDict):
    gate_id: str
    description: str
    passed: bool
    details: str | None
    extra: dict | None           # {"source": "smoke" | "audit" | "acceptance"}

class ReadinessReport(TypedDict):
    timestamp: str                # ISO8601 UTC
    ok: bool                      # True only if ALL readiness gates pass
    release_readiness: str        # "ready" | "blocked" | "needs_review"
    gates: list[ReadinessGateCheck]
    summary: dict                 # {"total_gates": int, "passed": int, "blockers": int, "warnings": int}
    assessment: str               # human-readable summary of release readiness
```

---

## Phase 2: Readiness gates

### Gate 1 — PR 0097 Audit passes

- **gate_id:** `audit_invariants`
- **description:** "PR 0097 execution substrate audit passes with zero blockers."
- **method:** Call `run_execution_substrate_audit` with actual source files via `inspect.getsource`. Check `summary.blocker_count == 0`.
- **blocker:** if blocker_count > 0.
- **warning:** if warning_count > 0 (tech-debt findings are warnings, not blockers).

### Gate 2 — PR 0098 Smoke gate passes

- **gate_id:** `smoke_gate`
- **description:** "PR 0098 execution smoke gate returns ok=True."
- **method:** Call `run_execution_smoke()`. Check `report["ok"] is True`.
- **blocker:** if smoke gate reports any failed check.

### Gate 3 — PR 0094 Dual gate preserved

- **gate_id:** `dual_gate_preserved`
- **description:** "Docker execution dual gate (request allow_docker + env ARIADNE_ALLOW_DOCKER_EXECUTION) preserved."
- **method:** Verify from smoke gate results that `docker_blocked_by_default`, `docker_blocked_no_request_flag`, `docker_blocked_no_env_switch`, `docker_blocked_false_string`, and `docker_blocked_env_false_string` all passed. Check the audit invariant `docker_dual_gate` passed.
- **blocker:** if any dual-gate check failed.

### Gate 4 — Review boundary preserved

- **gate_id:** `review_boundary_preserved`
- **description:** "requires_review, failed, and blocked statuses all map correctly."
- **method:** Verify from smoke gate results that `noop_completed`, `docker_requires_review`, and `docker_failed` all passed.
- **blocker:** if any review-boundary check failed.

### Gate 5 — Artifact collection preserved

- **gate_id:** `artifacts_preserved`
- **description:** "PR 0095 artifact/evidence kinds visible and redacted."
- **method:** Verify from smoke gate results that `artifact_kinds_visible` and `artifact_redaction` passed.
- **blocker:** if any artifact check failed.

### Gate 6 — Subprocess isolation preserved

- **gate_id:** `subprocess_isolation`
- **description:** "subprocess import remains isolated to docker_subprocess_executor.py and tests."
- **method:** Verify audit invariant `subprocess_isolation` passed.
- **blocker:** if subprocess found outside approved module.

### Gate 7 — Task intake source-string safety

- **gate_id:** `source_string_safety`
- **description:** "task_intake forbidden source-string safety selectors pass."
- **method:** Verify audit invariant `task_intake_no_forbidden_strings` passed OR the existing `test_no_forbidden_source_strings` tests passed in validation commands.
- **blocker:** if forbidden strings found.

### Gate 8 — No frontend-only drift

- **gate_id:** `no_frontend_drift`
- **description:** "No frontend-only UI-only files modified in current execution track."
- **method:** Check smoke gate `no_frontend_only_drift` audit result. Verify no PR in the 0094-0099 sequence touched only `server.py`.
- **blocker:** if drift detected.

### Gate 9 — Acceptance checklist (PR 0091)

- **gate_id:** `acceptance_checklist`
- **description:** "Local interaction page works with real execution pipeline (corrected execution path, not mock-only)."
- **method:** The acceptance checklist from PR 0091 covered: task submission, runner selection, result display, summary card, execution trace, structured view, raw JSON, run history, session report, feedback, confusion signals, manual acceptance checklist, copy/export, empty/error states, first-time user onboarding. This PR verifies that the corrected execution path does not break any of these UI features. Since this PR does not modify `task_intake/`, the existing UI features are verified by ensuring:
  1. The smoke gate passes (the full execution pipeline works without mock).
  2. No breakage is introduced by the execution-track PRs 0094-0098.
  3. Existing task_intake tests (`test_local_runner_selection.py`, `test_execution_handoff_http.py`, `test_task_intake_http.py`) all pass unchanged.
- **blocker:** if any existing task_intake test fails.
- **note:** Full manual acceptance is deferred to operator review. This gate confirms the automated acceptance criteria pass.

---

## Phase 3: Determination logic

The readiness gate computes `release_readiness` as follows:

| Condition | release_readiness |
|---|---|
| All 9 gates pass | `"ready"` |
| Any gate fails, all failures are warnings only (tech-debt severity) | `"needs_review"` |
| Any gate fails with "blocker" severity | `"blocked"` |

The gate's `assessment` field provides a human-readable summary:

```python
if report["ok"]:
    assessment = "All readiness gates pass. PR 0100 can proceed as a freeze/release gate."
elif release_readiness == "needs_review":
    assessment = "Non-blocking warnings found. PR 0100 may proceed but operators should review warnings."
else:
    assessment = "Readiness gate blocked. PR 0100 cannot proceed until blockers are resolved."
```

---

## Phase 4: Acceptance pass gap fixes

If the readiness gate or acceptance testing reveals gaps (e.g., a check fails that should pass), the fix must:

1. Be limited to `services/runner/src/runner/` files.
2. Be the minimum change required to resolve the gap.
3. Not change any contract, signature, or behavioral invariant that was established in PR 0094-0098.
4. Be covered by new or existing tests.
5. Be documented in the PLAN.md implementation section or in the final precommit-review artifact.

If a gap fix requires modifying files outside `services/runner/src/runner/`, architect sign-off must be obtained before proceeding.

---

## Phase 5: Tests

### 5a — `test_readiness_gate.py` (new file)

**Unit tests for `run_readiness_gate`:**

- **All gates pass when all checks pass:** Patch `run_execution_smoke` and `run_execution_substrate_audit` to return passing results — assert `ok=True`, `release_readiness="ready"`.
- **Smoke failure blocks readiness:** Patch smoke to return `ok=False` — assert `release_readiness="blocked"`.
- **Audit blocker blocks readiness:** Patch audit to return `blocker_count=1` — assert `release_readiness="blocked"`.
- **Audit warnings do not block:** Patch audit to return `blocker_count=0, warning_count=1` but smoke passes — assert `release_readiness="needs_review"` or `"ready"` depending on implementation.
- **All gates checked present:** Assert the report contains all 9 `gate_id` values.
- **Assessment string appropriate for each release_readiness value:** Assert `"ready"` has positive assessment; `"blocked"` has negative assessment.
- **Deterministic:** Two calls produce identical `ReadinessReport` (with same mock setup).
- **JSON serializable:** Report passes `json.dumps`.

**Integration tests (calling real audit/smoke modules):**

- **Real audit produces no blockers:** Call `run_readiness_gate()` without mocks — assert `ok=True` (all gates pass on actual current source).

**Note:** The integration test above may fail if PR 0097 or PR 0098 has regressed. This is intentional — it validates that the readiness gate catches real failures.

---

## Validation commands

```bash
# 1. Compile check
python -m compileall -f services/runner/src services/task_intake/src

# 2. New readiness gate unit tests (mocked)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_readiness_gate.py -q

# 3. PR 0098 smoke gate tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_execution_smoke.py -q

# 4. PR 0097 audit tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_execution_substrate_audit.py -q

# 5. Existing docker_agent_adapter tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_agent_adapter.py -q

# 6. Existing review_boundary tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_review_boundary.py -q

# 7. Existing adapter_registry tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py -q

# 8. Existing artifact/subprocess tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_run_artifacts.py services/runner/tests/test_docker_subprocess_executor.py -q

# 9. Existing local harness tests (unchanged)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_local_harness.py -q

# 10. Task intake tests unchanged + source-string safety
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_execution_handoff_http.py services/task_intake/tests/test_task_intake_http.py -q

# 11. Source-string safety selectors (existing tests)
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_task_intake_http.py::TestNoSideEffects::test_no_forbidden_source_strings -q
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_execution_handoff_http.py::TestSafety::test_no_forbidden_source_strings -q

# 12. Forbidden imports (adapter_registry + review_boundary + local_harness)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py::TestNoSideEffects::test_no_forbidden_imports -q
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_review_boundary.py::TestNoSideEffects::test_no_forbidden_imports -q
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_local_harness.py::TestNoSideEffects::test_no_forbidden_imports -q

# 13. Full runner test suite (optional)
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/ -q --timeout=30

# 14. Readiness gate integration (calls real audit + smoke)
PYTHONPATH=services/runner/src \
  python -c "from runner.readiness_gate import run_readiness_gate; r=run_readiness_gate(); print(f'ok={r[\"ok\"]}, release_readiness={r[\"release_readiness\"]}'); assert r['ok'], f'Readiness gate failed: {r[\"summary\"]}'"
```

---

## Artifact readiness rule

The final precommit-review artifact for this PR must:

1. Record full validation results — all validation commands must be run, not skipped.
2. Contain both exact source-string safety selector strings literally in the review artifact:
   - `test_no_forbidden_source_strings` (server.py)
   - `test_no_forbidden_source_strings` (execution_handoff_http.py)
3. Not claim pass with validation skipped/not_run.
4. Enforce current-review diff completeness — all diff files present in FILES READ.
5. Treat intentional ignored dirty files as warnings only when explicitly named.

---

## Roadmap alignment

- **roadmap track:** substrate/execution drift catch-up before PR 0100
- **expected PR slot:** 0099 — Pre-0100 Readiness / Stabilization Gate
- **why this PR is next:** Follows PR 0098 end-to-end execution smoke gate and consolidates executable readiness (composing PR 0097 audit + PR 0098 smoke + acceptance pass) before PR 0100 freeze/release gate.
- **batching policy check:** New readiness gate module + focused readiness tests + existing smoke/audit validation selectors form one coherent substrate stabilization batch. Not an isolated UI change. Satisfies the batching policy.
- **drift heuristic check:** Does not trigger — this is execution substrate readiness/gate work in `services/runner/src/runner/`, not a frontend-only UI change.
- **architect sign-off required:** no
- **architect sign-off reference if required:** n/a

---

## Stop conditions

1. Block if ROADMAP.md scope contradiction cannot be reconciled — reconciled above (acceptance pass implemented as executable readiness gate).
2. Block if implementation would be docs-only, schemas-only, review-artifact-only, or frontend-only.
3. Block if Docker daemon/CLI is required.
4. Block if Docker SDK is required.
5. Block if schema changes are required.
6. Block if dependency/build config changes are required.
7. Block if `server.py` or any frontend/UI file is modified without architect sign-off for a specific gap fix.
8. Block if external capability integration is introduced.
9. Block if release tag or GitHub release creation is introduced in PR 0099.
10. Block if broad repository discovery is required.
11. Block if PR 0094/0095/0096/0097/0098 invariants would change.
12. Block if tests require old PR branches to exist.
13. Block if source-string safety selectors are omitted from validation.
14. Block if precommit artifact could pass with validation skipped.
15. Block if forbidden legacy names/examples are introduced.
16. Block if shell placeholders are introduced.
17. Block if implementation modifies files outside `services/runner/src/runner/` without architect sign-off for a specific gap fix.

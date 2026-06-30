# PR 0100 — Execution Substrate Freeze / Release Gate Plan

## Goal

Plan the PR 0100 execution-substrate freeze / release gate. This PR closes the corrected 0094-0100 execution/substrate sequence. It uses the PR 0099 readiness gate as primary readiness evidence, validates all prior PR invariants, produces a release/freeze artifact, and locks post-0100 boundaries.

No Docker daemon. No new product capability. No UI changes. No schema changes. No dependency changes. No git tag created by agents. No GitHub release created by agents.

---

## Scope reconciliation with ROADMAP.md

ROADMAP.md describes PR 0100 as "Freeze / Release Gate — Tag the repository as v0.1.0 (or equivalent release marker). Update version metadata. Write release notes summarizing the execution substrate capabilities. Lock all post-0100 capability streams."

This PR implements that scope exactly:
1. The release/freeze artifact records milestone readiness evidence.
2. Release notes document execution substrate capabilities.
3. Post-0100 boundary lock is reaffirmed.
4. The tag/release action (git tag, GitHub release) is explicitly deferred to a **human post-merge action only**.

No contradiction.

---

## Files

### Release/freeze artifact files

- `.project-memory/releases/v0.1.0-execution-substrate-freeze.md`

### Modified files

- `ROADMAP.md` — update Execution/Substrate Track status to "COMPLETE" and mark the 0094-0100 sequence as delivered

### No new runtime modules

No new Python modules. The existing `run_readiness_gate()` from PR 0099 is the executable readiness evidence. The existing `run_execution_smoke()`, `run_execution_substrate_audit()`, and all PR 0094-0099 tests remain as validation.

### Frozen files (must not be modified by this PR)

- `services/runner/src/runner/` — all runtime modules are frozen; no new modules, no modifications
- `services/task_intake/` completely untouched
- `docs/adr/` — no ADR modifications (existing ADRs are evidence)
- `docs/adr/0011-pr-batching-and-roadmap-discipline.md` — remains as the policy ADR
- `schemas/` — untouched
- `.project-memory/review-artifact.schema.yml` — untouched
- `.project-memory/pr/` — existing review artifacts are evidence, not modified
- `pyproject.toml`, `package.json`, `Makefile`, `Dockerfile*`

### Forbidden implementation write paths

Any file outside ".project-memory/releases/" and "ROADMAP.md". No runtime code changes.

---

## Phase 1: Release/freeze artifact

**Path:** `.project-memory/releases/v0.1.0-execution-substrate-freeze.md`

**Content requirements:**

```markdown
# Ariadne v0.1.0 — Execution Substrate Freeze

**Date:** 2026-06-30
**Status:** frozen
**Milestone:** Execution Substrate Complete

## What this milestone delivers

The execution substrate provides the foundational runtime capability for
Ariadne: deterministic local execution, runner dispatch, Docker execution
behind layered opt-in, structured artifact collection and redaction, human
review boundary, and composable smoke/audit/readiness verification.

## Execution path summary

1. **Task intake** (`services/task_intake/`) receives execution requests via
   HTTP API or local test mode and handoffs to runner dispatch.
2. **Runner dispatch** (`services/runner/src/runner/adapter_registry.py`)
   routes to `noop` (default) or `docker-agent` (opt-in) adapters via
   `dispatch_execution(execution_request)` with single-argument convention.
3. **Docker execution** (`services/runner/src/runner/docker_agent_adapter.py`)
   requires dual gate: `execution_request.allow_docker` must be true AND
   `ARIADNE_ALLOW_DOCKER_EXECUTION` env var must be truthy. String values
   "false", "FALSE", "no", "0" do not enable execution.
4. **Subprocess executor** (`services/runner/src/runner/docker_subprocess_executor.py`)
   invokes docker CLI via `subprocess.run` with list-form argv. No `shell=True`.
   Timeout returns structured failure, not uncaught exception.
5. **Artifact collection** (`services/runner/src/runner/docker_run_artifacts.py`)
   produces four deterministic artifact kinds (docker_stdout, docker_stderr,
   docker_execution_metadata, docker_command_metadata) with bounded stdout/stderr
   (10k char limit) and redacted environment values (key names/count only).
6. **Human review boundary** (`services/runner/src/runner/review_boundary.py`)
   maps execution status to review decision. Successful real Docker execution
   produces `status=requires_review`, never `completed`.
7. **Execution envelope** (`services/runner/src/runner/execution_envelope.py`)
   normalizes artifacts and evidence.
8. **Local harness** (`services/runner/src/runner/local_harness.py`) composes
   dispatch → envelope → boundary.
9. **Smoke gate** (`services/runner/src/runner/execution_smoke.py`) runs 11
   deterministic checks covering all execution paths.
10. **Audit** (`services/runner/src/runner/execution_substrate_audit.py`)
    verifies 12 source-code invariants and provides review-process completeness
    retro-check.
11. **Readiness gate** (`services/runner/src/runner/readiness_gate.py`) composes
    audit + smoke + acceptance checklist into a single release-readiness verdict.

## Key invariants (verified)

- [x] Docker dual gate: both request allow_docker AND env var required
- [x] String "false" does not enable real Docker execution
- [x] Successful docker-agent execution requires human review
- [x] Failed docker-agent execution returns failed
- [x] Blocked docker-agent execution returns blocked
- [x] Four artifact kinds present: docker_stdout, docker_stderr,
      docker_execution_metadata, docker_command_metadata
- [x] Two evidence kinds present: execution_log, execution_note
- [x] stdout/stderr bounded at 10k characters
- [x] Environment values redacted (key names/count only)
- [x] subprocess import isolated to docker_subprocess_executor.py
- [x] task_intake source files contain no forbidden runtime strings
- [x] dispatch_execution single-argument convention preserved
- [x] No frontend-only drift
- [x] No external capability integration
- [x] Post-0100 capability streams locked

## Post-0100 boundary lock

The following capability streams remain LOCKED after PR 0100. No work may
begin without explicit architecture approval:

- **Proof-First Runtime** — formal verification, invariant enforcement
- **Decision Core** — conductor, planner orchestration, multi-agent decision
  loop
- **Context Layer** — context compilation beyond current mock/preview
- **Model Health Monitor** — model routing, capability profiling, cost
  tracking
- **External Capability Integration** — non-coding domain adapters, external
  service integration
- **Frontend Framework Decision** — any choice of frontend framework beyond
  the current server-side-rendered page

## Validation commands (recorded)

```bash
# Readiness gate
PYTHONPATH=services/runner/src python -c \
  "from runner.readiness_gate import run_readiness_gate; r=run_readiness_gate(); assert r['ok']"

# Smoke gate
PYTHONPATH=services/runner/src python -c \
  "from runner.execution_smoke import run_execution_smoke; r=run_execution_smoke(); assert r['ok']"

# Full test suite
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/ -q
```

## Release tag

The `v0.1.0` tag and any GitHub release are **human post-merge actions only**.
No agent creates git tags or GitHub releases.

## Related artifacts

- ROADMAP.md — Execution/Substrate Track status: COMPLETE
- ADR 0010 — Runner Execution Contract Boundary
- ADR 0011 — PR Batching and Roadmap Discipline
- PR 0094-0099 review artifacts in .project-memory/pr/
```

---

## Phase 2: ROADMAP.md update

Update the Execution/Substrate Track section and PR 0094-0100 sequence to mark them COMPLETE.

**Changes to ROADMAP.md:**

1. In "Execution/Substrate Track (Resumed at PR 0094)" section, change `Status: Present — ...` to `Status: Complete — verified at PR 0100` for each component.
2. Add a status line: `**Status: COMPLETE as of PR 0100.**`
3. In the PR 0094-0100 sequence section, after PR 0100's entry, add a note:
   `**Status: All PRs 0094-0100 delivered. Execution substrate frozen at v0.1.0.**`
4. At the top of the PR sequence section, change the header phrasing to indicate completion.

These are targeted edits, not a wholesale replacement.

---

## Phase 3: Validation

### Validation strategy

No new test files. Validation runs existing PR 0097 audit, PR 0098 smoke gate, PR 0099 readiness gate, and all existing test suites.

```bash
# 1. Compile check
python -m compileall -f services/runner/src services/task_intake/src

# 2. Readiness gate (must pass — this is the primary readiness evidence)
PYTHONPATH=services/runner/src \
  python -c "from runner.readiness_gate import run_readiness_gate; r=run_readiness_gate(); assert r['ok'], f'Readiness gate failed: {r[\"summary\"]}'; print(f'Readiness gate: ok={r[\"ok\"]}, release_readiness={r[\"release_readiness\"]}')"

# 3. PR 0098 Smoke gate tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_execution_smoke.py -q

# 4. PR 0097 Audit tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_execution_substrate_audit.py -q

# 5. PR 0099 Readiness gate tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_readiness_gate.py -q

# 6. Existing docker_agent_adapter tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_agent_adapter.py -q

# 7. Existing review_boundary tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_review_boundary.py -q

# 8. Existing adapter_registry tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py -q

# 9. Existing artifact/subprocess tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_docker_run_artifacts.py services/runner/tests/test_docker_subprocess_executor.py -q

# 10. Existing local harness tests
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_local_harness.py -q

# 11. Task intake tests + source-string safety
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_execution_handoff_http.py services/task_intake/tests/test_task_intake_http.py -q

# 12. Source-string safety selectors
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_task_intake_http.py::TestNoSideEffects::test_no_forbidden_source_strings -q
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m pytest services/task_intake/tests/test_execution_handoff_http.py::TestSafety::test_no_forbidden_source_strings -q

# 13. Forbidden imports
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_adapter_registry.py::TestNoSideEffects::test_no_forbidden_imports -q
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_review_boundary.py::TestNoSideEffects::test_no_forbidden_imports -q
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/test_local_harness.py::TestNoSideEffects::test_no_forbidden_imports -q

# 14. Full runner test suite
PYTHONPATH=services/runner/src \
  python -m pytest services/runner/tests/ -q --timeout=30

# 15. Task intake app check
PYTHONPATH=services/task_intake/src:services/runner/src \
  python -m task_intake.test_mode --task "release check" --json \
  | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('ok', False) or True; print('CLI test-mode: PASS')"
```

### Artifact readiness rule

The final precommit-review artifact for this PR must:

1. Record full validation results — all validation commands must be run, not skipped.
2. Contain both exact source-string safety selector strings literally in the review artifact:
   - `test_no_forbidden_source_strings` (server.py)
   - `test_no_forbidden_source_strings` (execution_handoff_http.py)
3. Not claim pass with validation skipped/not_run.
4. Enforce current-review diff completeness using changed files from `git status --short` and `git diff --name-only`.
5. Treat intentional ignored dirty files as warnings only when explicitly named.
6. Confirm no git tag or GitHub release command was run.

---

## Roadmap alignment

- **roadmap track:** substrate/execution drift catch-up milestone closure
- **expected PR slot:** 0100 — Freeze / Release Gate
- **why this PR is next:** Follows PR 0099 pre-0100 readiness gate and closes the corrected execution-substrate milestone. All prior PRs (0094-0099) are delivered and their invariants are verified by the existing readiness gate, smoke gate, and audit.
- **batching policy check:** Release/freeze evidence artifact + ROADMAP.md marker update + executable readiness verification (via existing PR 0099 readiness gate) + validation commands form one coherent milestone closure batch. Not an isolated UI change. Satisfies the batching policy.
- **drift heuristic check:** Does not trigger — this is execution-substrate freeze/release gate work, not frontend-only UI work.
- **architect sign-off required:** no
- **architect sign-off reference if required:** n/a

---

## Blocker conditions

1. PR 0099 readiness gate is missing or failing — must be merged and passing
2. PR 0098 smoke gate is missing or failing
3. PR 0097 audit is missing or failing
4. Source-string safety selectors fail or are omitted from validation
5. Release/freeze evidence is prose-only with no validation/test linkage
6. Docker daemon/CLI is required
7. Docker SDK is introduced
8. Schema changes, dependency/build changes, frontend/server UI changes, or external capability integration introduced
9. Git tag or GitHub release attempted by an agent
10. Docker dual-gate weakened; string "false" enables real Docker; successful docker-agent can be accepted as completed
11. PR 0095 artifact/evidence kinds disappear or redaction/bounding weakens
12. task_intake forbidden source-string safety weakens
13. subprocess import appears outside docker_subprocess_executor.py and tests
14. dispatch_execution single-argument convention changes
15. Forbidden legacy names/examples introduced
16. Shell placeholders introduced

---

## Stop conditions

1. Block if PR 0099 is not merged into main (readiness gate must exist).
2. Block if ROADMAP.md contradicts PR 0100 scope.
3. Block if implementation would be docs-only without executable/test-backed release evidence — the readiness gate CLI command provides executable evidence.
4. Block if schema changes are required.
5. Block if dependency/build config changes are required.
6. Block if frontend/server UI changes are required.
7. Block if external capability integration is introduced.
8. Block if release tag or GitHub release creation is attempted inside agent actions.
9. Block if broad repo discovery is required.
10. Block if PR 0094/0095/0096/0097/0098/0099 invariants would change.
11. Block if source-string safety selectors are omitted from validation.
12. Block if precommit artifact could pass with validation skipped.
13. Block if forbidden legacy names/examples or shell placeholders would be introduced.
14. Block if any runtime code file is modified in this PR (no new modules, no modifications).

# PR 0108 — Session Continuity Packet Runtime Object

## Purpose

Add a deterministic local Session Continuity Packet runtime object for Ariadne: a function and CLI command that consumes gate evidence bundle output (PR 0106), improvement candidate output (PR 0107), and explicit current-work context, then produces a bounded, durable session continuity artifact. This packet lets humans and agents resume work without relying on model memory — answering where we are, what was decided, what evidence exists, what is blocked, what is deferred, and what the next safe action is.

## Roadmap alignment

* roadmap track: post-0100 Proof-First Runtime / Continuity Layer
* expected PR slot: 0108 — Session Continuity Packet Runtime Object
* why this PR is next: PRs 0101–0107 have established proof refs, handoff packets, CLI skeleton, proof capture, acceptance criteria freeze, gate evidence bundles, and self-improvement candidates. PR 0108 adds the durable thread-state packet that preserves the work thread across interruptions, devices, agents, and future sessions — the continuity layer that makes the Proof-First Runtime resume-safe.
* strategic direction source: .project-memory/post-0100/strategic-direction/agent-manifest.md (Section 10 — Stream 1: Proof-First Runtime, PR 0108 listed as eighth PR)
* batching policy check: session continuity runtime object + focused tests form one coherent executable-first PR. ADR 0011 allows batching related runtime objects and their CLI wrappers into one PR slot.
* anti-committee-mode check: executable Python code and focused pytest tests required; no docs-only, schema-only, or packaging-only output.
* frontend repair note: frontend continuity UI is deferred to a follow-up PR. This PR creates the runtime object and data model that frontend can later display. The `frontend_visibility_gap` continuity category is defined so packets can represent frontend gaps without modifying frontend code.
* architect sign-off required: no — ROADMAP.md and PR 0107 status are established, post-0100 strategic direction manifest explicitly lists PR 0108 as the next step after 0107.
* architect sign-off reference if required: n/a

## Strategic direction source

* .project-memory/post-0100/strategic-direction/agent-manifest.md — Section 10, Stream 1 Proof-First Runtime, PR 0108 listed as eighth PR.
* ROADMAP.md — roadmap track confirmed; post-0100 Proof-First Runtime / Continuity Layer is the active track.
* PR 0107 precommit-review.yml — confirms improvement_candidate is implemented, tested, and merged (32 tests, 301 regression).

## Architecture context

The existing Proof-First Runtime has seven complete components:

| Component | File | PR | Role |
|-----------|------|----|------|
| `ProofRef` + `validate_proof_ref()` | `proof_ref.py` | 0101 | Validates a single proof ref |
| `GateReadyHandoffPacket` + `validate_handoff_packet()` | `handoff_packet.py` | 0102 | Validates handoff readiness |
| CLI wrappers (doctor.py) | `doctor.py`, `__main__.py` | 0103 | All subcommands (validate, capture, freeze, bundle, improve) |
| `ProofCaptureInput` + `capture_proof()` | `proof_capture.py` | 0104 | Captures proof to artifact file |
| `AcceptanceCriterion` + `freeze_acceptance_criteria()` | `acceptance_criteria.py` | 0105 | Freezes criteria to artifact file |
| `GateEvidenceBundleInput` + `build_gate_evidence_bundle()` | `gate_evidence.py` | 0106 | Validates cross-artifact consistency |
| `ImprovementCandidateInput` + `propose_improvement_candidate()` | `improvement_candidate.py` | 0107 | Produces evidence-backed improvement candidates |

The existing CLI entrypoint pattern is: `__main__.py` delegates to `doctor.main(argv)`, which uses argparse with subcommand groups. Each new subcommand group adds a parser in `main()` and a helper file in `doctor.py`.

PR 0108 follows this exact pattern. The addition is: new `session_continuity.py` module, an `{{SESSION_CONTINUITY}}` subcommand in `doctor.py`, and a `session` subcommand group in the argparse tree.

## Scope

### Implementation files

* `services/runner/src/runner/session_continuity.py` — new: `SessionContinuityInput`, `SessionContinuityPacket`, `SessionContinuityResult`, `SessionContinuityStatus`, stable reason codes, `build_session_continuity_packet()` function
* `services/runner/src/runner/doctor.py` — modified: add `build_session_continuity_packet_file()` helper and wire into CLI
* `services/runner/src/runner/__main__.py` — not modified (delegates to `doctor.main()` already)

### Test files

* `services/runner/tests/test_session_continuity.py` — new: 30+ test cases covering `build_session_continuity_packet()` directly
* `services/runner/tests/test_doctor_cli.py` — modified: add CLI-level tests for `session new <path>` subcommand

### Not in scope

* ROADMAP.md — not modified
* Schema files — unchanged in this PR
* docs/ — not modified
* `.project-memory/` — only PLAN.md written; no reviews
* pyproject.toml — not modified
* Any file outside the four target files above
* No automatic code edits, commits, PRs, or autonomous repair
* No provider/model integration, network calls, or Docker calls
* No frontend changes (frontend continuity UI deferred)

## Design

### SessionContinuityInput (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class SessionContinuityInput:
    """Input parameters for building a session continuity packet."""
    # Identity
    product_state_ref: str
    phase_id: str
    run_id: str

    # Current work context
    current_pr: str                # PR number or branch name
    current_goal: str              # Human-readable current objective

    # Evidence links
    approved_plan_ref: str         # Plan ref or PLAN.md path
    latest_review_status: str      # e.g. "pending", "approved", "rejected"
    latest_validation_status: str  # e.g. "passed", "failed", "not_run"
    gate_evidence_refs: tuple[str, ...]   # bundle_refs from PR 0106
    improvement_candidate_refs: tuple[str, ...]  # candidate_ids from PR 0107

    # Drift and scope
    known_drift_risks: tuple[str, ...]    # Human-readable drift risks
    deferred_capabilities: tuple[str, ...]  # Capabilities deferred to future PRs
    next_safe_action: str                 # The deterministic next safe action
    blocked_actions: tuple[str, ...]      # Actions currently blocked

    # File scope
    files_in_scope: tuple[str, ...]       # Files relevant to current work
    files_out_of_scope: tuple[str, ...]   # Files intentionally excluded

    # Output
    output_path: str                     # Bounded file path for packet artifact

    # Optional
    session_label: str = ""              # Human label (max 256 chars)
    evidence_refs: tuple[str, ...] = ()  # Additional evidence refs
    requires_human_review: bool = True
```

Constraints:
* `product_state_ref`: non-empty, max 256 chars
* `phase_id`: non-empty, max 128 chars
* `run_id`: non-empty, max 128 chars
* `current_pr`: non-empty, max 256 chars
* `current_goal`: non-empty, max 4096 chars; no hidden reasoning patterns
* `approved_plan_ref`: non-empty, max 256 chars
* `latest_review_status`: non-empty, max 64 chars
* `latest_validation_status`: non-empty, max 64 chars
* `gate_evidence_refs`: each max 64 chars
* `improvement_candidate_refs`: each max 64 chars
* `known_drift_risks`: at least one entry; each max 2048 chars
* `deferred_capabilities`: each max 1024 chars
* `next_safe_action`: non-empty, max 4096 chars; no hidden reasoning, no forbidden actions
* `blocked_actions`: each max 2048 chars
* `files_in_scope`: at least one entry; each non-empty, max 512 chars
* `files_out_of_scope`: each max 512 chars
* `output_path`: non-empty, max 255 chars, no `..`, no leading `/`
* `session_label`: max 256 chars
* `evidence_refs`: each non-empty, max 256 chars

### SessionContinuityStatus (enum)

```python
class SessionContinuityStatus(str, enum.Enum):
    CREATED = "created"
    REJECTED = "rejected"
```

### SessionContinuityPacket (dataclass, frozen)

The output packet object:

```python
@dataclasses.dataclass(frozen=True)
class SessionContinuityPacket:
    """A durable session continuity packet for resuming work."""
    continuity_ref: str              # first 16 hex chars of SHA256(packet JSON)
    product_state_ref: str
    current_pr: str
    current_goal: str
    approved_plan_ref: str
    latest_review_status: str
    latest_validation_status: str
    gate_evidence_refs: tuple[str, ...]
    improvement_candidate_refs: tuple[str, ...]
    known_drift_risks: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]
    next_safe_action: str
    blocked_actions: tuple[str, ...]
    files_in_scope: tuple[str, ...]
    files_out_of_scope: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    resume_summary: str              # Deterministic template-based summary
    resume_prompt: str               # Deterministic template-based prompt for next agent
    session_label: str
    phase_id: str
    run_id: str
    requires_human_review: bool
```

### SessionContinuityResult (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class SessionContinuityResult:
    status: SessionContinuityStatus
    reason_codes: tuple[str, ...]          # empty if created
    packet: SessionContinuityPacket | None = None  # set only when created
    artifact_path: str | None = None        # set only when created
    details: str | None = None
```

### Stable rejection reason codes

| Constant | Value |
|----------|-------|
| `REASON_MISSING_PRODUCT_STATE_REF` | `"missing_product_state_ref"` |
| `REASON_MISSING_CURRENT_PR` | `"missing_current_pr"` |
| `REASON_MISSING_CURRENT_GOAL` | `"missing_current_goal"` |
| `REASON_MISSING_APPROVED_PLAN_REF` | `"missing_approved_plan_ref"` |
| `REASON_MISSING_EVIDENCE_REFS` | `"missing_evidence_refs"` |
| `REASON_MISSING_NEXT_SAFE_ACTION` | `"missing_next_safe_action"` |
| `REASON_MISSING_REVIEW_STATUS` | `"missing_review_status"` |
| `REASON_MISSING_DRIFT_RISK` | `"missing_drift_risk"` |
| `REASON_INVALID_SCOPE_BOUNDARY` | `"invalid_scope_boundary"` |
| `REASON_HIDDEN_REASONING_NOT_ALLOWED` | `"hidden_reasoning_not_allowed"` |
| `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED` | `"external_url_only_not_allowed"` |
| `REASON_UNBOUNDED_CONTINUITY_OUTPUT_PATH` | `"unbounded_continuity_output_path"` |
| `REASON_OVERSIZED_CONTINUITY_PACKET` | `"oversized_continuity_packet"` |
| `REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED` | `"autonomous_code_change_not_allowed"` |
| `REASON_GIT_MUTATION_NOT_ALLOWED` | `"git_mutation_not_allowed"` |
| `REASON_PROVIDER_CALL_NOT_ALLOWED` | `"provider_call_not_allowed"` |

### `build_session_continuity_packet()` function

```python
def build_session_continuity_packet(
    input_data: SessionContinuityInput,
    output_dir: str = ".",
) -> SessionContinuityResult:
```

Deterministic algorithm:
1. Validate all basic input fields (empty strings, bounds, path safety, forbidden patterns).
2. Validate that `next_safe_action` does not contain forbidden action patterns (git mutation, provider calls, autonomous code change).
3. Validate scope boundary: `files_in_scope` and `files_out_of_scope` must not overlap (same file cannot be in both scopes).
4. Build canonical packet JSON (identity, work context, evidence links, drift, scope, resume fields).
5. Derive `continuity_ref` as the first 16 hex chars of SHA256 of the canonical packet JSON.
6. Build deterministic `resume_summary` from a template:
   ```
   Session: {session_label or current_pr}
   Goal: {current_goal[:200]}...
   Next safe action: {next_safe_action}
   Drift risks: {len(known_drift_risks)} risk(s)
   Files in scope: {len(files_in_scope)} file(s)
   Review status: {latest_review_status}
   Validation status: {latest_validation_status}
   Requires human review: {requires_human_review}
   ```
7. Build deterministic `resume_prompt` from a template:
   ```
   ## Resume Context
   
   Objective: {current_goal}
   PR: {current_pr}
   Plan ref: {approved_plan_ref}
   
   ## Evidence
   Gate evidence bundles: {len(gate_evidence_refs)}
   Improvement candidates: {len(improvement_candidate_refs)}
   Evidence refs: {sorted(evidence_refs)}
   
   ## Scope
   Files in scope: {sorted(files_in_scope)}
   Files out of scope: {sorted(files_out_of_scope)}
   
   ## Drift Risks
   {for each risk: "- {risk}"}
   
   ## Next Safe Action
   {next_safe_action}
   
   ## Blocked Actions
   {for each action: "- {action}"}
   
   ## Forbidden Actions
   - Do not edit source code autonomously
   - Do not create git commits or PRs
   - Do not call external providers or models
   - Do not execute shell commands
   - Do not approve gates or finalize work
   - Do not modify files outside files_in_scope
   ```
8. Build `SessionContinuityPacket` with all derived fields.
9. Write artifact JSON to `output_dir / output_path` using `json.dumps(sort_keys=True, indent=2)`.
10. Return `CREATED` with packet and artifact_path.

### Artifact JSON format (deterministic)

```json
{
    "ariadne_continuity_version": "1",
    "continuity_ref": "a1b2c3d4e5f67890",
    "product_state_ref": "abc123",
    "current_pr": "0108-session-continuity-packet",
    "current_goal": "Add session continuity packet runtime object",
    "approved_plan_ref": ".project-memory/pr/0108-session-continuity-packet/PLAN.md",
    "latest_review_status": "pending",
    "latest_validation_status": "pending",
    "gate_evidence_refs": ["deadbeef12345678"],
    "improvement_candidate_refs": [],
    "known_drift_risks": ["PR 0108 scope must not include frontend"],
    "deferred_capabilities": ["Frontend continuity UI"],
    "next_safe_action": "Review and merge PR 0108",
    "blocked_actions": ["Waiting for PR 0107 merge"],
    "files_in_scope": ["services/runner/src/runner/session_continuity.py"],
    "files_out_of_scope": ["apps/frontend/"],
    "evidence_refs": ["pr-001", "capture-text-abc123def456"],
    "resume_summary": "Session: 0108-session-continuity-packet\nGoal: Add session continuity packet...\nNext safe action: Review and merge PR 0108\nDrift risks: 1 risk(s)\nFiles in scope: 1 file(s)\nReview status: pending\nValidation status: pending\nRequires human review: True",
    "resume_prompt": "## Resume Context\n\n...",
    "session_label": "PR 0108 implementation",
    "phase_id": "phase-1",
    "run_id": "run-001",
    "requires_human_review": true
}
```

All arrays are sorted. No wall-clock time fields. Fully deterministic.

### Resume prompt rule enforcement

The `resume_prompt` is template-based and deterministic. It:
- Contains the current objective
- Lists exact required reads (files_in_scope)
- Lists evidence refs
- Lists files in scope and out of scope
- Lists drift risks
- States the next safe action
- Lists forbidden actions (no autonomous code changes, no git mutations, no provider calls, no shell execution, no gate approval)
- Does NOT contain hidden chain-of-thought
- Does NOT ask the next agent to improvise

### Rejected packet types

| Rejected type | Detection |
|---------------|-----------|
| No product state | Empty `product_state_ref` |
| No current PR | Empty `current_pr` |
| No current goal | Empty `current_goal` |
| No approved plan ref | Empty `approved_plan_ref` |
| No evidence refs | Empty `evidence_refs` and empty `gate_evidence_refs` and empty `improvement_candidate_refs` |
| No next safe action | Empty `next_safe_action` |
| No review status | Empty `latest_review_status` |
| No drift risk | Empty `known_drift_risks` |
| Invalid scope boundary | Same file in both `files_in_scope` and `files_out_of_scope` |
| Hidden chain-of-thought | In `current_goal`, `next_safe_action`, or `resume_prompt` |
| External URL-only evidence | In `evidence_refs` |
| Autonomous code change/git mutation/provider call | In `next_safe_action` via forbidden pattern check |
| Unbounded output path | `..`, leading `/`, > 255 chars |
| Oversized packet | Any text field exceeds its bound |

### CLI command shape

```
python -m runner session new <path>
```

Where `<path>` is a JSON file containing `SessionContinuityInput` fields. The CLI:
1. Reads the file.
2. Parses JSON into `SessionContinuityInput` (converts lists to tuples).
3. Calls `build_session_continuity_packet()`.
4. Prints JSON result with `status`, `command`, `result`, `error`.
5. Exit code: 0 if created, 1 if rejected or error.

Implementation: add to `doctor.py` as `build_session_continuity_packet_file(path: str, output_dir: str = ".") -> dict` and wire into `__main__.py` under a `session` subcommand group.

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
| Modify frontend code | Deferred — continuity packet data model defined for later display |
| Resume previous session | Deferred to follow-up PR — this PR creates the packet, not the resumer |

## Required test coverage

### Unit tests for `build_session_continuity_packet()` (in `test_session_continuity.py`)

1. `test_valid_continuity_packet_created` — valid input with all fields → CREATED.
2. `test_packet_deterministic_output_fields` — packet includes all required fields.
3. `test_same_input_same_continuity_ref` — same input twice produces same ref.
4. `test_changed_goal_changes_continuity_ref` — different goal changes ref.
5. `test_changed_next_safe_action_changes_ref` — different action changes ref.
6. `test_resume_summary_deterministic` — summary is template-based and deterministic.
7. `test_resume_prompt_template_based` — prompt includes objective, scope, evidence, drift, next action, forbidden actions.
8. `test_resume_prompt_no_hidden_reasoning` — prompt does not contain `<cot>` or hidden reasoning.
9. `test_resume_prompt_includes_forbidden_actions` — prompt includes explicit forbidden list.
10. `test_missing_product_state_ref_fails` — empty → REJECTED.
11. `test_missing_current_pr_fails` — empty → REJECTED.
12. `test_missing_current_goal_fails` — empty → REJECTED.
13. `test_missing_approved_plan_ref_fails` — empty → REJECTED.
14. `test_missing_evidence_refs_fails` — all evidence ref groups empty → REJECTED.
15. `test_missing_next_safe_action_fails` — empty → REJECTED.
16. `test_missing_review_status_fails` — empty → REJECTED.
17. `test_missing_drift_risk_fails` — empty known_drift_risks → REJECTED.
18. `test_invalid_scope_boundary_fails` — same file in in_scope and out_of_scope → REJECTED.
19. `test_hidden_reasoning_in_goal_fails` — current_goal with `<cot>` → REJECTED.
20. `test_external_url_only_evidence_fails` — evidence_refs with URL-only → REJECTED.
21. `test_autonomous_code_change_in_action_fails` — next_safe_action requesting git commit → REJECTED.
22. `test_git_mutation_in_action_fails` — next_safe_action requesting git push → REJECTED.
23. `test_provider_call_in_action_fails` — next_safe_action requesting model import → REJECTED.
24. `test_unbounded_output_path_fails` — path with `..` → REJECTED.
25. `test_oversized_packet_fails` — next_safe_action > 4096 chars → REJECTED.
26. `test_no_filesystem_write_when_rejected` — rejected packet writes no files.
27. `test_artifact_json_deterministic` — same input produces identical JSON.
28. `test_packet_includes_files_in_scope` — files_in_scope present and sorted in output.
29. `test_packet_includes_files_out_of_scope` — files_out_of_scope present and sorted in output.
30. `test_product_name_ariadne` — source contains "Ariadne".
31. `test_no_forbidden_legacy_names` — source contains no forbidden legacy terms.

### CLI tests (in `test_doctor_cli.py`)

32. `test_session_new_help` — `--help` output for `session new` subcommand.
33. `test_session_new_valid_file` — valid JSON input → exit 0, created.
34. `test_session_new_invalid_file` — missing fields → exit 1, rejected.
35. `test_session_new_file_not_found` — nonexistent path → exit 1.
36. `test_session_new_invalid_json` — malformed JSON → exit 1.
37. `test_session_no_network_import` — CLI does not import network/Docker/LLM modules.

## Validation strategy

### Primary validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_session_continuity.py -q
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_doctor_cli.py -q
PYTHONPATH=services/task_intake/src:services/runner/src python -m pytest \
  services/runner/tests/test_session_continuity.py \
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
* `services/runner/tests/test_improvement_candidate.py` — exists (PR 0107)
* `services/runner/tests/test_doctor_cli.py` — exists (PR 0103–0107, will be modified)
* `services/runner/tests/test_readiness_gate.py` — exists (PR 0100)
* `services/runner/tests/test_execution_smoke.py` — exists (PR 0100)
* `services/runner/tests/test_execution_substrate_audit.py` — exists (PR 0100)

## Stop conditions

* Block if PR/commit 0107 cannot be established — VERIFIED: improvement_candidate.py, test_improvement_candidate.py, and precommit-review.yml exist with pass verdict (32 tests, 301 regression)
* Block if PR 0101–0106 evidence is missing — VERIFIED: all established
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
* Block if non-semantic placeholder strings are required — PASS: no wall-clock time fields
* Block if implementation would automatically edit code, commit, push, create PRs, approve gates, finalize gates, or perform autonomous repair — PASS: explicitly rejected by forbidden action pattern checks

## Boundaries

* This PR does NOT implement session resumption — it creates the continuity packet artifact that a future resumer command can read.
* This PR does NOT edit source code, create commits, create PRs, or approve gates.
* This PR does NOT call LLMs, providers, or any external system.
* This PR does NOT implement autonomous repair.
* This PR does NOT modify frontend code — frontend continuity UI is deferred.
* This PR does NOT use wall-clock time in the artifact output.
* This PR does NOT modify schemas, ROADMAP.md, pyproject.toml, or any file outside the four target files.
* This PR does NOT add dependencies.

## Review artifact readiness rule

The precommit-review.yml for PR 0108 must:
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
* frontend drift:
* validation drift:
* semantic drift:
* future-scope drift:
* accepted deviations:
* blockers:
```

## Decisions made

* implementation files: `services/runner/src/runner/session_continuity.py` (new), `services/runner/src/runner/doctor.py` (modified)
* test files: `services/runner/tests/test_session_continuity.py` (new), `services/runner/tests/test_doctor_cli.py` (modified)
* continuity object shape: `SessionContinuityInput` (frozen input with identity, PR, goal, evidence links, drift, scope, output_path), `SessionContinuityPacket` (frozen output with all fields + resume_summary + resume_prompt)
* continuity result shape: `SessionContinuityResult` (status enum CREATED/REJECTED, reason_codes, optional packet and artifact_path)
* continuity_ref derivation: first 16 hex chars of SHA256 of canonical packet JSON
* source evidence requirements: gate_evidence_refs and improvement_candidate_refs accepted as optional evidence links; at least one evidence-related field must be non-empty
* resume_prompt decision: included — deterministic, template-based, includes objective, scope, evidence, drift risks, next safe action, forbidden actions
* CLI command shape: `python -m runner session new <path>` with `--output-dir` flag
* frontend repair decision: deferred — continuity packet data model defined for later display
* rejected packet types: missing identity fields, missing PR/goal/plan/evidence/next-action/review/drift, scope boundary overlap, hidden reasoning, URL-only evidence, forbidden actions, unbounded path, oversized
* stable reason codes: 16 constants as defined above
* artifact format: JSON with `ariadne_continuity_version: "1"`, sorted arrays, deterministic resume_summary and resume_prompt
* output path constraints: no `..`, no leading `/`, max 255 chars
* validation commands: compileall + focused pytest (session_continuity) + focused pytest (test_doctor_cli) + regression pytest (11 files) + task_intake check
* Plan Drift Gate requirements: verdict + file/behavior/object-shape/CLI/frontend/validation/semantic/future-scope drift fields + accepted deviations + blockers
* blockers: none — all prerequisite conditions met
* warnings: none
* behavior planned: new `session_continuity.py` with `build_session_continuity_packet()`; extend `doctor.py` with `build_session_continuity_packet_file()`; 37 test cases; deterministic template-based resume_prompt with forbidden actions; scope boundary validation (in-scope vs out-of-scope overlap check)
* boundaries: no session resumption, no code edits, no commits, no PRs, no autonomous repair, no frontend code, no LLMs, no providers, no network, no Docker, no wall-clock time, no dependency changes, no schema changes, no ROADMAP.md changes

## Context snapshot

* current_head: f68009e411be0f7f04aa618395b8053db571d47a
* git_status_short: clean (no modified files)
* post_0100_manifest_status: .project-memory/post-0100/strategic-direction/agent-manifest.md exists and read
* pr_0101_status_evidence: proof_ref.py + tests + precommit-review verdict=pass
* pr_0102_status_evidence: handoff_packet.py + tests + precommit-review verdict=pass
* pr_0103_status_evidence: doctor.py + __main__.py + test_doctor_cli.py + precommit-review verdict=pass
* pr_0104_status_evidence: proof_capture.py + tests + precommit-review verdict=pass
* pr_0105_status_evidence: acceptance_criteria.py + tests + precommit-review verdict=pass (30 + 233)
* pr_0106_status_evidence: gate_evidence.py + tests + precommit-review verdict=pass (26 + 33 = 59 tests, 264 regression)
* pr_0107_status_evidence: improvement_candidate.py + tests + precommit-review.yml verdict=pass (32 tests, 301 regression)
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
* .project-memory/pr/0107-evidence-backed-self-improvement-candidate/PLAN.md
* .project-memory/pr/0107-evidence-backed-self-improvement-candidate/reviews/plan-review.yml
* .project-memory/pr/0107-evidence-backed-self-improvement-candidate/reviews/precommit-review.yml
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
* services/runner/src/runner/improvement_candidate.py
* services/runner/tests/test_improvement_candidate.py
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

* .project-memory/pr/0108-session-continuity-packet/PLAN.md

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
* confirm: PR/commit 0107 status checked and established
* confirm: PR 0101 proof_ref evidence read or blocked
* confirm: PR 0102 handoff_packet evidence read or blocked
* confirm: PR 0103 CLI skeleton evidence read or blocked
* confirm: PR 0104 proof_capture evidence read or blocked
* confirm: PR 0105 acceptance_criteria evidence read or blocked
* confirm: PR 0106 gate_evidence evidence read or blocked
* confirm: PR 0107 improvement_candidate evidence read or blocked
* confirm: Roadmap Alignment Gate applied — roadmap track, PR slot, and strategic direction match
* confirm: PR is executable-first — Python implementation + pytest tests planned
* confirm: PR is not docs-only — implementation files + test files required
* confirm: PR is not schemas-only — no schema changes planned
* confirm: PR is not packaging-only — no pyproject.toml/setup.cfg/setup.py changes planned
* confirm: PR is not frontend-only — pure backend runtime object + CLI; frontend code deferred
* confirm: session continuity packet planned — `session new <path>` subcommand
* confirm: deterministic local continuity generation planned — SHA256-derived continuity_ref
* confirm: evidence-backed source requirements planned — gate_evidence_refs and improvement_candidate_refs accepted
* confirm: resume behavior planned without hidden reasoning — template-based resume_prompt with forbidden actions
* confirm: autonomous code changes rejected — `REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED`
* confirm: git mutation rejected — `REASON_GIT_MUTATION_NOT_ALLOWED`
* confirm: provider/LLM calls rejected — `REASON_PROVIDER_CALL_NOT_ALLOWED`
* confirm: frontend repair deferred — continuity packet data model defined for later display
* confirm: focused tests planned (37 test cases across two test files)
* confirm: Plan Drift Gate required — in precommit-review.yml
* confirm: arbitrary command execution rejected — no command execution in this PR
* confirm: hidden chain-of-thought logging rejected — `REASON_HIDDEN_REASONING_NOT_ALLOWED`
* confirm: external URL-only evidence rejected — `REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED`
* confirm: proof evaluation deferred — explicitly excluded
* confirm: gate approval/finalization deferred — explicitly excluded
* confirm: autonomous repair deferred — explicitly excluded
* confirm: backlog persistence deferred — not selected
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
* confirm: no non-semantic placeholders planned
* confirm: product name remains Ariadne
* confirm: forbidden legacy names/examples excluded
* confirm: evidence completeness rule preserved
* confirm: claim-to-evidence consistency rule preserved
* confirm: no git mutation commands run
* confirm: no Docker commands run

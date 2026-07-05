# PR 0126 — Verdict Parser Plan

## Summary

Plan the third executable Production Line PR after PR 0125: a deterministic Verdict Parser that reads review artifacts (plan-review and precommit-review), extracts verdict/blockers/warnings/evidence/normalized fields, and returns structured control decisions (`continue`, `continue_with_warning`, `stop`, and optional `retry_candidate` recommendation) for the future PR 0127 Pipeline Runner. No agent execution, no Docker, no prompt composition, no full pipeline. Executable-first.

## Context snapshot

| Field | Value |
|-------|-------|
| current_head | 7a8c040f488934b30f83d0a514b94e7430385dba |
| current_branch | 0126-verdict-parser |
| git_status_short | clean |
| production_line_roadmap_evidence | ROADMAP.md L302-L376: Production Line Stream ACTIVE; L313 "0126 — Verdict Parser: parse review artifacts, extract verdict/blockers, decide continue/stop/retry"; L370 docs-only block; L371 unattended git mutation block; L376 proof principle |
| pr_0124_agent_runner_bridge_evidence | `services/runner/src/runner/agent_runner_bridge.py` present; `run_agent_runner_bridge(agent_name, task_prompt, ...)` API available; precommit-review.yml verdict pass |
| pr_0125_prompt_composer_evidence | `services/runner/src/runner/prompt_composer.py` present; `compose_pr_prompts()` returns 4 `PromptPacket` objects; precommit-review.yml verdict pass |
| review_artifact_schema_evidence | `.project-memory/review-artifact.schema.yml` present with `schema_version: "0.1"`, `verdict: "approve | pass | warning | block"`, `blockers`, `warnings`, `validation`, `evidence_ledger`, `boundary_confirmations` |
| optional_missing_files | None |

## Roadmap alignment

* roadmap track: Production Line — Stage 1 Orchestrator
* expected PR slot: 0126 — Verdict Parser
* why this PR is next: PR 0124 added Agent Runner Bridge and PR 0125 added Prompt Composer; the next required capability is parsing review artifacts and turning review verdicts into deterministic continue/stop/retry-candidate control decisions for the future PR 0127 Pipeline Runner
* batching policy check: executable-first substrate PR; not docs-only, not schemas-only, not frontend-only
* drift heuristic check: does not continue Local Interaction UX Track; does not start frozen streams before PR 0136
* proof principle: Agent output is not evidence; runtime/file-captured review artifact proof is evidence

## PR 0124 / Agent Runner Bridge verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/agent_runner_bridge.py` exists | PRESENT ✓ |
| `.project-memory/pr/0124-agent-runner-bridge/reviews/precommit-review.yml` exists, verdict pass | PRESENT ✓ |
| `run_agent_runner_bridge(agent_name, task_prompt, ...)` | CONFIRMED ✓ |

## PR 0125 / Prompt Composer verification

| Check | Result |
|-------|--------|
| `services/runner/src/runner/prompt_composer.py` exists | PRESENT ✓ |
| `.project-memory/pr/0125-prompt-composer/reviews/precommit-review.yml` exists, verdict pass | PRESENT ✓ |
| `compose_pr_prompts()` returns 4 PromptPackets | CONFIRMED ✓ |

## Review artifact schema inventory

| Field | Schema type | Role for parser |
|-------|-------------|-----------------|
| `schema_version` | string "0.1" | Version check |
| `review_type` | "plan-review" | "precommit-review" | "security-review" | "ci-review" | "manual-review" | Review gate identity |
| `verdict` | "approve" | "pass" | "warning" | "block" | Primary control signal |
| `reviewer` | string | Source identification |
| `timestamp` | ISO8601 UTC | Deterministic time check |
| `snapshot_delta` | object | Plan base vs current head delta |
| `scope` | object | Expected vs actual files, forbidden paths |
| `files_checked` | list of strings | Files read during review |
| `validation` | list of ValidationCommand | Validation results |
| `blockers` | list of ReviewBlocker | Blocking issues (may be empty) |
| `warnings` | list of ReviewWarning | Non-blocking issues (may be empty) |
| `decisions_made` | list of ReviewDecision | Review decisions |
| `context_used` | object | Context file inventory |
| `checks` | object (precommit specific) | Section-level pass/fail |
| `boundary_confirmations` | list of strings | Scope boundary evidence |
| `evidence_ledger` | list of evidence rows | Claim-to-evidence mapping |

## Existing review artifact examples inventory

Two real review artifacts are available from the immediate predecessors:

| Artifact path | Review type | Verdict | Has blockers? |
|---------------|-------------|---------|---------------|
| `.project-memory/pr/0124-agent-runner-bridge/reviews/precommit-review.yml` | precommit-review | pass | No (blockers: []) |
| `.project-memory/pr/0125-prompt-composer/reviews/precommit-review.yml` | precommit-review | pass | No (blockers: []) |

Additionally, the plan-review artifacts for PR 0123, 0124, 0125 are available with `verdict: approve`.

## Proposed Verdict Parser contract

### New module

`services/runner/src/runner/verdict_parser.py`

Contains:
- `VerdictParserRequest` — input dataclass
- `ParsedReviewArtifact` — parsed artifact data
- `VerdictDecision` — control decision
- `VerdictDecisionStatus` — status enum: `continue`, `continue_with_warning`, `stop`, `invalid`
- `parse_review_artifact()` — main parse function
- `decide_next_action()` — derive control decision from parsed artifact
- Stable reason codes

### `VerdictParserRequest` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class VerdictParserRequest:
    artifact_path: str                     # path to review artifact YAML file
    artifact_text: str | None = None       # direct artifact text (bypasses file read)
    expected_review_type: str | None = None  # "plan-review" | "precommit-review" for strict mode
    expected_pr_id: str | None = None      # for strict mode
    schema_path: str | None = None         # path to review-artifact.schema.yml (optional)
    strict: bool = False                   # fail on type/pr mismatch
```

### `ParsedReviewArtifact` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class ParsedReviewArtifact:
    review_type: str
    pr_id: str | None
    raw_verdict: str                       # raw verdict from artifact
    normalized_verdict: str                # "pass" | "warning" | "block" | "invalid"
    has_blockers: bool
    blockers: tuple[tuple[str, str, str], ...]  # (id, description, severity)
    warnings: tuple[tuple[str, str], ...]       # (id, description)
    validation_summary: tuple[dict[str, object], ...]  # validation command entries
    evidence_ledger_summary: tuple[dict[str, str], ...] # evidence rows
    files_read: tuple[str, ...]
    files_written: tuple[str, ...]
    boundary_confirmations: tuple[str, ...]
    checks: dict[str, str]                 # section-level pass/fail results
    artifact_hash: str                     # SHA256[:16] of artifact text
    artifact_line_count: int
    schema_version: str | None
```

### `VerdictDecision` (dataclass, frozen)

```python
@dataclasses.dataclass(frozen=True)
class VerdictDecision:
    next_action: str                       # "continue" | "continue_with_warning" | "stop" | "invalid"
    normalized_verdict: str
    has_blockers: bool
    reason_codes: tuple[str, ...]
    is_retry_candidate: bool               # true only if fixable blocker class
    retry_reason: str | None               # explanation if retry_candidate
    human_required: bool                   # true if safety boundary violation
    details: str | None
    parsed_artifact: ParsedReviewArtifact | None
```

### `parse_review_artifact()` function

```python
def parse_review_artifact(
    request: VerdictParserRequest,
) -> ParsedReviewArtifact | None:
```

Reads and parses a review artifact YAML file (or uses `artifact_text` if provided), extracting all fields deterministically. Uses `yaml.safe_load()` from the project's existing YAML dependency. Falls back to line-oriented parsing if YAML fails.

Returns `None` on file read failure.

### `decide_next_action()` function

```python
def decide_next_action(
    parsed: ParsedReviewArtifact,
) -> VerdictDecision:
```

## Normalized verdict model

### Plan-review normalization

| Raw verdict | Normalized |
|-------------|------------|
| `approve` | `pass` |
| `warning` | `warning` |
| `block` | `block` |
| anything else or missing | `invalid` |

### Precommit-review normalization

| Raw verdict | Normalized |
|-------------|------------|
| `pass` | `pass` |
| `warning` | `warning` |
| `block` | `block` |
| anything else or missing | `invalid` |

## Control action decision rules

| Condition | `next_action` | `is_retry_candidate` | `human_required` |
|-----------|---------------|---------------------|-------------------|
| Normalized `pass`, no blockers | `continue` | `False` | `False` |
| Normalized `warning`, no blockers | `continue_with_warning` | `False` | `False` |
| Normalized `block`, blockers exist, fixable class | `stop` | `True` | `False` |
| Normalized `block`, blockers exist, safety violation | `stop` | `False` | `True` |
| Any blockers present (regardless of verdict) | `stop` | `False` | `True` |
| Normalized `invalid` | `stop` | `False` | `False` |
| Artifact read failure | `stop` | `False` | `False` |
| Strict mode: review type mismatch | `stop` | `False` | `False` |
| Strict mode: PR ID mismatch | `stop` | `False` | `False` |

### Retry candidate rules

`is_retry_candidate = True` only when ALL of the following are true:
- Normalized verdict is `block`
- Blockers exist
- No blocker has severity `critical`
- No blocker contains text matching safety boundary violation patterns (git mutation, Docker, forbidden commands, hidden reasoning, provider/network calls)
- No safety boundary violation in `boundary_confirmations`
- No evidence of actual git/Docker/command execution in `evidence_ledger`

### Fixable blocker classes

Blockers are considered fixable when the `required_fix` field suggests prompt/scoping/validation adjustments. Examples:
- Missing evidence
- Incomplete validation
- Missing file read
- Placeholder text
- Scope drift

Blockers are NOT fixable when they involve:
- Actual git mutation
- Actual Docker invocation
- Actual command execution
- Hidden reasoning capture
- Provider/network call evidence

## Evidence extraction contract

The parser extracts from the review artifact:

| Field | YAML path | Extraction rule |
|-------|-----------|----------------|
| `schema_version` | `schema_version` | Direct read |
| `review_type` | `review_type` | Direct read |
| `pr_id` | `pr_id` | Direct read |
| `verdict` | `verdict` | Direct read |
| `blockers` | `blockers` | List of dicts; extract id, description, severity |
| `warnings` | `warnings` | List of dicts; extract id, description |
| `validation` | `validation` | List of dicts; extract command, result, exit_code, evidence |
| `evidence_ledger` | `evidence_ledger` | List of dicts; extract claim, evidence_source, result |
| `files_checked` | `files_checked` | List of strings |
| `files_modified` | `files_modified` | List of strings (inside context_used or top-level) |
| `boundary_confirmations` | `boundary_confirmations` | List of strings |
| `checks` | `checks` | Dict of section → result |
| `artifact_hash` | Computed | SHA256[:16] of artifact text |
| `artifact_line_count` | Computed | Line count of artifact text |

The parser uses `yaml.safe_load()` for parsing. Python's `yaml` module (PyYAML) is already available in the project environment. If YAML parsing fails, the parser falls back to line-oriented extraction for known top-level fields (`verdict`, `schema_version`, `review_type`, `pr_id`, and minimal array headers for `blockers` and `warnings`).

## Safety and mutation boundaries

The parser must not:
- Execute commands from artifacts
- Trust artifact prose as proof without fields
- Mutate files
- Call agents
- Invoke Docker
- Install dependencies
- Perform git mutation
- Create PRs
- Create `.ariadne/runs/`
- Import or call `agent_runner_bridge`
- Import or call `prompt_composer`

The parser must treat safety boundary violations as `stop` with `human_required=True`.

## Non-goals

PR 0126 does not implement:
- Agent execution or Docker execution (PR 0124)
- Prompt composition (PR 0125)
- Full four-agent pipeline runner (PR 0127)
- Retry execution or automatic prompt refinement (PR 0132)
- Git boundary (PR 0128)
- `ariadne task` CLI (PR 0129)
- Run persistence in `.ariadne/runs/` (PR 0130)
- Model health live fallback (PR 0133)
- Run report (PR 0134)
- Parallel-safe queue (PR 0135)
- Decision Core / GRM, Context Warehouse, eval harness, faithfulness audit, frontend, new product-iteration surface features (frozen until PR 0136)

## Proposed implementation files

| File | Action |
|------|--------|
| `services/runner/src/runner/verdict_parser.py` | NEW |
| `services/runner/tests/test_verdict_parser.py` | NEW |

Default — not modified:
- `services/runner/src/runner/agent_runner_bridge.py` — NOT modified
- `services/runner/src/runner/prompt_composer.py` — NOT modified
- `services/runner/src/runner/docker_agent_adapter.py` — NOT modified
- `services/runner/src/runner/proof_capture.py` — NOT modified
- `services/runner/src/runner/handoff_packet.py` — NOT modified
- `services/runner/src/runner/acceptance_criteria.py` — NOT modified
- `services/runner/src/runner/gate_evidence.py` — NOT modified
- `agents/*.yml` — NOT modified
- `ROADMAP.md`, `docs/**` — NOT modified

## Forbidden files

- `services/task_intake/**` — out of scope for Production Line
- Any file under `.project-memory/pr/0115-*/` through `.project-memory/pr/0125-*/`
- `ROADMAP.md`, `docs/`, `schemas/`, `agents/`
- `.project-memory/post-0100/`
- `pyproject.toml`, `package.json`, `Makefile`

## Implementation steps

1. Create `verdict_parser.py` with:
   - `VerdictParserRequest`, `ParsedReviewArtifact`, `VerdictDecision`, `VerdictDecisionStatus`
   - `parse_review_artifact()` — YAML parse + fallback + field extraction
   - `decide_next_action()` — deterministic decision rules
   - `_normalize_verdict()` — raw → normalized mapping
   - `_check_retry_candidate()` — retry viability check
   - Stable reason codes for: `artifact_read_failure`, `yaml_parse_failure`, `missing_verdict`, `unknown_verdict`, `strict_type_mismatch`, `strict_pr_mismatch`, `blocker_safety_violation`

2. Create `test_verdict_parser.py` with focused tests (see test plan below).

## Test plan

| Class | Focus |
|-------|-------|
| `TestPlanReviewApprove` | Parse plan-review approve → pass → continue, no blockers |
| `TestPlanReviewWarning` | Parse plan-review warning → warning → continue_with_warning |
| `TestPlanReviewBlock` | Parse plan-review block → block → stop |
| `TestPrecommitPass` | Parse precommit pass → pass → continue |
| `TestPrecommitWarning` | Parse precommit warning → warning → continue_with_warning |
| `TestPrecommitBlock` | Parse precommit block → block → stop |
| `TestBlockersForceStop` | Blockers present even with pass verdict → stop, human_required=True |
| `TestMissingVerdict` | No verdict field → invalid → stop |
| `TestUnknownVerdict` | Unknown verdict string → invalid → stop |
| `TestArtifactReadFailure` | Nonexistent path → stop with artifact_read_failure |
| `TestStrictTypeMismatch` | expected_review_type mismatch → stop |
| `TestStrictPrMismatch` | expected_pr_id mismatch → stop |
| `TestArtifactHashStable` | Same artifact → same SHA256[:16] hash |
| `TestArtifactLineCount` | Line count recorded correctly |
| `TestBlockersExtraction` | Multiple blockers → all extracted with id/description/severity |
| `TestWarningsExtraction` | Multiple warnings → all extracted |
| `TestValidationSummary` | Validation commands extracted with result/exit_code/evidence |
| `TestEvidenceLedgerExtraction` | Evidence rows extracted |
| `TestFilesReadExtraction` | Files read list extracted |
| `TestFilesWrittenExtraction` | Files written list extracted |
| `TestBoundaryConfirmations` | Boundary confirmations extracted |
| `TestChecksExtraction` | Checks dict extracted (precommit artifacts) |
| `TestRetryCandidateFixable` | Fixable blocker → is_retry_candidate=True |
| `TestRetryCandidateSafetyViolation` | Safety violation → is_retry_candidate=False, human_required=True |
| `TestRetryCandidateCriticalSeverity` | Critical severity blocker → is_retry_candidate=False |
| `TestRetryCandidateGitMutation` | Blocker references git mutation → is_retry_candidate=False |
| `TestYamlParseFallback` | Invalid YAML → fallback line parsing for basic fields |
| `TestNoCommandExecution` | No subprocess.run, os.system, docker, git commands |
| `TestNoAgentImport` | No import of agent_runner_bridge or prompt_composer |
| `TestDeterministicRepeats` | Same input → same output |
| `TestNoAriadneResidue` | Uses tmp_path, no `.ariadne/` residue |
| `TestProductName` | Module docstring contains "Ariadne" |
| `TestNoForbiddenNames` | No forbidden legacy names |

## Validation commands

```bash
python -m compileall -f services/runner/src services/task_intake/src

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_verdict_parser.py -q

PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest \
  services/runner/tests/test_verdict_parser.py \
  services/runner/tests/test_prompt_composer.py \
  services/runner/tests/test_agent_runner_bridge.py \
  services/runner/tests/test_docker_agent_adapter.py \
  -q

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "VerdictParser|verdict_parser|parse_review_artifact|decide_next_action|normalized_verdict|retry_candidate|continue_with_warning|artifact_hash" services/runner/src services/runner/tests .project-memory/pr/0126-verdict-parser 2>/dev/null || true

grep -R -n -E --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "subprocess.run|docker compose|docker run|gh pr create|git push|git commit|git add|pip install|python -m pip install" services/runner/src/runner/verdict_parser.py services/runner/tests/test_verdict_parser.py 2>/dev/null || true

if [ -d .ariadne ]; then find .ariadne -maxdepth 5 -type f | sort; else echo ".ariadne absent"; fi

git status --short
git diff --name-only
```

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `verdict_parser.py` (new), `test_verdict_parser.py` (new)
- **behavior drift**: `parse_review_artifact()` + `decide_next_action()` only; no agent execution, no Docker, no prompt composition
- **parser API drift**: input/output shapes match the PLAN.md definitions
- **normalized verdict drift**: raw→normalized mapping correct for both review types
- **control action drift**: continue/stop/retry-candidate rules match PLAN.md
- **retry boundary drift**: `is_retry_candidate` only true for fixable blocker class; false for safety/git/Docker violations
- **evidence extraction drift**: all fields extracted (blockers, warnings, validation, evidence_ledger, etc.)
- **bridge/composer drift**: `agent_runner_bridge.py` and `prompt_composer.py` NOT modified
- **git mutation drift**: no git commands in parser code
- **validation drift**: all validation commands run; exit codes recorded
- **semantic drift**: no non-semantic placeholders; product name is "Ariadne"
- **future-scope drift**: no full pipeline, no git boundary, no CLI, no retry execution
- **dirty-tree residue drift**: no `.ariadne/` residue after validation

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- third executable Production Line PR after PR 0125 ✓
- parses plan-review and precommit-review artifacts ✓
- extracts verdict, blockers, warnings, evidence, fields ✓
- produces continue/stop/retry-candidate decisions ✓
- retry is recommendation only, not execution ✓
- no agent execution, no Docker invocation ✓
- no prompt composition ✓
- no full four-agent pipeline ✓
- no git boundary / ariadne task CLI / run persistence ✓
- no frozen stream capability started ✓
- no `.ariadne/` residue after validation ✓

## Dirty-Tree Expectations

During development, `tmp_path` is used for all test store directories. The post-validation `git status --short` and `find .ariadne` must confirm no residue.

## Artifact Write / Readback Requirements

The implementation precommit-review artifact must:
1. Record full validation output (command strings, exit codes, output snippets)
2. Read back the artifact after writing
3. Verify the artifact is listed by `find` and `test -f` exits 0
4. Not claim pass with validation skipped

## Stop conditions

- Block if current branch is not `0126-verdict-parser`
- Block if PR 0123 Production Line roadmap evidence is missing from ROADMAP.md — PASS: confirmed
- Block if PR 0124 `agent_runner_bridge.py` is missing — PASS: present
- Block if PR 0125 `prompt_composer.py` is missing — PASS: present
- Block if review artifact schema is missing and no conservative parser fallback is planned — PASS: schema present, but fallback planned
- Block if the plan is docs-only or schemas-only — PASS: executable-first
- Block if the plan modifies ROADMAP.md — PASS: not planned
- Block if the plan modifies agent configs — PASS: not planned
- Block if the plan runs agents — PASS: no agent execution
- Block if the plan invokes Docker — PASS: explicit prohibition
- Block if the plan executes commands found inside review artifacts — PASS: parser does not execute
- Block if the plan grants unattended git mutation rights — PASS: explicitly prohibited
- Block if parser treats raw agent output as evidence — PASS: reads structured YAML artifact
- Block if parser does not extract verdict/blockers/warnings/evidence — PASS: all extracted
- Block if parser cannot produce continue/stop/retry-candidate decisions — PASS: deterministic rules
- Block if parser executes retry or edits prompts — PASS: recommendation only
- Block if the plan implements the full four-agent pipeline — PASS: deferred to PR 0127
- Block if the plan implements prompt composition, git boundary, PR creation, `ariadne task` CLI, or run persistence — PASS: all deferred
- Block if the plan starts frozen streams before PR 0136 acceptance — PASS: none started
- Block if validation plan is incomplete — PASS: complete
- Block if artifact write/readback expectations are missing — PASS: included

## Implementation note

PR 0034 implemented:
- Extended `services/model_gateway/src/model_gateway/model_selection_dry_run.py` with a simplified CLI mode (detected via `--context-stress` flag) that accepts `--role`, `--task-type`, `--context-stress`, `--failure-mode`, `--cost-sensitivity`, and `--verification` arguments
- Created `services/model_gateway/tests/test_model_selection_dry_run_cli.py` with tests for happy path, invalid args, deterministic output, and no-side-effect guarantees
- Updated `services/model_gateway/README.md` with simplified CLI smoke section and expected output shape

The existing detailed CLI from PR 0033 is preserved unchanged. Mode detection is automatic based on whether `--context-stress` is present. No provider calls, no network, no API keys, no runner invocation, no `.ariadne/**` writes, no `run_record.yml`.# PR 0034: Model Selection Dry-Run CLI/README Smoke

## Goal

Add a CLI/demo path for the deterministic model-selection dry-run.

## Context snapshot

```yaml
context_snapshot:
  base_sha: "96dc84ca07cd0b5b84e802d231075a6b6b15914b"
  base_sha_source: "git rev-parse --verify HEAD at PLAN creation time"
  index_version: "0.12"
  index_version_source: ".project-memory/memory_index.yml"
  current_head: "96dc84ca07cd0b5b84e802d231075a6b6b15914b"
  stale_snapshot: false
  snapshot_verified: true
  snapshot_verified_by: "git introspection"
```

## Snapshot policy

```text
PLAN.md base_sha is historical evidence from PLAN creation time.
Implementation and review should report snapshot deltas but must not block
solely because current HEAD differs from PLAN.md base_sha, unless scope
evidence shows unrelated or forbidden changes.
```

## Non-goals

```text
- no live LLM calls
- no provider SDK imports
- no network calls
- no API keys
- no secrets
- no production model routing
- no runner invocation
- no runner request creation
- no agent orchestration
- no task execution
- no run_id creation
- no run_record.yml creation
- no .ariadne/** writes
- no project-memory schema/contract changes
- no memory_index bump
- no Docker/workflow/root dependency changes
```

## Required CLI behavior

The CLI must:

- use stdlib only
- parse arguments with `argparse`
- call existing deterministic dry-run logic from PR 0033
- print a readable decision record
- support a `--json` flag if simple and justified
- return exit code 0 on valid input
- return non-zero on invalid/missing required input
- not call live providers
- not perform network calls
- not call subprocess/git/docker
- not mutate repository state

### Specific CLI arguments to add or expose

PR 0033 already defines the detailed ModelSelectionResult CLI with `--role`, `--risk-level`, context stress fields, and reviewer model separation.

PR 0034 should add a simplified smoke/demo interface with arguments that are more intuitive for demonstration:

```text
--role              (string: coder | architect | reviewer | ui | backend | dataset)
--task-type         (string: description of the task)
--context-stress    (low | medium | high)
--failure-mode      (string: optional, known failure mode)
--cost-sensitivity  (low | medium | high)
--verification      (none | recommended | required)
```

This simplified interface should produce a `ModelSelectionResult`-compatible output by mapping these fields to the PR 0033 dry-run internals.

Relationship to PR 0033 module:

- PR 0034 may extend the existing `model_selection_dry_run.py` with a second CLI mode, or
- PR 0034 may create a separate `smoke.py` module that wraps the dry-run logic

The PLAN recommends extending the existing module and avoiding a separate file unless the module becomes too large.

## Required tests

Create a new test file or add to the existing test:

```text
services/model_gateway/tests/test_model_selection_dry_run_cli.py
```

Tests must cover:

- CLI happy path with simplified args
- invalid/missing args
- deterministic output
- JSON output if implemented
- no provider imports
- no network calls
- no subprocess/git/docker
- no runner import/invocation
- no `.ariadne/**`
- no `run_record.yml`

## README update

README must include:

- CLI command example with simplified args
- expected output shape
- dry-run-only boundary
- no API key required
- no live provider call
- no network call
- no runner/task execution
- relation to PR 0033 decision record

## Validation

Future implementation must run:

```bash
PYTHONPATH=services/model_gateway/src python -m pytest services/model_gateway/tests -q
python -m pytest -q
python -m compileall -f services packages
PYTHONPATH=services/runner/src python -m runner doctor
PYTHONPATH=services/model_gateway/src python -m model_gateway.model_selection_dry_run --help
PYTHONPATH=services/model_gateway/src python -m model_gateway.model_selection_dry_run \
  --role coder \
  --task-type "long-context-code-review" \
  --context-stress high \
  --failure-mode "hallucinated-diff" \
  --cost-sensitivity medium \
  --verification required
grep -R -n "openai\|anthropic\|gemini\|requests\|httpx\|urllib\|aiohttp\|socket\|subprocess\|docker\|git \|run_record.yml\|\.ariadne" services/model_gateway/src/model_gateway services/model_gateway/tests services/model_gateway/README.md || true
```

Expected:

- model_gateway tests pass
- full pytest passes
- compileall passes
- runner doctor passes
- CLI help works
- CLI sample works
- forbidden/live-execution grep has no actionable matches except tests/README asserting forbidden behavior

## Relationship to PR 0033

```text
PR 0033 introduced deterministic dry-run decision record logic.
PR 0034 exposes that logic through a reproducible CLI/demo path.

PR 0034 does not change model-selection methodology.
PR 0034 does not add runtime routing.
PR 0034 does not call models.
PR 0034 only makes the dry-run visible and repeatable.
```

## Machine-checkable acceptance criteria

```text
cli_entrypoint: python -m model_gateway.model_selection_dry_run
argparse_cli: required
human_readable_output: required
nonzero_on_invalid_input: required
deterministic_output: required
json_output: optional
stdlib_only: required
provider_sdk_imports: forbidden
network_calls: forbidden
api_keys: forbidden
secrets: forbidden
production_routing: forbidden
runner_invocation: forbidden
task_execution: forbidden
run_record_creation: forbidden
ariadne_writes: forbidden
project_memory_schema_changes: forbidden
memory_index_changes: forbidden
docker_workflow_changes: forbidden
root_dependency_changes: forbidden
```

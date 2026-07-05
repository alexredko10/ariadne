# PR 0123 — Production Line Roadmap Realignment Plan

## Summary

Plan a roadmap realignment PR that locks in the completed Product Iteration substrate stream (PRs 0117–0122) and replaces the post-0122 direction with a hard, product-oriented Production Line roadmap targeting a working `ariadne task "description"` → full 4-agent cycle → PR output. Dogfooding (PR 0131) is the acceptance milestone. This is a bridge/realignment PR — docs/roadmap-only — that also defines the next executable PR (PR 0124 Agent Runner Bridge).

## Context snapshot

| Field | Value |
|-------|-------|
| current_head | 5a37663a763e8f3d8caa7cce00c7e2663a73cf9e |
| current_branch | 0123-production-line-roadmap-realignment |
| git_status_short | clean |
| pr_0122_status_evidence | PLAN.md + plan-review.yml + precommit-review.yml (verdict: pass) all present |
| docker_agent_adapter_evidence | `services/runner/src/runner/docker_agent_adapter.py` present |
| adr_0008_status | MISSING (not present as docs/adr/0008-pr-batching-scope-discipline.md) |
| post-0100_manifest_status | PRESENT at .project-memory/post-0100/strategic-direction/agent-manifest.md |
| project_contract_status | PRESENT at .project-memory/project_contract.yml |
| .ariadne/ residue | absent |

## Roadmap alignment

* roadmap track: Production Line (new stream, locked in by this PR)
* expected PR slot: 0123 — Production Line Roadmap Realignment
* why this PR is next: ROADMAP.md does not contain the completed PR 0117–0122 Product Iteration stream; ADR 0011 requires ROADMAP sync before further feature PRs; the post-0122 direction is replaced with a product-first line
* bridge PR declaration: yes — docs/roadmap-only, next executable PR is 0124 Agent Runner Bridge, defined below
* anti-committee-mode check: this is the single allowed bridge PR; PRs 0124+ are all executable-first

## Current ROADMAP drift diagnosis

- ROADMAP.md currently does NOT officially contain the completed PR 0117–0122 Product Iteration substrate stream.
- ADR 0011 requires ROADMAP.md to stay in sync with actual PR sequence.
- Continuing feature PRs before roadmap sync would violate roadmap discipline.
- PR 0123 is therefore a bridge/realignment PR, not a feature PR.
- This bridge is allowed once only because it defines the next executable PR.
- PR 0124+ must be executable-first.

## PR 0117–0122 Product Iteration Substrate Stream completion record

The following PRs have been completed and validated with precommit-review evidence:

| PR | Title | Status |
|----|-------|--------|
| 0117 | Product Iteration Signal Contract / Local Screen-Time Record | precommit pass ✓ |
| 0119 | Product Iteration Session Capture Surface | precommit pass ✓ |
| 0120 | Product Iteration Evidence Summary | precommit pass ✓ |
| 0121 | Product Iteration Recommendation Candidate | precommit pass ✓ |
| 0122 | Product Iteration Human Review Packet | precommit pass ✓ |

Stream status: closed. Not a reopened Local Interaction UX Track.
Architect sign-off reference: `экран тайм, product, итерации.`

## Production Line Stream proposal

### Stage 1 — Orchestrator (PR 0123–0127)

```
0123 — production line roadmap realignment (this PR, bridge)
0124 — Agent Runner Bridge: run a docker agent from Ariadne code via
       docker_agent_adapter with a real agents/*.yml config;
       input agent_name + task_prompt, output captured artifact
0125 — Prompt Composer: generate planner/plan-review/coder/precommit
       task prompts from templates + PR context
0126 — Verdict Parser: parse review artifacts, extract verdict/blockers,
       decide continue/stop/retry
0127 — Pipeline Runner: planner → plan-review → gate → coder →
       precommit → gate; one call, full cycle, stop on block
```

### Stage 2 — Closed loop (PR 0128–0131)

```
0128 — Git Boundary: commit/push/PR creation only after explicit
       human approve; the single git-mutation surface in the substrate
0129 — ariadne task CLI: `ariadne task "description"` → full cycle → PR link
0130 — Run Persistence: run state/artifacts/proofs in .ariadne/runs/
0131 — DOGFOOD MILESTONE: PR 0131 is created by Ariadne itself
       via ariadne task
```

### Stage 3 — Production hardening (PR 0132–0136)

```
0132 — Failure Recovery: retry with refined prompt on block, max 2,
       then human escalation
0133 — Model Health live: block/violation counters per model,
       automatic fallback model switch
0134 — Run Report: single markdown per cycle (actions, evidence,
       cost, time)
0135 — Parallel-safe runs: branch lock, task queue
0136 — Acceptance: 10 consecutive real tasks via ariadne task with
       recorded metrics (success rate, cost, human interventions)
```

### Stage 4 — Public (PR 0137+)

```
0137+ — README/quickstart, GitHub release v0.1, demo. Post-0100
        capability streams (Decision Core, Context Warehouse, eval
        harness, faithfulness audit, frontend) queue AFTER the
        dogfood milestone.
```

## Frozen until PR 0136 acceptance

The following capability streams are frozen until the Production Line reaches PR 0136 acceptance:

- Decision Core / GRM
- Context Warehouse Bronze/Silver/Gold
- Eval harness / benchmarks
- Faithfulness audit
- Frontend
- New product-iteration surface features

All remain in the post-0100 manifest; their queue position is after the dogfood milestone.

## PR 0124 Agent Runner Bridge definition

| Field | Definition |
|-------|------------|
| PR number | 0124 |
| Name | Agent Runner Bridge |
| Branch | `0124-agent-runner-bridge` |
| Purpose | Run a Docker agent from Ariadne code via `docker_agent_adapter` with a real `agents/*.yml` config |
| Input | `agent_name` + `task_prompt` |
| Output | Captured artifact (proof capture) |
| Proof principle | Agent output is not evidence. Runtime-captured proof is evidence. |
| Must use | Existing runner substrate where possible (`docker_agent_adapter.py`, `proof_capture.py`, `handoff_packet.py`, `acceptance_criteria.py`, `gate_evidence.py`) |
| Must not | Grant agents unattended git mutation rights |
| Must not | Run the full four-agent pipeline yet |
| Must produce | Proof capture suitable for PR 0125/0126/0127 |
| Must be | Executable-first, not docs-only |
| Feasibility | `docker_agent_adapter.py` exists with `run_docker_agent_execution(agent_name, task_prompt, allow_docker=True)` signature |

## Decision on ADR 0012

**Decision: ROADMAP.md only.** No ADR 0012.

Rationale:
- ADR 0011 is the controlling roadmap-discipline authority. It requires ROADMAP.md to stay in sync with the actual PR sequence.
- A separate ADR for the Production Line stream would add document overhead without changing the behavioral contract.
- The Production Line is a roadmap stream replacement, not an architecture principle change.
- Keeping the bridge PR minimal prevents committee-mode drift.

Block if:
- PR 0123 becomes ADR-only.
- PR 0123 does not make ROADMAP.md the primary coder write target.
- PR 0123 fails to define PR 0124 Agent Runner Bridge as the next executable PR.

## Future coder write paths

The coder implementation is restricted to:

- `ROADMAP.md` — primary target; add Product Iteration Substrate Stream (completed) and Production Line Stream definitions
- `docs/adr/0012-production-line-stream.md` — only if PLAN.md explicitly justifies it (current decision: no)
- `.project-memory/pr/0123-production-line-roadmap-realignment/reviews/precommit-review.yml` — by precommit-review only

No runtime code. No tests. No service changes. No agent config changes. No schema changes.

## Content the coder must apply to ROADMAP.md

### 1. Product Iteration Substrate Stream — mark completed

```text
0117 — signal store contract        [completed]
0119 — session capture surface      [completed]
0120 — evidence summary             [completed]
0121 — recommendation candidate     [completed]
0122 — human review packet          [completed]
Stream status: closed. Not a reopened Local Interaction UX Track.
Architect sign-off reference: "экран тайм, product, итерации."
```

### 2. Production Line Stream — new active stream

```text
Stage 1 — Orchestrator (0123-0127):
0123 — production line roadmap realignment (this PR, bridge)
0124 — Agent Runner Bridge: run a docker agent from Ariadne code via
       docker_agent_adapter with a real agents/*.yml config;
       input agent_name + task_prompt, output captured artifact
0125 — Prompt Composer: generate planner/plan-review/coder/precommit
       task prompts from templates + PR context
0126 — Verdict Parser: parse review artifacts, extract verdict/blockers,
       decide continue/stop/retry
0127 — Pipeline Runner: planner → plan-review → gate → coder →
       precommit → gate; one call, full cycle, stop on block

Stage 2 — Closed loop (0128-0131):
0128 — Git Boundary: commit/push/PR creation only after explicit
       human approve; the single git-mutation surface in the substrate
0129 — ariadne task CLI: `ariadne task "description"` → full cycle → PR link
0130 — Run Persistence: run state/artifacts/proofs in .ariadne/runs/
0131 — DOGFOOD MILESTONE: PR 0131 is created by Ariadne itself
       via ariadne task

Stage 3 — Production hardening (0132-0136):
0132 — Failure Recovery: retry with refined prompt on block, max 2,
       then human escalation
0133 — Model Health live: block/violation counters per model,
       automatic fallback model switch
0134 — Run Report: single markdown per cycle (actions, evidence,
       cost, time)
0135 — Parallel-safe runs: branch lock, task queue
0136 — Acceptance: 10 consecutive real tasks via ariadne task with
       recorded metrics (success rate, cost, human interventions)

Stage 4 — Public (0137+):
0137+ — README/quickstart, GitHub release v0.1, demo. Post-0100
        capability streams (Decision Core, Context Warehouse, eval
        harness, faithfulness audit, frontend) queue AFTER the
        dogfood milestone.
```

### 3. Frozen-until-PR-0136 list

```text
Frozen until PR 0136 acceptance:
- Decision Core / GRM
- Context Warehouse Bronze/Silver/Gold
- Eval harness / benchmarks
- Faithfulness audit
- Frontend
- New product-iteration surface features

All remain in the post-0100 manifest; their queue position is
after the dogfood milestone.
```

### 4. Stop conditions for the stream

```text
Stream stop conditions:
- any PR 0124+ that is docs-only/schemas-only → block
- any PR that gives agents unattended git mutation rights → block
- any PR that adds a capability stream before 0136 acceptance → block
```

## Validation strategy

The coder/precommit-review must validate:

- grep confirms Product Iteration Substrate Stream exists in ROADMAP.md
- grep confirms PR 0117–0122 are marked completed
- grep confirms Production Line Stream exists
- grep confirms PR 0124 Agent Runner Bridge exists
- grep confirms DOGFOOD MILESTONE exists
- grep confirms frozen-until-0136 list exists
- grep confirms stop conditions exist
- `python -m compileall` is NOT required because PR 0123 has no code changes
- `git status --short` shows only ROADMAP.md changed, plus precommit-review artifact

## PLAN DRIFT GATE

The implementation precommit-review must check:

- **file drift**: only `ROADMAP.md` modified; no runtime/test/service/agent/config changes
- **behavior drift**: no runtime behavior changes
- **bridge scope drift**: ROADMAP.md is primary target; ADR 0012 not created unless explicitly justified
- **PR 0124 definition drift**: PR 0124 Agent Runner Bridge defined as the next executable PR with name, branch, purpose, input, output, constraints
- **PR 0117–0122 completion drift**: all 5 Product Iteration PRs listed as completed
- **frozen-stream drift**: no frozen capability stream started before PR 0136
- **roadmap discipline drift**: ADR 0011 Roadmap Alignment Gate satisfied

## NO-DRIFT CHECK

The implementation precommit-review must confirm:

- roadmap realignment only ✓
- no runtime code changes ✓
- no test changes ✓
- no service changes ✓
- no agent config changes ✓
- no schema changes ✓
- PR 0124 defined as next executable PR ✓
- PR 0117–0122 marked completed ✓
- Production Line Stream defined with 4 stages ✓
- DOGFOOD MILESTONE at PR 0131 ✓
- Frozen streams listed ✓
- Stop conditions listed ✓

## Dirty-Tree Expectations

The working tree will contain:
- `ROADMAP.md` — modified by coder
- `.project-memory/pr/0123-production-line-roadmap-realignment/reviews/precommit-review.yml` — written by precommit-review

No `.ariadne/` residue.

## Artifact Write / Readback Requirements

The implementation precommit-review artifact must:
1. Record fresh validation grep outputs confirming all required ROADMAP.md sections
2. Read back the artifact after writing
3. Verify the artifact is listed by `find` and `test -f` exits 0
4. Not claim pass with validation skipped

## Stop conditions

- Block if current branch is not `0123-production-line-roadmap-realignment`
- Block if PR 0122 completion evidence is missing — PASS: all artifacts present
- Block if ROADMAP.md already contains a conflicting active stream definition for 0123+ — to be checked by coder
- Block if PLAN.md would require runtime code changes — PASS: docs/roadmap only
- Block if PLAN.md would require test changes — PASS: no code changes
- Block if PLAN.md would modify ROADMAP.md during planning — PASS: coder modifies ROADMAP.md, not planner
- Block if PR 0123 becomes ADR-only or committee-mode — PASS: ROADMAP.md is primary target
- Block if ROADMAP.md is not the primary coder write target — PASS: ROADMAP.md listed as primary
- Block if next executable PR 0124 Agent Runner Bridge is not defined — PASS: defined with full specification
- Block if PR 0124 cannot be defined from current repository state because docker_agent_adapter.py is missing — PASS: `docker_agent_adapter.py` present
- Block if PLAN.md starts Decision Core / GRM, Context Warehouse, eval harness, faithfulness audit, frontend, or new product-iteration surface features before PR 0136 acceptance — PASS: frozen until 0136
- Block if PLAN.md allows any PR 0124+ docs-only/schemas-only PR — PASS: explicitly blocked
- Block if PLAN.md allows unattended git mutation rights for agents — PASS: PR 0128 defines git boundary with explicit human approve
- Block if PLAN.md allows a capability stream before PR 0136 acceptance — PASS: frozen list defined

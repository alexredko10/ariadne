# Ariadne Post-0100 Strategic Direction Manifest

Purpose: paste this document into the new Ariadne chat window to align the agent with the next strategic wave after PR/commit 0100.

Project: Ariadne  
Core thesis: **The model is replaceable. The substrate is the product.**  
Secondary formula: **Agent output is not evidence. Runtime-captured proof is evidence. Агент может быть исполнителем, но не нотариусом собственной работы.**

---

## 1. Immediate instruction to the new agent

You are now working on Ariadne after the execution-substrate track has reached PR/commit 0100 or later.

Your job is not to invent a new project and not to clone any external project. Your job is to preserve the Ariadne workflow and redirect the post-0100 program into the next major capability wave:

1. Proof-First Runtime
2. Decision Core / GRM-style hypothesis evaluation
3. Context Layer: Bronze / Silver / Gold
4. Model Health Monitor + Model Replaceability
5. External Capability Integration from selected sources

This strategic wave must remain executable-first. Do not regress to committee mode.

If Ariadne has not reached PR/commit 0100 yet, stop and continue the pre-0100 execution-substrate roadmap unchanged.

---

## 2. Identity and non-negotiables

Ariadne is an execution substrate for agentic software production.

The product is not a model wrapper. The product is the durable substrate around planning, execution, proof capture, review, context, routing, and safe continuation across models.

Never call the project GRACE in prompts, code, docs, PR bodies, or artifacts.

Never introduce these legacy names or examples:

```text
.grace/**
@grace-*
water_meter
water-meter
Broken Clock
broken_clock
daily-consumption
old Flask
```

The model may generate. The runtime must verify.

Agent output is not proof. Review summaries are not proof. Runtime-captured command output, tied to state and acceptance criteria, is proof.

---

## 3. The existing Ariadne workflow must stay intact

The new strategic direction does not replace the workflow. It builds on it.

Ariadne PRs continue to use two gate pairs.

### Phase A — planning gate

When the user asks for “два промпта” for a new PR, return exactly:

1. Prompt 1 — planner
2. Prompt 2 — plan-review

The planner writes only:

```text
.project-memory/pr/<PR-ID-slug>/PLAN.md
```

The plan-review agent writes only:

```text
.project-memory/pr/<PR-ID-slug>/reviews/plan-review.yml
```

After `plan-review: approve` or acceptable `warning`, the human commits the planning artifacts.

### Phase B — implementation gate

After plan-review is approved and the user asks for the next prompts, return exactly:

1. Prompt 1 — implementation
2. Prompt 2 — precommit-review

The implementation agent modifies only exact implementation/test files approved by PLAN.md.

The precommit-review agent writes only:

```text
.project-memory/pr/<PR-ID-slug>/reviews/precommit-review.yml
```

After `precommit-review: pass`, the human commits implementation files plus the precommit artifact, pushes, and creates the GitHub PR.

### Phase C — PR creation

When the user asks for the PR description after precommit pass, provide:

- exact commit scope
- commit command
- PR title
- short PR body
- `gh pr create` command

PR body must stay short and use only:

```markdown
## Summary
## Changed
## Behavior
## Validation
## Next step
```

Always include GitHub reviewer/assignees:

```bash
--reviewer zablose \
--assignee zablose \
--assignee alexredko10
```

---

## 4. Prompt creation rules

Every reusable prompt must be in a writing block:

```text
:::writing{variant="standard" id="<stable-id>"}
...
:::
```

PR bodies use:

```text
:::writing{variant="document" id="<stable-id>"}
...
:::
```

Return no more than three writing blocks in one assistant response.

Prompts must include:

- Task
- Agent
- Mode
- Branch
- Goal
- Required reads
- Allowed write paths
- Forbidden write paths
- Allowed commands
- Forbidden commands
- Token-efficiency discipline
- Requirements
- Validation commands
- Stop conditions
- Final output format
- Boundary confirmations

Do not bloat prompts with project history when the current PLAN.md or prior artifacts already carry the contract.

Implementation/precommit prompts should say:

```text
Use .project-memory/pr/<PR-ID-slug>/PLAN.md as the full implementation contract.
```

---

## 5. Source-of-truth lookup discipline

Do not perform broad repository discovery first.

For normal PR prompts after PR 0100, agents should start from:

```text
.project-memory/context-bundles/contracts.yml
.project-memory/memory_index.yml if contracts.yml is insufficient
.project-memory/project_contract.yml if scope is unclear
current PR PLAN.md
current PR approved review artifacts
previous directly relevant PR artifacts
exact files named by PLAN.md or prompt
```

For the post-0100 unified strategic planning task, the strategic-planner should start from:

```text
.project-memory/memory_index.yml
.project-memory/project_contract.yml
.project-memory/context-bundles/contracts.yml
.project-memory/anchors.yml
ARIADNE_ARCHITECTURE.md
ROADMAP.md if present
.project-memory/pr/**/PLAN.md for PRs 0063 through current
schemas/** existing schemas
docs/adr/** existing ADRs
services/** only after source-of-truth artifacts indicate relevant paths
```

Do not narrate lookup. Do not say “I will inspect the repo.” Do not restate project history. Output only the requested final format.

---

## 6. Commands policy for agents

Allowed read-only commands, only when needed:

```text
git rev-parse --verify HEAD
git status --short
git diff --name-only
git diff -- <explicit paths>
find <explicit parent> -maxdepth ... -type f | sort
grep -R -n "<pattern>" <explicit paths> || true
date -u +%Y-%m-%dT%H:%M:%SZ
```

Forbidden commands inside all agent prompts:

```text
git add
git commit
git push
git reset
git checkout
git switch
git merge
git rebase
git clean
git log
git tag
gh release
docker
docker compose
rm
mv
sudo
chmod
chown
pip install
python -m pip install
```

The assistant may give the human git commands after review passes. Agents must not run mutation commands.

---

## 7. Review artifact integrity rules

Ariadne now has three permanent review-process invariants.

### 7.1 Diff completeness

Current diff files must be read by the reviewer.

If `git diff --name-only` or the branch diff includes a file, that file must appear in FILES READ unless it is an explicitly named intentionally ignored dirty file.

Unspecified ignored files are blockers.

### 7.2 Validation completeness

A precommit artifact cannot claim `pass` if required validation was skipped or not run.

If an artifact is rewritten for correction, it must either preserve actual validation evidence or rerun full validation and record it.

Do not accept an “artifact-only pass” when implementation validation is required.

### 7.3 Evidence completeness

Not listed in FILES READ = not observed = cannot be claimed.

Any artifact may only claim schema validation, roadmap alignment, prior-gate validation, contract preservation, source-string safety, or release readiness if the exact supporting files appear in FILES READ.

For release/freeze gates, missing prior-gate evidence is a blocker, not a warning.

For a prior PR gate confirmation, FILES READ must include both:

```text
.project-memory/pr/<prior-pr>/PLAN.md
.project-memory/pr/<prior-pr>/reviews/precommit-review.yml
```

Never write confirmations implying a file was read unless it appears in FILES READ.

---

## 8. Anti-committee-mode policy

Committee mode means:

```text
standalone docs PRs with no executable follow-up
schemas not driving code/tests immediately
ADRs not tied to implementation gates
plans deferring all execution indefinitely
review artifacts substituting for behavior
architecture essays without runnable modules
```

Block plans that are docs-only or schemas-only unless they are explicitly short bridge PRs immediately followed by code PRs.

Every normal post-0100 PR must include at least one executable behavior item:

```text
Python implementation file
test file
runner adapter behavior
evaluator behavior
API endpoint or CLI command
deterministic fixture generator
executable validation behavior
```

The first 10 PRs after 0100 must be executable code PRs.

---

## 9. Current strategic pivot after PR 0100

The uploaded strategic direction requires a unified post-0100 implementation roadmap integrating five streams:

```text
Stream 1: Proof-First Runtime
Stream 2: Decision Core / GRM Hypothesis Evaluation
Stream 3: Context Layer (Bronze/Silver/Gold)
Stream 4: Model Health Monitor + Model Replaceability
Stream 5: External Capability Integration
```

This must not become a research report. It must not become a vague inspiration document. It must produce concrete PRs, expected files, tests, validation commands, non-goals, and dependencies.

The strategic-planner task writes only:

```text
.project-memory/post-0100/unified-strategic-plan/PLAN.md
```

Optional:

```text
.project-memory/post-0100/unified-strategic-plan/source-map.yml
```

It must not write implementation files, schemas, docs outside the allowed planning directory, or modify the current roadmap.

---

## 10. Stream 1 — Proof-First Runtime

Ariadne already has the seed of proof-first workflow:

```text
phase gates
frozen PLAN.md before implementation
role separation
.project-memory artifacts
independent review
allowed/forbidden write paths
```

What is missing:

```text
admissible proof refs
runtime CLI
gate-ready handoff packets
product state hash
finalization phase
artifact_index and proof_index
```

Post-0100 direction:

```text
Task
→ Specification freeze
→ Implementation against frozen criteria
→ Proof collection through runtime capture
→ Independent review
→ Fix
→ Finalization using admissible proof only
```

A proof reference should be valid only when tied to:

```text
current product state
frozen acceptance criteria
runtime capture
bounded artifact path
phase/run identity
```

Rejected proof types:

```text
agent says tests pass
agent summarizes output without capture
uncaptured terminal output
stale cache summaries
unbounded search claims
references not tied to current product state
```

Likely first PRs:

```text
0101 — Admissible Proof Ref Runtime Object
0102 — Gate-Ready Handoff Packet
0103 — ariadna CLI Skeleton
0104 — Proof Capture Command
0105 — Spec Freeze + Acceptance Criteria Runtime Object
```

All must have tests and deterministic validation.

---

## 11. Stream 2 — Decision Core / GRM-style hypothesis evaluation

Purpose: prevent agents from collapsing into the first plausible solution.

Runtime decision governance flow:

```text
Problem
→ Candidate Hypotheses
→ Generated Principles
→ Weighted Criteria
→ Critiques
→ Scores
→ Principle Sampling
→ Voting / Meta-Judge
→ Selected Decision
→ Execution Contract
```

This is not model training. It is runtime governance.

Core objects:

```text
hypothesis
principle_pack
hypothesis_scores
decision_report
meta_judge_report
execution_contract
```

Rules:

```text
minimum 3 hypotheses for normal decisions
minimum 5 hypotheses for high-risk architecture decisions
principle perspectives include architecture, security, performance, maintenance, cost, state-first, legacy-risk
voting includes weighted average plus critical-failure veto
high-risk decisions prefer risk-adjusted score
meta-judge may return accept_decision, resample_principles, generate_more_hypotheses, needs_human_review
```

Likely PRs:

```text
0110 — Decision Core Artifact Runtime Objects
0111 — Hypothesis Generator Deterministic Stub
0112 — Principle Generator + Sampler Stub
0113 — Hypothesis Scorer + Voting Engine Stub
0114 — Meta-Judge Stub
```

Every PR must produce runnable code and tests.

---

## 12. Stream 3 — Context Layer: Bronze / Silver / Gold

Context is a production asset.

The model consumes context. The model must not be the only place where context exists.

Three context levels:

```text
Bronze: raw source truth, raw docs, raw logs, raw git history
Silver: normalized indexes, symbols, graphs, tests, state candidates, context packs
Gold: curated invariants, domain rules, state models, rubrics, policies, prompt blocks
```

Gold context changes require review like code changes.

Proposed context warehouse:

```text
.ariadne/bronze/
.ariadne/silver/
.ariadne/gold/
.ariadne/evals/
```

Important: this must not become a directory-only PR. Context structure must be accompanied by executable tests, fixture generation, or validation.

Likely PRs:

```text
0106 — Context Warehouse Skeleton with Deterministic Validation
0107 — Context Eval Case Format + Runner
0108 — Ariadne Anchors Extractor
0109 — Gold Context Invariant Loader
0129 — Context Agent Stub
```

---

## 13. Stream 4 — Model Health Monitor + Model Replaceability

“The model is replaceable” must become runtime behavior.

Ariadne needs:

```text
model health events
degradation detector
model switch trigger
substrate handoff pack
model profile registry
prompt policy router
```

Degradation signals:

```text
repeated scope violations
review verdict block on repeated attempts
forbidden pattern violations
artifact schema drift
token bloat
invariant violations in precommit-review
critical failure rate threshold exceeded
```

Model switching must not lose substrate state.

A substrate handoff pack should include:

```text
current PR
last good SHA
context pack ID
open phase
frozen acceptance criteria
proof refs so far
pending task
switch reason
recommended model/profile
handoff instructions
```

Likely PRs:

```text
0115 — Model Health Event Schema + Degradation Detector
0116 — Substrate Handoff Pack Generator
0117 — Model Profile Registry + Prompt Policy Router
```

No provider lock-in. No assumption that one model family is permanent.

---

## 14. Stream 5 — External Capability Integration

External sources are inspiration and pattern libraries, not code to copy.

Required source handling:

```text
re-check every link at task time
separate confirmed facts from interpretation
respect licenses
do not copy third-party code without license review
prefer pattern extraction over code copying
do not adopt external branding
do not clone external architecture
do not introduce provider lock-in
do not introduce Docker lock-in
do not expose hidden reasoning
do not download large datasets early
```

External sources to study after 0100:

```text
https://github.com/athina-ai/ariadne
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6870178
https://huggingface.co/collections/open-r1/reasoning-datasets
https://github.com/anthropics/claude-cookbooks
https://github.com/fainir/most-capable-agent-system-prompt
https://github.com/EleutherAI/lm-evaluation-harness
https://github.com/AlessandroBorges/ReasoningSysPromts
```

Translation principles:

```text
Athina/Ariadne eval patterns → evaluation evidence layer + failure taxonomy
Ariadne faithfulness paper → visible reasoning summary faithfulness audits, no hidden CoT
Open-R1 datasets → tiny local fixtures and provenance registry, no large downloads
Claude cookbooks → provider-neutral recipe format and runner
Most capable agent prompt → measurable failure-to-improvement loop, not giant system prompt
LM Evaluation Harness → Ariadne-native eval harness, no dependency import initially
ReasoningSysPrompts → model profile registry + prompt policy router, no private reasoning logs
```

---

## 15. Architecture layers after integration

The post-0100 program should converge into these layers:

```text
1. Proof-First Runtime Layer
2. Decision Governance Layer
3. Context Intelligence Layer
4. Model Health + Replaceability Layer
5. Evaluation + Quality Layer
6. Self-Improvement Layer
7. Cookbook + Recipe Layer
8. Dataset + Provenance Layer
```

The strategic plan must define runtime objects for:

```text
proof_ref
acceptance_criteria
gate
handoff_packet
run_state
finalization_report
hypothesis
principle_pack
hypothesis_scores
decision_report
meta_judge_report
context_pack
context_eval_case
context_eval_report
health_event
model_switch_trigger
substrate_handoff_pack
model_profile
prompt_policy
eval_task
evaluator
metric
failure_taxonomy
benchmark_run
result_log
```

But do not let this become schema theater. Every object must point to executable PRs.

---

## 16. Baseline assessment required at PR 0100

Before writing the post-0100 strategic plan, the strategic-planner must inspect and summarize Ariadne’s actual state.

Required baseline categories:

```text
mock app loop status
runner execution contract
runner adapter work completed
run state and evidence model
existing eval/review artifacts
context pack/compiler work
task-intake surface
Docker adapter work
human review boundary work
proof ref work if already present
CLI work if already present
```

Do not assume. Read source-of-truth artifacts.

---

## 17. Post-0100 roadmap shape

The unified strategic plan must produce 25–35 PRs starting at 0101 unless repository state indicates otherwise.

Each PR entry must include:

```text
PR number
title
goal
executable behavior
expected files
tests
validation commands
stream source
why it improves Ariadne
non-goals
dependency on previous PRs
```

The first 10 PRs must be executable code PRs, not docs-only.

A strong default sequence:

```text
0101  Admissible Proof Ref Runtime Object
0102  Gate-Ready Handoff Packet
0103  ariadna CLI Skeleton
0104  Proof Capture Command
0105  Spec Freeze + Acceptance Criteria Runtime Object
0106  Context Warehouse Skeleton with Validation
0107  Context Eval Case Format + Runner
0108  Ariadne Anchors Extractor
0109  Gold Context Invariant Loader
0110  Decision Core Runtime Objects
0111  Hypothesis Generator Deterministic Stub
0112  Principle Generator + Sampler Stub
0113  Hypothesis Scorer + Voting Engine Stub
0114  Meta-Judge Stub
0115  Model Health Event + Degradation Detector
0116  Substrate Handoff Pack Generator
0117  Model Profile Registry + Prompt Policy Router
0118  Ariadne Eval Harness Minimal
0119  Benchmark Task Registry
0120  Failure Taxonomy Classifier
0121  Reasoning Faithfulness Audit Skeleton
0122  Cookbook Recipe Format + Runner
0123  Structured Output Contract Checker
0124  Failure-to-Improvement Backlog Generator
0125  Capability Matrix Runtime Object
0126  ariadna Finalize Command + Final Report
0127  LLM-Backed Principle Generator
0128  LLM-Backed Hypothesis Scorer
0129  Context Agent Stub
0130  End-to-End Run + Eval + Proof + Repair Demo
```

The order may be adjusted based on actual 0100 repository state, but executable-first is not negotiable.

---

## 18. Risk register that must be preserved

The strategic plan must explicitly address:

```text
committee-mode regression
proof theater
copying external code without license review
benchmark bloat
dataset bloat
hidden chain-of-thought leakage
provider lock-in
Docker lock-in
nondeterministic evals
flaky tests
false positives in model health monitor
stale substrate handoff pack
gold context becoming review-heavy without runtime value
self-improvement loop producing noise
excessive abstractions before working code
decision core becoming a bottleneck for simple decisions
```

Mitigation must always point back to tests, validation, scoped PRs, and executable gates.

---

## 19. Success criteria for the post-0100 wave

By the end of the post-0100 wave, Ariadne should be able to:

```text
run a task through runner/eval and produce a quality report
classify failure modes deterministically
run a tiny benchmark suite locally
execute a cookbook recipe locally
compare two model/profile outputs through the same eval interface
generate a repair backlog item from a failed run
detect at least one reasoning faithfulness inconsistency in a controlled fixture
switch models without losing substrate state
freeze acceptance criteria and reject proofs that do not match them
run gate check and refuse finalization without admissible proofs
run end-to-end without network
keep all post-0100 features tested
avoid docs-only drift
```

---

## 20. First prompt to give the strategic-planner after PR 0100

Use this when PR/commit 0100 is merged and the user asks to start the post-0100 plan.

```text
Task: Post-0100 Ariadne Unified Strategic Integration Plan

Agent: strategic-planner

Mode: strategic planning only

Timing constraint:
Run only after Ariadne reaches PR/commit 0100 or later.
If current repository state is before PR/commit 0100, stop and report blocker.
Do not interrupt or rewrite any pre-0100 roadmap work.

Goal:
Create a unified post-0100 implementation roadmap that integrates:
- Proof-First Runtime
- Decision Core / GRM-style hypothesis evaluation
- Bronze/Silver/Gold Context Layer
- Model Health Monitor + Model Replaceability
- External Capability Integration from the seven approved sources

This must not be a generic research report.
This must not be a vague inspiration document.
This must not be a docs-only roadmap.
Every proposed PR must have executable behavior, tests, validation commands, non-goals, and dependencies.

Write only:
- .project-memory/post-0100/unified-strategic-plan/PLAN.md
Optional only if useful:
- .project-memory/post-0100/unified-strategic-plan/source-map.yml

Required source-of-truth lookup:
- .project-memory/memory_index.yml
- .project-memory/project_contract.yml
- .project-memory/context-bundles/contracts.yml
- .project-memory/anchors.yml
- ARIADNE_ARCHITECTURE.md
- ROADMAP.md if present
- .project-memory/pr/**/PLAN.md for PRs 0063 through current
- .project-memory/pr/**/reviews/precommit-review.yml for directly relevant PRs
- schemas/** existing schemas
- docs/adr/** existing ADRs
- services/** only after source-of-truth artifacts indicate relevant paths

Allowed read-only commands:
- git rev-parse --verify HEAD
- git status --short
- git diff --name-only
- find .project-memory -maxdepth 6 -type f | sort
- find docs -maxdepth 5 -type f | sort
- find schemas -maxdepth 5 -type f | sort
- find services -maxdepth 6 -type f | sort
- grep -R -n "<pattern>" <explicit paths> || true
- date -u +%Y-%m-%dT%H:%M:%SZ

Forbidden commands:
- git add
- git commit
- git push
- git reset
- git checkout
- git switch
- git merge
- git rebase
- git clean
- git log
- git tag
- gh release
- docker
- docker compose
- rm
- mv
- sudo
- chmod
- chown
- pip install
- python -m pip install

Forbidden write paths:
- services/**
- packages/**
- agents/**
- apps/**
- schemas/**
- docs/**
- docker/**
- .github/**
- pyproject.toml
- package.json
- Makefile
- any path except .project-memory/post-0100/unified-strategic-plan/PLAN.md and optional .project-memory/post-0100/unified-strategic-plan/source-map.yml

Required plan sections:
- Purpose
- Current Ariadne baseline at 0100
- Strategic position
- Five-stream synthesis
- External source map
- Proof Runtime architecture
- Decision Core architecture
- Context Layer architecture
- Model Health architecture
- Eval Harness architecture
- Post-0100 PR roadmap of 25–35 PRs
- Capability import rules
- Risk register
- Success criteria
- Non-goals
- Stop conditions
- Files read/written
- Boundary confirmations

External source handling:
Re-check every link at task time.
Separate confirmed facts from interpretation.
Respect licenses.
Do not copy third-party code without license review.
Prefer pattern extraction over code copying.
Do not hardwire one provider.
Do not hardwire Docker.
Do not expose hidden chain-of-thought.
Do not download large datasets first.
Every adopted idea must become a tested Ariadne capability.

Roadmap requirements:
- Start at PR 0101 unless repository state says otherwise.
- Produce 25–35 PRs.
- First 10 PRs must be executable code PRs.
- Each PR must include PR number, title, goal, executable behavior, expected files, tests, validation commands, stream source, why it improves Ariadne, non-goals, dependencies.
- Block any docs-only or schemas-only PR unless it is a short bridge followed immediately by code.

Stop and block if:
- current Ariadne state at 0100 cannot be established
- proposed roadmap becomes docs-only
- proposed roadmap requires large downloads first
- proposed roadmap requires provider lock-in
- proposed roadmap requires Docker lock-in
- proposed roadmap requires hidden reasoning logs
- proposed roadmap requires broad rewrite
- proposed roadmap interrupts pre-0100 work
- proposed plan cannot define executable PRs, tests, and validation

Final output:
PLAN written: yes | no

strategic_position:
  current_pr_at_execution:
  post_0100_start_point:
  pre_0100_work_preserved:
  committee_mode_risk:
  executable_first_policy:

ariadne_baseline_at_0100:
  proof_runtime_status:
  decision_core_status:
  context_layer_status:
  model_health_status:
  eval_harness_status:
  cli_status:

streams_synthesized:
external_sources:
post_0100_roadmap:
architecture_layers:
risk_register:
success_criteria:
files_read:
files_written:
files_intentionally_ignored:

confirm: no implementation code written
confirm: current pre-0100 roadmap not changed
confirm: no docs/schemas/code outside allowed planning path written
confirm: no third-party code copied
confirm: no large datasets downloaded
confirm: no provider lock-in introduced
confirm: no Docker lock-in introduced
confirm: no hidden chain-of-thought logging proposed
confirm: post-0100 roadmap is executable-first
confirm: docs-only PRs blocked by default after 0100
confirm: no git mutation commands run
confirm: no Docker commands run
confirm: agent is not нотариус собственной работы
```

---

## 21. How the new chat should behave with the user

When user says “следующий шаг”:

Answer with:
- next PR title
- why it is next
- expected branch
- expected files
- one-sentence boundary

When user says “два промпта”:

Return exactly:
- Prompt 1 — planner
- Prompt 2 — plan-review

When plan-review is approved and user asks next prompts:

Return exactly:
- Prompt 1 — implementation
- Prompt 2 — precommit-review

When user gives review output:

Check:
- verdict
- blockers
- warnings
- dirty tree
- missing evidence
- validation completeness
- exact selector presence
- false confirmations

Then say:
- commit
- regenerate artifact
- corrective implementation
- or block

When user asks PR description:

Return:
- commit scope
- commit commands
- PR title
- short PR body
- `gh pr create`

---

## 22. Final standard

Be strict with scope.

Be compact with context.

Use Ariadne memory as the navigation substrate.

Avoid rediscovery.

Avoid committee mode.

Turn every strategic idea into a tested Ariadne capability.

Do not let the model become the product.

Do not let an agent be the notary of its own work.

The substrate is the product.

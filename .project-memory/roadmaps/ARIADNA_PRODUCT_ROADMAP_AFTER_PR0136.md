# Ariadna Product Roadmap After PR 0136

Status: draft target artifact for PR 0137
Scope: roadmap correction and stream unlock after Production Line readiness gate
Source prompt: `.project-memory/product/ARIADNA_PRODUCT_MASTER_PROMPT_SOURCE.md`
Derived roadmap artifact: `.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md`

## 0. Decision

PR 0131-0136 closed the Production Line hardening stream.

Ariadna now has enough runtime substrate to move from “agent execution substrate” into “runtime-owned artifact workspace”. The next active stream should be read-only Artifact Workspace UI, not autonomous UI mutation or broad Decision Core.

The product identity is:

```text
Ariadna = runtime package + artifact workspace + role-based agent orchestration substrate.
```

The operating principle is:

```text
Agent proposes.
Runtime captures.
Artifacts visualize.
Rubrics evaluate.
Proof verifies.
Human approves.
```

## 1. Roadmap policy after PR 0136

1. Every stream must be executable-first unless explicitly marked as architecture-only unlock.
2. Strategic prompts may be stored as source artifacts, but source artifacts are not proof.
3. Roadmap artifacts are planning surfaces, not implementation evidence.
4. Runtime-captured proof remains the source of truth for completion claims.
5. UI mutation remains frozen until read-only Artifact Workspace is complete.
6. Agent launch from UI remains frozen until UI can display state, gates, proofs, and run reports.
7. Decision Core, Context Warehouse, Rubrics, Model Router, ETL demo, and agent autonomy expansion remain staged, not immediate.
8. ROADMAP.md should summarize active/completed/frozen streams; detailed roadmap lives in this artifact.

## 2. Streams overview

| Stream | PRs | Purpose | Mutation allowed? |
|---|---:|---|---|
| Product Architecture Unlock | 0137 | Preserve master prompt and unlock roadmap | Docs/project-memory only |
| Artifact Workspace Read Model | 0138-0142 | Make runtime evidence visible to UI | Read-only |
| Artifact Workspace Shell | 0143-0147 | 4-zone UI shell and report/proof viewers | Read-only |
| Visual Gate / Mermaid | 0148-0152 | Visual phase gates before code | Read-only + accepted artifacts later |
| Artifact Registry / Acceptance State | 0153-0157 | Runtime artifact model and accept/reject state | Controlled runtime mutation |
| PCAM/PBS Purpose Layer | 0158-0162 | Root purpose, PBS, non-goals, approval triggers | Controlled runtime mutation |
| Context Core MVP | 0163-0169 | Bronze/Silver/Gold context and context packs | Controlled runtime mutation |
| GRACE-style Inline Contracts | 0170-0174 | Anchors, contract lints, stale-doc checks | Code/context linting |
| Rubrics Runtime Contracts | 0175-0179 | Runtime rubric packs and judge reports | Controlled evaluation |
| Decision Core MVP | 0180-0184 | Hypothesis/principle/scoring/meta-judge | Read-only decision reports first |
| Model Router / Observatory | 0185-0186+ | Routing, cost, progress dashboard | Initially read-only |

## 3. Detailed PR roadmap

### Stream 0 — Product Architecture Unlock

#### PR 0137 — Product Architecture Roadmap Unlock

Purpose: Close Production Line stream formally and open Artifact Workspace Read-Only stream.

Files:

```text
ROADMAP.md
.project-memory/product/ARIADNA_PRODUCT_MASTER_PROMPT_SOURCE.md
.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
.project-memory/pr/0137-product-architecture-roadmap-unlock/PLAN.md
.project-memory/pr/0137-product-architecture-roadmap-unlock/reviews/plan-review.yml
.project-memory/pr/0137-product-architecture-roadmap-unlock/reviews/precommit-review.yml
```

Acceptance:

```text
Production Line marked completed.
Master product prompt preserved as source artifact.
Roadmap artifact created.
Next active stream set to Artifact Workspace Read-Only.
No runtime code.
No tests.
No UI code.
No agent configs.
```

---

### Stream 1 — Artifact Workspace Read Model

#### PR 0138 — UI Runtime Evidence Read Model

Purpose: Define a stable read-only runtime evidence view model from run.json, manifest.json, run-report.txt, readiness result, payload cleanliness, and execution_results.

Acceptance:

```text
Read model returns run_id, status, branch, timestamps, report path, manifest path, execution result summary, readiness summary, payload cleanliness summary.
No frontend yet.
Focused tests cover complete, blocked, failed, and partial evidence runs.
No mutation.
```

#### PR 0139 — Local Run Index Reader

Purpose: Read `.ariadne/runs/*` into a deterministic local run index.

Acceptance:

```text
Reads isolated runs root.
Sorts by timestamp/run_id deterministically.
Classifies complete/partial/corrupt run directories.
Does not create or modify run files.
Tests use tmp_path.
```

#### PR 0140 — Run Detail Evidence Aggregator

Purpose: Aggregate one run into a complete detail packet for UI consumption.

Acceptance:

```text
Combines run.json, manifest, report, readiness, execution_results, artifact paths, hashes.
Missing fields explicit as not_available.
No fabricated status or PR URL.
Tests cover missing manifest/report/run_json.
```

#### PR 0141 — Runtime Evidence API Surface

Purpose: Expose read-only local HTTP or task_intake route for run index and run detail.

Acceptance:

```text
GET-only endpoints.
No POST mutation.
No agent launch.
No git/gh operations.
No network dependency beyond local server test client.
Tests cover index/detail/error states.
```

#### PR 0142 — Run Evidence Serialization Contract

Purpose: Freeze JSON contract for UI runtime evidence packets.

Acceptance:

```text
Versioned response shape.
Schema-like tests or golden fixtures.
Backward-compatible missing-field policy.
No production schema theater; only executable tests.
```

---

### Stream 2 — Artifact Workspace Shell

#### PR 0143 — Artifact Workspace 4-Zone Shell Skeleton

Purpose: Add initial read-only UI shell: left timeline, center artifact canvas, right gates/proofs, bottom logs/captures.

Acceptance:

```text
Static shell connected to read-only evidence API fixtures.
No runtime mutation.
No agent launch.
No commit/PR actions.
UI tests verify zones render.
```

#### PR 0144 — Local Run List Page

Purpose: Show local run list using PR 0139/0141 evidence API.

Acceptance:

```text
Run list shows run_id, status, branch, generated_at, readiness.
Handles empty/corrupt run roots.
Read-only.
```

#### PR 0145 — Run Detail Evidence Panel

Purpose: Show detailed run evidence in the 4-zone workspace.

Acceptance:

```text
Displays run status, reason codes, execution_results, artifact paths, hashes.
Missing evidence visible.
No mutation buttons.
```

#### PR 0146 — Run Report Viewer

Purpose: Render local run-report.txt in the artifact canvas.

Acceptance:

```text
Reads report through API, not arbitrary file paths.
Shows not_available when missing.
Does not trust report as proof unless linked to run.json/manifest.
```

#### PR 0147 — Proof and Manifest Viewer

Purpose: Display manifest and proof refs/evidence paths in right/bottom panels.

Acceptance:

```text
Manifest entries visible.
Proof refs clearly separated from agent claims.
Command captures/logs visible when available.
No proof acceptance mutation yet.
```

---

### Stream 3 — Visual Gate / Mermaid

#### PR 0148 — Mermaid Artifact Type Read Model

Purpose: Add read-only artifact type for Mermaid visual artifacts.

Acceptance:

```text
Artifact packet supports type mermaid.
Renderer handles mmd text from controlled artifact path.
No Mermaid generation yet.
```

#### PR 0149 — Visual Gate Runtime Object

Purpose: Define runtime visual_gate result with required diagrams, status, human_review_required, evidence refs.

Acceptance:

```text
VisualGateResult type and tests.
No code implementation allowed before pending/approved gate is represented.
No UI mutation.
```

#### PR 0150 — Requirement / State / Sequence Diagram Viewers

Purpose: Render core diagram types in artifact canvas.

Acceptance:

```text
Requirement, state, sequence diagrams render from artifacts.
Invalid Mermaid fails safe with visible error.
No arbitrary script execution.
```

#### PR 0151 — Visual Gate Readiness Check

Purpose: Check whether required diagrams exist before implementation phase.

Acceptance:

```text
Missing required diagram blocks visual gate.
Accepted diagram evidence passes.
Tests cover required/optional/invalid diagrams.
```

#### PR 0152 — Human Visual Approval Artifact

Purpose: Record explicit human approval/rejection for visual gate artifacts.

Acceptance:

```text
Approval is runtime state, not agent claim.
Approval has operator, timestamp, artifact hash, reason.
No implementation phase unlock without approval where required.
```

---

### Stream 4 — Artifact Registry / Acceptance State

#### PR 0153 — Artifact Registry Schema

Purpose: Define runtime artifact registry object.

Acceptance:

```text
artifact_id, artifact_type, run_id, phase_id, path, hash, source, proof_refs, status.
No UI mutation yet.
Tests cover deterministic registration.
```

#### PR 0154 — Artifact Registry Persistence

Purpose: Persist artifact_index.json under run directory.

Acceptance:

```text
Writes only runtime-owned local artifact registry.
Preserves run.json/manifest/report.
Tests cover write/readback and hashes.
```

#### PR 0155 — Artifact Accept / Reject Runtime State

Purpose: Add controlled accept/reject state transitions for artifacts.

Acceptance:

```text
Accept/reject requires human actor/reason.
Updates registry only.
Does not alter source artifact bytes.
Tests cover accepted/rejected/pending.
```

#### PR 0156 — Artifact Workspace Acceptance Read UI

Purpose: Show accepted/rejected/pending state in UI.

Acceptance:

```text
UI displays state only.
No mutation buttons unless runtime endpoint exists and is separately gated.
```

#### PR 0157 — Artifact Mutation Endpoint Gate

Purpose: Add safe local endpoint for artifact accept/reject if approved.

Acceptance:

```text
POST only for accept/reject.
Requires exact artifact_id/hash.
Rejects stale hash.
No file content mutation.
Tests cover stale/unknown/accepted states.
```

---

### Stream 5 — PCAM/PBS Purpose Layer

#### PR 0158 — Purpose Runtime Object

Purpose: Add purpose.json with root purpose, business goal, technical goal, non-goals, constraints, success definition.

Acceptance:

```text
Purpose object persisted under run/phase.
Root purpose change requires explicit approval.
Tests cover missing/changed/root purpose.
```

#### PR 0159 — PBS Runtime Object

Purpose: Add purpose breakdown structure with nodes linked to artifacts/proofs/tests.

Acceptance:

```text
pbs.json with node ids, parent/child, status, acceptance refs.
No vague free-form-only tasks.
Tests cover tree integrity.
```

#### PR 0160 — Human Approval Policy Object

Purpose: Define approval triggers for root purpose changes and high-risk work.

Acceptance:

```text
human_approval_policy.json.
Risk triggers include auth, payments, PII, permissions, deletion, migration.
Tests cover required approval detection.
```

#### PR 0161 — Purpose Gate Checker

Purpose: Block phase transition if purpose/non-goals/approval policy missing or violated.

Acceptance:

```text
PurposeGateResult with reason codes.
No implementation phase if acceptance criteria not tied to purpose_id.
```

#### PR 0162 — Purpose/PBS UI Panels

Purpose: Show purpose tree and non-goals in the workspace.

Acceptance:

```text
Read-only purpose tree.
Highlights approval-required nodes.
No silent purpose edits.
```

---

### Stream 6 — Context Core MVP

#### PR 0163 — Bronze Context Index

Purpose: Index raw docs, reports, logs, and session notes as non-authoritative Bronze context.

Acceptance:

```text
Bronze entries marked non-proof.
Session reports cannot satisfy proof requirements.
Tests cover authority classification.
```

#### PR 0164 — Silver Symbol/File Index

Purpose: Build file-symbol map and relevant tests index.

Acceptance:

```text
Deterministic index from local source files.
No embeddings required.
Tests cover symbols, tests, imports if available.
```

#### PR 0165 — Gold Context Registry

Purpose: Define trusted operational context registry.

Acceptance:

```text
Gold entries require owner, reason, review status, source refs.
Gold changes require context eval placeholder gate.
```

#### PR 0166 — Context Pack Compiler MVP

Purpose: Build context_pack.json with relevant files, symbols, tests, invariants, risk notes, missing_context, lineage.

Acceptance:

```text
No top-10-chunks-only model.
Structured context pack.
Tests cover required fields and missing context.
```

#### PR 0167 — Context Pack UI Viewer

Purpose: Show context packs in Artifact Workspace.

Acceptance:

```text
Displays relevant files/symbols/tests/invariants/missing context.
Bronze/Silver/Gold authority visibly separated.
```

#### PR 0168 — Context Invalidation Gate

Purpose: Detect stale context when files/symbols changed.

Acceptance:

```text
Context invalid if source hash changes.
Blocks use of stale Gold/Silver context without refresh.
```

#### PR 0169 — Context Eval Case Skeleton

Purpose: Add executable context eval case/report baseline format.

Acceptance:

```text
context_eval_case.json, report, baseline test fixtures.
No ML eval complexity yet.
```

---

### Stream 7 — GRACE-style Inline Contracts

#### PR 0170 — Ariadna Inline Anchor Extractor

Purpose: Extract @ariadna-* and @pcam-* anchors from code/comments.

Acceptance:

```text
Extractor returns anchors with file/line/symbol context.
No requirement to annotate entire codebase.
Tests cover domain/risk/invariant/purpose anchors.
```

#### PR 0171 — Inline Contract Linter

Purpose: Lint anchor shape, required fields, and broken references.

Acceptance:

```text
Contract lint report with warnings/blockers.
No code mutation.
```

#### PR 0172 — Contract Sweep Drift Detector

Purpose: Detect drift between inline contracts and external docs/context.

Acceptance:

```text
Flags stale docs as Bronze/non-authoritative.
Does not auto-promote docs to Gold.
```

#### PR 0173 — Doc Authority Classifier

Purpose: Classify docs/session reports as Bronze/Silver/Gold candidates.

Acceptance:

```text
Session reports default Bronze.
Gold requires explicit review metadata.
Tests cover historical/stale reports.
```

#### PR 0174 — Inline Contracts UI Surface

Purpose: Show inline contracts near files/symbols in workspace.

Acceptance:

```text
Read-only anchor viewer.
Links anchors to relevant files/symbols/context packs.
```

---

### Stream 8 — Rubrics Runtime Contracts

#### PR 0175 — Rubric Pack Runtime Object

Purpose: Define rubric_pack.json with essential, important, optional, pitfalls, evidence requirements, stop conditions.

Acceptance:

```text
Rubric pack linked to purpose_id and acceptance criteria.
Tests cover missing essential criteria.
```

#### PR 0176 — Rubric Judge Report Object

Purpose: Add rubric_judge_report.json result shape.

Acceptance:

```text
verdict pass/warning/fail/needs_human_review.
essential failure blocks completion.
Evidence insufficient => needs_human_review.
```

#### PR 0177 — Rubric Gate Checker

Purpose: Enforce rubric stop conditions before finalization.

Acceptance:

```text
Critical pitfall blocks.
Missing evidence blocks.
Human approval required when triggered.
```

#### PR 0178 — Rubric UI Viewer

Purpose: Display rubric criteria, pass/fail, pitfalls, evidence links.

Acceptance:

```text
Read-only viewer.
Shows evidence refs and missing proof.
```

#### PR 0179 — Rubric Eval Export Skeleton

Purpose: Export rubric judge reports for future eval/model selection data.

Acceptance:

```text
Local JSONL export.
No model training.
No external network.
```

---

### Stream 9 — Decision Core MVP

#### PR 0180 — Decision Hypothesis Runtime Object

Purpose: Define hypotheses.json for architecture/product decisions.

Acceptance:

```text
Hypotheses include purpose_id, options, assumptions, risks.
No automatic decision execution.
```

#### PR 0181 — Principle Pack Object

Purpose: Define principle_pack.json with weighted criteria.

Acceptance:

```text
Principles linked to purpose and risks.
Weights explicit and reviewable.
```

#### PR 0182 — Hypothesis Scoring Report

Purpose: Produce hypothesis_scores.json from explicit criteria.

Acceptance:

```text
Scores have evidence refs or mark missing evidence.
No hidden model-only verdict.
```

#### PR 0183 — Meta-Judge Report

Purpose: Evaluate hypothesis diversity, criteria quality, missing risks, and human approval needs.

Acceptance:

```text
meta_judge_report.json.
Flags one-answer-too-early and omitted risks.
```

#### PR 0184 — Decision Report UI Viewer

Purpose: Show decision reports in Artifact Workspace.

Acceptance:

```text
Read-only decision viewer.
Shows selected option, alternatives, scores, risks, approval required.
```

---

### Stream 10 — Model Router / Observatory

#### PR 0185 — Model Capability Profile Object

Purpose: Define model_capability_profile.json and model routing report shape.

Acceptance:

```text
Role, cost, risk, context stress, tool stability fields.
No provider integration yet.
No API calls.
```

#### PR 0186 — Agent Progress Observatory Snapshot

Purpose: Add iteration_snapshot.json and progress_dashboard.md for long runs.

Acceptance:

```text
Captures phase goal, files changed, tests, risks, drift indicators.
15-minute checkpoint policy represented.
No autonomous enforcement yet.
```

## 4. Deferred next PR candidates after 0186

These are intentionally not part of the first 50 PR count but are likely next:

```text
0187 — Autonomy Budget Gate
0188 — Drift Detector MVP
0189 — Risk Heatmap Artifact
0190 — Tool Permission Registry
0191 — ETL Import Artifact Model
0192 — Construction Estimate Diagnostic Artifact
0193 — WBS Artifact Model
0194 — Gantt Artifact Model
0195 — OLAP Cube Read Model
0196 — Boss Dashboard Demo Shell
```

## 5. Architecture guardrails

1. Agent output is never proof.
2. Runtime-captured evidence is proof candidate.
3. Proof must be admissible and tied to run_id, phase_id, state hash, acceptance criteria, artifact path, timestamp, and tool identity.
4. Artifacts are not pretty screens; they are runtime-bound control surfaces.
5. UI starts read-only.
6. Mutation enters only through explicit runtime transitions.
7. Human approvals are first-class state.
8. Context is infrastructure, not documentation.
9. Visual gates happen before implementation.
10. Markdown reports are audit/handoff, not source of truth.
11. Models are replaceable; substrate is durable.
12. State-First remains preferred for business logic.
13. Every stream must preserve Production Line guarantees from PR 0131-0136.

## 6. First 10 concrete implementation issues after PR 0137

1. UI Runtime Evidence Read Model.
2. Local Run Index Reader.
3. Run Detail Evidence Aggregator.
4. Runtime Evidence API Surface.
5. Run Evidence Serialization Contract.
6. Artifact Workspace 4-Zone Shell Skeleton.
7. Local Run List Page.
8. Run Detail Evidence Panel.
9. Run Report Viewer.
10. Proof and Manifest Viewer.

## 7. Next 10 issues after read-only workspace

1. Mermaid Artifact Type Read Model.
2. Visual Gate Runtime Object.
3. Requirement / State / Sequence Diagram Viewers.
4. Visual Gate Readiness Check.
5. Human Visual Approval Artifact.
6. Artifact Registry Schema.
7. Artifact Registry Persistence.
8. Artifact Accept / Reject Runtime State.
9. Artifact Workspace Acceptance Read UI.
10. Artifact Mutation Endpoint Gate.

## 8. Final product principle

```text
Ariadna is not where the model thinks.
Ariadna is where the work becomes controllable.
```

# PR 0137 — Product Architecture Roadmap Unlock Plan

## Roadmap Alignment

| Field | Value |
|-------|-------|
| **Track** | Production Line → Product Architecture (stream transition) |
| **Slot** | PR 0137 (post-0136 production-line readiness gate) |
| **Why this PR is next** | PR 0131–0136 closed the Production Line hardening stream. The runner now has dogfood proof (0131), execution result persistence (0132), test residue isolation (0133), commit payload cleanliness gate (0134), local run report (0135), and production-line readiness gate (0136). PR 0137 is the architecture transition PR that commits the product master prompt as a durable source artifact, records the post-0136 roadmap, and opens **Artifact Workspace Read-Only UI** as the next active stream. No runtime or UI implementation happens in this PR. |
| **Batching policy** | Single-purpose: transition and roadmap unlock. Artifact-only PR allowed because this completes a milestone and opens the next stream, not a capability implementation. |
| **Drift heuristic** | Does not start a frozen capability stream. The next stream is read-only Artifact Workspace — UI mutation, agent launch from UI, commit from UI, and PR creation from UI remain frozen. No Decision Core, Context Warehouse, Rubrics, Model Router, or ETL demo work starts. |
| **Architect note** | This PR is **artifact-only**, which is explicitly permitted because it is a stream transition after a completed milestone (PR 0131–0136 Production Line hardening). It does not implement runtime code, tests, UI, or agent configurations. The product master prompt is a source artifact — never edited in this PR, preserved for roadmap derivation. The roadmap artifact is derived from the master prompt and the post-0136 state. |

## Summary

PR 0137 commits three durable artifacts:

1. **Source artifact**: `.project-memory/product/ARIADNA_PRODUCT_MASTER_PROMPT_SOURCE.md`
   — The Ariadna Product Master Prompt defining product identity, architecture
   principles, runtime ownership model, UI concept, artifact model, and roadmap
   phases. This is a source artifact and must not be silently edited in this PR.

2. **Derived roadmap artifact**: `.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md`
   — A ~50-PR staged roadmap derived from the master prompt and the post-0136
   milestone state. This roadmap defines the next 10+ active streams.

3. **Prompt artifact**: `.project-memory/pr/0137-product-architecture-roadmap-unlock/PROMPTS.md`
   — The planner, plan-review, and coder prompts for this PR, preserved as
   a planning surface.

This PR closes the Production Line hardening stream (PR 0131–0136) and opens
**Artifact Workspace Read-Only UI** as the next active stream. All future UI
mutation, agent launch from UI, commit from UI, and PR creation from UI remain
frozen until explicitly unlocked by a future roadmap PR.

## Product Identity

Ariadna is a **runtime package, artifact workspace, and role-based agent
orchestration substrate** for controlled AI-assisted production.

- Ariadna is **not** a chatbot wrapper.
- Ariadna is **not** just an agent loop.
- Ariadna is **not** only an IDE plugin.
- The **model is replaceable**; the substrate is durable.
- **Agent may generate, runtime must verify, human owns root purpose, and
  artifacts make intermediate meaning visible.**
- **Agent output is not proof.**
- **Runtime-captured evidence, proof refs, artifacts, state, and human
  approvals are source-of-truth materials.**

## Artifact Classification

| Artifact | Type | Action in This PR |
|---|---|---|
| `.project-memory/product/ARIADNA_PRODUCT_MASTER_PROMPT_SOURCE.md` | Source | Preserved — not silently edited |
| `.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md` | Derived roadmap | Written from source + post-0136 state |
| `.project-memory/pr/0137-product-architecture-roadmap-unlock/PROMPTS.md` | Prompt artifact | Preserved as planning surface |
| `.project-memory/pr/0137-product-architecture-roadmap-unlock/PLAN.md` | Planning artifact | Written by this planning task |
| `.project-memory/pr/0137-product-architecture-roadmap-unlock/reviews/plan-review.yml` | Review artifact | Written by plan-review agent |
| `.project-memory/pr/0137-product-architecture-roadmap-unlock/reviews/precommit-review.yml` | Review artifact | Written by precommit-review agent |

## Scope

### Allowed Implementation Files

| File | Action |
|---|---|
| `.project-memory/pr/0137-product-architecture-roadmap-unlock/PLAN.md` | Written (this file) |
| `.project-memory/product/ARIADNA_PRODUCT_MASTER_PROMPT_SOURCE.md` | Preserved as-is (source artifact) |
| `.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md` | Written (derived roadmap) |
| `.project-memory/pr/0137-product-architecture-roadmap-unlock/PROMPTS.md` | Preserved as-is (prompt artifact) |
| `.project-memory/pr/0137-product-architecture-roadmap-unlock/reviews/plan-review.yml` | Written by plan-review |
| `.project-memory/pr/0137-product-architecture-roadmap-unlock/reviews/precommit-review.yml` | Written by precommit-review |

### Forbidden Files

- `ROADMAP.md` — must not be modified by this planner task (may be modified by coder to update stream status)
- `services/**` — no runtime code
- `docs/**` — no documentation changes in this PR
- `agents/**` — no agent configuration changes
- `schemas/**` — no schema changes
- `pyproject.toml`, `poetry.lock`, `requirements*.txt` — no dependency changes
- `.gitignore` — no ignore rule changes
- All previous PR artifacts (0131–0136) — no modifications

## Roadmap Validation

### Source Artifact Alignment

The roadmap artifact (`.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md`)
was validated against the master prompt source. Key alignment checks:

1. **Product identity preserved**: Master prompt defines Ariadna as "runtime
   package, artifact workspace, and role-based agent orchestration substrate."
   Roadmap artifact states the same identity.

2. **Architecture principles preserved**: Master prompt's "Agent may generate,
   runtime must verify, human owns root purpose, artifacts make intermediate
   meaning visible" is reflected in roadmap guardrails.

3. **Stream ordering**: Roadmap artifact follows the master prompt's suggested
   phase ordering: Artifact Workspace first, then Context Core, then GRACE
   contracts, PCAM/PBS, Rubrics, Decision Core, Model Router, ETL demo.

4. **Frozen boundaries**: Roadmap artifact keeps Decision Core, Context
   Warehouse, Rubrics, Model Router, ETL/ERP demo, UI mutation, agent launch
   from UI, and automatic commits/PRs frozen until their prerequisite streams
   are established.

5. **PR count**: Roadmap artifact includes approximately 50 PRs (0138–0186+)
   with explicit PR numbers, names, purposes, and acceptance summaries.

### Stream Order (from roadmap artifact)

| # | Stream | PRs | Purpose |
|---|--------|:---|---------|
| 0 | Product Architecture Unlock | 0137 | Transition and roadmap |
| 1 | Artifact Workspace Read Model | 0138–0142 | Read-only evidence API |
| 2 | Artifact Workspace Shell | 0143–0147 | 4-zone UI shell |
| 3 | Visual Gate / Mermaid | 0148–0152 | Visual phase gates |
| 4 | Artifact Registry / Acceptance State | 0153–0157 | Runtime artifact model |
| 5 | PCAM/PBS Purpose Layer | 0158–0162 | Root purpose and PBS |
| 6 | Context Core MVP | 0163–0169 | Bronze/Silver/Gold context |
| 7 | GRACE-style Inline Contracts | 0170–0174 | Anchors, lints, stale-doc |
| 8 | Rubrics Runtime Contracts | 0175–0179 | Rubric packs and judge |
| 9 | Decision Core MVP | 0180–0184 | Hypothesis/principle/scoring |
| 10 | Model Router / Observatory | 0185–0186+ | Routing, cost, progress |

## Frozen Boundaries

The following remain frozen until explicitly unlocked by a future roadmap PR:

1. **Context Warehouse** — frozen until Artifact Workspace read-only stream is
   established (PR 0147 complete).
2. **Decision Core** — frozen until Artifact Workspace and core evidence views
   are established.
3. **Rubrics runtime** — frozen until artifact and evidence views exist.
4. **Model Router** — frozen until observable role/evidence data exists.
5. **ETL/ERP demo** — frozen until Artifact Workspace, Artifact Registry, and
   Visual Gate foundations exist.
6. **UI mutation** — frozen until read-only UI is complete (Stream 2 complete).
7. **Automatic commits and PR creation from UI** — frozen until explicitly
   unlocked by a future roadmap PR.

## Non-Goals

- No runtime code
- No tests
- No UI code
- No agent configurations
- No schema changes
- No dependency changes
- No .gitignore changes
- No dogfood run
- No Docker
- No GitHub PR creation through runtime
- No Decision Core implementation
- No Context Warehouse implementation
- No Rubrics implementation
- No Model Router implementation
- No ETL/ERP demo
- No dashboard, control plane, retry system, eval harness, faithfulness audit,
  or frontend product features

## Validation Checklist

### 1. Artifact Presence Check

```bash
test -f .project-memory/product/ARIADNA_PRODUCT_MASTER_PROMPT_SOURCE.md
test -f .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
test -f .project-memory/pr/0137-product-architecture-roadmap-unlock/PROMPTS.md
```

Expected: all three files exist.
If not met: block.

### 2. Git Status Check

```bash
git status --short
```

Expected: only expected PR 0137 artifact files are dirty or untracked, plus
untracked known generated residue if present.
If forbidden tracked files are modified: block.
If unknown untracked files exist: block.

### 3. Git Diff Check

```bash
git diff --name-only
```

Expected: empty or only expected tracked artifact paths if files already existed.
If `services/`, `agents/`, `schemas/`, `docs/`, dependencies, `.gitignore`,
`ROADMAP.md`, or previous PR artifacts appear: block.

### 4. Git Diff Cached Check

```bash
git diff --cached --name-only
```

Expected: empty during planning.
If staged files exist: block.

### 5. Grep for Product Identity

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "runtime substrate|artifact workspace|agent orchestration substrate|Agent may generate|Runtime must verify|Human owns|artifacts make intermediate meaning visible|agent output is not proof" \
  .project-memory/product \
  .project-memory/roadmaps \
  .project-memory/pr/0137-product-architecture-roadmap-unlock
```

Expected: product identity appears in source and roadmap artifacts.
If not met: block.

### 6. Grep for Next Stream and Frozen Boundaries

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "0138|Artifact Workspace|Read-Only UI|UI mutation remains frozen|agent launch from UI remains frozen|commit.*UI.*frozen|PR creation.*UI.*frozen|Context Core|Decision Core|Rubrics|Model Router" \
  .project-memory/roadmaps \
  .project-memory/pr/0137-product-architecture-roadmap-unlock
```

Expected: next stream (Artifact Workspace Read-Only UI) and frozen later
streams (Context Core, Decision Core, Rubrics, Model Router are staged, not
active). UI mutation, agent launch, commit from UI, PR creation remain frozen.
If not met: block.

### 7. Grep for Forbidden Payload

```bash
grep -R -n -E \
  --exclude-dir=__pycache__ --exclude-dir=.pytest_cache \
  "services/|agents/|schemas/|pyproject.toml|poetry.lock|requirements|.gitignore|ROADMAP.md" \
  .project-memory/pr/0137-product-architecture-roadmap-unlock/PLAN.md
```

Expected: these appear only as forbidden files or validation guardrails, not
as allowed implementation payload.
If PLAN allows them as payload: block.

## Preserved Previous Fixes

| Feature | Preserved by |
|---------|-------------|
| PR 0131 dogfood proof | Not modified. Proof artifact remains committed. |
| PR 0132 execution result persistence | `run_persistence.py` not modified. |
| PR 0133 test residue isolation | `conftest.py` not modified. |
| PR 0134 commit payload cleanliness | `_check_payload_cleanliness` and constants not modified. |
| PR 0135 run report artifact | `_write_run_report` and `report_path` not modified. |
| PR 0136 readiness gate | `_evaluate_readiness` not modified (not yet implemented — PR 0136 is planned). |
| Git Boundary authority | `git_boundary.py` not modified. |
| Dirty-tree strictness | `_check_git_baseline`, `FORBIDDEN_PAYLOAD_PREFIXES`, `IGNORED_BASELINE_PREFIXES` unchanged. |

## Stop Conditions

This PLAN is blocked if any:
- Branch is not `0137-product-architecture-roadmap-unlock`
- PLAN does not state that PR 0137 is a roadmap unlock and stream transition PR
- PLAN does not state that PR 0131–0136 closed the Production Line hardening stream
- PLAN does not state that PR 0137 does not implement runtime behavior
- PLAN does not state that PR 0137 commits durable architecture and roadmap artifacts
- PLAN attempts to implement runtime code, tests, or UI
- PLAN does not open Artifact Workspace Read-Only UI as the next active stream
- PLAN does not freeze UI mutation, agent launch from UI, commit from UI, and PR creation from UI
- PLAN adds .gitignore entries
- PLAN modifies services/, agents/, schemas/, docs/, dependencies, or previous PR artifacts

# ADR 0011 — PR Batching and Roadmap Discipline

- **Status:** accepted
- **Date:** 2026-06-30
- **Deciders:** architect
- **Tags:** roadmap, pr-discipline, batching, drift-detection

## Context

The Ariadne substrate project generated PRs sequentially from PR 0001 through
PR 0092. PR 0068 established the runner execution contract. PR 0077 created the
Docker agent runner adapter. PR 0079 began a "Local Interaction UX" track that
added frontend-only features to the `GET /` page served by
`services/task_intake/src/task_intake/server.py`.

By PR 0092, 14 consecutive PRs (PR 0079–0092) had been created against this
single page. None of these PRs introduced a new backend contract, a runner
behavior change, an artifact contract change, or a schema change. All were
isolated UI additions: panels, checklists, feedback forms, confusion signal
buttons, run history lists, onboarding text, copy/export buttons, and error
state placeholders.

The original execution/substrate sequence (PR 0068–0078) ended at PR 0078
without an explicit stop condition. PR generation continued into the UX track
because no policy existed to require architect sign-off before starting a
sequence of single-file, single-feature frontend-only PRs.

## What Drifted

The drift was not a violation of any existing rule — no rule existed. The
execution/substrate track ended, and the UX track began, without an explicit
checkpoint or re-planning event. The roadmap continued to describe a
phase-based decomposition (Phases 1–10 from PR 0041/0042) that had no
relationship to the actual PR sequence being executed.

Consequences of drift:

1. The execution/substrate track — Docker execution wiring, artifact
   persistence, human review persistence, stabilization — was not resumed.
2. The roadmap became a stale artifact describing a parallel universe.
3. No minimum-scope policy existed to prevent single-feature frontend-only PRs
   from accumulating without architect oversight.
4. No drift-detection heuristic existed to alert when a sub-track was producing
   PRs that touched only one UI file.

## Decision

1. **Close the Local Interaction UX track.** The page is feature-complete for
   manual local testing purposes. No further single-feature frontend-only PRs
   against this page without explicit architect sign-off.

2. **Adopt a PR batching/minimum-scope policy (effective PR 0094 onward):**

   - Every PR from PR 0094 onward must deliver a coherent multi-step substrate
     capability unit.
   - Single isolated UI control/toggle/copy PRs must be merged into an adjacent
     backlog item or rejected by the planner.
   - The planner must block PRs that touch only
     `services/task_intake/src/task_intake/server.py` for isolated UI additions
     unless architect sign-off is cited.

3. **Adopt the following drift-detection heuristic:**

   > If 4 or more consecutive PRs touch only one runtime UI file under
   > `services/task_intake/src/task_intake/server.py` and introduce no backend
   > contract, runner behavior, artifact contract, or schema change, flag
   > architect review before next PR planning.

   This heuristic is falsifiable: a reviewer can check the set of files modified
   by the last N PRs and determine whether the condition is met.

4. **Resume the execution/substrate track.** The PR sequence from PR 0094 to
   PR 0100 is defined in ROADMAP.md and covers:

   - Real Docker-backed execution (PR 0094)
   - Run artifact persistence (PR 0095)
   - Human review persistence path (PR 0096)
   - Local Docker end-to-end smoke (PR 0097)
   - Stabilization/error handling (PR 0098)
   - Acceptance pass (PR 0099)
   - Freeze/release gate (PR 0100)

5. **Lock post-0100 capability streams.** No work on the following may begin
   before PR 0100 lands:

   - Proof-First Runtime
   - Decision Core
   - Context Layer
   - Model Health Monitor
   - External Capability Integration

   This lock is reaffirmed from the original architecture decomposition. The
   phase-based roadmap (Phases 1–10) is superseded by the explicit PR sequence
   up to PR 0100.

6. **Adopt the Roadmap Alignment Gate as permanent policy (PR 0094 onward).**

   Roadmap alignment is mandatory for every planner prompt from PR 0094
   onward. PLAN.md must include a `### Roadmap alignment` section that
   identifies the roadmap track, expected PR slot, why this PR is next,
   batching policy check, drift heuristic check, and whether architect
   sign-off is required.

   **Plan-review is the enforcement point.** Plan-review agents must block
   if PLAN.md lacks the Roadmap alignment section, if the PR does not match
   the active ROADMAP.md sequence, if the batching policy is not satisfied,
   if the drift heuristic triggers without cited architect sign-off, or if
   the PR continues a closed track.

   **Implementation agents do not reopen roadmap decisions.** If roadmap and
   proposed PR disagree during implementation, the implementation agent must
   stop and request architect review before writing code.

## Rationale

- The substrate is the product. Frontend page polish is a means not an end.
  Without a policy that prioritizes substrate capability over UI features, PR
  cadence will continue to drift toward the path of least resistance (HTML
  changes).

- A falsifiable heuristic ensures that drift is detectable by any reviewer
  without requiring architectural judgment about what constitutes "too many UI
  PRs." The threshold of 4 consecutive PRs was chosen because 4 is larger than
  any legitimate multi-step UI change (e.g., adding a panel: one PR for
  structure, one for tests, one for polish) but smaller than the 14-PR
  accumulation that actually occurred.

- The PR 0100 lock prevents premature expansion into higher-risk capability
  areas before the core execution substrate is stable and released.

## Consequences

- **Planner** must include a `### Roadmap alignment` section in every PLAN.md
  from PR 0094 onward, identifying track, PR slot, batching policy check,
  drift heuristic check, and architect sign-off status.

- **Plan-review** is the enforcement point. Reviewers must block any PLAN.md
  that lacks the mandatory section, contradicts the active roadmap sequence,
  fails the batching policy, triggers the drift heuristic without cited
  sign-off, or continues a closed track.

- **Implementation agents** must follow the approved PLAN.md and must not
  reinterpret roadmap decisions during implementation. Disagreement between
  roadmap and proposed PR must stop the agent and request architect review
  before any code is written.

- **Precommit-review** verifies no implementation drift beyond approved
  PLAN.md scope.

- **Architect** must provide explicit sign-off for any deviation from the
  batching policy, roadmap sequence, or drift heuristic.

- **Reviewers** must check the drift-detection heuristic periodically (every
  4 PRs) and flag architect review if triggered.

- **ROADMAP.md** must be kept in sync with the actual PR sequence. This ADR
  establishes that the roadmap is a living document that should be updated
  whenever a sub-track begins or ends.

- The phase-based decomposition (Phases 1–10) is superseded but preserved in
  ROADMAP.md as historical reference. No new PRs shall be planned against these
  phases without explicit architect permission.

## Related ADRs

- ADR 0008 — Cache Keys Are Substrate Contracts
- ADR 0009 — Context Steward Owns Context Memory
- ADR 0010 — Runner Execution Contract Boundary
- ADR 0011 — (this document)

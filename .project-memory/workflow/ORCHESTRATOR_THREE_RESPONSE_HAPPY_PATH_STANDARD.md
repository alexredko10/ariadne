# Ariadne Three-Response Orchestrator Happy Path Standard

Version: 1.0.0
Effective from: PR 0142A merge
Applies to: orchestrator
Maintained in: .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md

================================================================================
=== Status and applicability
================================================================================

This artifact defines the normative Ariadne orchestrator workflow lifecycle.

It applies to every PR orchestration cycle after PR 0142A merges.

The orchestrator must read this artifact before generating any workflow response.

This artifact is a mandatory companion to .project-memory/ORCHESTRATOR_STANDARD.txt.

ORCHESTRATOR_STANDARD controls prompt construction.
This artifact controls lifecycle sequencing.

Update process: plan-review and precommit-review cycle required.

================================================================================
=== Ariadne project identity
================================================================================

The project name is Ariadne.

The base branch is main.

The agents are:

  planner
  plan-review
  coder
  precommit-review

The lifecycle artifacts are:

  PLAN.md
  reviews/plan-review.yml
  IMPLEMENTATION_REPORT.md
  reviews/precommit-review.yml

None of these artifact names may be substituted or renamed.

Do not introduce:

  PLAN_REVIEW.yaml
  CODER_REPORT.txt
  PRECOMMIT_REVIEW.yaml
  master as base branch
  .grace, @grace, water_meter, Broken Clock, or unrelated project identities.

Examples from other projects may influence presentation only, never Ariadne facts.

================================================================================
=== Roadmap-first rule
================================================================================

Every orchestrator cycle begins by reading:

  1. ROADMAP.md
  2. .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
  3. docs/adr/0011-pr-batching-and-roadmap-discipline.md

The roadmap determines the next PR slot.

Governance insertions require explicit architect authorization.

The orchestrator must not invent new product slots or renumber existing ones.

================================================================================
=== Evidence hierarchy
================================================================================

Agent output is not proof.

Runtime-captured validation, command outputs, file contents, diffs, persisted
runtime artifacts, and accepted proof refs remain proof.

IMPLEMENTATION_REPORT.md is handoff context, not proof.

Precommit-review remains the final gatekeeper.

If IMPLEMENTATION_REPORT.md claims disagree with PLAN.md or actual evidence,
PLAN.md and actual evidence win.

================================================================================
=== Three-response happy path overview
================================================================================

The happy path for one Ariadne PR iteration requires exactly three substantive
orchestrator responses.

Each response is a complete task prompt for a specific agent or pair of agents.

Response 1: roadmap decision, branch preparation, planner prompt, plan-review prompt.

Response 2: plan-review assessment, planning lock commit, coder prompt, precommit-review prompt.

Response 3: precommit-review assessment, exact implementation commit, one idempotent pull-request submit script.

Refer to the detailed contract sections below for each response.

================================================================================
=== Response 1 contract
================================================================================

Response 1 must contain:

  1. Roadmap decision.
     The orchestrator reads ROADMAP.md and the detailed product roadmap,
     identifies the next product PR slot or confirms a governance insertion,
     and states what the next PR is and why it is next.

  2. Clean main branch preparation.
     The orchestrator verifies that the working tree is clean,
     that the branch is main, and that HEAD is current with origin/main.
     A new feature branch is created from main with the PR identifier.

  3. Planner prompt.
     A task prompt for the planner agent with:
       - roadmap alignment (track, slot, batching/drift check)
       - exact branch name and PR identifier
       - required PLAN.md path
       - no implementation or review authority

  4. Plan-review prompt.
     A task prompt for the plan-review agent with:
       - exact PLAN.md path under review
       - review-artifact schema reference
       - required output path (.project-memory/pr/<pr-id>/reviews/plan-review.yml)
       - no PLAN.md modification authority

Response 1 must not include:

  - coder prompts
  - precommit-review prompts
  - PR submit scripts
  - implementation commit blocks

================================================================================
=== Response 2 contract
================================================================================

Response 2 begins only after plan-review is complete and the verdict is approve
or acceptable warning.

Response 2 must contain:

  1. Plan-review assessment summary.
     The orchestrator reads reviews/plan-review.yml, verifies:
       - verdict is approve or acceptable warning
       - no blockers exist
       - warnings are explicit and acceptable
       - commit_readiness is ready
       - the review artifact path is correct

  2. Planning lock commit.
     PLAN.md and reviews/plan-review.yml are committed together on the branch.
     After this commit, both artifacts are locked.
     The coder and precommit-review must not edit locked planning artifacts.

  3. Coder prompt.
     A task prompt for the coder agent with:
       - locked PLAN.md reference (exact path)
       - plan-review verdict and warnings
       - exact ALLOWED FILES as defined by PLAN.md
       - IMPLEMENTATION_REPORT.md requirement (path, template, all 11 sections)
       - no PLAN.md or plan-review.yml modification authority
       - no review-artifact write authority

  4. Precommit-review prompt.
     A task prompt for the precommit-review agent with:
       - locked planning artifact paths
       - IMPLEMENTATION_REPORT.md path
       - review-artifact schema reference
       - required output path (.project-memory/pr/<pr-id>/reviews/precommit-review.yml)
       - requirement to compare IMPLEMENTATION_REPORT.md claims against PLAN.md and actual evidence

Response 2 must not include:

  - the final PR submit script
  - implementation commit (the coder implements, the orchestrator commits in Response 3)

================================================================================
=== Response 3 contract
================================================================================

Response 3 begins only after precommit-review is complete and the verdict is
pass or acceptable warning.

Response 3 must contain:

  1. Precommit-review assessment summary.
     The orchestrator reads reviews/precommit-review.yml, verifies:
       - verdict is pass or acceptable warning
       - no blockers exist (or blockers are resolved)
       - commit_readiness is ready
       - PLAN DRIFT GATE passed
       - NO-DRIFT CHECK passed
       - all claims in IMPLEMENTATION_REPORT.md are supported

  2. Exact implementation commit.
     The orchestrator commits all implementation files, test files, and
     IMPLEMENTATION_REPORT.md. The commit message must be evidence-based,
     derived from the PR description in PLAN.md.

  3. One idempotent PR submit script.
     A bash script placed in /tmp that:
       - starts with set -euo pipefail
       - contains a PR body heredoc with evidence-based content
       - runs git push -u origin with the current branch
       - detects an existing open PR by branch name
       - uses gh pr edit when an open PR exists
       - uses gh pr create when no open PR exists
       - uses main as the base branch
       - sets reviewer: zablose
       - sets assignees: zablose, alexredko10
       - runs gh pr merge "${PR_NUMBER}" --squash --delete-branch --auto
       - leaves the PR open if auto-merge cannot be enabled
       - prevents duplicate PR creation
       - uses evidence-based PR body content

Response 3 must not include:

  - a routine fourth orchestrator response for the same successful PR

================================================================================
=== Happy-path response count
================================================================================

Exactly three substantive orchestrator responses apply to the happy path.

The happy path is defined as:
  - plan-review passes
  - coder completes implementation without blockers
  - precommit-review passes
  - auto-merge succeeds

No fourth routine response is required for a successful PR.

The orchestrator must not issue additional routine command blocks after
Response 3 for the same PR.

================================================================================
=== Planning lock
================================================================================

PLAN.md and reviews/plan-review.yml must be committed together on the branch
before the coder prompt is issued.

After the planning commit, both artifacts are locked.

The coder must not edit PLAN.md or reviews/plan-review.yml.

The precommit-review must not edit PLAN.md or reviews/plan-review.yml.

If plan-review blocks (verdict is block or blockers exist):
  - coder and precommit-review prompts must not be issued
  - Response 2 may proceed only when verdict, blockers, warnings, and
    commit_readiness permit implementation

================================================================================
=== Plan-review blocked path
================================================================================

If plan-review returns verdict block or contains unresolved blockers:

  1. The orchestrator must not issue coder or precommit-review prompts.
  2. The orchestrator issues a repair response.
  3. The repair response contains an updated planner prompt incorporating
     the block reasons from reviews/plan-review.yml.
  4. The planner corrects PLAN.md accordingly.
  5. A new plan-review cycle runs on the corrected PLAN.md.
  6. The repair path may require additional responses beyond the three
     happy-path responses.

================================================================================
=== Coder blocked or continuation path
================================================================================

If the coder encounters blockers during implementation:

  1. The coder must stop and report blockers clearly.
  2. The orchestrator decides whether to issue a repair response or
     authorize a continuation/rerun.

Authorized continuation:
  - The coder re-reads the existing IMPLEMENTATION_REPORT.md.
  - The coder re-reads all existing implementation diffs.
  - The coder preserves correct PLAN-approved work.
  - The coder distinguishes pre-existing changes from new changes.
  - Destructive reset, restore, checkout, or clean commands are forbidden
    unless the human explicitly authorizes them.

Authorized rerun:
  - The coder re-reads PLAN.md completely.
  - The coder rewrites IMPLEMENTATION_REPORT.md.
  - Existing correct work may be preserved at the coder's discretion.

A new coder prompt following a blocked execution is a repair response,
not an additional happy-path response.

================================================================================
=== Precommit-review blocked path
================================================================================

If precommit-review returns verdict block or contains unresolved blockers:

  1. The orchestrator must not issue the implementation commit or PR script.
  2. The orchestrator issues a repair response.
  3. The repair response contains an updated coder prompt incorporating
     the block reasons from reviews/precommit-review.yml.
  4. The coder corrects the implementation accordingly.
  5. A new precommit-review cycle runs on the corrected implementation.
  6. The repair path may require additional responses beyond the three
     happy-path responses.

================================================================================
=== CI and reviewer repair path
================================================================================

After the PR is submitted via the Response 3 script:

  1. CI runs automatically. If CI fails, the orchestrator may issue
     additional repair responses.

  2. Human reviewer may request changes. If changes are requested, the
     orchestrator may issue additional repair responses.

  3. These repair responses are outside the three-response happy path.
     The happy path assumes CI passes and the reviewer approves.

  4. Auto-merge and branch deletion are platform responsibilities after
     the submit script.

================================================================================
=== Prompt construction rules
================================================================================

Every generated task prompt must follow the structure defined in
.project-memory/ORCHESTRATOR_STANDARD.txt.

Prompts must be plain text. Do not use markdown formatting inside prompts.

Prompts must include all mandatory sections enumerated by ORCHESTRATOR_STANDARD.

Prompts must respect ALLOWED FILES and FORBIDDEN FILES boundaries.

Prompts must not give agents git mutation authority unless explicitly
authorized for a specific runtime test.

================================================================================
=== Ariadne artifact lifecycle
================================================================================

Exact Ariadne artifact paths for every PR:

  1. .project-memory/pr/<pr-id>/PLAN.md — written by planner, reviewed by plan-review
  2. .project-memory/pr/<pr-id>/reviews/plan-review.yml — written by plan-review
  3. .project-memory/pr/<pr-id>/IMPLEMENTATION_REPORT.md — written by coder (handoff context, not proof)
  4. .project-memory/pr/<pr-id>/reviews/precommit-review.yml — written by precommit-review

Artifact lifecycle sequence:

  1. planner writes PLAN.md
  2. plan-review reviews PLAN.md, writes reviews/plan-review.yml
  3. planning lock commit: PLAN.md + reviews/plan-review.yml committed together
  4. coder implements, writes IMPLEMENTATION_REPORT.md
  5. precommit-review reviews implementation, writes reviews/precommit-review.yml
  6. implementation commit: all changed files committed
  7. PR submit script: creates or updates PR

================================================================================
=== PR submit script contract
================================================================================

The PR submit script must be a bash script placed in /tmp.

Mandatory requirements:

  1. set -euo pipefail as the first line after the shebang.
  2. PR body provided via heredoc with evidence-based content.
  3. git push -u origin with the current branch.
  4. Existing open PR detection by branch name.
  5. gh pr edit when an open PR exists for the branch.
  6. gh pr create when no open PR exists for the branch.
  7. Base branch: main.
  8. Reviewer: zablose.
  9. Assignees: zablose, alexredko10.
  10. Auto-merge: gh pr merge "${PR_NUMBER}" --squash --delete-branch --auto.
  11. Leave PR open if auto-merge cannot be enabled (gh prints a warning; the
      script must not treat this as a fatal error).
  12. Idempotent: no duplicate PR creation.
  13. Evidence-based PR body: derived from PLAN.md summary, not agent claims.

Prohibited:

  - gh pr checks --watch (CI waiting is a platform responsibility)
  - Any command that blocks waiting for CI
  - Multiple PR creation attempts without detection

================================================================================
=== "Next step" semantics
================================================================================

After the Response 3 submit script executes successfully, the next step is:

  The next roadmap PR iteration.

"Next step" is not another routine command block for the completed PR.

CI waiting, human review waiting, auto-merge, and branch deletion are platform
responsibilities after the submit script. The orchestrator does not continue
issuing commands for the completed PR unless a repair path is triggered.

================================================================================
=== No-fourth-routine-response rule
================================================================================

The happy path must not require a fourth orchestrator response for the same
successful PR.

The three responses cover the complete lifecycle:

  Response 1: plan
  Response 2: implement
  Response 3: submit

CI/CD waiting, review waiting, and merge are not orchestrator responses.
They are platform events.

================================================================================
=== Adoption and versioning
================================================================================

Version: 1.0.0.
Effective from: PR 0142A merge.
Maintained in: .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md.

Updates require a plan-review and precommit-review cycle.

This artifact is a mandatory companion to .project-memory/ORCHESTRATOR_STANDARD.txt.
Both must be read before orchestrating a PR lifecycle.

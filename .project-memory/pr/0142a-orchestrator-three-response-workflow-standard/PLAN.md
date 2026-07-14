# PR 0142A — Ariadne Three-Response Orchestrator Happy Path Standard Plan

## EVIDENCE SNAPSHOT

1. HEAD: `a8e97eb087fbb010837d65e61da9df2aac54db4a`
2. origin/main: `a8e97eb087fbb010837d65e61da9df2aac54db4a`
3. Merge base: `a8e97eb087fbb010837d65e61da9df2aac54db4a` (HEAD equals origin/main and merge base)
4. Branch: `0142a-orchestrator-three-response-workflow-standard`
5. Dirty tree: clean (no modified tracked files)
6. Cached diff: empty
7. Latest merged PR evidence: PR 0142 (Run Evidence Serialization Contract) present in `git log` at HEAD as `a8e97eb (HEAD -> 0142a-orchestrator-three-response-workflow-standard, origin/main, origin/HEAD, main) feat(task-intake): add runtime evidence serialization contract (#167)`
8. Workflow artifact inventory: `.project-memory/workflow/IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md` (one file)
9. AGENT_STANDARD.txt: ABSENT (verified by `test -e .project-memory/AGENT_STANDARD.txt`)
10. Unconditional AGENT_STANDARD references in ORCHESTRATOR_STANDARD.txt:
    - Line 31: `must remain compatible with .project-memory/AGENT_STANDARD.txt and the local agent files under agents/`
    - Line 150: `Rules must be derived from .project-memory/AGENT_STANDARD.txt and from task-specific non-negotiable constraints`
    - Line 241: `review schema defined by .project-memory/AGENT_STANDARD.txt and, where applicable, .project-memory/review-artifact.schema.yml`
11. Current ORCHESTRATOR_STANDARD version: 1.1 (line: `VERSION: 1.1`)
12. Current product roadmap PR 0143 definition:
    - ROADMAP.md: PR 0143 not listed in ROADMAP.md's active section (ROADMAP.md pauses at PR 0142 as the last substrate stream item and jumps to next active stream as Artifact Workspace Read-Only UI)
    - `.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md`: PR 0143 = "Artifact Workspace 4-Zone Shell Skeleton" (Stream 2: Artifact Workspace Shell, PR 0143-0147)

## ROADMAP ALIGNMENT

- roadmap track: Governance insertion — not a product roadmap stream
- expected PR slot: 0142A (inserted between PR 0142 and PR 0143)
- why this PR is next: Product stream PR 0142 (Run Evidence Serialization Contract) is complete. The human architect explicitly authorized one inserted governance PR before beginning product roadmap slot PR 0143. This PR codifies the current optimal orchestrator workflow as a durable repository artifact.
- batching policy check: This PR is documentation and governance only. No runtime code, tests, schemas, agents, dependencies, or GitHub workflow changes. ADR 0011 batching policy applies to product PRs; this PR is an architect-authorized governance insertion. No batching policy violation.
- drift heuristic check: Not triggered. This PR touches no runtime UI files. No consecutive UI PRs exist.
- architect sign-off required: yes
- architect sign-off reference: Human architect explicitly authorized one inserted governance PR before PR 0143 during the roadmap transition after PR 0142 completed.

### Governance Insertion Statement

1. Product stream PR 0142 (Run Evidence Serialization Contract) is complete.
2. Governance insertion is PR 0142A — it does not consume a product roadmap slot.
3. Product PR 0143 remains "Artifact Workspace 4-Zone Shell Skeleton" (Stream 2, Artifact Workspace Shell).
4. No product roadmap slots are renumbered. Later product streams (0143-0147, 0148-0152, etc.) retain their original numbers.
5. No frozen capability is unlocked.
6. No product capability is implemented.
7. The insertion is architect-authorized.

## TARGET IMPLEMENTATION SCOPE

The following implementation files are planned. Each file lists the exact text sections required.

### 1. .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md (NEW)

New normative workflow artifact defining the orchestrator's three-response happy path standard.

Required sections:

1. **Status and applicability** — artifact version, effective from PR 0142A merge, applies to orchestrator.
2. **Ariadne project identity** — the project name is Ariadne. No legacy project names (.grace, @grace, water_meter, Broken Clock, etc.). Examples from other projects may influence presentation only, never Ariadne facts.
3. **Roadmap-first rule** — every orchestrator cycle begins by reading ROADMAP.md, the product roadmap artifact, and ADR 0011. The roadmap determines the next PR slot. Governance insertions require explicit architect authorization.
4. **Evidence hierarchy** — agent output is not proof. Runtime-captured validation, command outputs, file contents, diffs, persisted runtime artifacts, and accepted proof refs remain proof. IMPLEMENTATION_REPORT.md is handoff context, not proof.
5. **Three-response happy path overview** — the happy path for one Ariadne PR iteration requires exactly three substantive orchestrator responses.
6. **Response 1 contract** — must contain: roadmap decision, clean main branch preparation, planner prompt (with roadmap alignment, exact branch, PR ID), plan-review prompt (with PLAN.md path, review schema reference).
7. **Response 2 contract** — must contain: plan-review assessment summary, planning lock commit block (PLAN.md + reviews/plan-review.yml committed together), coder prompt (with locked PLAN.md reference, plan-review verdict, IMPLEMENTATION_REPORT.md requirement, no PLAN.md/modify-planning-artifact authority), precommit-review prompt (with locked planning artifacts, IMPLEMENTATION_REPORT.md, review schema reference).
8. **Response 3 contract** — must contain: precommit-review assessment summary, exact implementation commit block, one idempotent PR submit script in /tmp.
9. **Happy-path response count** — exactly three substantive orchestrator responses for a successful PR. No fourth routine response required.
10. **Planning lock** — PLAN.md and reviews/plan-review.yml must be committed together before implementation prompts are run. After planning commit, both artifacts are locked. Coder and precommit-review must not edit locked planning artifacts. If plan-review blocks, coder and precommit-review prompts must not be issued. Response 2 may proceed only when verdict, blockers, warnings, and commit readiness permit implementation.
11. **Plan-review blocked path** — if plan-review blocks, a repair response is required. The orchestrator issues an updated planner prompt incorporating the block reasons. No coder prompt may be issued until a passing plan-review.
12. **Coder blocked or continuation path** — if coder encounters blockers, a repair response is required. Authorized continuation and authorized rerun handling defined. Destructive resets forbidden during authorized continuation unless the human explicitly authorizes them.
13. **Precommit-review blocked path** — if precommit-review blocks, implementation commit and PR script must not be issued. A repair response is required, returning to coder prompt with block reasons.
14. **CI and reviewer repair path** — CI failure or reviewer-requested repair may require additional repair responses beyond the three happy-path responses.
15. **Prompt construction rules** — every generated task prompt must follow the structure defined in ORCHESTRATOR_STANDARD.txt. Prompts must be plain text. Do not use markdown formatting inside prompts.
16. **Ariadne artifact lifecycle** — exact Ariadne artifact paths: `.project-memory/pr/<pr-id>/PLAN.md`, `reviews/plan-review.yml`, `IMPLEMENTATION_REPORT.md`, `reviews/precommit-review.yml`. Do not introduce PLAN_REVIEW.yaml, CODER_REPORT.txt, PRECOMMIT_REVIEW.yaml, master as base, or unrelated project terminology. Use main as base branch.
17. **PR submit script contract** — one /tmp bash script with set -euo pipefail. PR body heredoc. git push -u origin. Detection of existing open PR by branch. gh pr edit when PR exists. gh pr create when it does not. main as base. reviewer: zablose. assignees: zablose, alexredko10. gh pr merge "${PR_NUMBER}" --squash --delete-branch --auto. gh pr checks --watch is prohibited. Script leaves PR open if auto-merge cannot be enabled. Idempotent — no duplicate PR creation. PR body must be evidence-based.
18. **"Next step" semantics** — after a completed submit script, "next step" means start the next roadmap PR iteration. "Next step" must not be interpreted as another routine command block for the completed PR.
19. **No-fourth-routine-response rule** — the happy path must not require a fourth orchestrator response for the same successful PR. CI/CD waiting, review waiting, auto-merge, and branch deletion are platform responsibilities after the submit script.
20. **Adoption and versioning** — artifact version number, effective from PR 0142A merge, update process requires plan-review and precommit-review.

### 2. .project-memory/ORCHESTRATOR_STANDARD.txt (EDIT)

Narrow version 1.2 integration update.

Required bounded edits:

1. Bump version from `VERSION: 1.1` to `VERSION: 1.2`.
2. In the ORCHESTRATOR ROLE section, after the paragraph about agent names, add: "The orchestrator must also read `.project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md` before generating workflow responses. It is a mandatory companion to this standard."
3. In the MANDATORY TASK PROMPT STRUCTURE section or a new subsection, add: "The Ariadne PR lifecycle follows a three-response happy path defined in the companion workflow artifact. Blocked or failed paths may require additional repair responses."
4. In the PRECONDITION section, require reading the companion workflow artifact as part of precondition validation.
5. Preserve the existing mandatory task prompt structure (16 sections in exact order).
6. Preserve plain-text prompt rules.
7. Preserve strict ALLOWED FILES and FORBIDDEN FILES rules.
8. Preserve no-git-mutation authority for agents.
9. Preserve evidence-bound claims.
10. Correct references to absent AGENT_STANDARD.txt. The three unconditional references (lines 31, 150, 241) must be resolved as follows:
    - Line 31: `must remain compatible with .project-memory/AGENT_STANDARD.txt and the local agent files under agents/` — Change to `must remain compatible with the local agent files under agents/`.
    - Line 150: `Rules must be derived from .project-memory/AGENT_STANDARD.txt and from task-specific non-negotiable constraints` — Change to `Rules must be derived from the project-memory review-artifact schema and from task-specific non-negotiable constraints`.
    - Line 241: `review schema defined by .project-memory/AGENT_STANDARD.txt and, where applicable, .project-memory/review-artifact.schema.yml` — Change to `review schema defined by .project-memory/review-artifact.schema.yml`.
11. Do not create a replacement AGENT_STANDARD.txt.
12. Do not duplicate the entire companion artifact inside ORCHESTRATOR_STANDARD.
13. Make the companion authoritative for lifecycle sequencing.
14. Make ORCHESTRATOR_STANDARD authoritative for prompt construction.

### 3. ROADMAP.md (EDIT)

Bounded note recording PR 0142A governance insertion and preserving product PR 0143.

Required addition: After the "### PR 0142 — Run Evidence Serialization Contract" completion note (or in the Product Architecture Stream section), add a governance insertion entry:

```
### PR 0142A — Ariadne Three-Response Orchestrator Happy Path Standard (GOVERNANCE INSERTION)

This PR is a non-product governance insertion authorized by the human architect
between product PR 0142 (Run Evidence Serialization Contract) and product PR 0143
(Artifact Workspace 4-Zone Shell Skeleton).

PR 0142A codifies the current optimal orchestrator workflow as a durable
repository artifact. It does not consume or renumber product roadmap slot PR 0143.
No product capability is implemented. No frozen stream is opened.

PR 0143 remains the next product PR: Artifact Workspace 4-Zone Shell Skeleton.
```

### 4. .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md (EDIT)

Bounded note between PR 0142 and Stream 2 recording the non-product insertion without renumbering product slots.

Required addition: After the `PR 0142 — Run Evidence Serialization Contract` entry (Stream 1, Artifact Workspace Read Model), add a governance note:

```
### Governance Insertion: PR 0142A — Ariadne Three-Response Orchestrator Happy Path Standard

PR 0142A is a non-product governance insertion authorized by the human architect.
It does not consume a product roadmap slot and does not renumber later product slots.
PR 0143 remains the next product PR (Artifact Workspace Shell, Stream 2).
```

**Note about ROADMAP.md:** ROADMAP.md currently does not list individual PRs 0138-0142 in a detailed table within its body — the detailed sequence lives in the product roadmap artifact. However, the ROADMAP.md "Product Architecture Stream" section and the completion context must be consistent. If the existing ROADMAP.md text lists PR 0142 as the last stream item without a sequential itemization that would be broken by insertion, a bounded note at the end of the Product Architecture Stream section is sufficient. The exact location will be determined during implementation by finding the natural boundary after PR 0142 mentions.

**Note about the product roadmap artifact:** If the detailed roadmap already marks PR 0142 as the last Artifact Workspace Read Model PR and Stream 2 (0143-0147) starts immediately after, the governance insertion note goes between the two entries without renumbering.

### 5. .project-memory/pr/0142a-orchestrator-three-response-workflow-standard/IMPLEMENTATION_REPORT.md (NEW)

Coder handoff artifact. Must follow the IMPLEMENTATION_REPORT_TEMPLATE.md with all 11 required sections.

The implementation report is handoff context, not proof. Agent output is not proof. Actual files, diffs, validation output, dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK remain proof.

### 6. .project-memory/pr/0142a-orchestrator-three-response-workflow-standard/reviews/precommit-review.yml (NEW)

Final review artifact. Written by precommit-review agent following the review-artifact schema.

## ORCHESTRATOR STANDARD UPDATE — EXACT CHANGES

### Change 1: Version bump and companion reference (ORCHESTRATOR_STANDARD ARTIFACT TYPE INFORMATION section)

Replace the ARTIFACT TYPE INFORMATION section's version line:

Old: `Version: 1.1`
New: `Version: 1.2`

Old: `It serves as the system prompt and output contract for the Orchestrator agent.`
New: `It serves as the system prompt and output contract for the Orchestrator agent. The companion artifact .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md defines the workflow lifecycle and must be read before orchestrating a PR lifecycle.`

### Change 2: Adjust ORCHESTRATOR ROLE section

Old: `must remain compatible with .project-memory/AGENT_STANDARD.txt and the local agent files under agents/.`
New: `must remain compatible with the local agent files under agents/.`

Add after line ~33 (after the agent names list): `The orchestrator must read .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md before generating workflow responses. This document is a mandatory companion to ARIADNE ORCHESTRATOR STANDARD.`

### Change 3: Adjust HARD RULES section

Old line 150: `Rules must be derived from .project-memory/AGENT_STANDARD.txt and from task-specific non-negotiable constraints`
New: `Rules must be derived from the project-memory review-artifact schema and from task-specific non-negotiable constraints`

### Change 4: Adjust OUTPUT FORMAT section

Old line 241: `review schema defined by .project-memory/AGENT_STANDARD.txt and, where applicable, .project-memory/review-artifact.schema.yml`
New: `review schema defined by .project-memory/review-artifact.schema.yml`

### Change 5: Add three-response happy path requirement

In the ORCHESTRATOR RULES section, add a new rule after the existing rules:

`17. The Ariadne PR lifecycle follows a three-response happy path defined in .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md. Response 1 prepares the branch and issues planner and plan-review prompts. Response 2 evaluates plan-review, locks planning artifacts, and issues coder and precommit-review prompts. Response 3 evaluates precommit-review, commits implementation, and submits the PR. Blocked or failed paths may require additional repair responses. Do not require a fourth routine response for a successful PR.`

### Change 6: In MANDATORY TASK PROMPT STRUCTURE, PRECONDITION section

Add after the existing precondition text: `The orchestrator must read .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md before constructing the planner or coder prompt and ensure the prompt structure follows the three-response lifecycle stage.`

## ROADMAP INSERTION NOTE — EXACT TEXT

### ROADMAP.md insertion

Location: After the "Product Architecture Stream (ACTIVE)" section's PR 0142 description, before the "### Next active stream: Artifact Workspace Read-Only UI (0138+)" subsection.

Inserted text:

```
### PR 0142A — Ariadne Three-Response Orchestrator Happy Path Standard (GOVERNANCE INSERTION)

This PR is a non-product governance insertion authorized by the human architect
between product PR 0142 (Run Evidence Serialization Contract) and product PR 0143
(Artifact Workspace 4-Zone Shell Skeleton).

PR 0142A codifies the current optimal orchestrator workflow as a durable
repository artifact. It does not consume or renumber product roadmap slot PR 0143.
No product capability is implemented. No frozen stream is opened.

PR 0143 remains the next product PR: Artifact Workspace 4-Zone Shell Skeleton.
```

### Product roadmap artifact insertion

Location: In `.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md`, between Stream 1 (Artifact Workspace Read Model) completion point and Stream 2 (Artifact Workspace Shell) start.

```
### Governance Insertion: PR 0142A

PR 0142A is a non-product governance insertion authorized by the human architect.
It does not consume a product roadmap slot and does not renumber later product slots.
PR 0143 (Artifact Workspace 4-Zone Shell Skeleton) remains the next product PR.
```

## VALIDATION PLAN

### 1. Text-file existence checks

```bash
test -f .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md
```
Expected: file exists.
If not met: block.

```bash
test -f .project-memory/ORCHESTRATOR_STANDARD.txt
```
Expected: file exists.
If not met: block.

```bash
test -f ROADMAP.md
```
Expected: file exists.
If not met: block.

```bash
test -f .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
```
Expected: file exists.
If not met: block.

### 2. Physical readback

```bash
sed -n '1,70p' .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md
```
Expected: first 70 lines readable.
If not met: block.

```bash
head -20 .project-memory/ORCHESTRATOR_STANDARD.txt
```
Expected: version header readable.
If not met: block.

### 3. ORCHESTRATOR_STANDARD version 1.2

```bash
grep -n "VERSION: 1.2" .project-memory/ORCHESTRATOR_STANDARD.txt
```
Expected: version line present.
If not met: block.

### 4. Mandatory companion reference

```bash
grep -n "ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD" .project-memory/ORCHESTRATOR_STANDARD.txt
```
Expected: at least one reference.
If not met: block.

### 5. All 20 workflow sections

```bash
grep -n -E "Status and applicability|Ariadne project identity|Roadmap-first rule|Evidence hierarchy|Three-response happy path overview|Response 1 contract|Response 2 contract|Response 3 contract|Happy-path response count|Planning lock|Plan-review blocked path|Coder blocked or continuation path|Precommit-review blocked path|CI and reviewer repair path|Prompt construction rules|Ariadne artifact lifecycle|PR submit script contract|Next step semantics|No-fourth-routine-response rule|Adoption and versioning" .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md
```
Expected: all 20 section headings present.
If not met: block.

### 6. Exact three-response wording

```bash
grep -n -E "exactly three|three substantive|Response 1|Response 2|Response 3" .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md
```
Expected: three-response pattern present.
If not met: block.

### 7. Exact Ariadne artifact paths

```bash
grep -n -E "PLAN.md|plan-review.yml|IMPLEMENTATION_REPORT.md|precommit-review.yml" .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md
```
Expected: all four artifact paths referenced.
If not met: block.

### 8. main base branch

```bash
grep -n "main" .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md | grep -i "base\|branch"
```
Expected: main referenced as base branch.
If not met: block.

### 9. Reviewer and assignee requirements

```bash
grep -n "zablose\|alexredko10" .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md
```
Expected: reviewer (zablose) and assignees (zablose, alexredko10) present.
If not met: block.

### 10. Auto-merge command

```bash
grep -n "gh pr merge.*--squash.*--delete-branch.*--auto" .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md
```
Expected: auto-merge command present.
If not met: block.

### 11. Absence of gh pr checks --watch

```bash
grep -n "checks --watch\|checks.*--watch" .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md; echo "EXIT:$?"
```
Expected: no matches (exit code 1).
If not met: block.

### 12. Absence of foreign project identities and artifact names

```bash
grep -n -i "water_meter\|broken.clock\|daily-consumption\|\.grace\|@grace\|master.*base\|PLAN_REVIEW\|CODER_REPORT\|PRECOMMIT_REVIEW" .project-memory/workflow/ORCHESTRATOR_THREE_RESPONSE_HAPPY_PATH_STANDARD.md; echo "EXIT:$?"
```
Expected: no matches (exit code 1).
If not met: block.

### 13. Consistent PR 0142A roadmap notes

```bash
grep -n "0142A" ROADMAP.md .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
```
Expected: PR 0142A governance insertion noted in both files.
If not met: block.

### 14. Preservation of PR 0143 shell definition

```bash
grep -n "0143.*4-Zone Shell" .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
```
Expected: PR 0143 remains Artifact Workspace 4-Zone Shell Skeleton.
If not met: block.

```bash
grep -n "0143" ROADMAP.md; echo "EXIT:$?"
```
Expected: If PR 0143 is not explicitly mentioned in ROADMAP.md (which uses a different listing pattern), this is acceptable. If mentioned, it must remain unchanged as Artifact Workspace Shell.
If not met: warn.

### 15. AGENT_STANDARD reference consistency

```bash
grep -n "AGENT_STANDARD" .project-memory/ORCHESTRATOR_STANDARD.txt
```
Expected: No remaining unconditional references (lines 31, 150, 241 corrected). If any remain, they must be conditional, not executable requirements.
If not met: block.

### 16. Forbidden-path diff

```bash
git diff --name-only -- services/ tests/ schemas/ agents/ .github/ pyproject.toml poetry.lock docs/
```
Expected: empty.
If not met: block.

### 17. git diff --check

```bash
git diff --check
```
Expected: no whitespace errors.
If not met: block.

### 18. Dirty-tree state

```bash
git status --short
```
Expected: only approved governance files modified or untracked: workflow artifact, ORCHESTRATOR_STANDARD.txt, ROADMAP.md, product roadmap, PR 0142A artifacts.
If unknown untracked files exist: block.

### 19. Cached-diff state

```bash
git diff --cached --name-only
```
Expected: empty (no staged files).
If not met: block.

### 20. Implementation-report existence and readback

```bash
test -f .project-memory/pr/0142a-orchestrator-three-response-workflow-standard/IMPLEMENTATION_REPORT.md
```
Expected: file exists.
If not met: block.

```bash
sed -n '1,30p' .project-memory/pr/0142a-orchestrator-three-response-workflow-standard/IMPLEMENTATION_REPORT.md
```
Expected: first 30 lines readable including proof boundary disclaimer.
If not met: block.

## IMPLEMENTATION REPORT OBLIGATION

Per PR 0140 Implementation Handoff Artifact Contract, the coder must write:

`.project-memory/pr/0142a-orchestrator-three-response-workflow-standard/IMPLEMENTATION_REPORT.md`

The report must include all 11 standard sections:

1. TASK SUMMARY
2. FILES READ
3. FILES CHANGED
4. IMPLEMENTATION DECISIONS
5. PLAN ALIGNMENT
6. DEVIATIONS FROM PLAN
7. VALIDATION RUN
8. BOUNDARY CONFIRMATIONS
9. NON-GOALS PRESERVED
10. RISKS OR WARNINGS
11. NEXT REVIEWER FOCUS

The implementation report is handoff context, not proof. Agent output is not proof. Actual files, diffs, validation output, dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK remain proof.

### Fresh run handling

This PR starts from a clean main branch. The implementation is a fresh execution. All files are created or edited fresh.

### Authorized continuation handling

Not applicable — this is a fresh run.

### Authorized rerun handling

If a rerun is authorized, the existing PLAN.md governs. Coder must verify locked planning artifacts are unchanged, then re-execute implementation according to PLAN.md.

### Unexplained pre-existing report handling

No pre-existing implementation report is expected. If one exists, the reviewer must verify it matches PLAN.md and flag it. If it does not match, block.

## PLAN DRIFT GATE

Block implementation completion if:

1. Any file outside approved scope changes.
2. Runtime code or tests change.
3. Agent YAML files change.
4. Schemas or dependencies change.
5. Product PR 0143 is renumbered or replaced.
6. Later product streams (0144+) are reordered.
7. Foreign project content (water_meter, Broken Clock, .grace, etc.) appears.
8. Ariadne artifact paths (PLAN.md, plan-review.yml, IMPLEMENTATION_REPORT.md, precommit-review.yml) are replaced with unrelated artifact names (PLAN_REVIEW.yaml, CODER_REPORT.txt, PRECOMMIT_REVIEW.yaml).
9. The workflow companion does not define exactly three happy-path responses.
10. Blocked paths are incorrectly forced into three responses.
11. Planning lock is missing from the workflow companion.
12. IMPLEMENTATION_REPORT.md is omitted.
13. PR submit script requirements are incomplete (missing set -euo pipefail, missing reviewer/assignee, missing auto-merge command, present gh pr checks --watch).
14. gh pr checks --watch is permitted anywhere.
15. Reviewer (zablose) or assignees (zablose, alexredko10) drift.
16. ORCHESTRATOR_STANDARD does not require the companion workflow artifact.
17. AGENT_STANDARD references remain as executable contradictions after verified absence — the three unconditional references in ORCHESTRATOR_STANDARD.txt must be corrected.
18. Validation is absent or failing.
19. Unknown untracked files exist.
20. Generated residue enters commit payload.

## NO-DRIFT CHECK

Require confirmation:

1. Correct branch: `0142a-orchestrator-three-response-workflow-standard`.
2. Only approved governance files changed (workflow artifact, ORCHESTRATOR_STANDARD.txt, ROADMAP.md, product roadmap, PR 0142A artifacts).
3. Planning artifacts remained locked — PLAN.md and reviews/plan-review.yml not modified by coder or precommit-review.
4. Workflow companion artifact exists and contains all 20 required sections.
5. ORCHESTRATOR_STANDARD is version 1.2.
6. Companion-read requirement exists in ORCHESTRATOR_STANDARD.
7. Exactly three happy-path responses are defined.
8. Repair paths (plan-review blocked, coder blocked, precommit-review blocked, CI/reviewer repair) remain separate from the happy path.
9. Exact Ariadne artifact lifecycle is used: PLAN.md, reviews/plan-review.yml, IMPLEMENTATION_REPORT.md, reviews/precommit-review.yml.
10. main remains base branch.
11. zablose is reviewer.
12. zablose and alexredko10 are assignees.
13. Auto-merge command is correct: `gh pr merge "${PR_NUMBER}" --squash --delete-branch --auto`.
14. gh pr checks --watch is prohibited.
15. "Next step" semantics are explicit: next roadmap PR iteration, not another command for the completed PR.
16. PR 0142A roadmap insertion is consistent in both ROADMAP.md and the detailed product roadmap.
17. Product PR 0143 remains unchanged as Artifact Workspace 4-Zone Shell Skeleton.
18. No foreign project content exists.
19. No runtime or product behavior changed.
20. IMPLEMENTATION_REPORT.md exists and was read back.
21. PLAN DRIFT GATE passed.
22. Actual evidence overrides agent claims.

## STOP CONDITIONS

Implementation must stop if:

1. Product PR 0143 cannot remain unrenumbered.
2. Workflow guidance conflicts irreconcilably with committed Ariadne standards (ORCHESTRATOR_STANDARD.txt, review-artifact.schema.yml, agent files).
3. More than the approved governance files must change.
4. Runtime code, tests, schemas, agents, dependencies, or GitHub workflows must change.
5. AGENT_STANDARD inconsistency cannot be corrected narrowly — the three unconditional references in ORCHESTRATOR_STANDARD.txt must be correctable with minimal edits.
6. Exact three-response semantics cannot be expressed without contradicting review gates (plan-review and precommit-review must remain as gates).
7. Required validation fails.

## NON-GOALS

1. Implementing the workflow artifact (this is a planning task only).
2. Editing ORCHESTRATOR_STANDARD during planning.
3. Editing ROADMAP.md during planning.
4. Editing the detailed product roadmap during planning.
5. Writing plan-review.yml during planning.
6. Writing IMPLEMENTATION_REPORT.md during planning.
7. Writing precommit-review.yml during planning.
8. Creating AGENT_STANDARD.txt.
9. Modifying runtime code.
10. Modifying tests.
11. Modifying schemas.
12. Modifying agent YAML files.
13. Modifying dependencies.
14. Modifying GitHub workflows.
15. Implementing Artifact Workspace Shell.
16. Implementing product PR 0143.
17. Renumbering product roadmap slots.
18. Opening later streams.
19. Committing, pushing, or creating a pull request during planning.
20. Removing or rewriting existing ORCHESTRATOR_STANDARD sections beyond the narrow AGENT_STANDARD reference corrections and companion requirement additions.

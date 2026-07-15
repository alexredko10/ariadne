# PR 0147 — Artifact Workspace Proof and Manifest Viewer Plan

## EVIDENCE SNAPSHOT

1. HEAD: `c7e3e7640cfec684aba1d8f1857d7c311716c26a`
2. origin/main: `c7e3e7640cfec684aba1d8f1857d7c311716c26a`
3. Merge base: `c7e3e7640cfec684aba1d8f1857d7c311716c26a`
4. Branch: `0147-artifact-workspace-proof-manifest-viewer`
5. Dirty tree: clean
6. Cached diff: empty
7. PR 0146 merge evidence: `c7e3e76 (HEAD -> 0147-..., origin/main, origin/HEAD, main) PR 0146 — Artifact Workspace Run Report Viewer (#172)`
8. PR 0147 roadmap definition: `.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md` L222 — PR 0147 = Proof and Manifest Viewer. Acceptance: "Manifest entries visible. Proof refs clearly separated from agent claims. Command captures/logs visible when available. No proof acceptance mutation yet."

## MANIFEST PERSISTENCE INVENTORY

| Property | Value | Evidence source |
|---|---|---|
| Filename | `manifest.json` | run_persistence.py L276 |
| Schema | `{"schema_version": "1", "run_id": "...", "run_json_hash": "...", "files": ["run.json", "run-report.txt"]}` | run_persistence.py L276-280 |
| files array | Array of filename strings — "run.json" always, "run-report.txt" conditionally | run_persistence.py L274-275 |
| Hash per file | None — only run_json_hash at the manifest level | run_persistence.py L278 |
| Artifact types | None — files are plain string names with no type classification | runtime_evidence.py L320 |
| Unsupported entries | None — the schema is strictly string array | — |
| Missing state | MissingEvidenceNotice with reason "file_not_found" | runtime_evidence.py L315-317 |
| Malformed state | MissingEvidenceNotice with reason "malformed_json" | runtime_evidence.py L318-320 |

## PROOF-REFERENCE INVENTORY

| Property | Value | Evidence source |
|---|---|---|
| proof_refs in persisted evidence | **Does not exist** — no proof_ref key in run.json or manifest.json | Checked run_persistence.py: run.json data has no proof_ref field |
| ArtifactEvidenceRef | Defined in runtime_evidence.py as `path`, `exists`, `file_size`, `description` | runtime_evidence.py L61-65 |
| ArtifactEvidenceRef usage | Defined but **never constructed** in the read_model functions | runtime_evidence.py L61-65 (dataclass only) |
| evidence_paths in serialized detail | Array of absolute file paths (run.json, manifest.json, run-report.txt) | runtime_evidence.py L341-347 |
| PR URL as proof ref | Extracted from execution_results where operation="gh_pr_create" | runtime_evidence.py L143-152 |

## EXECUTION RESULT INVENTORY

| Property | Value | Evidence source |
|---|---|---|
| execution_results type | tuple[dict[str, str], ...] | ariadne_task_cli.py L111 |
| Typical keys | operation (str), exit_code (str) | git_boundary.py execution_results |
| stdout/stderr | **Not stored** in execution_results | — |
| capture paths | **Not stored** in execution_results | — |
| log paths | **Not stored** in execution_results | — |
| source_errors | tuple[str, ...] — free-form error strings from reading evidence | runtime_evidence.py L354 |

## CAPTURE AND LOG INVENTORY

| Property | Value | Evidence source |
|---|---|---|
| captures/ directory | Runtime cleanup directory, removed by _cleanup_runtime_residue() | ariadne_task_cli.py L616-630 |
| Captures as persisted evidence | **Not persisted** — captures are temporary runtime artifacts | ariadne_task_cli.py L891 |
| Log files | **Not stored** per-run — no logs/ directory pattern | — |
| Execution stdout/stderr | **Not captured** in run.json or manifest | — |

## OPTION DECISION

### Decision: OPTION A — EXISTING DETAIL AND REPORT CONTRACTS

No new backend endpoint is required. The existing `GET /runs/<run_id>` detail response and `GET /runs/<run_id>/report` already expose all available data: manifest_files, evidence_paths, execution_results, run_json_hash, source_errors. The viewer renders these existing fields into the Gates & Proofs and Logs & Captures zones.

**Why Option A satisfies every PR 0147 acceptance criterion:**

1. **Manifest entries visible**: `detail.manifest_files` provides the list of filenames from manifest.json. Gates & Proofs renders them as clearly labelled "Runtime Evidence" entries.
2. **Proof refs clearly separated from claims**: No proof_refs exist in the current data model. The available classification is: runtime evidence (manifest files, evidence paths), evidence references (paths to persisted files), and agent claims (PR URL metadata from execution_results). The viewer labels each category explicitly.
3. **Command captures/logs visible when available**: The current model stores no per-command stdout/stderr or log files. Execution results contain only operation names and exit_codes. The viewer presents these as "Execution Summary" (not "command captures") with an explicit note that stdout/stderr is not captured.
4. **No mutation**: No new backend endpoint. No file writing. No approval controls.

**Why Option A is backward compatible**: No new route, no serializer change, no read-model change. Workspace JavaScript reads the same `renderDetail(data)` response and the existing report endpoint — just rendering additional fields into the right and bottom zones.

**Why Option A does not fabricate**: All displayed values come from the existing versioned JSON contracts. Fields that do not exist (captures, stderr, stdout, proof hashes) are labelled "not available".

## READ-ONLY API CONTRACT

The viewer consumes only:

1. **GET /runs/<run_id>** — existing version-1 detail response, for summary, detail (manifest_files, evidence_paths, execution_results, run_json_hash, source_errors), and missing/malformed notices.
2. **GET /runs/<run_id>/report** — existing version-1 report response, for report_exists, provenance.

No new route, no serializer change, no read-model change.

## EVIDENCE CLASSIFICATION CONTRACT

| Classification | Source | Persisted source | Linkage predicate | Visible label | Prohibited claim |
|---|---|---|---|---|---|
| Runtime evidence | detail.manifest_files | manifest.json | run.json exists and parsed | "Runtime Evidence: manifest.json lists file" | "Verified proof" |
| Evidence reference | detail.evidence_paths | File system co-location | run.json exists and file exists | "Evidence path" | "Accepted proof" |
| Execution summary | detail.execution_results | run.json | run.json exists | "Execution Result: operation_name" | "Command verified" |
| Agent metadata | execution_results pr_url | run.json | operation="gh_pr_create" | "PR URL (from agent execution)" | "PR accepted" |
| Run JSON hash | detail.run_json_hash | run.json + manifest.json | manifest contains run_json_hash | "Run JSON hash (as recorded)" | "Hash verified" |
| Source errors | detail.source_errors | runtime_evidence read | Read failure occurred | "Source error" | "Error resolved" |
| Report provenance | GET /runs/<run_id>/report -> provenance | manifest.json | manifest lists run-report.txt | "Report provenance: linked" / "unavailable" | "Report verified as proof" |
| Captures/logs | Not available | Not persisted | Always unavailable | "Command captures and logs are not stored in the current run evidence model." | N/A — always unavailable |

## MANIFEST VIEWER CONTRACT (Gates & Proofs zone)

| Property | Value |
|---|---|
| Zone root | `#zone-gates-proofs` |
| Heading | h2 "Gates & Proofs" (unchanged from PR 0143-0145) |
| Viewer container | `#gates-content` — added inside the zone, below the heading |
| Section header | h3 "Manifest Files" |
| Section purpose | Display files listed in manifest.json for the selected run |
| Entry format | Each manifest file listed with: filename (safeText), and note "Listed in manifest.json" |
| Entry ordering | Preserve order from detail.manifest_files array |
| Empty manifest | "No manifest files available. Run a task to generate manifest evidence." |
| Missing manifest | "Manifest not available. The manifest.json file is missing or unreadable." (reuse existing detail error states) |
| Malformed manifest | "Manifest evidence is malformed (from detail notices)" |
| No selected run | Zone retains its original placeholder text |
| Hash display | Run JSON hash from detail.run_json_hash displayed as "Run JSON hash: <hash>" with label "(as recorded in manifest)" |
| Forbidden | No file: links. No clickable paths. No arbitrary file-open controls. No download. |

### Manifest state handling

The existing `renderDetail(data)` already receives `data.detail.manifest_files`. The viewer reads this from the same renderDetail function. State handling:

| State | Render behavior |
|---|---|
| Selected run, manifest_files available | Render file list |
| Selected run, manifest_files empty [] | "Manifest file list is empty." |
| Selected run, ok=false | Summary/detail may be null — show "Manifest not available" |
| Selected run, no detail | Already handled by detail state contract — "Detail evidence not available." |
| No selected run | Original zone placeholder |

## PROOF / EVIDENCE VIEWER CONTRACT (Gates & Proofs zone, second section)

| Property | Value |
|---|---|
| Section header | h3 "Evidence Paths" |
| Section purpose | Display evidence file references |
| Entry format | Each path rendered as inert text (safeText). Prefixed with "Evidence path:" label. |
| Empty evidence_paths | "No evidence paths available." |
| No selected run | Not shown (zone placeholder active) |
| Classification label | Each entry is labeled "Runtime evidence stored at:" for paths that exist |
| Hash section | Separate sub-section "Run JSON Hash" showing run_json_hash with label "As recorded in manifest" |
| Source errors section | Separate sub-section "Source Errors" showing source_errors entries |
| Agent claims section | If PR URL exists, show "Agent-performed operation: gh_pr_create" with URL rendered using isSafeUrl policy |
| Forbidden | No proof acceptance. No approve/reject. No gate mutation. No hash verification claim. |

## CAPTURES AND LOGS VIEWER CONTRACT (Logs & Captures zone)

| Property | Value |
|---|---|
| Zone root | `#zone-logs-captures` |
| Heading | h2 "Logs & Captures" (unchanged) |
| Viewer container | `#logs-content` — added inside the zone, below the heading |
| Default state (no captures/logs) | "Command captures and logs are not stored in the current run evidence model. Each execution result shows only operation name and exit code. stdout, stderr, and command output are not captured." |
| Execution summary section | When a run is selected, show h3 "Execution Summary" listing each execution result with operation and exit_code via safeText |
| Empty execution_results | "No execution results recorded." |
| Source errors section | When present, show h3 "Source Errors" listing each error string via safeText |
| Forbidden | No fabricated stdout/stderr. No automatic linkification. No command execution. No ANSI interpretation. No shell commands. |

### Captures/logs state machine

| State | Render behavior |
|---|---|
| No selected run | Original zone placeholder |
| Selected, execution_results with entries | Render execution summary table |
| Selected, execution_results empty [] | "No execution results recorded." |
| Selected, source_errors with entries | Append source errors section |
| Selected, no source_errors | No source errors section |
| Selected, detail not available | Detail unavailable state propagated (same as canvas) |

## SELECTED-RUN REQUEST CONTRACT

| Property | Value |
|---|---|
| Data source | Reuses existing `renderDetail()` response — no additional HTTP requests |
| Run_id encoding | Existing `encodeURIComponent(runId)` unchanged |
| Stale protection | Existing `detailRequestCounter` — gates/logs content is re-rendered from the same detail response |
| Loading state | Gates & Proofs and Logs & Captures show "... loading" text when detail is being fetched |
| No additional requests | Gates/Proofs and Logs/Captures render from the same `data` object already passed to renderDetail |
| Report data | Report viewer already fetches via fetchReport. Gates/Proofs may reuse report_exists/provenance from the stored report response if needed |
| Cleanup on selection change | Old gates/logs content is removed before new content is rendered |

## PR 0145 PRESERVATION CONTRACT

| Behavior | How preserved |
|---|---|
| Timeline live list (fetchRuns, renderRunList) | Unchanged |
| Selected-run aria-selected | Unchanged |
| encodeURIComponent | Unchanged |
| detailRequestCounter | Unchanged |
| Bounded detail rows in #detail-content | Unchanged — gates/logs are separate zones, not in #detail-content |
| Missing/malformed evidence notices in detail | Unchanged |
| Safe URL policy | Unchanged |
| Evidence paths as non-clickable text | Unchanged — gates zone also renders paths as text |
| detail-loading, detail state messages | Unchanged |

## PR 0146 PRESERVATION CONTRACT

| Behavior | How preserved |
|---|---|
| Report viewer (#report-viewer, #report-text, #report-provenance) | Unchanged — not moved or modified |
| fetchReport | Unchanged |
| Report states (loading, complete, missing, etc.) | Unchanged |
| Report provenance label | Unchanged — gates zone may reference report_exists from separate storage |

## PR 0147A / 0147B DEFERRAL CONTRACT

| Capability | Status |
|---|---|
| PR 0147A Local Operator Launch and End-to-End Smoke | Deferred — no agent-launch or execution controls in this PR |
| PR 0147B Human-Gated Manual Orchestration Mode | Deferred — no orchestration, gating, or launch UX in this PR |
| PR 0147C Domain-neutral / dogfood | Deferred beyond these PRs |
| Visual Gate (PR 0148+) | Deferred — no gate mutation, mermaid rendering, or diagram viewers |
| Artifact Registry | Deferred |
| Proof acceptance | Deferred |

## ACCESSIBILITY CONTRACT

| Property | Value |
|---|---|
| Gates & Proofs zone | `role="region"`, `aria-labelledby="zone-gates-proofs-heading"` — unchanged |
| Logs & Captures zone | `role="region"`, `aria-labelledby="zone-logs-captures-heading"` — unchanged |
| New section headings | h3 "Manifest Files", h3 "Evidence Paths", h3 "Execution Summary", h3 "Source Errors" |
| Entry format | Text spans using safeText — no interactive controls |
| Keyboard | No new interactive elements — gate zones are read-only display |
| Loading state | Visible text in each zone |
| No selected run | Zone retains existing placeholder |

## SAFE-RENDERING CONTRACT

| Rule | Value |
|---|---|
| All runtime values | Rendered via safeText(textContent) or escHtml for HTML attributes |
| innerHTML | Static structural templates only — no runtime values concatenated |
| Event handlers | No event handlers built from runtime data |
| eval | Prohibited |
| Function constructors | Prohibited |
| document.write | Prohibited |
| iframe srcdoc | Prohibited |
| Clickable file links | Prohibited — evidence_paths rendered as text, not anchors |
| URL linkification | Prohibited — no automatic linking in gate/log zones |
| External assets | Prohibited |

## IMPLEMENTATION FILE SCOPE

### Approved files

#### 1. services/task_intake/src/task_intake/artifact_workspace.py (EDIT)

**Action**: Edit.
**Exact responsibility**: Add gates/proofs and logs/captures rendering functions that consume the existing detail and report response data.

**Exact expected additions**:
- `renderGatesProofs(data, reportData)` — updates `#zone-gates-proofs` with manifest files section, evidence paths section, and provenance information from the detail response
- `renderLogsCaptures(data)` — updates `#zone-logs-captures` with execution summary table and source errors section
- In `renderDetail(data)`, after rendering `#detail-content`, call both zone renderers
- In `selectRun()`, after the detail fetch completes, pass data to zone renderers
- Loading state: when detail is being fetched, zone content shows "Loading..." text
- Empty/unavailable states per the viewer contracts above
- CSS for gate/log zone sections (section headings within zones, entry formatting)

**Existing unchanged**: All timeline code (fetchRuns, renderRunList), detail code (renderDetail, selectRun, detailRequestCounter, escHtml, safeText, isSafeUrl), report viewer (fetchReport, renderReport), zone IDs and headings, responsive layout.

**Content prohibited**: No new HTTP requests. No modification to existing zone IDs or headings. No proof acceptance. No artifact mutation. No agent launch. No execution commands. No external assets.

#### 2. services/task_intake/tests/test_artifact_workspace_shell.py (EDIT)

**Action**: Edit (add new test class for gates/proofs/logs/captures viewer contracts).

**Exact expected additions**: Tests for:
- Gates & Proofs shows manifest files when detail contains them
- Gates & Proofs shows "Manifest file list is empty" when manifest_files is []
- Gates & Proofs shows evidence paths as text (not links)
- Gates & Proofs shows run JSON hash
- Gates & Proofs shows "not available" when no run selected
- Logs & Captures shows execution summary when execution_results present
- Logs & Captures shows "No execution results recorded" when empty
- Logs & Captures shows source errors when present
- Logs & Captures shows default text about no captures/logs stored
- Hostile strings in execution_results/evidence_paths rendered as safe text
- No mutation controls in gate/log zones
- PR 0145 detail rendering regression
- PR 0146 report rendering regression
- GET /workspace regression
- GET / regression
- GET /runs regression
- GET /runs/<run_id> regression
- GET /runs/<run_id>/report regression

**Existing unchanged**: All existing detail, report, timeline, zone, and mutation tests.

#### 3. .project-memory/pr/0147-artifact-workspace-proof-manifest-viewer/IMPLEMENTATION_REPORT.md (NEW)

All 11 required sections.

#### 4. .project-memory/pr/0147-artifact-workspace-proof-manifest-viewer/reviews/precommit-review.yml (NEW)

Follows review-artifact.schema.yml.

### Not modified

- services/runner/src/runner/runtime_evidence.py
- services/runner/src/runner/run_persistence.py
- services/runner/tests/test_runtime_evidence.py
- services/runner/tests/test_run_persistence.py
- services/task_intake/src/task_intake/server.py
- services/task_intake/src/task_intake/runtime_evidence_serialization.py
- services/task_intake/tests/test_local_run_history_in_page.py
- services/task_intake/tests/test_runtime_evidence_serialization_contract.py
- services/task_intake/tests/test_task_intake.py
- ROADMAP.md, agents/**, schemas/**, docs/**, .github/**, pyproject.toml, etc.

## TEST PLAN

### 1. PR 0147 Gates/Proofs and Logs/Captures Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "Gates or Proofs or Logs or Captures or manifest or evidence_path or execution_summary" -q
```

Expected: all gate/log viewer tests pass.
If not met: block.

### 2. Existing Workspace Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "not Gates and not Proofs and not Logs and not Captures" -q
```

Expected: all existing workspace tests pass.
If not met: block.

### 3. Existing Detail API Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_local_run_history_in_page.py -q
```

Expected: all 73+ tests pass.
If not met: block.

### 4. Report API Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "Report or report" -q
```

Expected: all report tests pass.
If not met: block.

### 5. Serialization Contract Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_runtime_evidence_serialization_contract.py -q
```

Expected: all 61+ tests pass.
If not met: block.

### 6. Runtime Evidence Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_runtime_evidence.py -q
```

Expected: all 32 tests pass.
If not met: block.

### 7. Python Compile

```bash
python -m compileall -f services/task_intake/src services/runner/src
```

Expected: all files compile.
If not met: block.

### 8. Manifest Schema Grep

```bash
grep -n "manifest_files" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: manifest_files referenced from detail response.
If not met: block.

### 9. Proof-Reference Fabrication Grep

```bash
grep -n -i "proof_ref\|proof_refs\|proof ref" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: no proof_ref references (exit code 1) — proof_refs are not rendered.
If not met: block.

### 10. Capture/Log Fabrication Grep

```bash
grep -n -i "stdout\|stderr\|captured\|log.*file\|command.*captur" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: only the explicit "not available" text for captures/logs. No fabricated stdout/stderr.
If not met: block.

### 11. Runtime-Evidence versus Agent-Claim Label Grep

```bash
grep -n -E "Runtime evidence|Evidence path|Execution result|Agent-performed|as recorded|not verified" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: classification labels present.
If not met: block.

### 12. Inert Path Rendering Grep

```bash
grep -n -E "evidence_path|file: href|file.*link|clickable" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: paths rendered as text (textContent/safeText), not clickable.
If not met: block.

### 13. Unsafe-Rendering Prohibition Grep

```bash
grep -n -E "innerHTML|eval|Function\(|document.write|srcdoc|javascript:" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: innerHTML only for static structural templates. No eval/Function/document.write/srcdoc/javascript:.
If not met: block.

### 14. Mutation-Control Prohibition Grep

```bash
grep -n -i -E "accept|reject|approve|retry|rerun|regenerat|edit|delet|commit|push|merge|pr create|gh pr|agent.*launch" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: no mutation controls.
If not met: block.

### 15. External-Asset Prohibition Grep

```bash
grep -n -i -E "https?://|//[a-z]+\." services/task_intake/src/task_intake/artifact_workspace.py; echo "EXIT:$?"
```

Expected: no matches (exit code 1).
If not met: block.

### 16. PR 0147A/0147B Deferral Grep

```bash
grep -n -i -E "launch|orchestrat|execute.*button|run.*button" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: no launch/orchestration controls.
If not met: block.

### 17. Forbidden-Path Diff

```bash
git diff --name-only -- services/runner/src/runner/runtime_evidence.py services/runner/src/runner/run_persistence.py services/task_intake/src/task_intake/server.py services/task_intake/src/task_intake/runtime_evidence_serialization.py services/runner/tests/ services/task_intake/tests/test_local_run_history_in_page.py services/task_intake/tests/test_runtime_evidence_serialization_contract.py services/task_intake/tests/test_task_intake.py
```

Expected: empty.
If not met: block.

### 18. Planning-Lock Diff

```bash
git diff -- .project-memory/pr/0147-artifact-workspace-proof-manifest-viewer/PLAN.md .project-memory/pr/0147-artifact-workspace-proof-manifest-viewer/reviews/plan-review.yml
```

Expected: no differences.
If not met: block.

### 19. Whitespace Check

```bash
git diff --check
```

Expected: no whitespace errors.
If not met: block.

### 20. Dirty-Tree and Cached-Diff

```bash
git status --short && git diff --cached --name-only
```

Expected: only artifact_workspace.py (modified), test_artifact_workspace_shell.py (modified), PR artifacts. Cached diff empty.
If not met: block.

### 21. IMPLEMENTATION_REPORT.md Existence and Readback

```bash
test -f .project-memory/pr/0147-artifact-workspace-proof-manifest-viewer/IMPLEMENTATION_REPORT.md && sed -n '1,30p' .project-memory/pr/0147-artifact-workspace-proof-manifest-viewer/IMPLEMENTATION_REPORT.md
```

Expected: file exists with proof disclaimer.
If not met: block.

## IMPLEMENTATION REPORT OBLIGATION

`.project-memory/pr/0147-artifact-workspace-proof-manifest-viewer/IMPLEMENTATION_REPORT.md` — all 11 standard sections. Report is handoff context, not proof.

## PLAN DRIFT GATE

Block implementation completion if:

1. Any file outside approved scope changes.
2. PLAN.md or plan-review.yml changes.
3. OPTION A is not followed — a new backend route or serializer change is introduced.
4. Manifest fields are fabricated (fields that don't exist in the actual manifest schema).
5. Proof references are fabricated (proof_refs that don't exist in persisted evidence).
6. Agent claims are represented as runtime proof.
7. Paths are represented as verified proof without evidence.
8. Hashes are represented as verified without comparison.
9. Acceptance or approval is inferred.
10. Missing evidence is represented as empty success.
11. Malformed evidence is represented as missing.
12. Captures or logs are fabricated from execution summaries (stdout/stderr that was never captured).
13. Arbitrary filesystem paths are accepted.
14. Persisted run evidence is modified.
15. Existing GET routes break.
16. PR 0145 selected-run/detail behavior breaks.
17. PR 0146 report behavior breaks.
18. Runtime values enter unsafe HTML.
19. Proof acceptance or artifact mutation is added.
20. Agent launch or orchestration is added.
21. Git or PR authority is added.
22. PR 0147A, PR 0147B, or later roadmap work is absorbed.
23. External assets, dependencies, or build tooling are added.
24. Required viewer states are absent.
25. Required tests are weak or failing.
26. IMPLEMENTATION_REPORT.md is absent or incomplete.
27. Unknown untracked files exist.

## NO-DRIFT CHECK

Require confirmation:

1. Correct branch: `0147-artifact-workspace-proof-manifest-viewer`.
2. Only approved files changed: artifact_workspace.py (edit), test_artifact_workspace_shell.py (edit), IMPLEMENTATION_REPORT.md (new), precommit-review.yml (new).
3. Planning artifacts remain locked.
4. PR 0147 scope is preserved (Proof and Manifest Viewer — not orchestration/launch).
5. PR 0147A and PR 0147B remain separate.
6. PR 0148 remains separate.
7. OPTION A is implemented (no new backend endpoint).
8. Existing routes remain compatible.
9. Selected-run behavior remains intact.
10. Manifest source is exact (manifest_files from detail response).
11. Manifest entries are honestly bounded (only filename strings).
12. Runtime evidence is labelled separately ("Runtime evidence: manifest.json lists file").
13. Evidence references are labelled separately ("Evidence path").
14. Agent claims are labelled separately ("Agent-performed operation").
15. Unavailable state exists.
16. Empty manifest state exists.
17. Missing manifest state exists.
18. Malformed manifest state exists.
19. Unsupported-entry state exists.
20. Capture/log unavailable state exists (with explanation text).
21. Paths render as inert text.
22. Hashes are not falsely described as verified.
23. Command text remains inert.
24. Stale-response protection exists (detailRequestCounter).
25. PR 0145 detail behavior remains intact.
26. PR 0146 report behavior remains intact.
27. No proof acceptance or mutation exists.
28. No agent launch or orchestration exists.
29. No arbitrary filesystem input exists.
30. No external assets or dependencies exist.
31. Required tests pass.
32. IMPLEMENTATION_REPORT.md exists and was read back.
33. PLAN DRIFT GATE passed.
34. Actual evidence overrides agent claims.

## STOP CONDITIONS

Implementation must stop if:

1. A new backend endpoint appears necessary.
2. An arbitrary path input is required.
3. Persisted evidence would need mutation.
4. A breaking contract change is required.
5. PR 0147A/0147B scope is required.
6. An unapproved file must change.
7. Safe rendering cannot be guaranteed.
8. Required validation fails.

## NON-GOALS

1. Implementing the viewer (planning task only).
2. Editing source or tests during planning.
3. Writing plan-review.yml, IMPLEMENTATION_REPORT.md, or precommit-review.yml during planning.
4. Adding a new backend endpoint.
5. Modifying runtime_evidence.py, run_persistence.py, runtime_evidence_serialization.py, or server.py.
6. Adding arbitrary file browsing.
7. Adding proof acceptance or artifact mutation.
8. Adding agent launch or orchestration.
9. Adding git or PR controls.
10. Implementing PR 0147A, PR 0147B, or PR 0148 work.
11. Adding external assets or dependencies.
12. Committing, pushing, or creating a pull request.

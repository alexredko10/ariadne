# PR 0148 — Mermaid Artifact Type Read Model Plan

## EVIDENCE SNAPSHOT

1. HEAD: 3e2085d6aa3b2160b26246c877579e877412da4a
2. Branch: 0148-mermaid-artifact-type-read-model
3. Dirty tree: clean
4. Cached diff: empty
5. origin/main: 3e2085d6aa3b2160b26246c877579e877412da4a
6. Merge base: 3e2085d6aa3b2160b26246c877579e877412da4a
7. Recent log: PR 0147D merged at 3e2085d ("PR 0147D — Construction Estimate Read-Only Dogfood Adapter (#177)")
8. PR 0147D merge evidence: present in history
9. PR 0148 implementation: does not exist — no prior PR 0148 work
10. Mermaid references in codebase: zero in runtime source. Only deferred references in prior PR plans and roadmap artifacts. No .mmd files. No mermaid dependency. No mermaid rendering.
11. artifact_kind / media_type / controlled references: established in PR 0147C (run_profile.py, artifacts.py)

## ROADMAP ALIGNMENT

- roadmap track: Visual Gate / Mermaid (Stream 3, post-0147 governance insertions)
- expected PR slot: PR 0148 (Mermaid Artifact Type Read Model)
- why this PR is next: PR 0147D (Construction Estimate Read-Only Dogfood Adapter) was the last governance insertion. ROADMAP.md and ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md both identify PR 0148 as the next product PR. PR 0147A-0147D were explicit non-renumbering insertions that did not consume PR 0148.
- batching policy check: Pass — PR 0148 is a coherent multi-step substrate capability unit (artifact type + read model + controlled reference resolution + safe presentation). It is not an isolated single-feature frontend PR.
- drift heuristic check: Not triggered. PR 0147D was a backend adapter (no UI-only touch). PR 0148 touches both backend (read model) and frontend (presentation). The 4-consecutive-UI-file heuristic only counts PRs touching only server.py — no such PR exists in the current sequence.
- architect sign-off required: no — PR 0148 is the expected normal roadmap slot, not a governance insertion.
- architect sign-off reference: N/A

PR 0149 remains next (Visual Gate Runtime Object).

## CURRENT ARCHITECTURE INVENTORY

### ArtifactStore (services/runner/src/runner/artifacts.py)

Content-addressed store keyed by SHA-256. Stores bytes at `<store_root>/<sha256_prefix>/<sha256>`. `put_bytes()` returns ArtifactWriteResult with kind, media_type, sha256. `read_bytes(sha256)` returns bytes. `find_by_sha256(sha256)` returns ArtifactRecord or None. Kind is an ArtifactKind enum with known values: docker_stdout, docker_stderr, docker_execution_metadata, docker_command_metadata, prompt_planner, prompt_plan_review, prompt_coder, prompt_precommit. Kind is stored metadata, not a validation gate — unknown kinds are accepted.

### Artifact kind in profile descriptors (PR 0147C)

Artifact descriptors in run-profile.json have a `kind` field (string, 100-char max). Evidence roles: input, output, report, capture, supporting. The kind field is descriptive metadata, not validated against an enum — any string is accepted.

### media_type in profile descriptors

`media_type` field (string, 100-char max, MIME type). Used in artifact descriptors. No MIME validation gate exists.

### SHA-256 storage and byte reads

Profile artifact descriptors carry an optional `sha256` field. Controlled references include `sha256:<64-char-hex>` for ArtifactStore lookups and `run-relative:<path>` for run-directory file reads. The ArtifactStore resolves sha256 references to stored bytes. Run-relative paths resolve to `<runs_root>/<run_id>/<path>` with containment checks via `os.path.realpath()`.

### run-profile schema "1"

Established by PR 0147C. `schema_version: "1"`. Contains neutral_facts (max 50), artifact_groups (max 20), artifact_descriptors (max 100). Profile_hash computed via deterministic canonical JSON with self-referential exclusion. Profile metadata is explicitly labelled "not runtime proof."

### GET /runs/<run_id>/profile

Returns versioned profile JSON. States: ready (200 with profile), missing (200 with ok=false), malformed (200 with ok=false and error), unsupported_version (200 with ok=false), hash_mismatch (200 with ok=false and profile content). No POST/PUT/PATCH/DELETE.

### Artifact Workspace profile fetching

`fetchProfile(runId)` called from `selectRun()` alongside `fetchReport()`. Uses same `detailRequestCounter` for stale-response protection. `renderProfile(data)` renders the profile section in the Canvas zone.

### detailRequestCounter stale-response protection

`detailRequestCounter` variable increments on each selection change. Each fetch captures `requestId`. Responses check `if (requestId !== detailRequestCounter) return;` in both .then() and .catch(). Shared by detail fetch, report fetch, and profile fetch.

### Server-owned roots

Runs root is server-configured (not browser-provided). Browser provides run_id via query or path segment, never a root path. No browser-controlled paths exist.

### Safe runtime-value rendering

All runtime values rendered via `textContent` or `safeText()`. No innerHTML with untrusted values. `isSafeUrl()` gate for safe URLs. No `file:` links. No `javascript:` links. No auto-linkification. No Markdown parsing. No Mermaid execution. No ANSI interpretation.

### Current dependency model

No Mermaid dependency exists. `pyproject.toml` has no mermaid package. No rendering libs. No diagramming libs. Safe rendering contract: no innerHTML with runtime values.

### Existing Mermaid support

Confirmed absent: zero Mermaid imports, zero .mmd files, zero Mermaid CDN references, zero Mermaid configuration. The word "mermaid" appears only in deferred roadmap references and prior PR plan texts that identify PR 0148 as future work.

## SELECTED ARCHITECTURE: OPTION A — EXTENDED PROFILE DESCRIPTOR READ MODEL

**Why OPTION A over a parallel Mermaid-specific endpoint:**

The profile contract (PR 0147C) already supports arbitrary artifact kinds via the `kind` string field, arbitrary `media_type` values, and both controlled reference forms (`run-relative:` and `sha256:`). Mermaid artifacts are distinguished by kind (`mermaid`) and media type (`text/vnd.mermaid`). The existing `GET /runs/<run_id>/profile` endpoint, `renderProfile()` workspace function, and reference resolution infrastructure are reused without modification. No new backend route, no new workspace fetch function, no new serialization contract, no new profile schema version.

**Why not a dedicated GET /runs/<run_id>/mermaid route:**

A dedicated route would duplicate the profile contract's reference-resolution logic, create a second API surface for artifact types, and couple the API shape to a specific diagram kind. The profile descriptor model is intentionally generic — adding Mermaid as a kind value preserves universality and defers PR 0150 (diagram viewers) without API proliferation.

### Canonical source of truth

1. **Mermaid type metadata**: The `kind` field in profile artifact descriptors. Value: `"mermaid"`.
2. **Mermaid source bytes**: Read from the file resolved by controlled reference (`run-relative:` or `sha256:`) in the descriptor. The profile descriptor does not embed diagram content — it references it.
3. **Content hash**: The `sha256` field in the profile artifact descriptor, verified against actual bytes read from the resolved reference.
4. **Read-model state**: The existing profile response (`GET /runs/<run_id>/profile`). Mermaid artifacts appear as descriptors in the profile's artifact groups. The workspace `renderProfile()` displays them with kind, media_type, reference, hash, and hash-verification status. No separate Mermaid-specific response shape.

### Architecture decisions

1. **Kind value**: `"mermaid"` — used as the profile artifact descriptor kind field. No new enum or schema change.
2. **ArtifactStore and run-profile descriptors relationship**: Unchanged. ArtifactStore continues to store content-addressed bytes. Profile descriptors reference via `sha256:` or `run-relative:`. Mermaid artifacts use the same two reference forms.
3. **run-profile schema "1"**: Unchanged. profile_schema_version remains "1". No new fields added. No existing fields reinterpreted.
4. **ev_contract_version "1"**: Unchanged.
5. **GET /runs/<run_id>/profile**: Reused. No additional GET-only route added.
6. **Reference forms**: Both `run-relative:` and `sha256:` can supply Mermaid bytes — the same two controlled reference forms already validated by the profile contract.
7. **Reference resolution**: Through existing server-owned roots and containment checks. `run-relative:` resolves via `resolve_run_relative()` in run_profile.py. `sha256:` resolves via ArtifactStore.
8. **Workspace location**: Mermaid artifacts appear in the Profile section of the Canvas zone, rendered by the existing `renderProfile()` function. Artifact groups show descriptors with their kind, media_type, ref, sha256, and hash status.
9. **Safe presentation**: PR 0148 presents inert Mermaid source text. No rendered diagram preview. No HTML, SVG, or canvas rendering. The .mmd text is displayed in a `<pre>` element via `textContent` — the same safe pattern used for run reports (PR 0146) and proof/manifest (PR 0147).
10. **Rendering dependency**: Not required. Mermaid source is displayed as inert text via textContent. Diagram rendering is deferred to PR 0150.
11. **No-dependency behavior**: The absence of a rendering dependency is the correct behavior for PR 0148 — source display only. If the coder attempts to add a rendering dependency, it must be blocked.
12. **PR 0150 deferral**: Diagram rendering, SVG generation, Canvas-based diagram viewers, and Visual Gate integration are deferred to PR 0150+.

## MERMAID ARTIFACT CONTRACT

1. **Canonical kind**: `"mermaid"`.
2. **Exact media type**: `"text/vnd.mermaid"`. This is the registered media type for Mermaid syntax text.
3. **Accepted extension**: `.mmd` for run-relative references. Not enforced as a rejection — if a file has content parsable as Mermaid but a different extension, it is still presented. Extension mismatch is displayed as a warning notice, not a hard rejection.
4. **Strict encoding**: UTF-8 only. Non-UTF-8 bytes are rejected with reason code `unsupported_encoding`.
5. **UTF-8 BOM behavior**: BOM (byte-order mark U+FEFF) is stripped if present at the start of the file. If a BOM appears mid-file (invalid in UTF-8), the content is rejected as malformed.
6. **Newline behavior**: CRLF and LF accepted. Uses universal newline mode (`newline=""` or str.splitlines()). No normalization — original newlines preserved in displayed text.
7. **Empty-content behavior**: An empty .mmd file is valid Mermaid (produces no diagram). Displayed as empty content with a notice: "Mermaid artifact contains no content." Hash verification still applies.
8. **Maximum byte size**: 100 KB (same as the run-report truncation limit from PR 0146). Larger files are rejected with reason code `artifact_too_large`.
9. **Character or line bounds**: No per-character or per-line bounds beyond the 100 KB total.
10. **Required descriptor fields**: kind (`"mermaid"`), media_type (`"text/vnd.mermaid"`), ref (controlled reference), label (human-readable label, max 200 chars).
11. **Optional descriptor fields**: sha256 (64-char hex), group (string), display_order (integer), required (boolean, default false), evidence_role (string).
12. **Descriptor and content SHA-256 behavior**: If a descriptor supplies sha256, the content bytes are hashed and compared. Hash match: displayed with "SHA-256 verified" label. Hash mismatch: displayed with "SHA-256 mismatch — content differs from declared hash" label. No sha256: no hash verification performed; displayed with "SHA-256 not declared" label.
13. **Media-type mismatch behavior**: If media_type is not `"text/vnd.mermaid"`, the artifact is still displayed but with a warning: "Unexpected media type: <media_type> (expected text/vnd.mermaid)."
14. **Extension mismatch behavior**: If the run-relative reference does not end in `.mmd`, a warning notice is displayed: "Non-standard extension for Mermaid artifact."
15. **Duplicate descriptors**: Two descriptors with identical kind `"mermaid"`, identical ref, and identical media_type are displayed as a single artifact reference. The profile creation API (PR 0147C) rejects duplicate group keys. Descriptor uniqueness is enforced by the profile contract — duplicate descriptors are not possible within a valid profile.
16. **Multiple Mermaid artifacts**: Supported. Each appears as a separate descriptor in its artifact group. Each has its own reference, label, hash, and verification status.
17. **Deterministic ordering**: Descriptors are ordered by display_order (ascending), then by label (alphabetical). Deterministic within the profile.
18. **Required versus optional behavior**: Required Mermaid artifacts that are missing display: "Required Mermaid artifact is missing — descriptor references non-existent file." Optional missing: "Optional Mermaid artifact not found."
19. **Legacy descriptors**: Descriptors with kind other than `"mermaid"` are displayed normally — no Mermaid-specific rendering. The existing `renderProfile()` already handles arbitrary kinds.
20. **Unknown kinds**: Displayed with their kind value as-is. No Mermaid treatment.
21. **Unsupported versions**: The profile schema version gate (run_profile.py) rejects unsupported profile versions independently of Mermaid content.

**Descriptor presence does not prove physical artifact exists.** The profile metadata label "Profile metadata — not runtime proof" applies to all descriptors. Missing-file states are explicitly displayed.

## CONTROLLED REFERENCE SAFETY

The existing reference validation (`resolve_run_relative()`, `validate_reference()`) from run_profile.py applies unchanged to Mermaid artifact references. Exact behavior:

1. **run-relative references**: Path after `run-relative:` prefix. Resolved relative to `<runs_root>/<run_id>/`. Containment check via `os.path.realpath()`.
2. **sha256 references**: Path after `sha256:` prefix. 64-char lowercase hex validated. Resolved through ArtifactStore at controlled store root.
3. **Server-owned roots**: Runs root configured via `runs_root` parameter. ArtifactStore root configured via `store_root`. Neither is browser-controllable.
4. **Path normalization**: `os.path.normpath()` applied before containment check.
5. **Parent traversal**: `..` segments detected by checking that the normalized realpath starts with the run directory realpath.
6. **Absolute paths**: Accepted only if they resolve within the run directory (via containment check). Non-contained absolute paths are rejected with reason code `unsafe_path`.
7. **Windows-style absolute paths**: Not relevant (POSIX-only). If present on POSIX, treated as relative paths that fail containment.
8. **Symlink and realpath containment**: `os.path.realpath()` resolves all symlinks. The resolved path must start with the resolved runs_root/run_id directory.
9. **Regular-file checks**: `os.path.isfile()` before reading. Directories and special files rejected with reason code `not_a_file`.
10. **Directories and special files**: Rejected with reason code `not_a_file`.
11. **Missing and unreadable files**: `file_not_found` (missing) or `read_error` (permissions). Same behavior as the run-report read logic.
12. **Size checks before full reads**: File size checked via `os.path.getsize()` before reading. If > 100 KB, rejected with `artifact_too_large`. If 0 bytes, accepted as empty content.
13. **Strict decoding**: Read as UTF-8. `UnicodeDecodeError` produces reason code `unsupported_encoding`.
14. **Hash comparison**: SHA-256 computed on decoded UTF-8 bytes (not on text lines). Compared to descriptor sha256 if present.
15. **URLs**: Rejected by `validate_reference()` — the six-prefix check matches URLs as neither `run-relative:` nor `sha256:`.
16. **file: scheme**: Rejected — matches neither approved prefix.
17. **data: scheme**: Rejected — matches neither approved prefix.
18. **javascript: scheme**: Rejected — matches neither approved prefix.
19. **Browser-controlled paths and roots**: None accepted. Browser provides only run_id, never a root or absolute path.

Every rejection has a visible reason code reported in the profile response.

## READ MODEL AND API

No new HTTP routes. The existing `GET /runs/<run_id>/profile` conveys all Mermaid artifact state through its profile descriptors and their hash status.

The workspace display (via `renderProfile()`) shows each Mermaid descriptor with:

```
[label] — Mermaid artifact
  Reference: <ref>
  Media type: text/vnd.mermaid
  SHA-256: <status label>
  Bytes: <byte count>
```

### State table for Mermaid artifacts in profile response

| State | Profile field values | Workspace display |
|---|---|---|
| Ready Mermaid artifact | descriptor with kind="mermaid", media_type="text/vnd.mermaid", ref valid, sha256 match | Full descriptor with "SHA-256 verified" |
| No Mermaid descriptor | No descriptor with kind="mermaid" | No Mermaid artifacts listed |
| Optional artifact missing | descriptor present, required=false, ref points to missing file | "Optional Mermaid artifact not found" |
| Required artifact missing | descriptor present, required=true, ref points to missing file | "Required Mermaid artifact missing" |
| Malformed descriptor | descriptor missing required fields | Schema validation error in profile read |
| Unsafe reference | ref matches url/absolute/traversal pattern (blocked by validate_reference) | "Unsafe reference rejected" |
| Missing physical artifact | descriptor valid, file does not exist | "Artifact not found at reference path" |
| Oversized artifact | file > 100 KB | "Artifact too large (max 100 KB)" |
| Unsupported encoding | non-UTF-8 bytes | "Unsupported encoding — not valid UTF-8" |
| Unsupported media type | media_type != "text/vnd.mermaid" | Warning: "Unexpected media type" (still displays) |
| Extension mismatch | run-relative ref does not end in .mmd | Warning: "Non-standard extension" (still displays) |
| Hash mismatch | supplied sha256 does not match computed hash | "SHA-256 mismatch" |
| Malformed or unsupported Mermaid | content read successfully, no Mermaid validation | Displayed as inert text (validation deferred to PR 0150) |
| Unsupported profile version | profile schema_version not "1" | Profile-level error (existing behavior) |
| Malformed profile | profile JSON is not parseable | Profile-level error (existing behavior) |
| Invalid run ID | run_id fails validation | Existing 200/error response |
| Missing run | run directory does not exist | Existing run-not-found response |
| Internal read failure | filesystem error | "Internal error reading artifact" |

**No POST, PUT, PATCH, or DELETE route is added.**

## CURRENT AND PROPOSED RESPONSE FIELDS

This section explicitly distinguishes the current GET /runs/<run_id>/profile response from the proposed additive Mermaid read-state fields. The profile response is NOT modified — Mermaid read-state fields are proposed additive fields in the server response or new internal functions. The workspace display reads them from the existing profile response.

### Current GET /runs/<run_id>/profile response fields (physical, verified from run_profile.py and server.py)

| Field | Type | Required | Source | Evidence meaning |
|---|---|---|---|---|
| ev_contract_version | str | yes | Serialization contract | Contract version identifier. Must be "1". |
| ok | bool | yes | Profile read result | Whether the read succeeded. True for ready, hash_mismatch. False for missing, malformed, unsupported-version. |
| error | str or None | no | Profile read error | Reason code. One of: "profile not found", "profile malformed", "unsupported profile version", "profile hash mismatch", "invalid run_id". |
| run_id | str | yes | Request path | Canonical run identifier. |
| profile_exists | bool | yes | File existence check | Whether the run-profile.json file exists. |
| profile_sha256 | str or None | no | Profile hash | Computed SHA-256 of profile (self-excluding). Present when profile parses successfully. |
| hash_match | bool or None | no | Hash comparison | Whether stored hash matches computed hash. None if profile does not exist or cannot parse. |
| profile | dict or None | no | Profile file content | The full run-profile.json dict: schema_version, profile_key, run_id, profile_sha256, run_presentation (title, status_label, neutral_facts), artifact_groups, artifact_descriptors. Present when profile parses successfully and version is supported. |

### Profile artifact descriptor fields (current, within profile dict)

| Field | Type | Required | Source | Max length |
|---|---|---|---|---|
| key | str | yes | Profile descriptor | 100 chars |
| label | str | yes | Profile descriptor | 200 chars |
| kind | str | yes | Profile descriptor | 100 chars (e.g. "mermaid", "summary", "spreadsheet") |
| evidence_role | str | yes | Profile descriptor | One of: input, output, report, capture, supporting |
| media_type | str | yes | Profile descriptor | 100 chars (MIME type, e.g. "text/vnd.mermaid") |
| ref | str | yes | Profile descriptor | Controlled reference: run-relative:path or sha256:hex |
| group_key | str | yes | Profile descriptor | References artifact_groups key |
| display_order | int | no | Profile descriptor | Integer for sort ordering |
| required | bool | no | Profile descriptor | Default false |
| sha256 | str or null | no | Profile descriptor | 64-char lowercase hex string |

The profile dict and its descriptor fields exist in the current codebase. They are NOT modified by PR 0148. Mermaid artifacts add new descriptors with kind="mermaid" and media_type="text/vnd.mermaid" using these same existing fields.

### Proposed additive fields: Mermaid artifact read state

These fields are not part of the current profile response. They are produced by the proposed `read_mermaid_artifact()` and `mermaid_artifact_states_for_profile()` functions in run_profile.py. The workspace renderProfile() receives them as derived state, not as raw profile fields.

| Field | Type | Required | Source | Missing behavior | Malformed behavior | Evidence meaning |
|---|---|---|---|---|---|---|
| ok | bool | yes | read_mermaid_artifact() | False | False | Whether the Mermaid artifact read succeeded. |
| error | str or None | no | Reason code from read | "file_not_found", "artifact_too_large", "unsupported_encoding", "read_error" | N/A | Descriptive error, not proof. |
| content | str or None | no | Resolved file bytes as UTF-8 | None | None on error | Mermaid source text. Contains diagram syntax, not rendered output. Not proof. |
| byte_count | int or None | no | os.path.getsize() | 0 | 0 | Physical file size in bytes. Not proof of content correctness. |
| sha256_verified | bool | no | Hash comparison | False (no sha256 in descriptor) | False | Whether the declared sha256 matches computed hash of content bytes. True means byte-for-byte match, not diagram validation. |
| hash_match | bool or None | no | Hash comparison | None (no sha256 declared) | None | True: declared hash matches computed hash. False: mismatch. None: no sha256 in descriptor. |
| sha256_declared | str or None | no | Descriptor sha256 field | None | None | The declared hash value from the descriptor (if present). |

These fields are computed server-side per descriptor on every profile read. They are deterministic for the same file and descriptor content. They never imply diagram correctness, approval, acceptance, or Visual Gate passage.

## PROFILE VERSUS MANIFEST ZONES

The Artifact Workspace has four zones. PR 0148 affects exactly one zone conditionally and leaves three zones entirely unchanged:

| Zone | Rendered by | Affected by PR 0148 | Rationale |
|---|---|---|---|
| Timeline (zone-timeline) | fetchRuns, renderRunList | Unchanged | Run list index — no profile or Mermaid data. |
| Canvas (zone-canvas) | renderDetail, renderReport, **renderProfile** | **Profile section only** — Mermaid descriptor display added inside renderProfile() | Mermaid metadata and read state belong to the profile/Canvas read-model surface. renderProfile() already handles arbitrary descriptor kinds. Mermaid adds a sub-function renderMermaidArtifact() called by renderProfile(). |
| Gates & Proofs (zone-gates-proofs) | renderGatesProofs | Unchanged | Manifest files, evidence paths, run JSON hash, source errors, agent claims, report provenance, proof refs — these are runtime evidence from manifest.json and run.json. Mermaid descriptors are NOT manifest entries. |
| Logs & Captures (zone-logs-captures) | renderLogsCaptures | Unchanged | Execution results only. No profile or Mermaid data. |

### Separation rules enforced by OPTION A

1. **Mermaid profile metadata and Mermaid read state belong to the profile/Canvas read-model surface** — rendered by renderProfile() in zone-canvas. This is the existing profile section that displays profile_key, neutral facts, artifact groups, and artifact descriptors.

2. **Existing manifest filenames and runtime evidence remain in Gates & Proofs** — unchanged. renderGatesProofs() continues to display manifest_files, evidence_paths, run_json_hash, source_errors, agent claims, report provenance, and the proof_refs-unavailable notice.

3. **renderGatesProofs() must not be repurposed as the Mermaid renderer** — Mermaid source text appears in the Profile section, not in Gates & Proofs. The Gates & Proofs zone has no knowledge of artifact kinds.

4. **Mermaid descriptor presence must not alter manifest truth** — adding a Mermaid descriptor to run-profile.json does not change manifest.json. manifest.json continues to list only the files the runtime recorded.

5. **Mermaid reads must not fabricate manifest entries** — reading a .mmd file via a profile descriptor does not create a manifest entry. The manifest is read-only and unchanged.

6. **Manifest entries must not automatically become Mermaid descriptors** — a .mmd file listed in manifest.json does not automatically gain a profile descriptor. Profile descriptors are separately authored.

7. **Profile metadata must not replace runtime evidence** — the profile heading "Profile metadata — not runtime proof" applies to all Mermaid descriptors. Runtime evidence (manifest entries, evidence paths) retains its own classification.

8. **No value may be duplicated across zones with conflicting evidence meaning** — if a Mermaid .mmd file is also listed in manifest.json, it appears in both zones but with distinct labels: "Mermaid artifact" (Profile/Canvas) and "Runtime Evidence: listed in manifest.json" (Gates & Proofs). These are consistent — the manifest entry confirms the file exists; the profile descriptor provides structured metadata.

9. **Existing PR 0147 proof and manifest classifications remain unchanged**:
   - Gates & Proofs labels: "Runtime Evidence", "Evidence reference", "Execution Result", "Agent-performed operation", "(as recorded in manifest)", "Source error", "Report provenance", "proof_refs are not stored".
   - Profile labels: "Profile metadata — not runtime proof", "Profile key", "Profile hash match/mismatch".
   - Mermaid labels (new, in Profile section): "Mermaid artifact", "SHA-256 verified / mismatch / not declared", "Mermaid source text".

10. **Regression tests verify zone separation** — the existing test class TestWorkspaceDisplay (test_artifact_workspace_shell.py) tests zone headings, structure, role attributes, and placeholder text. The new TestMermaidWorkspaceDisplay test class verifies that Mermaid content appears only in the profile context and does not duplicate into Gates & Proofs or Logs & Captures.

### Exact Artifact Workspace functions affected by implementation

Only these functions are modified or added:
- **renderProfile()** (existing, in artifact_workspace.py) — modified to call renderMermaidArtifact() when descriptors with kind="mermaid" exist.
- **renderMermaidArtifact()** (new, in artifact_workspace.py) — added as a helper called by renderProfile(), not by any existing renderer. Renders inert Mermaid source text in a `<pre>` element.

These functions remain completely unchanged:
- fetchRuns, renderRunList, showTimelineState (Timeline zone)
- renderDetail, showDetailLoading, showDetailFetchFailure (Canvas zone detail section)
- fetchReport, renderReport, getOrCreateReportViewer, setReportState, clearReportViewer (Canvas zone report section)
- fetchProfile, showProfileLoading, showProfileUnavailable (Canvas zone profile section — only renderProfile is modified within)
- showGatesLoading, showGatesUnavailable, renderGatesProofs (Gates & Proofs zone — entirely unchanged)
- showLogsLoading, showLogsUnavailable, renderLogsCaptures (Logs & Captures zone — entirely unchanged)
- selectRun (selection/stale protection — unchanged)
- escHtml, safeText, isSafeUrl (rendering helpers — unchanged)

## SAFE PRESENTATION

### Inert source display via textContent

Mermaid source text is displayed in a `<pre>` element using `textContent` — the exact same safe pattern used for run reports (PR 0146). This ensures:

1. **textContent or equivalent inert rendering**: All Mermaid source text rendered via `textContent`. No innerHTML.
2. **innerHTML restrictions**: innerHTML is never used with Mermaid source text. innerHTML is used only for container clearing (`innerHTML = ""`).
3. **HTML and SVG handling**: Mermaid source may contain HTML-like or SVG-like text. Because textContent is used, these characters are displayed as literal text, not parsed as markup.
4. **Mermaid directives**: Mermaid directives (e.g., `%%{init: ...}%%`) are not executed. Displayed as inert text.
5. **click directives and links**: Mermaid `click` directives are not executed. Displayed as inert text.
6. **active URI schemes**: `javascript:`, `data:`, `file:` URIs within Mermaid content are displayed as inert text. No auto-linkification. The `isSafeUrl()` gate prevents any `href` attribute being set from Mermaid content.
7. **External assets**: No external assets are loaded. No CDN references. No image URLs fetched.
8. **Network access**: No network access. No fetch/XHR from Mermaid content. No img/script/iframe elements.
9. **Script execution**: No script execution. No eval. No Function constructor. No document.write. No innerHTML.
10. **DOM ID collisions**: Mermaid text is in a `<pre>` element. No persistent DOM IDs are assigned from Mermaid content.
11. **Stale selected-run responses**: Mermaid content is part of the profile response. The same `detailRequestCounter` stale-response protection covers profile fetches. When a new run is selected, old profile data is discarded.
12. **Selection changes during reads**: Same stale protection — the profile fetch captures `requestId` and checks against `detailRequestCounter`.
13. **Loading and all failure states**: Each descriptor's hash-verification and read status is computed server-side and returned in the profile response. The workspace displays the pre-computed status. Loading states are at the profile level (existing fetchProfile loading), not per-descriptor.
14. **Accessibility**: `<pre>` element with appropriate `aria-label`. Support for keyboard focus and screenreader text content.
15. **Explicit metadata/not-proof wording**: The existing profile section heading "Profile" retains the "Profile metadata — not runtime proof" label. Each Mermaid descriptor displays the label "Mermaid artifact" (not "Mermaid diagram" or "Mermaid proof"). The hash status label uses neutral wording: "SHA-256 match", "SHA-256 mismatch", "SHA-256 not declared".

### No diagram rendering in PR 0148

Diagram rendering (SVG generation, Canvas rendering, image output) is deferred to PR 0150 (Requirement / State / Sequence Diagram Viewers). PR 0148 displays only the inert source text. The coder must not add any rendering library, CDN script, canvas element, or SVG generation.

## EVIDENCE SEMANTICS

Exact labels and messages preventing semantic confusion:

1. **Descriptor does not prove file existence**: Profile heading: "Profile metadata — not runtime proof." Descriptor shown with ref, not clickable, not labeled as verified content.
2. **Unverified hash is not verified**: If no sha256 in descriptor, displayed as "SHA-256: not declared." Not "verified" or "trusted."
3. **Valid syntax is not factually correct**: Mermaid content displayed as-is. No "valid diagram" claim. Label: "Mermaid source text."
4. **Display does not mean approval**: No approve/reject controls. No "accepted" label. No Visual Gate passage indicator.
5. **Display does not mean Visual Gate passage**: VisualGateResult is deferred to PR 0149. No Visual Gate status shown.
6. **Artifact is not registered or accepted**: No registry badge. No acceptance state. No lifecycle controls.
7. **Agent did not generate or review it**: No agent-generation claim. No agent-review badge. The profile metadata label applies.
8. **Missing optional evidence is not successful proof**: Optional missing: "Optional Mermaid artifact not found." Required missing: "Required Mermaid artifact is missing." Neither implies successful proof.

## BACKWARD COMPATIBILITY

Preservation requirements and their evidence:

1. **PR 0143-0147 Artifact Workspace behavior**: All workspace zones, headings, region roles, keyboard behavior, timeline, detail panel, report viewer, gates/proofs, logs/captures — unchanged. Profile section unchanged for non-Mermaid profiles.
2. **PR 0147A local operator**: Unchanged. runs-root configuration, loopback defaults, read-only status — unchanged.
3. **PR 0147B manual orchestration**: Unchanged. Session store, stage gates, CLI subcommands, orchestration route — untouched.
4. **PR 0147C profile contract**: Unchanged. `run-profile.json` schema version "1", profile_sha256, neutral facts, groups, descriptors, controlled references — all preserved. Mermaid is a new kind value, not a schema change.
5. **PR 0147D construction adapter**: Unchanged. Profile_key `construction-estimate-v1`, CSV parsing, Decimal arithmetic, source immutability — untouched.
6. **ev_contract_version "1"**: Unchanged and unmodified.
7. **run-profile schema "1"**: Unchanged.
8. **profile_sha256 behavior**: Unchanged. Deterministic self-excluding hash unaffected by Mermaid descriptor content.
9. **Existing controlled-reference rejection**: All existing validation (absolute path rejection, traversal detection, URL rejection, file: rejection, data: rejection, javascript: rejection) unchanged.
10. **Existing GET routes**: All unchanged. Only GET /runs/<run_id>/profile is the source of Mermaid artifact state.
11. **Server-owned roots**: Unchanged. No browser-controllable roots.
12. **Read-only UI**: Unchanged. No mutation controls added.
13. **Metadata/not-proof distinction**: Unchanged. Profile metadata disclaimer retained.
14. **Legacy runs without profiles**: Unchanged. Return existing profile-not-found state.
15. **Profiles without Mermaid**: < 20 descriptor limit (PR 0147C) means non-Mermaid descriptors continue to display normally. No Mermaid rendering or Mermaid-specific branches.
16. **Non-Mermaid descriptors**: Unchanged. Displayed as-is with their original kind value.
17. **Stale-response protection**: Unchanged. detailRequestCounter continues to protect profile, report, and detail fetches.

### Compatibility tests

All existing tests must pass unmodified:
All existing physical tests must pass unmodified. No existing test is modified — all are run as-is to confirm the new Mermaid artifact logic does not break existing behavior.

**ArtifactStore compatibility coverage**: Provided by the existing physical test file `services/runner/tests/test_artifact_store.py` (put_text, put_bytes, sha256 determinism, read_bytes, read_record, traversal rejection, symlink safety).

**Existing run-artifact compatibility coverage**: Provided by the existing physical test file `services/runner/tests/test_docker_run_artifacts.py` (Docker artifact shapes, content bounding, redaction, deterministic IDs).

**Run-profile compatibility coverage**: Provided by the existing physical test file `services/runner/tests/test_run_profile.py` (profile schema, validation, hashing, references, persistence).

**Existing task-intake API compatibility coverage**: Provided by the existing physical test files:
- `services/task_intake/tests/test_run_profile_api.py` (GET /runs/<run_id>/profile states)
- `services/task_intake/tests/test_artifact_workspace_shell.py` (workspace rendering, zone structure, existing profile section)
- `services/task_intake/tests/test_local_operator.py` (operator configuration)
- `services/task_intake/tests/test_local_run_history_in_page.py` (timeline)
- `services/task_intake/tests/test_runtime_evidence_serialization_contract.py` (evidence JSON contract)
- `services/task_intake/tests/test_task_intake.py` (server)
- `services/runner/tests/test_runtime_evidence.py` (evidence reads)
- `services/runner/tests/test_run_persistence.py` (persistence)

## IMPLEMENTATION ALLOWLIST

Every file is listed with exact purpose and permitted/prohibited changes.

### services/runner/src/runner/run_profile.py (EDIT)

- **Permitted**: Add a function `read_mermaid_artifact(runs_root, run_id, descriptor) -> dict` that resolves a controlled reference, reads .mmd bytes, verifies hash, and returns a state dict with {ok, error, content, byte_count, sha256_verified, hash_match, sha256_declared}. Add a function `mermaid_artifact_states_for_profile(profile, runs_root, run_id) -> list[dict]` that iterates profile descriptors with kind="mermaid", calls read_mermaid_artifact for each, returns per-descriptor state. Both functions are pure file-system readers — no HTTP, no rendering, no mutation.
- **Prohibited**: No changes to run-profile.json schema, profile_sha256 computation, validation functions, create_run_profile(), descriptor bounds, reference validation logic, controlled-reference rejection. No new fields in profile schema. No new fact value types. No version changes.

### services/task_intake/src/task_intake/artifact_workspace.py (EDIT)

- **Permitted**: Add a workspace display function `renderMermaidArtifact(container_id, descriptor, state)` that renders an inert Mermaid source block in a `<pre>` element via textContent in the Profile section. The function is called from the existing `renderProfile()` when descriptors with kind="mermaid" are detected. The display shows the descriptor label, ref, media type, byte count, and hash status. The Mermaid source text is rendered in a scrollable `<pre>` element.
- **Prohibited**: No Mermaid rendering library. No CDN. No canvas. No SVG. No innerHTML with Mermaid content. No approve/reject controls. No Visual Gate controls. No diagram generation code. No changes to non-Mermaid rendering. No changes to timeline, detail, report, gates, logs, or other workspace zones. No changes to CSS that affect other zones.

### services/task_intake/src/task_intake/server.py (NO CHANGE)

- Not modified. No new route added. Mermaid artifacts are served through the existing GET /runs/<run_id>/profile endpoint.

### services/runner/tests/test_run_profile.py (EDIT)

- **Permitted**: New test class `TestMermaidArtifactRead` with tests for reference resolution (run-relative, sha256), UTF-8 reading, BOM stripping, empty content, size bounds (100 KB), hash verification (match, mismatch, absent), encoding rejection, missing-file states, traversal rejection, URL rejection. Tests use temporary directories with synthetic .mmd files. No Mermaid parsing or validation tests — those are deferred to PR 0150.
- **Prohibited**: No tests that require Mermaid generation. No tests that call a diagram renderer. No tests that modify the profile schema.

### services/task_intake/tests/test_artifact_workspace_shell.py (EDIT)

- **Permitted**: New test class `TestMermaidWorkspaceDisplay` with tests for Mermaid descriptor presence in workspace, inert source text display via textContent, hash-status labels, missing/empty/oversized states, extension-mismatch warning, media-type-mismatch warning, non-Mermaid descriptor preservation. Use the existing `_request()` test helper to GET /workspace and assert HTML/JS content.
- **Prohibited**: No tests that require Mermaid generation. No tests that render diagrams.

### tests/fixtures/sample-diagram.mmd (NEW)

- Synthetic single-node Mermaid file:
  ```
  graph TD
      A[Start] --> B[End]
  ```
- Saved as UTF-8 without BOM.

### tests/fixtures/empty-diagram.mmd (NEW)

- Empty file (0 bytes).

### tests/fixtures/hash-mismatch-diagram.mmd (NEW)

- Content "different content than declared hash". Used to test hash mismatch.

### scripts/smoke-mermaid-artifact.py (NEW)

- End-to-end smoke test: creates a temporary runs root and run directory, creates run-profile.json with a Mermaid descriptor, creates the referenced .mmd file, calls the profile read and workspace rendering functions, verifies Mermaid descriptor state, source text display, hash status, missing-file state, oversized rejection, non-Mermaid preservation. Cleanup removes temporary directory.

### .project-memory/pr/0148-mermaid-artifact-type-read-model/IMPLEMENTATION_REPORT.md (NEW)

- Written by coder per Implementation Handoff Artifact Contract.

### .project-memory/pr/0148-mermaid-artifact-type-read-model/reviews/precommit-review.yml (NEW)

- Written only by precommit-review. Not coder-writable.

### Forbidden files — not modified

- ROADMAP.md
- .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
- All PR 0147A-0147D source, tests, and documentation
- All other service source files (run_persistence.py, runtime_evidence.py, runtime_evidence_serialization.py, local_operator.py, manual_orchestration.py, manual_orchestration_cli.py)
- All other test files
- pyproject.toml, Makefile, README.md
- Docs (LOCAL_OPERATOR.md, MANUAL_ORCHESTRATION.md, RUN_ARTIFACT_PROFILE.md, CONSTRUCTION_ESTIMATE_DOGFOOD.md)
- All agents/*.yml
- All schemas/*.yml

## TEST AND SMOKE PLAN

### 1. Profile read model tests (test_run_profile.py)

```
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_run_profile.py -k "Mermaid" -q
```

Expected: All Mermaid artifact read tests pass (reference resolution, encoding, hash, size, traversal, rejection). If not met: block.

### 2. Existing profile tests

```
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_run_profile.py -q
```

Expected: All existing profile tests pass (39). If not met: block — indicates backward incompatibility.

### 3. Existing API tests

```
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_run_profile_api.py -q
```

Expected: All pass (8). If not met: block.

### 4. Workspace display tests (test_artifact_workspace_shell.py)

```
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -k "Mermaid" -q
```

Expected: All Mermaid workspace display tests pass. If not met: block.

### 5. Existing workspace tests

```
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -q
```

Expected: All pass (310+). If not met: block.

### 6. Full regression

```
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_run_profile.py services/runner/tests/test_artifact_store.py services/runner/tests/test_docker_run_artifacts.py services/runner/tests/test_run_persistence.py services/runner/tests/test_runtime_evidence.py services/task_intake/tests/test_run_profile_api.py services/task_intake/tests/test_artifact_workspace_shell.py services/task_intake/tests/test_local_run_history_in_page.py services/task_intake/tests/test_local_operator.py services/task_intake/tests/test_runtime_evidence_serialization_contract.py services/task_intake/tests/test_task_intake.py -q
```

Expected: All pass. If not met: block.

### 7. Mermaid artifact smoke

```
PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-mermaid-artifact.py
```

Expected: "MERMAID ARTIFACT SMOKE PASSED" as the last stdout line. No repository residue. Temporary directories cleaned up. If not met: block.

### 8. Safe rendering grep

```
grep -n -E "innerHTML.*mermaid|mermaid.*innerHTML|mermaid.*src|svg.*innerHTML|canvas.*mermaid|mermaid.*render" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: exit code 1 (no matches). If not met: block.

### 9. No Mermaid dependency grep

```
grep -n -i "mermaid" pyproject.toml
```

Expected: exit code 1 (no matches) or only the test/smoke script path reference. If not met: block.

### 10. Forbidden file changes

```
git diff --name-only -- services/runner/src/runner/run_persistence.py services/runner/src/runner/runtime_evidence.py services/runner/src/runner/runtime_evidence_serialization.py services/task_intake/src/task_intake/local_operator.py services/task_intake/src/task_intake/manual_orchestration.py services/task_intake/src/task_intake/manual_orchestration_cli.py ROADMAP.md .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md pyproject.toml Makefile
```

Expected: empty. If not met: block.

### 11. Planning lock diff

```
git diff -- .project-memory/pr/0148-mermaid-artifact-type-read-model/PLAN.md
```

Expected: empty (PLAN.md not modified during implementation). If not met: block.

### 12. Residue check

```
git status --short
```

Expected: only approved files in dirty tree. No unknown files outside the PR directory and the approved paths. If not met: block.

## IMPLEMENTATION REPORT

Require:

`.project-memory/pr/0148-mermaid-artifact-type-read-model/IMPLEMENTATION_REPORT.md`

It must begin with:

> This implementation report is handoff context, not proof.
> Agent output is not proof.
> Reviewer must verify claims against files, diffs, validation output,
> dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK.

Require all 11 canonical sections per IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md:
TASK SUMMARY, FILES READ, FILES CHANGED, IMPLEMENTATION DECISIONS, PLAN ALIGNMENT, DEVIATIONS FROM PLAN, VALIDATION RUN, BOUNDARY CONFIRMATIONS, NON-GOALS PRESERVED, RISKS OR WARNINGS, NEXT REVIEWER FOCUS.

## PLAN DRIFT GATE

Block implementation completion if:

1. Any changed file outside the approved allowlist.
2. PLAN.md or plan-review.yml changes during implementation.
3. Architecture diverges from OPTION A (extended profile descriptor read model).
4. A new route is added (dedicated Mermaid endpoint).
5. A new profile schema version is created.
6. ev_contract_version changes.
7. Controlled reference resolution is bypassed or weakened.
8. Browser-controlled paths or roots are accepted.
9. URL or active URI artifact sources are accepted.
10. Unsafe Mermaid presentation — innerHTML with Mermaid content, CDN scripts, script execution, SVG or canvas rendering, linkification, or network access.
11. External network or CDN dependency is added.
12. Hidden or repaired hash mismatch — mismatch displayed as silent success.
13. Missing or malformed evidence shown as success — missing file shown as available, oversize shown as normal.
14. Descriptor or agent claims shown as proof — "Mermaid artifact" labelled as "Mermaid proof" or "verified diagram."
15. HTTP mutation — POST, PUT, PATCH, DELETE routes.
16. Execution authority — shell, subprocess, agent, Git, gh, Docker from Mermaid content.
17. PR 0149 or later scope — VisualGateResult, Visual Gate readiness, diagram rendering, approve/reject, Artifact Registry, or any item from Stream 3+.
18. Construction-specific rendering — PR 0147D adapter behavior duplicated.
19. Stale-response regression — detailRequestCounter broken for profile fetches.
20. Route or workspace regression — existing GET routes or workspace zones broken.
21. Validation or smoke failure — any required test or smoke command fails.
22. Residue — unknown untracked files in working tree.
23. Missing or inaccurate IMPLEMENTATION_REPORT.md.

## NO-DRIFT CHECK

Require affirmative confirmation:

1. Correct branch: `0148-mermaid-artifact-type-read-model`.
2. Correct roadmap slot: PR 0148 (Mermaid Artifact Type Read Model).
3. Exact scope and planning lock: only approved files changed. PLAN.md and plan-review.yml unchanged.
4. Selected architecture: OPTION A — extended profile descriptor read model. No new route. No new schema version.
5. Exact type: kind `"mermaid"`, media_type `"text/vnd.mermaid"`.
6. Contained references: only `run-relative:` and `sha256:`. All other reference forms rejected.
7. Deterministic encoding: UTF-8, BOM stripped, 100 KB max, CRLF/LF accepted.
8. Visible failure states: missing, oversized, unsupported-encoding, hash-mismatch, unsafe-ref, extension-warning, media-type-warning — all visible with reason codes.
9. Safe offline presentation: textContent in `<pre>` element. No rendering. No CDN. No network. No script execution. No innerHTML with Mermaid content.
10. Metadata/proof/approval separation: "Profile metadata — not runtime proof." Hash status labels neutral. No approve/reject. No Visual Gate.
11. Stale-response preservation: detailRequestCounter covers profile fetches.
12. Existing workspace preservation: all zones, timeline, detail, report, gates, logs, profile rendering unchanged for non-Mermaid profiles.
13. PR 0147C preservation: profile schema version "1", profile_sha256, controlled references, validation — unchanged.
14. PR 0147D preservation: construction-estimate-v1 profile_key, CSV adapter behavior, source immutability — unchanged.
15. PR 0149 and later deferral: no diagram rendering, no VisualGateResult, no Visual Gate readiness check, no approve/reject, no Artifact Registry.
16. Required validation and smoke: all 12 validation commands pass.
17. No residue: git status clean except approved files.
18. Physical evidence precedence: file contents, test results, smoke output, diffs, and validation evidence override agent claims.

## STOP CONDITIONS

Implementation must stop if:

1. The locked plan cannot be followed (architecture, scope, allowlist).
2. A required file is outside the allowlist.
3. run-profile schema version "1" requires modification.
4. ev_contract_version "1" requires modification.
5. Controlled reference resolution cannot be made safe (traversal escape, URL bypass).
6. Inert presentation requires unsafe execution, innerHTML with Mermaid content, CDN, or network.
7. Later-roadmap behavior (diagram rendering, Visual Gate, artifact registry) becomes necessary.
8. Physical repository state contradicts the plan (e.g., a change in profile schema from a previous PR).
9. Tests or smoke fail.
10. Unexplained residue appears.
11. Architect authority is required beyond what is already documented.

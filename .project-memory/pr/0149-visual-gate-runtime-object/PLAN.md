# PR 0149 — Visual Gate Runtime Object Plan

## EVIDENCE SNAPSHOT

1. HEAD: 7340c5cdff7d57c7f3ca38067f83048fce5f7d96
2. Branch: 0149-visual-gate-runtime-object
3. Dirty tree: clean
4. Cached diff: empty
5. origin/main: 7340c5cdff7d57c7f3ca38067f83048fce5f7d96
6. Merge base: 7340c5cdff7d57c7f3ca38067f83048fce5f7d96
7. Recent log: PR 0148 merged at 7340c5c ("PR 0148 — Mermaid Artifact Type Read Model (#178)")
8. PR 0148 merge evidence: present — HEAD at origin/main, PR 0148 at top of `git log --oneline`
9. Existing Visual Gate discoveries: zero — no VisualGateResult type, schema, file, or implementation exists in the repository. The word "visual_gate" appears only in deferred roadmap references.
10. Existing gate, review, approval, evidence, and state-contract patterns: review_boundary.py uses deterministic interpretation with decision states (completed, blocked, requires_review, failed). Manual orchestrator (PR 0147B) uses versioned session objects with deterministic state hashes, atomic writes, run ID validation, and controlled roots. Run persistence (PR 0130/0131) uses run.json + manifest.json with sort_keys=True canonical JSON and hash verification. Run-profile sidecar (PR 0147C) uses schema_version "1", atomic temp-write + replace, self-excluding profile_sha256. Mermaid read model (PR 0148) uses kind="mermaid" in profile descriptors with controlled reference resolution and hash verification. ArtifactStore (PR 0021) uses sha256 keys, containment checks, symlink safety.
11. PR 0149 work does not exist.
12. No existing canonical VisualGateResult contract exists.

## ROADMAP ALIGNMENT

- roadmap track: Visual Gate / Mermaid (Stream 3, PR 0149)
- expected PR slot: PR 0149 (Visual Gate Runtime Object)
- why this PR is next: PR 0148 (Mermaid Artifact Type Read Model) is merged. ROADMAP.md and ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md both identify PR 0149 as the next product PR after PR 0148. PR 0147A-0147D were governance insertions that did not renumber PR 0148 or PR 0149.
- batching policy check: Pass — PR 0149 is a coherent single-capability PR (runtime object contract, validation, hashing, read-only API). It is not an isolated single-feature frontend PR.
- drift heuristic check: Not triggered. No consecutive UI-only PRs exist. PR 0148 added both backend and frontend. PR 0149 adds a backend runtime contract.
- architect sign-off required: no — PR 0149 is the expected normal roadmap slot.
- architect sign-off reference: N/A

PR 0150 remains next (Requirement / State / Sequence Diagram Viewers).

## CURRENT ARCHITECTURE INVENTORY

### Run persistence (services/runner/src/runner/run_persistence.py)

Persists run.json and manifest.json under <runs_root>/<run_id>/. Uses canonical JSON with sort_keys=True. Atomic write via temporary sibling file + os.replace. Run ID validated against _RUN_ID_RE. run_json_hash stored in manifest. Readback verifies hash. Status: persisted, rejected, not_found, read_ok.

### Runtime evidence (services/runner/src/runner/runtime_evidence.py)

Read model for run evidence. list_run_evidence_summaries() enumerates run directories and builds RunEvidenceSummary. read_run_evidence_detail() reads one run and builds RunEvidenceDetail. Both are read-only, no mutation. Evidence notices for missing and malformed files.

### ArtifactStore (services/runner/src/runner/artifacts.py)

Content-addressed store keyed by SHA-256. put_text, put_bytes, read_bytes, read_record, find_by_sha256. Path containment via os.path.realpath(). Symlink safety. Deterministic sha256 for identical content.

### Run-profile sidecar (services/runner/src/runner/run_profile.py)

run-profile.json at <runs_root>/<run_id>/. Schema version "1". Deterministic self-excluding profile_sha256. Neutral facts, artifact groups, artifact descriptors with controlled references (run-relative:, sha256:). Atomic write via temp file + os.replace. read_run_profile() returns ok, error, profile, profile_sha256, profile_exists, hash_match states.

### Mermaid artifact read states (PR 0148)

Added read_mermaid_artifact() and mermaid_artifact_states_for_profile() in run_profile.py. Mermaid descriptors use kind="mermaid", media_type="text/vnd.mermaid". Controlled .mmd reads with hash verification. Inert source display in profile/Canvas. No VisualGateResult.

### Manual-orchestration state hashing and persistence (PR 0147B)

Session store at .ariadne/orchestration/<session_id>.json. Schema version "1". Deterministic session_id (sha256[:16]). Deterministic state_hash (sha256[:16], self-ref excluded). Atomic writes via temp file + os.replace. Stale-state protection via expected-hash on all mutation operations.

### Existing review-boundary or human-review semantics (services/runner/src/runner/review_boundary.py)

Deterministic function derive_review_boundary() interpreting execution_request + execution_result. Decision states: completed, blocked, requires_review, failed. Approval field optional. No persistence. No notification. No UI.

### Existing schema and version conventions

All runtime contracts use schema_version "1". Canonical JSON uses sort_keys=True, ensure_ascii=False, indent=2. Hash algorithms are SHA-256. Hash truncation at 16 hex chars for identifiers (run persistence, orchestrator sessions). Full 64-char hex for content hashes (ArtifactStore, profile_sha256).

### Existing atomic-write patterns

Write to temporary sibling path (filename.tmp), then os.replace(target, source). Atomic on POSIX. Readback verifies write succeeded.

### Existing run ID validation

_RUN_ID_RE pattern: typically [a-zA-Z0-9_-]+, max 128 chars. Used by run_persistence, run_profile, server.py.

### Existing evidence-reference forms

run-relative:<path> resolved relative to run directory. sha256:<64-char-hex> resolved through ArtifactStore. Absolute paths, traversal, URLs, file:, data:, javascript: rejected by validate_reference().

### Current server and workspace behavior

GET /runs/<run_id>/profile returns versioned profile response. GET /runs/<run_id>/report returns versioned report response. GET /runs/<run_id> returns versioned detail response. GET / returns Local Interaction page. GET /workspace returns Artifact Workspace. No POST/PUT/PATCH/DELETE for evidence, profiles, or reports. No Visual Gate routes, UI, or workspace zones exist.

### Existing Visual Gate implementation

Confirmed absent. No VisualGateResult type, schema file, route, workspace zone, or UI element exists in the codebase.

## SELECTED ARCHITECTURE: OPTION A — RUN-DIRECTORY VISUAL GATE SIDECAR

**Why OPTION A:**

The run-directory sidecar pattern is already established and proven by:
1. run.json (PR 0130/0131) — canonical run record.
2. run-profile.json (PR 0147C) — descriptive profile metadata with versioned schema, deterministic hash, atomic writes.
3. manifest.json — runtime file listing.

VisualGateResult is a runtime object (not descriptive metadata), so it must be its own file — not embedded in run-profile.json. Embedding it in the profile would violate the principle that profile metadata is descriptive, not runtime gate truth. A separate visual-gate-result.json sidecar follows the established storage pattern, lives alongside the other run-owned files, and can be independently versioned and validated.

**Why not in run.json:** run.json is the persisted runtime record schema. Adding Visual Gate state would require a new run.json version or optional fields that other consumers must understand. The sidecar pattern keeps each contract independently versioned.

**Why not in the ArtifactStore:** The VisualGateResult is run-scoped state, not a content-addressed artifact. It belongs with the run directory.

**Canonical path:** `<runs_root>/<run_id>/visual-gate-result.json`

**Cardinality:** Exactly one VisualGateResult per run. No phase-level granularity — phase_id is recorded as metadata within the object for future multi-phase runs but the object itself is per-run.

**Schema version:** "1". Uses ev_contract_version "1" for API responses.

**Serialization:** Canonical JSON with sort_keys=True, ensure_ascii=False, indent=2. Same pattern as run-profile.json.

**Hashing:** Self-excluding SHA-256 computed on canonical JSON excluding the `visual_gate_sha256` field. Same pattern as profile_sha256 (PR 0147C). Full 64-char lowercase hex.

**Atomic write:** Temporary sibling write + os.replace. Readback verification.

**Read-only API:** GET /runs/<run_id>/visual-gate-result. Returns versioned JSON response. Server-owned runs_root. No mutation.

**Workspace:** No workspace changes in PR 0149. The VisualGateResult is created and tested at the runtime-object level. UI display is deferred to a future PR in the Visual Gate / Mermaid stream.

**Pipeline enforcement:** None in PR 0149. The object can be created with any valid status. Readiness enforcement is deferred to PR 0151. Human approval is deferred to PR 0152.

**Relationship to PR 0148 Mermaid artifacts:** The required_diagrams entry references Mermaid profile descriptors by their `key` field (the artifact descriptor key from run-profile.json). It does not duplicate the Mermaid descriptor content or the .mmd file bytes. The reference is: `profile_descriptor_key:<descriptor_key>`. This is a third controlled reference form specific to VisualGateResult, identifying which profile descriptor describes the required diagram.

**Stale state:** The VisualGateResult file is immutable once written. No update transitions exist in PR 0149. Staleness is detected by the consumer comparing the visual_gate_sha256 (or object existence) against expected state — deferred to PR 0151 readiness enforcement.

**Dependencies:** No new Python dependencies. Uses standard-library hashlib, json, os, tempfile.

## VISUALGATERESULT CONTRACT

### Top-level fields

| Field | Type | Required | Bounds | Source | Evidence meaning |
|---|---|---|---|---|---|
| schema_version | str | yes | Exactly "1" | Serialization contract | Contract version identifier. |
| visual_gate_id | str | yes | 64 chars, run_id-based unique identifier | Deterministic from run_id + visual_gate_sha256[:16] | Canonical identity. Not proof. |
| run_id | str | yes | 128 chars, _RUN_ID_RE pattern | Provided at creation | Links to the persisted run. |
| phase_id | str or null | no | null or 128 chars | Provided at creation | Identifies the phase within the run. null for single-phase runs. Default: null. |
| required_diagrams | list of RequiredDiagramEntry | yes | Max 20 entries | Provided at creation | List of diagrams that must exist. |
| status | str | yes | One of: pending, ready_needs_review, passed, failed | Provided at creation | Visual Gate passage status. See state machine below. |
| human_review_required | bool | yes | true or false | Derived from status consistency | Whether human review is required. See consistency rules. |
| evidence_refs | list of str | no | Max 50 refs, each max 500 chars | Provided at creation | Controlled references to runtime evidence that supports the gate. |
| reason_codes | list of str | no | Max 20 codes, each max 100 chars | Provided at creation | Reason codes explaining status. |
| created_at | str | yes | ISO 8601 UTC, max 30 chars | clock_provider | Deterministic timestamp. |
| visual_gate_sha256 | str | yes | 64-char lowercase hex | Computed | Self-excluding SHA-256 of canonical JSON. Deterministic. |
| source | str | no | Max 100 chars | Provided at creation | Producer identity (e.g. "operator", "adapter:construction-estimate-v1"). |
| warnings | list of str | no | Max 10 warnings, each max 500 chars | Provided at creation | Non-blocking warnings about gate state. |

**No updated_at field** — the object is immutable once created in PR 0149. Updates/transitions are deferred. The created_at timestamp is the only time field.

**No approval field** — human approval is deferred to PR 0152. The status field and human_review_required flag describe current gate state without claiming approval happened.

### Deterministic serialization

Canonical JSON key ordering for top-level fields (sorted alphabetically):
- created_at
- evidence_refs
- human_review_required
- phase_id
- reason_codes
- required_diagrams
- run_id
- schema_version
- source
- status
- visual_gate_id
- visual_gate_sha256 (excluded from hash input)
- warnings

Keys with null or empty-list values are omitted from canonical JSON (except required fields).

### visual_gate_id generation

visual_gate_id = f"vg-{run_id}-{sha256[:16]}" where sha256 is the visual_gate_sha256 (computed after excluding itself). This is deterministic because the same input produces the same hash.

## REQUIRED DIAGRAMS

### RequiredDiagramEntry fields

| Field | Type | Required | Bounds | Source | Evidence meaning |
|---|---|---|---|---|---|
| diagram_id | str | yes | 100 chars, matches ^[a-zA-Z0-9_\-]+$ | Provided | Stable identifier for the required diagram. |
| diagram_type | str | yes | 100 chars | Provided | Type of diagram (see allowed types below). |
| descriptor_ref | str | yes | 500 chars, must match profile_descriptor_key:<key> | Provided | Reference to a PR 0148 profile artifact descriptor with kind="mermaid". The <key> must exist in the run's profile's artifact_descriptors. |
| required | bool | yes | true or false | Provided | Whether the diagram is required for gate passage. Default: true. |
| presence_state | str | yes | One of: present, absent, not_checked | Computed by reader | Whether the referenced descriptor and its artifact file exist. |
| validity_state | str | yes | One of: valid, invalid, not_checked | Computed by reader | Whether the diagram content is valid Mermaid syntax. Deferred to PR 0150. Current value: "not_checked". |

**diagram_type allowed values:** "requirement", "state", "sequence". These are the three core diagram types from the roadmap. No other types are accepted.

**descriptor_ref form:** `profile_descriptor_key:<artifact_descriptor.key>`. The reader resolves this by loading the run's run-profile.json, finding an artifact_descriptor with the matching `key`, verifying it has kind="mermaid", and then reading the file referenced by its `ref`. This is a derived reference — it traverses from VisualGateResult through the profile to find the Mermaid artifact.

**Deterministic ordering:** required_diagrams are ordered by diagram_id (alphabetical).

**Duplicate diagram_id:** Rejected — duplicate diagram_id values produce validation error "duplicate_diagram_id:<id>".

**Duplicate descriptor_ref:** Allowed — two different required diagrams could reference the same Mermaid artifact (e.g., one requirement diagram and one state diagram could be the same file if the author chose to combine them). This is unusual but not an error.

**Unsupported diagram_type:** Accepted if the type is in the allowed set above. Any other value produces "unsupported_diagram_type:<type>" validation error.

**Missing artifact:** If the descriptor_ref does not resolve to an existing descriptor or the referenced file does not exist, the required diagram is still valid as a declaration — but presence_state becomes "absent" when the object is read. This is not a validation error; it is a visible state.

**Hash mismatch:** If the Mermaid artifact exists but its content SHA-256 does not match the descriptor sha256, presence_state is "present" but a hash mismatch warning is added to the warnings list.

**Multiple artifacts:** Each required diagram is a separate entry. The existence check resolves each independently.

**Relationship to PR 0148:** The descriptor_ref relies on PR 0148's kind="mermaid" and media_type="text/vnd.mermaid" contract. If the profile does not exist or has no matching descriptor, presence_state becomes "absent".

**Validator versus reader:** The VisualGateResult object stores only the declaration (diagram_id, diagram_type, descriptor_ref, required). The presence_state and validity_state are computed by a reader function when the object is loaded — they are not stored fields. This keeps the stored contract stable and defers diagram-type-specific validation.

## STATUS STATE MACHINE

### Status values

| Status | Meaning | human_review_required | Terminal | Allowed reason_codes |
|---|---|---|---|---|
| pending | Visual gate has not been evaluated. Default for newly created gate. | false | No | "not_yet_evaluated" |
| ready_needs_review | Required diagrams are present and gate is ready for human review. | true | No | "ready_for_review" |
| passed | Gate passed — all required evidence satisfied without human review requirement. | false | Yes | "all_required_diagrams_present", "evidence_satisfied" |
| failed | Gate failed — required diagrams missing, artifacts invalid, or evidence insufficient. | false | Yes | "missing_required_diagrams", "artifact_not_found", "unsupported_encoding", "hash_mismatch" |

### Consistency rules between status and human_review_required

- status=ready_needs_review => human_review_required=true. If false, reject with "human_review_required_must_be_true".
- status=pending => human_review_required=false. If true, reject with "human_review_required_must_be_false".
- status=passed => human_review_required=false. If true, reject with "human_review_required_must_be_false".
- status=failed => human_review_required=false. If true, reject with "human_review_required_must_be_false".

### Transition rules

PR 0149 has NO transition API. The VisualGateResult object is created once with its initial status by the producer. Transitions between statuses (e.g., pending -> ready_needs_review, pending -> passed, ready_needs_review -> passed, ready_needs_review -> failed) are deferred to PR 0151 (Visual Gate Readiness Check) or a follow-up PR that adds an update/transition endpoint.

### Roadmap resolution: "No code implementation allowed before pending/approved gate is represented"

PR 0149 represents the gate runtime object with two statuses that satisfy this requirement:
- pending — the gate exists and has not been evaluated. This satisfies "pending".
- passed — the gate passed its checks. This satisfies "approved" in the sense of automated check passage.

"Approved" in the roadmap language refers to automated gate passage via the evidence checks that PR 0151 will implement. PR 0149 does NOT claim that "passed" means "human approval." The human_approval artifact is deferred to PR 0152.

The plan does not add pipeline enforcement. The existence of the VisualGateResult object does not block or allow code execution. PR 0149 represents the contract; PR 0151 will add enforcement.

## HUMAN REVIEW SEMANTICS

### human_review_required behavior

1. **When it must be true:** Only when status is "ready_needs_review". This means the gate is complete enough for a human to evaluate, but automated checks cannot declare passage.
2. **When it may be false:** Status is pending, passed, or failed.
3. **Consistency with status:** Enforced by validation — contradictory combinations are rejected with specific reason codes.
4. **Cannot be inferred:** human_review_required is an explicit field, not derived from evidence_refs presence or absence. If not provided, it is set based on the status consistency rules.
5. **Cannot be supplied by an agent:** The status and human_review_required are creator-provided. An agent that creates a VisualGateResult with status=passed and human_review_required=false is creating a valid object — but the object does not claim human review occurred. The evidence_refs would need to contain admissible evidence to support the claim.
6. **Does not prove review occurred:** human_review_required=true means review is needed, not that it happened. human_review_required=false means no review is required by this gate, not that review was performed.
7. **Evidence required to claim review occurred:** The evidence_refs would need to reference a PR 0152 HumanApprovalArtifact or similar admissible evidence. PR 0149 does not define approval evidence.
8. **PR 0152 deferral:** Human approval is a separate artifact. VisualGateResult has no approval field. The human_review_required flag indicates review-needed status, not approval status.
9. **Missing human-review evidence:** If human_review_required=true but the evidence_refs contain no approval artifact, this is a visible state — the gate declares review is needed, and evidence_refs show what supports that need. The absence of approval evidence is not hidden.
10. **Contradictory combinations:** See consistency rules above. Validation rejects contradictory status+human_review_required pairs.

## EVIDENCE REFERENCES

### Accepted controlled reference forms

VisualGateResult.evidence_refs accepts the same controlled reference forms as PR 0147C:
- **run-relative:**<path> — resolved relative to runs_root/<run_id>/ with containment check.
- **sha256:**<64-char-hex> — resolved through ArtifactStore.
- **profile_descriptor_key:**<key> — NEW form specific to VisualGateResult. Resolved by loading the run's run-profile.json, finding the matching artifact_descriptor by key, then reading that descriptor's referenced artifact.

### Bounds and ordering

- Max 50 refs per VisualGateResult.
- Each ref max 500 chars.
- Evidence_refs are ordered alphabetically (deterministic).

### Duplicate references

Duplicate refs are not rejected but are deduplicated to one entry when serialized.

### Unsafe reference rejection

The same validate_reference() logic from run_profile.py applies to run-relative: and sha256: forms. For profile_descriptor_key: refs, validation checks that the key matches the pattern ^[a-zA-Z0-9_\-]+$ (same as profile descriptor keys).

### Absolute paths, traversal, URLs, file:, data:, javascript:

Rejected by the existing controlled reference validation for run-relative: and sha256: forms. For profile_descriptor_key: refs, the form itself contains no path — only a descriptor key — so these attacks are structurally impossible.

### Missing targets

- run-relative: target file does not exist => not an error (declared ref is valid). The consumer must check file existence when using the ref.
- sha256: target not in ArtifactStore => not an error for the reference. Consumer discovers missing artifact.
- profile_descriptor_key: target key not found in profile => not an error for the VisualGateResult. The presence_state for that required diagram becomes "absent".

### Hash mismatch

If a referenced artifact has a declared sha256 in its profile descriptor and the actual bytes differ, this is discovered by the consumer. The VisualGateResult validation does not follow references at creation time.

### Proof versus reference semantics

An evidence_ref is a reference — not independently verified proof. The consumer (PR 0151 readiness checker, human reviewer) must verify that the referenced evidence exists and satisfies the gate. The VisualGateResult contract does not claim verification.

## VALIDATION, SERIALIZATION, AND HASHING

### Validation order

1. Required field presence
2. Field type checks
3. Field bounds (string length, list length, numeric bounds)
4. schema_version must be "1"
5. run_id must match _RUN_ID_RE
6. visual_gate_id format: must start with "vg-"
7. status must be one of the allowed values
8. human_review_required consistency with status (see consistency rules above)
9. required_diagrams max 20, each has all required fields
10. diagram_id must match ^[a-zA-Z0-9_\-]+$
11. diagram_type must be in allowed types
12. descriptor_ref must match profile_descriptor_key:<key> with valid key pattern
13. evidence_refs max 50, each validated as controlled reference
14. reason_codes max 20
15. created_at must be valid ISO 8601 UTC
16. warnings max 10

### Exact reason codes

| Validation failure | Reason code |
|---|---|
| Missing required field | missing_field:<field_name> |
| Invalid schema_version | unsupported_schema_version:<version> |
| Invalid run_id | invalid_run_id |
| Invalid visual_gate_id format | invalid_visual_gate_id |
| Invalid status | invalid_status:<status> |
| Status and human_review_required inconsistent | human_review_required_mismatch:expected:<expected>:got:<got> |
| Too many required_diagrams | too_many_required_diagrams:<count> |
| Invalid diagram_id | invalid_diagram_id:<id> |
| Duplicate diagram_id | duplicate_diagram_id:<id> |
| Invalid diagram_type | unsupported_diagram_type:<type> |
| Invalid descriptor_ref | invalid_descriptor_ref:<ref> |
| Too many evidence_refs | too_many_evidence_refs:<count> |
| Invalid evidence_ref | invalid_evidence_ref:<ref> |
| Too many reason_codes | too_many_reason_codes:<count> |
| Invalid created_at | invalid_created_at |
| Too many warnings | too_many_warnings:<count> |

### Canonical JSON encoding

- sort_keys=True
- ensure_ascii=False
- indent=2
- Key ordering: alphabetical (enforced by sort_keys)
- List ordering: alphabetical for evidence_refs, reason_codes, warnings; by diagram_id for required_diagrams
- Whitespace: trailing newline at end of file
- Unicode: UTF-8 encoded. Non-ASCII characters stored directly (ensure_ascii=False).

### Hash algorithm

SHA-256. Full 64-char lowercase hex string. Same as profile_sha256.

### Self-excluding hash

visual_gate_sha256 is excluded from its own canonical JSON input. Same pattern as profile_sha256 (PR 0147C).

### Hash mismatch state

When reading, the stored visual_gate_sha256 is compared to the recomputed hash (excluding the stored hash field). If mismatched, the read result reports hash_match=False with error "hash_mismatch". The stored object data is still returned so the consumer can inspect it.

### Unsupported schema state

If schema_version is not "1", the read result returns ok=False with error "unsupported_schema_version".

### Malformed state

If the JSON file is unparseable, returns ok=False with error "malformed".

### Missing state

If the file does not exist, returns ok=False with error "not_found".

### No silent repair

If hash mismatch is detected, the file must NOT be rewritten with the corrected hash. The mismatch must remain visible.

## STORAGE AND READBACK

### Canonical root and path

- Root: Inferred from runs_root (same pattern as run-profile.json). No separate root.
- Canonical path: `<runs_root>/<run_id>/visual-gate-result.json`
- Directory containment: The normalized realpath must resolve within the run directory.

### Server/runtime ownership

The runs_root is server-configured (same as all other run files). Browser does not control the root.

### Run and phase validation

Run ID is validated against _RUN_ID_RE before any file operations. Phase ID (if provided) is validated as a string within bounds — no phase-level file path is constructed.

### Atomic temporary write

1. Create `<run_dir>/visual-gate-result.json.tmp` with canonical JSON.
2. Call os.fsync() on the file descriptor.
3. os.replace(tmp_path, target_path).
4. Verify file was written by reading it back.

### Replacement behavior

If a visual-gate-result.json already exists, the write is rejected with error "already_exists". PR 0149 does not support update/overwrite — the object is created once.

### Duplicate-create behavior

If the file already exists, create_visual_gate_result() returns ok=False with error "already_exists". No idempotent overwrite.

### Conflicting-create behavior

If the run directory does not exist, creation returns ok=False with error "run_not_found".

### Readback

After atomic write, the file is read back and validated. The returned dict includes readback state.

### Process-exit durability

os.replace is atomic on POSIX. Data written to temp file is fsynced before rename. On process crash between write and rename, the temp file may be orphaned but the target file is unchanged (or contains the complete new content).

### Symlink safety

The run directory path is resolved via os.path.realpath() before any file operations.

### Size bounds

visual-gate-result.json max 1 MB.

### Permission errors

OSError on write or read returns ok=False with error "write_error" or "read_error" including the system error message.

### Temporary-file cleanup

On successful os.replace, the temp file no longer exists (it was renamed). On failure, the temp file is removed via os.remove() in a cleanup block.

### Repository-residue isolation

All tests use temporary directories (tmp_path). No production .ariadne or runs_root is accessed.

## READ SURFACE

### GET /runs/<run_id>/visual-gate-result

**Exact path:** Same routing scope as GET /runs/<run_id>/profile and GET /runs/<run_id>/report.

**Server-owned root:** runs_root is server-configured. Browser provides only run_id.

**Response contract:**

| Field | Type | Always present | Description |
|---|---|---|---|
| ev_contract_version | str | yes | "1" |
| ok | bool | yes | Read success |
| error | str or None | no | Error reason code |
| run_id | str | yes | Run identifier |
| visual_gate_result_exists | bool | yes | Whether the file exists |
| visual_gate_sha256 | str or None | no | Computed hash (present when file exists and parsable) |
| hash_match | bool or None | no | Whether stored hash matches computed hash |
| visual_gate_result | dict or None | no | The full VisualGateResult object (present when file exists, parsable, and version supported) |

**HTTP status:** Always 200. Errors are conveyed in the JSON response body (same pattern as all other Ariadne read routes).

**States:**
- Ready: ok=True, visual_gate_result_exists=True, hash_match=True, visual_gate_result contains full object.
- Missing: ok=False, error="not_found", visual_gate_result_exists=False, visual_gate_result=None.
- Malformed: ok=False, error="malformed", visual_gate_result_exists=True, visual_gate_result=None.
- Unsupported version: ok=False, error="unsupported_schema_version", visual_gate_result_exists=True, visual_gate_result=None.
- Hash mismatch: ok=True, error="hash_mismatch", visual_gate_result_exists=True, hash_match=False, visual_gate_result contains object (for inspection).
- Invalid run_id: ok=False, error="invalid_run_id".

**No browser-controlled roots** — runs_root is server-configured.

**No mutation** — GET only.

## BACKWARD COMPATIBILITY

Preservation requirements:

1. **PR 0148 Mermaid descriptor contract**: kind="mermaid", media_type="text/vnd.mermaid", bounded .mmd reads, hash verification — all unchanged. VisualGateResult references Mermaid descriptors via profile_descriptor_key: refs, not by modifying the profile.
2. **kind="mermaid"**: Unchanged.
3. **media_type="text/vnd.mermaid"**: Unchanged.
4. **Mermaid bounded-read behavior**: Unchanged. VisualGateResult does not duplicate the read logic.
5. **Inert Mermaid source display**: Unchanged. No Visual Gate data is injected into the workspace profile section.
6. **ev_contract_version "1"**: Unchanged.
7. **run-profile schema "1"**: Unchanged. No Visual Gate fields added to profile.
8. **profile_sha256 behavior**: Unchanged.
9. **Existing run persistence**: Unchanged. run.json and manifest.json untouched.
10. **Existing runtime evidence**: Unchanged.
11. **Existing GET routes**: /runs, /runs/<run_id>, /runs/<run_id>/report, /runs/<run_id>/profile — all unchanged. Visual gate route is additive.
12. **Artifact Workspace**: Unchanged. No workspace changes in PR 0149.
13. **Manual orchestration**: Unchanged.
14. **Construction adapter**: Unchanged.
15. **Legacy runs**: A run without visual-gate-result.json is valid — GET returns ok=False, visual_gate_result_exists=False. No error for absence.
16. **Profiles without Mermaid**: Unchanged.
17. **Runs without Visual Gate state**: Unchanged — the file simply does not exist.
18. **Existing evidence and review semantics**: Unchanged.

### Preservation tests

All existing physical test suites must pass unmodified:
- services/runner/tests/test_run_persistence.py
- services/runner/tests/test_runtime_evidence.py
- services/runner/tests/test_artifact_store.py
- services/runner/tests/test_docker_run_artifacts.py
- services/runner/tests/test_run_profile.py
- services/task_intake/tests/test_run_profile_api.py
- services/task_intake/tests/test_artifact_workspace_shell.py
- services/task_intake/tests/test_local_operator.py
- services/task_intake/tests/test_local_run_history_in_page.py
- services/task_intake/tests/test_runtime_evidence_serialization_contract.py
- services/task_intake/tests/test_task_intake.py

## IMPLEMENTATION ALLOWLIST

### services/runner/src/runner/visual_gate_result.py (NEW)

Core module containing:
- VisualGateResult dict creation, validation, serialization, hash.
- RequiredDiagramEntry validation.
- create_visual_gate_result(runs_root, run_id, ...) -> dict.
- read_visual_gate_result(runs_root, run_id) -> dict.
- compute_visual_gate_sha256(data) -> str.
- validate_visual_gate_result(data) -> list[str].

Permitted: Pure functions operating on dicts. Atomic file write. Canonical JSON. Deterministic hashing. Controlled reference validation for evidence_refs.

Prohibited: No Mermaid parsing. No diagram rendering. No pipeline enforcement. No approval controls. No workspace rendering. No UI. No HTTP route definition (that belongs in server.py). No agent, provider, shell, git, gh, or Docker execution.

### services/task_intake/src/task_intake/server.py (EDIT)

Add import of read_visual_gate_result. Add GET /runs/<run_id>/visual-gate-result route. Route handler mirrors the profile route pattern (validate run_id, call read function, build versioned JSON response).

Permitted: One additive GET route handler. Import statement for read_visual_gate_result.

Prohibited: No POST/PUT/PATCH/DELETE. No changes to existing routes. No workspace modifications. No changes to the existing route dispatch logic beyond adding the visual-gate-result path check.

### services/runner/tests/test_visual_gate_result.py (NEW)

Comprehensive tests for the VisualGateResult contract.

Permitted: All test cases listed in the TEST PLAN section below.

Prohibited: No tests requiring Mermaid generation. No tests calling diagram renderers. No tests invoking agents or external services. No workspace test dependencies (workspace display is deferred).

### services/task_intake/tests/test_visual_gate_result_api.py (NEW)

Tests for the GET /runs/<run_id>/visual-gate-result route.

Permitted: Create persisted runs, write visual-gate-result.json, verify route responses. Use the existing _request() test helper pattern from test_artifact_workspace_shell.py (direct HTTP test client, not a running server).

Prohibited: No tests that start the full server. No tests that modify existing routes.

### scripts/smoke-visual-gate-result.py (NEW)

End-to-end smoke test.

Permitted: All smoke conditions listed in the END-TO-END SMOKE section.

Prohibited: No Docker, no agents, no external services, no repository residue.

### .project-memory/pr/0149-visual-gate-runtime-object/IMPLEMENTATION_REPORT.md (NEW)

Written by coder per Implementation Handoff Artifact Contract.

### .project-memory/pr/0149-visual-gate-runtime-object/reviews/precommit-review.yml (PREEXISTING)

Written only by precommit-review. Not coder-writable.

### Forbidden files — not modified

- ROADMAP.md
- .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md
- All PR 0147A-0147D and PR 0148 source, tests, and documentation
- services/runner/src/runner/run_profile.py (no changes to profile schema, hashing, or descriptors)
- services/runner/src/runner/artifacts.py
- services/runner/src/runner/runtime_evidence.py
- services/runner/src/runner/run_persistence.py
- services/runner/src/runner/review_boundary.py
- services/task_intake/src/task_intake/artifact_workspace.py (no workspace changes in PR 0149)
- services/task_intake/src/task_intake/runtime_evidence_serialization.py
- services/task_intake/src/task_intake/manual_orchestration.py
- services/task_intake/src/task_intake/local_operator.py
- All other test files
- pyproject.toml, Makefile, README.md
- All agents/*.yml
- All schemas/*.yml
- Docs
- Construction-estimate files and fixtures
- Mermaid fixtures and smoke scripts from PR 0148

## TEST PLAN

All test commands use existing physical test files or future PLAN-approved files. No phantom paths.

### 1. VisualGateResult unit tests

```
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_visual_gate_result.py -q
```

Expected: All VisualGateResult tests pass. If not met: block.

### 2. VisualGateResult API route tests

```
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_visual_gate_result_api.py -q
```

Expected: All API route tests pass. If not met: block.

### 3. Existing run-profile tests

```
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_run_profile.py -q
```

Expected: All existing profile tests pass (50). If not met: block — indicates backward incompatibility.

### 4. Existing API tests

```
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_run_profile_api.py -q
```

Expected: All pass (8). If not met: block.

### 5. Existing workspace tests

```
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -q
```

Expected: All pass (310+). If not met: block.

### 6. Full regression

```
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_run_persistence.py services/runner/tests/test_runtime_evidence.py services/runner/tests/test_artifact_store.py services/runner/tests/test_docker_run_artifacts.py services/runner/tests/test_run_profile.py services/task_intake/tests/test_run_profile_api.py services/task_intake/tests/test_artifact_workspace_shell.py services/task_intake/tests/test_local_run_history_in_page.py services/task_intake/tests/test_local_operator.py services/task_intake/tests/test_runtime_evidence_serialization_contract.py services/task_intake/tests/test_task_intake.py -q
```

Expected: All pass. If not met: block.

### 7. Visual Gate smoke

```
PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-visual-gate-result.py
```

Expected: "VISUAL GATE RESULT SMOKE PASSED" as the last stdout line. No repository residue. Temporary directories cleaned up. If not met: block.

### 8. Forbidden file changes

```
git diff --name-only -- services/runner/src/runner/run_profile.py services/runner/src/runner/artifacts.py services/runner/src/runner/runtime_evidence.py services/runner/src/runner/run_persistence.py services/runner/src/runner/review_boundary.py services/task_intake/src/task_intake/artifact_workspace.py services/task_intake/src/task_intake/runtime_evidence_serialization.py services/task_intake/src/task_intake/manual_orchestration.py services/task_intake/src/task_intake/local_operator.py ROADMAP.md .project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md pyproject.toml Makefile
```

Expected: empty. If not met: block.

### 9. Planning lock diff

```
git diff -- .project-memory/pr/0149-visual-gate-runtime-object/PLAN.md .project-memory/pr/0149-visual-gate-runtime-object/reviews/plan-review.yml
```

Expected: empty (planning artifacts unchanged during implementation). If not met: block.

### 10. Residue check

```
git status --short
```

Expected: only approved files in dirty tree. No unknown files outside the PR directory and the approved paths. If not met: block.

## END-TO-END SMOKE

Script path: scripts/smoke-visual-gate-result.py

Command:
```
PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-visual-gate-result.py
```

Smoke sequence:
1. Create isolated temporary runs_root.
2. Create a run directory with a canonical persisted run (via persist_run_record).
3. Create a run-profile.json with a Mermaid artifact descriptor (kind="mermaid", media_type="text/vnd.mermaid", ref pointing to a synthetic .mmd file).
4. Create the synthetic .mmd file referenced by the profile descriptor.
5. Create a VisualGateResult with:
   - status="pending", human_review_required=false, evidence_refs containing a run-relative ref.
   - required_diagrams with one entry referencing the Mermaid descriptor via profile_descriptor_key:.
6. Verify creation succeeds and returns ok=True, visual_gate_sha256 is a 64-char hex string.
7. Verify readback returns the same object with hash_match=True.
8. Verify deterministic hash: create identical object, assert same hash.
9. Verify semantic hash change: change status to "ready_needs_review", assert different hash.
10. Create a VisualGateResult with status="passed", human_review_required=false.
11. Verify passed object validates and reads back.
12. Test missing state: read nonexistent VisualGateResult, assert ok=False, error="not_found".
13. Test malformed state: write corrupt JSON, assert ok=False, error="malformed".
14. Test unsupported schema version: write object with schema_version="2", assert ok=False, error="unsupported_schema_version".
15. Test hash mismatch: modify the file after creation, assert hash_match=False.
16. Test status and human_review_required consistency: attempt creation with status="passed" and human_review_required=true, assert validation rejection.
17. Test rejected references: create with invalid descriptor_ref, assert validation rejection.
18. Test duplicate diagram_id: create with two required_diagrams having same diagram_id, assert validation rejection.
19. Verify GET /runs/<run_id>/visual-gate-result returns correct JSON for ready state.
20. Verify GET /runs/<run_id>/visual-gate-result returns 200 with ok=False for missing state.
21. Verify no repository residue: temporary directory cleaned up, no .ariadne directory created under pwd.
22. Verify no UI mutation: no artifact_workspace.py changes needed.

Exact success marker: "VISUAL GATE RESULT SMOKE PASSED" as last stdout line.

## IMPLEMENTATION REPORT

Require:

`.project-memory/pr/0149-visual-gate-runtime-object/IMPLEMENTATION_REPORT.md`

It must begin with:

> This implementation report is handoff context, not proof.
> Agent output is not proof.
> Reviewer must verify claims against files, diffs, validation output,
> dirty tree, PLAN DRIFT GATE, and NO-DRIFT CHECK.

Require all 11 canonical sections per IMPLEMENTATION_HANDOFF_ARTIFACT_CONTRACT.md.

## PLAN DRIFT GATE

Block implementation completion if:

1. Any changed file outside the approved allowlist.
2. PLAN.md or plan-review.yml changes during implementation.
3. Architecture diverges from OPTION A (run-directory visual gate sidecar).
4. A second Visual Gate source of truth exists alongside visual-gate-result.json.
5. Visual Gate state is embedded into run-profile.json (profile schema change).
6. Agent output is represented as gate proof (e.g., an agent-generated status shown as verified).
7. Mermaid descriptor presence is represented as diagram validity or approval.
8. Evidence references are represented as verified proof without physical verification.
9. "passed" status is represented as human approval without admissible evidence.
10. Contradictory status + human_review_required combinations are silently accepted.
11. Non-deterministic serialization or hashes (e.g., non-deterministic key order, timezone-dependent timestamps).
12. Silent hash repair or automatic rewrite after mismatch detection.
13. Unsafe references or paths accepted (absolute, traversal, URL, file:, data:, javascript:).
14. Browser-controlled roots or paths accepted for the API route.
15. UI mutation — any change to artifact_workspace.py workspace rendering.
16. HTTP mutation outside the single approved GET-only route.
17. Diagram rendering or viewer work from PR 0150.
18. Readiness enforcement from PR 0151 (pipeline blocking, missing-diagram enforcement).
19. Human approval artifact from PR 0152 (approval field, approve/reject controls).
20. Artifact Registry or artifact acceptance state.
21. Agent, provider, Git, gh, Docker, shell, or external execution.
22. Existing contract regression (profile tests, persistence tests, evidence tests fail).
23. Validation or smoke failure.
24. Repository residue (untracked files outside PR directory and approved paths).
25. Missing or inaccurate IMPLEMENTATION_REPORT.md.

## NO-DRIFT CHECK

Require affirmative confirmation:

1. Correct branch: 0149-visual-gate-runtime-object.
2. Correct roadmap slot: PR 0149 (Visual Gate Runtime Object) — next after PR 0148.
3. Exact allowlist and planning lock: only approved files changed. PLAN.md and plan-review.yml unchanged.
4. Selected architecture: OPTION A — run-directory visual gate sidecar at visual-gate-result.json.
5. One Visual Gate source of truth: visual-gate-result.json. No duplicate state in run-profile.json or run.json.
6. Exact schema version "1", exact fields with bounds, types, and patterns as defined.
7. Exact required-diagram semantics: diagram_id, diagram_type, descriptor_ref, required as stored fields. presence_state and validity_state computed by reader, not stored.
8. Exact status semantics: pending, ready_needs_review, passed, failed — with consistency rules against human_review_required.
9. Exact human-review semantics: human_review_required only true for ready_needs_review. Does not prove review occurred. PR 0152 deferred.
10. Controlled evidence references: run-relative:, sha256:, profile_descriptor_key: — all validated. Unsafe forms rejected.
11. Deterministic serialization: sort_keys=True, alphabetical lists, canonical key order.
12. Visible missing, malformed, unsupported, stale, and mismatch states in read responses.
13. No false proof or approval claims: "passed" does not mean human approval. evidence_refs are references, not verified proof.
14. PR 0148 preservation: kind="mermaid", media_type="text/vnd.mermaid", Mermaid read functions unchanged. profile schema version "1" unchanged.
15. Existing runtime preservation: run persistence, runtime evidence, profile sidecar, ArtifactStore, all unchanged.
16. PR 0150-0152 deferral: no diagram rendering, no readiness enforcement, no human approval artifact.
17. Artifact Registry deferral: no registry, no acceptance state.
18. Required validation and smoke: all 10 validation commands pass.
19. No residue: git status clean except approved files.
20. Physical evidence precedence: file contents, test results, smoke output, diffs, and validation evidence override agent claims.

## STOP CONDITIONS

Implementation must stop if:

1. The locked plan cannot be followed (architecture, scope, allowlist).
2. A required file is outside the allowlist.
3. Existing architecture contradicts OPTION A (e.g., a profile schema change is needed).
4. ev_contract_version or profile schema version must change unexpectedly.
5. Human approval semantics cannot remain separate from PR 0152.
6. Readiness enforcement from PR 0151 becomes necessary during implementation.
7. UI mutation becomes necessary.
8. Unsafe references or non-deterministic state cannot be avoided.
9. Tests or smoke fail.
10. Unexplained residue appears.
11. Architect authority is required beyond what is already documented.

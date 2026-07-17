# PR 0147D — Construction Estimate Read-Only Dogfood Adapter Plan

## EVIDENCE SNAPSHOT

1. HEAD: `73f1c65ef1a10c9ee04bfdabf5d62c762727a913`
2. origin/main: `73f1c65ef1a10c9ee04bfdabf5d62c762727a913`
3. Merge base: `73f1c65ef1a10c9ee04bfdabf5d62c762727a913`
4. Branch: `0147d-construction-estimate-read-only-dogfood-adapter`
5. Dirty tree: clean
6. Cached diff: empty
7. PR 0147C merge evidence: `73f1c65 (HEAD -> 0147d-..., origin/main, origin/HEAD, main) PR 0147C — Domain-Neutral Run and Artifact Profile Contract (#176)`

## ROADMAP ALIGNMENT

- roadmap track: Operator Enablement Bridge (non-product governance insertions after Stream 2, before PR 0148)
- expected PR slot: PR 0147D (Construction Estimate Read-Only Dogfood Adapter)
- why this PR is next: PR 0147C (Domain-Neutral Run and Artifact Profile Contract) is complete. PR 0147D is the first real non-software dogfood adapter that proves the profile contract works for a construction-estimate domain without changing the core profile schema, adding domain-specific rendering, or adding HTTP mutation.
- batching policy check: Coherent single-adapter PR — bounded source parser, deterministic profile mapping, no core contract changes, no new dependencies.
- drift heuristic check: Not triggered.
- architect sign-off required: yes
- architect sign-off reference: Human architect authorized PR 0147D as a non-renumbering insertion after PR 0147C and before PR 0148. PR 0148 remains Mermaid Artifact Type Read Model.

## OPTION DECISION: OPTION A — STRICT UTF-8 CSV ESTIMATE

**Why CSV over JSON**: A CSV input contract mirrors real-world construction-estimate exchange formats (spreadsheet exports, quantity surveyor outputs, cost database CSV dumps). The standard-library `csv` module requires no dependency. The strict header contract provides deterministic column mapping without schema negotiation.

**Why not JSON**: A JSON input contract would be a second domain-neutral schema alongside the profile schema, adding maintenance burden without demonstrating real-world CSV ingestion.

**Why not XLSX**: The repository does not have an approved XLSX dependency. Adding `openpyxl` or similar would require justification for a single adapter. CSV is a universally accepted estimate exchange format.

## INPUT CONTRACT

### Source format: Strict UTF-8 CSV

### Required headers (exact, case-sensitive, deterministic column mapping)

```
estimate_id,title,project_name,currency,line_item_id,description,category,quantity,unit,unit_rate,line_total,notes
```

### Column specification

| Column | Type | Required | Max length | Validation |
|---|---|---|---|---|
| estimate_id | str | yes | 64 chars | Non-empty, no commas within field |
| title | str | yes | 200 chars | Non-empty |
| project_name | str | yes | 200 chars | Non-empty |
| currency | str | yes | 3 chars | ISO 4217 code (USD, EUR, GBP, etc.) |
| line_item_id | str | yes | 64 chars | Must match `^[a-zA-Z0-9_\-\.]+$`. Unique across rows. |
| description | str | yes | 500 chars | Non-empty |
| category | str | yes | 100 chars | Non-empty |
| quantity | str | yes | — | Parsed as Decimal. Must be > 0. |
| unit | str | yes | 50 chars | See unit policy below |
| unit_rate | str | yes | — | Parsed as Decimal. Must be > 0. |
| line_total | str | no | — | If present, parsed as Decimal. If absent or empty, recalculated as quantity * unit_rate. |
| notes | str | no | 1000 chars | Optional text |

### Numeric contract

| Property | Value |
|---|---|
| Number type | `decimal.Decimal` for all financial values |
| Decimal separator | `.` (period) — rejects `,` as thousands separator |
| Thousands separator | None — digits only |
| Negative values | Rejected for quantity, unit_rate, line_total |
| Zero values | Rejected for quantity, unit_rate |
| Max precision | 20 digits |
| Max scale | 4 decimal places |
| Rounding | `ROUND_HALF_UP` for any display formatting |
| Line-total policy | **Authoritative if supplied, recalculated if absent**. If supplied, must match `quantity * unit_rate` within 0.01 tolerance (2 decimal places). Mismatch = rejection. |
| Subtotal | Computed as sum of line_total (authoritative or recalculated) |
| Grand total | Computed as sum of subtotal (single currency — no multi-currency estimate accepted) |

### Currency policy

- All rows must have the same ISO 4217 currency code.
- Mixed currencies are rejected with a `mixed_currencies` error.
- Currency code is validated against a known set (USD, EUR, GBP, CAD, AUD, JPY, CHF, CNY, INR, MXN, BRL, SEK, NOK, NZD, KRW, SGD).

### Unit policy

Bounded inert strings with an explicit "other" escape:

```
"each", "hour", "day", "week", "month", "lump_sum",
"linear_foot", "square_foot", "cubic_foot",
"linear_meter", "square_meter", "cubic_meter",
"kilogram", "tonne", "pound",
"gallon", "liter",
"percent"
```

Any other value is accepted as a valid unit string (bounded to 50 chars) but flagged in the validation report as "unrecognized_unit".

No unit conversion or dimensional inference is performed.

### Row and size bounds

| Property | Value |
|---|---|
| Max file size | 1 MB |
| Max rows (data, excluding header) | 1000 |
| Max field length | 1000 chars |
| Max duplicate estimate_id | 1 (all rows share the same estimate_id — mismatched estimate_id rejected) |

### Encoding

- UTF-8 only. Reject non-UTF-8 bytes.
- BOM (byte-order mark) is stripped if present.
- CRLF and LF line endings accepted.

### Blank rows

Blank rows are silently skipped.

### Duplicate header detection

If the header row contains duplicate column names, the input is rejected.

### Malformed CSV detection

The Python `csv` module raises on quoting errors. Any `csv.Error` results in a malformed-input rejection.

### Source hash

SHA-256 of the complete source file bytes, excluding any leading BOM.

## REASON CODES

All reason codes are lowercase with underscores:

```text
source_missing
source_not_a_file
source_too_large
unsupported_encoding
malformed_csv
malformed_header
missing_required_column:<column_name>
duplicate_header_column:<column_name>
missing_estimate_id
mismatched_estimate_id
invalid_line_item_id:<id>
duplicate_line_item_id:<id>
invalid_quantity:<id>
invalid_unit_rate:<id>
invalid_line_total:<id>
line_total_mismatch:<id>:expected:<expected>:got:<got>
invalid_currency
mixed_currencies:<currencies>
too_many_rows:<count>
unsafe_path
run_not_found
run_missing
profile_validation_error:<code>
profile_write_error
profile_readback_error
profile_hash_mismatch
source_changed_during_read
```

## ADAPTER MODULE

### services/runner/src/runner/construction_estimate_adapter.py (NEW)

Public functions:

```python
def read_estimate_csv(path: str) -> dict:
    """Parse and validate a CSV estimate file.
    
    Returns dict with:
      - ok: bool
      - error: str or None
      - details: list of error codes or None
      - estimate: dict or None (parsed and validated estimate data)
      - source_sha256: str or None
    """

def estimate_to_profile(
    runs_root: str,
    run_id: str,
    estimate: dict,
    source_sha256: str,
) -> dict:
    """Map a validated estimate to a PR 0147C run profile.
    
    Calls run_profile.create_run_profile() with:
      - profile_key: "construction-estimate-v1"
      - presentation with title, neutral facts
      - artifact groups (original_estimate, normalized_estimate, validation)
      - artifact descriptors
    """

def create_construction_estimate_profile(
    runs_root: str,
    run_id: str,
    source_path: str,
) -> dict:
    """Read CSV, validate, create profile in one call.
    
    This is the CLI-callable entrypoint.
    """
```

The module does NOT import `csv` at module level — only inside `read_estimate_csv()`.

## PROFILE MAPPING

### profile_key

`"construction-estimate-v1"`

### Run presentation title

`f"Estimate: {estimate['title']} ({estimate['estimate_id']})"`

### Neutral facts

| Key | Label | Value | Value type |
|---|---|---|---|
| estimate_id | Estimate ID | estimate.estimate_id | text |
| project_name | Project Name | estimate.project_name | text |
| currency | Currency | estimate.currency (e.g. "USD") | text |
| item_count | Line Items | len(estimate.items) | number |
| category_count | Categories | len(estimate.categories) | number |
| subtotal | Subtotal | estimate.subtotal (Decimal) | currency |
| grand_total | Grand Total | estimate.grand_total (Decimal) | currency |
| source_format | Source Format | "CSV" | text |
| validation_status | Validation | "passed" | text |

### Artifact groups

| Key | Label | Display order |
|---|---|---|
| original | Original Estimate | 1 |
| normalized | Normalized Estimate | 2 |
| validation | Validation Reports | 3 |

### Artifact descriptors

| Key | Label | Kind | Evidence role | Media type | Ref | Required |
|---|---|---|---|---|---|---|
| source_csv | Original CSV | source_file | input | text/csv | run-relative:source-estimate.csv | true |
| normalized_json | Normalized Estimate | normalized_data | output | application/json | run-relative:normalized-estimate.json | true |
| line_items_csv | Line Items Table | itemized_list | report | text/csv | run-relative:line-items.csv | true |
| validation_report | Validation Report | validation | supporting | text/plain | run-relative:validation-report.txt | false |

**Note**: The original source CSV is COPIED into the run directory as `source-estimate.csv` to ensure the profile reference is contained. The adapter reads from the source path, validates, and then copies the source bytes (unchanged) into the run directory. Source immutability is verified by comparing SHA-256 before and after the copy.

## CLI CONTRACT

### scripts/create-construction-estimate-profile.py (NEW)

```
python -m scripts.create_construction_estimate_profile \
    --source /path/to/estimate.csv \
    --runs-root /path/to/runs \
    --run-id <id>
```

Options:
- `--source` (required): controlled local file path
- `--runs-root` (required): validated runs root directory
- `--run-id` (required): existing or to-be-created run ID
- `--create-run`: if set, creates a canonical run via `run_persistence.persist_run_record()` before processing
- `--json`: output JSON result

Exit codes:
- 0: success (profile created, source unchanged)
- 1: validation or processing error
- 2: unsafe or missing source

The CLI does NOT:
- Launch agents
- Call providers
- Access network
- Use shell commands
- Use git or gh
- Use Docker
- Open a browser
- Start the local operator
- Write to source file
- Modify run.json

## SOURCE HANDLING

1. `--source` path is resolved via `os.path.realpath()`.
2. Must be a regular file (`os.path.isfile()`).
3. Must not be a symlink that escapes expected directories (optional hardening — at minimum reject absolute path traversal relative to the resolved real path).
4. Must be <= 1 MB.
5. Must be readable as UTF-8 (with BOM stripping).
6. SHA-256 computed before reading content.
7. After reading and copying to run directory, SHA-256 recomputed on the copy. Must match original.
8. Source file is NEVER modified by the adapter.

## DOGFOOD FIXTURE

### tests/fixtures/construction-estimate-sample.csv (NEW)

A synthetic, non-confidential CSV estimate:

```csv
estimate_id,title,project_name,currency,line_item_id,description,category,quantity,unit,unit_rate,line_total,notes
EST-001,Sample Warehouse Construction,Acme Industrial Park,USD,ITEM-001,Site Preparation,site_prep,1,lump_sum,25000.00,25000.00,Mobilize equipment
EST-001,Sample Warehouse Construction,Acme Industrial Park,USD,ITEM-002,Concrete Foundation (Type A),foundation,500,square_foot,85.00,42500.00,
EST-001,Sample Warehouse Construction,Acme Industrial Park,USD,ITEM-003,Structural Steel Frame,structure,50,tonne,3200.00,160000.00,Supplier quote attached
EST-001,Sample Warehouse Construction,Acme Industrial Park,USD,ITEM-004,Metal Roofing,roofing,20000,square_foot,12.50,250000.00,
EST-001,Sample Warehouse Construction,Acme Industrial Park,USD,ITEM-005,Electrical Rough-In,electrical,1,lump_sum,45000.00,45000.00,
EST-001,Sample Warehouse Construction,Acme Industrial Park,USD,ITEM-006,Plumbing Rough-In,plumbing,1,lump_sum,35000.00,35000.00,
EST-001,Sample Warehouse Construction,Acme Industrial Park,USD,ITEM-007,HVAC System,hvac,1,lump_sum,55000.00,55000.00,,
```

Also add programmatic invalid fixtures:
- Empty file
- Missing columns
- Duplicate line_item_id
- Invalid quantity (non-numeric, negative, zero)
- Mixed currencies
- Line-total mismatch
- Oversize (>1 MB)
- Non-UTF-8 encoding

## WORKSPACE BEHAVIOR

The existing generic profile renderer from PR 0147C renders the construction estimate profile without ANY construction-specific branches.

Rendered content includes:
1. Profile key: `construction-estimate-v1`
2. Estimate title from neutral facts
3. Project name, currency, item count, categories
4. Subtotal and grand total (currency type — displayed with currency label)
5. Artifact groups: Original Estimate, Normalized Estimate, Validation Reports
6. Artifact descriptors under each group
7. Source CSV descriptor with `text/csv` media type
8. Profile hash state displayed
9. Label: "Profile metadata — not runtime proof."

No construction-specific JavaScript, no estimate editing, no recalculate buttons, no approve/reject controls.

## VALIDATION PLAN

### 1. Adapter Tests

```bash
PYTHONPATH=services/runner/src python -m pytest services/runner/tests/test_construction_estimate_adapter.py -q
```

Expected: all adapter tests pass (schema, decimal, path security, source immutability, profile mapping).
If not met: block.

### 2. Existing Profile Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/runner/tests/test_run_profile.py -q
```

Expected: all profile tests pass.
If not met: block.

### 3. Existing API Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_run_profile_api.py -q
```

Expected: all pass.
If not met: block.

### 4. Existing Workspace Tests

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python -m pytest services/task_intake/tests/test_artifact_workspace_shell.py -q
```

Expected: all pass.
If not met: block.

### 5. Existing Contract and Regression Tests

Full standard regression suite.

### 6. Construction Dogfood Smoke

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-construction-estimate-profile.py
```

Expected: all smoke assertions pass. No repository residue. Source unchanged.
If not met: block.

### 7. Forbidden Checks

```bash
# Source non-mutation
grep "write\|modify\|edit\|update" scripts/create-construction-estimate-profile.py | grep -i "source\|csv"
```

Expected: no source write in the adapter CLI (only copy to run directory).
If not met: block.

```bash
# No construction-specific workspace branch
grep -n "construction\|estimate\|EST-" services/task_intake/src/task_intake/artifact_workspace.py
```

Expected: no matches (exit code 1).
If not met: block.

## PLAN DRIFT GATE

Block implementation completion if:

1. Any changed file outside the approved allowlist.
2. PLAN.md or plan-review.yml changes.
3. More than one source format is implemented.
4. Binary floating-point is used for canonical financial totals.
5. Source estimate files are modified.
6. Source writeback exists.
7. Arbitrary paths or URLs are accepted.
8. Browser upload or path selection is added.
9. Profile schema version "1" is changed.
10. A new profile value type is added.
11. A new evidence role is added.
12. A new controlled-reference form is added.
13. Construction-specific rendering is added to the generic workspace.
14. HTTP mutation is added.
15. Quantity takeoff, scheduling, WBS, Gantt, procurement, or optimization is added.
16. Agent, provider, shell, git, gh, Docker, or network execution is added.
17. PR 0148 or later work is absorbed.
18. Required tests or smoke fail.
19. Repository-local runtime residue remains.
20. IMPLEMENTATION_REPORT.md is missing or inaccurate.

## NO-DRIFT CHECK

Require confirmation:

1. Correct branch.
2. Exact approved file scope.
3. Planning artifacts locked.
4. Roadmap alignment complete.
5. One source format (CSV).
6. Strict UTF-8 CSV with exact header contract.
7. Decimal-based financial arithmetic.
8. Line-total policy: authoritative if supplied, recalculated if absent, mismatch rejected.
9. Source file remains unchanged (SHA-256 verified).
10. Profile mapping deterministic.
11. run-profile.json schema remains version "1".
12. profile_sha256 behavior unchanged.
13. Six fact types unchanged.
14. Five evidence roles unchanged.
15. Two controlled-reference forms unchanged.
16. Generic GET profile route reused.
17. Generic workspace renderer reused (no construction-specific branches).
18. No source writeback.
19. No HTTP mutation.
20. No Artifact Registry or artifact acceptance.
21. No quantity takeoff, schedule, WBS, Gantt.
22. No agent/provider/shell/git/gh/Docker/network execution.
23. PR 0143–0147C preserved.
24. PR 0148 remains separate.
25. Construction smoke passes.
26. No repository residue.
27. IMPLEMENTATION_REPORT.md exists and was read back.
28. PLAN DRIFT GATE passed.

## STOP CONDITIONS

Implementation must stop if:

1. The CSV input format cannot be selected unconditionally.
2. Decimal arithmetic cannot be deterministic.
3. Source immutability cannot be guaranteed.
4. PR 0147C cannot represent the estimate without schema changes.
5. Generic workspace rendering is insufficient.
6. An unapproved core file must change.
7. An external dependency is required.
8. Required validation fails.

## IMPLEMENTATION FILE SCOPE

### Approved files

1. **services/runner/src/runner/construction_estimate_adapter.py** (NEW) — CSV parser, estimate validator, profile mapper, CLI delegate function.
2. **services/runner/tests/test_construction_estimate_adapter.py** (NEW) — All adapter, schema, decimal, path, immutability, and profile-mapping tests.
3. **tests/fixtures/construction-estimate-sample.csv** (NEW) — Synthetic valid estimate fixture.
4. **scripts/create-construction-estimate-profile.py** (NEW) — CLI entrypoint.
5. **scripts/smoke-construction-estimate-profile.py** (NEW) — End-to-end dogfood smoke.
6. **docs/CONSTRUCTION_ESTIMATE_DOGFOOD.md** (NEW) — Runbook documenting the adapter.
7. **ROADMAP.md** (EDIT) — Add PR 0147D insertion note.
8. **.project-memory/roadmaps/ARIADNA_PRODUCT_ROADMAP_AFTER_PR0136.md** (EDIT) — Add PR 0147D insertion note.
9. **.project-memory/pr/0147d-construction-estimate-read-only-dogfood-adapter/IMPLEMENTATION_REPORT.md** (NEW)
10. **.project-memory/pr/0147d-construction-estimate-read-only-dogfood-adapter/reviews/precommit-review.yml** (NEW)

### Not modified

- services/runner/src/runner/run_profile.py
- services/runner/src/runner/run_persistence.py
- services/runner/src/runner/runtime_evidence.py
- services/runner/src/runner/artifacts.py
- services/task_intake/src/task_intake/server.py
- services/task_intake/src/task_intake/artifact_workspace.py
- services/task_intake/src/task_intake/local_operator.py
- services/task_intake/src/task_intake/runtime_evidence_serialization.py
- services/task_intake/src/task_intake/manual_orchestration.py
- services/task_intake/src/task_intake/manual_orchestration_cli.py
- services/task_intake/tests/test_run_profile_api.py
- services/task_intake/tests/test_artifact_workspace_shell.py
- services/task_intake/tests/test_local_operator.py
- services/task_intake/tests/test_manual_orchestration.py
- services/runner/tests/test_run_profile.py
- scripts/create-run-profile.py
- scripts/smoke-run-profile.py
- Makefile, pyproject.toml, README.md
- docs/LOCAL_OPERATOR.md, docs/MANUAL_ORCHESTRATION.md, docs/RUN_ARTIFACT_PROFILE.md

## NON-GOALS

1. Implementing the adapter (planning task only).
2. XLSX, PDF, OCR parsing.
3. BIM, IFC, or drawing measurement.
4. Quantity takeoff or dimension inference.
5. Cost database or material price lookup.
6. Procurement, purchase orders, or supplier integration.
7. Schedule, WBS, PBS, Gantt generation.
8. ML or LLM extraction.
9. Agent execution.
10. Mermaid or Visual Gate.
11. Artifact Registry or artifact acceptance.
12. Source writeback or estimate editing.
13. HTTP mutation.
14. Editing core profile, workspace, server, operator, or orchestration code.
15. Writing plan-review.yml, IMPLEMENTATION_REPORT.md, or precommit-review.yml during planning.

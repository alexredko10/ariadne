# Ariadne — Construction Estimate Dogfood Adapter

PR 0147D demonstrates the PR 0147C domain-neutral run-profile contract with
a real non-software dogfood adapter for construction estimates.

## Core Principle

The adapter reads a strict UTF-8 CSV construction estimate, validates it
deterministically, and maps it to a version-1 run-profile sidecar without
changing the profile schema, adding new HTTP routes, or modifying workspace
rendering.

## Source Format

Strict UTF-8 CSV with exactly 12 ordered columns:

| # | Column | Type | Required | Max Length |
|---|---|---|---|---|
| 1 | estimate_id | str | yes | 64 |
| 2 | title | str | yes | 200 |
| 3 | project_name | str | yes | 200 |
| 4 | currency | str | yes | 3 (ISO 4217) |
| 5 | line_item_id | str | yes | 64 (unique) |
| 6 | description | str | yes | 500 |
| 7 | category | str | yes | 100 |
| 8 | quantity | decimal | yes | > 0 |
| 9 | unit | str | yes | 50 |
| 10 | unit_rate | decimal | yes | > 0 |
| 11 | line_total | decimal | no | Recalculated if absent |
| 12 | notes | str | no | 1000 |

### Numeric Rules

- `decimal.Decimal` for all financial values
- Decimal separator: period (`.`)
- No thousands separators
- Max precision 20, max scale 4
- Negative and zero rejected for quantity, unit_rate
- Line-total: authoritative if supplied (must match quantity × unit_rate within 0.01), recalculated if absent
- Rounding: `ROUND_HALF_UP`

### Currency Rules

- All rows must share the same ISO 4217 currency code
- Mixed currencies are rejected
- Supported: USD, EUR, GBP, CAD, AUD, JPY, CHF, CNY, INR, MXN, BRL, SEK, NOK, NZD, KRW, SGD

### Unit Rules

19 approved units: each, hour, day, week, month, lump_sum, linear_foot, square_foot,
cubic_foot, linear_meter, square_meter, cubic_meter, kilogram, tonne, pound,
gallon, liter, percent, piece. Any other unit is valid but flagged as "unrecognized_unit".

### Bounds

- Max file size: 1 MB
- Max rows: 1000
- Source immutability: verified via SHA-256 before and after copy

## CLI

```bash
python -m scripts.create_construction_estimate_profile \
    --source /path/to/estimate.csv \
    --runs-root /path/to/runs \
    --run-id <id> \
    [--create-run] \
    [--json]
```

Exit codes: 0 success, 1 validation/processing error, 2 unsafe/missing source.

The CLI does NOT launch agents, call providers, access the network, use shell
commands, use git/gh, use Docker, open a browser, write to the source CSV, or
modify run.json.

## Profile Mapping

Profile key: `construction-estimate-v1`

Neutral facts:

| Key | Label | Type |
|---|---|---|
| estimate_id | Estimate ID | text |
| project_name | Project Name | text |
| currency | Currency | text |
| item_count | Line Items | number |
| category_count | Categories | number |
| subtotal | Subtotal | currency |
| grand_total | Grand Total | currency |
| source_format | Source Format | text |
| validation_status | Validation | text |

Artifact groups: Original Estimate, Normalized Estimate, Validation Reports.

Artifact descriptors:
- Original CSV (required, `run-relative:source-estimate.csv`)
- Normalized Estimate (required, `run-relative:normalized-estimate.json`)
- Line Items Table (required, `run-relative:line-items.csv`)
- Validation Report (optional, `run-relative:validation-report.txt`)

## Profile Integrity

The profile is written with `profile_key: construction-estimate-v1` using
the same deterministic serialization, self-excluding hash, and atomic write
pattern as the PR 0147C profile contract.

## Read-Only Surface

The existing `GET /runs/<run_id>/profile` route and generic workspace renderer
display the construction estimate profile without any construction-specific code.

## Boundaries

- **Read-only**: The source CSV is NEVER modified by the adapter.
- **No HTTP mutation**: No new routes, no POST/PUT/PATCH/DELETE.
- **No workspace changes**: Generic renderer only — no construction-specific branches.
- **No new data types**: Only the six PR 0147C fact types are used.
- **No execution**: No agents, providers, shell, git, gh, Docker, or network access.
- **No Artifact Registry**: No artifact lifecycle or acceptance state.

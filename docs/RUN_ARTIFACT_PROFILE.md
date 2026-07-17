# Ariadne — Run Artifact Profile Contract

PR 0147C introduces a domain-neutral descriptive profile for persisted runs.

## Core Principle

A run profile (`run-profile.json`) sits alongside `run.json` and `manifest.json` in each run directory. It supplements runtime evidence with optional descriptive metadata — neutral facts, artifact groups, and artifact descriptors. It does not replace or override any existing evidence.

## Canonical Path

```
<runs_root>/<run_id>/run-profile.json
```

## Schema Version

Current: `"1"`

## Profile Key

The `profile_key` field identifies the profile type. It must match `^[a-z][a-z0-9\-]{1,63}$`. For domain-neutral use: `"domain-neutral-v1"`.

## Profile Hash

`profile_sha256` is a full 64-character lowercase SHA-256 hex of the canonical profile JSON, computed with the `profile_sha256` field itself excluded from the hash input.

## Profile JSON Shape

```json
{
    "schema_version": "1",
    "profile_key": "domain-neutral-v1",
    "profile_sha256": "<64-char hex>",
    "run_id": "<existing-run-id>",
    "run_presentation": {
        "title": "Optional title (max 200 chars)",
        "status_label": "Optional label (max 100 chars)",
        "neutral_facts": [
            {
                "key": "unique_key",
                "label": "Display Label",
                "value": "...",
                "value_type": "text|number|date|boolean|enum|currency",
                "unit": null,
                "currency": null,
                "display_order": 1,
                "source": "operator|adapter|system"
            }
        ]
    },
    "artifact_groups": {
        "reports": {
            "key": "reports",
            "label": "Reports",
            "display_order": 1
        }
    },
    "artifact_descriptors": [
        {
            "key": "unique_key",
            "label": "Display Label",
            "kind": "summary",
            "evidence_role": "input|output|report|capture|supporting",
            "media_type": "application/pdf",
            "ref": "run-relative:report.pdf",
            "sha256": null,
            "group_key": "reports",
            "display_order": 1,
            "required": true
        }
    ]
}
```

## Neutral Facts

| Field | Required | Type | Max | Notes |
|---|---|---|---|---|
| key | yes | string | 64 | `^[a-z][a-z0-9_]{1,63}$` |
| label | yes | string | 200 | Plain text |
| value | yes | varies | 1000 | See value types |
| value_type | yes | string | 20 | One of the six approved types |
| unit | no | string | 50 | Number type only |
| currency | no | string | 3 | ISO 4217, currency type only |
| display_order | yes | integer | — | >= 0 |
| source | no | string | 50 | operator, adapter, or system |

### Approved Value Types

| Type | JSON | Example |
|---|---|---|
| text | string | "My Project" |
| number | finite number | 150000.0 |
| date | YYYY-MM-DD | "2026-07-17" |
| boolean | true/false | true |
| enum | lowercase + underscore | "in_progress" |
| currency | finite number | 50000 (with "USD" currency field) |

Max 50 facts. Duplicate keys rejected.

## Artifact Groups

| Field | Required | Type | Max | Notes |
|---|---|---|---|---|
| key | yes | string | 64 | `^[a-z][a-z0-9_\-]{1,63}$` |
| label | yes | string | 200 | Plain text |
| display_order | yes | integer | — | >= 0 |

Max 20 groups. Duplicate keys rejected.

## Artifact Descriptors

| Field | Required | Type | Max | Notes |
|---|---|---|---|---|
| key | yes | string | 64 | Must match `^[a-z][a-z0-9_\-]{1,63}$` |
| label | yes | string | 200 | Plain text |
| kind | yes | string | 50 | Free form, e.g. "summary" |
| evidence_role | yes | string | 20 | input, output, report, capture, or supporting |
| media_type | yes | string | 100 | MIME type |
| ref | yes | string | 500 | See references below |
| sha256 | no | string | 64 | Lowercase hex |
| group_key | yes | string | 64 | Must reference an artifact group |
| display_order | yes | integer | — | >= 0 |
| required | yes | boolean | — | true or false |

Max 100 descriptors. Duplicate keys rejected. Conflicting refs (same ref, different sha256) rejected.

## Controlled References

| Form | Example | Security |
|---|---|---|
| run-relative:path | `run-relative:report.pdf` | Resolved relative to run directory. Traversal rejected. |
| sha256:hex | `sha256:abc123...` | ArtifactStore reference. Must be 64-char lowercase hex. |

Rejected: absolute paths, traversal, all URLs (https://, http://, file://, javascript:, data:).

## GET Route

```
GET /runs/<run_id>/profile
```

Returns versioned JSON with `ev_contract_version: "1"`. Response states:

| State | ok | profile_exists | hash_match |
|---|---|---|---|
| Available and verified | true | true | true |
| Available, hash mismatch | true | true | false |
| Not found | false | false | null |
| Malformed | false | true | null |
| Unsupported version | false | true | null |

## CLI Tool

```bash
python -m scripts.create_run_profile --runs-root /path/to/runs --run-id <id> [options]
```

## API (Library)

```python
from runner.run_profile import create_run_profile, read_run_profile

# Create a profile
result = create_run_profile(
    runs_root="/path/to/runs",
    run_id="my-run",
    presentation={"title": "My Run", "neutral_facts": [...]},
    artifact_groups={"docs": {...}},
    artifact_descriptors=[{...}],
)

# Read a profile
result = read_run_profile(runs_root="/path/to/runs", run_id="my-run")
```

## Boundaries

- Profile metadata is descriptive, not runtime proof.
- Profile does not override run_id, status, or any existing evidence.
- Profile does not add artifact acceptance or lifecycle state.
- Profile does not define executable code, templates, or plugins.
- Profile does not require Git, GitHub, branches, or PRs.
- Profile references are contained — no arbitrary filesystem access.

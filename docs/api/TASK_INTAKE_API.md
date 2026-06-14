# Task Intake API MVP

## POST /task-intake/normalize

Request:

```json
{
  "raw_input": "Fix the failing task flow after recent changes.",
  "input_type": "text",
  "repo_id": "example-repo",
  "branch": "main",
  "hint_labels": [],
  "language": "en"
}
```

Response:

```json
{
  "draft_id": "draft_example",
  "description": "Fix the failing task flow after recent changes.",
  "original_input": "Fix the failing task flow after recent changes.",
  "input_type": "text",
  "inferred_mode": "bugfix",
  "inferred_domains": ["example-domain"],
  "inferred_risk_hints": [],
  "suggested_repo_id": "example-repo",
  "mode_confidence": 0.75,
  "description_quality": "clear",
  "warnings": []
}
```

## POST /context/preview

MVP returns a mock preview until Core is implemented.

## POST /runs

MVP creates a mock run object until Conductor is implemented.

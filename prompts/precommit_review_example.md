# Example prompt for precommit-review.yml

Task:
Review current git diff before the initial skeleton commit.

Use memory:
- Read `.project-memory/memory_index.yml` first.
- Use labels: `contracts`, `agent-config`, `sprint-0`.

Check:
- No generated files.
- No old project-specific references.
- Docker Agent configs remain separate and controlled.
- Coder cannot commit/push/reset/restore/checkout.
- Read-only agents cannot write files.
- `.project-memory/` exists and is neutral.
- Validation was run or reason is stated.

Output:
- verdict: pass | warning | block
- blockers
- warnings
- suggested commit message

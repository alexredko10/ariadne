# Sprint 1 — Runner and Patch Pipeline

## Goal

Prove the core safety model: agents operate in an isolated sandbox and produce patch artifacts, not direct repository mutations.

## Scope

```text
[ ] Runner service skeleton
[ ] WorktreeManager.create_context_snapshot
[ ] WorktreeManager.create_sandbox
[ ] Mock Coder writes only inside sandbox
[ ] Raw diff generation
[ ] PatchNormalizer
[ ] Content-addressed artifact store
[ ] Patch validation: no absolute paths, no path traversal
[ ] ApplyPatch stub requiring approval
```

## Proof checklist

```text
[ ] sandbox has no VCS metadata
[ ] mock Coder cannot write to canonical repository
[ ] normalized patch uses repository-relative paths
[ ] new files are represented correctly
[ ] deleted files are represented correctly
[ ] ApplyPatch refuses to run without approval
```

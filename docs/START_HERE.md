# Start Here

## Product goal

Build a universal agentic development platform for controlled AI-assisted software engineering.

The platform must work with arbitrary repositories. It must not be tied to a specific application, route structure, storage backend, UI feature, or legacy project name.

## Core outcome

A user can submit a task, inspect what the system believes is in scope, approve the run, observe execution, review the patch, and apply it only after validation.

## Core pipeline

```text
Input
  -> Task Intake
  -> Repository Context Preview
  -> Task Subgraph
  -> Workflow Planning
  -> Sandboxed Execution
  -> Patch Normalization
  -> Verification
  -> Human Approval
  -> Apply Patch
  -> Graph and Memory Update
```

## Non-negotiable principles

```text
Agents never write directly to the canonical repository.
ApplyPatch is the only component allowed to modify the canonical repository.
The Runner owns sandbox execution.
The Conductor never mounts the container runtime socket.
The model gateway does not trust agent-provided request bodies for policy decisions.
Context previews do not start agents.
Voice input never starts agents directly.
Every patch is scope-checked before it can be applied.
Every run is observable and auditable.
```

## What to build first

Start with the Git repository skeleton. Then implement two parallel tracks:

```text
Track A: Task Intake mock loop
  manual text -> normalize -> preview mock -> mock run

Track B: Runner proof
  repository snapshot -> sandbox -> mock edit -> raw diff -> normalized patch artifact
```

This gives the project both a visible product loop and a safety-critical execution proof.

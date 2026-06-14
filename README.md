# Universal Agentic Development Platform

This repository is the neutral starting point for a platform that turns a software repository into a controlled AI-assisted engineering workspace.

The platform accepts a task, builds a scoped repository context, runs agents in isolated sandboxes, verifies their work, and applies changes only after policy checks and approval.

```text
task + repository
  -> task draft
  -> context preview
  -> task subgraph
  -> validated workflow
  -> sandboxed agents
  -> normalized patch
  -> verification
  -> approval gate
  -> apply patch
  -> update graph and memory
```

## Start here

Read these first:

1. `docs/START_HERE.md`
2. `docs/REPOSITORY_STRUCTURE.md`
3. `docs/DEVELOPMENT_ORDER.md`
4. `docs/AGENTS.md`
5. `docs/sprints/SPRINT_0_REPOSITORY_SKELETON.md`
6. `docs/sprints/SPRINT_1_RUNNER_PATCH_PIPELINE.md`

## First implementation goal

The first goal is not a full AI system. The first goal is a safe repository skeleton and a minimal visible loop:

```text
manual task text
  -> normalize task draft
  -> context preview mock
  -> create mock run
  -> show run status
```

In parallel, implement the first backend proof: Runner + snapshot + sandbox + raw diff + normalized patch artifact.

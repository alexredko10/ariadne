# Development Order

## Start with Git and structure

The first real development action should be repository initialization, not service implementation.

```bash
git init
git add .
git commit -m "chore: initialize platform repository skeleton"
```

After the skeleton is committed, build in this order.

## Phase 0: Repository skeleton

Deliver:

```text
- folder structure
- README
- Developer Pack
- agent briefs
- placeholder services
- placeholder tests
- docker-compose placeholder
- CI placeholder
```

## Phase 1: Runner proof

Deliver:

```text
- create repository snapshot without VCS metadata
- create sandbox from snapshot
- run mock agent edit inside sandbox
- compute raw diff
- normalize diff to repository-relative patch
- store patch as content-addressed artifact
```

This phase proves the most important safety property: agent code execution cannot modify the canonical repository.

## Phase 2: Task Intake mock loop

Deliver:

```text
- POST /task-intake/normalize
- POST /context/preview mock
- POST /runs mock
- simple run status object
```

This gives the frontend a visible product loop.

## Phase 3: Core MVP

Deliver:

```text
- repository scanner
- file and symbol nodes
- basic import/test links
- lexical search
- task subgraph output
```

## Phase 4: Conductor MVP

Deliver:

```text
- Run and Step models
- workflow state machine
- DAG validator stub
- Runner client
- approval gate state
```

## Phase 5: Frontend MVP

Deliver:

```text
- New Task screen
- context preview panel
- run progress page
- diff/artifacts page
- approval controls
```

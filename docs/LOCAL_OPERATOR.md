# Ariadne — Local Operator Runbook

PR 0147A makes the read-only Artifact Workspace platform operable locally
through a single supported operator entrypoint with safe loopback defaults.

## Prerequisites

- Python >= 3.11
- Git clone of the Ariadne repository
- `make install-dev` (installs runtime dependencies including uvicorn)

## Installation

```bash
make install-dev
```

This installs uvicorn>=0.29.0 and development dependencies (pytest, httpx).

## Primary Launch Command

```bash
make local-operator
```

This delegates directly to `python -m task_intake.local_operator`.

Default configuration:

- **Host**: `127.0.0.1` (loopback only)
- **Port**: `8000`
- **Runs root**: `.ariadne/runs` relative to the repository root

## Optional Configuration Flags

| Flag | Default | Description |
|---|---|---|
| `--host HOST` | `127.0.0.1` | Bind host. Public bind requires `--allow-public-bind`. |
| `--port PORT` | `8000` | Bind port. Privileged ports (<1024) require `--allow-privileged-port`. |
| `--runs-root PATH` | `.ariadne/runs` | Directory containing persisted run records. Created if absent. |
| `--check` | off | Validate configuration, print JSON, and exit. Does not start server. |
| `--allow-public-bind` | off | Permit binding to `0.0.0.0` (unsafe — prints warning). |
| `--allow-privileged-port` | off | Permit ports below 1024. |

Port override via Makefile:

```bash
make local-operator PORT=8080
```

## Expected Startup Output

```
Ariadne — Local Operator
  Runs root: /absolute/path/to/.ariadne/runs
  Workspace: http://127.0.0.1:8000/workspace
  Health:    http://127.0.0.1:8000/health
  Status:    READ-ONLY — no agent execution, no mutation, no orchestration.
  Press Ctrl-C to stop.
```

## Health Check

```bash
curl http://127.0.0.1:8000/health
```

Expected response includes `"status": "ok"`.

## Workspace URL

Open `http://127.0.0.1:8000/workspace` in a browser to see the Artifact Workspace
with four zones: Timeline, Artifact Canvas, Gates & Proofs, Logs & Captures.

## Runs Root Location

Default: `./.ariadne/runs` (created automatically if absent).

Each run is a subdirectory containing:

- `run.json` — persisted run record
- `manifest.json` — file manifest with hashes
- `run-report.txt` — run report (when available)

## How Persisted Runs Appear

Launch the workspace (`http://127.0.0.1:8000/workspace`). Runs appear in the
Timeline panel on the left. Click a run to view its detail in the Artifact Canvas.

## Empty Workspace Behavior

When no runs exist in the runs root, the Timeline shows:

> No runs available. Submit a task to see timeline entries.

## Missing Runs Root

Created automatically as an empty directory at startup (normal launch only).
The `--check` mode does not create the directory.

## How to Stop

Press `Ctrl-C`. The server shuts down gracefully via uvicorn's default signal
handling. No lingering processes, sockets, or temporary files remain.

## Common Configuration Failures

| Symptom | Likely Cause | Fix |
|---|---|---|
| `Error: uvicorn is not installed` | Missing installation | `make install-dev` |
| `Error: Public bind (0.0.0.0) is not permitted` | Forgot flag | Add `--allow-public-bind` |
| `Error: Privileged port (80) is not permitted` | Port < 1024 | Add `--allow-privileged-port` |
| `Error: Port must be between 1 and 65535` | Invalid port | Use valid port number |
| Port in use | Another process on same port | Use `--port` with different value |
| Workspace returns error | Server not ready | Wait for startup message |

## Read-Only Boundaries

The local operator serves the **read-only** Artifact Workspace. The following
are explicitly unavailable:

1. No agent launch — the operator does not start planner, plan-review, coder,
   precommit-review, or any other agent.
2. No orchestration — no orchestration pipeline, no role routing, no multi-step
   agent execution is available.
3. No mutation — no POST routes that create, modify, or delete artifact evidence.
4. No git push or PR creation — git and GitHub operations remain human-run.
5. No Docker — no Docker daemon interaction, no container execution.
6. No browser auto-open — the operator prints URLs but does not open a browser.
7. No external network calls — the operator only binds to the configured host.
8. No authentication or TLS — local, single-user, loopback-only by default.
9. No production deployment — `0.0.0.0` requires explicit `--allow-public-bind`
   and prints a warning. Production use is not supported.
10. No runs-root override via browser — the operator owns the runs root.
    Browser query parameters (`?runs_root=...`) are ignored in operator mode.
11. No persistent state changes — the operator does not write to the runs root
    during normal operation (except directory creation at startup).
12. No custom HTTP server — the operator uses uvicorn as the ASGI runtime.
13. No multi-user hosting — loopback-only by default.

## No Agent Execution

Agent launch is not implemented. `GET /workspace` shows read-only evidence only.

## No Orchestration

The orchestration pipeline (planner → plan-review → coder → precommit-review)
is not available from the operator. This is deferred to PR 0147B and later work.

## No Git Push or PR Creation

Git and GitHub operations are explicitly excluded from operator mode. These
remain human actions outside the operator boundary.

## Smoke Command

```bash
PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-local-operator.py
```

The smoke creates a canonical persisted run in an isolated temporary directory,
launches the official operator entrypoint, waits for readiness, and asserts all
13 route checks against the real running server.

## Expected Smoke Output

Successful smoke output ends with:

```
smoke: ALL CHECKS PASSED
```

Individual check lines:

```
smoke: creating canonical run...
smoke: using port NNNNN
smoke: launching operator: ...
smoke: waiting for /health...
smoke: operator ready
smoke: checking GET /health...
smoke: checking GET /workspace...
smoke: checking GET /runs...
smoke: checking GET /runs/<run_id>...
smoke: checking GET /runs/<run_id>/report...
smoke: checking operator mode security...
smoke: ALL CHECKS PASSED
smoke: shutting down operator...
smoke: temp directory removed
```

## Cleanup Guarantee

The smoke:

- Creates all run data in an isolated temporary directory (`/tmp/ariadne-smoke-*`).
- Launches the operator with `--runs-root` pointing to the temp directory.
- Terminates the operator via SIGTERM, escalating to SIGKILL after 5 seconds.
- Removes the temporary directory.
- Does **not** write to or modify the repository `.ariadne/runs` directory.

## Troubleshooting

1. Verify installation: `make install-dev`
2. Check configuration: `python -m task_intake.local_operator --check`
3. Run existing tests: `make test`
4. Check Python version: `python --version` (must be >= 3.11)

## Public Bind Warning

Binding to `0.0.0.0` makes the server accessible on the local network.
This is not a supported production deployment and should only be used
for local testing across containers or VMs. Always use `127.0.0.1` by default.

## Production Deployment

The local operator is **not** a production deployment tool. It does not support
TLS, authentication, rate limiting, logging infrastructure, or multi-user hosting.
Production deployment is out of scope for PR 0147A.

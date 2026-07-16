#!/usr/bin/env python3
"""
PR 0147A — End-to-End Smoke for Local Operator Launch.

Proves the full read-only Artifact Workspace platform works against a real
launched operator with real persisted run data.

Usage:
    PYTHONPATH=services/runner/src:services/task_intake/src python scripts/smoke-local-operator.py
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


# ---------------------------------------------------------------------------
# Free-port helper
# ---------------------------------------------------------------------------


def _find_free_port() -> int:
    """Find a free TCP port on 127.0.0.1."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _http_get(url: str) -> tuple[int, bytes, str]:
    """Send GET request. Returns (status, raw_body, content_type)."""
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read() if exc.fp else b"", ""
    except urllib.error.URLError as exc:
        return 0, str(exc.reason).encode(), ""


def _http_get_json(url: str) -> tuple[int, dict]:
    """Send GET request and parse JSON response."""
    status, raw, ct = _http_get(url)
    try:
        return status, json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return status, {"_raw": raw.decode("utf-8", errors="replace")}


# ---------------------------------------------------------------------------
# Readiness waiting
# ---------------------------------------------------------------------------


def _wait_for_health(base_url: str, timeout: float = 5.0) -> bool:
    """Poll GET /health until OK or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, data = _http_get_json(f"{base_url}/health")
        if status == 200 and isinstance(data, dict) and data.get("status") == "ok":
            return True
        time.sleep(0.2)
    return False


# ---------------------------------------------------------------------------
# Canonical persisted run fixture
# ---------------------------------------------------------------------------


def _create_smoke_run(runs_root: str) -> str:
    """Create a canonical persisted run using the real persist_run_record API.

    Returns the run_id.
    """
    from runner.run_persistence import (
        RunPersistenceRequest,
        persist_run_record,
    )

    run_id = "smoke-run-001"
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)

    report_path = os.path.join(run_dir, "run-report.txt")

    request = RunPersistenceRequest(
        runs_root=runs_root,
        run_id=run_id,
        task_description_hash="smoke-hash-001",
        task_description_redacted="Smoke test run for end-to-end validation",
        branch="main",
        base_branch="main",
        status="completed",
        reason_codes=(),
        pipeline_status="passed",
        pipeline_final_action=None,
        pipeline_has_blockers=False,
        pipeline_step_summary=(),
        pipeline_gate_summary=(),
        git_boundary_status="clean",
        command_plan_summary=(),
        execution_attempted=True,
        execution_results_summary=(
            {"operation": "smoke_noop", "exit_code": 0, "stdout": "", "stderr": ""},
        ),
        approval_summary="smoke run — no human approval required",
        artifact_hashes={"run.json": "smoke-fake-hash"},
        warnings=(),
        next_action="none",
        started_at="2026-07-15T00:00:00Z",
        finished_at="2026-07-15T00:00:01Z",
        clock_provider=lambda: "2026-07-15T00:00:01Z",
        report_path=report_path,
    )

    result = persist_run_record(request)
    if result.status != "persisted":
        raise RuntimeError(f"Failed to persist smoke run: {result.status} {result.reason_codes}")

    # Write the actual report content
    report_content = (
        "=== Ariadne Smoke Run Report ===\n\n"
        "Run ID: smoke-run-001\n"
        "Status: completed\n"
        "Pipeline: passed\n"
        "Git boundary: clean\n"
        "Execution attempted: yes\n\n"
        "This is a canonical smoke test run created by PR 0147A.\n"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    return run_id


# ---------------------------------------------------------------------------
# Route assertions
# ---------------------------------------------------------------------------


def _assert_health(base_url: str) -> None:
    """Check GET /health."""
    status, data = _http_get_json(f"{base_url}/health")
    assert status == 200, f"GET /health expected 200, got {status}"
    assert isinstance(data, dict), f"GET /health expected JSON dict, got {type(data)}"
    assert data.get("status") == "ok", f"GET /health expected status=ok, got {data.get('status')}"


def _assert_workspace(base_url: str) -> None:
    """Check GET /workspace returns HTML with all four zone selectors and hooks."""
    status, raw, ct = _http_get(f"{base_url}/workspace")
    assert status == 200, f"GET /workspace expected 200, got {status}"
    assert "text/html" in ct.lower(), f"GET /workspace expected text/html, got {ct}"
    body = raw.decode("utf-8", errors="replace")

    # Four zone selectors
    assert "artifact-workspace" in body, "workspace missing #artifact-workspace"
    assert "zone-timeline" in body, "workspace missing #zone-timeline"
    assert "zone-canvas" in body, "workspace missing #zone-canvas"
    assert "zone-gates-proofs" in body, "workspace missing #zone-gates-proofs"
    assert "zone-logs-captures" in body, "workspace missing #zone-logs-captures"

    # Detail rendering hooks (PR 0145)
    assert "detail-content" in body, "workspace missing detail-content hook"
    assert "detail-row" in body, "workspace missing detail-row hook"

    # Report viewer hooks (PR 0146)
    assert "report-viewer" in body, "workspace missing report-viewer hook"
    assert "report-provenance" in body, "workspace missing report-provenance hook"

    # Gates/proofs hooks (PR 0147)
    assert "gates-content" in body, "workspace missing gates-content hook"

    # Logs/captures hooks (PR 0147)
    assert "logs-content" in body, "workspace missing logs-content hook"


def _assert_runs_index(base_url: str, run_id: str) -> None:
    """Check GET /runs returns version-1 envelope with our run."""
    status, data = _http_get_json(f"{base_url}/runs")
    assert status == 200, f"GET /runs expected 200, got {status}"
    assert data.get("ev_contract_version") == "1", (
        f"GET /runs expected ev_contract_version=1, got {data.get('ev_contract_version')}"
    )
    assert data.get("ok") is True, f"GET /runs expected ok=true, got {data.get('ok')}"
    runs = data.get("runs", [])
    assert any(r.get("run_id") == run_id for r in runs), (
        f"GET /runs did not contain run_id={run_id}"
    )


def _assert_run_detail(base_url: str, run_id: str) -> None:
    """Check GET /runs/<run_id> returns version-1 detail envelope."""
    encoded = urllib.request.quote(run_id, safe="")
    status, data = _http_get_json(f"{base_url}/runs/{encoded}")
    assert status == 200, f"GET /runs/{run_id} expected 200, got {status}"
    assert data.get("ev_contract_version") == "1", (
        f"GET /runs/{run_id} expected ev_contract_version=1, got {data.get('ev_contract_version')}"
    )
    assert data.get("ok") is True, f"GET /runs/{run_id} expected ok=true, got {data.get('ok')}"
    summary = data.get("summary", {})
    assert summary.get("run_id") == run_id, (
        f"GET /runs/{run_id} summary.run_id expected {run_id}, got {summary.get('run_id')}"
    )
    detail = data.get("detail", {})
    manifest_files = detail.get("manifest_files", [])
    assert "run.json" in manifest_files, (
        f"GET /runs/{run_id} manifest_files missing run.json: {manifest_files}"
    )
    assert "run-report.txt" in manifest_files, (
        f"GET /runs/{run_id} manifest_files missing run-report.txt: {manifest_files}"
    )
    evidence_paths = detail.get("evidence_paths", [])
    assert len(evidence_paths) >= 2, (
        f"GET /runs/{run_id} expected >=2 evidence_paths, got {len(evidence_paths)}"
    )


def _assert_run_report(base_url: str, run_id: str) -> None:
    """Check GET /runs/<run_id>/report returns version-1 report envelope."""
    encoded = urllib.request.quote(run_id, safe="")
    status, data = _http_get_json(f"{base_url}/runs/{encoded}/report")
    assert status == 200, f"GET /runs/{run_id}/report expected 200, got {status}"
    assert data.get("ev_contract_version") == "1", (
        f"GET /runs/{run_id}/report expected ev_contract_version=1, got {data.get('ev_contract_version')}"
    )
    assert data.get("ok") is True, (
        f"GET /runs/{run_id}/report expected ok=true, got {data.get('ok')}"
    )
    assert data.get("run_id") == run_id, (
        f"GET /runs/{run_id}/report run_id expected {run_id}, got {data.get('run_id')}"
    )
    assert data.get("report_exists") is True, (
        f"GET /runs/{run_id}/report expected report_exists=true, got {data.get('report_exists')}"
    )
    assert data.get("truncated") is False, (
        f"GET /runs/{run_id}/report expected truncated=false, got {data.get('truncated')}"
    )
    assert data.get("provenance") is not None, "GET report missing provenance"
    content = data.get("content", "")
    assert len(content) > 0, "GET report content is empty"
    assert "Smoke Run Report" in content, "GET report content missing expected text"


def _assert_security_operator_mode(base_url: str, runs_root: str, run_id: str) -> None:
    """Verify operator mode security: browser runs_root query cannot override server-owned root."""
    encoded = urllib.request.quote(run_id, safe="")
    # Try to override runs_root via query string — should be ignored
    status, data = _http_get_json(f"{base_url}/runs?runs_root=/tmp/nonexistent-should-be-ignored")
    assert status == 200, f"GET /runs?runs_root=... expected 200, got {status}"
    assert data.get("ok") is True, (
        "GET /runs with override runs_root should still return ok (query ignored)"
    )
    runs = data.get("runs", [])
    assert any(r.get("run_id") == run_id for r in runs), (
        "Operator mode runs_root query override must not replace server-owned root"
    )

    # Try detail with runs_root override
    status, data = _http_get_json(
        f"{base_url}/runs/{encoded}?runs_root=/tmp/nonexistent-should-be-ignored"
    )
    assert status == 200, f"GET /runs/{run_id}?runs_root=... expected 200, got {status}"
    assert data.get("ok") is True, "Run detail with override runs_root should still work"


# ---------------------------------------------------------------------------
# Main smoke
# ---------------------------------------------------------------------------


def main() -> int:
    """Run the end-to-end smoke. Returns 0 on success, 1 on any failure."""
    temp_dir = tempfile.mkdtemp(prefix="ariadne-smoke-")
    runs_root = os.path.join(temp_dir, "runs")

    server_process = None
    try:
        # 1. Create canonical persisted run
        print("smoke: creating canonical run...")
        run_id = _create_smoke_run(runs_root)

        # 2. Find a free port
        port = _find_free_port()
        base_url = f"http://127.0.0.1:{port}"
        print(f"smoke: using port {port}")

        # 3. Launch the operator as subprocess
        env = os.environ.copy()
        # Set PYTHONPATH for the subprocess
        pythonpath_parts = [
            os.path.join(os.getcwd(), "services", "runner", "src"),
            os.path.join(os.getcwd(), "services", "task_intake", "src"),
        ]
        existing = env.get("PYTHONPATH", "")
        if existing:
            pythonpath_parts.insert(0, existing)
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

        # Determine the Python executable — prefer .venv/bin/python if available
        python_exe = sys.executable
        venv_python = os.path.join(os.getcwd(), ".venv", "bin", "python")
        if os.path.isfile(venv_python):
            python_exe = venv_python

        cmd = [
            python_exe,
            "-m",
            "task_intake.local_operator",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--runs-root", runs_root,
        ]
        print(f"smoke: launching operator: {' '.join(cmd)}")
        server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        # 4. Wait for readiness
        print("smoke: waiting for /health...")
        if not _wait_for_health(base_url, timeout=5.0):
            stdout, stderr = server_process.communicate(timeout=1)
            print(f"smoke: FAILED — operator did not become ready")
            print(f"stdout: {stdout.decode('utf-8', errors='replace')[:500]}")
            print(f"stderr: {stderr.decode('utf-8', errors='replace')[:500]}")
            return 1
        print("smoke: operator ready")

        # 5. Run all route assertions
        print("smoke: checking GET /health...")
        _assert_health(base_url)

        print("smoke: checking GET /workspace...")
        _assert_workspace(base_url)

        print("smoke: checking GET /runs...")
        _assert_runs_index(base_url, run_id)

        print("smoke: checking GET /runs/<run_id>...")
        _assert_run_detail(base_url, run_id)

        print("smoke: checking GET /runs/<run_id>/report...")
        _assert_run_report(base_url, run_id)

        print("smoke: checking operator mode security...")
        _assert_security_operator_mode(base_url, runs_root, run_id)

        print("smoke: ALL CHECKS PASSED")
        return 0

    except Exception as exc:
        print(f"smoke: FAILED — {exc}")
        return 1

    finally:
        # Always terminate the server
        if server_process is not None and server_process.poll() is None:
            print("smoke: shutting down operator...")
            server_process.send_signal(signal.SIGTERM)
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("smoke: operator did not stop — sending SIGKILL")
                server_process.kill()
                server_process.wait(timeout=2)

        # Remove temp directory
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            print("smoke: temp directory removed")


if __name__ == "__main__":
    sys.exit(main())

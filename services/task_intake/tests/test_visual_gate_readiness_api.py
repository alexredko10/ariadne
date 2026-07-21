"""PR 0151 — Visual Gate Readiness API route tests."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from runner.visual_gate_result import create_visual_gate_result
from runner.run_profile import create_run_profile

FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "tests", "fixtures"
)


def _request(method, path, runs_root_override=None):
    """Send a request to the ASGI app with optional runs_root."""
    from task_intake.server import app
    import asyncio

    async def _do():
        results = []
        async def _send(msg):
            if msg["type"] == "http.response.start":
                results.append(("start", msg["status"]))
            elif msg["type"] == "http.response.body":
                results.append(("body", msg.get("body", b"")))
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
        }
        await app(scope, None, _send, runs_root=runs_root_override or "unused")
        return results
    return asyncio.run(_do())


def _load_fixture(name: str) -> str:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _clock() -> str:
    return "2026-07-01T00:00:00Z"


def _make_env(tmp_dir: str, run_id: str = "readiness-api-001",
              with_mmd: bool = True, with_profile: bool = True,
              with_vg: bool = True) -> tuple[str, str]:
    """Create a test environment. Returns (runs_root, run_dir)."""
    runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)

    # Create run.json
    run_json = {
        "schema_version": "1", "run_id": run_id, "status": "completed",
    }
    with open(os.path.join(run_dir, "run.json"), "w") as f:
        json.dump(run_json, f)

    if with_mmd:
        content = _load_fixture("requirement-diagram.mmd")
        with open(os.path.join(run_dir, "req.mmd"), "w", encoding="utf-8") as f:
            f.write(content)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        if with_profile:
            profile_result = create_run_profile(
                runs_root=runs_root,
                run_id=run_id,
                presentation={"title": "API Test"},
                artifact_groups={"diagrams": {"key": "diagrams", "label": "Diagrams", "display_order": 1}},
                artifact_descriptors=[{
                    "key": "req_diagram",
                    "label": "Requirement Diagram",
                    "kind": "mermaid",
                    "evidence_role": "supporting",
                    "media_type": "text/vnd.mermaid",
                    "ref": "run-relative:req.mmd",
                    "sha256": content_hash,
                    "group_key": "diagrams",
                    "display_order": 1,
                    "required": True,
                }],
            )
            assert profile_result["ok"] is True

        if with_vg:
            vg_result = create_visual_gate_result(
                runs_root=runs_root,
                run_id=run_id,
                status="ready_needs_review",
                human_review_required=True,
                required_diagrams=[{
                    "diagram_id": "req",
                    "diagram_type": "requirement",
                    "descriptor_ref": "profile_descriptor_key:req_diagram",
                    "required": True,
                }],
                clock_provider=_clock,
            )
            assert vg_result["ok"] is True

    return runs_root, run_dir


class TestReadinessApi:
    """PR 0151: Visual Gate Readiness API route tests."""

    def test_ready_state_returns_200_with_true(self):
        """Ready state returns 200 with is_ready=True."""
        with tempfile.TemporaryDirectory(prefix="rdns-api-") as td:
            runs_root, _ = _make_env(td)
            path = "/runs/readiness-api-001/visual-gate-readiness"
            results = _request("GET", path, runs_root_override=runs_root)
            body = json.loads(results[-1][1].decode("utf-8"))
            assert results[0][1] == 200
            assert body.get("ok") is True
            assert body.get("is_ready") is True
            assert body.get("status") == "ready"
            assert body.get("reason_codes") == []

    def test_not_ready_returns_codes(self):
        """Not ready state returns reason_codes."""
        with tempfile.TemporaryDirectory(prefix="rdns-api-") as td:
            runs_root, run_dir = _make_env(td)
            mmd_path = os.path.join(run_dir, "req.mmd")
            if os.path.isfile(mmd_path):
                os.remove(mmd_path)
            path = "/runs/readiness-api-001/visual-gate-readiness"
            results = _request("GET", path, runs_root_override=runs_root)
            body = json.loads(results[-1][1].decode("utf-8"))
            assert body.get("is_ready") is False
            assert body.get("status") == "not_ready"
            assert len(body.get("reason_codes", [])) > 0

    def test_no_gate_state(self):
        """No gate state returns status=no_gate."""
        with tempfile.TemporaryDirectory(prefix="rdns-api-") as td:
            runs_root, _ = _make_env(td, with_vg=False)
            path = "/runs/readiness-api-001/visual-gate-readiness"
            results = _request("GET", path, runs_root_override=runs_root)
            body = json.loads(results[-1][1].decode("utf-8"))
            assert body.get("is_ready") is False
            assert body.get("status") == "no_gate"

    def test_unavailable_state(self):
        """Unavailable state returns ok=False."""
        with tempfile.TemporaryDirectory(prefix="rdns-api-") as td:
            runs_root, _ = _make_env(td, with_profile=False, with_vg=False)
            path = "/runs/readiness-api-001/visual-gate-readiness"
            results = _request("GET", path, runs_root_override=runs_root)
            body = json.loads(results[-1][1].decode("utf-8"))
            assert body.get("is_ready") is False

    def test_invalid_run_id_returns_ok_false(self):
        """Invalid run_id returns ok=False."""
        with tempfile.TemporaryDirectory(prefix="rdns-api-") as td:
            runs_root, _ = _make_env(td)
            path = "/runs/%00invalid/visual-gate-readiness"
            results = _request("GET", path, runs_root_override=runs_root)
            body = json.loads(results[-1][1].decode("utf-8"))
            assert body.get("ok") is False

    def test_non_get_returns_404(self):
        """POST/PUT/PATCH/DELETE return 404."""
        with tempfile.TemporaryDirectory(prefix="rdns-api-") as td:
            runs_root, _ = _make_env(td)
            path = "/runs/readiness-api-001/visual-gate-readiness"
            for method in ["POST", "PUT", "PATCH", "DELETE"]:
                results = _request(method, path, runs_root_override=runs_root)
                body = json.loads(results[-1][1].decode("utf-8"))
                assert body.get("ok") is False or body.get("error") is not None

    def test_missing_runs_root(self):
        """Missing runs_root returns ok=False."""
        results = _request("GET", "/runs/nonexistent/visual-gate-readiness")
        body = json.loads(results[-1][1].decode("utf-8"))
        assert body.get("ok") is False or body.get("is_ready") is False

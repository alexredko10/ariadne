"""Tests for the runner adapter registry / dispatcher."""

from __future__ import annotations

import inspect
import json

import pytest

from runner.adapter_registry import (
    dispatch_execution,
    get_supported_adapters,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _noop_request(**overrides: object) -> dict:
    """Build a minimal valid no-op execution request."""
    base = {
        "execution_request_id": "er-001",
        "run_id": "run-001",
        "task_intake_id": "task_a1b2c3d4e5f6",
        "context_preview_id": "ctxpreview_a1b2c3d4e5f6",
        "requested_adapter": "noop-v1",
        "execution_mode": "dry_run",
        "inputs": {"note": "test"},
        "constraints": ["no_git_mutation"],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Dispatch no-op
# ---------------------------------------------------------------------------


class TestDispatchNoop:
    def test_dispatch_noop_returns_completed(self):
        result = dispatch_execution(_noop_request())
        assert result["status"] == "completed"
        assert result["adapter"] == "noop-v1"

    def test_dispatch_noop_result_passed_through(self):
        direct = _noop_request()
        result = dispatch_execution(direct)
        assert result["execution_result_id"] == "er-001-result"
        assert result["execution_request_id"] == "er-001"

    def test_dispatch_result_json_serializable(self):
        result = dispatch_execution(_noop_request())
        dumped = json.dumps(result, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == result

    def test_dispatch_deterministic(self):
        req = _noop_request()
        r1 = dispatch_execution(req)
        r2 = dispatch_execution(req)
        assert r1 == r2

    def test_noop_adapter_blocked_passes_through(self):
        """Approval-pending request passes through to adapter, returns blocked."""
        req = _noop_request(
            approval={"required": True, "approved": False},
        )
        result = dispatch_execution(req)
        assert result["status"] == "blocked"


# ---------------------------------------------------------------------------
# Unsupported adapter
# ---------------------------------------------------------------------------


class TestUnsupportedAdapter:
    def test_unsupported_adapter_returns_failed(self):
        result = dispatch_execution(_noop_request(requested_adapter="unknown-v1"))
        assert result["status"] == "failed"
        errors = result.get("errors", [])
        assert any("unsupported_adapter" in e.get("code", "") for e in errors)

    def test_unsupported_adapter_error_message_includes_supported(self):
        result = dispatch_execution(_noop_request(requested_adapter="unknown-v1"))
        errors = result.get("errors", [])
        assert any("noop" in e.get("message", "").lower() for e in errors)

    def test_empty_adapter_returns_failed(self):
        result = dispatch_execution(_noop_request(requested_adapter=""))
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# Invalid request
# ---------------------------------------------------------------------------


class TestInvalidRequest:
    def test_non_dict_request_returns_failed(self):
        result = dispatch_execution("not a dict")
        assert result["status"] == "failed"
        errors = result.get("errors", [])
        assert any("invalid_request" in e.get("code", "") for e in errors)

    def test_missing_execution_request_id_still_dispatches(self):
        """Missing fields are validated by the adapter, not the dispatcher."""
        result = dispatch_execution(_noop_request(execution_request_id=""))
        # The dispatcher should pass through to the noop adapter
        assert result["status"] == "failed"  # noop adapter returns failed
        assert result["adapter"] == "noop-v1"  # dispatched to noop


# ---------------------------------------------------------------------------
# get_supported_adapters
# ---------------------------------------------------------------------------


class TestGetSupportedAdapters:
    def test_returns_noop(self):
        adapters = get_supported_adapters()
        assert "noop" in adapters

    def test_noop_spec(self):
        adapters = get_supported_adapters()
        noop = adapters["noop"]
        assert noop["version"] == "v1"
        assert "dry_run" in noop["modes"]
        assert "preview" in noop["modes"]
        assert "execute" not in noop["modes"]

    def test_deterministic(self):
        assert get_supported_adapters() == get_supported_adapters()

    def test_json_serializable(self):
        adapters = get_supported_adapters()
        dumped = json.dumps(adapters, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == adapters

    def test_includes_docker_agent(self):
        adapters = get_supported_adapters()
        assert "docker-agent" in adapters

    def test_docker_agent_spec(self):
        adapters = get_supported_adapters()
        da = adapters["docker-agent"]
        assert da["version"] == "v1"
        assert "execute" in da["modes"]
        assert "dry_run" in da["modes"]
        assert "preview" in da["modes"]


# ---------------------------------------------------------------------------
# Side effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_forbidden_imports(self):
        import re
        source = inspect.getsource(dispatch_execution)
        src = inspect.getsource(dispatch_execution)
        src += inspect.getsource(get_supported_adapters)
        # Remove docstrings and string literals
        clean = re.sub(r'""".*?"""', "", src, flags=re.DOTALL)
        clean = re.sub(r"'''.*?'''", "", clean, flags=re.DOTALL)
        clean = re.sub(r"'[^']*'", "", clean)
        clean = re.sub(r'"[^"]*"', "", clean)
        assert "subprocess" not in clean
        assert "popen" not in clean.lower()
        assert "docker" not in clean.lower()
        assert "requests" not in clean.lower()
        assert "httpx" not in clean.lower()
        assert "urllib" not in clean.lower()
        assert "socket" not in clean.lower()
        assert "redis" not in clean.lower()
        assert "sqlite" not in clean.lower()
        assert "importlib" not in clean
        assert "pkg_resources" not in clean
        assert "entry_points" not in clean

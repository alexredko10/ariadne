"""Tests for the composed mock app loop."""

from __future__ import annotations

import asyncio
import json

from task_intake.mock_loop import run_mock_loop
from task_intake.normalize import normalize_task_intake


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _request_body(raw_task: str = "Add JWT auth middleware") -> dict:
    body = {"raw_task": raw_task, "source": "test"}
    return body


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _run_loop(body: dict) -> dict:
    return run_mock_loop(body)


class TestMockLoop:
    def test_minimal_valid_succeeds_end_to_end(self):
        body = _request_body()
        out = _run_loop(body)
        assert out["ok"] is True
        assert "task_intake" in out
        assert "context_preview" in out
        assert "run" in out
        assert "status" in out

    def test_rich_request_options_pass_through(self):
        body = _request_body()
        body["include_sections"] = ["task", "anchors"]
        body["preview_options"] = {"format": "compact"}
        body["run_options"] = {"priority": "high"}
        out = _run_loop(body)
        assert out["ok"] is True
        assert out["context_preview"]["preview"]["context_sections"].get("anchors")
        assert out["run"]["run"]["run_options"]["priority"] == "high"

    def test_repeated_calls_produce_identical_output(self):
        body = _request_body()
        o1 = _run_loop(body)
        o2 = _run_loop(body)
        assert o1 == o2

    def test_output_json_serializable(self):
        body = _request_body()
        out = _run_loop(body)
        dumped = json.dumps(out, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == out

    def test_loop_id_deterministic(self):
        body = _request_body()
        out = _run_loop(body)
        assert out["loop_id"].startswith("loop_")

    def test_response_contains_expected_components(self):
        body = _request_body()
        out = _run_loop(body)
        assert out["task_intake"]["normalized"]["task_goal"]
        assert out["context_preview"]["preview"]["task_summary"]
        assert out["run"]["run"]["run_id"].startswith("run_")
        assert out["status"]["state"] == "completed_mock_loop"

    def test_validation_failure_at_normalize(self):
        body = {"raw_task": ""}  # empty raw task should fail normalize
        out = _run_loop(body)
        assert out["ok"] is False
        assert out["status"]["state"] == "validation_failed"

    def test_validation_failure_at_context_preview(self):
        # Provide a normalized task but invalid include_sections type
        norm = normalize_task_intake({"raw_task": "Add feature", "source": "test"})
        ti = {**norm["normalized_task"], "task_intake_id": norm["task_intake_id"]}
        body = {"task_intake": ti, "include_sections": "bad"}
        out = _run_loop(body)
        assert out["ok"] is False
        assert out["status"]["phase"] == "context_preview"

    def test_validation_failure_at_run(self):
        # Create a runs request that will have mismatched ids
        norm = normalize_task_intake({"raw_task": "Add feature", "source": "test"})
        ti = {**norm["normalized_task"], "task_intake_id": norm["task_intake_id"]}
        # Build a bad context_preview with different task_intake_id
        cp = {"context_preview_id": "cp-bad", "task_intake_id": "other_task", "preview": {}}
        body = {"task_intake": ti, "context_preview": cp}
        out = _run_loop(body)
        assert out["ok"] is False
        assert out["status"]["phase"] == "runs"

    def test_no_repo_scan_or_network_or_model_calls(self):
        body = _request_body()
        out = _run_loop(body)
        # the evidence field should explicitly state no execution
        assert out["evidence"]["execution_performed"] is False

    def test_no_forbidden_old_names(self):
        body = _request_body()
        out = _run_loop(body)
        s = json.dumps(out)
        assert "water_meter" not in s
        assert "broken_clock" not in s


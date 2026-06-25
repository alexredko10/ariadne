"""Tests for the context preview mock endpoint."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from task_intake.server import app
from task_intake.normalize import normalize_task_intake


# ---------------------------------------------------------------------------
# ASGI test harness
# ---------------------------------------------------------------------------


async def _asgi_request(
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, dict]:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "http_version": "1.1",
        "scheme": "http",
        "client": ("127.0.0.1", 8001),
        "server": ("127.0.0.1", 8001),
    }

    response_status = 500
    response_body = b""

    async def receive() -> dict:
        if body is not None:
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict) -> None:
        nonlocal response_status, response_body
        if event["type"] == "http.response.start":
            response_status = event["status"]
        elif event["type"] == "http.response.body":
            response_body += event.get("body", b"")

    await app(scope, receive, send)

    try:
        parsed = json.loads(response_body) if response_body else {}
    except json.JSONDecodeError:
        parsed = {"raw": response_body.decode("utf-8", errors="replace")}

    return response_status, parsed


def _request(
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, dict]:
    return asyncio.run(_asgi_request(method, path, body=body))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalized_task(raw_task: str = "Add JWT auth middleware") -> dict:
    """Generate a normalized task intake dict using the normalize endpoint."""
    result = normalize_task_intake({"raw_task": raw_task, "source": "test"})
    return result["normalized_task"]


def _request_body(task_goal: str | None = None, **overrides: object) -> dict:
    ti = _normalized_task(task_goal or "Add JWT auth middleware")
    body = {"task_intake": ti}
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# Context preview endpoint
# ---------------------------------------------------------------------------


class TestContextPreviewEndpoint:
    def test_valid_request_returns_200(self):
        body = json.dumps(_request_body()).encode("utf-8")
        status, _ = _request("POST", "/context/preview", body=body)
        assert status == 200

    def test_valid_request_has_ok_true(self):
        body = json.dumps(_request_body()).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        assert data["ok"] is True

    def test_valid_request_has_preview_id(self):
        body = json.dumps(_request_body()).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        assert data["context_preview_id"].startswith("ctxpreview_")

    def test_valid_request_has_preview(self):
        body = json.dumps(_request_body()).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        assert "preview" in data
        assert "task_summary" in data["preview"]

    def test_valid_request_has_next_runs(self):
        body = json.dumps(_request_body()).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        assert data["next"] == "/runs"

    def test_deterministic(self):
        body = json.dumps(_request_body()).encode("utf-8")
        _, r1 = _request("POST", "/context/preview", body=body)
        _, r2 = _request("POST", "/context/preview", body=body)
        assert r1 == r2

    def test_json_serializable(self):
        body = json.dumps(_request_body()).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        dumped = json.dumps(data, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == data


class TestRequestFields:
    def test_task_intake_goal_preserved(self):
        goal = "Implement JWT auth"
        body = json.dumps(_request_body(task_goal=goal)).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        assert data["preview"]["task_summary"] == goal

    def test_task_intake_id_preserved(self):
        goal = "Add login endpoint"
        norm = normalize_task_intake({"raw_task": goal, "source": "test"})
        body_dict = {
            "task_intake": {**norm["normalized_task"],
                           "task_intake_id": norm["task_intake_id"]},
        }
        body = json.dumps(body_dict).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        assert data["task_intake_id"] == norm["task_intake_id"]

    def test_task_intake_id_from_normalize(self):
        """Verify that the preview can receive intake from normalize."""
        raw_task = "Implement JWT auth"
        normalize_result = normalize_task_intake({"raw_task": raw_task})
        ti = {**normalize_result["normalized_task"],
              "task_intake_id": normalize_result["task_intake_id"]}
        body = json.dumps({"task_intake": ti}).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        assert data["task_intake_id"] == normalize_result["task_intake_id"]
        assert data["preview"]["task_summary"] == raw_task

    def test_include_sections_controls_output(self):
        sections = ["task", "anchors"]
        body = json.dumps(_request_body(include_sections=sections)).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        preview_sections = data["preview"]["context_sections"]
        assert "task" in preview_sections
        assert "anchors" in preview_sections
        assert "scope" not in preview_sections


class TestValidation:
    def test_missing_task_intake_returns_400(self):
        body = json.dumps({"source": "cli"}).encode("utf-8")
        status, data = _request("POST", "/context/preview", body=body)
        assert status == 400
        assert data["ok"] is False

    def test_non_dict_task_intake_returns_400(self):
        body = json.dumps({"task_intake": "bad"}).encode("utf-8")
        status, _ = _request("POST", "/context/preview", body=body)
        assert status == 400

    def test_missing_task_goal_returns_400(self):
        body = json.dumps({"task_intake": {"source": "test"}}).encode("utf-8")
        status, _ = _request("POST", "/context/preview", body=body)
        assert status == 400

    def test_non_list_include_sections_returns_400(self):
        body = json.dumps(_request_body(include_sections="bad")).encode("utf-8")
        status, _ = _request("POST", "/context/preview", body=body)
        assert status == 400

    def test_non_dict_preview_options_returns_400(self):
        body = json.dumps(_request_body(preview_options="bad")).encode("utf-8")
        status, _ = _request("POST", "/context/preview", body=body)
        assert status == 400


class TestPreviewContent:
    def test_preview_has_task_summary(self):
        body = json.dumps(_request_body()).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        assert isinstance(data["preview"]["task_summary"], str)
        assert len(data["preview"]["task_summary"]) > 0

    def test_preview_has_context_sections(self):
        body = json.dumps(_request_body()).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        sections = data["preview"]["context_sections"]
        assert "task" in sections
        assert "scope" in sections
        assert "risks" in sections

    def test_preview_has_context_pack_summary(self):
        body = json.dumps(_request_body()).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        summary = data["preview"]["context_pack_preview_summary"]
        assert summary["schema_version"] == "0.1"
        assert summary["field_count"] > 0

    def test_preview_anchors_section(self):
        sections = ["anchors"]
        body = json.dumps(_request_body(include_sections=sections)).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        anchors = data["preview"]["context_sections"]["anchors"]
        assert "relevant" in anchors
        assert len(anchors["relevant"]) > 0

    def test_preview_inferred_mode_preserved(self):
        body = json.dumps(_request_body(task_goal="Fix bug")).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        assert data["preview"]["inferred_mode"] is not None
        assert data["preview"]["inferred_domains"] is not None

    def test_missing_inputs_identified(self):
        """Task with no constraints should produce a missing_inputs entry."""
        ti_dict = _normalized_task("Add basic route")
        # Remove constraints from the copy
        del ti_dict["constraints"]
        body_dict = {"task_intake": ti_dict}
        body = json.dumps(body_dict).encode("utf-8")
        _, data = _request("POST", "/context/preview", body=body)
        assert "constraints" in data["preview"]["missing_inputs"]


class TestSafety:
    def test_no_forbidden_source_strings(self):
        import inspect
        from task_intake.context_preview import generate_context_preview
        source = inspect.getsource(generate_context_preview)
        assert "subprocess" not in source
        assert "requests" not in source.lower()
        assert "docker" not in source.lower()
        assert "git " not in source.lower()
        assert "open(" not in source

    def test_no_old_names(self):
        import inspect
        from task_intake.context_preview import generate_context_preview
        source = inspect.getsource(generate_context_preview)
        assert "water_meter" not in source
        assert "broken_clock" not in source.lower()
        assert ".grace" not in source.lower()

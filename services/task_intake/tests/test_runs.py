"""Tests for the mock runs endpoint."""

from __future__ import annotations

import asyncio
import json

from task_intake.server import app
from task_intake.normalize import normalize_task_intake
from task_intake.context_preview import generate_context_preview


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


def _make_request_body(
    raw_task: str = "Add JWT auth",
    include_cp_id: bool = True,
) -> dict:
    """Build a valid mock run request body from scratch."""
    # Normalize task
    norm = normalize_task_intake({"raw_task": raw_task, "source": "test"})
    ti = {**norm["normalized_task"], "task_intake_id": norm["task_intake_id"]}

    # Preview context
    preview_body = {"task_intake": ti}
    _, preview_result = _request("POST", "/context/preview", body=json.dumps(preview_body).encode("utf-8"))
    cp = {
        "context_preview_id": preview_result["context_preview_id"] if include_cp_id else "",
        "task_intake_id": preview_result["task_intake_id"],
        "preview": preview_result.get("preview", {}),
    }

    return {"task_intake": ti, "context_preview": cp}


# ---------------------------------------------------------------------------
# Runs endpoint
# ---------------------------------------------------------------------------


class TestRunsEndpoint:
    def test_valid_request_returns_200(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        status, _ = _request("POST", "/runs", body=body)
        assert status == 200

    def test_valid_request_has_ok_true(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert data["ok"] is True

    def test_valid_request_has_run_id(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert data["run_id"].startswith("run_")

    def test_valid_request_has_status(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert "status" in data
        assert data["status"]["state"] == "created"

    def test_valid_request_has_next(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert data["next"].startswith("/runs/")

    def test_deterministic(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, r1 = _request("POST", "/runs", body=body)
        _, r2 = _request("POST", "/runs", body=body)
        assert r1 == r2

    def test_json_serializable(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        dumped = json.dumps(data, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == data


class TestStatusObject:
    def test_status_state_is_created(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert data["status"]["state"] == "created"

    def test_status_is_not_terminal(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert data["status"]["is_terminal"] is False

    def test_status_progress_is_zero(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert data["status"]["progress"] == 0

    def test_status_message_indicates_mock(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert "mock" in data["status"]["message"].lower()

    def test_status_has_updated_by(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert data["status"]["updated_by"] == "task-intake-api"


class TestRunObject:
    def test_run_has_task_intake_id(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert "task_intake_id" in data["run"]

    def test_run_has_context_preview_id(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert "context_preview_id" in data["run"]

    def test_run_has_execution_plan_placeholder(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert "execution_plan_placeholder" in data["run"]

    def test_run_evidence_indicates_mock(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        ev = data["run"]["evidence"]
        assert ev["mock_run"] is True
        assert ev["execution_performed"] is False
        assert ev["runner_adapter_required"] is True

    def test_run_options_preserved(self):
        body_dict = _make_request_body()
        body_dict["run_options"] = {"priority": "high", "target_agent": "reviewer"}
        body = json.dumps(body_dict).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert data["run"]["run_options"]["priority"] == "high"

    def test_run_options_default_empty(self):
        body = json.dumps(_make_request_body()).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        assert data["run"]["run_options"] == {}


class TestValidation:
    def test_missing_task_intake_returns_400(self):
        body = json.dumps({"context_preview": {}}).encode("utf-8")
        status, data = _request("POST", "/runs", body=body)
        assert status == 400
        assert data["ok"] is False

    def test_missing_context_preview_returns_400(self):
        body = json.dumps({"task_intake": {"task_goal": "x"}}).encode("utf-8")
        status, data = _request("POST", "/runs", body=body)
        assert status == 400
        assert data["ok"] is False

    def test_missing_task_goal_returns_400(self):
        body = json.dumps({
            "task_intake": {"source": "test"},
            "context_preview": {"context_preview_id": "cp-1"},
        }).encode("utf-8")
        status, _ = _request("POST", "/runs", body=body)
        assert status == 400

    def test_non_dict_task_intake_returns_400(self):
        body = json.dumps({
            "task_intake": "bad",
            "context_preview": {"context_preview_id": "cp-1"},
        }).encode("utf-8")
        status, _ = _request("POST", "/runs", body=body)
        assert status == 400

    def test_missing_context_preview_id_returns_400(self):
        body = json.dumps({
            "task_intake": {"task_goal": "x"},
            "context_preview": {},
        }).encode("utf-8")
        status, _ = _request("POST", "/runs", body=body)
        assert status == 400

    def test_mismatched_ids_returns_400(self):
        """Create bodies where ti_id differs between task_intake and context_preview."""
        body_dict = _make_request_body()
        body_dict["task_intake"]["task_intake_id"] = "task_one"
        body_dict["context_preview"]["task_intake_id"] = "task_two"
        body = json.dumps(body_dict).encode("utf-8")
        status, data = _request("POST", "/runs", body=body)
        assert status == 400
        assert "mismatch" in str(data).lower()

    def test_non_dict_run_options_returns_400(self):
        body_dict = _make_request_body()
        body_dict["run_options"] = "bad"
        body = json.dumps(body_dict).encode("utf-8")
        status, data = _request("POST", "/runs", body=body)
        assert status == 400
        assert data["ok"] is False

    def test_validation_failed_status_shape(self):
        body = json.dumps({"task_intake": "bad"}).encode("utf-8")
        _, data = _request("POST", "/runs", body=body)
        status_obj = data["status"]
        assert status_obj["state"] == "validation_failed"
        assert status_obj["is_terminal"] is True
        assert status_obj["progress"] == 0


class TestSafety:
    def test_no_forbidden_source_strings(self):
        import inspect
        from task_intake.runs import create_mock_run
        source = inspect.getsource(create_mock_run)
        assert "subprocess" not in source
        assert "requests" not in source.lower()
        assert "docker" not in source.lower()
        assert "git " not in source.lower()
        assert "open(" not in source

    def test_no_old_names(self):
        import inspect
        from task_intake.runs import create_mock_run
        source = inspect.getsource(create_mock_run)
        assert "water_meter" not in source
        assert "broken_clock" not in source.lower()
        assert ".grace" not in source.lower()

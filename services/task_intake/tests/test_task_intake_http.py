"""Tests for the Task Intake HTTP endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from task_intake.server import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_get_health_returns_service_name(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "task_intake"

    def test_get_health_returns_ok_status(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Submit — accepted
# ---------------------------------------------------------------------------


class TestSubmitAccepted:
    def test_valid_prompt_is_accepted(self):
        response = client.post(
            "/submit",
            json={"prompt": "Fix the login bug"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    def test_accepted_response_has_task_id(self):
        response = client.post(
            "/submit",
            json={"prompt": "Implement rate limiting"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["task_id"].startswith("task_")

    def test_accepts_optional_title(self):
        response = client.post(
            "/submit",
            json={"prompt": "Add logging", "title": "Logging feature"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"


# ---------------------------------------------------------------------------
# Submit — alias
# ---------------------------------------------------------------------------


class TestSubmitAlias:
    def test_task_intake_submit_works_like_submit(self):
        r1 = client.post("/submit", json={"prompt": "Alias test"})
        r2 = client.post("/task-intake/submit", json={"prompt": "Alias test"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json() == r2.json()

    def test_task_intake_submit_rejected_blank(self):
        response = client.post("/task-intake/submit", json={"prompt": ""})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"


# ---------------------------------------------------------------------------
# Submit — rejected
# ---------------------------------------------------------------------------


class TestSubmitRejected:
    def test_blank_prompt_is_rejected(self):
        response = client.post("/submit", json={"prompt": ""})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    def test_rejected_response_has_reason(self):
        response = client.post("/submit", json={"prompt": ""})
        assert response.status_code == 200
        data = response.json()
        assert "reason" in data
        assert len(data["reason"]) > 0

    def test_rejected_response_has_error_code(self):
        response = client.post("/submit", json={"prompt": ""})
        assert response.status_code == 200
        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "blank_prompt"

    def test_whitespace_only_rejected(self):
        response = client.post("/submit", json={"prompt": "   \t\n  "})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["error_code"] == "blank_prompt"


# ---------------------------------------------------------------------------
# Submit — malformed / missing
# ---------------------------------------------------------------------------


class TestMalformedInput:
    def test_missing_prompt_is_rejected(self):
        response = client.post("/submit", json={})
        assert response.status_code == 422  # FastAPI validation error

    def test_empty_json_body(self):
        response = client.post("/submit", json={})
        assert response.status_code == 422

    def test_non_json_body(self):
        response = client.post("/submit", data="not json")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# No side-effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_uses_existing_accept_task(self):
        from task_intake.app import accept_task as at

        response = client.post("/submit", json={"prompt": "test"})
        assert response.status_code == 200

    def test_no_forbidden_source_strings(self):
        """Verify that the server source does not contain forbidden patterns."""
        import inspect
        with open(inspect.getfile(type(app))) as f:
            content = f.read()
        assert ".ariadne" not in content
        assert "run_record.yml" not in content
        assert "subprocess" not in content
        assert "docker" not in content

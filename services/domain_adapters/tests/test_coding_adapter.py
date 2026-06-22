"""Tests for the Coding Domain Adapter."""

from __future__ import annotations

import json

import pytest

from domain_adapters.coding import (
    ALLOWED_WRITE_PATHS,
    APPLY_MECHANISM,
    EXECUTION_ENVIRONMENT,
    FORBIDDEN_WRITE_PATHS,
    HUMAN_APPROVAL_POLICY,
    RISKS,
    ROLLBACK_MECHANISM,
    STOP_CONDITIONS,
    VALIDATION_COMMANDS,
    CodingAdapterError,
    CodingDomainAdapter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter() -> CodingDomainAdapter:
    return CodingDomainAdapter()


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


class TestCodingDomainAdapterIdentity:
    def test_adapter_id_deterministic(self):
        assert CodingDomainAdapter.adapter_id == "coding-v1"

    def test_domain(self):
        assert CodingDomainAdapter.domain == "coding"

    def test_description_non_empty(self):
        assert len(CodingDomainAdapter.description) > 0


# ---------------------------------------------------------------------------
# describe
# ---------------------------------------------------------------------------


class TestDescribe:
    def test_returns_dict(self, adapter: CodingDomainAdapter):
        result = adapter.describe()
        assert isinstance(result, dict)

    def test_contains_expected_keys(self, adapter: CodingDomainAdapter):
        result = adapter.describe()
        assert result["adapter_id"] == "coding-v1"
        assert result["domain"] == "coding"
        assert result["description"] == CodingDomainAdapter.description

    def test_repeated_calls_equal(self, adapter: CodingDomainAdapter):
        assert adapter.describe() == adapter.describe()


# ---------------------------------------------------------------------------
# describe_capabilities
# ---------------------------------------------------------------------------


class TestDescribeCapabilities:
    def test_returns_list(self, adapter: CodingDomainAdapter):
        caps = adapter.describe_capabilities()
        assert isinstance(caps, list)

    def test_each_capability_has_id_and_description(self, adapter: CodingDomainAdapter):
        caps = adapter.describe_capabilities()
        for cap in caps:
            assert "id" in cap
            assert "description" in cap

    def test_deterministic_order(self, adapter: CodingDomainAdapter):
        assert adapter.describe_capabilities() == adapter.describe_capabilities()

    def test_json_serializable(self, adapter: CodingDomainAdapter):
        caps = adapter.describe_capabilities()
        dumped = json.dumps(caps, sort_keys=True)
        assert isinstance(dumped, str)


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


class TestValidateRequest:
    def test_accepts_minimal_valid_request(self, adapter: CodingDomainAdapter):
        result = adapter.validate_request({
            "task_id": "coding-task-001",
            "intent": "inspect",
            "target_paths": ["services/example.py"],
        })
        assert result["valid"] is True
        assert result["task_id"] == "coding-task-001"

    def test_accepts_optional_constraints(self, adapter: CodingDomainAdapter):
        result = adapter.validate_request({
            "task_id": "coding-task-001",
            "intent": "plan",
            "target_paths": ["services/a.py", "services/b.py"],
            "constraints": ["no_git_mutation", "no_network"],
        })
        assert result["valid"] is True
        assert "no_git_mutation" in result["constraints"]

    def test_missing_task_id_raises(self, adapter: CodingDomainAdapter):
        with pytest.raises(CodingAdapterError) as exc:
            adapter.validate_request({
                "intent": "inspect",
                "target_paths": ["services/example.py"],
            })
        assert "task_id" in exc.value.subject
        assert exc.value.operation == "validate_request"

    def test_missing_intent_raises(self, adapter: CodingDomainAdapter):
        with pytest.raises(CodingAdapterError) as exc:
            adapter.validate_request({
                "task_id": "t1",
                "target_paths": ["services/example.py"],
            })
        assert "intent" in exc.value.subject

    def test_invalid_intent_raises(self, adapter: CodingDomainAdapter):
        with pytest.raises(CodingAdapterError) as exc:
            adapter.validate_request({
                "task_id": "t1",
                "intent": "unknown_intent",
                "target_paths": ["services/example.py"],
            })
        assert "intent" in exc.value.subject

    def test_missing_target_paths_raises(self, adapter: CodingDomainAdapter):
        with pytest.raises(CodingAdapterError) as exc:
            adapter.validate_request({
                "task_id": "t1",
                "intent": "inspect",
            })
        assert "target_paths" in exc.value.subject

    def test_empty_target_paths_raises(self, adapter: CodingDomainAdapter):
        with pytest.raises(CodingAdapterError):
            adapter.validate_request({
                "task_id": "t1",
                "intent": "inspect",
                "target_paths": [],
            })

    def test_target_paths_sorted(self, adapter: CodingDomainAdapter):
        result = adapter.validate_request({
            "task_id": "t1",
            "intent": "inspect",
            "target_paths": ["b.py", "a.py", "c.py"],
        })
        assert result["target_paths"] == ["a.py", "b.py", "c.py"]

    def test_constraints_sorted(self, adapter: CodingDomainAdapter):
        result = adapter.validate_request({
            "task_id": "t1",
            "intent": "inspect",
            "target_paths": ["x.py"],
            "constraints": ["z", "a", "m"],
        })
        assert result["constraints"] == ["a", "m", "z"]

    def test_error_includes_operation_subject_reason(self, adapter: CodingDomainAdapter):
        try:
            adapter.validate_request({
                "task_id": "t1",
                "intent": "bad",
                "target_paths": ["x.py"],
            })
        except CodingAdapterError as exc:
            assert exc.operation == "validate_request"
            assert exc.subject == "intent"
            assert isinstance(exc.reason, str)
            assert len(exc.reason) > 0


# ---------------------------------------------------------------------------
# plan_dry_run
# ---------------------------------------------------------------------------


class TestPlanDryRun:
    def test_returns_dict_with_expected_keys(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "coding-task-001",
            "intent": "inspect",
            "target_paths": ["services/example.py"],
        })
        for key in ("adapter_id", "domain", "task_id", "intent",
                     "target_paths", "constraints", "planned_actions",
                     "side_effects", "requires_human_approval",
                     "model_required", "validation_commands"):
            assert key in result, f"Missing key: {key}"

    def test_includes_adapter_id(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "t1", "intent": "inspect", "target_paths": ["x"],
        })
        assert result["adapter_id"] == "coding-v1"

    def test_includes_domain(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "t1", "intent": "inspect", "target_paths": ["x"],
        })
        assert result["domain"] == "coding"

    def test_side_effects_empty(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "t1", "intent": "inspect", "target_paths": ["x"],
        })
        assert result["side_effects"] == []

    def test_requires_human_approval_false(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "t1", "intent": "inspect", "target_paths": ["x"],
        })
        assert result["requires_human_approval"] is False

    def test_model_required_false(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "t1", "intent": "inspect", "target_paths": ["x"],
        })
        assert result["model_required"] is False

    def test_inspect_intent_actions(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "t1", "intent": "inspect", "target_paths": ["x"],
        })
        assert "read_target_files" in result["planned_actions"]
        assert "report_findings" in result["planned_actions"]

    def test_plan_intent_actions(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "t1", "intent": "plan", "target_paths": ["x"],
        })
        assert "propose_plan" in result["planned_actions"]

    def test_implement_intent_actions(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "t1", "intent": "implement", "target_paths": ["x"],
        })
        assert "apply_changes" in result["planned_actions"]

    def test_review_intent_actions(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "t1", "intent": "review", "target_paths": ["x"],
        })
        assert "report_review" in result["planned_actions"]

    def test_json_serializable(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "t1", "intent": "inspect", "target_paths": ["x"],
        })
        dumped = json.dumps(result, sort_keys=True)
        assert isinstance(dumped, str)

    def test_deterministic(self, adapter: CodingDomainAdapter):
        request = {"task_id": "t1", "intent": "inspect", "target_paths": ["a", "b"]}
        assert adapter.plan_dry_run(request) == adapter.plan_dry_run(request)

    def test_validation_commands_included(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "t1", "intent": "inspect", "target_paths": ["x"],
        })
        assert "python -m pytest -q" in result["validation_commands"]


# ---------------------------------------------------------------------------
# Policy data
# ---------------------------------------------------------------------------


class TestPolicyData:
    def test_allowed_write_paths(self):
        assert "services/**" in ALLOWED_WRITE_PATHS

    def test_forbidden_write_paths(self):
        assert ".git/**" in FORBIDDEN_WRITE_PATHS

    def test_validation_commands(self):
        assert "python -m pytest -q" in VALIDATION_COMMANDS

    def test_execution_environment(self):
        assert EXECUTION_ENVIRONMENT == "worktree"

    def test_apply_mechanism_git_based(self):
        assert APPLY_MECHANISM["git_based"] is True

    def test_apply_mechanism_human_approval(self):
        assert APPLY_MECHANISM["requires_human_apply"] is True

    def test_rollback_mechanism_git_based(self):
        assert ROLLBACK_MECHANISM["git_based"] is True

    def test_risks_non_empty(self):
        assert len(RISKS) > 0

    def test_stop_conditions_non_empty(self):
        assert len(STOP_CONDITIONS) > 0

    def test_human_approval_policy_non_empty(self):
        assert len(HUMAN_APPROVAL_POLICY) > 0


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------


class TestSafety:
    def test_no_forbidden_imports(self):
        import inspect
        source = inspect.getsource(CodingDomainAdapter.describe)
        assert "subprocess" not in source
        assert "open(" not in source
        assert "urllib" not in source.lower()
        assert "requests" not in source.lower()
        assert "docker" not in source.lower()
        assert "git " not in source.lower()

    def test_does_not_import_core_runtime(self, adapter: CodingDomainAdapter):
        import inspect
        source = inspect.getsource(CodingDomainAdapter.plan_dry_run)
        assert "core.runtime" not in source
        assert "core.runtime_substrate" not in source
        assert "core.runtime.transitions" not in source

    def test_no_absolute_paths_in_output(self, adapter: CodingDomainAdapter):
        result = adapter.plan_dry_run({
            "task_id": "t1", "intent": "inspect", "target_paths": ["services/x.py"],
        })
        dumped = json.dumps(result)
        assert "//" not in dumped
        assert "/etc" not in dumped
        assert "/Users" not in dumped

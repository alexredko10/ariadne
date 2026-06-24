"""Tests for the context pack input generator."""

from __future__ import annotations

import inspect
import json
import sys

import pytest

from conductor.context_pack_inputs import (
    build_context_pack_inputs,
    context_pack_inputs_error,
    normalize_context_pack_inputs,
    validate_context_pack_inputs,
)


# ---------------------------------------------------------------------------
# build_context_pack_inputs
# ---------------------------------------------------------------------------


class TestBuildContextPackInputs:
    def test_minimal_valid_input(self):
        result = build_context_pack_inputs(pr_id="0056", task_goal="Implement generator")
        assert result["pr_id"] == "0056"
        assert result["task_goal"] == "Implement generator"
        assert result["schema_version"] == "0.1"

    def test_minimal_has_default_freshness(self):
        result = build_context_pack_inputs(pr_id="0056", task_goal="Test")
        assert result["context_freshness"]["status"] == "fresh"
        assert result["context_freshness"]["last_verified_hook"] == "none"

    def test_full_input_preserves_all_fields(self):
        risks = [{"id": "r1", "description": "Risk 1"}]
        result = build_context_pack_inputs(
            pr_id="0056",
            feature_id="f-001",
            task_goal="Full test",
            source_contracts=["state-first", "run-record"],
            relevant_anchors=["anchor-1"],
            allowed_paths=["services/**", "tests/**"],
            forbidden_paths=[".git/**"],
            cache_key_refs=[{"namespace": "context", "artifact_kind": "context_pack"}],
            prior_pr_refs=[{"pr_id": "0055"}],
            qa_evidence_refs=["ev-001"],
            known_risks=risks,
            manual_checks_required=["Check tests"],
            invalidation_inputs={"base_sha": "abc123"},
            requested_context_sections=["purpose", "domain"],
            output_preferences={"format": "compact"},
            created_from_agent="steward",
            created_from_hook="before_plan",
            created_from_template="context-steward.before_plan.v1",
        )
        assert result["pr_id"] == "0056"
        assert result["feature_id"] == "f-001"
        assert result["task_goal"] == "Full test"
        assert "services/**" in result["allowed_paths"]
        assert ".git/**" in result["forbidden_paths"]
        assert result["cache_key_refs"][0]["namespace"] == "context"
        assert result["known_risks"][0]["id"] == "r1"
        assert result["invalidation_inputs"]["base_sha"] == "abc123"
        assert "purpose" in result["requested_context_sections"]
        assert result["output_preferences"]["format"] == "compact"
        assert result["created_from"]["agent"] == "steward"
        assert result["created_from"]["hook"] == "before_plan"

    def test_empty_pr_id_raises(self):
        with pytest.raises(ValueError, match="pr_id"):
            build_context_pack_inputs(pr_id="", task_goal="Test")

    def test_empty_task_goal_raises(self):
        with pytest.raises(ValueError, match="task_goal"):
            build_context_pack_inputs(pr_id="0056", task_goal="")

    def test_absolute_path_in_allowed_paths_raises(self):
        with pytest.raises(ValueError, match="allowed_paths"):
            build_context_pack_inputs(
                pr_id="0056",
                task_goal="Test",
                allowed_paths=["/etc/passwd", "services/**"],
            )

    def test_absolute_path_in_forbidden_paths_raises(self):
        with pytest.raises(ValueError, match="forbidden_paths"):
            build_context_pack_inputs(
                pr_id="0056",
                task_goal="Test",
                forbidden_paths=["/tmp"],
            )

    def test_shell_placeholder_in_path_raises(self):
        with pytest.raises(ValueError, match="allowed_paths"):
            build_context_pack_inputs(
                pr_id="0056",
                task_goal="Test",
                allowed_paths=["services/$(whoami)"],
            )

    def test_invalid_freshness_status_raises(self):
        with pytest.raises(ValueError, match="context_freshness"):
            build_context_pack_inputs(
                pr_id="0056",
                task_goal="Test",
                context_freshness_status="invalid_status",
            )

    def test_deterministic_repeated_calls_equal(self):
        r1 = build_context_pack_inputs(pr_id="0056", task_goal="Test")
        r2 = build_context_pack_inputs(pr_id="0056", task_goal="Test")
        assert r1 == r2

    def test_lists_are_sorted_in_output(self):
        result = build_context_pack_inputs(
            pr_id="0056",
            task_goal="Test",
            source_contracts=["run-record", "state-first", "apply-gate"],
        )
        assert result["source_contracts"] == [
            "apply-gate", "run-record", "state-first"
        ]

    def test_invalidation_inputs_keys_sorted(self):
        result = build_context_pack_inputs(
            pr_id="0056",
            task_goal="Test",
            invalidation_inputs={"z": "1", "a": "2", "m": "3"},
        )
        keys = list(result["invalidation_inputs"].keys())
        assert keys == ["a", "m", "z"]

    def test_json_serializable(self):
        result = build_context_pack_inputs(pr_id="0056", task_goal="Test")
        dumped = json.dumps(result, sort_keys=True)
        assert isinstance(dumped, str)

    def test_no_filesystem_io(self):
        """The function does not use open() or Path()."""
        source = inspect.getsource(build_context_pack_inputs)
        assert "open(" not in source
        assert "Path(" not in source

    def test_no_subprocess(self):
        source = inspect.getsource(build_context_pack_inputs)
        assert "subprocess" not in source

    def test_empty_lists_omitted(self):
        result = build_context_pack_inputs(pr_id="0056", task_goal="Test")
        assert "source_contracts" not in result

    def test_empty_strings_in_lists_omitted(self):
        result = build_context_pack_inputs(
            pr_id="0056",
            task_goal="Test",
            source_contracts=["a", "", "b", ""],
        )
        assert result["source_contracts"] == ["a", "b"]


# ---------------------------------------------------------------------------
# normalize_context_pack_inputs
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_already_normalized_unchanged(self):
        raw = {
            "pr_id": "0056",
            "task_goal": "Test",
            "context_freshness": {"status": "fresh", "last_verified_hook": "none"},
            "created_from": {"agent": "test", "hook": "after_plan_review"},
            "source_contracts": ["a", "b"],
        }
        norm = normalize_context_pack_inputs(raw)
        assert norm["source_contracts"] == ["a", "b"]

    def test_unsorted_lists_are_sorted(self):
        raw = {
            "pr_id": "0056",
            "task_goal": "Test",
            "allowed_paths": ["z", "a", "m"],
        }
        norm = normalize_context_pack_inputs(raw)
        assert norm["allowed_paths"] == ["a", "m", "z"]

    def test_empty_lists_removed(self):
        raw = {
            "pr_id": "0056",
            "task_goal": "Test",
            "source_contracts": [],
            "allowed_paths": ["a"],
        }
        norm = normalize_context_pack_inputs(raw)
        assert "source_contracts" not in norm
        assert norm["allowed_paths"] == ["a"]

    def test_none_values_removed(self):
        raw = {
            "pr_id": "0056",
            "task_goal": "Test",
            "feature_id": None,
        }
        norm = normalize_context_pack_inputs(raw)
        assert "feature_id" not in norm

    def test_created_from_various_hooks(self):
        raw = {
            "pr_id": "0056",
            "task_goal": "Test",
            "created_from": {"agent": "steward", "hook": "after_qa", "template": ""},
        }
        norm = normalize_context_pack_inputs(raw)
        assert norm["created_from"]["hook"] == "after_qa"
        assert "template" not in norm["created_from"]


# ---------------------------------------------------------------------------
# validate_context_pack_inputs
# ---------------------------------------------------------------------------


class TestValidate:
    def test_valid_dict_passes(self):
        data = {
            "pr_id": "0056",
            "task_goal": "Test",
        }
        validate_context_pack_inputs(data)

    def test_empty_pr_id_raises(self):
        with pytest.raises(ValueError, match="pr_id"):
            validate_context_pack_inputs({"pr_id": "", "task_goal": "Test"})

    def test_empty_task_goal_raises(self):
        with pytest.raises(ValueError, match="task_goal"):
            validate_context_pack_inputs({"pr_id": "0056", "task_goal": ""})

    def test_invalid_freshness_raises(self):
        with pytest.raises(ValueError, match="context_freshness"):
            validate_context_pack_inputs({
                "pr_id": "0056",
                "task_goal": "Test",
                "context_freshness": {"status": "bad"},
            })

    def test_invalid_cache_key_ref_raises(self):
        with pytest.raises(ValueError, match="cache_key_refs"):
            validate_context_pack_inputs({
                "pr_id": "0056",
                "task_goal": "Test",
                "cache_key_refs": [{"not_namespace": "x"}],
            })

    def test_cache_key_ref_not_dict_raises(self):
        with pytest.raises(ValueError, match="cache_key_refs"):
            validate_context_pack_inputs({
                "pr_id": "0056",
                "task_goal": "Test",
                "cache_key_refs": ["not_a_dict"],
            })


# ---------------------------------------------------------------------------
# context_pack_inputs_error
# ---------------------------------------------------------------------------


class TestErrorHelper:
    def test_includes_field(self):
        err = context_pack_inputs_error("pr_id", "must not be empty")
        assert "pr_id" in str(err)

    def test_includes_reason(self):
        err = context_pack_inputs_error("pr_id", "must not be empty")
        assert "must not be empty" in str(err)

    def test_is_value_error(self):
        err = context_pack_inputs_error("x", "y")
        assert isinstance(err, ValueError)

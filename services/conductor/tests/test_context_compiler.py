"""Tests for the minimal context compiler."""

from __future__ import annotations

import inspect
import json

import pytest

from conductor.context_compiler import (
    compile_context_pack,
    normalize_context_pack,
    validate_context_pack,
)
from conductor.context_pack_inputs import build_context_pack_inputs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_inputs(pr_id: str = "0057") -> dict:
    return build_context_pack_inputs(
        pr_id=pr_id,
        task_goal="Implement minimal compiler",
    )


def _full_inputs() -> dict:
    return build_context_pack_inputs(
        pr_id="0057",
        feature_id="f-001",
        task_goal="Full compiler test",
        source_contracts=["state-first", "run-record"],
        relevant_anchors=["anchor-auth", "anchor-db"],
        allowed_paths=["services/**", "tests/**"],
        forbidden_paths=[".git/**"],
        cache_key_refs=[{"namespace": "context", "artifact_kind": "context_pack"}],
        prior_pr_refs=[{"pr_id": "0056"}],
        qa_evidence_refs=["ev-001"],
        known_risks=[{"id": "r1", "description": "Test risk"}],
        manual_checks_required=["Check coverage"],
        invalidation_inputs={"base_sha": "abc123"},
        requested_context_sections=["purpose", "domain"],
        output_preferences={"format": "compact"},
        created_from_agent="steward",
    )


# ---------------------------------------------------------------------------
# compile_context_pack
# ---------------------------------------------------------------------------


class TestCompileContextPack:
    def test_minimal_valid_input(self):
        inputs = _minimal_inputs()
        result = compile_context_pack(
            context_pack_inputs=inputs,
            repo_id="ariadne",
            purpose_id="p-001",
            domain="coding",
            risk_level="medium",
            base_sha="abc123",
            index_version="0.23",
        )
        assert result["context_pack_id"] == "cp-0057-ariadne"
        assert result["repo_id"] == "ariadne"
        assert result["task"] == "Implement minimal compiler"
        assert result["purpose_id"] == "p-001"
        assert result["domain"] == "coding"
        assert result["risk_level"] == "medium"
        assert result["base_sha"] == "abc123"
        assert result["index_version"] == "0.23"

    def test_full_input_preserves_values(self):
        inputs = _full_inputs()
        result = compile_context_pack(
            context_pack_inputs=inputs,
            repo_id="ariadne",
            purpose_id="p-001",
            domain="coding",
            risk_level="high",
            base_sha="def456",
            index_version="0.23",
            task_subgraph=["services/**"],
            relevant_files=["src/main.py"],
            relevant_symbols=["main"],
            related_tests=["tests/test_main.py"],
            configs=["pyproject.toml"],
            invariants=["auth.token.rotation"],
            recent_changes=["Added compiler"],
            suggested_entry_points=["src/compiler.py"],
        )
        assert result["context_pack_id"] == "cp-0057-ariadne"
        assert "services/**" in result["task_subgraph"]
        assert "src/main.py" in result["relevant_files"]
        assert result["invariants"] is not None
        assert "auth.token.rotation" in result["invariants"]
        assert "Test risk" in result["risks"]
        assert "anchor-auth" in result["anchors"]

    def test_invariants_from_source_contracts(self):
        inputs = _minimal_inputs()
        # Add source_contracts to inputs by rebuilding
        inputs = build_context_pack_inputs(
            pr_id="0057",
            task_goal="Test",
            source_contracts=["contract-a", "contract-b"],
        )
        result = compile_context_pack(
            context_pack_inputs=inputs,
            repo_id="r",
            purpose_id="p",
            domain="d",
            risk_level="l",
            base_sha="s",
            index_version="iv",
        )
        assert "contract-a" in result["invariants"]
        assert "contract-b" in result["invariants"]

    def test_risks_from_known_risks(self):
        inputs = build_context_pack_inputs(
            pr_id="0057",
            task_goal="Test",
            known_risks=[{"id": "r1", "description": "Risk one"}],
        )
        result = compile_context_pack(
            context_pack_inputs=inputs,
            repo_id="r", purpose_id="p", domain="d",
            risk_level="l", base_sha="s", index_version="iv",
        )
        assert "Risk one" in result["risks"]

    def test_anchors_from_relevant_anchors(self):
        inputs = build_context_pack_inputs(
            pr_id="0057",
            task_goal="Test",
            relevant_anchors=["anchor-auth"],
        )
        result = compile_context_pack(
            context_pack_inputs=inputs,
            repo_id="r", purpose_id="p", domain="d",
            risk_level="l", base_sha="s", index_version="iv",
        )
        assert "anchor-auth" in result["anchors"]

    def test_context_pack_id_deterministic(self):
        inputs = _minimal_inputs()
        r1 = compile_context_pack(
            context_pack_inputs=inputs, repo_id="r", purpose_id="p",
            domain="d", risk_level="l", base_sha="s", index_version="iv",
        )
        r2 = compile_context_pack(
            context_pack_inputs=inputs, repo_id="r", purpose_id="p",
            domain="d", risk_level="l", base_sha="s", index_version="iv",
        )
        assert r1["context_pack_id"] == r2["context_pack_id"] == "cp-0057-r"

    def test_deterministic_repeated_calls_equal(self):
        inputs = _minimal_inputs()
        r1 = compile_context_pack(
            context_pack_inputs=inputs, repo_id="r", purpose_id="p",
            domain="d", risk_level="l", base_sha="s", index_version="iv",
        )
        r2 = compile_context_pack(
            context_pack_inputs=inputs, repo_id="r", purpose_id="p",
            domain="d", risk_level="l", base_sha="s", index_version="iv",
        )
        assert r1 == r2

    def test_lists_sorted_in_output(self):
        inputs = build_context_pack_inputs(
            pr_id="0057",
            task_goal="Test",
            source_contracts=["z", "a"],
        )
        result = compile_context_pack(
            context_pack_inputs=inputs, repo_id="r", purpose_id="p",
            domain="d", risk_level="l", base_sha="s", index_version="iv",
        )
        assert result["invariants"] == ["a", "z"]

    def test_stable_prompt_blocks_empty(self):
        inputs = _minimal_inputs()
        result = compile_context_pack(
            context_pack_inputs=inputs, repo_id="r", purpose_id="p",
            domain="d", risk_level="l", base_sha="s", index_version="iv",
        )
        # stable_prompt_blocks is omitted by normalize because it's empty
        assert "stable_prompt_blocks" not in result or result["stable_prompt_blocks"] == []

    def test_state_first_context_none(self):
        inputs = _minimal_inputs()
        result = compile_context_pack(
            context_pack_inputs=inputs, repo_id="r", purpose_id="p",
            domain="d", risk_level="l", base_sha="s", index_version="iv",
        )
        # state_first_context is omitted by normalize because it's None
        assert "state_first_context" not in result or result["state_first_context"] is None

    def test_json_serializable(self):
        inputs = _minimal_inputs()
        result = compile_context_pack(
            context_pack_inputs=inputs, repo_id="r", purpose_id="p",
            domain="d", risk_level="l", base_sha="s", index_version="iv",
        )
        dumped = json.dumps(result, sort_keys=True)
        assert isinstance(dumped, str)

    def test_no_filesystem_io(self):
        source = inspect.getsource(compile_context_pack)
        assert "open(" not in source
        assert "Path(" not in source

    def test_no_subprocess(self):
        source = inspect.getsource(compile_context_pack)
        assert "subprocess" not in source

    def test_required_repo_id_empty_raises(self):
        with pytest.raises(ValueError, match="repo_id"):
            compile_context_pack(
                context_pack_inputs=_minimal_inputs(),
                repo_id="", purpose_id="p", domain="d",
                risk_level="l", base_sha="s", index_version="iv",
            )

    def test_required_purpose_id_empty_raises(self):
        with pytest.raises(ValueError, match="purpose_id"):
            compile_context_pack(
                context_pack_inputs=_minimal_inputs(),
                repo_id="r", purpose_id="", domain="d",
                risk_level="l", base_sha="s", index_version="iv",
            )

    def test_required_domain_empty_raises(self):
        with pytest.raises(ValueError, match="domain"):
            compile_context_pack(
                context_pack_inputs=_minimal_inputs(),
                repo_id="r", purpose_id="p", domain="",
                risk_level="l", base_sha="s", index_version="iv",
            )

    def test_required_risk_level_empty_raises(self):
        with pytest.raises(ValueError, match="risk_level"):
            compile_context_pack(
                context_pack_inputs=_minimal_inputs(),
                repo_id="r", purpose_id="p", domain="d",
                risk_level="", base_sha="s", index_version="iv",
            )

    def test_required_base_sha_empty_raises(self):
        with pytest.raises(ValueError, match="base_sha"):
            compile_context_pack(
                context_pack_inputs=_minimal_inputs(),
                repo_id="r", purpose_id="p", domain="d",
                risk_level="l", base_sha="", index_version="iv",
            )

    def test_required_index_version_empty_raises(self):
        with pytest.raises(ValueError, match="index_version"):
            compile_context_pack(
                context_pack_inputs=_minimal_inputs(),
                repo_id="r", purpose_id="p", domain="d",
                risk_level="l", base_sha="s", index_version="",
            )

    def test_invalid_context_pack_inputs_not_dict_raises(self):
        with pytest.raises(ValueError, match="context_pack_inputs"):
            compile_context_pack(
                context_pack_inputs="not_a_dict",
                repo_id="r", purpose_id="p", domain="d",
                risk_level="l", base_sha="s", index_version="iv",
            )

    def test_context_pack_inputs_without_pr_id_raises(self):
        with pytest.raises(ValueError, match="pr_id"):
            compile_context_pack(
                context_pack_inputs={"task_goal": "x"},
                repo_id="r", purpose_id="p", domain="d",
                risk_level="l", base_sha="s", index_version="iv",
            )

    def test_output_keys_match_schema(self):
        inputs = _minimal_inputs()
        result = compile_context_pack(
            context_pack_inputs=inputs,
            repo_id="ariadne", purpose_id="p", domain="coding",
            risk_level="medium", base_sha="abc", index_version="0.23",
        )
        expected_keys = {
            "context_pack_id", "repo_id", "task", "purpose_id", "domain",
            "risk_level", "base_sha", "index_version",
        }
        assert expected_keys.issubset(result.keys())

    def test_merge_explicit_invariants_with_contracts(self):
        inputs = build_context_pack_inputs(
            pr_id="0057",
            task_goal="Test",
            source_contracts=["contract-a"],
        )
        result = compile_context_pack(
            context_pack_inputs=inputs,
            repo_id="r", purpose_id="p", domain="d",
            risk_level="l", base_sha="s", index_version="iv",
            invariants=["explicit-inv"],
        )
        assert "contract-a" in result["invariants"]
        assert "explicit-inv" in result["invariants"]

    def test_does_not_mutate_caller_input(self):
        inputs = _minimal_inputs()
        original_pr_id = inputs["pr_id"]
        compile_context_pack(
            context_pack_inputs=inputs,
            repo_id="r", purpose_id="p", domain="d",
            risk_level="l", base_sha="s", index_version="iv",
        )
        assert inputs["pr_id"] == original_pr_id


# ---------------------------------------------------------------------------
# normalize_context_pack
# ---------------------------------------------------------------------------


class TestNormalizeContextPack:
    def test_empty_lists_removed(self):
        raw = {
            "context_pack_id": "cp-1",
            "repo_id": "r",
            "task": "t",
            "purpose_id": "p",
            "domain": "d",
            "risk_level": "l",
            "base_sha": "s",
            "index_version": "iv",
            "risks": [],
            "stable_prompt_blocks": [],
        }
        norm = normalize_context_pack(raw)
        assert "risks" not in norm
        assert "stable_prompt_blocks" not in norm

    def test_unsorted_lists_sorted(self):
        raw = {
            "context_pack_id": "cp-1",
            "repo_id": "r",
            "task": "t",
            "purpose_id": "p",
            "domain": "d",
            "risk_level": "l",
            "base_sha": "s",
            "index_version": "iv",
            "anchors": ["z", "a"],
        }
        norm = normalize_context_pack(raw)
        assert norm["anchors"] == ["a", "z"]


# ---------------------------------------------------------------------------
# validate_context_pack
# ---------------------------------------------------------------------------


class TestValidateContextPack:
    def test_valid_dict_passes(self):
        data = {
            "context_pack_id": "cp-1",
            "repo_id": "r",
            "task": "t",
            "purpose_id": "p",
            "domain": "d",
            "risk_level": "l",
            "base_sha": "s",
            "index_version": "iv",
        }
        validate_context_pack(data)

    def test_missing_context_pack_id_raises(self):
        with pytest.raises(ValueError, match="context_pack_id"):
            validate_context_pack({
                "repo_id": "r", "task": "t", "purpose_id": "p",
            })

    def test_missing_task_raises(self):
        with pytest.raises(ValueError, match="task"):
            validate_context_pack({
                "context_pack_id": "cp-1", "repo_id": "r",
                "purpose_id": "p",
            })

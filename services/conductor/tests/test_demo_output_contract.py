"""Demo output contract snapshot tests."""

from __future__ import annotations

import json
from pathlib import Path

from conductor.demo_flow import run_ariadne_e2e_demo

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
_FIXTURE_PATH = _FIXTURE_DIR / "ariadne_demo_output.json"


class TestDemoOutputContract:
    """Stable demo output contract."""

    def _get_current_output(self) -> dict:
        return run_ariadne_e2e_demo()

    def test_fixture_exists(self):
        assert _FIXTURE_PATH.exists()

    def test_output_matches_fixture(self):
        current = self._get_current_output()
        with open(_FIXTURE_PATH) as f:
            fixture = json.load(f)
        assert current == fixture, (
            "Demo output does not match fixture. "
            "If intentional, regenerate with:\n"
            f"  PYTHONPATH=services/core/src:services/conductor/src "
            f"python -m conductor ariadne-demo > {_FIXTURE_PATH}"
        )

    def test_output_deterministic(self):
        assert self._get_current_output() == self._get_current_output()

    def test_output_json_serializable(self):
        result = self._get_current_output()
        dumped = json.dumps(result, sort_keys=True)
        loaded = json.loads(dumped)
        assert loaded == result

    # --- Top-level keys ---

    def test_top_level_keys(self):
        result = self._get_current_output()
        assert result["demo_name"] == "Ariadne E2E Substrate Demo"
        assert isinstance(result["demo_version"], str)
        assert isinstance(result["pr_id"], str)
        assert isinstance(result["feature_id"], str)
        assert isinstance(result["task_goal"], str)
        assert isinstance(result["context_pack_inputs"], dict)
        assert isinstance(result["context_pack"], dict)
        assert isinstance(result["conductor_dry_run_summary"], dict)
        assert result["deterministic"] is True
        assert result["model_free"] is True
        assert result["repository_scan_free"] is True

    # --- context_pack_inputs ---

    def test_context_pack_inputs_keys(self):
        inputs = self._get_current_output()["context_pack_inputs"]
        assert isinstance(inputs["pr_id"], str)
        assert isinstance(inputs["task_goal"], str)
        assert len(inputs["source_contracts"]) > 0
        assert len(inputs["relevant_anchors"]) > 0
        assert len(inputs["allowed_paths"]) > 0
        assert len(inputs["forbidden_paths"]) > 0
        assert len(inputs["cache_key_refs"]) > 0
        assert len(inputs["known_risks"]) > 0
        assert isinstance(inputs["schema_version"], str)

    # --- context_pack ---

    def test_context_pack_keys(self):
        pack = self._get_current_output()["context_pack"]
        assert isinstance(pack["context_pack_id"], str)
        assert isinstance(pack["task"], str)
        assert isinstance(pack["domain"], str)
        assert isinstance(pack["risk_level"], str)
        assert len(pack["invariants"]) > 0
        assert len(pack["risks"]) > 0
        assert len(pack["anchors"]) > 0

    # --- conductor_dry_run_summary ---

    def test_conductor_dry_run_summary(self):
        summary = self._get_current_output()["conductor_dry_run_summary"]
        assert summary["dry_run"] == "conductor"
        assert isinstance(summary["run_id"], str)
        assert summary["run_status"] == "completed"
        assert summary["step_count"] > 0
        assert isinstance(summary["checkpoint_count"], int)
        assert summary["final_report_present"] is True

        cps = summary["context_pack_summary"]
        assert cps["present"] is True
        assert isinstance(cps["context_pack_id"], str)
        assert isinstance(cps["task"], str)
        assert isinstance(cps["domain"], str)
        assert isinstance(cps["risk_level"], str)
        assert cps["section_count"] > 0

    # --- Safety ---

    def test_no_absolute_paths(self):
        result = json.dumps(self._get_current_output(), sort_keys=True)
        # Check for typical absolute path patterns in value positions
        assert "//" not in result
        assert "C:" not in result
        # The doc pattern contains forward slashes in POSIX path patterns
        # like "docs/**" and "services/**" — those are portable, not absolute

    def test_no_shell_placeholders(self):
        result = json.dumps(self._get_current_output(), sort_keys=True)
        assert "$(" not in result

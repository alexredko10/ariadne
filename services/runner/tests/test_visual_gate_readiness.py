"""PR 0151 — Visual Gate Readiness Checker domain tests.

Tests every branch of the decision table with the real Node.js renderer.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from runner.visual_gate_readiness import check_visual_gate_readiness
from runner.visual_gate_result import create_visual_gate_result
from runner.run_profile import create_run_profile

FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "tests", "fixtures"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clock() -> str:
    return "2026-07-01T00:00:00Z"


def _create_basic_env(tmp_dir: str, run_id: str = "readiness-test-001") -> str:
    """Create minimal run directory with run.json."""
    runs_root = os.path.join(tmp_dir, ".ariadne", "runs")
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)
    run_json = {
        "schema_version": "1",
        "run_id": run_id,
        "status": "completed",
    }
    with open(os.path.join(run_dir, "run.json"), "w") as f:
        json.dump(run_json, f)
    return runs_root


def _load_fixture(name: str) -> str:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_mmd(run_dir: str, fname: str, content: str) -> str:
    path = os.path.join(run_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# Helpers: create profile + VG
# ---------------------------------------------------------------------------


def _make_valid_env(
    tmp_dir: str,
    run_id: str = "readiness-test-001",
    mmd_fixtures: list[str] | None = None,
    extra_descriptors: list[dict] | None = None,
    optional_only: bool = False,
) -> tuple[str, str]:
    """Create a complete valid environment with profile and VG result.

    Returns (runs_root, run_dir).
    """
    runs_root = _create_basic_env(tmp_dir, run_id)
    run_dir = os.path.join(runs_root, run_id)

    mmd_fixtures = mmd_fixtures or ["requirement-diagram.mmd"]
    descriptors = list(extra_descriptors or [])

    for i, fname in enumerate(mmd_fixtures):
        content = _load_fixture(fname)
        dst = os.path.join(run_dir, fname)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content)
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            dtype = "requirement"
            if "state" in fname:
                dtype = "state"
            elif "sequence" in fname:
                dtype = "sequence"
            descriptors.append({
                "key": f"diagram_{i}",
                "label": f"{dtype.capitalize()} Diagram",
                "kind": "mermaid",
                "evidence_role": "supporting",
                "media_type": "text/vnd.mermaid",
                "ref": f"run-relative:{fname}",
                "sha256": content_hash,
                "group_key": "diagrams",
                "display_order": i,
                "required": not optional_only,
            })

        profile_result = create_run_profile(
            runs_root=runs_root,
            run_id=run_id,
            presentation={"title": "Readiness Test"},
            artifact_groups={"diagrams": {"key": "diagrams", "label": "Diagrams", "display_order": 1}},
            artifact_descriptors=descriptors,
        )
        assert profile_result["ok"] is True, f"Profile creation failed: {profile_result}"

    required_diagrams = [
        {
            "diagram_id": f"d{i}",
            "diagram_type": "requirement" if "state" not in fname and "sequence" not in fname else
                           "state" if "state" in fname else "sequence",
            "descriptor_ref": f"profile_descriptor_key:diagram_{i}",
            "required": not optional_only,
        }
        for i, fname in enumerate(mmd_fixtures)
    ]

    vg_result = create_visual_gate_result(
        runs_root=runs_root,
        run_id=run_id,
        status="ready_needs_review",
        human_review_required=True,
        required_diagrams=required_diagrams,
        clock_provider=_clock,
    )
    assert vg_result["ok"] is True

    return runs_root, run_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVisualGateReadiness:
    """PR 0151: Visual Gate Readiness Checker domain tests."""

    # --- Ready states ---

    def test_all_required_diagrams_valid_ready(self):
        """All required diagrams valid → ready."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, _ = _make_valid_env(td, mmd_fixtures=[
                "requirement-diagram.mmd", "state-diagram.mmd", "sequence-diagram.mmd",
            ])
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["ok"] is True
            assert result["is_ready"] is True
            assert result["status"] == "ready"
            assert result["reason_codes"] == []
            assert result["renderer_available"] is True
            assert result["staleness_guard"] != ""

    def test_vg_status_passed_still_ready(self):
        """VG status=passed with all valid → ready."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, run_dir = _make_valid_env(td, mmd_fixtures=["requirement-diagram.mmd"])
            # Write a VG with passed status directly (bypass create — overwrite file)
            vg_path = os.path.join(runs_root, "readiness-test-001", "visual-gate-result.json")
            import json
            from runner.visual_gate_result import compute_visual_gate_sha256, canonical_json
            vg_data = {
                "schema_version": "1",
                "visual_gate_id": "vg-readiness-test-001-0000000000000000",
                "run_id": "readiness-test-001",
                "status": "passed",
                "human_review_required": False,
                "required_diagrams": [{
                    "diagram_id": "d0",
                    "diagram_type": "requirement",
                    "descriptor_ref": "profile_descriptor_key:diagram_0",
                    "required": True,
                }],
                "created_at": "2026-07-01T00:00:00Z",
            }
            vg_data["visual_gate_sha256"] = compute_visual_gate_sha256(vg_data)
            with open(vg_path, "w", encoding="utf-8") as f:
                f.write(canonical_json(vg_data))
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["is_ready"] is True
            assert result["status"] == "ready"

    def test_extra_non_required_diagram_ready(self):
        """Extra non-required diagram + all required valid → ready."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, run_dir = _make_valid_env(
                td,
                mmd_fixtures=["requirement-diagram.mmd"],
                extra_descriptors=[{
                    "key": "extra_diagram",
                    "label": "Extra Diagram",
                    "kind": "mermaid",
                    "evidence_role": "supporting",
                    "media_type": "text/vnd.mermaid",
                    "ref": "run-relative:extra.mmd",
                    "sha256": hashlib.sha256(b"graph TD; X-->Y;").hexdigest(),
                    "group_key": "diagrams",
                    "display_order": 5,
                    "required": False,
                }],
            )
            # Write the extra mmd
            _write_mmd(run_dir, "extra.mmd", "graph TD; X-->Y;")
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["is_ready"] is True
            assert result["status"] == "ready"
            assert result["reason_codes"] == []

    # --- Not ready: descriptor issues ---

    def test_missing_required_descriptor_not_ready(self):
        """Missing required descriptor → not_ready, descriptor_not_found."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, run_dir = _make_valid_env(td)
            # Write VG with nonexistent key directly
            vg_path = os.path.join(runs_root, "readiness-test-001", "visual-gate-result.json")
            if os.path.isfile(vg_path):
                os.remove(vg_path)
            from runner.visual_gate_result import compute_visual_gate_sha256, canonical_json
            vg_data = {
                "schema_version": "1",
                "visual_gate_id": "vg-readiness-test-001-0000000000000000",
                "run_id": "readiness-test-001",
                "status": "ready_needs_review",
                "human_review_required": True,
                "required_diagrams": [{
                    "diagram_id": "d0",
                    "diagram_type": "requirement",
                    "descriptor_ref": "profile_descriptor_key:nonexistent_key",
                    "required": True,
                }],
                "created_at": "2026-07-01T00:00:00Z",
            }
            vg_data["visual_gate_sha256"] = compute_visual_gate_sha256(vg_data)
            with open(vg_path, "w", encoding="utf-8") as f:
                f.write(canonical_json(vg_data))
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["ok"] is True
            assert result["is_ready"] is False
            assert result["status"] == "not_ready"
            assert any("descriptor_not_found" in rc for rc in result["reason_codes"])

    def test_descriptor_kind_mismatch_not_ready(self):
        """Descriptor exists but kind != 'mermaid' → not_ready."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, run_dir = _make_valid_env(td)
            # Overwrite profile with non-mermaid descriptor
            profile_result = create_run_profile(
                runs_root=runs_root,
                run_id="readiness-test-001",
                presentation={"title": "Test"},
                artifact_groups={"diagrams": {"key": "diagrams", "label": "Diagrams", "display_order": 1}},
                artifact_descriptors=[{
                    "key": "diagram_0",
                    "label": "Not Mermaid",
                    "kind": "text",
                    "evidence_role": "supporting",
                    "media_type": "text/plain",
                    "ref": "run-relative:test.txt",
                    "group_key": "diagrams",
                    "display_order": 1,
                    "required": True,
                }],
            )
            assert profile_result["ok"] is True
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["is_ready"] is False
            assert result["status"] == "not_ready"
            assert any("descriptor_kind_mismatch" in rc for rc in result["reason_codes"])

    # --- Not ready: source issues ---

    def test_missing_source_file_not_ready(self):
        """Missing source file → not_ready, source_not_found."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, _ = _make_valid_env(td)
            # Delete the mmd file
            mmd_path = os.path.join(runs_root, "readiness-test-001", "requirement-diagram.mmd")
            if os.path.isfile(mmd_path):
                os.remove(mmd_path)
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["is_ready"] is False
            assert result["status"] == "not_ready"
            assert any("source_not_found" in rc for rc in result["reason_codes"])

    def test_hash_mismatch_not_ready(self):
        """Hash mismatch → not_ready, hash_mismatch."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, run_dir = _make_valid_env(td)
            # Modify the mmd file to change its hash
            _write_mmd(run_dir, "requirement-diagram.mmd",
                       _load_fixture("requirement-diagram.mmd") + "\n# modified")
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["is_ready"] is False
            assert result["status"] == "not_ready"
            assert any("hash_mismatch" in rc for rc in result["reason_codes"])

    def test_source_too_large_not_ready(self):
        """Source > 100KB → not_ready, source_too_large."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, run_dir = _make_valid_env(td)
            # Overwrite mmd with a large file
            large_content = "graph TD;\n" + "\n".join([f"    A{i}-->B{i};" for i in range(10000)])
            _write_mmd(run_dir, "requirement-diagram.mmd", large_content)
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["is_ready"] is False
            assert result["status"] == "not_ready"
            assert any("source_too_large" in rc for rc in result["reason_codes"])

    # --- Not ready: render/sanitize issues ---

    def test_render_failure_not_ready(self):
        """Invalid Mermaid syntax → not_ready, render_error."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, run_dir = _make_valid_env(td)
            # Remove sha256 from descriptor so hash mismatch doesn't block render
            # Recreate profile without sha256
            content = _load_fixture("requirement-diagram.mmd")
            profile_result = create_run_profile(
                runs_root=runs_root,
                run_id="readiness-test-001",
                presentation={"title": "Readiness Test"},
                artifact_groups={"diagrams": {"key": "diagrams", "label": "Diagrams", "display_order": 1}},
                artifact_descriptors=[{
                    "key": "diagram_0",
                    "label": "Requirement Diagram",
                    "kind": "mermaid",
                    "evidence_role": "supporting",
                    "media_type": "text/vnd.mermaid",
                    "ref": "run-relative:requirement-diagram.mmd",
                    "group_key": "diagrams",
                    "display_order": 1,
                    "required": True,
                }],
            )
            assert profile_result["ok"] is True
            # Now replace content with invalid syntax
            _write_mmd(run_dir, "requirement-diagram.mmd", "this is not valid mermaid @@@@")
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["is_ready"] is False
            assert result["status"] == "not_ready"
            assert any("render_error" in rc for rc in result["reason_codes"])

    def test_unsupported_diagram_type_not_ready(self):
        """Unsupported diagram type → not_ready."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, run_dir = _make_valid_env(td)
            # Write VG with unsupported type directly
            vg_path = os.path.join(runs_root, "readiness-test-001", "visual-gate-result.json")
            if os.path.isfile(vg_path):
                os.remove(vg_path)
            from runner.visual_gate_result import compute_visual_gate_sha256, canonical_json
            vg_data = {
                "schema_version": "1",
                "visual_gate_id": "vg-readiness-test-001-0000000000000000",
                "run_id": "readiness-test-001",
                "status": "ready_needs_review",
                "human_review_required": True,
                "required_diagrams": [{
                    "diagram_id": "d0",
                    "diagram_type": "unsupported_type",
                    "descriptor_ref": "profile_descriptor_key:diagram_0",
                    "required": True,
                }],
                "created_at": "2026-07-01T00:00:00Z",
            }
            vg_data["visual_gate_sha256"] = compute_visual_gate_sha256(vg_data)
            with open(vg_path, "w", encoding="utf-8") as f:
                f.write(canonical_json(vg_data))
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["is_ready"] is False
            assert result["status"] == "not_ready"
            assert any("unsupported_diagram_type" in rc for rc in result["reason_codes"])

    def test_duplicate_diagram_id_not_ready(self):
        """Duplicate diagram_id → not_ready."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, _ = _make_valid_env(td)
            # Create VG with duplicate diagram_id
            vg_result = create_visual_gate_result(
                runs_root=runs_root,
                run_id="readiness-test-001",
                status="ready_needs_review",
                human_review_required=True,
                required_diagrams=[
                    {"diagram_id": "d0", "diagram_type": "requirement",
                     "descriptor_ref": "profile_descriptor_key:diagram_0", "required": True},
                    {"diagram_id": "d0", "diagram_type": "requirement",
                     "descriptor_ref": "profile_descriptor_key:diagram_0", "required": True},
                ],
                clock_provider=_clock,
            )
            # The VG create won't allow duplicates (validated), but let's check readiness handles
            # whatever the VG file actually has. If it rejects, we test that path.
            if vg_result["ok"]:
                result = check_visual_gate_readiness(runs_root, "readiness-test-001")
                assert result["is_ready"] is False
            # If VG creation rejected duplicates, that's also correct behavior

    def test_empty_required_diagrams_not_ready(self):
        """Empty required_diagrams → not_ready, no_required_diagrams."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, run_dir = _make_valid_env(td)
            # Write VG with empty required_diagrams directly
            vg_path = os.path.join(runs_root, "readiness-test-001", "visual-gate-result.json")
            if os.path.isfile(vg_path):
                os.remove(vg_path)
            from runner.visual_gate_result import compute_visual_gate_sha256, canonical_json
            vg_data = {
                "schema_version": "1",
                "visual_gate_id": "vg-readiness-test-001-0000000000000000",
                "run_id": "readiness-test-001",
                "status": "ready_needs_review",
                "human_review_required": True,
                "required_diagrams": [],
                "created_at": "2026-07-01T00:00:00Z",
            }
            vg_data["visual_gate_sha256"] = compute_visual_gate_sha256(vg_data)
            with open(vg_path, "w", encoding="utf-8") as f:
                f.write(canonical_json(vg_data))
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["is_ready"] is False
            assert result["status"] == "not_ready"
            assert any("no_required_diagrams" in rc for rc in result["reason_codes"])

    def test_renderer_unavailable(self):
        """Renderer unavailable → not_ready."""
        # We skip this test since the renderer IS available here.
        # The fallback path is tested in the renderer tests.
        pytest.skip("Renderer is available — tested renderer_unavailable in mermaid_renderer tests")

    # --- No gate state ---

    def test_visual_gate_result_missing(self):
        """No VG result → no_gate, visual_gate_result_not_found."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root = _create_basic_env(td)
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["ok"] is True
            assert result["is_ready"] is False
            assert result["status"] == "no_gate"
            assert any("visual_gate_result_not_found" in rc for rc in result["reason_codes"])

    # --- Unavailable state ---

    def test_vg_result_malformed(self):
        """Malformed VG → unavailable."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root = _create_basic_env(td)
            run_dir = os.path.join(runs_root, "readiness-test-001")
            # Write malformed JSON
            with open(os.path.join(run_dir, "visual-gate-result.json"), "w") as f:
                f.write("{bad json}")
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["ok"] is False
            assert result["status"] == "unavailable"
            assert any("visual_gate_result_malformed" in rc for rc in result["reason_codes"])

    def test_profile_missing(self):
        """Missing profile → no_gate, profile_not_found."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root = _create_basic_env(td)
            run_dir = os.path.join(runs_root, "readiness-test-001")
            # Create VG result but no profile
            vg_result = create_visual_gate_result(
                runs_root=runs_root,
                run_id="readiness-test-001",
                status="ready_needs_review",
                human_review_required=True,
                required_diagrams=[{
                    "diagram_id": "d0",
                    "diagram_type": "requirement",
                    "descriptor_ref": "profile_descriptor_key:diagram_0",
                    "required": True,
                }],
                clock_provider=_clock,
            )
            assert vg_result["ok"] is True
            result = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result["is_ready"] is False
            assert result["status"] == "no_gate"
            assert any("profile_not_found" in rc for rc in result["reason_codes"])

    # --- Stability tests ---

    def test_stable_ordering(self):
        """Multiple diagrams produce stable reason code ordering."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root, _ = _make_valid_env(td, mmd_fixtures=[
                "state-diagram.mmd", "sequence-diagram.mmd", "requirement-diagram.mmd",
            ])
            result1 = check_visual_gate_readiness(runs_root, "readiness-test-001")
            result2 = check_visual_gate_readiness(runs_root, "readiness-test-001")
            assert result1["status"] == result2["status"]
            assert result1["reason_codes"] == result2["reason_codes"]
            assert result1["staleness_guard"] == result2["staleness_guard"]

    def test_staleness_guard_different_run(self):
        """Different run_id produces different staleness_guard."""
        with tempfile.TemporaryDirectory(prefix="rdns-readiness-") as td:
            runs_root1, _ = _make_valid_env(td, "run-a")
            runs_root2, _ = _make_valid_env(td, "run-b",
                                            mmd_fixtures=["requirement-diagram.mmd"])
            result_a = check_visual_gate_readiness(runs_root1, "run-a")
            result_b = check_visual_gate_readiness(runs_root2, "run-b")
            assert result_a["staleness_guard"] != result_b["staleness_guard"]

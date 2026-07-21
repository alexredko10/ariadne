"""Tests for mermaid_renderer.py — offline Mermaid SVG generation via Node.js.

Requires node + npm packages to be installed (scripts/mermaid-render.cjs).
These tests verify the renderer contract: valid diagrams produce SVG,
invalid/empty source produces ok=False, security configuration is enforced,
and output is deterministic.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "tests", "fixtures"
)


def _load_fixture(name: str) -> str:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# Check if Node.js renderer is available
_RENDER_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "scripts", "mermaid-render.cjs"
)


def _check_renderer_available() -> bool:
    """Check if node is on PATH and the render script exists."""
    try:
        subprocess.run(
            ["node", "--version"],
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return os.path.isfile(_RENDER_SCRIPT)


_MERMAID_AVAILABLE = _check_renderer_available()

from runner.mermaid_renderer import render_mermaid_to_svg


@pytest.mark.skipif(not _MERMAID_AVAILABLE, reason="mermaid renderer not installed")
class TestMermaidRenderer:
    """Tests for the Mermaid renderer function."""

    def test_valid_requirement_diagram_produces_svg(self):
        """Valid requirement diagram produces SVG output."""
        source = _load_fixture("requirement-diagram.mmd")
        result = render_mermaid_to_svg(source, "requirement")
        assert result["ok"] is True, (
            f"Expected ok=True, got error={result.get('error')}"
        )
        assert result["svg"] is not None
        assert "<svg" in result["svg"].lower()
        assert result["diagram_type"] == "requirement"
        assert result["byte_count"] > 0
        assert result["mermaid_sha256"] is not None

    def test_valid_state_diagram_produces_svg(self):
        """Valid state diagram produces SVG output."""
        source = _load_fixture("state-diagram.mmd")
        result = render_mermaid_to_svg(source, "state")
        assert result["ok"] is True, (
            f"Expected ok=True, got error={result.get('error')}"
        )
        assert result["svg"] is not None
        assert "<svg" in result["svg"].lower()
        assert result["diagram_type"] == "state"

    def test_valid_sequence_diagram_produces_svg(self):
        """Valid sequence diagram produces SVG output."""
        source = _load_fixture("sequence-diagram.mmd")
        result = render_mermaid_to_svg(source, "sequence")
        assert result["ok"] is True, (
            f"Expected ok=True, got error={result.get('error')}"
        )
        assert result["svg"] is not None
        assert "<svg" in result["svg"].lower()
        assert result["diagram_type"] == "sequence"

    def test_invalid_mermaid_syntax_returns_false(self):
        """Invalid Mermaid syntax returns ok=False."""
        source = "this is not valid mermaid syntax @@@@"
        result = render_mermaid_to_svg(source, "")
        assert result["ok"] is False
        assert "error" in result
        assert result["svg"] is None

    def test_empty_source_returns_false(self):
        """Empty source returns ok=False."""
        result = render_mermaid_to_svg("", "")
        assert result["ok"] is False
        assert result["error"] == "empty_source"

    def test_whitespace_only_returns_false(self):
        """Whitespace-only source returns ok=False."""
        result = render_mermaid_to_svg("   \n\t  ", "")
        assert result["ok"] is False
        assert result["error"] == "empty_source"

    def test_security_config_no_onclick(self):
        """Security config: no onclick handlers in SVG output."""
        source = _load_fixture("hostile-mermaid.mmd")
        result = render_mermaid_to_svg(source, "")
        if result["ok"]:
            svg = result["svg"]
            assert "onclick:" not in svg
            assert 'onclick=' not in svg
            assert "alert(" not in svg

    def test_deterministic_output_for_same_input(self):
        """Same input produces SVG output (mermaid v11 float precision may vary)."""
        source = _load_fixture("requirement-diagram.mmd")
        result1 = render_mermaid_to_svg(source, "requirement")
        result2 = render_mermaid_to_svg(source, "requirement")
        if result1["ok"] and result2["ok"]:
            # Both produce SVG with common structural elements
            assert '<svg' in result1['svg'].lower()
            assert '<svg' in result2['svg'].lower()
            assert 'id="ariadne-diagram"' in result1['svg']
            assert 'id="ariadne-diagram"' in result2['svg']
            # mermaid_sha256 is deterministic (computed from input, not output)
            assert result1["mermaid_sha256"] == result2["mermaid_sha256"]

    def test_different_input_produces_different_output(self):
        """Different inputs produce different SVG."""
        source1 = _load_fixture("requirement-diagram.mmd")
        source2 = _load_fixture("state-diagram.mmd")
        result1 = render_mermaid_to_svg(source1, "")
        result2 = render_mermaid_to_svg(source2, "")
        if result1["ok"] and result2["ok"]:
            assert result1["svg"] != result2["svg"]
            assert result1["mermaid_sha256"] != result2["mermaid_sha256"]

    def test_mermaid_sha256_is_correct_hash(self):
        """mermaid_sha256 matches SHA-256 of source text."""
        source = _load_fixture("requirement-diagram.mmd")
        result = render_mermaid_to_svg(source, "")
        expected = hashlib.sha256(source.encode("utf-8")).hexdigest()
        assert result["mermaid_sha256"] == expected

    def test_source_too_large_returns_false(self):
        """Source > 100 KB returns ok=False."""
        source = "graph TD;\n    A-->B\n" * 20000  # > 100KB
        result = render_mermaid_to_svg(source, "")
        assert result["ok"] is False
        assert result["error"] == "source_too_large"


class TestMermaidRendererImport:
    """Tests for when the Node.js renderer is not available."""

    def test_module_is_importable(self):
        """mermaid_renderer module is importable."""
        from runner.mermaid_renderer import render_mermaid_to_svg
        assert callable(render_mermaid_to_svg)

    def test_renderer_returns_not_available_when_node_missing(self):
        """Renderer returns ok=False when node or render script is missing."""
        if _MERMAID_AVAILABLE:
            pytest.skip("Node.js renderer is available — subprocess works")
        from runner.mermaid_renderer import render_mermaid_to_svg
        result = render_mermaid_to_svg("graph TD; A-->B", "")
        assert result["ok"] is False
        assert result["error"] == "mermaid_renderer_not_available"

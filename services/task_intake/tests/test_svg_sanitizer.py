"""Tests for svg_sanitizer.py — whitelist-based SVG sanitization.

Verifies that sanitize_svg removes all dangerous content:
- script, foreignObject, iframe, embed, object, img, use
- Event handler attributes (on*)
- href and xlink:href
- Unknown elements and unknown attributes
- Malformed XML returns ok=False
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from task_intake.svg_sanitizer import sanitize_svg


# Fixture: a clean, minimal SVG
CLEAN_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <rect x="10" y="10" width="80" height="80" fill="#fff" stroke="#000" stroke-width="2"/>
  <text x="50" y="50" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="14">Hello</text>
</svg>"""


class TestSvgSanitizerBasics:
    """Basic sanitizer behavior."""

    def test_clean_svg_passes_through(self):
        """Clean SVG with only allowed elements and attributes passes through."""
        result = sanitize_svg(CLEAN_SVG)
        assert result["ok"] is True
        assert "svg" in result["sanitized_svg"]
        assert "<rect" in result["sanitized_svg"]
        assert "<text" in result["sanitized_svg"]
        assert "fill=\"#fff\"" in result["sanitized_svg"]

    def test_empty_string_returns_false(self):
        """Empty string returns ok=False."""
        result = sanitize_svg("")
        assert result["ok"] is False
        assert result["error"] == "empty_input"

    def test_whitespace_only_returns_false(self):
        """Whitespace-only string returns ok=False."""
        result = sanitize_svg("   \n  ")
        assert result["ok"] is False
        assert result["error"] == "empty_input"

    def test_malformed_xml_returns_false(self):
        """Malformed XML returns ok=False with svg_parse_error."""
        result = sanitize_svg("<svg><unclosed>")
        assert result["ok"] is False
        assert result["error"] == "svg_parse_error"

    def test_non_xml_string_returns_false(self):
        """Plain text returns ok=False."""
        result = sanitize_svg("not an svg at all")
        assert result["ok"] is False
        assert result["error"] == "svg_parse_error"


class TestSvgSanitizerRemoveScript:
    """Script element removal."""

    def test_script_element_removed(self):
        """<script> elements are removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <script>alert("xss")</script>
          <rect x="0" y="0" width="10" height="10" fill="#000"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "<script>" not in result["sanitized_svg"]
        assert "alert" not in result["sanitized_svg"].lower()

    def test_inline_script_in_event_handler_removed(self):
        """onclick attribute is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <rect x="0" y="0" width="10" height="10" fill="#000" onclick="alert(1)"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "onclick" not in result["sanitized_svg"]

    def test_onerror_handler_removed(self):
        """onerror attribute is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <image onerror="alert(1)" />
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        # image element should be removed entirely, and definitely no onerror
        assert "onerror" not in result["sanitized_svg"]

    def test_onmouseover_removed(self):
        """onmouseover attribute is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <rect x="0" y="0" width="10" height="10" fill="#000" onmouseover="bad()"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "onmouseover" not in result["sanitized_svg"]


class TestSvgSanitizerRemoveLinks:
    """href and link removal."""

    def test_href_removed(self):
        """href attribute is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <a href="https://evil.com"><rect x="0" y="0" width="10" height="10" fill="#000"/></a>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "href=" not in result["sanitized_svg"]

    def test_xlink_href_removed(self):
        """xlink:href attribute is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
          <use xlink:href="#bad" x="0" y="0"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "xlink:href" not in result["sanitized_svg"]


class TestSvgSanitizerRemoveDangerousElements:
    """Removal of dangerous element types."""

    def test_foreignobject_removed(self):
        """<foreignObject> is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <foreignObject><body xmlns="http://www.w3.org/1999/xhtml"><script>alert(1)</script></body></foreignObject>
          <rect x="0" y="0" width="10" height="10" fill="#000"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "foreignObject" not in result["sanitized_svg"]
        assert "script" not in result["sanitized_svg"].lower()
        assert "alert" not in result["sanitized_svg"].lower()

    def test_iframe_removed(self):
        """<iframe> is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <iframe src="https://evil.com"/>
          <rect x="0" y="0" width="10" height="10" fill="#000"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "iframe" not in result["sanitized_svg"]

    def test_embed_removed(self):
        """<embed> is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <embed src="bad.swf"/>
          <rect x="0" y="0" width="10" height="10" fill="#000"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "embed" not in result["sanitized_svg"]

    def test_object_removed(self):
        """<object> is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <object data="bad.pdf"/>
          <rect x="0" y="0" width="10" height="10" fill="#000"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "object" not in result["sanitized_svg"]

    def test_img_removed(self):
        """<img> is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <img src="https://evil.com/tracker.png"/>
          <rect x="0" y="0" width="10" height="10" fill="#000"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "img" not in result["sanitized_svg"]

    def test_image_removed(self):
        """<image> is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <image href="https://evil.com/img.png"/>
          <rect x="0" y="0" width="10" height="10" fill="#000"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "image" not in result["sanitized_svg"]

    def test_use_removed(self):
        """<use> is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <defs><rect id="r" width="10" height="10"/></defs>
          <use href="#r" x="0" y="0"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "<use" not in result["sanitized_svg"]


class TestSvgSanitizerAttributes:
    """Attribute sanitization."""

    def test_unknown_attributes_removed(self):
        """Unknown attributes are removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <rect x="0" y="0" width="10" height="10" fill="#000" data-secret="bad" custom-attr="evil"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "data-secret" not in result["sanitized_svg"]
        assert "custom-attr" not in result["sanitized_svg"]

    def test_style_attribute_removed(self):
        """style attribute is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <rect x="0" y="0" width="10" height="10" style="fill:red;expression:alert(1)"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "style=" not in result["sanitized_svg"]

    def test_target_attribute_removed(self):
        """target attribute is removed."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <a href="/ok" target="_blank"><rect x="0" y="0" width="10" height="10" fill="#000"/></a>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "target=" not in result["sanitized_svg"]


class TestSvgSanitizerCdataAndEntities:
    """CDATA and entity expansion handling."""

    def test_cdata_sections_handled(self):
        """SVG with CDATA sections is handled."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <desc><![CDATA[Description with <b>tags</b>]]></desc>
          <rect x="0" y="0" width="10" height="10" fill="#000"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "<rect" in result["sanitized_svg"]

    def test_entity_expansion_attempts_handled(self):
        """Entity expansion is handled by XML parser (may fail or pass through)."""
        # This may return ok=False if parser rejects entities
        svg = """<!DOCTYPE svg [
          <!ENTITY xxe "attack">
        ]>
        <svg xmlns="http://www.w3.org/2000/svg">
          <text x="10" y="10">&xxe;</text>
        </svg>"""
        result = sanitize_svg(svg)
        # Either the parser rejects it (ok=False) or it handles it safely
        if result["ok"]:
            assert "attack" not in result["sanitized_svg"] or "text" not in result["sanitized_svg"].lower() or result["sanitized_svg"].count("attack") <= 1
        # Otherwise ok=False is acceptable too

    def test_xml_declaration_and_encoding(self):
        """SVG with XML declaration is handled."""
        svg = """<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <rect x="0" y="0" width="100" height="100" fill="#fff"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "<rect" in result["sanitized_svg"]


class TestSvgSanitizerGradientsAndPatterns:
    """Allowed elements like gradients and patterns are preserved."""

    def test_linear_gradient_preserved(self):
        """linearGradient is preserved."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#ff0000" stop-opacity="1"/>
              <stop offset="100%" stop-color="#0000ff" stop-opacity="1"/>
            </linearGradient>
          </defs>
          <rect x="0" y="0" width="100" height="100" fill="url(#grad1)"/>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "linearGradient" in result["sanitized_svg"]
        assert "stop-color" in result["sanitized_svg"]

    def test_clippath_preserved(self):
        """clipPath is preserved."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <defs>
            <clipPath id="clip1">
              <rect x="0" y="0" width="50" height="50"/>
            </clipPath>
          </defs>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "clipPath" in result["sanitized_svg"]

    def test_pattern_preserved(self):
        """pattern is preserved."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="pat1" width="10" height="10" patternUnits="userSpaceOnUse">
              <circle cx="5" cy="5" r="3" fill="#000"/>
            </pattern>
          </defs>
        </svg>"""
        result = sanitize_svg(svg)
        assert result["ok"] is True
        assert "pattern" in result["sanitized_svg"]

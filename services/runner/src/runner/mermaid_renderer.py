"""Mermaid diagram renderer — offline SVG generation via Node.js subprocess.

This module invokes `node scripts/mermaid-render.cjs` as a subprocess to
produce deterministic SVG output from Mermaid source strings with strict
security configuration (securityLevel: 'strict').

All rendering is server-side, offline, and sandboxed:
- No network access at render time.
- Subprocess receives only .mmd source text via stdin (no shell commands).
- Strict 30-second timeout prevents resource exhaustion.
- SVG output is passed to svg_sanitizer before use.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from typing import Any

# Path to the committed Node.js render script
_RENDER_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "scripts", "mermaid-render.cjs"
)


def _check_renderer_available() -> bool:
    """Return True if node is on PATH and the render script exists."""
    try:
        subprocess.run(
            ["node", "--version"],
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return os.path.isfile(_RENDER_SCRIPT)


def render_mermaid_to_svg(mermaid_source: str, diagram_type: str = "") -> dict[str, Any]:
    """Render Mermaid source text to SVG via Node.js subprocess.

    Parameters
    ----------
    mermaid_source:
        Mermaid diagram source (plain text, e.g., "graph TD; A-->B;").
    diagram_type:
        Informational label (requirement|state|sequence). Does not
        affect rendering; the actual syntax determines the output.

    Returns
    -------
    dict with keys:
        ok (bool) — True if SVG was generated.
        svg (str|None) — SVG string on success.
        error (str|None) — Error code on failure.
        diagram_type (str) — Echo of diagram_type parameter.
        byte_count (int) — Byte length of generated SVG.
        mermaid_sha256 (str|None) — SHA-256 of source text.
    """
    # Compute source hash unconditionally
    mermaid_sha256 = hashlib.sha256(mermaid_source.encode("utf-8")).hexdigest()

    if not mermaid_source or not mermaid_source.strip():
        return {
            "ok": False,
            "svg": None,
            "error": "empty_source",
            "diagram_type": diagram_type,
            "byte_count": 0,
            "mermaid_sha256": mermaid_sha256,
        }

    # Enforce 100 KB source limit (before sending to subprocess)
    source_bytes = len(mermaid_source.encode("utf-8"))
    if source_bytes > 100_000:
        return {
            "ok": False,
            "svg": None,
            "error": "source_too_large",
            "diagram_type": diagram_type,
            "byte_count": 0,
            "mermaid_sha256": mermaid_sha256,
        }

    # Check renderer availability
    if not _check_renderer_available():
        return {
            "ok": False,
            "svg": None,
            "error": "mermaid_renderer_not_available",
            "diagram_type": diagram_type,
            "byte_count": 0,
            "mermaid_sha256": mermaid_sha256,
        }

    try:
        proc = subprocess.run(
            ["node", _RENDER_SCRIPT],
            input=mermaid_source.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "svg": None,
            "error": "render_timeout",
            "diagram_type": diagram_type,
            "byte_count": 0,
            "mermaid_sha256": mermaid_sha256,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "svg": None,
            "error": "mermaid_renderer_not_available",
            "diagram_type": diagram_type,
            "byte_count": 0,
            "mermaid_sha256": mermaid_sha256,
        }
    except Exception as exc:
        return {
            "ok": False,
            "svg": None,
            "error": f"subprocess_error:{str(exc)[:500]}",
            "diagram_type": diagram_type,
            "byte_count": 0,
            "mermaid_sha256": mermaid_sha256,
        }

    # Check exit code
    if proc.returncode != 0:
        stderr_msg = proc.stderr.decode("utf-8", errors="replace").strip()
        return {
            "ok": False,
            "svg": None,
            "error": f"render_error:{stderr_msg[:500]}",
            "diagram_type": diagram_type,
            "byte_count": 0,
            "mermaid_sha256": mermaid_sha256,
        }

    svg = proc.stdout.decode("utf-8", errors="replace")
    svg_bytes = len(svg.encode("utf-8"))

    # Detect empty/invalid render output
    if "<svg" not in svg.lower() and not svg.startswith("<?xml"):
        return {
            "ok": False,
            "svg": None,
            "error": "render_produced_no_svg_element",
            "diagram_type": diagram_type,
            "byte_count": svg_bytes,
            "mermaid_sha256": mermaid_sha256,
        }

    return {
        "ok": True,
        "svg": svg,
        "error": None,
        "diagram_type": diagram_type,
        "byte_count": svg_bytes,
        "mermaid_sha256": mermaid_sha256,
    }

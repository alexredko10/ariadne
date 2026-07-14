"""
Artifact Workspace 4-Zone Shell Skeleton — PR 0143.

Isolated HTML/CSS/JS module for the read-only Artifact Workspace surface.
No filesystem access, no ASGI routing, no mutation, no external dependencies.
"""

from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# Deterministic fixture — matches GET /runs v1 contract shape
# ---------------------------------------------------------------------------

_WORKSPACE_FIXTURE = [
    {
        "run_id": "mock-run-001",
        "status": "completed",
        "reason_codes": ["completed"],
        "pipeline_status": "completed",
        "git_boundary_status": "approved",
        "execution_attempted": True,
        "created_at": "2026-07-10T12:05:00Z",
        "run_json_available": True,
        "manifest_available": True,
        "run_report_available": True,
        "missing_evidence": [],
        "malformed_evidence": [],
        "pr_url": None,
        "payload_cleanliness_available": False,
        "readiness_available": False,
    },
    {
        "run_id": "mock-run-002",
        "status": "blocked",
        "reason_codes": ["approval_required"],
        "pipeline_status": "completed",
        "git_boundary_status": "approved",
        "execution_attempted": False,
        "created_at": "2026-07-10T11:30:00Z",
        "run_json_available": True,
        "manifest_available": False,
        "run_report_available": False,
        "missing_evidence": ["manifest.json", "run-report.txt"],
        "malformed_evidence": [],
        "pr_url": None,
        "payload_cleanliness_available": False,
        "readiness_available": False,
    },
]

_WORKSPACE_FIXTURE_JSON = json.dumps(_WORKSPACE_FIXTURE, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------


def render_artifact_workspace() -> str:
    """Return the complete Artifact Workspace 4-Zone Shell HTML page.

    Returns
    -------
    str
        Complete HTML document with inline CSS, JS, and fixture data.
    """
    return _WORKSPACE_HTML.format(fixture_json=_WORKSPACE_FIXTURE_JSON)


# ---------------------------------------------------------------------------
# Workspace HTML
# ---------------------------------------------------------------------------

_WORKSPACE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ariadne — Artifact Workspace</title>
<style>
/* --- Layout --- */
* {{ box-sizing: border-box; }}
body {{ font-family: sans-serif; margin: 0; padding: 0; }}
#artifact-workspace {{ display: flex; flex-wrap: wrap; min-height: 100vh; }}
#artifact-workspace h1 {{
    width: 100%; margin: 0; padding: 0.75rem 1rem;
    background: #1a1a2e; color: #e0e0e0; font-size: 1.25rem;
}}

/* --- Zones --- */
.workspace-zone {{
    padding: 1rem; border: 1px solid #ccc;
    overflow-y: auto;
}}
.workspace-zone h2 {{ margin: 0 0 0.5rem 0; font-size: 1.1rem; color: #333; }}
.zone-placeholder {{ color: #888; font-style: italic; }}

#zone-timeline {{ background: #f0f4f8; }}
#zone-canvas {{ background: #fff; }}
#zone-gates-proofs {{ background: #f9f9f9; }}
#zone-logs-captures {{ background: #f5f5f5; }}

/* --- Timeline entries --- */
.timeline-entry {{
    padding: 0.4rem 0.5rem; margin-bottom: 0.25rem;
    border-bottom: 1px solid #ddd; font-size: 0.9rem; cursor: pointer;
}}
.timeline-entry:last-child {{ border-bottom: none; }}
.timeline-entry:hover {{ background: #e8ecf0; }}
.timeline-run-id {{ font-weight: bold; }}
.timeline-status {{ margin-left: 0.5rem; }}
.timeline-time {{ color: #888; font-size: 0.8rem; margin-left: 0.5rem; }}
.status-completed {{ color: #0a0; font-weight: bold; }}
.status-blocked {{ color: #a50; font-weight: bold; }}
.status-failed {{ color: #a00; font-weight: bold; }}

/* --- Desktop layout: two rows --- */
@media (min-width: 769px) {{
    #zone-timeline {{ flex: 0 0 220px; max-width: 220px; }}
    #zone-canvas {{ flex: 1 1 auto; }}
    #zone-gates-proofs {{ flex: 0 0 260px; max-width: 260px; }}
    #zone-logs-captures {{ width: 100%; max-height: 200px; }}
}}

/* --- Mobile layout: vertical stack --- */
@media (max-width: 768px) {{
    #zone-timeline, #zone-canvas, #zone-gates-proofs, #zone-logs-captures {{
        flex: 1 1 100%; max-width: 100%; max-height: none;
    }}
}}

/* --- Fabrication notice --- */
#fixture-notice {{
    background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;
    padding: 0.4rem 0.75rem; margin-bottom: 0.5rem; font-size: 0.8rem;
    color: #664d03;
}}
</style>
</head>
<body>
<div id="artifact-workspace" role="main" aria-label="Artifact Workspace">
<h1>Artifact Workspace</h1>

<div id="zone-timeline" class="workspace-zone" role="region" aria-labelledby="zone-timeline-heading">
<h2 id="zone-timeline-heading">Timeline</h2>
<div id="fixture-notice">Fixture data — not runtime evidence. Live timeline coming in PR 0144.</div>
<div id="timeline-entries"></div>
<noscript><p class="zone-placeholder">JavaScript is required for the timeline.</p></noscript>
</div>

<div id="zone-canvas" class="workspace-zone" role="region" aria-labelledby="zone-canvas-heading">
<h2 id="zone-canvas-heading">Artifact Canvas</h2>
<p class="zone-placeholder">Select a run from the timeline to view artifacts. No artifact loaded.</p>
</div>

<div id="zone-gates-proofs" class="workspace-zone" role="region" aria-labelledby="zone-gates-proofs-heading">
<h2 id="zone-gates-proofs-heading">Gates &amp; Proofs</h2>
<p class="zone-placeholder">No gate checks available. Gates and proofs will appear after Visual Gate implementation.</p>
</div>

<div id="zone-logs-captures" class="workspace-zone" role="region" aria-labelledby="zone-logs-captures-heading">
<h2 id="zone-logs-captures-heading">Logs &amp; Captures</h2>
<p class="zone-placeholder">No logs available. Captured execution output will appear here after a run is selected.</p>
</div>
</div>
<script>
// Safe HTML escaping — same pattern as server.js escHtml
function escHtml(s) {{
    if (s == null || s === undefined) return "not available";
    var div = document.createElement("div");
    div.textContent = String(s);
    return div.innerHTML;
}}

// Deterministic fixture data (matches GET /runs v1 contract with ev_contract_version "1")
var WORKSPACE_FIXTURE = {fixture_json};

// Render timeline entries from fixture
(function() {{
    var entriesDiv = document.getElementById("timeline-entries");
    if (!entriesDiv) return;
    var runs = WORKSPACE_FIXTURE;
    if (!runs || runs.length === 0) {{
        entriesDiv.innerHTML = '<p class="zone-placeholder">No runs available. Submit a task to see timeline entries.</p>';
        return;
    }}
    var html = "";
    for (var i = 0; i < runs.length; i++) {{
        var r = runs[i];
        var statusClass = "status-" + r.status;
        html += '<div class="timeline-entry" role="button" tabindex="0" '
            + 'onclick="selectRun(\'' + escHtml(r.run_id) + '\')" '
            + 'onkeydown="if(event.key===\'Enter\')selectRun(\'' + escHtml(r.run_id) + '\')">'
            + '<span class="timeline-run-id">' + escHtml(r.run_id) + '</span>'
            + '<span class="timeline-status ' + statusClass + '">' + escHtml(r.status) + '</span>'
            + '<span class="timeline-time">' + escHtml(r.created_at) + '</span>'
            + '</div>';
    }}
    entriesDiv.innerHTML = html;
}})();

// Run selection handler (placeholder — full detail in PR 0145)
function selectRun(runId) {{
    var canvas = document.getElementById("zone-canvas");
    var placeholder = canvas.querySelector(".zone-placeholder");
    if (placeholder) {{
        placeholder.textContent = "Selected run: " + runId + " — detail panel coming in PR 0145.";
    }}
}}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Module identity
# ---------------------------------------------------------------------------

__all__ = ["render_artifact_workspace"]

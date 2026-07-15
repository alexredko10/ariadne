"""
Artifact Workspace 4-Zone Shell — PR 0144 Live Run List Page.

Isolated HTML/CSS/JS module for the read-only Artifact Workspace surface.
PR 0144: Replaces production fixture with live GET /runs Timeline.
No filesystem access, no ASGI routing, no mutation, no external dependencies.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------


def render_artifact_workspace() -> str:
    """Return the complete Artifact Workspace 4-Zone Shell HTML page.

    Returns
    -------
    str
        Complete HTML document with inline CSS and JS.
    """
    return _WORKSPACE_HTML


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
.status-unknown {{ color: #888; font-weight: bold; }}

/* --- Timeline entry detail fields --- */
.timeline-branch {{ color: #888; font-size: 0.8rem; margin-left: 0.5rem; }}
.timeline-readiness {{ color: #888; font-size: 0.8rem; margin-left: 0.5rem; }}
.timeline-reason-codes {{ color: #555; font-size: 0.8rem; margin-left: 0.5rem; }}
.timeline-evidence-missing {{ color: #a50; font-size: 0.8rem; margin-left: 0.5rem; }}
.timeline-evidence-malformed {{ color: #a00; font-size: 0.8rem; margin-left: 0.5rem; }}
.timeline-pr-url {{ margin-left: 0.5rem; font-size: 0.8rem; }}
.timeline-pr-url a {{ color: #4a90d9; }}

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

</style>
</head>
<body>
<div id="artifact-workspace" role="main" aria-label="Artifact Workspace">
<h1>Artifact Workspace</h1>

<div id="zone-timeline" class="workspace-zone" role="region" aria-labelledby="zone-timeline-heading">
<h2 id="zone-timeline-heading">Timeline</h2>
<div id="timeline-entries" role="list" aria-label="Local run list"></div>
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

// Escapes text into a text node (safer than escHtml for plain text display)
function safeText(s) {{
    if (s == null || s === undefined) return "not available";
    return String(s);
}}

// ---- Live Run List ----

// Validate that a URL starts with http:// or https://
function isSafeUrl(url) {{
    if (typeof url !== "string") return false;
    return url.indexOf("http://") === 0 || url.indexOf("https://") === 0;
}}

// Show a state message in the timeline entries container
function showTimelineState(message, statusClass) {{
    var entriesDiv = document.getElementById("timeline-entries");
    if (!entriesDiv) return;
    entriesDiv.setAttribute("role", "status");
    entriesDiv.innerHTML = "";
    var p = document.createElement("p");
    p.className = "zone-placeholder";
    if (statusClass) p.className += " " + statusClass;
    p.textContent = message;
    entriesDiv.appendChild(p);
}}

// Render a non-empty run list
function renderRunList(runs) {{
    var entriesDiv = document.getElementById("timeline-entries");
    if (!entriesDiv) return;
    entriesDiv.setAttribute("role", "list");
    entriesDiv.innerHTML = "";

    if (!runs || runs.length === 0) {{
        showTimelineState("No runs available. Submit a task to see timeline entries.");
        return;
    }}

    for (var i = 0; i < runs.length; i++) {{
        var r = runs[i];

        // Validate minimum entry fields (run_id, status)
        if (!r.run_id || !r.status) {{
            // Malformed entry — show as incomplete with run_id if available
            var malformedDiv = document.createElement("div");
            malformedDiv.className = "timeline-entry";
            var malformedId = document.createElement("span");
            malformedId.className = "timeline-run-id";
            malformedId.textContent = safeText(r.run_id || "unknown");
            malformedDiv.appendChild(malformedId);
            var malformedStatus = document.createElement("span");
            malformedStatus.className = "timeline-status status-unknown";
            malformedStatus.textContent = "(incomplete)";
            malformedDiv.appendChild(malformedStatus);
            entriesDiv.appendChild(malformedDiv);
            continue;
        }}

        var entry = document.createElement("div");
        entry.className = "timeline-entry";
        entry.setAttribute("role", "button");
        entry.setAttribute("tabindex", "0");
        entry.setAttribute("aria-label", "Run " + r.run_id + ", status " + r.status);

        // Run ID
        var runIdSpan = document.createElement("span");
        runIdSpan.className = "timeline-run-id";
        runIdSpan.textContent = safeText(r.run_id);
        entry.appendChild(runIdSpan);

        // Status (visible text, not color-only)
        var statusSpan = document.createElement("span");
        statusSpan.className = "timeline-status status-" + safeText(r.status);
        statusSpan.textContent = safeText(r.status);
        entry.appendChild(statusSpan);

        // Created at
        var timeSpan = document.createElement("span");
        timeSpan.className = "timeline-time";
        var createdAt = r.created_at;
        timeSpan.textContent = "Created at: " + (createdAt || "not available");
        entry.appendChild(timeSpan);

        // Branch (always unavailable per OPTION A)
        var branchSpan = document.createElement("span");
        branchSpan.className = "timeline-branch";
        branchSpan.textContent = "branch: not available";
        entry.appendChild(branchSpan);

        // Readiness (always unavailable per OPTION A)
        var readinessSpan = document.createElement("span");
        readinessSpan.className = "timeline-readiness";
        readinessSpan.textContent = "readiness: not available";
        entry.appendChild(readinessSpan);

        // Reason codes
        if (r.reason_codes && r.reason_codes.length > 0) {{
            var rcSpan = document.createElement("span");
            rcSpan.className = "timeline-reason-codes";
            rcSpan.textContent = safeText(r.reason_codes.join(", "));
            entry.appendChild(rcSpan);
        }}

        // Evidence status indicators
        if (r.missing_evidence && r.missing_evidence.length > 0) {{
            var missingSpan = document.createElement("span");
            missingSpan.className = "timeline-evidence-missing";
            missingSpan.textContent = "Missing: " + safeText(r.missing_evidence.join(", "));
            entry.appendChild(missingSpan);
        }}
        if (r.malformed_evidence && r.malformed_evidence.length > 0) {{
            var malformedEvSpan = document.createElement("span");
            malformedEvSpan.className = "timeline-evidence-malformed";
            malformedEvSpan.textContent = "Malformed: " + safeText(r.malformed_evidence.join(", "));
            entry.appendChild(malformedEvSpan);
        }}

        // PR URL (safe rendering)
        if (r.pr_url) {{
            var prWrapper = document.createElement("span");
            prWrapper.className = "timeline-pr-url";
            if (isSafeUrl(r.pr_url)) {{
                var prLink = document.createElement("a");
                prLink.href = r.pr_url;
                prLink.target = "_blank";
                prLink.rel = "noopener noreferrer";
                prLink.textContent = safeText(r.pr_url);
                prWrapper.appendChild(prLink);
            }} else {{
                prWrapper.textContent = safeText(r.pr_url);
            }}
            entry.appendChild(prWrapper);
        }}

        // Keyboard and click handlers for entry selection
        (function(rid) {{
            entry.addEventListener("click", function() {{ selectRun(rid); }});
            entry.addEventListener("keydown", function(e) {{
                if (e.key === "Enter" || e.key === " ") {{
                    e.preventDefault();
                    selectRun(rid);
                }}
            }});
        }})(r.run_id);

        entriesDiv.appendChild(entry);
    }}
}}

// Fetch runs from GET /runs
function fetchRuns() {{
    var entriesDiv = document.getElementById("timeline-entries");
    if (!entriesDiv) return;

    // Show loading state
    showTimelineState("Loading runs...");

    fetch("/runs")
        .then(function(resp) {{
            if (!resp.ok) {{
                throw new Error("HTTP " + resp.status);
            }}
            return resp.json();
        }})
        .then(function(data) {{
            // Validate ev_contract_version
            if (!data.ev_contract_version || data.ev_contract_version !== "1") {{
                var actual = data.ev_contract_version || "missing";
                showTimelineState(
                    "Contract version mismatch. Expected '1' but received '" + actual + "'."
                );
                return;
            }}

            // Validate envelope
            if (typeof data.ok !== "boolean" || !Array.isArray(data.runs)) {{
                showTimelineState(
                    "Unexpected response format. Could not parse run list."
                );
                return;
            }}

            // Check root error
            if (data.ok === false) {{
                var errMsg = data.error || "Unknown error";
                showTimelineState(
                    "Runs directory not available. Run a task to create run evidence."
                );
                return;
            }}

            // Empty success
            if (data.count === 0 || data.runs.length === 0) {{
                showTimelineState(
                    "No runs available. Submit a task to see timeline entries."
                );
                return;
            }}

            // Non-empty success — render list
            renderRunList(data.runs);
        }})
        .catch(function(err) {{
            showTimelineState(
                "Failed to load run data. Check that the server is running."
            );
        }});
}}

// Run selection handler (placeholder — full detail in PR 0145)
function selectRun(runId) {{
    var canvas = document.getElementById("zone-canvas");
    var placeholder = canvas.querySelector(".zone-placeholder");
    if (placeholder) {{
        placeholder.textContent = "Selected run: " + runId + " — detail panel coming in PR 0145.";
    }}
}}

// Fetch live run list on page load
fetchRuns();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Module identity
# ---------------------------------------------------------------------------

__all__ = ["render_artifact_workspace"]

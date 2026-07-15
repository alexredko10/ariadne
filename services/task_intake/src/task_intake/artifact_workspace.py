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

/* --- Selected timeline entry --- */
.timeline-selected {{ background: #d0e0f0; border-left: 3px solid #4a90d9; }}

/* --- Timeline entry detail fields --- */
.timeline-branch {{ color: #888; font-size: 0.8rem; margin-left: 0.5rem; }}
.timeline-readiness {{ color: #888; font-size: 0.8rem; margin-left: 0.5rem; }}
.timeline-reason-codes {{ color: #555; font-size: 0.8rem; margin-left: 0.5rem; }}
.timeline-evidence-missing {{ color: #a50; font-size: 0.8rem; margin-left: 0.5rem; }}
.timeline-evidence-malformed {{ color: #a00; font-size: 0.8rem; margin-left: 0.5rem; }}
.timeline-pr-url {{ margin-left: 0.5rem; font-size: 0.8rem; }}
.timeline-pr-url a {{ color: #4a90d9; }}

/* --- Detail panel --- */
#detail-content {{ padding: 0.5rem; }}
#detail-content h3 {{ margin: 0.75rem 0 0.25rem 0; font-size: 1rem; color: #333; border-bottom: 1px solid #eee; padding-bottom: 0.2rem; }}
#detail-content .detail-row {{ margin: 0.3rem 0; font-size: 0.9rem; }}
#detail-content .detail-label {{ font-weight: bold; display: inline-block; min-width: 10rem; }}
#detail-content .detail-notice {{ margin: 0.3rem 0; padding-left: 1rem; font-size: 0.9rem; }}
#detail-content .detail-notice-path {{ font-weight: bold; }}
#detail-content .detail-exec-result {{ margin: 0.2rem 0; padding-left: 1rem; font-size: 0.9rem; }}
#detail-loading {{ color: #888; font-style: italic; }}

/* --- Report viewer --- */
#report-viewer {{ margin-top: 1.5rem; padding-top: 0.5rem; border-top: 2px solid #eee; }}
#report-viewer h3 {{ margin: 0 0 0.5rem 0; font-size: 1rem; color: #333; }}
#report-provenance {{ font-size: 0.85rem; color: #666; margin-bottom: 0.5rem; display: block; }}
#report-text {{ background: #f5f5f5; padding: 1rem; overflow: auto; max-height: 400px; white-space: pre-wrap; font-family: monospace; font-size: 0.85rem; margin: 0.5rem 0; border-radius: 4px; }}
#report-loading {{ color: #888; font-style: italic; }}
#report-not-proof {{ font-size: 0.85rem; color: #666; margin-top: 0.5rem; }}
#report-truncated-notice {{ color: #a50; font-size: 0.85rem; margin-top: 0.25rem; }}

/* --- Gates & Proofs and Logs & Captures zone content --- */
#gates-content h3, #logs-content h3 {{ margin: 0.75rem 0 0.25rem 0; font-size: 1rem; color: #333; border-bottom: 1px solid #eee; padding-bottom: 0.2rem; }}
#gates-content .gate-entry, #logs-content .log-entry {{ margin: 0.25rem 0; font-size: 0.85rem; }}
#gates-content .gate-label, #logs-content .log-label {{ font-weight: bold; }}
#gates-content .gate-classification, #logs-content .log-classification {{ color: #666; font-size: 0.8rem; margin-left: 0.5rem; }}
.gate-not-available {{ color: #888; font-style: italic; font-size: 0.85rem; }}

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
<div id="gates-content"><p class="zone-placeholder">No gate checks available. Select a run to view manifest and evidence.</p></div>
</div>

<div id="zone-logs-captures" class="workspace-zone" role="region" aria-labelledby="zone-logs-captures-heading">
<h2 id="zone-logs-captures-heading">Logs &amp; Captures</h2>
<div id="logs-content"><p class="zone-placeholder">No logs available. Select a run to view execution output.</p></div>
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

// ---- Selection and Detail Panel ----

var detailRequestCounter = 0;
var selectedRunId = null;

// Run selection handler — fetches detail and renders panel
function selectRun(runId) {{
    // Update selected state on timeline entries
    var prevSelected = document.querySelector(".timeline-entry[aria-selected='true']");
    if (prevSelected) {{
        prevSelected.removeAttribute("aria-selected");
        prevSelected.classList.remove("timeline-selected");
    }}
    var entries = document.querySelectorAll(".timeline-entry");
    for (var i = 0; i < entries.length; i++) {{
        if (entries[i].querySelector(".timeline-run-id") &&
            entries[i].querySelector(".timeline-run-id").textContent === runId) {{
            entries[i].setAttribute("aria-selected", "true");
            entries[i].classList.add("timeline-selected");
        }}
    }}

    selectedRunId = runId;
    var requestId = ++detailRequestCounter;
    showDetailLoading(runId);
    showGatesLoading();
    showLogsLoading();

    fetch("/runs/" + encodeURIComponent(runId))
        .then(function(resp) {{
            if (!resp.ok) {{
                throw new Error("HTTP " + resp.status);
            }}
            return resp.json();
        }})
        .then(function(data) {{
            if (requestId !== detailRequestCounter) return; // stale
            renderDetail(data);
            renderGatesProofs(data);
            renderLogsCaptures(data);
        }})
        .catch(function(err) {{
            if (requestId !== detailRequestCounter) return; // stale
            showDetailFetchFailure();
            showGatesUnavailable();
            showLogsUnavailable();
        }});

    // Fetch report in parallel with detail
    fetchReport(runId);
}}

// Show loading state in the canvas
function showDetailLoading(runId) {{
    var canvas = document.getElementById("zone-canvas");
    if (!canvas) return;
    // Remove any existing detail content or placeholder
    var existingContent = canvas.querySelector("#detail-content");
    if (existingContent) existingContent.remove();
    var existingLoading = canvas.querySelector("#detail-loading");
    if (existingLoading) existingLoading.remove();
    var placeholder = canvas.querySelector(".zone-placeholder");
    if (placeholder) placeholder.remove();

    var loadingP = document.createElement("p");
    loadingP.id = "detail-loading";
    loadingP.className = "zone-placeholder";
    loadingP.textContent = "Loading detail for " + runId + "...";
    canvas.appendChild(loadingP);
}}

// Show a detail state message
function showDetailState(message) {{
    var canvas = document.getElementById("zone-canvas");
    if (!canvas) return;
    var existingContent = canvas.querySelector("#detail-content");
    if (existingContent) existingContent.remove();
    var existingLoading = canvas.querySelector("#detail-loading");
    if (existingLoading) existingLoading.remove();
    var placeholder = canvas.querySelector(".zone-placeholder");
    if (placeholder) placeholder.remove();

    var p = document.createElement("p");
    p.className = "zone-placeholder";
    p.textContent = message;
    canvas.appendChild(p);
}}

// Show fetch failure state
function showDetailFetchFailure() {{
    showDetailState("Failed to load run detail. Check that the server is running.");
}}

// Render a label-value detail row
function detailRow(label, value) {{
    var div = document.createElement("div");
    div.className = "detail-row";
    var labelSpan = document.createElement("span");
    labelSpan.className = "detail-label";
    labelSpan.textContent = label + ":";
    div.appendChild(labelSpan);
    if (typeof value === "string") {{
        div.appendChild(document.createTextNode(" " + value));
    }} else {{
        // value element
        div.appendChild(document.createTextNode(" "));
        div.appendChild(value);
    }}
    return div;
}}

// Render the full detail panel
function renderDetail(data) {{
    var canvas = document.getElementById("zone-canvas");
    if (!canvas) return;

    // Clear existing content
    var existingContent = canvas.querySelector("#detail-content");
    if (existingContent) existingContent.remove();
    var existingLoading = canvas.querySelector("#detail-loading");
    if (existingLoading) existingLoading.remove();
    var placeholder = canvas.querySelector(".zone-placeholder");
    if (placeholder) placeholder.remove();

    // Validate version
    if (!data.ev_contract_version || data.ev_contract_version !== "1") {{
        var actual = data.ev_contract_version || "missing";
        showDetailState("Contract version mismatch. Expected '1' but received '" + actual + "'.");
        return;
    }}

    // Validate envelope
    if (typeof data.ok !== "boolean") {{
        showDetailState("Unexpected detail response format.");
        return;
    }}

    // Error state — ok=false
    if (data.ok === false) {{
        // Unknown run or root error
        showDetailState("Run not found: " + selectedRunId + ". The run may have been removed.");
        return;
    }}

    // Validate summary
    if (!data.summary || typeof data.summary !== "object") {{
        showDetailState("Run summary not available.");
        return;
    }}

    // Validate detail
    if (!data.detail || typeof data.detail !== "object") {{
        showDetailState("Detail evidence not available.");
        return;
    }}

    // Build detail content container
    var content = document.createElement("div");
    content.id = "detail-content";

    var s = data.summary;
    var d = data.detail;

    // ---- Summary Section ----
    var summaryH3 = document.createElement("h3");
    summaryH3.textContent = "Summary";
    content.appendChild(summaryH3);

    // 1. Run ID
    content.appendChild(detailRow("Run ID", safeText(s.run_id)));

    // 2. Status
    var statusSpan = document.createElement("span");
    statusSpan.className = "status-" + safeText(s.status);
    statusSpan.textContent = safeText(s.status);
    content.appendChild(detailRow("Status", statusSpan));

    // 3. Reason codes
    var rcText = (s.reason_codes && s.reason_codes.length > 0)
        ? s.reason_codes.join(", ")
        : "none";
    content.appendChild(detailRow("Reason codes", safeText(rcText)));

    // 4. Pipeline status
    content.appendChild(detailRow("Pipeline status", safeText(s.pipeline_status)));

    // 5. Git boundary status
    content.appendChild(detailRow("Git boundary status", safeText(s.git_boundary_status)));

    // 6. Execution attempted
    var execAttempted = (s.execution_attempted === true) ? "yes" :
        (s.execution_attempted === false) ? "no" : "not available";
    content.appendChild(detailRow("Execution attempted", execAttempted));

    // 7. Created at
    content.appendChild(detailRow("Created at", safeText(s.created_at)));

    // 8. PR URL
    if (s.pr_url) {{
        var prSpan = document.createElement("span");
        if (isSafeUrl(s.pr_url)) {{
            var prLink = document.createElement("a");
            prLink.href = s.pr_url;
            prLink.target = "_blank";
            prLink.rel = "noopener noreferrer";
            prLink.textContent = safeText(s.pr_url);
            prSpan.appendChild(prLink);
        }} else {{
            prSpan.textContent = safeText(s.pr_url);
        }}
        content.appendChild(detailRow("PR URL", prSpan));
    }}

    // 9. Run JSON available
    content.appendChild(detailRow("Run JSON available", s.run_json_available ? "available" : "not available"));

    // 10. Manifest available
    content.appendChild(detailRow("Manifest available", s.manifest_available ? "available" : "not available"));

    // 11. Run report available
    content.appendChild(detailRow("Run report available", s.run_report_available ? "available" : "not available"));

    // ---- Detail Section ----
    var detailH3 = document.createElement("h3");
    detailH3.textContent = "Evidence";
    content.appendChild(detailH3);

    // 12. Execution results
    var erH4 = document.createElement("h4");
    erH4.textContent = "Execution Results";
    content.appendChild(erH4);
    if (d.execution_results && d.execution_results.length > 0) {{
        for (var i = 0; i < d.execution_results.length; i++) {{
            var er = d.execution_results[i];
            var erDiv = document.createElement("div");
            erDiv.className = "detail-exec-result";
            var opText = safeText(er.operation || "unknown");
            var ecText = (er.exit_code !== undefined && er.exit_code !== null)
                ? safeText(String(er.exit_code))
                : "—";
            erDiv.textContent = opText + ": exit_code " + ecText;
            content.appendChild(erDiv);
        }}
    }} else {{
        var erEmpty = document.createElement("p");
        erEmpty.className = "zone-placeholder";
        erEmpty.textContent = "No execution results available.";
        content.appendChild(erEmpty);
    }}

    // 13. Evidence paths (text only, not clickable)
    var epH4 = document.createElement("h4");
    epH4.textContent = "Evidence Paths";
    content.appendChild(epH4);
    if (d.evidence_paths && d.evidence_paths.length > 0) {{
        for (var j = 0; j < d.evidence_paths.length; j++) {{
            var epDiv = document.createElement("div");
            epDiv.className = "detail-row";
            epDiv.textContent = safeText(d.evidence_paths[j]);
            content.appendChild(epDiv);
        }}
    }} else {{
        var epEmpty = document.createElement("p");
        epEmpty.className = "zone-placeholder";
        epEmpty.textContent = "No evidence paths available.";
        content.appendChild(epEmpty);
    }}

    // 14. Run JSON hash
    content.appendChild(detailRow("Run JSON hash", safeText(d.run_json_hash)));

    // 15. Source errors
    var seH4 = document.createElement("h4");
    seH4.textContent = "Source Errors";
    content.appendChild(seH4);
    if (d.source_errors && d.source_errors.length > 0) {{
        content.appendChild(detailRow("Source errors", safeText(d.source_errors.join(", "))));
    }} else {{
        var seEmpty = document.createElement("p");
        seEmpty.className = "zone-placeholder";
        seEmpty.textContent = "No source errors reported.";
        content.appendChild(seEmpty);
    }}

    // ---- Unavailable Values ----
    var unavH3 = document.createElement("h3");
    unavH3.textContent = "Unavailable Values";
    content.appendChild(unavH3);

    // 16. Payload cleanliness (always null)
    content.appendChild(detailRow("Payload cleanliness", "not available"));

    // 17. Readiness (always null)
    content.appendChild(detailRow("Readiness", "not available"));

    // ---- Notices ----
    var noticesH3 = document.createElement("h3");
    noticesH3.textContent = "Notices";
    content.appendChild(noticesH3);

    // 18. Missing evidence
    var missingH4 = document.createElement("h4");
    missingH4.textContent = "Missing Evidence";
    content.appendChild(missingH4);
    if (data.missing && data.missing.length > 0) {{
        for (var k = 0; k < data.missing.length; k++) {{
            var mDiv = document.createElement("div");
            mDiv.className = "detail-notice";
            var mPath = document.createElement("span");
            mPath.className = "detail-notice-path";
            mPath.textContent = safeText(data.missing[k].expected_path);
            mDiv.appendChild(mPath);
            mDiv.appendChild(document.createTextNode(": " + safeText(data.missing[k].reason)));
            content.appendChild(mDiv);
        }}
    }} else {{
        var mEmpty = document.createElement("p");
        mEmpty.className = "zone-placeholder";
        mEmpty.textContent = "No missing evidence.";
        content.appendChild(mEmpty);
    }}

    // 19. Malformed evidence
    var malformedH4 = document.createElement("h4");
    malformedH4.textContent = "Malformed Evidence";
    content.appendChild(malformedH4);
    if (data.malformed && data.malformed.length > 0) {{
        for (var l = 0; l < data.malformed.length; l++) {{
            var mfDiv = document.createElement("div");
            mfDiv.className = "detail-notice";
            var mfPath = document.createElement("span");
            mfPath.className = "detail-notice-path";
            mfPath.textContent = safeText(data.malformed[l].expected_path);
            mfDiv.appendChild(mfPath);
            mfDiv.appendChild(document.createTextNode(": " + safeText(data.malformed[l].reason)));
            content.appendChild(mfDiv);
        }}
    }} else {{
        var mfEmpty = document.createElement("p");
        mfEmpty.className = "zone-placeholder";
        mfEmpty.textContent = "No malformed evidence.";
        content.appendChild(mfEmpty);
    }}

    canvas.appendChild(content);
}}

// ---- Report Viewer ----

function fetchReport(runId) {{
    var requestId = ++detailRequestCounter;
    showReportLoading();

    fetch("/runs/" + encodeURIComponent(runId) + "/report")
        .then(function(resp) {{
            if (!resp.ok) {{
                throw new Error("HTTP " + resp.status);
            }}
            return resp.json();
        }})
        .then(function(data) {{
            if (requestId !== detailRequestCounter) return; // stale
            renderReport(data);
        }})
        .catch(function(err) {{
            if (requestId !== detailRequestCounter) return; // stale
            showReportFetchFailure();
        }});
}}

function showReportLoading() {{
    var viewer = getOrCreateReportViewer();
    if (!viewer) return;
    var loading = viewer.querySelector("#report-loading");
    var pre = viewer.querySelector("#report-text");
    var provenance = viewer.querySelector("#report-provenance");
    if (loading) loading.style.display = "";
    if (pre) pre.style.display = "none";
    if (provenance) provenance.textContent = "";
    if (loading) loading.textContent = "Loading report...";
}}

function showReportFetchFailure() {{
    var viewer = getOrCreateReportViewer();
    if (!viewer) return;
    setReportState(viewer, "Failed to load report. Check that the server is running.", "");
}}

function getOrCreateReportViewer() {{
    var canvas = document.getElementById("zone-canvas");
    if (!canvas) return null;

    var viewer = canvas.querySelector("#report-viewer");
    if (!viewer) {{
        viewer = document.createElement("div");
        viewer.id = "report-viewer";
        viewer.setAttribute("role", "region");
        viewer.setAttribute("aria-labelledby", "report-heading");

        var heading = document.createElement("h3");
        heading.id = "report-heading";
        heading.textContent = "Run Report";
        viewer.appendChild(heading);

        var provenanceSpan = document.createElement("span");
        provenanceSpan.id = "report-provenance";
        viewer.appendChild(provenanceSpan);

        var loadingP = document.createElement("p");
        loadingP.id = "report-loading";
        loadingP.className = "zone-placeholder";
        loadingP.textContent = "Loading report...";
        viewer.appendChild(loadingP);

        var pre = document.createElement("pre");
        pre.id = "report-text";
        pre.style.display = "none";
        viewer.appendChild(pre);

        canvas.appendChild(viewer);
    }}
    return viewer;
}}

function clearReportViewer() {{
    var canvas = document.getElementById("zone-canvas");
    if (!canvas) return;
    var viewer = canvas.querySelector("#report-viewer");
    if (viewer) viewer.remove();
}}

function setReportState(viewer, message, provenanceText) {{
    if (!viewer) return;
    var loading = viewer.querySelector("#report-loading");
    var pre = viewer.querySelector("#report-text");
    var provenance = viewer.querySelector("#report-provenance");

    if (loading) loading.style.display = "none";
    if (pre) pre.style.display = "none";
    if (provenance) provenance.textContent = provenanceText || "";

    // Remove truncation notice and not-proof disclaimer
    var truncNotice = viewer.querySelector("#report-truncated-notice");
    if (truncNotice) truncNotice.remove();
    var nproof = viewer.querySelector("#report-not-proof");
    if (nproof) nproof.remove();

    if (message) {{
        if (loading) {{
            loading.style.display = "";
            loading.textContent = message;
        }}
    }}
}}

function renderReport(data) {{
    var viewer = getOrCreateReportViewer();
    if (!viewer) return;

    var loading = viewer.querySelector("#report-loading");
    var pre = viewer.querySelector("#report-text");
    var provenance = viewer.querySelector("#report-provenance");

    // Clear prior state
    loading.style.display = "none";
    pre.style.display = "";
    pre.textContent = "";
    provenance.textContent = "";
    var truncNotice = viewer.querySelector("#report-truncated-notice");
    if (truncNotice) truncNotice.remove();
    var nproof = viewer.querySelector("#report-not-proof");
    if (nproof) nproof.remove();

    // Validate version
    if (!data.ev_contract_version || data.ev_contract_version !== "1") {{
        var actual = data.ev_contract_version || "missing";
        setReportState(viewer,
            "Contract version mismatch. Expected '1' but received '" + actual + "'.",
            "");
        return;
    }}

    // Validate envelope
    if (typeof data.ok !== "boolean") {{
        setReportState(viewer, "Unexpected report response format.", "");
        return;
    }}

    // Set provenance
    if (data.provenance) {{
        provenance.textContent = data.provenance;
    }}

    // Error states
    if (data.ok === false) {{
        var err = data.error || "unknown error";
        if (err === "file_not_found") {{
            setReportState(viewer,
                "Run report not available.",
                data.provenance || "");
        }} else if (err === "run not found") {{
            setReportState(viewer,
                "Report not available: run not found.",
                data.provenance || "");
        }} else if (err && err.indexOf("read_error") === 0) {{
            setReportState(viewer,
                "Report could not be read: " + err + ".",
                data.provenance || "");
        }} else {{
            setReportState(viewer,
                "Report could not be read: " + err + ".",
                data.provenance || "");
        }}
        return;
    }}

    // Success — set report content via textContent
    if (data.content === "" || data.content === null) {{
        if (data.report_exists) {{
            setReportState(viewer,
                "Report file exists but contains no content.",
                data.provenance || "");
        }} else {{
            setReportState(viewer,
                "Run report not available.",
                data.provenance || "");
        }}
        return;
    }}

    // Complete report — use textContent on pre element
    pre.textContent = data.content;

    // Show truncation notice if truncated
    if (data.truncated) {{
        var truncP = document.createElement("p");
        truncP.id = "report-truncated-notice";
        truncP.className = "zone-placeholder";
        truncP.textContent = "(Report truncated at " + data.truncation_limit + " characters.)";
        viewer.insertBefore(truncP, pre.nextSibling);
    }}

    // Add "not proof" disclaimer
    var disclaimer = document.createElement("p");
    disclaimer.id = "report-not-proof";
    disclaimer.textContent =
        "Report text is displayed as evidence context. " +
        "It is not independently verified proof.";
    viewer.appendChild(disclaimer);
}}

// ---- Gates & Proofs Viewer ----

function showGatesLoading() {{
    var zone = document.getElementById("zone-gates-proofs");
    if (!zone) return;
    var content = zone.querySelector("#gates-content");
    if (!content) return;
    content.innerHTML = "";
    var p = document.createElement("p");
    p.className = "zone-placeholder";
    p.textContent = "Loading...";
    content.appendChild(p);
}}

function showGatesUnavailable() {{
    var zone = document.getElementById("zone-gates-proofs");
    if (!zone) return;
    var content = zone.querySelector("#gates-content");
    if (!content) return;
    content.innerHTML = "";
    var p = document.createElement("p");
    p.className = "zone-placeholder";
    p.textContent = "Gates and proofs data not available. Check that the server is running.";
    content.appendChild(p);
}}

function renderGatesProofs(data) {{
    var zone = document.getElementById("zone-gates-proofs");
    if (!zone) return;
    var content = zone.querySelector("#gates-content");
    if (!content) return;

    // Clear zone content
    content.innerHTML = "";

    // No detail data — show unavailable
    if (!data.detail) {{
        var p = document.createElement("p");
        p.className = "zone-placeholder";
        p.textContent = "Manifest and evidence not available.";
        content.appendChild(p);
        return;
    }}

    var d = data.detail;

    // ---- Manifest Files ----
    var mfH3 = document.createElement("h3");
    mfH3.textContent = "Manifest Files";
    content.appendChild(mfH3);

    if (d.manifest_files && d.manifest_files.length > 0) {{
        for (var i = 0; i < d.manifest_files.length; i++) {{
            var entry = document.createElement("div");
            entry.className = "gate-entry";
            var nameSpan = document.createElement("span");
            nameSpan.className = "gate-label";
            nameSpan.textContent = safeText(d.manifest_files[i]);
            entry.appendChild(nameSpan);
            var classSpan = document.createElement("span");
            classSpan.className = "gate-classification";
            classSpan.textContent = "Runtime Evidence: listed in manifest.json";
            entry.appendChild(classSpan);
            content.appendChild(entry);
        }}
    }} else if (d.manifest_files && d.manifest_files.length === 0) {{
        var emptyP = document.createElement("p");
        emptyP.className = "gate-not-available";
        emptyP.textContent = "Manifest file list is empty.";
        content.appendChild(emptyP);
    }} else {{
        var naP = document.createElement("p");
        naP.className = "gate-not-available";
        naP.textContent = "Manifest not available. The manifest.json file is missing or unreadable.";
        content.appendChild(naP);
    }}

    // ---- Evidence Paths ----
    var epH3 = document.createElement("h3");
    epH3.textContent = "Evidence Paths";
    content.appendChild(epH3);

    if (d.evidence_paths && d.evidence_paths.length > 0) {{
        for (var j = 0; j < d.evidence_paths.length; j++) {{
            var epEntry = document.createElement("div");
            epEntry.className = "gate-entry";
            var epName = document.createElement("span");
            epName.className = "gate-label";
            epName.textContent = safeText(d.evidence_paths[j]);
            epEntry.appendChild(epName);
            var epClass = document.createElement("span");
            epClass.className = "gate-classification";
            epClass.textContent = "Evidence reference";
            epEntry.appendChild(epClass);
            content.appendChild(epEntry);
        }}
    }} else {{
        var epNA = document.createElement("p");
        epNA.className = "gate-not-available";
        epNA.textContent = "No evidence paths available.";
        content.appendChild(epNA);
    }}

    // ---- Run JSON Hash ----
    var hashH3 = document.createElement("h3");
    hashH3.textContent = "Run JSON Hash";
    content.appendChild(hashH3);

    if (d.run_json_hash) {{
        var hashEntry = document.createElement("div");
        hashEntry.className = "gate-entry";
        var hashName = document.createElement("span");
        hashName.className = "gate-label";
        hashName.textContent = safeText(d.run_json_hash);
        hashEntry.appendChild(hashName);
        var hashClass = document.createElement("span");
        hashClass.className = "gate-classification";
        hashClass.textContent = "(as recorded in manifest)";
        hashEntry.appendChild(hashClass);
        content.appendChild(hashEntry);
    }} else {{
        var hashNA = document.createElement("p");
        hashNA.className = "gate-not-available";
        hashNA.textContent = "Run JSON hash not available.";
        content.appendChild(hashNA);
    }}

    // ---- Source Errors ----
    var seH3 = document.createElement("h3");
    seH3.textContent = "Source Errors";
    content.appendChild(seH3);

    if (d.source_errors && d.source_errors.length > 0) {{
        for (var k = 0; k < d.source_errors.length; k++) {{
            var seEntry = document.createElement("div");
            seEntry.className = "gate-entry";
            var seName = document.createElement("span");
            seName.className = "gate-label";
            seName.textContent = safeText(d.source_errors[k]);
            seEntry.appendChild(seName);
            var seClass = document.createElement("span");
            seClass.className = "gate-classification";
            seClass.textContent = "Source error";
            seEntry.appendChild(seClass);
            content.appendChild(seEntry);
        }}
    }} else {{
        var seNA = document.createElement("p");
        seNA.className = "gate-not-available";
        seNA.textContent = "No source errors reported.";
        content.appendChild(seNA);
    }}

    // ---- Agent Claims (PR URL) ----
    if (data.summary && data.summary.pr_url) {{
        var acH3 = document.createElement("h3");
        acH3.textContent = "Agent Claims";
        content.appendChild(acH3);

        var acEntry = document.createElement("div");
        acEntry.className = "gate-entry";
        var acLabel = document.createElement("span");
        acLabel.className = "gate-label";
        acLabel.textContent = "Agent-performed operation: gh_pr_create";
        acEntry.appendChild(acLabel);
        var acUrl = document.createElement("span");
        acUrl.className = "gate-classification";
        if (isSafeUrl(data.summary.pr_url)) {{
            var acLink = document.createElement("a");
            acLink.href = data.summary.pr_url;
            acLink.target = "_blank";
            acLink.rel = "noopener noreferrer";
            acLink.textContent = safeText(data.summary.pr_url);
            acUrl.appendChild(acLink);
        }} else {{
            acUrl.textContent = safeText(data.summary.pr_url);
        }}
        acEntry.appendChild(acUrl);
        content.appendChild(acEntry);
    }}

    // ---- Report Provenance ----
    var rpH3 = document.createElement("h3");
    rpH3.textContent = "Report Provenance";
    content.appendChild(rpH3);

    var rpP = document.createElement("p");
    rpP.className = "gate-entry";
    if (data.summary && data.summary.run_report_available) {{
        rpP.textContent = "Run report is available. \"Report text is not independently verified proof.\"";
    }} else {{
        rpP.textContent = "Run report is not available.";
    }}
    content.appendChild(rpP);

    // ---- Proof references unavailable ----
    var prH3 = document.createElement("h3");
    prH3.textContent = "Proof References";
    content.appendChild(prH3);

    var prP = document.createElement("p");
    prP.className = "gate-not-available";
    prP.textContent = "proof_refs are not stored in the current persisted evidence model. Evidence paths are file references, not independently verified proof.";
    content.appendChild(prP);
}}

// ---- Logs & Captures Viewer ----

function showLogsLoading() {{
    var zone = document.getElementById("zone-logs-captures");
    if (!zone) return;
    var content = zone.querySelector("#logs-content");
    if (!content) return;
    content.innerHTML = "";
    var p = document.createElement("p");
    p.className = "zone-placeholder";
    p.textContent = "Loading...";
    content.appendChild(p);
}}

function showLogsUnavailable() {{
    var zone = document.getElementById("zone-logs-captures");
    if (!zone) return;
    var content = zone.querySelector("#logs-content");
    if (!content) return;
    content.innerHTML = "";
    var p = document.createElement("p");
    p.className = "zone-placeholder";
    p.textContent = "Logs and captures data not available. Check that the server is running.";
    content.appendChild(p);
}}

function renderLogsCaptures(data) {{
    var zone = document.getElementById("zone-logs-captures");
    if (!zone) return;
    var content = zone.querySelector("#logs-content");
    if (!content) return;

    // Clear zone content
    content.innerHTML = "";

    // Default explanation about captures/logs
    var defaultP = document.createElement("p");
    defaultP.className = "gate-not-available";
    defaultP.textContent = "Command captures and logs are not stored in the current run evidence model. " +
        "Each execution result shows only operation name and exit code. " +
        "stdout, stderr, and command output are not captured.";
    content.appendChild(defaultP);

    if (!data.detail) {{
        return;
    }}

    var d = data.detail;

    // ---- Execution Summary ----
    var esH3 = document.createElement("h3");
    esH3.textContent = "Execution Summary";
    content.appendChild(esH3);

    if (d.execution_results && d.execution_results.length > 0) {{
        for (var i = 0; i < d.execution_results.length; i++) {{
            var er = d.execution_results[i];
            var erDiv = document.createElement("div");
            erDiv.className = "log-entry";
            var opSpan = document.createElement("span");
            opSpan.className = "log-label";
            opSpan.textContent = "Execution Result: " + safeText(er.operation || "unknown");
            erDiv.appendChild(opSpan);
            var ecSpan = document.createElement("span");
            ecSpan.className = "log-classification";
            var ecText = (er.exit_code !== undefined && er.exit_code !== null)
                ? safeText(String(er.exit_code))
                : "unknown";
            ecSpan.textContent = "exit_code: " + ecText;
            erDiv.appendChild(ecSpan);
            content.appendChild(erDiv);
        }}
    }} else {{
        var erNA = document.createElement("p");
        erNA.className = "gate-not-available";
        erNA.textContent = "No execution results recorded.";
        content.appendChild(erNA);
    }}

    // ---- Source Errors ----
    if (d.source_errors && d.source_errors.length > 0) {{
        var seH3 = document.createElement("h3");
        seH3.textContent = "Source Errors";
        content.appendChild(seH3);

        for (var j = 0; j < d.source_errors.length; j++) {{
            var seDiv = document.createElement("div");
            seDiv.className = "log-entry";
            seDiv.textContent = safeText(d.source_errors[j]);
            content.appendChild(seDiv);
        }}
    }}
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

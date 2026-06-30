"""Task Intake HTTP server — minimal stdlib ASGI application.

Exposes the Task Intake service via HTTP endpoints.
This is intake-only.  It does not invoke the runner, orchestrate agents,
create run records, or write to ``.ariadne/**``.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs

from task_intake.app import accept_task
from task_intake.doctor import doctor
from task_intake.models import TaskIntakeRequest
from task_intake.normalize import normalize_task_intake
from task_intake.context_preview import generate_context_preview
from task_intake.runs import create_mock_run
from task_intake.mock_loop import run_mock_loop
from task_intake.execution_handoff import run_mock_execution_handoff

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONTENT_TYPE_JSON = "application/json"

# ---------------------------------------------------------------------------
# ASGI app
# ---------------------------------------------------------------------------


async def app(scope: dict, receive: callable, send: callable) -> None:
    """Minimal ASGI application for Task Intake HTTP.

    Parameters
    ----------
    scope
        ASGI connection scope.
    receive
        ASGI receive callable.
    send
        ASGI send callable.
    """
    if scope["type"] != "http":
        return

    method = scope["method"]
    path = scope["path"]

    # --- Route matching ---
    if method == "GET" and path == "/health":
        body = json.dumps(dict(doctor()), ensure_ascii=False).encode("utf-8")
        await _send_json(send, 200, body)
        return

    if method == "POST" and path in ("/submit", "/task-intake/submit"):
        # Read body
        body_bytes = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] == "http.request":
                body_bytes += event.get("body", b"")
                more_body = event.get("more_body", False)

        # Parse JSON
        try:
            data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            await _send_json(
                send, 400,
                json.dumps({
                    "status": "rejected",
                    "reason": "Invalid JSON body.",
                    "error_code": "unsupported_request",
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        prompt = data.get("prompt") if isinstance(data, dict) else None
        if not isinstance(prompt, str):
            await _send_json(
                send, 400,
                json.dumps({
                    "status": "rejected",
                    "reason": "prompt is required and must be a string.",
                    "error_code": "unsupported_request",
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        result = accept_task(TaskIntakeRequest(prompt=prompt))

        if result.status.value == "accepted":
            body = json.dumps({
                "status": "accepted",
                "task_id": result.task_id,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps({
                "status": "rejected",
                "reason": result.reason,
                "error_code": result.error_code.value if result.error_code else "",
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        return

    if method == "POST" and path == "/task-intake/normalize":
        # Read body
        body_bytes = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] == "http.request":
                body_bytes += event.get("body", b"")
                more_body = event.get("more_body", False)

        # Parse JSON
        try:
            data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            await _send_json(
                send, 400,
                json.dumps({
                    "ok": False,
                    "validation": {
                        "valid": False,
                        "errors": ["Invalid JSON body."],
                        "warnings": [],
                    },
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        result = normalize_task_intake(data)

        if result.get("ok") is True:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 400, body)
        return

    if method == "POST" and path == "/context/preview":
        # Read body
        body_bytes = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] == "http.request":
                body_bytes += event.get("body", b"")
                more_body = event.get("more_body", False)

        # Parse JSON
        try:
            data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            await _send_json(
                send, 400,
                json.dumps({
                    "ok": False,
                    "validation": {
                        "valid": False,
                        "errors": ["Invalid JSON body."],
                        "warnings": [],
                    },
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        result = generate_context_preview(data)

        if result.get("ok") is True:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 400, body)
        return

    if method == "POST" and path == "/runs":
        # Read body
        body_bytes = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] == "http.request":
                body_bytes += event.get("body", b"")
                more_body = event.get("more_body", False)

        # Parse JSON
        try:
            data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            await _send_json(
                send, 400,
                json.dumps({
                    "ok": False,
                    "status": {
                        "state": "validation_failed",
                        "phase": "mock_run",
                        "message": "Invalid JSON body.",
                        "is_terminal": True,
                        "progress": 0,
                        "updated_by": "task-intake-api",
                    },
                    "validation": {
                        "valid": False,
                        "errors": ["Invalid JSON body."],
                        "warnings": [],
                    },
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        result = create_mock_run(data)

        if result.get("ok") is True:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 400, body)
        return

    if method == "POST" and path == "/runs/execute":
        # Read body
        body_bytes = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] == "http.request":
                body_bytes += event.get("body", b"")
                more_body = event.get("more_body", False)

        # Parse JSON
        try:
            data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            await _send_json(
                send, 400,
                json.dumps({
                    "ok": False,
                    "errors": [{"code": "invalid_json", "message": "Invalid JSON body."}],
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        # Map "task" field to "raw_task" if raw_task is not set
        if isinstance(data, dict) and "task" in data and not data.get("raw_task"):
            data = dict(data)
            data["raw_task"] = data.pop("task")

        result = run_mock_execution_handoff(data)

        if result.get("ok") is True:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 400, body)
        return

    if method == "POST" and path == "/mock-loop":
        # Read body
        body_bytes = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] == "http.request":
                body_bytes += event.get("body", b"")
                more_body = event.get("more_body", False)

        # Parse JSON
        try:
            data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            await _send_json(
                send, 400,
                json.dumps({
                    "ok": False,
                    "validation": {
                        "valid": False,
                        "errors": ["Invalid JSON body."],
                        "warnings": [],
                    },
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        result = run_mock_loop(data)

        if result.get("ok") is True:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 400, body)
        return

    if method == "GET" and path == "/":
        html = _HTML_PAGE.encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/html; charset=utf-8"),
                (b"content-length", str(len(html)).encode("utf-8")),
            ],
        })
        await send({"type": "http.response.body", "body": html})
        return

    # --- 404 ---
    body = json.dumps({"error": "Not Found"}, ensure_ascii=False).encode("utf-8")
    await _send_json(send, 404, body)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _send_json(send: callable, status: int, body: bytes) -> None:
    """Send a JSON response."""
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            (b"content-type", _CONTENT_TYPE_JSON.encode("utf-8")),
            (b"content-length", str(len(body)).encode("utf-8")),
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })


# ---------------------------------------------------------------------------
# HTML page for local interaction at GET /
# ---------------------------------------------------------------------------

_HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ariadne — Local Interaction</title>
<style>
body { font-family: sans-serif; margin: 2rem; }
pre { background: #f5f5f5; padding: 1rem; overflow-x: auto; }
.status-completed { color: #0a0; font-weight: bold; }
.status-requires_review, .status-blocked { color: #a50; font-weight: bold; }
.status-failed, .status-error { color: #a00; font-weight: bold; }
.ok-true { color: #0a0; }
.ok-false { color: #a00; }
.section { margin-top: 1rem; border: 1px solid #ddd; padding: 0.5rem; }
.section h3 { margin: 0 0 0.5rem; cursor: pointer; }
.section-content { margin-left: 1rem; }
#explanation { background: #e8f4f8; padding: 0.5rem 1rem; margin-bottom: 1rem; border-left: 4px solid #4a90d9; }
#explanation p { margin: 0.3rem 0; }
#summary-card { background: #f9f9f9; border: 1px solid #ccc; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
#summary-card h3 { margin: 0 0 0.5rem 0; }
.summary-field { margin: 0.3rem 0; }
.summary-label { font-weight: bold; display: inline-block; min-width: 10rem; }
.trace-step { display: flex; align-items: center; padding: 0.4rem 0; border-bottom: 1px solid #eee; }
.trace-step:last-child { border-bottom: none; }
.trace-indicator { font-size: 1.2rem; width: 2rem; text-align: center; }
.trace-label { flex: 1; margin-left: 0.5rem; }
.trace-detail { color: #555; font-size: 0.9rem; margin-left: 0.5rem; }
.history-entry { display: flex; align-items: center; padding: 0.3rem 0; border-bottom: 1px solid #eee; font-size: 0.9rem; }
.history-entry:last-child { border-bottom: none; }
.history-index { font-weight: bold; min-width: 2.5rem; }
.history-status { min-width: 7rem; }
.history-task { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin: 0 0.5rem; }
.history-runner { min-width: 7rem; color: #555; }
.history-time { min-width: 12rem; color: #888; font-size: 0.8rem; }
#run-history-placeholder { color: #888; font-style: italic; }
#clear-history-btn { margin-bottom: 0.5rem; }
</style>
</head>
<body>
<h1>Ariadne — Local Interaction</h1>
<div id="explanation">
<p>Ariadne turns your task into an execution request.</p>
<p>The local harness dispatches the request to a selected runner adapter.</p>
<p><strong>Default mode is deterministic local/no-op.</strong> No real agent execution happens by default.</p>
<p>Docker agent is an explicit opt-in boundary. Selecting it returns a structured result without running Docker.</p>
<p>The response includes execution result, execution envelope, and review boundary.</p>
</div>
<fieldset id="scenarios">
<legend>Guided scenarios</legend>
<p>Click a scenario to prefill the task and runner, then click Submit.</p>
<div id="scenario-buttons">
<button onclick="fillScenario('noop','Implement a JWT authentication middleware for FastAPI')">1. Default local/no-op run</button>
<button onclick="fillScenario('noop','Add input validation to all API endpoints')">2. Inspect summary and trace</button>
<button onclick="fillScenario('docker-agent','Run unit tests on the authentication module')">3. Docker-agent opt-in boundary</button>
<button onclick="fillScenario('noop','Create a health check endpoint')">4. Generate user-test feedback</button>
</div>
</fieldset>
<fieldset id="runner-selection">
<legend>Runner adapter</legend>
<label><input type="radio" name="runner" value="noop" checked> Local deterministic / no-op (default)</label>
<br>
<label><input type="radio" name="runner" value="docker-agent"> Docker agent (opt-in — does not run Docker)</label>
</fieldset>
<label for="task">Task:</label>
<textarea id="task" rows="4" cols="60" placeholder="Describe your task…">Implement JWT authentication middleware</textarea>
<br>
<button id="submit">Submit</button>
<div id="status-bar" style="margin-top:0.5rem;"></div>
<div id="result">
<h2>Result</h2>
<div id="summary-card">
<h3>Ariadne Local Run Summary</h3>
<p id="summary-placeholder">Submit a task to see the run summary.</p>
</div>
<div id="run-report-section" style="display:none;">
<h2>Run Report</h2>
<p id="run-report-placeholder" style="display:none;">Run a task to generate a run report.</p>
<button id="generate-run-report-btn">Generate run report</button>
<button id="copy-run-report-btn" style="margin-left:0.5rem;">Copy report</button>
<button id="download-run-report-btn" style="margin-left:0.5rem;">Download report (.txt)</button>
<textarea id="run-report-output" rows="10" cols="80" readonly style="margin-top:0.5rem; display:block; width:100%;"></textarea>
</div>
<div id="run-history-section">
<h2>Run History</h2>
<p id="run-history-placeholder">No runs yet. Submit a task to see your run history.</p>
<button id="clear-history-btn" style="display:none;">Clear history</button>
<div id="run-history-list"></div>
</div>
<div id="execution-trace-section">
<h3>Execution Trace</h3>
<div id="trace-steps"></div>
</div>
<div id="structured-view"></div>
<h3>Raw JSON</h3>
<pre id="json"></pre>
</div>
<div id="feedback-panel">
<h2>User Test Feedback</h2>
<fieldset>
<legend>1. Did you understand what Ariadne does?</legend>
<label><input type="radio" name="q_understood" value="yes"> Yes</label>
<label><input type="radio" name="q_understood" value="no"> No</label>
</fieldset>
<fieldset>
<legend>2. Was runner selection clear?</legend>
<label><input type="radio" name="q_runner_clear" value="yes"> Yes</label>
<label><input type="radio" name="q_runner_clear" value="no"> No</label>
</fieldset>
<fieldset>
<legend>3. Was the summary card clear?</legend>
<label><input type="radio" name="q_summary_clear" value="yes"> Yes</label>
<label><input type="radio" name="q_summary_clear" value="no"> No</label>
</fieldset>
<fieldset>
<legend>4. Was the execution trace useful?</legend>
<label><input type="radio" name="q_trace_useful" value="yes"> Yes</label>
<label><input type="radio" name="q_trace_useful" value="no"> No</label>
</fieldset>
<fieldset>
<legend>5. What was confusing?</legend>
<textarea id="q_confusing" rows="3" cols="60" placeholder="Describe what was confusing…"></textarea>
</fieldset>
<fieldset>
<legend>6. What would you expect Ariadne to do next?</legend>
<textarea id="q_expect_next" rows="3" cols="60" placeholder="Describe your expectation…"></textarea>
</fieldset>
<fieldset>
<legend>Additional notes</legend>
<textarea id="feedback_notes" rows="3" cols="60" placeholder="Optional additional notes…"></textarea>
</fieldset>
<button id="generate-feedback-btn">Generate &amp; copy feedback</button>
<textarea id="feedback-output" rows="6" cols="80" readonly style="margin-top:0.5rem; display:none;"></textarea>
<hr>
<button id="generate-session-report-btn">Generate session report</button>
<button id="copy-report-btn" style="margin-left:0.5rem;">Copy report</button>
<textarea id="session-report-output" rows="10" cols="80" readonly style="margin-top:0.5rem; display:block; width:100%;"></textarea>
</div>
<script>
var TRACE_STEPS = [
    {label: "Task received", field: null, complete: true},
    {label: "Execution request built", field: "execution_request.execution_request_id"},
    {label: "Handoff prepared", field: "handoff_id"},
    {label: "Local harness invoked", field: "execution_envelope.envelope_id"},
    {label: "Runner selected: ", field: "execution_result.adapter"},
    {label: "Execution result returned", field: "execution_result.status"},
    {label: "Execution envelope created", field: "execution_envelope.envelope_id"},
    {label: "Review boundary derived", field: "review_boundary.decision"},
];
var __ariadne_run_history = [];
function get(obj, path, def) {
    try {
        var parts = path.split(".");
        var cur = obj;
        for (var i = 0; i < parts.length; i++) {
            if (cur == null || typeof cur === "undefined") return def;
            cur = cur[parts[i]];
        }
        return cur != null ? cur : def;
    } catch (e) { return def; }
}
function val(v, def) { return (v != null && v !== undefined) ? v : (def != null ? def : "—"); }
function boolSpan(v) { return "<span class=\"" + (v ? "ok-true\">true" : "ok-false\">false") + "</span>"; }
function listItems(arr) {
    if (!arr || arr.length === 0) return "<em>none</em>";
    var html = "<ul>";
    for (var i = 0; i < arr.length; i++) {
        var item = arr[i];
        if (typeof item === "object") html += "<li>" + JSON.stringify(item) + "</li>";
        else html += "<li>" + val(item) + "</li>";
    }
    return html + "</ul>";
}
function keyValue(key, value) {
    return "<p><strong>" + key + ":</strong> " + value + "</p>";
}
function section(title, content) {
    return "<div class=\"section\">"
        + "<h3 onclick=\"var n=this.nextElementSibling; n.style.display=n.style.display==='none'?'':'none';\">"
        + title + "</h3>"
        + "<div class=\"section-content\">" + content + "</div></div>";
}
function renderSummaryCard(data) {
    var adapter = get(data, "execution_request.requested_adapter", "unknown");
    var runtimeStatus = get(data, "runtime_status", "unknown");
    var execStatus = get(data, "execution_result.status", "unknown");
    var reviewDec = get(data, "review_boundary.decision", "unknown");
    var evCount = get(data, "execution_envelope.evidence", []).length;
    var ok = get(data, "ok", false);
    var isNoop = adapter.indexOf("noop") >= 0;
    var requiresReview = get(data, "review_boundary.requires_review", false);
    var whatHappened = "";
    if (runtimeStatus === "completed" && isNoop)
        whatHappened = "Deterministic local/no-op run completed. No real execution was performed.";
    else if (runtimeStatus === "completed" && !isNoop)
        whatHappened = "Docker opt-in boundary \u2014 completed without Docker. Enable Docker with allow_docker=True to execute.";
    else if (runtimeStatus === "blocked")
        whatHappened = "Execution was blocked. Review the review boundary section for details.";
    else if (runtimeStatus === "requires_review")
        whatHappened = "Execution completed but requires human review. See review boundary for details.";
    else if (runtimeStatus === "failed")
        whatHappened = "Execution failed. Check the errors section for details.";
    else if (runtimeStatus === "error")
        whatHappened = "An error occurred. Check the errors section for details.";
    else
        whatHappened = "Run completed (" + runtimeStatus + ").";
    var nextStep = "";
    if (requiresReview) nextStep = "Human review is required before proceeding.";
    else if (ok) nextStep = "Inspect the structured sections below for details, or review the raw JSON output.";
    else nextStep = "Review the errors and warnings sections below to resolve the issue.";
    return "<h3>Ariadne Local Run Summary</h3>"
        + "<div class=\"summary-field\"><span class=\"summary-label\">Selected runner:</span> " + adapter + "</div>"
        + "<div class=\"summary-field\"><span class=\"summary-label\">What happened:</span> " + whatHappened + "</div>"
        + "<div class=\"summary-field\"><span class=\"summary-label\">Runtime status:</span> <span class=\"status-" + runtimeStatus + "\">" + runtimeStatus + "</span></div>"
        + "<div class=\"summary-field\"><span class=\"summary-label\">Execution result:</span> <span class=\"status-" + execStatus + "\">" + execStatus + "</span></div>"
        + "<div class=\"summary-field\"><span class=\"summary-label\">Review decision:</span> <span class=\"status-" + reviewDec + "\">" + reviewDec + "</span></div>"
        + "<div class=\"summary-field\"><span class=\"summary-label\">Evidence:</span> " + evCount + " evidence record(s)</div>"
        + "<div class=\"summary-field\"><span class=\"summary-label\">Next step:</span> " + nextStep + "</div>";
}
function renderTrace(data) {
    var html = "";
    for (var i = 0; i < TRACE_STEPS.length; i++) {
        var step = TRACE_STEPS[i];
        var indicator = "\u2b1c";
        var detail = "";
        if (data) {
            if (i === 4) {
                var adapter = get(data, step.field, "");
                detail = adapter ? adapter : "";
                indicator = detail ? "\u2705" : "\u274c";
            } else if (i === 0) {
                indicator = "\u2705";
            } else if (step.field) {
                var value = get(data, step.field, null);
                indicator = value ? "\u2705" : "\u274c";
                if (i === 7 && value) detail = value;
            }
        }
        var label = step.label;
        if (i === 4 && detail) label = "Runner selected: <strong>" + detail + "</strong>";
        var detailHtml = detail && i !== 4 && i !== 7 ? "<span class=\"trace-detail\">" + detail + "</span>" : "";
        if (i === 7 && detail) detailHtml = "<span class=\"trace-detail\">" + detail + "</span>";
        html += "<div class=\"trace-step\">"
            + "<span class=\"trace-indicator\">" + indicator + "</span>"
            + "<span class=\"trace-label\">" + label + "</span>"
            + detailHtml + "</div>";
    }
    return html;
}
function renderStructured(data) {
    var html = "";
    var status = get(data, "runtime_status", "unknown");
    var ok = get(data, "ok", false);
    html += section("Status",
        keyValue("OK", boolSpan(ok))
        + "<p><strong>Runtime status:</strong> <span class=\"status-" + status + "\">" + val(status) + "</span></p>"
    );
    var er = get(data, "execution_request", {});
    html += section("Execution Request",
        keyValue("Execution request ID", val(get(er, "execution_request_id")))
        + keyValue("Run ID", val(get(er, "run_id")))
        + keyValue("Requested adapter", val(get(er, "requested_adapter")))
        + keyValue("Execution mode", val(get(er, "execution_mode")))
        + keyValue("Task goal", val(get(er, "inputs.task_goal"), ""))
    );
    var eres = get(data, "execution_result", {});
    html += section("Execution Result",
        keyValue("Result ID", val(get(eres, "execution_result_id")))
        + "<p><strong>Status:</strong> <span class=\"status-" + get(eres, "status", "") + "\">" + val(get(eres, "status")) + "</span></p>"
        + keyValue("Adapter", val(get(eres, "adapter")))
        + keyValue("Review required", boolSpan(get(eres, "review_required", false)))
        + keyValue("Evidence count", val(get(eres, "evidence", []).length))
    );
    var env = get(data, "execution_envelope", {});
    html += section("Execution Envelope",
        keyValue("Envelope ID", val(get(env, "envelope_id")))
        + "<p><strong>Status:</strong> <span class=\"status-" + get(env, "status", "") + "\">" + val(get(env, "status")) + "</span></p>"
        + keyValue("Schema version", val(get(env, "schema_version")))
        + keyValue("Artifact count", val(get(env, "artifacts", []).length))
        + keyValue("Evidence count", val(get(env, "evidence", []).length))
    );
    var rb = get(data, "review_boundary", {});
    html += section("Review Boundary",
        "<p><strong>Decision:</strong> <span class=\"status-" + get(rb, "decision", "") + "\">" + val(get(rb, "decision")) + "</span></p>"
        + keyValue("Completed", boolSpan(get(rb, "completed", false)))
        + keyValue("Requires review", boolSpan(get(rb, "requires_review", false)))
        + keyValue("Blocked", boolSpan(get(rb, "blocked", false)))
        + keyValue("Failed", boolSpan(get(rb, "failed", false)))
        + keyValue("Reason code", val(get(rb, "reason_code")))
        + "<p><strong>Reasons:</strong></p>" + listItems(get(rb, "reasons", []))
    );
    var warns = get(data, "warnings", []);
    var errs = get(data, "errors", []);
    if (warns.length > 0 || errs.length > 0) {
        var weHtml = "";
        if (warns.length > 0) weHtml += "<h4>Warnings</h4>" + listItems(warns);
        if (errs.length > 0) weHtml += "<h4>Errors</h4>" + listItems(errs);
        html += section("Warnings &amp; Errors", weHtml);
    }
    return html;
}
function fillScenario(runnerValue, taskText) {
    document.getElementById("task").value = taskText;
    window.__ariadne_last_scenario = taskText;
    var radios = document.querySelectorAll('input[name="runner"]');
    for (var i = 0; i < radios.length; i++) {
        radios[i].checked = (radios[i].value === runnerValue);
    }
}
document.getElementById("submit").addEventListener("click", async function () {
    var task = document.getElementById("task").value;
    if (!task) { alert("Task text is required."); return; }
    var runner = document.querySelector('input[name="runner"]:checked');
    var runnerValue = runner ? runner.value : "noop";
    document.getElementById("status-bar").textContent = "Running…";
    document.getElementById("trace-steps").innerHTML = renderTrace(null);
    try {
        var body = {task: task, requested_adapter: runnerValue};
        var resp = await fetch("/runs/execute", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body),
        });
        var data = await resp.json();
        document.getElementById("status-bar").innerHTML =
            "<span class=\"status-" + (get(data, "runtime_status", "unknown")) + "\">"
            + (get(data, "runtime_status", "unknown")) + "</span>";
        document.getElementById("summary-card").innerHTML = renderSummaryCard(data);
        document.getElementById("run-report-section").style.display = "";
        window._latestData = data;
        pushRunHistory(data);
        document.getElementById("trace-steps").innerHTML = renderTrace(data);
        document.getElementById("structured-view").innerHTML = renderStructured(data);
        document.getElementById("json").textContent = JSON.stringify(data, null, 2);
    } catch (e) {
        document.getElementById("status-bar").textContent = "Error: " + e.message;
    }
});
document.getElementById("generate-feedback-btn").addEventListener("click", generateFeedback);
function generateFeedback() {
    var data = window._latestData || {};
    var adapter = get(data, "execution_request.requested_adapter", "no run submitted");
    var rt = get(data, "runtime_status", "no run submitted");
    var eres = get(data, "execution_result.status", "no run submitted");
    var rb = get(data, "review_boundary.decision", "no run submitted");
    var g = function(n) {
        var sel = document.querySelector('input[name="' + n + '"]:checked');
        return sel ? sel.value : "not answered";
    };
    var text = "=== Ariadne Local User Test Feedback ===\n\n";
    text += "Run summary:\n";
    text += "  Selected runner: " + adapter + "\n";
    text += "  Runtime status: " + rt + "\n";
    text += "  Execution result: " + eres + "\n";
    text += "  Review decision: " + rb + "\n\n";
    text += "Questions:\n";
    text += "  1. Did you understand what Ariadne does? " + g("q_understood") + "\n";
    text += "  2. Was runner selection clear? " + g("q_runner_clear") + "\n";
    text += "  3. Was the summary card clear? " + g("q_summary_clear") + "\n";
    text += "  4. Was the execution trace useful? " + g("q_trace_useful") + "\n";
    text += "  5. What was confusing? " + (document.getElementById("q_confusing").value || "(none)") + "\n";
    text += "  6. What would you expect Ariadne to do next? " + (document.getElementById("q_expect_next").value || "(none)") + "\n";
    text += "\nAdditional notes: " + (document.getElementById("feedback_notes").value || "(none)");
    var output = document.getElementById("feedback-output");
    output.value = text;
    output.style.display = "";
    try {
        navigator.clipboard.writeText(text);
    } catch (e) {
        output.focus();
        output.select();
    }
}
function generateSessionReport() {
    var data = window._latestData || {};
    var scenarioName = window.__ariadne_last_scenario || "Manual";
    var taskText = document.getElementById("task").value || "(empty)";
    var runner = document.querySelector('input[name="runner"]:checked');
    var runnerValue = runner ? runner.value : "noop";
    var adapter = get(data, "execution_request.requested_adapter", "not submitted");
    var rt = get(data, "runtime_status", "not submitted");
    var eres = get(data, "execution_result.status", "not submitted");
    var rb = get(data, "review_boundary.decision", "not submitted");
    var g = function(n) {
        var sel = document.querySelector('input[name="' + n + '"]:checked');
        return sel ? sel.value : "not answered";
    };
    var ts = new Date().toISOString();
    var text = "=== Ariadne User Test Session Report ===\n\n";
    text += "Scenario: " + scenarioName + "\n";
    text += "Submitted task: " + taskText + "\n";
    text += "Selected runner: " + runnerValue + "\n";
    text += "Runtime status: " + rt + "\n";
    text += "Execution result: " + eres + "\n";
    text += "Review decision: " + rb + "\n\n";
    text += "Tester feedback:\n";
    text += "  Understood: " + g("q_understood") + "\n";
    text += "  Runner clear: " + g("q_runner_clear") + "\n";
    text += "  Summary clear: " + g("q_summary_clear") + "\n";
    text += "  Trace useful: " + g("q_trace_useful") + "\n";
    text += "  Confusing: " + (document.getElementById("q_confusing").value || "(none)") + "\n";
    text += "  Expected next: " + (document.getElementById("q_expect_next").value || "(none)") + "\n";
    text += "  Additional notes: " + (document.getElementById("feedback_notes").value || "(none)") + "\n\n";
    text += "Session generated locally in browser at: " + ts + "\n";
    text += "No data was sent to any server.\n";
    document.getElementById("session-report-output").value = text;
}
document.getElementById("generate-session-report-btn").addEventListener("click", generateSessionReport);
document.getElementById("copy-report-btn").addEventListener("click", function() {
    var ta = document.getElementById("session-report-output");
    try { navigator.clipboard.writeText(ta.value); } catch (e) { ta.focus(); ta.select(); }
});
document.getElementById("generate-run-report-btn").addEventListener("click", generateRunReport);
document.getElementById("copy-run-report-btn").addEventListener("click", function() {
    var ta = document.getElementById("run-report-output");
    try { navigator.clipboard.writeText(ta.value); } catch (e) { ta.focus(); ta.select(); }
});
document.getElementById("clear-history-btn").addEventListener("click", clearRunHistory);
document.getElementById("download-run-report-btn").addEventListener("click", function() {
    var ta = document.getElementById("run-report-output");
    var text = ta.value;
    if (!text) return;
    var blob = new Blob([text], {type: "text/plain"});
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "ariadne-run-report.txt";
    a.click();
    URL.revokeObjectURL(url);
});
function generateRunReport() {
    var data = window._latestData || {};
    var taskText = document.getElementById("task").value || "(empty)";
    var runner = document.querySelector('input[name="runner"]:checked');
    var runnerValue = runner ? runner.value : "noop";
    var adapter = get(data, "execution_request.requested_adapter", "not submitted");
    var rt = get(data, "runtime_status", "not submitted");
    var eres = get(data, "execution_result.status", "not submitted");
    var rb = get(data, "review_boundary.decision", "not submitted");
    var summary = get(data, "review_boundary.completed", false) ? "completed" : get(data, "review_boundary.decision", "...");
    var ts = new Date().toISOString();
    var text = "=== Ariadne Local Run Report ===\n\n";
    text += "Submitted task: " + taskText + "\n";
    text += "Selected runner: " + runnerValue + "\n";
    text += "Runtime status: " + rt + "\n";
    text += "Execution result: " + eres + "\n";
    text += "Review decision: " + rb + "\n";
    text += "Summary card: " + summary + "\n\n";
    text += "=== Execution Trace ===\n";
    var traceAdap = get(data, "execution_result.adapter", "") || "—";
    var traceEnvId = get(data, "execution_envelope.envelope_id", "") || "—";
    text += "1. Task received \u2705\n";
    text += "2. Execution request built \u2705\n";
    text += "3. Handoff prepared \u2705\n";
    text += "4. Local harness invoked \u2705\n";
    text += "5. Runner selected: " + traceAdap + "\n";
    text += "6. Execution result returned: " + eres + "\n";
    text += "7. Execution envelope created: " + traceEnvId + "\n";
    text += "8. Review boundary derived: " + rb + "\n\n";
    var understood = document.querySelector('input[name="q_understood"]:checked');
    if (understood) {
        var g = function(n) {
            var s = document.querySelector('input[name="' + n + '"]:checked');
            return s ? s.value : "not answered";
        };
        text += "=== Related feedback ===\n";
        text += "Understood: " + g("q_understood") + "\n";
        text += "Runner clear: " + g("q_runner_clear") + "\n";
        text += "Summary clear: " + g("q_summary_clear") + "\n";
        text += "Trace useful: " + g("q_trace_useful") + "\n";
        text += "Notes: " + (document.getElementById("feedback_notes").value || "(none)") + "\n\n";
    }
    text += "Generated in browser at: " + ts + "\n";
    text += "No data was sent to any server.\n";
    document.getElementById("run-report-output").value = text;
}
function pushRunHistory(data) {
    var taskText = document.getElementById("task").value || "(empty)";
    var runner = document.querySelector('input[name="runner"]:checked');
    var runnerValue = runner ? runner.value : "noop";
    var status = get(data, "runtime_status", "unknown");
    var ts = new Date().toISOString();
    __ariadne_run_history.push({
        task: taskText,
        runner: runnerValue,
        status: status,
        timestamp: ts,
    });
    if (__ariadne_run_history.length > 10) {
        __ariadne_run_history.shift();
    }
    renderRunHistory();
}
function renderRunHistory() {
    var placeholder = document.getElementById("run-history-placeholder");
    var list = document.getElementById("run-history-list");
    var clearBtn = document.getElementById("clear-history-btn");
    if (__ariadne_run_history.length === 0) {
        placeholder.style.display = "";
        list.innerHTML = "";
        clearBtn.style.display = "none";
        return;
    }
    placeholder.style.display = "none";
    clearBtn.style.display = "";
    var html = "";
    var total = __ariadne_run_history.length;
    for (var i = total - 1; i >= 0; i--) {
        var entry = __ariadne_run_history[i];
        var idx = total - i;
        var taskDisplay = entry.task.length > 60 ? entry.task.substring(0, 60) + "…" : entry.task;
        html += "<div class=\"history-entry\">"
            + "<span class=\"history-index\">#" + idx + "</span>"
            + "<span class=\"history-status status-" + entry.status + "\">" + entry.status + "</span>"
            + "<span class=\"history-task\" title=\"" + entry.task.replace(/"/g, "&quot;") + "\">" + taskDisplay + "</span>"
            + "<span class=\"history-runner\">" + entry.runner + "</span>"
            + "<span class=\"history-time\">" + entry.timestamp + "</span>"
            + "</div>";
    }
    list.innerHTML = html;
}
function clearRunHistory() {
    __ariadne_run_history = [];
    renderRunHistory();
}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Expose app title for PLAN import check
# ---------------------------------------------------------------------------

title = "Task Intake API"

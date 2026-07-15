"""Task Intake HTTP server — minimal stdlib ASGI application.

Exposes the Task Intake service via HTTP endpoints.
This is intake-only.  It does not invoke the runner, orchestrate agents,
create run records, or write to ``.ariadne/**``.
"""

from __future__ import annotations

import json
import os
from urllib.parse import parse_qs
import re

from task_intake.app import accept_task
from task_intake.backlog_decision import BacklogDecisionInput, record_human_decision
from task_intake.backlog_review import BacklogReviewInput, build_backlog_review_json
from task_intake.decision_history import DecisionHistoryInput, load_decision_history
from task_intake.decision_backlog_trace_summary import DecisionTraceInput, build_decision_trace
from task_intake.doctor import doctor
from task_intake.product_iteration import (
    ProductIterationInput,
    ProductIterationStatus,
    record_product_iteration_signal,
    list_product_iteration_signals,
)
from task_intake.product_iteration_surface import (
    generate_session_ref,
    record_session_signal,
)
from task_intake.product_iteration_review_packet import (
    ProductIterationReviewPacketStatus,
    build_product_iteration_review_packet,
)
from task_intake.models import TaskIntakeRequest
from task_intake.normalize import normalize_task_intake
from task_intake.context_preview import generate_context_preview
from task_intake.runs import create_mock_run
from runner.runtime_evidence import list_run_evidence_summaries
from runner.runtime_evidence import read_run_evidence_detail
from task_intake.runtime_evidence_serialization import (
    EVIDENCE_CONTRACT_VERSION,
    serialize_run_evidence_detail,
    serialize_run_index,
)
from task_intake.artifact_workspace import render_artifact_workspace

# Safe run_id pattern: alphanumeric, underscore, hyphen only
_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")
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

    if method == "GET" and path == "/backlog":
        # Parse query parameters
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        status_filter = params.get("status", [None])[0]
        category_filter = params.get("category", [None])[0]
        max_items_str = params.get("max_items", ["0"])[0]
        try:
            max_items = int(max_items_str)
        except (ValueError, TypeError):
            max_items = 0

        inp = BacklogReviewInput(
            status_filter=status_filter,
            category_filter=category_filter,
            max_items=max_items,
        )
        result = build_backlog_review_json(inp)
        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        await _send_json(send, 200, body)
        return

    if method == "POST" and path == "/backlog":
        # Read body
        body_bytes = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] == "http.request":
                body_bytes += event.get("body", b"")
                more_body = event.get("more_body", False)

        # Parse JSON body for optional filter overrides
        try:
            data = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            await _send_json(
                send, 400,
                json.dumps({
                    "status": "rejected",
                    "read_only": True,
                    "reason_codes": ["invalid_json_body"],
                    "details": "Invalid JSON body.",
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        if not isinstance(data, dict):
            await _send_json(
                send, 400,
                json.dumps({
                    "status": "rejected",
                    "read_only": True,
                    "reason_codes": ["invalid_json_body"],
                    "details": "Body must be a JSON object.",
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        inp = BacklogReviewInput(
            backlog_store_dir=data.get("backlog_store_dir", ".ariadne/backlog"),
            status_filter=data.get("status_filter"),
            category_filter=data.get("category_filter"),
            max_items=data.get("max_items", 0),
        )
        result = build_backlog_review_json(inp)
        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        await _send_json(send, 200, body)
        return

    if method == "POST" and path == "/backlog/decision":
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
                    "reason_codes": ["invalid_json_body"],
                    "details": "Invalid JSON body.",
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        if not isinstance(data, dict):
            await _send_json(
                send, 400,
                json.dumps({
                    "status": "rejected",
                    "reason_codes": ["invalid_json_body"],
                    "details": "Body must be a JSON object.",
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        inp = BacklogDecisionInput(
            backlog_item_ref=data.get("backlog_item_ref", ""),
            decision_type=data.get("decision_type", ""),
            human_actor=data.get("human_actor", ""),
            decision_reason=data.get("decision_reason", ""),
            decision_store_dir=data.get("decision_store_dir", ".ariadne/decisions"),
            evidence_refs=tuple(data.get("evidence_refs", [])),
            next_human_action=data.get("next_human_action", ""),
            candidate_ref=data.get("candidate_ref", ""),
            continuity_ref=data.get("continuity_ref", ""),
        )
        result = record_human_decision(inp)

        if result.status == "recorded":
            record = result.decision_record
            record_dict = {
                "decision_ref": record.decision_ref,
                "backlog_item_ref": record.backlog_item_ref,
                "decision_type": record.decision_type,
                "human_actor": record.human_actor,
                "decision_reason": record.decision_reason,
                "evidence_refs": list(record.evidence_refs),
                "next_human_action": record.next_human_action,
                "candidate_ref": record.candidate_ref,
                "continuity_ref": record.continuity_ref,
                "created_at": record.created_at,
            } if record else None
            body = json.dumps({
                "status": "recorded",
                "decision_ref": result.decision_ref,
                "decision_record": record_dict,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        elif result.status == "duplicate":
            body = json.dumps({
                "status": "duplicate",
                "decision_ref": result.decision_ref,
                "reason_codes": list(result.reason_codes),
                "details": result.details,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps({
                "status": "rejected",
                "reason_codes": list(result.reason_codes),
                "details": result.details,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        return

    if method == "GET" and path == "/backlog/decision/history":
        # Parse query parameters
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        max_results_str = params.get("max_results", ["100"])[0]
        try:
            max_results = int(max_results_str)
        except (ValueError, TypeError):
            max_results = 100
        backlog_item_ref = params.get("backlog_item_ref", [None])[0]
        decision_type = params.get("decision_type", [None])[0]
        human_actor = params.get("human_actor", [None])[0]
        sort_by = params.get("sort_by", ["created_at"])[0]
        sort_descending_str = params.get("sort_descending", ["true"])[0]
        sort_descending = sort_descending_str.lower() not in ("false", "0", "no")

        inp = DecisionHistoryInput(
            max_results=max_results,
            backlog_item_ref=backlog_item_ref,
            decision_type=decision_type,
            human_actor=human_actor,
            sort_by=sort_by,
            sort_descending=sort_descending,
        )
        result = load_decision_history(inp)

        if result.status == "rejected":
            body = json.dumps({
                "status": "rejected",
                "reason_codes": list(result.reason_codes),
                "details": result.details,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        elif result.status == "empty":
            body = json.dumps({
                "status": "empty",
                "view": {
                    "items": [],
                    "total_count": 0,
                    "summary": {
                        "total_decisions": 0,
                        "decisions_by_type": {},
                        "decisions_by_backlog_item": {},
                        "rejected_or_invalid_decision_records": 0,
                        "human_review_required": 0,
                    },
                },
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            view = result.view
            items_json = []
            if view:
                for item in view.items:
                    items_json.append({
                        "decision_ref": item.decision_ref,
                        "backlog_item_ref": item.backlog_item_ref,
                        "candidate_ref": item.candidate_ref,
                        "continuity_ref": item.continuity_ref,
                        "evidence_refs": list(item.evidence_refs),
                        "human_actor": item.human_actor,
                        "decision_type": item.decision_type,
                        "decision_reason": item.decision_reason,
                        "next_human_action": item.next_human_action,
                        "blocked_agent_actions": list(item.blocked_agent_actions),
                        "created_at": item.created_at,
                        "product_name": item.product_name,
                        "source_surface": item.source_surface,
                        "requires_human_review": item.requires_human_review,
                        "decision_record_path": item.decision_record_path,
                        "linked_backlog_item_status": item.linked_backlog_item_status,
                        "schema_version": item.schema_version,
                    })
                summary = view.summary
                body = json.dumps({
                    "status": "ready",
                    "reason_codes": list(result.reason_codes) if result.reason_codes else [],
                    "view": {
                        "items": items_json,
                        "total_count": view.total_count,
                        "summary": {
                            "total_decisions": summary.total_decisions,
                            "decisions_by_type": summary.decisions_by_type,
                            "decisions_by_backlog_item": summary.decisions_by_backlog_item,
                            "rejected_or_invalid_decision_records": summary.rejected_or_invalid_decision_records,
                            "human_review_required": summary.human_review_required,
                        },
                    },
                }, ensure_ascii=False).encode("utf-8")
            else:
                body = json.dumps({
                    "status": "empty",
                    "view": None,
                }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        return

    if method == "GET" and path == "/backlog/decision/trace":
        # Parse query parameters
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        max_traces_str = params.get("max_traces", ["50"])[0]
        try:
            max_traces = int(max_traces_str)
        except (ValueError, TypeError):
            max_traces = 50
        backlog_item_ref = params.get("backlog_item_ref", [None])[0]
        include_without_decisions_str = params.get("include_backlog_items_without_decisions", ["false"])[0]
        include_without_decisions = include_without_decisions_str.lower() in ("true", "1", "yes")
        sort_by = params.get("sort_by", ["backlog_item_ref"])[0]
        sort_descending_str = params.get("sort_descending", ["false"])[0]
        sort_descending = sort_descending_str.lower() in ("true", "1", "yes")

        inp = DecisionTraceInput(
            max_traces=max_traces,
            backlog_item_ref=backlog_item_ref,
            include_backlog_items_without_decisions=include_without_decisions,
            sort_by=sort_by,
            sort_descending=sort_descending,
        )
        result = build_decision_trace(inp)

        if result.status == "rejected":
            body = json.dumps({
                "status": "rejected",
                "reason_codes": list(result.reason_codes),
                "details": result.details,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        elif result.status == "empty":
            body = json.dumps({
                "status": "empty",
                "traces": [],
                "untraced_decisions": [],
                "summary": {
                    "total_backlog_items": 0,
                    "traced_backlog_items": 0,
                    "backlog_items_without_decisions": 0,
                    "total_decisions": 0,
                    "decisions_without_backlog_item": 0,
                    "total_evidence_refs": 0,
                    "unresolved_traces": 0,
                    "invalid_decision_records": 0,
                    "human_review_required": 0,
                },
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            traces_json = []
            for trace in result.traces:
                decisions_json = []
                for d in trace.decisions:
                    decisions_json.append({
                        "decision_ref": d.decision_ref,
                        "decision_type": d.decision_type,
                        "decision_reason": d.decision_reason,
                        "human_actor": d.human_actor,
                        "created_at": d.created_at,
                        "evidence_refs": list(d.evidence_refs),
                        "next_human_action": d.next_human_action,
                        "blocked_agent_actions": list(d.blocked_agent_actions),
                        "source_surface": d.source_surface,
                        "requires_human_review": d.requires_human_review,
                    })
                traces_json.append({
                    "backlog_item": {
                        "backlog_item_ref": trace.backlog_item.backlog_item_ref,
                        "backlog_status": trace.backlog_item.backlog_status,
                        "backlog_category": trace.backlog_item.backlog_category,
                        "candidate_ref": trace.backlog_item.candidate_ref,
                        "continuity_ref": trace.backlog_item.continuity_ref,
                    },
                    "decisions": decisions_json,
                    "decision_refs": list(trace.decision_refs),
                    "latest_decision_ref": trace.latest_decision_ref,
                    "latest_decision_type": trace.latest_decision_type,
                    "evidence_refs": list(trace.evidence_refs),
                    "missing_evidence_refs": list(trace.missing_evidence_refs),
                    "blocked_agent_actions": list(trace.blocked_agent_actions),
                    "next_safe_human_action": trace.next_safe_human_action,
                    "trace_status": trace.trace_status,
                    "trace_warnings": list(trace.trace_warnings),
                    "requires_human_review": trace.requires_human_review,
                })

            untraced_json = []
            for d in result.untraced_decisions:
                untraced_json.append({
                    "decision_ref": d.decision_ref,
                    "decision_type": d.decision_type,
                    "decision_reason": d.decision_reason,
                    "human_actor": d.human_actor,
                    "created_at": d.created_at,
                    "evidence_refs": list(d.evidence_refs),
                    "next_human_action": d.next_human_action,
                    "blocked_agent_actions": list(d.blocked_agent_actions),
                    "source_surface": d.source_surface,
                    "requires_human_review": d.requires_human_review,
                })

            summary = result.summary
            body = json.dumps({
                "status": result.status,
                "reason_codes": list(result.reason_codes) if result.reason_codes else [],
                "traces": traces_json,
                "untraced_decisions": untraced_json,
                "summary": {
                    "total_backlog_items": summary.total_backlog_items if summary else 0,
                    "traced_backlog_items": summary.traced_backlog_items if summary else 0,
                    "backlog_items_without_decisions": summary.backlog_items_without_decisions if summary else 0,
                    "total_decisions": summary.total_decisions if summary else 0,
                    "decisions_without_backlog_item": summary.decisions_without_backlog_item if summary else 0,
                    "total_evidence_refs": summary.total_evidence_refs if summary else 0,
                    "unresolved_traces": summary.unresolved_traces if summary else 0,
                    "invalid_decision_records": summary.invalid_decision_records if summary else 0,
                    "human_review_required": summary.human_review_required if summary else 0,
                },
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        return

    if method == "POST" and path == "/product/iterations":
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
                    "reason_codes": ["invalid_json_body"],
                    "details": "Invalid JSON body.",
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        if not isinstance(data, dict):
            await _send_json(
                send, 400,
                json.dumps({
                    "status": "rejected",
                    "reason_codes": ["invalid_json_body"],
                    "details": "Body must be a JSON object.",
                }, ensure_ascii=False).encode("utf-8"),
            )
            return

        inp = ProductIterationInput(
            session_ref=data.get("session_ref", ""),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            screen_time_seconds=data.get("screen_time_seconds", 0),
            active_time_seconds=data.get("active_time_seconds", 0),
            idle_time_seconds=data.get("idle_time_seconds", 0),
            run_refs=tuple(data.get("run_refs", [])),
            feedback_refs=tuple(data.get("feedback_refs", [])),
            confusion_refs=tuple(data.get("confusion_refs", [])),
            report_refs=tuple(data.get("report_refs", [])),
            decision_trace_refs=tuple(data.get("decision_trace_refs", [])),
            human_iteration_note=data.get("human_iteration_note", ""),
            source_surface=data.get("source_surface", "task_intake"),
            product_signal_status=data.get("product_signal_status", "recorded"),
            store_dir=data.get("store_dir", ".ariadne/product-iterations"),
        )
        result = record_product_iteration_signal(inp)

        if result.status == ProductIterationStatus.RECORDED:
            record = result.record
            record_dict = {
                "iteration_ref": record.iteration_ref,
                "session_ref": record.session_ref,
                "started_at": record.started_at,
                "ended_at": record.ended_at,
                "screen_time_seconds": record.screen_time_seconds,
                "active_time_seconds": record.active_time_seconds,
                "idle_time_seconds": record.idle_time_seconds,
                "run_refs": list(record.run_refs),
                "feedback_refs": list(record.feedback_refs),
                "confusion_refs": list(record.confusion_refs),
                "report_refs": list(record.report_refs),
                "decision_trace_refs": list(record.decision_trace_refs),
                "human_iteration_note": record.human_iteration_note,
                "product_signal_status": record.product_signal_status,
                "created_at": record.created_at,
                "source_surface": record.source_surface,
                "schema_version": record.schema_version,
            } if record else None
            body = json.dumps({
                "status": "recorded",
                "iteration_ref": result.iteration_ref,
                "record": record_dict,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            body = json.dumps({
                "status": "rejected",
                "reason_codes": list(result.reason_codes),
                "details": result.details,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        return

    if method == "GET" and path == "/product/iterations":
        # Parse query parameters
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        session_ref = params.get("session_ref", [None])[0]
        max_results_str = params.get("max_results", ["100"])[0]
        try:
            max_results = int(max_results_str)
        except (ValueError, TypeError):
            max_results = 100

        result = list_product_iteration_signals(
            session_ref=session_ref,
            max_results=max_results,
        )

        if result.status == ProductIterationStatus.REJECTED:
            body = json.dumps({
                "status": "rejected",
                "reason_codes": list(result.reason_codes),
                "details": result.details,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        elif result.status == ProductIterationStatus.EMPTY:
            body = json.dumps({
                "status": "empty",
                "records": [],
                "total_count": 0,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            records_json = []
            for record in result.records:
                records_json.append({
                    "iteration_ref": record.iteration_ref,
                    "session_ref": record.session_ref,
                    "started_at": record.started_at,
                    "ended_at": record.ended_at,
                    "screen_time_seconds": record.screen_time_seconds,
                    "active_time_seconds": record.active_time_seconds,
                    "idle_time_seconds": record.idle_time_seconds,
                    "run_refs": list(record.run_refs),
                    "feedback_refs": list(record.feedback_refs),
                    "confusion_refs": list(record.confusion_refs),
                    "report_refs": list(record.report_refs),
                    "decision_trace_refs": list(record.decision_trace_refs),
                    "human_iteration_note": record.human_iteration_note,
                    "product_signal_status": record.product_signal_status,
                    "created_at": record.created_at,
                    "source_surface": record.source_surface,
                    "schema_version": record.schema_version,
                })
            body = json.dumps({
                "status": "recorded",
                "records": records_json,
                "total_count": result.total_count,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        return

    if method == "GET" and path == "/product/iterations/review-packet":
        # Parse query parameters
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        session_ref = params.get("session_ref", [None])[0]
        max_results_str = params.get("max_results", ["1000"])[0]
        try:
            max_results = int(max_results_str)
        except (ValueError, TypeError):
            max_results = 1000

        result = build_product_iteration_review_packet(
            session_ref=session_ref,
            max_results=max_results,
        )

        if result.status == ProductIterationReviewPacketStatus.REJECTED:
            body = json.dumps({
                "status": "rejected",
                "reason_codes": list(result.reason_codes),
                "details": result.details,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        elif result.status == ProductIterationReviewPacketStatus.EMPTY:
            body = json.dumps({
                "status": "empty",
                "packet": None,
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        else:
            p = result.packet
            body = json.dumps({
                "status": "ready",
                "packet": {
                    "packet_ref": p.packet_ref,
                    "packet_status": p.packet_status,
                    "generated_from": p.generated_from,
                    "candidate_ref": p.candidate_ref,
                    "candidate_status": p.candidate_status,
                    "priority": p.priority,
                    "confidence": p.confidence,
                    "reason_codes": list(p.reason_codes),
                    "recommended_focus": p.recommended_focus,
                    "human_review_required": p.human_review_required,
                    "evidence_counts": p.evidence_counts,
                    "evidence_highlights": p.evidence_highlights,
                    "recommended_human_questions": list(p.recommended_human_questions),
                    "decision_options": list(p.decision_options),
                    "safety_boundaries": list(p.safety_boundaries),
                    "validation_notes": list(p.validation_notes),
                    "record_count": p.record_count,
                    "session_count": p.session_count,
                    "markdown_text": p.markdown_text,
                    "plain_text": p.plain_text,
                },
            }, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
        return

    # Combined route handler: GET /runs/<run_id>/report and GET /runs/<run_id>
    if method == "GET" and path.startswith("/runs/"):
        is_report = path.endswith("/report")
        if is_report:
            # Report route: GET /runs/<run_id>/report
            run_id = path[len("/runs/"):-len("/report")]
        else:
            # Detail route: GET /runs/<run_id>
            run_id = path[len("/runs/"):]
        # Validate run_id
        if not run_id or not _RUN_ID_RE.match(run_id) or len(run_id) > 128:
            body = json.dumps({
                "ev_contract_version": EVIDENCE_CONTRACT_VERSION,
                "ok": False,
                "error": "invalid_run_id",
            }, sort_keys=True, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
            return

        # Parse optional runs_root query parameter
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        runs_root = params.get("runs_root", [None])[0]
        if not runs_root:
            runs_root = os.path.join(os.getcwd(), ".ariadne", "runs")

        if not os.path.isdir(runs_root):
            body = json.dumps({
                "ev_contract_version": EVIDENCE_CONTRACT_VERSION,
                "ok": False,
                "error": "runs_root not found or unreadable",
            }, sort_keys=True, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
            return

        if is_report:
            # --- Report route: GET /runs/<run_id>/report ---
            run_dir = os.path.join(runs_root, run_id)

            # Check if run directory exists
            if not os.path.isdir(run_dir):
                body = json.dumps({
                    "ev_contract_version": EVIDENCE_CONTRACT_VERSION,
                    "ok": False,
                    "error": "run not found",
                    "run_id": run_id,
                    "content": None,
                    "content_length": 0,
                    "truncated": False,
                    "truncation_limit": None,
                    "report_exists": False,
                    "manifest_lists_report": False,
                    "provenance": (
                        "Report provenance: cannot verify "
                        "— manifest evidence is unavailable."
                    ),
                }, sort_keys=True, ensure_ascii=False).encode("utf-8")
                await _send_json(send, 200, body)
                return

            # --- Provenance: read manifest and run.json ---
            manifest_path = os.path.join(run_dir, "manifest.json")
            run_json_path = os.path.join(run_dir, "run.json")

            manifest_lists_report = False
            manifest_available = False
            manifest_malformed = False
            run_json_available = os.path.exists(run_json_path)

            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest_data = json.load(f)
                    if isinstance(manifest_data, dict):
                        manifest_available = True
                        files = manifest_data.get("files", [])
                        if "run-report.txt" in files:
                            manifest_lists_report = True
                except (json.JSONDecodeError, OSError):
                    manifest_malformed = True

            # Determine provenance text
            if manifest_available and manifest_lists_report and run_json_available:
                provenance = (
                    "run.json and manifest.json exist for this run_id. "
                    "run-report.txt is listed in manifest files."
                )
            elif manifest_malformed:
                provenance = "Report provenance: manifest evidence is malformed."
            else:
                provenance = (
                    "Report provenance: cannot verify "
                    "— manifest evidence is unavailable."
                )

            # --- Read report file ---
            report_path = os.path.join(run_dir, "run-report.txt")
            report_exists = os.path.exists(report_path)

            if not report_exists:
                body = json.dumps({
                    "ev_contract_version": EVIDENCE_CONTRACT_VERSION,
                    "ok": False,
                    "error": "file_not_found",
                    "run_id": run_id,
                    "content": None,
                    "content_length": 0,
                    "truncated": False,
                    "truncation_limit": None,
                    "report_exists": False,
                    "manifest_lists_report": manifest_lists_report,
                    "provenance": provenance,
                }, sort_keys=True, ensure_ascii=False).encode("utf-8")
                await _send_json(send, 200, body)
                return

            # Read report content with 100,001 char max to detect truncation
            content_raw = None
            read_err = None
            truncation_limit = 100000
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    content_raw = f.read(truncation_limit + 1)
            except OSError as e:
                read_err = f"read_error: {e}"

            if read_err is not None:
                body = json.dumps({
                    "ev_contract_version": EVIDENCE_CONTRACT_VERSION,
                    "ok": False,
                    "error": read_err,
                    "run_id": run_id,
                    "content": None,
                    "content_length": 0,
                    "truncated": False,
                    "truncation_limit": None,
                    "report_exists": True,
                    "manifest_lists_report": manifest_lists_report,
                    "provenance": provenance,
                }, sort_keys=True, ensure_ascii=False).encode("utf-8")
                await _send_json(send, 200, body)
                return

            # Determine truncation and slice content
            content_length = len(content_raw)
            truncated = content_length > truncation_limit
            content = content_raw[:truncation_limit] if truncated else content_raw

            body = json.dumps({
                "ev_contract_version": EVIDENCE_CONTRACT_VERSION,
                "ok": True,
                "error": None,
                "run_id": run_id,
                "content": content,
                "content_length": min(content_length, truncation_limit),
                "truncated": truncated,
                "truncation_limit": truncation_limit if truncated else None,
                "report_exists": True,
                "manifest_lists_report": manifest_lists_report,
                "provenance": provenance,
            }, sort_keys=True, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
            return

        # --- Detail route: GET /runs/<run_id> (existing) ---
        result = read_run_evidence_detail(runs_root, run_id)
        response = serialize_run_evidence_detail(result)
        body = json.dumps(response, sort_keys=True, ensure_ascii=False).encode("utf-8")
        await _send_json(send, 200, body)
        return

    if method == "GET" and path == "/runs":
        # Parse optional runs_root query parameter
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        runs_root = params.get("runs_root", [None])[0]
        if not runs_root:
            # Default to .ariadne/runs relative to server working directory
            runs_root = os.path.join(os.getcwd(), ".ariadne", "runs")

        if not os.path.isdir(runs_root):
            response = serialize_run_index(
                summaries=(),
                runs_root=runs_root,
                ok=False,
                error="runs_root not found or unreadable",
            )
            body = json.dumps(response, sort_keys=True, ensure_ascii=False).encode("utf-8")
            await _send_json(send, 200, body)
            return

        summaries = list_run_evidence_summaries(runs_root)
        response = serialize_run_index(summaries=summaries, runs_root=runs_root)
        body = json.dumps(response, sort_keys=True, ensure_ascii=False).encode("utf-8")
        await _send_json(send, 200, body)
        return

    if method == "GET" and path == "/workspace":
        html = render_artifact_workspace().encode("utf-8")
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
.validation-error { color: #d00; font-size: 0.85rem; margin-top: 0.25rem; display: none; }
#error-panel { background: #fdd; border: 1px solid #d00; border-radius: 6px; padding: 0.75rem 1rem; margin-bottom: 1rem; display: none; }
#error-panel h3 { margin: 0 0 0.5rem 0; color: #a00; }
#error-panel p { margin: 0.3rem 0; }
#dismiss-error-btn { margin-top: 0.5rem; }
#submit:disabled { opacity: 0.6; cursor: not-allowed; }
#onboarding-panel { background: #f0f8ff; border: 2px solid #4a90d9; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 1rem; }
#onboarding-panel h2 { margin: 0 0 0.5rem 0; color: #2a5f8a; }
#onboarding-panel p { margin: 0.4rem 0; line-height: 1.5; }
.onboarding-dismiss { float: right; }
.onboarding-steps { padding-left: 1.5rem; margin: 0.5rem 0; }
.onboarding-steps li { margin: 0.3rem 0; line-height: 1.5; }
.checklist-item { padding: 0.25rem 0; }
.checklist-counter { margin: 0.5rem 0; font-weight: bold; }
.checklist-all-passed { color: #0a0; }
.confusion-buttons { margin: 0.5rem 0; display: flex; gap: 0.5rem; flex-wrap: wrap; }
.confusion-btn { padding: 0.4rem 0.75rem; cursor: pointer; }
.confusion-note-area { margin: 0.5rem 0; }
.confusion-note-area textarea { width: 100%; max-width: 40rem; }
.confusion-list { margin: 0.5rem 0; }
.confusion-entry { padding: 0.3rem 0; border-bottom: 1px solid #eee; font-size: 0.9rem; }
.confusion-entry:last-child { border-bottom: none; }
.confusion-type { font-weight: bold; display: inline-block; min-width: 12rem; }
.confusion-note { color: #555; margin-left: 0.5rem; }
.confusion-time { color: #888; font-size: 0.8rem; margin-left: 0.5rem; }
#clear-confusion-btn { margin-top: 0.5rem; }
</style>
</head>
<body>
<h1>Ariadne — Local Interaction</h1>
<div id="onboarding-panel">
<button class="onboarding-dismiss" id="dismiss-onboarding-btn">Dismiss</button>
<h2>Welcome to Ariadne</h2>
<p>Ariadne is a local execution substrate for agentic software development.</p>
<p>It accepts a task, builds an execution request, dispatches it through a selected runner, and returns a deterministic result with an execution envelope and review boundary.</p>
<p><strong>Local/no-op runner (default):</strong> A deterministic simulation that returns results without executing any real work. No Docker daemon, no process spawning, no network calls.</p>
<p><strong>Docker agent runner (opt-in):</strong> A boundary that runs tasks in a Docker container. Must be explicitly selected. Selecting it returns a structured blocked result without running Docker — enabling real execution requires additional configuration.</p>
<p>After submitting a task, inspect the summary card, execution trace, structured result, and raw JSON.</p>
<p>Use the feedback panel to capture your observations.</p>
<h3>Step-by-step local flow</h3>
<ol class="onboarding-steps">
<li>Select a guided scenario or type your own task.</li>
<li>Choose a runner (local/no-op default, docker-agent opt-in).</li>
<li>Click Submit.</li>
<li>Inspect the summary card, execution trace, and structured result.</li>
<li>Use the feedback panel to record observations.</li>
<li>Generate and copy a run report.</li>
</ol>
</div>
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
<label><input type="radio" name="runner" value="docker-agent"> Docker agent (opt-in)</label>
<br>
<label><input type="checkbox" id="allow-docker-checkbox"> Enable real Docker execution (requires ARIADNE_ALLOW_DOCKER_EXECUTION environment variable)</label>
</fieldset>
<label for="task">Task:</label>
<textarea id="task" rows="4" cols="60" placeholder="Describe your task…">Implement JWT authentication middleware</textarea>
<div id="task-validation" class="validation-error">Task text is required.</div>
<br>
<button id="submit">Submit</button>
<div id="error-panel">
<h3>Request Error</h3>
<p id="error-message"></p>
<button id="dismiss-error-btn">Dismiss</button>
</div>
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
<div id="run-detail-panel" style="display:none;">
<h2>Run Detail</h2>
<p><strong>Selected run:</strong> <span id="detail-run-id"></span></p>
<div id="run-detail-content"></div>
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
<div id="manual-checklist">
<h3>Manual Acceptance Checklist</h3>
<p class="checklist-counter" id="checklist-counter">0/15 checked</p>
<button id="reset-checklist-btn">Reset all</button>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 1. First-time onboarding is visible and understandable</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 2. Scenario can be selected (task prefilled, runner set)</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 3. Task can be submitted</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 4. Local/no-op remains default</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 5. Docker-agent remains opt-in and non-default</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 6. Summary card is visible after run</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 7. Execution trace is visible after run</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 8. Structured result is visible after run</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 9. Raw JSON remains available</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 10. Feedback can be captured</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 11. Session report can be generated</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 12. Run report can be copied/exported</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 13. Local run history updates</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 14. Empty task validation works (inline message shown)</label></div>
<div class="checklist-item"><label><input type="checkbox" onchange="updateChecklistCounter()" class="checklist-cb"> 15. Error state preserves previous run and history</label></div>
</div>
<div id="confusion-signals-panel">
<h3>Confusion Signals</h3>
<p>Click a button to record a moment of confusion.</p>
<div class="confusion-buttons">
<button class="confusion-btn" onclick="addConfusionSignal('unclear_next_step')">Unclear next step</button>
<button class="confusion-btn" onclick="addConfusionSignal('unexpected_result')">Unexpected result</button>
<button class="confusion-btn" onclick="addConfusionSignal('runner_confusion')">Runner confusion</button>
<button class="confusion-btn" onclick="addConfusionSignal('report_export_confusion')">Report/export confusion</button>
</div>
<div class="confusion-note-area">
<label for="confusion-note-input">Optional note (applied to last/next signal):</label>
<br>
<textarea id="confusion-note-input" rows="2" cols="60" placeholder="What were you confused about? (optional)"></textarea>
</div>
<button id="clear-confusion-btn">Clear all signals</button>
<div id="confusion-signal-list" class="confusion-list"></div>
</div>
<fieldset>
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
<hr>
<h3>Product Iteration Session Capture</h3>
<p>Record a product iteration signal with current session data.</p>
<button id="record-session-btn">Record session signal</button>
<span id="session-status" style="margin-left:0.5rem;"></span>
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
var __onboarding_dismissed = false;
var __ariadne_confusion_signals = [];
function dismissOnboarding() {
    __onboarding_dismissed = true;
    document.getElementById("onboarding-panel").style.display = "none";
}
function updateChecklistCounter() {
    var cbs = document.querySelectorAll(".checklist-cb");
    var checked = 0;
    for (var i = 0; i < cbs.length; i++) {
        if (cbs[i].checked) checked++;
    }
    var el = document.getElementById("checklist-counter");
    if (checked === 15) {
        el.innerHTML = "15/15 — <span class=\"checklist-all-passed\">All checks passed.</span>";
    } else {
        el.textContent = checked + "/15 checked";
    }
}
function addConfusionSignal(type) {
    var note = document.getElementById("confusion-note-input").value.trim();
    var ts = new Date().toISOString();
    __ariadne_confusion_signals.push({type: type, note: note, timestamp: ts});
    document.getElementById("confusion-note-input").value = "";
    renderConfusionSignals();
}
function renderConfusionSignals() {
    var list = document.getElementById("confusion-signal-list");
    if (__ariadne_confusion_signals.length === 0) {
        list.innerHTML = "<em>No confusion signals recorded.</em>";
        return;
    }
    var html = "";
    for (var i = 0; i < __ariadne_confusion_signals.length; i++) {
        var sig = __ariadne_confusion_signals[i];
        var label = sig.type.replace(/_/g, " ").replace(/\b\w/g, function(c) { return c.toUpperCase(); });
        html += "<div class=\"confusion-entry\">"
            + "<span class=\"confusion-type\">" + label + "</span>"
            + (sig.note ? "<span class=\"confusion-note\">" + sig.note + "</span>" : "<span class=\"confusion-note\" style=\"color:#aaa;\">(no note)</span>")
            + "<span class=\"confusion-time\">" + sig.timestamp + "</span>"
            + "</div>";
    }
    list.innerHTML = html;
}
function clearConfusionSignals() {
    __ariadne_confusion_signals = [];
    renderConfusionSignals();
}
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
        whatHappened = "Docker execution completed. See execution trace for details.";
    else if (runtimeStatus === "failed" && !isNoop)
        whatHappened = "Docker execution failed. Check the errors section for details.";
    else if (runtimeStatus === "blocked" && !isNoop)
        whatHappened = "Docker execution blocked. You must select the Docker opt-in checkbox and set the ARIADNE_ALLOW_DOCKER_EXECUTION environment variable to proceed.";
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
    document.getElementById("task-validation").style.display = "none";
    var radios = document.querySelectorAll('input[name="runner"]');
    for (var i = 0; i < radios.length; i++) {
        radios[i].checked = (radios[i].value === runnerValue);
    }
}
document.getElementById("task").addEventListener("input", function() {
    document.getElementById("task-validation").style.display = "none";
});
function showError(msg) {
    document.getElementById("error-message").textContent = msg;
    document.getElementById("error-panel").style.display = "";
}
function dismissError() {
    document.getElementById("error-panel").style.display = "none";
}
function validateTask() {
    var task = document.getElementById("task").value;
    var el = document.getElementById("task-validation");
    if (!task || task.trim() === "") {
        el.style.display = "";
        return false;
    }
    el.style.display = "none";
    return true;
}
document.getElementById("dismiss-error-btn").addEventListener("click", dismissError);
document.getElementById("submit").addEventListener("click", async function () {
    var task = document.getElementById("task").value;
    var runner = document.querySelector('input[name="runner"]:checked');
    var runnerValue = runner ? runner.value : "noop";
    // Validate: empty or whitespace-only
    if (!task || task.trim() === "") {
        document.getElementById("task-validation").style.display = "";
        return;
    }
    document.getElementById("task-validation").style.display = "none";
    dismissError();
    // Loading state
    var btn = document.getElementById("submit");
    btn.disabled = true;
    btn.textContent = "Running…";
    document.getElementById("status-bar").innerHTML = "<span class=\"loading\">Running…</span>";
    try {
        var body = {task: task, requested_adapter: runnerValue, allow_docker: document.getElementById("allow-docker-checkbox").checked};
        var resp = await fetch("/runs/execute", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            var errBody = "";
            try { errBody = await resp.text(); } catch (e) {}
            showError("Unexpected response status: " + resp.status + (errBody ? " — " + errBody : ""));
            btn.disabled = false;
            btn.textContent = "Submit";
            document.getElementById("status-bar").innerHTML = "<span class=\"status-failed\">Request failed (status " + resp.status + ")</span>";
            return;
        }
        var data;
        try {
            data = await resp.json();
        } catch (e) {
            showError("Failed to parse response as JSON: " + e.message);
            btn.disabled = false;
            btn.textContent = "Submit";
            document.getElementById("status-bar").innerHTML = "<span class=\"status-error\">Invalid JSON response</span>";
            return;
        }
        // Check expected fields
        var rt = get(data, "runtime_status", null);
        if (rt === null) {
            document.getElementById("status-bar").innerHTML = "<span class=\"status-error\">Unexpected response format</span>";
            document.getElementById("json").textContent = JSON.stringify(data, null, 2);
            btn.disabled = false;
            btn.textContent = "Submit";
            return;
        }
        document.getElementById("status-bar").innerHTML =
            "<span class=\"status-" + rt + "\">" + rt + "</span>";
        document.getElementById("summary-card").innerHTML = renderSummaryCard(data);
        document.getElementById("run-report-section").style.display = "";
        window._latestData = data;
        pushRunHistory(data);
        document.getElementById("trace-steps").innerHTML = renderTrace(data);
        document.getElementById("structured-view").innerHTML = renderStructured(data);
        document.getElementById("json").textContent = JSON.stringify(data, null, 2);
        // Refresh evidence-backed run list after submit
        fetchRuns();
    } catch (e) {
        showError("Request failed: " + e.message);
        document.getElementById("status-bar").innerHTML = "<span class=\"status-error\">Request failed: " + e.message + "</span>";
    }
    btn.disabled = false;
    btn.textContent = "Submit";
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
    text += "=== Confusion Signals ===\n";
    if (__ariadne_confusion_signals.length === 0) {
        text += "  (none)\n";
    } else {
        for (var si = 0; si < __ariadne_confusion_signals.length; si++) {
            var sig = __ariadne_confusion_signals[si];
            var slabel = sig.type.replace(/_/g, " ");
            text += "  - " + slabel + (sig.note ? (": " + sig.note) : "") + " (" + sig.timestamp + ")\n";
        }
    }
    text += "\nSession generated locally in browser at: " + ts + "\n";
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
document.getElementById("dismiss-onboarding-btn").addEventListener("click", dismissOnboarding);
document.getElementById("reset-checklist-btn").addEventListener("click", function() {
    var cbs = document.querySelectorAll(".checklist-cb");
    for (var i = 0; i < cbs.length; i++) {
        cbs[i].checked = false;
    }
    updateChecklistCounter();
});
document.getElementById("clear-confusion-btn").addEventListener("click", clearConfusionSignals);
document.getElementById("record-session-btn").addEventListener("click", recordSessionSignal);
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
function fetchRuns() {
    fetch("/runs")
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var placeholder = document.getElementById("run-history-placeholder");
            var list = document.getElementById("run-history-list");
            var clearBtn = document.getElementById("clear-history-btn");
            if (!data.ok || data.count === 0) {
                placeholder.style.display = "";
                list.innerHTML = "";
                clearBtn.style.display = "none";
                return;
            }
            placeholder.style.display = "none";
            clearBtn.style.display = "";
            var html = "";
            for (var i = 0; i < data.runs.length; i++) {
                var r = data.runs[i];
                var statusClass = "status-" + r.status;
                var evidenceIndicators = "";
                if (r.missing_evidence.length > 0) {
                    evidenceIndicators += " <span style=\"color:#a50;\" title=\"Missing: " + r.missing_evidence.join(", ") + "\">[" + r.missing_evidence.length + " missing]</span>";
                }
                if (r.malformed_evidence.length > 0) {
                    evidenceIndicators += " <span style=\"color:#a00;\" title=\"Malformed: " + r.malformed_evidence.join(", ") + "\">[" + r.malformed_evidence.length + " malformed]</span>";
                }
                var prLink = r.pr_url ? " <a href=\"" + r.pr_url + "\" target=\"_blank\">PR</a>" : "";
                var viewBtn = " <button onclick=\"fetchRunDetail('" + r.run_id + "')\" style=\"cursor:pointer;\">View</button>";
                html += "<div class=\"history-entry\">"
                    + "<span class=\"history-index\">" + r.run_id + "</span>"
                    + "<span class=\"history-status " + statusClass + "\">" + r.status + "</span>"
                    + evidenceIndicators
                    + prLink
                    + viewBtn
                    + "</div>";
            }
            list.innerHTML = html;
        })
        .catch(function(err) {
            // Silent fail — keep existing history display
        });
}
var __ariadne_session_ref = null;
function getOrCreateSessionRef() {
    if (!__ariadne_session_ref) {
        __ariadne_session_ref = "session-" + Date.now().toString(36) + "-" + Math.random().toString(36).substring(2, 8);
    }
    return __ariadne_session_ref;
}
function recordSessionSignal() {
    var btn = document.getElementById("record-session-btn");
    var statusEl = document.getElementById("session-status");
    btn.disabled = true;
    statusEl.textContent = "Recording…";
    var sessionRef = getOrCreateSessionRef();
    var runRefs = __ariadne_run_history.map(function(e) { return e.timestamp + "-" + e.runner; });
    var confusionRefs = __ariadne_confusion_signals.map(function(s) { return s.type + "-" + s.timestamp; });
    var feedbackNote = document.getElementById("feedback_notes").value.trim();
    var body = {
        session_ref: sessionRef,
        screen_time_seconds: Math.floor((Date.now() - window.__ariadne_session_start || Date.now()) / 1000),
        active_time_seconds: Math.floor((Date.now() - window.__ariadne_session_start || Date.now()) / 1000),
        idle_time_seconds: 0,
        run_refs: runRefs,
        confusion_refs: confusionRefs,
        feedback_refs: feedbackNote ? ["feedback-" + Date.now().toString(36)] : [],
        human_iteration_note: feedbackNote || "Session recorded via surface capture.",
        source_surface: "task_intake",
    };
    fetch("/product/iterations", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body),
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.status === "recorded") {
            statusEl.innerHTML = "<span class=\"ok-true\">Recorded: " + data.iteration_ref + "</span>";
        } else {
            statusEl.innerHTML = "<span class=\"status-failed\">Rejected: " + (data.reason_codes || []).join(", ") + "</span>";
        }
    })
    .catch(function(err) {
        statusEl.innerHTML = "<span class=\"status-error\">Error: " + err.message + "</span>";
    })
    .finally(function() {
        btn.disabled = false;
    });
}
window.__ariadne_session_start = Date.now();
// Run detail panel
function fetchRunDetail(runId) {
    var panel = document.getElementById("run-detail-panel");
    var content = document.getElementById("run-detail-content");
    var runIdSpan = document.getElementById("detail-run-id");
    panel.style.display = "";
    runIdSpan.textContent = runId;
    content.innerHTML = "<em>Loading...</em>";
    fetch("/runs/" + encodeURIComponent(runId))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            renderRunDetail(data);
        })
        .catch(function(err) {
            content.innerHTML = "<p class=\"status-error\">Error: " + err.message + "</p>";
        });
}
function esc(s) {
    if (s == null) return "not available";
    if (typeof s === "string") return s;
    return String(s);
}
function escHtml(s) {
    var div = document.createElement("div");
    div.textContent = esc(s);
    return div.innerHTML;
}
function renderRunDetail(data) {
    var content = document.getElementById("run-detail-content");
    var html = "";
    html += "<p><strong>OK:</strong> <span class=\"" + (data.ok ? "ok-true\">true" : "ok-false\">false") + "</span></p>";
    if (data.error) {
        html += "<p><strong>Error:</strong> " + escHtml(data.error) + "</p>";
    }
    // Summary
    if (data.summary) {
        var s = data.summary;
        html += "<h3>Summary</h3>";
        html += "<p><strong>Run ID:</strong> " + escHtml(s.run_id) + "</p>";
        html += "<p><strong>Status:</strong> <span class=\"status-" + s.status + "\">" + escHtml(s.status) + "</span></p>";
        html += "<p><strong>Reason codes:</strong> " + (s.reason_codes && s.reason_codes.length > 0 ? escHtml(s.reason_codes.join(", ")) : "none") + "</p>";
        html += "<p><strong>Pipeline status:</strong> " + escHtml(s.pipeline_status) + "</p>";
        html += "<p><strong>Git boundary:</strong> " + escHtml(s.git_boundary_status) + "</p>";
        html += "<p><strong>Execution attempted:</strong> " + (s.execution_attempted ? "yes" : "no") + "</p>";
        html += "<p><strong>Created at:</strong> " + escHtml(s.created_at) + "</p>";
        html += "<p><strong>Run JSON:</strong> " + (s.run_json_available ? "available" : "not available") + "</p>";
        html += "<p><strong>Manifest:</strong> " + (s.manifest_available ? "available" : "not available") + "</p>";
        html += "<p><strong>Run report:</strong> " + (s.run_report_available ? "available" : "not available") + "</p>";
        if (s.pr_url) {
            html += "<p><strong>PR URL:</strong> <a href=\"" + escHtml(s.pr_url) + "\" target=\"_blank\">" + escHtml(s.pr_url) + "</a></p>";
        } else {
            html += "<p><strong>PR URL:</strong> not available</p>";
        }
    }
    // Detail
    if (data.detail) {
        var d = data.detail;
        html += "<h3>Execution Results</h3>";
        if (d.execution_results && d.execution_results.length > 0) {
            html += "<ul>";
            for (var i = 0; i < d.execution_results.length; i++) {
                html += "<li>" + JSON.stringify(d.execution_results[i]) + "</li>";
            }
            html += "</ul>";
        } else {
            html += "<p><em>none</em></p>";
        }
        html += "<h3>Manifest Files</h3>";
        if (d.manifest_files && d.manifest_files.length > 0) {
            html += "<ul>";
            for (var i = 0; i < d.manifest_files.length; i++) {
                html += "<li>" + escHtml(d.manifest_files[i]) + "</li>";
            }
            html += "</ul>";
        } else {
            html += "<p><em>none</em></p>";
        }
        html += "<h3>Report Preview</h3>";
        if (d.report_preview) {
            html += "<pre>" + escHtml(d.report_preview) + "</pre>";
        } else {
            html += "<p><em>not available</em></p>";
        }
        html += "<h3>Evidence Paths</h3>";
        if (d.evidence_paths && d.evidence_paths.length > 0) {
            html += "<ul>";
            for (var i = 0; i < d.evidence_paths.length; i++) {
                html += "<li>" + escHtml(d.evidence_paths[i]) + "</li>";
            }
            html += "</ul>";
        } else {
            html += "<p><em>none</em></p>";
        }
        html += "<p><strong>Run JSON hash:</strong> " + escHtml(d.run_json_hash) + "</p>";
        html += "<p><strong>Source errors:</strong> " + (d.source_errors && d.source_errors.length > 0 ? escHtml(d.source_errors.join(", ")) : "none") + "</p>";
    }
    // Unavailable values
    html += "<h3>Unavailable Values</h3>";
    html += "<p><strong>Payload cleanliness:</strong> " + escHtml(data.payload_cleanliness) + "</p>";
    html += "<p><strong>Readiness:</strong> " + escHtml(data.readiness) + "</p>";
    // Missing evidence
    html += "<h3>Notices</h3>";
    html += "<h4>Missing Evidence</h4>";
    if (data.missing && data.missing.length > 0) {
        html += "<ul>";
        for (var i = 0; i < data.missing.length; i++) {
            html += "<li><strong>" + escHtml(data.missing[i].expected_path) + "</strong>: " + escHtml(data.missing[i].reason) + "</li>";
        }
        html += "</ul>";
    } else {
        html += "<p><em>none</em></p>";
    }
    html += "<h4>Malformed Evidence</h4>";
    if (data.malformed && data.malformed.length > 0) {
        html += "<ul>";
        for (var i = 0; i < data.malformed.length; i++) {
            html += "<li><strong>" + escHtml(data.malformed[i].expected_path) + "</strong>: " + escHtml(data.malformed[i].reason) + "</li>";
        }
        html += "</ul>";
    } else {
        html += "<p><em>none</em></p>";
    }
    content.innerHTML = html;
}
// Fetch evidence-backed run list on page load
fetchRuns();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Expose app title for PLAN import check
# ---------------------------------------------------------------------------

title = "Task Intake API"

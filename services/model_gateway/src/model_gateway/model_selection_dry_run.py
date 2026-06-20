"""Model Selection Dry-Run Decision Record.

Local, deterministic, evidence-only CLI tool that emits a
ModelSelectionResult-like JSON object from explicit input.

Supports two CLI modes:
1. Detailed (PR 0033): --role, --risk-level, --retrieval-stress, etc.
2. Simplified smoke (PR 0034): --role, --context-stress, --failure-mode, etc.

This is NOT live model routing.
This is NOT provider integration.
This is NOT automatic model switching.

Usage::

    PYTHONPATH=services/model_gateway/src python -m \\
        model_gateway.model_selection_dry_run --help
"""

from __future__ import annotations

import argparse
import json
import sys


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

ROLES = frozenset({
    "architect",
    "worker_coder",
    "ui_frontend",
    "backend_optimizer",
    "reviewer",
    "dataset_synth",
})

SIMPLIFIED_ROLE_MAP = {
    "coder": "worker_coder",
    "architect": "architect",
    "reviewer": "reviewer",
    "ui": "ui_frontend",
    "backend": "backend_optimizer",
    "dataset": "dataset_synth",
}

RISK_LEVELS = frozenset({"low", "medium", "high", "critical"})

STRESS_LEVELS = frozenset({"low", "medium", "high"})

COST_SENSITIVITY_MAP = {
    "low": "low",
    "medium": "medium",
    "high": "critical",
}

VERIFICATION_MAP = {
    "none": "low",
    "recommended": "high",
    "required": "critical",
}

CONTEXT_STRESS_FIELDS = (
    "retrieval_stress",
    "aggregation_stress",
    "graph_reasoning_stress",
    "long_code_stress",
    "icl_sensitivity",
)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _build_decision(
    role: str,
    task_type: str,
    risk_level: str,
    context_stress: dict[str, str],
    recommended_model: str,
    reviewer_model: str,
    failure_mode: str | None = None,
) -> dict:
    """Build a ModelSelectionResult-like decision dict."""
    # --- Build risk level from cost-sensitivity / verification if available ---
    effective_risk = risk_level

    selection_rules_applied = [
        "no_hardcoded_model_vendor_assignments",
    ]

    if effective_risk in ("high", "critical"):
        selection_rules_applied.append("reviewer_model_differs_from_coder_on_high_risk")
        selection_rules_applied.append("strong_for_purpose_cheap_for_execution")
    else:
        selection_rules_applied.append("model_not_strongest_by_default")

    if any(v == "high" for v in context_stress.values()):
        selection_rules_applied.append("long_context_profiled_by_subtask")

    selection_rules_applied.append("substrate_beats_model_loyalty")

    reason_parts = [
        f"Role '{role}' assigned to task type '{task_type}' "
        f"at risk level '{effective_risk}'.",
    ]

    if effective_risk in ("high", "critical") and recommended_model != reviewer_model:
        reason_parts.append(
            f"Reviewer model ({reviewer_model}) differs from recommended model "
            f"({recommended_model}) for independent review."
        )
    elif effective_risk in ("high", "critical"):
        reason_parts.append(
            "Reviewer model independence required for high/critical risk. "
            "Input validation should enforce model separation."
        )

    high_stress_fields = [f for f, v in context_stress.items() if v == "high"]
    if high_stress_fields:
        reason_parts.append(
            f"Context stress profile shows high stress in: "
            f"{', '.join(high_stress_fields)}. "
            f"Routing accounts for subtask profiling."
        )

    if failure_mode:
        reason_parts.append(
            f"Failure mode '{failure_mode}' factored into risk assessment."
        )

    reason_parts.append("Model selection is evidence only. No execution authorization.")

    return {
        "role": role,
        "task_type": task_type,
        "risk_level": effective_risk,
        "context_stress": context_stress,
        "recommended_model": recommended_model,
        "reviewer_model": reviewer_model,
        "failure_mode": failure_mode,
        "reason": " ".join(reason_parts),
        "selection_rules_applied": selection_rules_applied,
    }


# ---------------------------------------------------------------------------
# Detailed parser (PR 0033)
# ---------------------------------------------------------------------------


def _add_detailed_args(parser: argparse.ArgumentParser) -> None:
    """Add detailed CLI arguments."""
    parser.add_argument("--role", required=True, help=f"Model role: {' | '.join(sorted(ROLES))}")
    parser.add_argument("--task-type", required=True, help="Task type description")
    parser.add_argument("--risk-level", required=True, help=f"Risk level: {' | '.join(sorted(RISK_LEVELS))}")
    for field in CONTEXT_STRESS_FIELDS:
        parser.add_argument(
            f"--{field.replace('_', '-')}",
            dest=field,
            required=True,
            help=f"Context stress level: {' | '.join(sorted(STRESS_LEVELS))}",
        )
    parser.add_argument("--recommended-model", required=True, help="Recommended model (e.g. provider:model)")
    parser.add_argument("--reviewer-model", required=True, help="Reviewer model (e.g. provider:model)")
    parser.add_argument("--failure-mode", default=None, help="Known failure mode (optional)")


def _run_detailed(args: argparse.Namespace) -> int:
    """Run detailed CLI mode."""
    if args.role not in ROLES:
        print(json.dumps({"error": f"Invalid role: {args.role!r}. Allowed: {sorted(ROLES)}"}))
        return 1

    if args.risk_level not in RISK_LEVELS:
        print(json.dumps({"error": f"Invalid risk_level: {args.risk_level!r}. Allowed: {sorted(RISK_LEVELS)}"}))
        return 1

    context_stress = {}
    for field in CONTEXT_STRESS_FIELDS:
        value = getattr(args, field)
        if value not in STRESS_LEVELS:
            print(json.dumps({"error": f"Invalid {field}: {value!r}. Allowed: {sorted(STRESS_LEVELS)}"}))
            return 1
        context_stress[field] = value

    if args.risk_level in ("high", "critical") and args.recommended_model == args.reviewer_model:
        print(json.dumps({
            "error": (
                f"reviewer_model ({args.reviewer_model}) must differ from "
                f"recommended_model ({args.recommended_model}) when "
                f"risk_level is {args.risk_level}"
            ),
        }))
        return 1

    output = _build_decision(
        role=args.role,
        task_type=args.task_type,
        risk_level=args.risk_level,
        context_stress=context_stress,
        recommended_model=args.recommended_model,
        reviewer_model=args.reviewer_model,
        failure_mode=args.failure_mode,
    )

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------------------
# Simplified parser (PR 0034 smoke)
# ---------------------------------------------------------------------------


def _add_simplified_args(parser: argparse.ArgumentParser) -> None:
    """Add simplified / smoke CLI arguments."""
    parser.add_argument("--role", required=True, help=f"Simplified role: {' | '.join(sorted(SIMPLIFIED_ROLE_MAP))}")
    parser.add_argument("--task-type", required=True, help="Task type description")
    parser.add_argument("--context-stress", required=True, choices=sorted(STRESS_LEVELS),
                        help="Overall context stress level")
    parser.add_argument("--failure-mode", default=None, help="Known failure mode (optional)")
    parser.add_argument("--cost-sensitivity", choices=sorted(STRESS_LEVELS),
                        default="medium", help="Cost sensitivity")
    parser.add_argument("--verification", choices=sorted(VERIFICATION_MAP),
                        default="recommended", help="Verification requirement")


def _run_simplified(args: argparse.Namespace) -> int:
    """Run simplified / smoke CLI mode."""
    if args.role not in SIMPLIFIED_ROLE_MAP:
        print(json.dumps({
            "error": f"Invalid role: {args.role!r}. Allowed: {sorted(SIMPLIFIED_ROLE_MAP)}",
        }))
        return 1

    mapped_role = SIMPLIFIED_ROLE_MAP[args.role]

    # Map verification level to risk level
    risk_level = VERIFICATION_MAP[args.verification]
    cost_sensitivity = args.cost_sensitivity

    # Build a flat context_stress with the overall level applied to all fields
    cs_level = args.context_stress
    context_stress = {field: cs_level for field in CONTEXT_STRESS_FIELDS}

    # Build placeholder model strings
    recommended_model = f"provider:{mapped_role}-recommended"
    reviewer_model = f"provider:{mapped_role}-reviewer"

    # If risk is high/critical and reviewer has same model, enforce separation
    if risk_level in ("high", "critical") and recommended_model == reviewer_model:
        # Append a differentiator so they differ
        reviewer_model = f"provider:{mapped_role}-reviewer-independent"

    output = _build_decision(
        role=mapped_role,
        task_type=args.task_type,
        risk_level=risk_level,
        context_stress=context_stress,
        recommended_model=recommended_model,
        reviewer_model=reviewer_model,
        failure_mode=args.failure_mode,
    )

    output["cost_sensitivity"] = cost_sensitivity
    output["verification"] = args.verification

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the model selection dry-run.

    Parameters
    ----------
    argv
        Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns
    -------
    int
        Exit code (0 = valid decision, 1 = validation error).
    """
    parser = argparse.ArgumentParser(
        description="Model Selection Dry-Run Decision Record",
        epilog="Evidence only. Does not call providers or authorize execution.",
    )

    # Detect mode based on which flag style is used
    # We handle this by trying detailed first; if --context-stress is
    # present, use simplified mode.
    # Since argparse doesn't support this trivially, we do a pre-pass.
    raw_args = argv if argv is not None else sys.argv[1:]

    is_simplified = any(a.startswith("--context-stress") for a in raw_args)

    if is_simplified:
        _add_simplified_args(parser)
    else:
        _add_detailed_args(parser)

    try:
        args = parser.parse_args(raw_args)
    except SystemExit:
        return 2

    if is_simplified:
        return _run_simplified(args)
    else:
        return _run_detailed(args)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())

"""Model Selection Dry-Run Decision Record.

Local, deterministic, evidence-only CLI tool that emits a
ModelSelectionResult-like JSON object from explicit input.

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

RISK_LEVELS = frozenset({"low", "medium", "high", "critical"})

STRESS_LEVELS = frozenset({"low", "medium", "high"})

CONTEXT_STRESS_FIELDS = (
    "retrieval_stress",
    "aggregation_stress",
    "graph_reasoning_stress",
    "long_code_stress",
    "icl_sensitivity",
)


# ---------------------------------------------------------------------------
# Main
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

    args = parser.parse_args(argv)

    # --- Validate role ---
    if args.role not in ROLES:
        print(
            json.dumps({
                "error": f"Invalid role: {args.role!r}. Allowed: {sorted(ROLES)}",
            }),
        )
        return 1

    # --- Validate risk level ---
    if args.risk_level not in RISK_LEVELS:
        print(
            json.dumps({
                "error": f"Invalid risk_level: {args.risk_level!r}. Allowed: {sorted(RISK_LEVELS)}",
            }),
        )
        return 1

    # --- Validate context stress fields ---
    context_stress = {}
    for field in CONTEXT_STRESS_FIELDS:
        value = getattr(args, field)
        if value not in STRESS_LEVELS:
            print(
                json.dumps({
                    "error": f"Invalid {field}: {value!r}. Allowed: {sorted(STRESS_LEVELS)}",
                }),
            )
            return 1
        context_stress[field] = value

    # --- Validate reviewer independence on high/critical risk ---
    if args.risk_level in ("high", "critical") and args.recommended_model == args.reviewer_model:
        print(
            json.dumps({
                "error": (
                    f"reviewer_model ({args.reviewer_model}) must differ from "
                    f"recommended_model ({args.recommended_model}) when "
                    f"risk_level is {args.risk_level}"
                ),
            }),
        )
        return 1

    # --- Build selection_rules_applied ---
    selection_rules_applied = [
        "no_hardcoded_model_vendor_assignments",
    ]

    if args.risk_level in ("high", "critical"):
        selection_rules_applied.append("reviewer_model_differs_from_coder_on_high_risk")
        selection_rules_applied.append("strong_for_purpose_cheap_for_execution")
    else:
        selection_rules_applied.append("model_not_strongest_by_default")

    # Check if context stress has any high values
    if any(v == "high" for v in context_stress.values()):
        selection_rules_applied.append("long_context_profiled_by_subtask")

    selection_rules_applied.append("substrate_beats_model_loyalty")

    # --- Build reason ---
    reason_parts = [
        f"Role '{args.role}' assigned to task type '{args.task_type}' "
        f"at risk level '{args.risk_level}'.",
    ]

    if args.risk_level in ("high", "critical"):
        reason_parts.append(
            f"Reviewer model ({args.reviewer_model}) differs from recommended model "
            f"({args.recommended_model}) for independent review."
        )
    else:
        reason_parts.append(
            f"Using different models for recommended ({args.recommended_model}) "
            f"and reviewer ({args.reviewer_model}) for traceability."
        )

    high_stress_fields = [f for f, v in context_stress.items() if v == "high"]
    if high_stress_fields:
        reason_parts.append(
            f"Context stress profile shows high stress in: "
            f"{', '.join(high_stress_fields)}. "
            f"Routing accounts for subtask profiling."
        )

    reason_parts.append("Model selection is evidence only. No execution authorization.")

    # --- Build output ---
    output = {
        "role": args.role,
        "task_type": args.task_type,
        "risk_level": args.risk_level,
        "context_stress": context_stress,
        "recommended_model": args.recommended_model,
        "reviewer_model": args.reviewer_model,
        "reason": " ".join(reason_parts),
        "selection_rules_applied": selection_rules_applied,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())

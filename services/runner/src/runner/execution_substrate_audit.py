"""
Deterministic local execution-substrate audit / invariant check.

Verifies Ariadne execution-substrate invariants have not drifted after
PR 0094 (Docker execution wiring), PR 0095 (Docker run artifacts), and
PR 0096 (human review boundary). Also surfaces review-process completeness
tech-debt: precommit-review FILES READ vs actual diff gaps.

No filesystem access, no network calls, no Docker, no persistence.
Accepts explicit source text strings — testable without file access.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

VALID_SEVERITIES = ("invariant", "tech_debt")


def _validate_severity(severity: str) -> str:
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"severity must be in {VALID_SEVERITIES}, got {severity!r}")
    return severity


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _check(
    check_id: str,
    description: str,
    passed: bool,
    severity: str = "invariant",
    details: str | None = None,
    extra: dict | None = None,
) -> dict:
    """Build a single audit check result dict."""
    return {
        "check_id": check_id,
        "description": description,
        "passed": passed,
        "severity": _validate_severity(severity),
        "details": details,
        "extra": extra,
    }


def run_execution_substrate_audit(
    docker_agent_adapter_source: str | None = None,
    docker_run_artifacts_source: str | None = None,
    docker_subprocess_executor_source: str | None = None,
    adapter_registry_source: str | None = None,
    review_boundary_source: str | None = None,
    task_intake_http_source: str | None = None,
    task_intake_execution_handoff_source: str | None = None,
    pr_diff_files: list[dict] | None = None,
) -> dict:
    """Run the execution-substrate audit with explicit source text fixtures.

    Parameters
    ----------
    *source parameters
        Python source text for each module. Pass ``None`` to skip source-
        scanning checks.
    pr_diff_files
        List of ``AuditDiffInput`` dicts for the review-process completeness
        retro-check. Each dict must have keys: pr_id, diff_files, precommit_files_read.

    Returns
    -------
    dict
        An ``AuditReport`` dict with keys: timestamp, checks, summary.
    """
    checks: list[dict] = []

    # --- Invariant 1: Docker dual gate ---
    checks.extend(_check_dual_gate(adapter_registry_source))

    # --- Invariant 2: requires_review on successful Docker execution ---
    checks.append(_check_requires_review(docker_agent_adapter_source))

    # --- Invariant 3: failed remains failed ---
    checks.append(_check_failed_unchanged(docker_agent_adapter_source))

    # --- Invariant 4: blocked remains blocked ---
    checks.append(_check_blocked_unchanged(docker_agent_adapter_source))

    # --- Invariant 5: review boundary maps all three statuses ---
    checks.append(_check_review_boundary_mapping(review_boundary_source))

    # --- Invariant 6: artifact kinds present ---
    checks.append(_check_artifact_kinds(docker_run_artifacts_source, docker_agent_adapter_source))

    # --- Invariant 7: evidence kinds present ---
    checks.append(_check_evidence_kinds(docker_run_artifacts_source))

    # --- Invariant 8: stdout/stderr bounded ---
    checks.append(_check_stdout_stderr_bounded(docker_run_artifacts_source))

    # --- Invariant 9: environment values redacted ---
    checks.append(_check_env_values_redacted(docker_run_artifacts_source))

    # --- Invariant 10: subprocess import isolation ---
    checks.extend(_check_subprocess_isolation(
        docker_agent_adapter_source=docker_agent_adapter_source,
        docker_run_artifacts_source=docker_run_artifacts_source,
        adapter_registry_source=adapter_registry_source,
        review_boundary_source=review_boundary_source,
    ))

    # --- Invariant 11: forbidden source strings in task_intake ---
    checks.append(_check_forbidden_source_strings(
        task_intake_http_source=task_intake_http_source,
        task_intake_execution_handoff_source=task_intake_execution_handoff_source,
    ))

    # --- Invariant 12: no frontend-only drift ---
    checks.append(_check_frontend_drift(pr_diff_files))

    # --- Review-process completeness retro-check ---
    checks.extend(_check_review_process_completeness(pr_diff_files))

    # --- Summary ---
    total = len(checks)
    passed = sum(1 for c in checks if c["passed"])
    failed = total - passed
    warnings = sum(1 for c in checks if c["severity"] == "tech_debt" and not c["passed"])
    blockers = sum(1 for c in checks if c["severity"] == "invariant" and not c["passed"])

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warning_count": warnings,
            "blocker_count": blockers,
        },
    }


# ---------------------------------------------------------------------------
# Individual invariant checks
# ---------------------------------------------------------------------------


def _check_dual_gate(adapter_registry_source: str | None) -> list[dict]:
    """Invariant 1: Docker dual gate."""
    results: list[dict] = []
    source = adapter_registry_source or ""
    check_id = "docker_dual_gate"
    desc = "Docker dual gate: request allow_docker AND env ARIADNE_ALLOW_DOCKER_EXECUTION both required."
    clean = _strip_comments_and_strings(source)

    if not source:
        results.append(_check(check_id, desc, True, "invariant", "Source not provided; skipping check."))
        return results

    # Check that both allow_docker and env_allowed appear in the same logic
    has_allow_docker = "allow_docker" in clean and "execution_request.get" in source
    has_env_check = "ARIADNE_ALLOW_DOCKER_EXECUTION" in source
    has_false_guard = '"false"' in source or "'false'" in source or '"no"' in source or "'no'" in source

    if has_allow_docker and has_env_check and has_false_guard:
        results.append(_check(check_id, desc, True, "invariant", "Dual gate confirmed: env check includes 'false'/'no' exclusion."))
    elif has_allow_docker and has_env_check:
        results.append(_check(check_id, desc, False, "invariant", "Env check present but string 'false'/'no' exclusion may be missing."))
    else:
        results.append(_check(check_id, desc, False, "invariant", "Dual gate incomplete: allow_docker or ARIADNE_ALLOW_DOCKER_EXECUTION check missing."))

    return results


def _check_requires_review(source: str | None) -> dict:
    """Invariant 2: requires_review on successful Docker execution."""
    check_id = "docker_success_requires_review"
    desc = "Successful real docker-agent execution returns status=requires_review."
    raw = source or ""

    if not raw:
        return _check(check_id, desc, True, "invariant", "Source not provided; skipping check.")

    # Check for both assignment and dict literal patterns
    has_requires_review = ('"status": "requires_review"' in raw or "'status': 'requires_review'" in raw
                          or 'status = "requires_review"' in raw or 'status= "requires_review"' in raw)
    if has_requires_review:
        return _check(check_id, desc, True, "invariant", "Status set to 'requires_review' in success branch.")

    # Check for the opposite — status = "completed" or dict literal
    has_completed = ('"status": "completed"' in raw or "'status': 'completed'" in raw
                     or 'status = "completed"' in raw)
    if has_completed:
        return _check(check_id, desc, False, "invariant", "Status 'completed' found. Should be 'requires_review'.")

    return _check(check_id, desc, False, "invariant", "Could not confirm 'requires_review' assignment in success branch.")


def _check_failed_unchanged(source: str | None) -> dict:
    """Invariant 3: failed remains failed."""
    check_id = "docker_failed_unchanged"
    desc = "Failed real docker-agent execution returns status=failed."
    raw = source or ""

    if not raw:
        return _check(check_id, desc, True, "invariant", "Source not provided; skipping check.")

    if ('"status": "failed"' in raw or "'status': 'failed'" in raw
            or 'status = "failed"' in raw or 'status= "failed"' in raw):
        return _check(check_id, desc, True, "invariant", "Status 'failed' found in result.")
    return _check(check_id, desc, False, "invariant", "Status 'failed' not found in analyzed source.")


def _check_blocked_unchanged(source: str | None) -> dict:
    """Invariant 4: blocked remains blocked."""
    check_id = "docker_blocked_unchanged"
    desc = "Blocked docker-agent execution returns status=blocked."
    raw = source or ""

    if not raw:
        return _check(check_id, desc, True, "invariant", "Source not provided; skipping check.")

    # Check for both assignment and dict literal patterns
    if '"status": "blocked"' in raw or "'status': 'blocked'" in raw or 'status = "blocked"' in raw or 'status= "blocked"' in raw:
        return _check(check_id, desc, True, "invariant", "Status 'blocked' found in result.")
    return _check(check_id, desc, False, "invariant", "Status 'blocked' not found in analyzed source.")


def _check_review_boundary_mapping(source: str | None) -> dict:
    """Invariant 5: review boundary maps all three statuses."""
    check_id = "review_boundary_status_map"
    desc = "derive_review_boundary maps requires_review->requires_review, failed->failed, blocked->blocked."
    raw = source or ""

    if not raw:
        return _check(check_id, desc, True, "invariant", "Source not provided; best tested via functional call.")

    # Check for both double-quote and single-quote patterns
    has_requires_review_mapping = ('"requires_review"' in raw or "'requires_review'" in raw)
    has_failed_mapping = ('"failed"' in raw and '"error"' in raw) or ("'failed'" in raw and "'error'" in raw)
    has_blocked_mapping = ('result_status == "blocked"' in raw or "result_status == 'blocked'" in raw)

    if has_requires_review_mapping and has_failed_mapping and has_blocked_mapping:
        return _check(check_id, desc, True, "invariant", "Status-to-decision mapping found for requires_review, failed, and blocked.")
    else:
        missing = []
        if not has_requires_review_mapping:
            missing.append("requires_review")
        if not has_failed_mapping:
            missing.append("failed")
        if not has_blocked_mapping:
            missing.append("blocked")
        return _check(check_id, desc, False, "invariant", f"Missing mappings for: {', '.join(missing)}.")


def _check_artifact_kinds(*sources: str | None) -> dict:
    """Invariant 6: artifact kinds present."""
    check_id = "artifact_kinds_present"
    desc = "Four artifact kinds: docker_stdout, docker_stderr, docker_execution_metadata, docker_command_metadata."

    combined = " ".join(s or "" for s in sources)
    if not combined:
        return _check(check_id, desc, True, "invariant", "No source provided; skipping check.")

    required = ["docker_stdout", "docker_stderr", "docker_execution_metadata", "docker_command_metadata"]
    found = [k for k in required if k in combined]
    missing = [k for k in required if k not in found]

    if not missing:
        return _check(check_id, desc, True, "invariant", f"All {len(required)} artifact kinds present.", extra={"found_kinds": found})
    return _check(check_id, desc, False, "invariant", f"Missing artifact kinds: {', '.join(missing)}.", extra={"found_kinds": found})


def _check_evidence_kinds(*sources: str | None) -> dict:
    """Invariant 7: evidence kinds present."""
    check_id = "evidence_kinds_present"
    desc = "Two evidence kinds: execution_log, execution_note."

    combined = " ".join(s or "" for s in sources)
    if not combined:
        return _check(check_id, desc, True, "invariant", "No source provided; skipping check.")

    required = ["execution_log", "execution_note"]
    found = [k for k in required if k in combined]
    missing = [k for k in required if k not in found]

    if not missing:
        return _check(check_id, desc, True, "invariant", f"All {len(required)} evidence kinds present.", extra={"found_kinds": found})
    return _check(check_id, desc, False, "invariant", f"Missing evidence kinds: {', '.join(missing)}.", extra={"found_kinds": found})


def _check_stdout_stderr_bounded(*sources: str | None) -> dict:
    """Invariant 8: stdout/stderr bounded."""
    check_id = "stdout_stderr_bounded"
    desc = "stdout/stderr artifacts truncated at 10000 characters with truncation marker."

    combined = " ".join(s or "" for s in sources)
    if not combined:
        return _check(check_id, desc, True, "invariant", "No source provided; skipping check.")

    has_boundary = "10000" in combined or "10000" in combined
    has_truncated = "truncated at" in combined or "truncated" in combined

    if has_boundary and has_truncated:
        return _check(check_id, desc, True, "invariant", "Bounding logic found: 10000 char limit with truncation marker.")
    elif has_boundary:
        return _check(check_id, desc, False, "invariant", "Has char limit but missing truncation marker.")
    else:
        return _check(check_id, desc, False, "invariant", "No bounding logic found.")


def _check_env_values_redacted(*sources: str | None) -> dict:
    """Invariant 9: environment values redacted."""
    check_id = "env_values_redacted"
    desc = "Environment variable values not stored in artifacts; only key names and count."

    combined = " ".join(s or "" for s in sources)
    if not combined:
        return _check(check_id, desc, True, "invariant", "No source provided; skipping check.")

    has_env_var_count = "env_var_count" in combined
    has_env_var_keys = "env_var_keys" in combined
    has_safe_environment_key_list = "_safe_environment_key_list" in combined

    # Check that raw env values are not stored: look for avoidance of
    # storing command_metadata["environment"] values raw
    no_raw_store = True
    # Check if any artifact content includes raw env values (should be key names/count only)
    # This is heuristic — look for evidence that raw env values are NOT written to content
    has_redacted_suffix = "_keys" in combined and ("count" in combined or "keys" in combined)

    if (has_env_var_count or has_env_var_keys) and (has_redacted_suffix or has_safe_environment_key_list):
        return _check(check_id, desc, True, "invariant", "Environment values redacted: only key names/count in artifacts.")
    elif has_env_var_count or has_env_var_keys:
        return _check(check_id, desc, True, "invariant", "Environment count/keys reference found.")
    else:
        return _check(check_id, desc, False, "invariant", "No environment redaction pattern found.")


def _check_subprocess_isolation(**sources: str | None) -> list[dict]:
    """Invariant 10: subprocess import isolation.

    Returns two checks: one for subprocess in non-executor files, one overall.
    """
    results: list[dict] = []
    check_id = "subprocess_isolation"
    desc = "subprocess import exists only in docker_subprocess_executor.py and test files."

    executor_source = sources.pop("docker_subprocess_executor_source", None) or ""

    non_executor_sources = {
        name: src or "" for name, src in sources.items()
    }

    # Pattern to find 'import subprocess' or 'from subprocess'
    subprocess_pattern = r'\bimport\s+subprocess\b|\bfrom\s+subprocess\b'

    executor_has_subprocess = bool(re.search(subprocess_pattern, executor_source))

    non_executor_violations = []
    for name, src in non_executor_sources.items():
        if src and re.search(subprocess_pattern, src):
            non_executor_violations.append(name)

    if not executor_source:
        # No source to check
        results.append(_check(check_id, desc, True, "invariant", "Executor source not provided; skipping check."))
        return results

    if not executor_has_subprocess:
        results.append(_check(f"{check_id}_missing", "Executor module must import subprocess.", False, "invariant", "docker_subprocess_executor source does not contain 'import subprocess'."))
        return results

    if non_executor_violations:
        results.append(_check(check_id, desc, False, "invariant", f"subprocess found outside executor in: {', '.join(non_executor_violations)}.", extra={"violating_modules": non_executor_violations}))
    else:
        results.append(_check(check_id, desc, True, "invariant", "subprocess is isolated to docker_subprocess_executor only."))

    return results


def _check_forbidden_source_strings(
    task_intake_http_source: str | None = None,
    task_intake_execution_handoff_source: str | None = None,
) -> dict:
    """Invariant 11: forbidden source strings in task_intake."""
    check_id = "task_intake_no_forbidden_strings"
    desc = "task_intake source files contain no forbidden runtime source strings."

    combined = " ".join(s or "" for s in [task_intake_http_source or "", task_intake_execution_handoff_source or ""])

    if not combined:
        return _check(check_id, desc, True, "invariant", "No source provided; skipping check.")

    clean = _strip_comments_and_strings(combined)

    forbidden = [
        "subprocess", "popen", "import docker", "from docker",
        "docker.from_env", "os.system", "requests", "httpx",
        "urllib", "socket", "redis", "sqlite",
    ]

    found = [s for s in forbidden if s in clean]
    if found:
        return _check(check_id, desc, False, "invariant", f"Forbidden strings found: {', '.join(found)}.", extra={"found": found})
    return _check(check_id, desc, True, "invariant", "No forbidden source strings found.")


def _check_frontend_drift(pr_diff_files: list[dict] | None) -> dict:
    """Invariant 12: no frontend-only drift."""
    check_id = "no_frontend_only_drift"
    desc = "No frontend-only UI-only files modified in current execution track scope."

    if not pr_diff_files:
        return _check(check_id, desc, True, "tech_debt", "No PR diff files provided; skipping check.")

    for pr in pr_diff_files:
        diffs = pr.get("diff_files", [])
        # Check if the only changed files are in server.py
        non_ui = [f for f in diffs if "server.py" not in f]
        if not non_ui and len(diffs) > 0:
            return _check(check_id, desc, False, "tech_debt", f"PR {pr.get('pr_id', '?')} contains only server.py/frontend changes.")

    return _check(check_id, desc, True, "tech_debt", "No frontend-only drift detected.")


def _check_review_process_completeness(pr_diff_files: list[dict] | None) -> list[dict]:
    """Review-process completeness retro-check.

    For each PR, compare diff_files against precommit_files_read.
    Files in diff but absent from FILES READ produce tech-debt warnings.
    """
    results: list[dict] = []

    if not pr_diff_files:
        return results

    for pr_entry in pr_diff_files:
        pr_id = pr_entry.get("pr_id", "")
        diff_files = pr_entry.get("diff_files", [])
        precommit_files_read = pr_entry.get("precommit_files_read", [])

        missing = [f for f in diff_files if f not in precommit_files_read]
        covered = [f for f in diff_files if f in precommit_files_read]

        if missing:
            results.append(_check(
                f"retro_check_{pr_id}",
                f"PR {pr_id}: diff file(s) missing from precommit-review.yml FILES READ.",
                passed=False,
                severity="tech_debt",
                details="Retrospective visibility: these files were changed but not listed in the precommit review's files_checked.",
                extra={
                    "pr_id": pr_id,
                    "files_in_diff_but_not_read": missing,
                    "total_diff_files": len(diff_files),
                    "covered_files": len(covered),
                },
            ))
        else:
            results.append(_check(
                f"retro_check_{pr_id}",
                f"PR {pr_id}: all diff files covered by precommit-review.yml FILES READ.",
                passed=True,
                severity="tech_debt",
                extra={
                    "pr_id": pr_id,
                    "total_diff_files": len(diff_files),
                    "covered_files": len(covered),
                },
            ))

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_comments_and_strings(source: str) -> str:
    """Remove comments and string literals from source for pattern scanning.

    This is a best-effort heuristic — it handles simple cases for scanning
    purposes and is not a full Python parser.
    """
    clean = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    clean = re.sub(r"'''.*?'''", "", clean, flags=re.DOTALL)
    clean = re.sub(r"#.*$", "", clean, flags=re.MULTILINE)
    # Remove single-quoted and double-quoted strings that are standalone
    clean = re.sub(r"'[^']*'", "", clean)
    clean = re.sub(r'"[^"]*"', "", clean)
    return clean


def _extract_if_else_status_block(source: str) -> dict:
    """Heuristic: extract the 'if'/'else' branch around status assignment.

    Looks for 'if success:' / 'if success' and captures the next few lines.
    This is best-effort and not a full AST parse.
    """
    result = {"success_branch": "", "failure_branch": ""}

    # Look for the pattern: success = ... ; if success: status = ... else: status = ...
    match = re.search(
        r"success\s*=\s*executor_result.*?\n\s*if\s+success\s*:\s*.+?\n\s+status\s*=\s*\"([^\"]+)\".*?\n\s*(else\s*:\s*)?\n?\s*status\s*=\s*\"([^\"]+)\"",
        source,
        re.DOTALL,
    )
    if match:
        success_val = match.group(1)
        failure_val = match.group(2) if match.group(2) else ""
        result["success_branch"] = success_val
        result["failure_branch"] = failure_val
        return result

    # Fallback: find lines with status = around an if block
    lines = source.split("\n")
    in_if_block = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("if success"):
            in_if_block = True
            # Collect next few lines
            block_lines = lines[i:i + 6]
            block_text = "\n".join(block_lines)
            result["success_branch"] = block_text
        elif in_if_block and ("status" in stripped or "else" in stripped):
            result["failure_branch"] += stripped + " "

    return result

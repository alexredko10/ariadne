"""
Prompt Composer for Ariadne — second executable Production Line PR.

Generates four agent task prompts (planner, plan-review, coder,
precommit-review) from templates, PR context, and repository evidence.
The composed prompt packets are structured for direct use as ``task_prompt``
inputs to ``run_agent_runner_bridge(...)``.

Core principle:
    Agent output is not evidence.  Runtime-captured proof is evidence.
    The composed prompt packet is a deterministic artifact, not proof that
    an agent performed work.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# PromptComposerStatus — status values
# ---------------------------------------------------------------------------


class PromptComposerStatus(str):
    """Status values for prompt composer operations."""

    READY = "ready"
    BLOCKED = "blocked"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# PromptComposerRequest — input dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PromptComposerRequest:
    """Input parameters for composing PR prompts."""

    pr_id: str
    branch: str
    task_title: str
    task_description: str
    roadmap_path: str = "ROADMAP.md"
    agents_dir: str = "agents"
    project_memory_dir: str = ".project-memory"
    repo_root: str = "."
    included_context_paths: tuple[str, ...] = ()
    clock_provider: Optional[Callable[[], str]] = None


# ---------------------------------------------------------------------------
# PromptPacket — single prompt packet
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PromptPacket:
    """A single composed prompt packet."""

    agent_name: str
    prompt_kind: str
    prompt_text: str
    prompt_hash: str
    required_inputs: tuple[str, ...]
    expected_output_path: str
    allowed_write_paths: tuple[str, ...]
    forbidden_write_paths: tuple[str, ...]
    forbidden_commands: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    boundary_confirmations: tuple[str, ...]
    source_template_hash: Optional[str]
    source_context_hash: str
    ready_for_agent_runner_bridge: bool = True


# ---------------------------------------------------------------------------
# PromptComposerResult — result dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PromptComposerResult:
    """Result of a prompt composition operation."""

    status: str
    reason_codes: tuple[str, ...]
    pr_id: str
    branch: str
    task_title: str
    task_description_hash: str
    context_hash: str
    source_evidence: dict[str, str]
    prompt_packets: tuple[PromptPacket, ...]
    prompt_order: tuple[str, ...]
    warnings: tuple[str, ...]
    details: Optional[str]


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_PR_ID = "missing_pr_id"
REASON_MISSING_BRANCH = "missing_branch"
REASON_MISSING_TASK_TITLE = "missing_task_title"
REASON_MISSING_TASK_DESCRIPTION = "missing_task_description"
REASON_MISSING_ROADMAP = "missing_roadmap"
REASON_MISSING_AGENTS_DIR = "missing_agents_dir"
REASON_MISSING_AGENT_CONFIG = "missing_agent_config"
REASON_UNBOUNDED_PATH = "unbounded_path"

# ---------------------------------------------------------------------------
# Agent name regex
# ---------------------------------------------------------------------------

_AGENT_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")

# ---------------------------------------------------------------------------
# Forbidden commands embedded in generated prompts
# ---------------------------------------------------------------------------

_FORBIDDEN_COMMANDS: tuple[str, ...] = (
    "git add",
    "git commit",
    "git push",
    "git checkout",
    "git switch",
    "git merge",
    "git rebase",
    "git reset",
    "git clean",
    "git tag",
    "gh pr create",
    "gh release",
    "docker",
    "docker compose",
    "pip install",
    "python -m pip install",
)

# ---------------------------------------------------------------------------
# Template IDs (built-in deterministic strings)
# ---------------------------------------------------------------------------

_TEMPLATE_IDS: dict[str, str] = {
    "planner": "planner-template-v1",
    "plan-review": "plan-review-template-v1",
    "coder": "coder-template-v1",
    "precommit-review": "precommit-review-template-v1",
}


# ---------------------------------------------------------------------------
# Collect source evidence
# ---------------------------------------------------------------------------


def _collect_source_evidence(
    request: PromptComposerRequest,
) -> tuple[dict[str, str], list[str], list[str]]:
    """Collect source evidence from the filesystem.

    Returns
    -------
    tuple[dict[str, str], list[str], list[str]]
        ``(evidence, warnings, blockers)``.
    """
    evidence: dict[str, str] = {}
    warnings: list[str] = []
    blockers: list[str] = []

    # 1. ROADMAP.md evidence
    roadmap_path = os.path.join(request.repo_root, request.roadmap_path)
    if os.path.exists(roadmap_path):
        with open(roadmap_path, "r", encoding="utf-8") as f:
            roadmap_content = f.read()
        evidence["roadmap_content"] = roadmap_content
        evidence["roadmap_hash"] = hashlib.sha256(roadmap_content.encode("utf-8")).hexdigest()[:16]

        # Check for Production Line Stream
        if "Production Line Stream" in roadmap_content:
            evidence["roadmap_production_line"] = "present"
        else:
            warnings.append("ROADMAP.md does not contain 'Production Line Stream'")

        # Check for PR 0124
        if "0124" in roadmap_content:
            evidence["roadmap_pr_0124"] = "present"
        else:
            warnings.append("ROADMAP.md does not reference PR 0124")

        # Check for frozen streams
        if "Frozen until PR 0136" in roadmap_content or "frozen until" in roadmap_content.lower():
            evidence["roadmap_frozen_streams"] = "present"
        else:
            warnings.append("ROADMAP.md does not contain frozen-streams section")
    else:
        blockers.append(REASON_MISSING_ROADMAP)

    # 2. Agent config inventory
    agents_dir = os.path.join(request.repo_root, request.agents_dir)
    if os.path.isdir(agents_dir):
        agent_files = sorted([
            f for f in os.listdir(agents_dir)
            if f.endswith(".yml") and os.path.isfile(os.path.join(agents_dir, f))
        ])
        evidence["agent_configs"] = ",".join(agent_files)

        # Hash each agent config
        for agent_file in agent_files:
            agent_path = os.path.join(agents_dir, agent_file)
            try:
                with open(agent_path, "r", encoding="utf-8") as f:
                    content = f.read()
                agent_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
                evidence[f"agent_config_hash_{agent_file.replace('.yml', '')}"] = agent_hash
            except OSError:
                warnings.append(f"Cannot read agent config: {agent_file}")

        # Check for required agent configs
        required_configs = ["coder.yml", "plan-review.yml", "precommit-review.yml"]
        for cfg in required_configs:
            if cfg not in agent_files:
                warnings.append(f"Missing required agent config: {cfg}")
    else:
        blockers.append(REASON_MISSING_AGENTS_DIR)

    # 3. Review artifact schema
    schema_path = os.path.join(request.repo_root, ".project-memory", "review-artifact.schema.yml")
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_content = f.read()
        evidence["review_artifact_schema_hash"] = hashlib.sha256(schema_content.encode("utf-8")).hexdigest()[:16]
    else:
        warnings.append("review-artifact.schema.yml not found")

    # 4. Included context paths
    for i, ctx_path in enumerate(request.included_context_paths):
        full_path = os.path.join(request.repo_root, ctx_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    ctx_content = f.read()
                evidence[f"context_path_{i}"] = ctx_path
                evidence[f"context_hash_{i}"] = hashlib.sha256(ctx_content.encode("utf-8")).hexdigest()[:16]
            except OSError:
                warnings.append(f"Cannot read context path: {ctx_path}")
        else:
            warnings.append(f"Context path not found: {ctx_path}")

    return evidence, warnings, blockers


# ---------------------------------------------------------------------------
# Compute context hash
# ---------------------------------------------------------------------------


def _compute_context_hash(evidence: dict[str, str]) -> str:
    """Compute a deterministic context hash from all evidence."""
    canonical = json.dumps(evidence, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------


def _forbidden_commands_block() -> str:
    """Return the forbidden commands block for generated prompts."""
    lines = ["Forbidden commands:"]
    for cmd in _FORBIDDEN_COMMANDS:
        lines.append(f"- {cmd}")
    return "\n".join(lines)


def _safety_boundaries_block() -> str:
    """Return the safety boundaries block for generated prompts."""
    return (
        "Safety boundaries:\n"
        "- Do not execute commands.\n"
        "- Do not mutate git state.\n"
        "- Do not call providers/network/LLM from code.\n"
        "- Agent output is not evidence. Runtime-captured proof is evidence.\n"
        "- Do not edit agents/*.yml.\n"
        "- Do not edit ROADMAP.md unless the task explicitly allows roadmap work.\n"
        "- Do not edit docs/** unless the task explicitly allows docs.\n"
        "- Do not edit schemas/** unless the task explicitly allows schemas.\n"
        "- Do not edit .project-memory/post-0100/**."
    )


# ---------------------------------------------------------------------------
# Compose planner prompt
# ---------------------------------------------------------------------------


def _compose_planner_prompt(
    request: PromptComposerRequest,
    evidence: dict[str, str],
    context_hash: str,
) -> PromptPacket:
    """Compose the planner prompt packet."""
    template_id = _TEMPLATE_IDS["planner"]
    template_hash = hashlib.sha256(template_id.encode("utf-8")).hexdigest()[:16]

    roadmap_evidence = evidence.get("roadmap_content", "ROADMAP.md not available")
    agent_config_inventory = evidence.get("agent_configs", "No agent configs found")

    prompt_text = (
        f"Agent: planner\n"
        f"Task: Plan the next Ariadne PR for: {request.task_description}\n"
        f"\n"
        f"PR context:\n"
        f"- PR ID: {request.pr_id}\n"
        f"- Branch: {request.branch}\n"
        f"- Title: {request.task_title}\n"
        f"- Task: {request.task_description}\n"
        f"\n"
        f"Roadmap evidence:\n"
        f"{roadmap_evidence[:2000]}\n"
        f"\n"
        f"Repository evidence:\n"
        f"- Agent configs: {agent_config_inventory}\n"
        f"- Context hash: {context_hash}\n"
        f"\n"
        f"Expected output path: .project-memory/pr/{request.pr_id}/PLAN.md\n"
        f"\n"
        f"Allowed write paths:\n"
        f"- .project-memory/pr/{request.pr_id}/PLAN.md\n"
        f"\n"
        f"Forbidden write paths:\n"
        f"- ROADMAP.md, docs/**, schemas/**, agents/**, pyproject.toml, package.json, Makefile\n"
        f"- .project-memory/pr/{request.pr_id}/reviews/**\n"
        f"- .project-memory/post-0100/**\n"
        f"\n"
        f"{_forbidden_commands_block()}\n"
        f"\n"
        f"{_safety_boundaries_block()}\n"
        f"\n"
        f"Evidence requirements to include in PLAN.md:\n"
        f"- PR 0124 Agent Runner Bridge presence\n"
        f"- PR 0125 Prompt Composer presence\n"
        f"- agents/*.yml inventory\n"
        f"- Frozen streams until PR 0136\n"
        f"\n"
        f"You are the planner, not the coder, not the reviewer."
    )

    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:16]

    return PromptPacket(
        agent_name="planner",
        prompt_kind="planner",
        prompt_text=prompt_text,
        prompt_hash=prompt_hash,
        required_inputs=("pr_id", "branch", "task_title", "task_description"),
        expected_output_path=f".project-memory/pr/{request.pr_id}/PLAN.md",
        allowed_write_paths=(f".project-memory/pr/{request.pr_id}/PLAN.md",),
        forbidden_write_paths=(
            "ROADMAP.md", "docs/**", "schemas/**", "agents/**",
            "pyproject.toml", "package.json", "Makefile",
            f".project-memory/pr/{request.pr_id}/reviews/**",
            ".project-memory/post-0100/**",
        ),
        forbidden_commands=_FORBIDDEN_COMMANDS,
        evidence_requirements=(
            "PR 0124 Agent Runner Bridge presence",
            "PR 0125 Prompt Composer presence",
            "agents/*.yml inventory",
            "Frozen streams until PR 0136",
        ),
        boundary_confirmations=(
            "Do not execute commands",
            "Do not mutate git state",
            "Do not call providers/network/LLM from code",
            "Agent output is not evidence",
        ),
        source_template_hash=template_hash,
        source_context_hash=context_hash,
        ready_for_agent_runner_bridge=True,
    )


# ---------------------------------------------------------------------------
# Compose plan-review prompt
# ---------------------------------------------------------------------------


def _compose_plan_review_prompt(
    request: PromptComposerRequest,
    evidence: dict[str, str],
    context_hash: str,
) -> PromptPacket:
    """Compose the plan-review prompt packet."""
    template_id = _TEMPLATE_IDS["plan-review"]
    template_hash = hashlib.sha256(template_id.encode("utf-8")).hexdigest()[:16]

    roadmap_evidence = evidence.get("roadmap_content", "ROADMAP.md not available")

    prompt_text = (
        f"Agent: plan-review\n"
        f"Task: Review the PLAN.md for PR {request.pr_id}: {request.task_description}\n"
        f"\n"
        f"PR context:\n"
        f"- PR ID: {request.pr_id}\n"
        f"- Branch: {request.branch}\n"
        f"- Title: {request.task_title}\n"
        f"- Task: {request.task_description}\n"
        f"\n"
        f"Roadmap evidence:\n"
        f"{roadmap_evidence[:2000]}\n"
        f"\n"
        f"Expected output path: .project-memory/pr/{request.pr_id}/reviews/plan-review.yml\n"
        f"\n"
        f"Allowed write paths:\n"
        f"- .project-memory/pr/{request.pr_id}/reviews/plan-review.yml\n"
        f"\n"
        f"Forbidden write paths:\n"
        f"- ROADMAP.md, docs/**, schemas/**, agents/**, pyproject.toml, package.json, Makefile\n"
        f"- .project-memory/pr/{request.pr_id}/PLAN.md\n"
        f"- .project-memory/pr/{request.pr_id}/reviews/precommit-review.yml\n"
        f"- .project-memory/post-0100/**\n"
        f"\n"
        f"{_forbidden_commands_block()}\n"
        f"\n"
        f"{_safety_boundaries_block()}\n"
        f"\n"
        f"You are the plan-review agent, not the planner, not the coder."
    )

    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:16]

    return PromptPacket(
        agent_name="plan-review",
        prompt_kind="plan-review",
        prompt_text=prompt_text,
        prompt_hash=prompt_hash,
        required_inputs=("pr_id", "branch", "task_title", "task_description"),
        expected_output_path=f".project-memory/pr/{request.pr_id}/reviews/plan-review.yml",
        allowed_write_paths=(f".project-memory/pr/{request.pr_id}/reviews/plan-review.yml",),
        forbidden_write_paths=(
            "ROADMAP.md", "docs/**", "schemas/**", "agents/**",
            "pyproject.toml", "package.json", "Makefile",
            f".project-memory/pr/{request.pr_id}/PLAN.md",
            f".project-memory/pr/{request.pr_id}/reviews/precommit-review.yml",
            ".project-memory/post-0100/**",
        ),
        forbidden_commands=_FORBIDDEN_COMMANDS,
        evidence_requirements=(
            "PLAN.md exists and is readable",
            "Plan-review artifact schema matches",
        ),
        boundary_confirmations=(
            "Do not execute commands",
            "Do not mutate git state",
            "Do not call providers/network/LLM from code",
            "Agent output is not evidence",
        ),
        source_template_hash=template_hash,
        source_context_hash=context_hash,
        ready_for_agent_runner_bridge=True,
    )


# ---------------------------------------------------------------------------
# Compose coder prompt
# ---------------------------------------------------------------------------


def _compose_coder_prompt(
    request: PromptComposerRequest,
    evidence: dict[str, str],
    context_hash: str,
) -> PromptPacket:
    """Compose the coder prompt packet."""
    template_id = _TEMPLATE_IDS["coder"]
    template_hash = hashlib.sha256(template_id.encode("utf-8")).hexdigest()[:16]

    roadmap_evidence = evidence.get("roadmap_content", "ROADMAP.md not available")

    prompt_text = (
        f"Agent: coder\n"
        f"Task: Implement PR {request.pr_id}: {request.task_description}\n"
        f"\n"
        f"PR context:\n"
        f"- PR ID: {request.pr_id}\n"
        f"- Branch: {request.branch}\n"
        f"- Title: {request.task_title}\n"
        f"- Task: {request.task_description}\n"
        f"\n"
        f"Roadmap evidence:\n"
        f"{roadmap_evidence[:2000]}\n"
        f"\n"
        f"Approved PLAN.md path: .project-memory/pr/{request.pr_id}/PLAN.md\n"
        f"\n"
        f"Expected output paths:\n"
        f"- Per PLAN.md\n"
        f"\n"
        f"Allowed write paths:\n"
        f"- Per PLAN.md\n"
        f"\n"
        f"Forbidden write paths:\n"
        f"- ROADMAP.md, docs/**, schemas/**, agents/**, pyproject.toml, package.json, Makefile\n"
        f"- .project-memory/pr/{request.pr_id}/reviews/**\n"
        f"- .project-memory/post-0100/**\n"
        f"\n"
        f"{_forbidden_commands_block()}\n"
        f"\n"
        f"{_safety_boundaries_block()}\n"
        f"\n"
        f"You are the coder, not the planner, not the reviewer."
    )

    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:16]

    return PromptPacket(
        agent_name="coder",
        prompt_kind="coder",
        prompt_text=prompt_text,
        prompt_hash=prompt_hash,
        required_inputs=("pr_id", "branch", "task_title", "task_description"),
        expected_output_path=f".project-memory/pr/{request.pr_id}/PLAN.md",
        allowed_write_paths=(f".project-memory/pr/{request.pr_id}/PLAN.md",),
        forbidden_write_paths=(
            "ROADMAP.md", "docs/**", "schemas/**", "agents/**",
            "pyproject.toml", "package.json", "Makefile",
            f".project-memory/pr/{request.pr_id}/reviews/**",
            ".project-memory/post-0100/**",
        ),
        forbidden_commands=_FORBIDDEN_COMMANDS,
        evidence_requirements=(
            "Approved PLAN.md exists",
            "Implementation paths match PLAN.md",
        ),
        boundary_confirmations=(
            "Do not execute commands",
            "Do not mutate git state",
            "Do not call providers/network/LLM from code",
            "Agent output is not evidence",
        ),
        source_template_hash=template_hash,
        source_context_hash=context_hash,
        ready_for_agent_runner_bridge=True,
    )


# ---------------------------------------------------------------------------
# Compose precommit-review prompt
# ---------------------------------------------------------------------------


def _compose_precommit_review_prompt(
    request: PromptComposerRequest,
    evidence: dict[str, str],
    context_hash: str,
) -> PromptPacket:
    """Compose the precommit-review prompt packet."""
    template_id = _TEMPLATE_IDS["precommit-review"]
    template_hash = hashlib.sha256(template_id.encode("utf-8")).hexdigest()[:16]

    roadmap_evidence = evidence.get("roadmap_content", "ROADMAP.md not available")

    prompt_text = (
        f"Agent: precommit-review\n"
        f"Task: Review implementation for PR {request.pr_id}: {request.task_description}\n"
        f"\n"
        f"PR context:\n"
        f"- PR ID: {request.pr_id}\n"
        f"- Branch: {request.branch}\n"
        f"- Title: {request.task_title}\n"
        f"- Task: {request.task_description}\n"
        f"\n"
        f"Roadmap evidence:\n"
        f"{roadmap_evidence[:2000]}\n"
        f"\n"
        f"Expected output path: .project-memory/pr/{request.pr_id}/reviews/precommit-review.yml\n"
        f"\n"
        f"Allowed write paths:\n"
        f"- .project-memory/pr/{request.pr_id}/reviews/precommit-review.yml\n"
        f"\n"
        f"Forbidden write paths:\n"
        f"- ROADMAP.md, docs/**, schemas/**, agents/**, pyproject.toml, package.json, Makefile\n"
        f"- .project-memory/pr/{request.pr_id}/PLAN.md\n"
        f"- .project-memory/pr/{request.pr_id}/reviews/plan-review.yml\n"
        f"- .project-memory/post-0100/**\n"
        f"\n"
        f"{_forbidden_commands_block()}\n"
        f"\n"
        f"{_safety_boundaries_block()}\n"
        f"\n"
        f"Validation requirements:\n"
        f"- Run PLAN DRIFT GATE\n"
        f"- Run all validation commands from PLAN.md\n"
        f"- Check for .ariadne/ residue\n"
        f"- Check for forbidden legacy names\n"
        f"- Check for non-semantic placeholder strings\n"
        f"\n"
        f"You are the precommit-review agent, not the planner, not the coder."
    )

    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:16]

    return PromptPacket(
        agent_name="precommit-review",
        prompt_kind="precommit-review",
        prompt_text=prompt_text,
        prompt_hash=prompt_hash,
        required_inputs=("pr_id", "branch", "task_title", "task_description"),
        expected_output_path=f".project-memory/pr/{request.pr_id}/reviews/precommit-review.yml",
        allowed_write_paths=(f".project-memory/pr/{request.pr_id}/reviews/precommit-review.yml",),
        forbidden_write_paths=(
            "ROADMAP.md", "docs/**", "schemas/**", "agents/**",
            "pyproject.toml", "package.json", "Makefile",
            f".project-memory/pr/{request.pr_id}/PLAN.md",
            f".project-memory/pr/{request.pr_id}/reviews/plan-review.yml",
            ".project-memory/post-0100/**",
        ),
        forbidden_commands=_FORBIDDEN_COMMANDS,
        evidence_requirements=(
            "Implementation matches PLAN.md",
            "All validation commands pass",
            "No .ariadne/ residue",
        ),
        boundary_confirmations=(
            "Do not execute commands",
            "Do not mutate git state",
            "Do not call providers/network/LLM from code",
            "Agent output is not evidence",
        ),
        source_template_hash=template_hash,
        source_context_hash=context_hash,
        ready_for_agent_runner_bridge=True,
    )


# ---------------------------------------------------------------------------
# Main composition function
# ---------------------------------------------------------------------------


def compose_pr_prompts(
    request: PromptComposerRequest,
) -> PromptComposerResult:
    """Compose all four PR prompt packets.

    Parameters
    ----------
    request:
        Input parameters including PR identity, task description, and
        optional context paths.

    Returns
    -------
    PromptComposerResult
        ``status="ready"`` with four ``prompt_packets`` when composition
        succeeds.
        ``status="blocked"`` when required evidence is missing.
        ``status="failed"`` when validation fails.
    """
    codes: list[str] = []

    # 1. Validate required fields
    if not request.pr_id or request.pr_id.strip() == "":
        codes.append(REASON_MISSING_PR_ID)
    if not request.branch or request.branch.strip() == "":
        codes.append(REASON_MISSING_BRANCH)
    if not request.task_title or request.task_title.strip() == "":
        codes.append(REASON_MISSING_TASK_TITLE)
    if not request.task_description or request.task_description.strip() == "":
        codes.append(REASON_MISSING_TASK_DESCRIPTION)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Prompt composer failed:\n" + "\n".join(detail_lines)
        return PromptComposerResult(
            status=PromptComposerStatus.FAILED,
            reason_codes=tuple(codes),
            pr_id=request.pr_id,
            branch=request.branch,
            task_title=request.task_title,
            task_description_hash=hashlib.sha256(request.task_description.encode("utf-8")).hexdigest()[:16] if request.task_description else "",
            context_hash="",
            source_evidence={},
            prompt_packets=(),
            prompt_order=("planner", "plan-review", "coder", "precommit-review"),
            warnings=(),
            details=details,
        )

    # 2. Hash task description
    task_description_hash = hashlib.sha256(request.task_description.encode("utf-8")).hexdigest()[:16]

    # 3. Collect source evidence
    evidence, warnings, blockers = _collect_source_evidence(request)

    # 4. Check for blockers
    if blockers:
        codes.extend(blockers)
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Prompt composer blocked:\n" + "\n".join(detail_lines)
        return PromptComposerResult(
            status=PromptComposerStatus.BLOCKED,
            reason_codes=tuple(codes),
            pr_id=request.pr_id,
            branch=request.branch,
            task_title=request.task_title,
            task_description_hash=task_description_hash,
            context_hash="",
            source_evidence=evidence,
            prompt_packets=(),
            prompt_order=("planner", "plan-review", "coder", "precommit-review"),
            warnings=tuple(warnings),
            details=details,
        )

    # 5. Compute context hash
    context_hash = _compute_context_hash(evidence)

    # 6. Compose four prompt packets
    planner_packet = _compose_planner_prompt(request, evidence, context_hash)
    plan_review_packet = _compose_plan_review_prompt(request, evidence, context_hash)
    coder_packet = _compose_coder_prompt(request, evidence, context_hash)
    precommit_packet = _compose_precommit_review_prompt(request, evidence, context_hash)

    prompt_packets = (
        planner_packet,
        plan_review_packet,
        coder_packet,
        precommit_packet,
    )

    # 7. Determine status
    if warnings:
        status = PromptComposerStatus.READY
    else:
        status = PromptComposerStatus.READY

    return PromptComposerResult(
        status=status,
        reason_codes=tuple(codes),
        pr_id=request.pr_id,
        branch=request.branch,
        task_title=request.task_title,
        task_description_hash=task_description_hash,
        context_hash=context_hash,
        source_evidence=evidence,
        prompt_packets=prompt_packets,
        prompt_order=("planner", "plan-review", "coder", "precommit-review"),
        warnings=tuple(warnings),
        details=None,
    )

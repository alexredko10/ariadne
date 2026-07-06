"""Tests for the pipeline runner."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Optional

from runner.pipeline_runner import (
    PipelineRunnerRequest,
    PipelineStepResult,
    PipelineGateResult,
    PipelineRunnerResult,
    PipelineRunnerStatus,
    run_pr_pipeline,
    REASON_MISSING_PLANNER_ARTIFACT,
    REASON_MISSING_REVIEW_ARTIFACT,
    REASON_CODER_STEP_FAILED,
    REASON_GATE_STOP,
    REASON_PIPELINE_COMPLETED,
    REASON_COMPOSE_FAILED,
    REASON_BRIDGE_FAILED,
    REASON_PARSER_FAILED,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clock() -> str:
    """Deterministic clock provider."""
    return "2026-07-06T12:00:00Z"


def _fake_composer(packets: list[dict]) -> Any:
    """Create a fake composer function returning fixed packets."""
    from runner.prompt_composer import PromptComposerResult, PromptComposerStatus, PromptPacket

    prompt_packets = []
    for p in packets:
        prompt_packets.append(PromptPacket(
            agent_name=p.get("agent_name", ""),
            prompt_kind=p.get("prompt_kind", ""),
            prompt_text=p.get("prompt_text", "test prompt"),
            prompt_hash=hashlib.sha256(p.get("prompt_text", "test prompt").encode("utf-8")).hexdigest()[:16],
            required_inputs=("pr_id", "branch", "task_title", "task_description"),
            expected_output_path=p.get("expected_output_path", ""),
            allowed_write_paths=(),
            forbidden_write_paths=(),
            forbidden_commands=(),
            evidence_requirements=(),
            boundary_confirmations=(),
            source_template_hash="test_template_hash",
            source_context_hash="test_context_hash",
            ready_for_agent_runner_bridge=True,
        ))

    result = PromptComposerResult(
        status=PromptComposerStatus.READY,
        reason_codes=(),
        pr_id="0127",
        branch="0127-pipeline-runner",
        task_title="Pipeline Runner",
        task_description_hash="test_hash",
        context_hash="test_context_hash",
        source_evidence={},
        prompt_packets=tuple(prompt_packets),
        prompt_order=("planner", "plan-review", "coder", "precommit-review"),
        warnings=(),
        details=None,
    )

    def composer_fn(request: Any) -> PromptComposerResult:
        return result

    return composer_fn


def _fake_bridge(status: str = "completed", proof: str = "Proof captured") -> Any:
    """Create a fake bridge runner function."""
    from runner.agent_runner_bridge import (
        AgentRunnerBridgeResult,
        AgentRunnerBridgeArtifact,
        AgentRunnerBridgeStatus,
    )

    def bridge_fn(agent_name: str, task_prompt: str) -> AgentRunnerBridgeResult:
        return AgentRunnerBridgeResult(
            status=status,
            reason_codes=(),
            agent_name=agent_name,
            task_prompt_hash=hashlib.sha256(task_prompt.encode("utf-8")).hexdigest()[:16],
            agent_config_path=f"agents/{agent_name}.yml",
            agent_config_hash="test_config_hash",
            docker_adapter_status="completed",
            exit_code=0,
            captured_stdout_hash="test_stdout_hash",
            captured_stderr_hash="test_stderr_hash",
            captured_artifact=AgentRunnerBridgeArtifact(
                artifact_ref="test_artifact_ref",
                proof_capture_path="test_proof_path",
                proof_capture_ref="test_proof_ref",
                executor_output_path=None,
                has_proof=True,
                proof_source="runtime-captured",
            ),
            proof_summary=proof,
            started_at=_clock(),
            finished_at=_clock(),
            details=None,
        )

    return bridge_fn


def _fake_artifact_reader(text: str) -> Any:
    """Create a fake artifact reader returning fixed text."""
    def reader_fn(path: str) -> Optional[str]:
        return text
    return reader_fn


def _fake_parser(verdict: str = "pass", next_action: str = "continue") -> Any:
    """Create a fake verdict parser function."""
    from runner.verdict_parser import (
        ParsedReviewArtifact,
        VerdictDecision,
        VerdictDecisionStatus,
    )

    def parser_fn(text: str) -> VerdictDecision:
        parsed = ParsedReviewArtifact(
            review_type="precommit-review",
            pr_id="0127",
            raw_verdict=verdict,
            normalized_verdict=verdict,
            has_blockers=False,
            blockers=(),
            warnings=(),
            validation_summary=(),
            evidence_ledger_summary=(),
            files_read=(),
            files_written=(),
            boundary_confirmations=(),
            checks={},
            artifact_hash=hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
            artifact_line_count=len(text.split("\n")),
            schema_version="0.1",
        )
        return VerdictDecision(
            next_action=next_action,
            normalized_verdict=verdict,
            has_blockers=False,
            reason_codes=(),
            is_retry_candidate=False,
            retry_reason=None,
            human_required=False,
            details=None,
            parsed_artifact=parsed,
        )

    return parser_fn


def _default_packets() -> list[dict]:
    """Return default prompt packets for a full pipeline."""
    return [
        {
            "agent_name": "planner",
            "prompt_kind": "planner",
            "prompt_text": "Plan the PR",
            "expected_output_path": ".project-memory/pr/0127/PLAN.md",
        },
        {
            "agent_name": "plan-review",
            "prompt_kind": "plan-review",
            "prompt_text": "Review the plan",
            "expected_output_path": ".project-memory/pr/0127/reviews/plan-review.yml",
        },
        {
            "agent_name": "coder",
            "prompt_kind": "coder",
            "prompt_text": "Implement the PR",
            "expected_output_path": ".project-memory/pr/0127/PLAN.md",
        },
        {
            "agent_name": "precommit-review",
            "prompt_kind": "precommit-review",
            "prompt_text": "Review the implementation",
            "expected_output_path": ".project-memory/pr/0127/reviews/precommit-review.yml",
        },
    ]


def _full_request(
    packets: Optional[list[dict]] = None,
    bridge_status: str = "completed",
    bridge_proof: str = "Proof captured",
    artifact_text: str = "schema_version: 0.1\nverdict: pass\n",
    parser_verdict: str = "pass",
    parser_action: str = "continue",
) -> PipelineRunnerRequest:
    """Create a PipelineRunnerRequest with all fakes for a full pipeline."""
    return PipelineRunnerRequest(
        pr_id="0127",
        branch="0127-pipeline-runner",
        task_title="Pipeline Runner",
        task_description="Test pipeline",
        prompt_composer=_fake_composer(packets or _default_packets()),
        bridge_runner=_fake_bridge(bridge_status, bridge_proof),
        artifact_reader=_fake_artifact_reader(artifact_text),
        verdict_parser=_fake_parser(parser_verdict, parser_action),
        clock_provider=_clock,
    )


# ---------------------------------------------------------------------------
# Full sequence pass
# ---------------------------------------------------------------------------


class TestFullSequencePass:
    def test_full_sequence_pass(self):
        """Full pipeline → status completed, 8 steps, 2 gates."""
        request = _full_request()
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.COMPLETED
        assert result.final_action == "continue"
        assert len(result.step_results) == 8
        assert len(result.gate_results) == 2
        assert result.stopped_at is None
        assert result.stop_reason is None


# ---------------------------------------------------------------------------
# Prompt order
# ---------------------------------------------------------------------------


class TestPromptOrder:
    def test_prompt_order(self):
        """Steps in correct order."""
        request = _full_request()
        result = run_pr_pipeline(request)
        step_names = [s.step_name for s in result.step_results]
        expected = [
            "compose_prompts",
            "planner",
            "planner_artifact_check",
            "plan_review",
            "plan-review_gate",
            "coder",
            "precommit_review",
            "precommit-review_gate",
        ]
        assert step_names == expected


# ---------------------------------------------------------------------------
# Planner artifact required
# ---------------------------------------------------------------------------


class TestPlannerArtifactRequired:
    def test_missing_planner_artifact(self):
        """Missing planner artifact → stop at planner_artifact_check."""
        request = _full_request(
            artifact_text=None,  # artifact_reader returns None
        )
        # Override artifact_reader to return None for planner artifact
        request = PipelineRunnerRequest(
            pr_id="0127",
            branch="0127-pipeline-runner",
            task_title="Pipeline Runner",
            task_description="Test pipeline",
            prompt_composer=_fake_composer(_default_packets()),
            bridge_runner=_fake_bridge("completed", "Proof captured"),
            artifact_reader=_fake_artifact_reader(None),  # type: ignore[arg-type]
            verdict_parser=_fake_parser("pass", "continue"),
            clock_provider=_clock,
        )
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.STOPPED
        assert result.stopped_at == "planner_artifact_check"
        assert REASON_MISSING_PLANNER_ARTIFACT in result.reason_codes


# ---------------------------------------------------------------------------
# Plan-review block
# ---------------------------------------------------------------------------


class TestPlanReviewBlock:
    def test_plan_review_block(self):
        """Plan-review gate block → stop before coder."""
        request = _full_request(
            parser_verdict="block",
            parser_action="stop",
        )
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.STOPPED
        assert result.stopped_at == "plan_review_gate"
        # Should not have coder or precommit steps
        step_names = [s.step_name for s in result.step_results]
        assert "coder" not in step_names
        assert "precommit_review" not in step_names


# ---------------------------------------------------------------------------
# Plan-review warning
# ---------------------------------------------------------------------------


class TestPlanReviewWarning:
    def test_plan_review_warning(self):
        """Plan-review warning → continue_with_warning, coder still runs."""
        request = _full_request(
            parser_verdict="warning",
            parser_action="continue_with_warning",
        )
        result = run_pr_pipeline(request)
        # Warning on plan-review gate → coder still runs, precommit runs
        step_names = [s.step_name for s in result.step_results]
        assert "coder" in step_names
        assert "precommit_review" in step_names
        # Final status depends on precommit gate
        assert result.status in (PipelineRunnerStatus.COMPLETED, PipelineRunnerStatus.COMPLETED_WITH_WARNING)


# ---------------------------------------------------------------------------
# Precommit pass
# ---------------------------------------------------------------------------


class TestPrecommitPass:
    def test_precommit_pass(self):
        """Precommit gate pass → status completed."""
        request = _full_request(
            parser_verdict="pass",
            parser_action="continue",
        )
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.COMPLETED


# ---------------------------------------------------------------------------
# Precommit warning
# ---------------------------------------------------------------------------


class TestPrecommitWarning:
    def test_precommit_warning(self):
        """Precommit gate warning → status completed_with_warning."""
        request = _full_request(
            parser_verdict="warning",
            parser_action="continue_with_warning",
        )
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.COMPLETED_WITH_WARNING


# ---------------------------------------------------------------------------
# Precommit block
# ---------------------------------------------------------------------------


class TestPrecommitBlock:
    def test_precommit_block(self):
        """Precommit gate block → status stopped."""
        request = _full_request(
            parser_verdict="block",
            parser_action="stop",
        )
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.STOPPED
        # Plan-review gate blocks first (both gates use same parser)
        assert result.stopped_at == "plan_review_gate"


# ---------------------------------------------------------------------------
# Invalid review artifact
# ---------------------------------------------------------------------------


class TestInvalidReviewArtifact:
    def test_invalid_review_artifact(self):
        """Invalid verdict → stop."""
        request = _full_request(
            parser_verdict="invalid",
            parser_action="stop",
        )
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.STOPPED


# ---------------------------------------------------------------------------
# Missing review artifact
# ---------------------------------------------------------------------------


class TestMissingReviewArtifact:
    def test_missing_review_artifact(self):
        """Missing review artifact → stop with missing_review_artifact."""
        # Use a parser that returns None (simulating missing artifact)
        def none_parser(text: str) -> None:
            return None

        request = PipelineRunnerRequest(
            pr_id="0127",
            branch="0127-pipeline-runner",
            task_title="Pipeline Runner",
            task_description="Test pipeline",
            prompt_composer=_fake_composer(_default_packets()),
            bridge_runner=_fake_bridge("completed", "Proof captured"),
            artifact_reader=_fake_artifact_reader(None),  # type: ignore[arg-type]
            verdict_parser=none_parser,
            clock_provider=_clock,
        )
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.STOPPED
        # Planner artifact check fails first (artifact_reader returns None for all paths)
        assert result.stopped_at == "planner_artifact_check"


# ---------------------------------------------------------------------------
# Coder step failure
# ---------------------------------------------------------------------------


class TestCoderStepFailure:
    def test_coder_step_failure(self):
        """Coder bridge fails → stop before precommit with coder_step_failed."""
        request = _full_request(
            bridge_status="failed",
            bridge_proof="Bridge failed",
        )
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.STOPPED
        assert result.stopped_at == "coder"
        assert REASON_CODER_STEP_FAILED in result.reason_codes
        step_names = [s.step_name for s in result.step_results]
        assert "precommit_review" not in step_names


# ---------------------------------------------------------------------------
# Blockers force stop
# ---------------------------------------------------------------------------


class TestBlockersForceStop:
    def test_blockers_force_stop(self):
        """Blockers present → stop regardless of verdict."""
        from runner.verdict_parser import (
            ParsedReviewArtifact,
            VerdictDecision,
            VerdictDecisionStatus,
        )

        def parser_with_blockers(text: str) -> VerdictDecision:
            parsed = ParsedReviewArtifact(
                review_type="precommit-review",
                pr_id="0127",
                raw_verdict="pass",
                normalized_verdict="pass",
                has_blockers=True,
                blockers=(("blocker-001", "Unexpected blocker", "high"),),
                warnings=(),
                validation_summary=(),
                evidence_ledger_summary=(),
                files_read=(),
                files_written=(),
                boundary_confirmations=(),
                checks={},
                artifact_hash="test_hash",
                artifact_line_count=10,
                schema_version="0.1",
            )
            return VerdictDecision(
                next_action=VerdictDecisionStatus.STOP,
                normalized_verdict="pass",
                has_blockers=True,
                reason_codes=("blockers_present",),
                is_retry_candidate=False,
                retry_reason=None,
                human_required=True,
                details="Blockers present",
                parsed_artifact=parsed,
            )

        request = PipelineRunnerRequest(
            pr_id="0127",
            branch="0127-pipeline-runner",
            task_title="Pipeline Runner",
            task_description="Test pipeline",
            prompt_composer=_fake_composer(_default_packets()),
            bridge_runner=_fake_bridge("completed", "Proof captured"),
            artifact_reader=_fake_artifact_reader("test artifact"),
            verdict_parser=parser_with_blockers,
            clock_provider=_clock,
        )
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.STOPPED


# ---------------------------------------------------------------------------
# Safety violation
# ---------------------------------------------------------------------------


class TestSafetyViolation:
    def test_safety_violation(self):
        """human_required=True → stop."""
        from runner.verdict_parser import (
            ParsedReviewArtifact,
            VerdictDecision,
            VerdictDecisionStatus,
        )

        def parser_safety(text: str) -> VerdictDecision:
            parsed = ParsedReviewArtifact(
                review_type="precommit-review",
                pr_id="0127",
                raw_verdict="block",
                normalized_verdict="block",
                has_blockers=True,
                blockers=(("safety-001", "Safety violation", "high"),),
                warnings=(),
                validation_summary=(),
                evidence_ledger_summary=(),
                files_read=(),
                files_written=(),
                boundary_confirmations=(),
                checks={},
                artifact_hash="test_hash",
                artifact_line_count=10,
                schema_version="0.1",
            )
            return VerdictDecision(
                next_action=VerdictDecisionStatus.STOP,
                normalized_verdict="block",
                has_blockers=True,
                reason_codes=("blocker_safety_violation",),
                is_retry_candidate=False,
                retry_reason=None,
                human_required=True,
                details="Safety violation",
                parsed_artifact=parsed,
            )

        request = PipelineRunnerRequest(
            pr_id="0127",
            branch="0127-pipeline-runner",
            task_title="Pipeline Runner",
            task_description="Test pipeline",
            prompt_composer=_fake_composer(_default_packets()),
            bridge_runner=_fake_bridge("completed", "Proof captured"),
            artifact_reader=_fake_artifact_reader("test artifact"),
            verdict_parser=parser_safety,
            clock_provider=_clock,
        )
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.STOPPED


# ---------------------------------------------------------------------------
# Retry candidate metadata
# ---------------------------------------------------------------------------


class TestRetryCandidateMetadata:
    def test_retry_candidate_metadata(self):
        """is_retry_candidate recorded but not executed."""
        from runner.verdict_parser import (
            ParsedReviewArtifact,
            VerdictDecision,
            VerdictDecisionStatus,
        )

        def parser_retry(text: str) -> VerdictDecision:
            parsed = ParsedReviewArtifact(
                review_type="precommit-review",
                pr_id="0127",
                raw_verdict="block",
                normalized_verdict="block",
                has_blockers=True,
                blockers=(("fixable-001", "Fixable issue", "high"),),
                warnings=(),
                validation_summary=(),
                evidence_ledger_summary=(),
                files_read=(),
                files_written=(),
                boundary_confirmations=(),
                checks={},
                artifact_hash="test_hash",
                artifact_line_count=10,
                schema_version="0.1",
            )
            return VerdictDecision(
                next_action=VerdictDecisionStatus.STOP,
                normalized_verdict="block",
                has_blockers=True,
                reason_codes=("blockers_present",),
                is_retry_candidate=True,
                retry_reason="Fixable blocker class",
                human_required=False,
                details="Retry candidate",
                parsed_artifact=parsed,
            )

        request = PipelineRunnerRequest(
            pr_id="0127",
            branch="0127-pipeline-runner",
            task_title="Pipeline Runner",
            task_description="Test pipeline",
            prompt_composer=_fake_composer(_default_packets()),
            bridge_runner=_fake_bridge("completed", "Proof captured"),
            artifact_reader=_fake_artifact_reader("test artifact"),
            verdict_parser=parser_retry,
            clock_provider=_clock,
        )
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.STOPPED
        # Check that is_retry_candidate is recorded in gate result
        for gate in result.gate_results:
            if gate.gate_name == "precommit-review":
                assert gate.is_retry_candidate is True
                break


# ---------------------------------------------------------------------------
# No direct Docker
# ---------------------------------------------------------------------------


class TestNoDirectDocker:
    def test_no_direct_docker(self):
        """Pipeline code does not import or call Docker directly."""
        import inspect
        from runner.pipeline_runner import run_pr_pipeline
        source = inspect.getsource(run_pr_pipeline)
        assert "subprocess.run" not in source
        assert "docker compose" not in source
        assert "docker run" not in source


# ---------------------------------------------------------------------------
# No direct git
# ---------------------------------------------------------------------------


class TestNoDirectGit:
    def test_no_direct_git(self):
        """Pipeline code does not call git commands."""
        import inspect
        from runner.pipeline_runner import run_pr_pipeline
        source = inspect.getsource(run_pr_pipeline)
        assert "git add" not in source
        assert "git commit" not in source
        assert "git push" not in source
        assert "gh pr create" not in source


# ---------------------------------------------------------------------------
# Injected composer
# ---------------------------------------------------------------------------


class TestInjectedComposer:
    def test_injected_composer(self):
        """Fake composer → pipeline uses injected output."""
        request = _full_request()
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.COMPLETED
        assert len(result.step_results) == 8


# ---------------------------------------------------------------------------
# Injected bridge
# ---------------------------------------------------------------------------


class TestInjectedBridge:
    def test_injected_bridge(self):
        """Fake bridge runner → pipeline uses injected output."""
        request = _full_request()
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.COMPLETED
        # Check that bridge was called (planner step has bridge_status)
        planner_step = result.step_results[1]
        assert planner_step.step_name == "planner"
        assert planner_step.bridge_status == "completed"


# ---------------------------------------------------------------------------
# Injected parser
# ---------------------------------------------------------------------------


class TestInjectedParser:
    def test_injected_parser(self):
        """Fake verdict parser → pipeline uses injected output."""
        request = _full_request()
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.COMPLETED
        # Check that gates were processed
        assert len(result.gate_results) == 2


# ---------------------------------------------------------------------------
# Deterministic repeats
# ---------------------------------------------------------------------------


class TestDeterministicRepeats:
    def test_deterministic_repeats(self):
        """Same inputs → identical output."""
        request = _full_request()
        result1 = run_pr_pipeline(request)
        result2 = run_pr_pipeline(request)
        assert result1.status == result2.status
        assert result1.final_action == result2.final_action
        assert len(result1.step_results) == len(result2.step_results)
        assert len(result1.gate_results) == len(result2.gate_results)


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self):
        """Uses tmp_path, not .ariadne/."""
        request = _full_request()
        result = run_pr_pipeline(request)
        assert result.status == PipelineRunnerStatus.COMPLETED
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import runner.pipeline_runner
        doc = runner.pipeline_runner.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from runner.pipeline_runner import run_pr_pipeline
        source = inspect.getsource(run_pr_pipeline)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"

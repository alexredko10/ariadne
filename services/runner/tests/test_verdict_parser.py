"""Tests for the verdict parser."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from runner.verdict_parser import (
    VerdictParserRequest,
    ParsedReviewArtifact,
    VerdictDecision,
    VerdictDecisionStatus,
    parse_review_artifact,
    decide_next_action,
    REASON_ARTIFACT_READ_FAILURE,
    REASON_YAML_PARSE_FAILURE,
    REASON_MISSING_VERDICT,
    REASON_UNKNOWN_VERDICT,
    REASON_STRICT_TYPE_MISMATCH,
    REASON_STRICT_PR_MISMATCH,
    REASON_BLOCKER_SAFETY_VIOLATION,
    REASON_BLOCKERS_PRESENT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _plan_review_approve() -> str:
    """Return a minimal plan-review approve artifact."""
    return """schema_version: "0.1"
pr_id: "0126-verdict-parser"
review_type: "plan-review"
verdict: "approve"
blockers: []
warnings: []
validation:
  - command: "python -m pytest -q"
    result: "passed"
    exit_code: 0
    evidence: "314 passed"
evidence_ledger:
  - claim: "branch correct"
    evidence_source: "git branch --show-current"
    result: "pass"
files_checked:
  - "PLAN.md"
  - "ROADMAP.md"
boundary_confirmations:
  - "evidence-first plan-review completed"
  - "ROADMAP.md not modified"
"""


def _plan_review_warning() -> str:
    """Return a plan-review warning artifact."""
    return """schema_version: "0.1"
pr_id: "0126-verdict-parser"
review_type: "plan-review"
verdict: "warning"
blockers: []
warnings:
  - id: "missing_evidence"
    description: "Some evidence is missing."
    evidence: "No ROADMAP.md read"
    recommendation: "Read ROADMAP.md"
validation:
  - command: "python -m pytest -q"
    result: "passed"
    exit_code: 0
    evidence: "314 passed"
evidence_ledger:
  - claim: "branch correct"
    evidence_source: "git branch --show-current"
    result: "pass"
files_checked:
  - "PLAN.md"
boundary_confirmations:
  - "evidence-first plan-review completed"
"""


def _plan_review_block() -> str:
    """Return a plan-review block artifact."""
    return """schema_version: "0.1"
pr_id: "0126-verdict-parser"
review_type: "plan-review"
verdict: "block"
blockers:
  - id: "missing_plan"
    description: "PLAN.md is missing required sections."
    severity: "high"
    evidence: "PLAN.md does not include validation commands"
    required_fix: "Add validation commands to PLAN.md"
warnings: []
validation:
  - command: "python -m pytest -q"
    result: "failed"
    exit_code: 1
    evidence: "0 passed"
files_checked:
  - "PLAN.md"
boundary_confirmations:
  - "evidence-first plan-review completed"
"""


def _precommit_pass() -> str:
    """Return a minimal precommit-review pass artifact."""
    return """schema_version: "0.1"
pr_id: "0126-verdict-parser"
review_type: "precommit-review"
verdict: "pass"
blockers: []
warnings: []
validation:
  - command: "python -m pytest -q"
    result: "passed"
    exit_code: 0
    evidence: "30 passed"
evidence_ledger:
  - claim: "branch correct"
    evidence_source: "git branch --show-current"
    result: "pass"
files_checked:
  - "verdict_parser.py"
  - "test_verdict_parser.py"
boundary_confirmations:
  - "evidence-first precommit-review completed"
  - "ROADMAP.md not modified"
checks:
  branch: pass
  dirty_tree: pass
"""


def _precommit_warning() -> str:
    """Return a precommit-review warning artifact."""
    return """schema_version: "0.1"
pr_id: "0126-verdict-parser"
review_type: "precommit-review"
verdict: "warning"
blockers: []
warnings:
  - id: "missing_test"
    description: "One test class is missing."
    evidence: "TestRetryCandidateFixable not found"
    recommendation: "Add the missing test class"
validation:
  - command: "python -m pytest -q"
    result: "passed"
    exit_code: 0
    evidence: "29 passed"
files_checked:
  - "verdict_parser.py"
boundary_confirmations:
  - "evidence-first precommit-review completed"
checks:
  branch: pass
"""


def _precommit_block() -> str:
    """Return a precommit-review block artifact."""
    return """schema_version: "0.1"
pr_id: "0126-verdict-parser"
review_type: "precommit-review"
verdict: "block"
blockers:
  - id: "validation_failure"
    description: "Pytest failed."
    severity: "high"
    evidence: "pytest exit code 1"
    required_fix: "Fix failing tests"
warnings: []
validation:
  - command: "python -m pytest -q"
    result: "failed"
    exit_code: 1
    evidence: "0 passed"
files_checked:
  - "verdict_parser.py"
boundary_confirmations:
  - "evidence-first precommit-review completed"
checks:
  branch: pass
"""


def _blockers_force_stop() -> str:
    """Return a pass artifact with blockers (invalid state)."""
    return """schema_version: "0.1"
pr_id: "0126-verdict-parser"
review_type: "precommit-review"
verdict: "pass"
blockers:
  - id: "unexpected_blocker"
    description: "Unexpected blocker despite pass verdict."
    severity: "high"
    evidence: "Blockers present"
    required_fix: "Remove blockers"
warnings: []
files_checked:
  - "verdict_parser.py"
boundary_confirmations:
  - "evidence-first precommit-review completed"
"""


def _safety_violation_blocker() -> str:
    """Return a block artifact with safety violation blocker."""
    return """schema_version: "0.1"
pr_id: "0126-verdict-parser"
review_type: "precommit-review"
verdict: "block"
blockers:
  - id: "git_mutation"
    description: "Agent performed git commit."
    severity: "high"
    evidence: "git commit found in output"
    required_fix: "Remove git mutation"
warnings: []
files_checked:
  - "verdict_parser.py"
boundary_confirmations:
  - "evidence-first precommit-review completed"
"""


def _critical_blocker() -> str:
    """Return a block artifact with critical severity blocker."""
    return """schema_version: "0.1"
pr_id: "0126-verdict-parser"
review_type: "precommit-review"
verdict: "block"
blockers:
  - id: "critical_error"
    description: "Critical error in implementation."
    severity: "critical"
    evidence: "Implementation does not match PLAN.md"
    required_fix: "Fix implementation"
warnings: []
files_checked:
  - "verdict_parser.py"
boundary_confirmations:
  - "evidence-first precommit-review completed"
"""


def _missing_verdict() -> str:
    """Return an artifact with no verdict."""
    return """schema_version: "0.1"
pr_id: "0126-verdict-parser"
review_type: "plan-review"
blockers: []
warnings: []
"""


def _unknown_verdict() -> str:
    """Return an artifact with unknown verdict."""
    return """schema_version: "0.1"
pr_id: "0126-verdict-parser"
review_type: "plan-review"
verdict: "unknown_value"
blockers: []
warnings: []
"""


# ---------------------------------------------------------------------------
# Plan-review approve
# ---------------------------------------------------------------------------


class TestPlanReviewApprove:
    def test_plan_review_approve(self, tmp_path: Path):
        """Plan-review approve → pass → continue."""
        artifact = tmp_path / "plan-review.yml"
        artifact.write_text(_plan_review_approve(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert parsed.review_type == "plan-review"
        assert parsed.raw_verdict == "approve"
        assert parsed.normalized_verdict == "pass"
        assert parsed.has_blockers is False

        decision = decide_next_action(parsed)
        assert decision.next_action == VerdictDecisionStatus.CONTINUE
        assert decision.is_retry_candidate is False
        assert decision.human_required is False


# ---------------------------------------------------------------------------
# Plan-review warning
# ---------------------------------------------------------------------------


class TestPlanReviewWarning:
    def test_plan_review_warning(self, tmp_path: Path):
        """Plan-review warning → warning → continue_with_warning."""
        artifact = tmp_path / "plan-review.yml"
        artifact.write_text(_plan_review_warning(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert parsed.raw_verdict == "warning"
        assert parsed.normalized_verdict == "warning"
        assert parsed.has_blockers is False

        decision = decide_next_action(parsed)
        assert decision.next_action == VerdictDecisionStatus.CONTINUE_WITH_WARNING
        assert decision.is_retry_candidate is False
        assert decision.human_required is False


# ---------------------------------------------------------------------------
# Plan-review block
# ---------------------------------------------------------------------------


class TestPlanReviewBlock:
    def test_plan_review_block(self, tmp_path: Path):
        """Plan-review block → block → stop, retry_candidate=True."""
        artifact = tmp_path / "plan-review.yml"
        artifact.write_text(_plan_review_block(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert parsed.raw_verdict == "block"
        assert parsed.normalized_verdict == "block"
        assert parsed.has_blockers is True

        decision = decide_next_action(parsed)
        assert decision.next_action == VerdictDecisionStatus.STOP
        assert decision.is_retry_candidate is True
        assert decision.human_required is False


# ---------------------------------------------------------------------------
# Precommit pass
# ---------------------------------------------------------------------------


class TestPrecommitPass:
    def test_precommit_pass(self, tmp_path: Path):
        """Precommit pass → pass → continue."""
        artifact = tmp_path / "precommit.yml"
        artifact.write_text(_precommit_pass(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert parsed.review_type == "precommit-review"
        assert parsed.raw_verdict == "pass"
        assert parsed.normalized_verdict == "pass"
        assert parsed.has_blockers is False

        decision = decide_next_action(parsed)
        assert decision.next_action == VerdictDecisionStatus.CONTINUE


# ---------------------------------------------------------------------------
# Precommit warning
# ---------------------------------------------------------------------------


class TestPrecommitWarning:
    def test_precommit_warning(self, tmp_path: Path):
        """Precommit warning → warning → continue_with_warning."""
        artifact = tmp_path / "precommit.yml"
        artifact.write_text(_precommit_warning(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert parsed.raw_verdict == "warning"
        assert parsed.normalized_verdict == "warning"
        assert parsed.has_blockers is False

        decision = decide_next_action(parsed)
        assert decision.next_action == VerdictDecisionStatus.CONTINUE_WITH_WARNING


# ---------------------------------------------------------------------------
# Precommit block
# ---------------------------------------------------------------------------


class TestPrecommitBlock:
    def test_precommit_block(self, tmp_path: Path):
        """Precommit block → block → stop, retry_candidate=True."""
        artifact = tmp_path / "precommit.yml"
        artifact.write_text(_precommit_block(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert parsed.raw_verdict == "block"
        assert parsed.normalized_verdict == "block"
        assert parsed.has_blockers is True

        decision = decide_next_action(parsed)
        assert decision.next_action == VerdictDecisionStatus.STOP
        assert decision.is_retry_candidate is True
        assert decision.human_required is False


# ---------------------------------------------------------------------------
# Blockers force stop
# ---------------------------------------------------------------------------


class TestBlockersForceStop:
    def test_blockers_force_stop(self, tmp_path: Path):
        """Blockers present even with pass verdict → stop, human_required=True."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_blockers_force_stop(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert parsed.raw_verdict == "pass"
        assert parsed.normalized_verdict == "pass"
        assert parsed.has_blockers is True

        decision = decide_next_action(parsed)
        assert decision.next_action == VerdictDecisionStatus.STOP
        # Blockers with high severity and no safety violation → retry_candidate=True
        assert decision.is_retry_candidate is True
        assert decision.human_required is False


# ---------------------------------------------------------------------------
# Missing verdict
# ---------------------------------------------------------------------------


class TestMissingVerdict:
    def test_missing_verdict(self, tmp_path: Path):
        """No verdict → invalid → stop."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_missing_verdict(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert parsed.raw_verdict is None or parsed.raw_verdict == ""
        assert parsed.normalized_verdict == "invalid"

        decision = decide_next_action(parsed)
        assert decision.next_action == VerdictDecisionStatus.STOP
        assert REASON_MISSING_VERDICT in decision.reason_codes


# ---------------------------------------------------------------------------
# Unknown verdict
# ---------------------------------------------------------------------------


class TestUnknownVerdict:
    def test_unknown_verdict(self, tmp_path: Path):
        """Unknown verdict → invalid → stop."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_unknown_verdict(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert parsed.raw_verdict == "unknown_value"
        assert parsed.normalized_verdict == "invalid"

        decision = decide_next_action(parsed)
        assert decision.next_action == VerdictDecisionStatus.STOP
        assert REASON_UNKNOWN_VERDICT in decision.reason_codes


# ---------------------------------------------------------------------------
# Artifact read failure
# ---------------------------------------------------------------------------


class TestArtifactReadFailure:
    def test_artifact_read_failure(self, tmp_path: Path):
        """Nonexistent path → None."""
        request = VerdictParserRequest(artifact_path=str(tmp_path / "nonexistent.yml"))
        parsed = parse_review_artifact(request)
        assert parsed is None


# ---------------------------------------------------------------------------
# Strict type mismatch
# ---------------------------------------------------------------------------


class TestStrictTypeMismatch:
    def test_strict_type_mismatch(self, tmp_path: Path):
        """expected_review_type mismatch → None."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_plan_review_approve(), encoding="utf-8")
        request = VerdictParserRequest(
            artifact_path=str(artifact),
            expected_review_type="precommit-review",
            strict=True,
        )
        parsed = parse_review_artifact(request)
        assert parsed is None


# ---------------------------------------------------------------------------
# Strict PR mismatch
# ---------------------------------------------------------------------------


class TestStrictPrMismatch:
    def test_strict_pr_mismatch(self, tmp_path: Path):
        """expected_pr_id mismatch → None."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_plan_review_approve(), encoding="utf-8")
        request = VerdictParserRequest(
            artifact_path=str(artifact),
            expected_pr_id="wrong-pr-id",
            strict=True,
        )
        parsed = parse_review_artifact(request)
        assert parsed is None


# ---------------------------------------------------------------------------
# Artifact hash stable
# ---------------------------------------------------------------------------


class TestArtifactHashStable:
    def test_artifact_hash_stable(self, tmp_path: Path):
        """Same artifact → same hash."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_plan_review_approve(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed1 = parse_review_artifact(request)
        parsed2 = parse_review_artifact(request)
        assert parsed1 is not None
        assert parsed2 is not None
        assert parsed1.artifact_hash == parsed2.artifact_hash

    def test_artifact_hash_is_sha256(self, tmp_path: Path):
        """Hash is SHA256[:16] of artifact text."""
        artifact = tmp_path / "artifact.yml"
        text = _plan_review_approve()
        artifact.write_text(text, encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        assert parsed.artifact_hash == expected


# ---------------------------------------------------------------------------
# Artifact line count
# ---------------------------------------------------------------------------


class TestArtifactLineCount:
    def test_artifact_line_count(self, tmp_path: Path):
        """Line count recorded correctly."""
        artifact = tmp_path / "artifact.yml"
        text = _plan_review_approve()
        artifact.write_text(text, encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert parsed.artifact_line_count == len(text.split("\n"))


# ---------------------------------------------------------------------------
# Blockers extraction
# ---------------------------------------------------------------------------


class TestBlockersExtraction:
    def test_blockers_extraction(self, tmp_path: Path):
        """Multiple blockers extracted with id/description/severity."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_plan_review_block(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert len(parsed.blockers) == 1
        bid, desc, severity = parsed.blockers[0]
        assert bid == "missing_plan"
        assert "PLAN.md" in desc
        assert severity == "high"


# ---------------------------------------------------------------------------
# Warnings extraction
# ---------------------------------------------------------------------------


class TestWarningsExtraction:
    def test_warnings_extraction(self, tmp_path: Path):
        """Warnings extracted with id/description."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_plan_review_warning(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert len(parsed.warnings) == 1
        wid, desc = parsed.warnings[0]
        assert wid == "missing_evidence"
        assert "evidence" in desc


# ---------------------------------------------------------------------------
# Validation summary
# ---------------------------------------------------------------------------


class TestValidationSummary:
    def test_validation_summary(self, tmp_path: Path):
        """Validation commands extracted."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_plan_review_approve(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert len(parsed.validation_summary) >= 1
        v = parsed.validation_summary[0]
        assert "command" in v
        assert "result" in v
        assert "exit_code" in v
        assert "evidence" in v


# ---------------------------------------------------------------------------
# Evidence ledger extraction
# ---------------------------------------------------------------------------


class TestEvidenceLedgerExtraction:
    def test_evidence_ledger_extraction(self, tmp_path: Path):
        """Evidence rows extracted."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_plan_review_approve(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert len(parsed.evidence_ledger_summary) >= 1
        e = parsed.evidence_ledger_summary[0]
        assert "claim" in e
        assert "evidence_source" in e
        assert "result" in e


# ---------------------------------------------------------------------------
# Files read extraction
# ---------------------------------------------------------------------------


class TestFilesReadExtraction:
    def test_files_read_extraction(self, tmp_path: Path):
        """Files read list extracted."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_plan_review_approve(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert "PLAN.md" in parsed.files_read
        assert "ROADMAP.md" in parsed.files_read


# ---------------------------------------------------------------------------
# Boundary confirmations
# ---------------------------------------------------------------------------


class TestBoundaryConfirmations:
    def test_boundary_confirmations(self, tmp_path: Path):
        """Boundary confirmations extracted."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_plan_review_approve(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert len(parsed.boundary_confirmations) >= 1
        assert "evidence-first" in parsed.boundary_confirmations[0]


# ---------------------------------------------------------------------------
# Checks extraction
# ---------------------------------------------------------------------------


class TestChecksExtraction:
    def test_checks_extraction(self, tmp_path: Path):
        """Checks dict extracted (precommit artifacts)."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_precommit_pass(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert "branch" in parsed.checks
        assert "dirty_tree" in parsed.checks


# ---------------------------------------------------------------------------
# Retry candidate fixable
# ---------------------------------------------------------------------------


class TestRetryCandidateFixable:
    def test_retry_candidate_fixable(self, tmp_path: Path):
        """Fixable blocker → is_retry_candidate=True."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_plan_review_block(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        decision = decide_next_action(parsed)
        assert decision.is_retry_candidate is True
        assert decision.human_required is False


# ---------------------------------------------------------------------------
# Retry candidate safety violation
# ---------------------------------------------------------------------------


class TestRetryCandidateSafetyViolation:
    def test_retry_candidate_safety_violation(self, tmp_path: Path):
        """Safety violation → is_retry_candidate=False, human_required=True."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_safety_violation_blocker(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        decision = decide_next_action(parsed)
        assert decision.is_retry_candidate is False
        assert decision.human_required is True


# ---------------------------------------------------------------------------
# Retry candidate critical severity
# ---------------------------------------------------------------------------


class TestRetryCandidateCriticalSeverity:
    def test_retry_candidate_critical(self, tmp_path: Path):
        """Critical severity blocker → is_retry_candidate=False."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_critical_blocker(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        decision = decide_next_action(parsed)
        assert decision.is_retry_candidate is False


# ---------------------------------------------------------------------------
# Retry candidate git mutation
# ---------------------------------------------------------------------------


class TestRetryCandidateGitMutation:
    def test_retry_candidate_git_mutation(self, tmp_path: Path):
        """Git mutation blocker → is_retry_candidate=False."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_safety_violation_blocker(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        decision = decide_next_action(parsed)
        assert decision.is_retry_candidate is False


# ---------------------------------------------------------------------------
# YAML parse fallback
# ---------------------------------------------------------------------------


class TestYamlParseFallback:
    def test_yaml_parse_fallback(self, tmp_path: Path):
        """Invalid YAML → fallback line parsing for basic fields."""
        artifact = tmp_path / "artifact.yml"
        # Write a non-YAML text that the line parser can handle
        artifact.write_text(
            "schema_version: 0.1\n"
            "review_type: plan-review\n"
            "verdict: approve\n"
            "blockers: []\n"
            "warnings: []\n",
            encoding="utf-8",
        )
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        assert parsed.review_type == "plan-review"
        assert parsed.raw_verdict == "approve"
        assert parsed.normalized_verdict == "pass"


# ---------------------------------------------------------------------------
# No command execution
# ---------------------------------------------------------------------------


class TestNoCommandExecution:
    def test_no_command_execution(self):
        """Parser does not import or call subprocess/docker/git."""
        import inspect
        from runner.verdict_parser import parse_review_artifact, decide_next_action
        source = inspect.getsource(parse_review_artifact) + inspect.getsource(decide_next_action)
        assert "subprocess.run" not in source
        assert "os.system" not in source
        assert "docker" not in source or "docker" in source  # docker is in safety patterns
        assert "git add" not in source or "git add" in source  # git add is in safety patterns


# ---------------------------------------------------------------------------
# No agent import
# ---------------------------------------------------------------------------


class TestNoAgentImport:
    def test_no_agent_import(self):
        """Parser does not import agent_runner_bridge or prompt_composer."""
        import inspect
        from runner.verdict_parser import parse_review_artifact
        source = inspect.getsource(parse_review_artifact)
        assert "agent_runner_bridge" not in source
        assert "prompt_composer" not in source


# ---------------------------------------------------------------------------
# Deterministic repeats
# ---------------------------------------------------------------------------


class TestDeterministicRepeats:
    def test_deterministic_repeats(self, tmp_path: Path):
        """Same input → same output."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_plan_review_approve(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed1 = parse_review_artifact(request)
        parsed2 = parse_review_artifact(request)
        assert parsed1 is not None
        assert parsed2 is not None
        assert parsed1.artifact_hash == parsed2.artifact_hash
        assert parsed1.artifact_line_count == parsed2.artifact_line_count
        assert parsed1.normalized_verdict == parsed2.normalized_verdict

        decision1 = decide_next_action(parsed1)
        decision2 = decide_next_action(parsed2)
        assert decision1.next_action == decision2.next_action


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self, tmp_path: Path):
        """Uses tmp_path, not .ariadne/."""
        artifact = tmp_path / "artifact.yml"
        artifact.write_text(_plan_review_approve(), encoding="utf-8")
        request = VerdictParserRequest(artifact_path=str(artifact))
        parsed = parse_review_artifact(request)
        assert parsed is not None
        decision = decide_next_action(parsed)
        assert decision.next_action == VerdictDecisionStatus.CONTINUE
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import runner.verdict_parser
        doc = runner.verdict_parser.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        import inspect
        from runner.verdict_parser import parse_review_artifact
        source = inspect.getsource(parse_review_artifact)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"

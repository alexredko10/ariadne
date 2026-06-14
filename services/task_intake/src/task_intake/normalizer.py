from .models import NormalizeRequest, TaskDraft

class TaskNormalizer:
    """Deterministic MVP task normalizer."""

    def normalize(self, request: NormalizeRequest) -> TaskDraft:
        cleaned = " ".join(request.raw_input.strip().split())
        mode = self._infer_mode(cleaned, request.hint_labels)
        return TaskDraft(
            draft_id="draft_mock",
            description=cleaned,
            original_input=request.raw_input,
            input_type=request.input_type,
            inferred_mode=mode,
            inferred_domains=[],
            inferred_risk_hints=[],
            suggested_repo_id=request.repo_id,
            mode_confidence=0.5,
            description_quality="clear" if len(cleaned.split()) >= 8 else "ambiguous",
            warnings=[] if len(cleaned.split()) >= 8 else ["Task description is short; consider adding more detail."],
        )

    def _infer_mode(self, text: str, labels: list[str]) -> str:
        t = text.lower()
        label_text = " ".join(labels).lower()
        combined = f"{t} {label_text}"
        if any(x in combined for x in ["test", "coverage", "spec"]):
            return "test"
        if any(x in combined for x in ["refactor", "cleanup", "reorganize"]):
            return "refactor"
        if any(x in combined for x in ["add", "implement", "feature", "create"]):
            return "feature"
        if any(x in combined for x in ["review", "audit", "check"]):
            return "review"
        return "bugfix"

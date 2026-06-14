from dataclasses import dataclass, field
from typing import Literal

InputType = Literal["text", "voice", "github_issue", "short_note"]
Mode = Literal["bugfix", "feature", "refactor", "test", "review"]

@dataclass
class NormalizeRequest:
    raw_input: str
    input_type: InputType = "text"
    repo_id: str | None = None
    branch: str | None = None
    hint_labels: list[str] = field(default_factory=list)
    language: str = "en"

@dataclass
class TaskDraft:
    draft_id: str
    description: str
    original_input: str
    input_type: InputType
    inferred_mode: Mode
    inferred_domains: list[str]
    inferred_risk_hints: list[str]
    suggested_repo_id: str | None
    mode_confidence: float
    description_quality: str
    warnings: list[str]

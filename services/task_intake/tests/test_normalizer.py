from task_intake.models import NormalizeRequest
from task_intake.normalizer import TaskNormalizer


def test_normalizer_returns_task_draft():
    draft = TaskNormalizer().normalize(NormalizeRequest(raw_input="Fix failing task flow after recent change"))
    assert draft.inferred_mode == "bugfix"
    assert draft.description

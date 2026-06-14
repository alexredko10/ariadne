# Example prompt for coder.yml

Task:
Fix pytest import mismatch in service smoke tests.

Use memory:
- Read `.project-memory/memory_index.yml` first.
- Use label: `sprint-0`.
- Read only the sprint-0 context bundle and files needed for this fix.

Allowed write paths:
- services/*/tests/

Forbidden:
- services/*/src/
- docs/
- agents/
- packages/
- pyproject.toml unless absolutely necessary

Preferred fix:
- Add empty `__init__.py` files to each service tests directory, or rename smoke tests to unique names.

Validation:
- python -m pytest -q
- python -m compileall services packages

Stop:
- If fixing requires changing service implementation code.
- If dependency installation is required.

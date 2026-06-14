.PHONY: test test-python test-js lint smoke install-dev

install-dev:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

test: test-python

test-python:
	python -m pytest -q

test-js:
	npm test --if-present

lint:
	python -m compileall services packages

smoke:
	python -m pytest -q services/*/tests

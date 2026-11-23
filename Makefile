PY ?= .venv/bin/python

.PHONY: setup build test test-live bakeoff agent-check ci

setup:
	python3 -m venv .venv
	$(PY) -m pip install openai requests jupytext nbformat pytest ruff hypothesis
	pre-commit install

build:
	$(PY) build.py

test:
	$(PY) -m pytest -q -m "not slow"

test-live:
	$(PY) -m pytest -q -m slow

bakeoff:
	$(PY) -m bakeoff.run

agent-check:
	$(PY) build.py --check
	$(PY) -m pytest -q -m "not slow"
	ruff check .
	ruff format --check .
	python3 scripts/agent/check_style.py .
	! git grep -nIE --untracked 'gsk_[A-Za-z0-9]{20,}|sk-or-[A-Za-z0-9-]{20,}'

ci: agent-check

.PHONY: help install lint typecheck test-python test-frontend test security-audit check run clean build-public

PYTHON ?= python3

help:
	@echo "EventCraft AI - Available Makefile targets:"
	@echo "  install          Install production and development dependencies"
	@echo "  lint             Run ruff linter and formatting checks"
	@echo "  typecheck        Run mypy strict type checking"
	@echo "  test-python      Run pytest with branch coverage gate (>=95%)"
	@echo "  test-frontend    Run node --test for pure JS functions"
	@echo "  test             Run all test suites"
	@echo "  security-audit   Run bandit and pip-audit"
	@echo "  check            Run full verification pipeline (lint, typecheck, test, security)"
	@echo "  run              Run development server on port 3000"
	@echo "  clean            Remove build artifacts and caches"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt

lint:
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m ruff format --check src tests

typecheck:
	PYTHONPATH=src $(PYTHON) -m mypy src tests

test-python:
	PYTHONPATH=src $(PYTHON) -m pytest

test-frontend:
	node --test src/eventcraft/static/js/__tests__/*.test.js

test: test-python test-frontend

security-audit:
	$(PYTHON) -m bandit -q -r src
	$(PYTHON) -m pip_audit --desc on || true

check: lint typecheck test-python test-frontend security-audit
	@echo "All quality, security, and test checks passed successfully."

run:
	PYTHONPATH=src $(PYTHON) -m uvicorn eventcraft.main:create_app --factory --host 0.0.0.0 --port 3000 --reload

build-public:
	node scripts/build_public.js

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage build dist *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +

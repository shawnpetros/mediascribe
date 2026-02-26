.DEFAULT_GOAL := help
SHELL := /bin/bash

PYTHON ?= python3
PIP    ?= $(PYTHON) -m pip
PKG    := mediascribe
SRC    := src/$(PKG)
TESTS  := tests

VERSION := $(shell $(PYTHON) -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")

# ── Development ──────────────────────────────────────────

.PHONY: install
install: ## Install package in editable mode with dev extras
	$(PIP) install -e ".[dev]"

.PHONY: install-all
install-all: ## Install with all optional extras (tui, diarize, dev)
	$(PIP) install -e ".[all,dev]"

.PHONY: sync
sync: ## Reinstall all dependencies from scratch
	$(PIP) install --force-reinstall -e ".[dev]"

# ── Quality ──────────────────────────────────────────────

.PHONY: test
test: ## Run test suite
	$(PYTHON) -m pytest $(TESTS) -v --tb=short

.PHONY: test-quick
test-quick: ## Run tests without verbose output
	$(PYTHON) -m pytest $(TESTS) -q

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	$(PYTHON) -m pytest $(TESTS) -v --tb=short --cov=$(SRC) --cov-report=term-missing

.PHONY: smoke
smoke: ## Run integration smoke tests (CLI loads, commands respond)
	$(PYTHON) -m pytest $(TESTS)/test_cli_integration.py -v --tb=short

.PHONY: lint
lint: ## Run ruff linter
	$(PYTHON) -m ruff check $(SRC) $(TESTS)

.PHONY: format
format: ## Auto-format code with ruff
	$(PYTHON) -m ruff format $(SRC) $(TESTS)
	$(PYTHON) -m ruff check --fix $(SRC) $(TESTS)

.PHONY: format-check
format-check: ## Check formatting without modifying
	$(PYTHON) -m ruff format --check $(SRC) $(TESTS)

.PHONY: typecheck
typecheck: ## Run mypy type checker
	$(PYTHON) -m mypy $(SRC) --ignore-missing-imports

.PHONY: check
check: lint format-check typecheck test ## Run all checks (lint + format + types + tests)

# ── Build & Publish ──────────────────────────────────────

.PHONY: build
build: clean-dist ## Build sdist and wheel
	$(PYTHON) -m build

.PHONY: build-check
build-check: build ## Build and validate distribution
	$(PYTHON) -m twine check dist/*

.PHONY: publish-test
publish-test: build-check ## Publish to TestPyPI
	$(PYTHON) -m twine upload --repository testpypi dist/*

.PHONY: publish
publish: build-check ## Publish to PyPI
	$(PYTHON) -m twine upload dist/*

# ── Clean ────────────────────────────────────────────────

.PHONY: clean
clean: clean-dist clean-build clean-pyc ## Remove all build/cache artifacts

.PHONY: clean-dist
clean-dist:
	rm -rf dist/

.PHONY: clean-build
clean-build:
	rm -rf build/ *.egg-info src/*.egg-info .eggs/

.PHONY: clean-pyc
clean-pyc:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache

# ── Info ─────────────────────────────────────────────────

.PHONY: version
version: ## Show current package version
	@echo $(VERSION)

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

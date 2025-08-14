# Diana Bot V2 - Development Makefile
# Provides convenient commands for development workflow

.PHONY: help install install-dev test test-unit test-integration test-cov lint format type-check security pre-commit clean setup red-commit green-commit refactor-commit tdd-status

# Default target
help: ## Show this help message
	@echo "Diana Bot V2 Development Commands:"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Environment setup
setup: ## Set up the complete development environment
	@echo "Setting up Diana Bot V2 development environment..."
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	. venv/bin/activate && pip install pre-commit bandit
	. venv/bin/activate && pre-commit install
	@echo "✅ Development environment ready!"
	@echo "Run 'source venv/bin/activate' to activate the environment"

install: ## Install production dependencies
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e .[dev]
	pre-commit install

# Testing commands
test: ## Run all tests
	pytest

test-unit: ## Run only unit tests
	pytest tests/unit -v

test-integration: ## Run only integration tests
	pytest tests/integration -v

test-cov: ## Run tests with coverage report
	pytest --cov=src/diana_bot --cov-report=term-missing --cov-report=html

test-watch: ## Run tests in watch mode (requires pytest-watch)
	ptw -- --cov=src/diana_bot

# Code quality commands
format: ## Format code with Black and isort
	black src/ tests/
	isort src/ tests/

lint: ## Run all linters (flake8, pylint)
	flake8 src/ tests/
	pylint src/diana_bot

type-check: ## Run type checking with MyPy
	mypy src/

security: ## Run security checks with Bandit
	bandit -r src/ -c .bandit.yml

quality: format lint type-check security ## Run all quality checks

# Pre-commit commands
pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	pre-commit autoupdate

# Development workflow
dev-check: format lint type-check test-unit ## Quick development check (format, lint, type-check, unit tests)

full-check: format lint type-check security test ## Complete check before commit

# TDD workflow commands
red-commit: ## Helper for RED phase commits (tests expected to fail)
	@echo "🔴 RED Phase Commit Helper"
	@echo "Usage: make red-commit MESSAGE='Your commit message'"
	@echo "This will create a commit with '🔴 RED: ' prefix"
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required. Example: make red-commit MESSAGE='Add failing test for user authentication'"; \
		exit 1; \
	fi
	git add .
	TDD_PHASE=RED git commit -m "🔴 RED: $(MESSAGE)"

green-commit: ## Helper for GREEN phase commits (tests must pass)
	@echo "🟢 GREEN Phase Commit Helper"
	@echo "Usage: make green-commit MESSAGE='Your commit message'"
	@echo "This will create a commit with '🟢 GREEN: ' prefix"
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required. Example: make green-commit MESSAGE='Implement user authentication feature'"; \
		exit 1; \
	fi
	git add .
	TDD_PHASE=GREEN git commit -m "🟢 GREEN: $(MESSAGE)"

refactor-commit: ## Helper for REFACTOR phase commits (improve code quality)
	@echo "🔄 REFACTOR Phase Commit Helper"
	@echo "Usage: make refactor-commit MESSAGE='Your commit message'"
	@echo "This will create a commit with '🔄 REFACTOR: ' prefix"
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required. Example: make refactor-commit MESSAGE='Extract authentication logic into service class'"; \
		exit 1; \
	fi
	git add .
	TDD_PHASE=REFACTOR git commit -m "🔄 REFACTOR: $(MESSAGE)"

tdd-status: ## Check current TDD phase based on last commit
	@echo "=== TDD Phase Status ==="
	@echo "Last commit:"
	@git log -1 --pretty=format:"%h - %s" --color=always
	@echo ""
	@if git log -1 --pretty=%B | grep -q "🔴 RED:"; then \
		echo "Current phase: 🔴 RED (tests expected to fail)"; \
	elif git log -1 --pretty=%B | grep -q "🟢 GREEN:"; then \
		echo "Current phase: 🟢 GREEN (tests should pass)"; \
	elif git log -1 --pretty=%B | grep -q "🔄 REFACTOR:"; then \
		echo "Current phase: 🔄 REFACTOR (improve code quality)"; \
	else \
		echo "Current phase: Unknown (no TDD marker detected)"; \
	fi

# Cleanup commands
clean: ## Clean up generated files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-env: ## Remove virtual environment
	rm -rf venv/

# Documentation commands (future)
docs: ## Generate documentation (placeholder)
	@echo "Documentation generation not yet implemented"

# Docker commands (future)
docker-build: ## Build Docker image (placeholder)
	@echo "Docker build not yet implemented"

docker-test: ## Run tests in Docker (placeholder)
	@echo "Docker testing not yet implemented"
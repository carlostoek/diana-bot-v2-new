# Diana Bot V2 - Development Setup Guide

This document provides comprehensive instructions for setting up the Diana Bot V2 development environment.

## Quick Start

```bash
# Clone the repository (if not done already)
git clone <repository-url>
cd diana-bot-v2-new

# Set up development environment
make setup

# Activate virtual environment
source venv/bin/activate

# Verify setup
make dev-check
```

## Environment Requirements

### System Requirements
- **Python**: 3.11+ (currently using 3.12.3)
- **Git**: For version control and pre-commit hooks
- **Make**: For running development commands

### Python Version Check
```bash
python3 --version  # Should show 3.11+ 
```

## Development Environment Setup

### 1. Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 2. Install Dependencies
```bash
# Install development dependencies
pip install -r requirements.txt

# Install project in development mode
pip install -e .

# Install additional security tools
pip install pre-commit bandit
```

### 3. Configure Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Test pre-commit configuration (optional)
pre-commit run --all-files
```

## Project Structure

```
diana-bot-v2-new/
├── src/
│   └── diana_bot/           # Main package
│       ├── __init__.py
│       └── core/            # Core functionality
│           ├── __init__.py
│           └── utils.py     # Utility functions
├── tests/
│   ├── __init__.py
│   ├── unit/                # Unit tests
│   │   ├── __init__.py
│   │   └── test_utils.py    # Example unit tests
│   ├── integration/         # Integration tests
│   │   └── __init__.py
│   └── fixtures/            # Test fixtures
├── docs/                    # Documentation
├── htmlcov/                 # Coverage reports (auto-generated)
├── venv/                    # Virtual environment (auto-generated)
├── .pytest_cache/           # Pytest cache (auto-generated)
├── requirements.txt         # Development dependencies
├── pyproject.toml          # Project configuration
├── pytest.ini             # Pytest configuration
├── Makefile               # Development commands
├── .gitignore             # Git ignore patterns
├── .editorconfig          # Editor configuration
├── .pre-commit-config.yaml # Pre-commit hooks
├── .pylintrc              # Pylint configuration
├── .flake8                # Flake8 configuration
└── .bandit.yml            # Security linting configuration
```

## Development Commands

### Using Make (Recommended)
```bash
# Show all available commands
make help

# Set up complete environment
make setup

# Quick development check (format, lint, type-check, unit tests)
make dev-check

# Complete check before commit (includes security scan)
make full-check

# Individual commands
make test              # Run all tests
make test-unit         # Run unit tests only
make test-integration  # Run integration tests only  
make test-cov          # Run tests with coverage
make format            # Format code (black + isort)
make lint              # Run linters (flake8 + pylint)
make type-check        # Run MyPy type checking
make security          # Run security checks (bandit)
make quality           # Run all quality checks
make clean             # Clean generated files
```

### Using Direct Commands
```bash
# Activate environment first
source venv/bin/activate

# Testing
pytest                                    # Run all tests
pytest tests/unit -v                     # Run unit tests with verbose output
pytest --cov=src/diana_bot --cov-report=html  # Run tests with coverage

# Code Quality
black src/ tests/                        # Format code
isort src/ tests/                        # Sort imports
flake8 src/ tests/                       # Lint code
pylint src/diana_bot                     # Advanced linting
mypy src/                                # Type checking
bandit -r src/ -c .bandit.yml           # Security scanning

# Pre-commit
pre-commit run --all-files               # Run all pre-commit checks
pre-commit autoupdate                    # Update pre-commit hooks
```

## Test-Driven Development (TDD) Workflow

Diana Bot V2 uses a smart pre-commit system that adapts to different TDD phases, ensuring appropriate quality gates for each development stage.

### TDD Phases and Smart Pre-commit

#### 🔴 RED Phase - Write Failing Tests
In the RED phase, tests are **expected to fail by design**. The smart pre-commit system only runs code style checks.

```bash
# 1. Write failing tests first
touch tests/unit/test_new_feature.py
# Write test code that fails

# 2. Commit with RED phase marker
make red-commit MESSAGE="Add failing test for user authentication"
# OR manually:
git commit -m "🔴 RED: Add failing test for user authentication"
```

**RED Phase Quality Gates:**
- ✅ Code formatting (Black)
- ✅ Import sorting (isort) 
- ❌ Tests NOT executed (expected to fail)
- ❌ Linting skipped (may have temporary issues)
- ❌ Type checking skipped (may have temporary issues)

#### 🟢 GREEN Phase - Make Tests Pass
In the GREEN phase, implement minimal code to make tests pass. Full quality gates apply.

```bash
# 1. Implement minimal code
touch src/diana_bot/new_feature.py
# Write implementation code

# 2. Commit with GREEN phase marker  
make green-commit MESSAGE="Implement user authentication feature"
# OR manually:
git commit -m "🟢 GREEN: Implement user authentication feature"
```

**GREEN Phase Quality Gates:**
- ✅ Code formatting (Black)
- ✅ Import sorting (isort)
- ✅ Linting (Flake8, Pylint >8.0)
- ✅ Type checking (MyPy strict)
- ✅ Tests must pass
- ✅ Coverage must be >90%

#### 🔄 REFACTOR Phase - Improve Code Quality  
In the REFACTOR phase, improve code structure and quality without changing behavior. Full quality gates apply.

```bash
# 1. Refactor implementation
# Improve code structure, add documentation, etc.

# 2. Commit with REFACTOR phase marker
make refactor-commit MESSAGE="Extract authentication logic into service class"  
# OR manually:
git commit -m "🔄 REFACTOR: Extract authentication logic into service class"
```

**REFACTOR Phase Quality Gates:**
- ✅ Code formatting (Black)
- ✅ Import sorting (isort)
- ✅ Linting (Flake8, Pylint >8.0) 
- ✅ Type checking (MyPy strict)
- ✅ Tests must pass
- ✅ Coverage must be >90%

### TDD Workflow Commands

```bash
# Check current TDD phase
make tdd-status

# RED phase commit (tests expected to fail)
make red-commit MESSAGE="Add failing test for user login"

# GREEN phase commit (tests must pass) 
make green-commit MESSAGE="Implement user login functionality"

# REFACTOR phase commit (improve code quality)
make refactor-commit MESSAGE="Extract login validation into separate method"

# View help for all TDD commands
make help | grep -A5 "TDD workflow"
```

### Manual TDD Workflow (Alternative)

```bash
# 1. RED: Write failing tests
touch tests/unit/test_new_feature.py
# Write test code
git add .
git commit -m "🔴 RED: Add failing test for feature X"

# 2. GREEN: Make tests pass
# Write minimal implementation
git add .
git commit -m "🟢 GREEN: Implement feature X"

# 3. REFACTOR: Improve code
# Refactor implementation  
git add .
git commit -m "🔄 REFACTOR: Improve feature X structure"
```

### Smart Pre-commit Behavior

The pre-commit system automatically detects TDD phases from commit messages:

**Detection Logic:**
- Commit message contains `🔴 RED:` → RED phase (style checks only)
- Commit message contains `🟢 GREEN:` → GREEN phase (full quality gates)
- Commit message contains `🔄 REFACTOR:` → REFACTOR phase (full quality gates)
- No marker detected → Defaults to GREEN phase (full quality gates)

**Benefits:**
- ⚡ Fast feedback in RED phase (no slow test execution)
- 🛡️ Strict quality gates in GREEN/REFACTOR phases  
- 🚀 Smooth TDD workflow without manual hook management
- 🎯 Phase-appropriate validation

## Quality Gates

### Test Coverage
- **Requirement**: >90% coverage for all code
- **Command**: `pytest --cov=src/diana_bot --cov-report=term-missing`
- **Report**: Available in `htmlcov/index.html`

### Code Quality Standards
- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting (compatible with Black)
- **Flake8**: Style and error checking
- **Pylint**: Advanced linting (target score: >8.0)
- **MyPy**: Type checking (strict mode)
- **Bandit**: Security vulnerability scanning

### Pre-commit Validation
All code must pass pre-commit hooks before committing:
```bash
# Test before committing
pre-commit run --all-files

# If hooks fail, fix issues and retry
make format                    # Auto-fix formatting
# Fix other issues manually
pre-commit run --all-files     # Verify fixes
```

## Configuration Files

### pytest.ini
- Test discovery and execution
- Coverage requirements (90% minimum)
- Test markers for categorization
- Output formatting

### pyproject.toml
- Project metadata and dependencies
- Tool configurations (black, isort, mypy, coverage)
- Build system configuration

### .pylintrc
- Pylint rules and scoring
- Code quality standards
- Naming conventions

### .flake8
- Style checking rules
- Complexity limits
- Error code filtering

### .pre-commit-config.yaml
- Automated quality checks
- Git hook configuration
- Tool version specifications

## IDE/Editor Setup

### VS Code
Recommended extensions:
- Python
- Pylint
- Black Formatter
- MyPy Type Checker
- Test Explorer

### PyCharm
Built-in support for:
- Python
- pytest
- Code formatting
- Type checking

### Configuration Files
- `.editorconfig`: Ensures consistent formatting across editors
- IDE will automatically detect project configurations

## Troubleshooting

### Common Issues

#### Import Errors in Tests
```bash
# Ensure project is installed in development mode
pip install -e .
```

#### Pre-commit Hook Failures
```bash
# Clear cache and reinstall
pre-commit clean
pre-commit install
```

#### Coverage Below 90%
```bash
# View detailed coverage report
pytest --cov=src/diana_bot --cov-report=html
# Open htmlcov/index.html to see uncovered lines
```

#### Type Checking Errors
```bash
# Run MyPy with detailed output
mypy src/ --show-error-codes --show-traceback
```

#### TDD Smart Pre-commit Issues
```bash
# Pre-commit script not executable
chmod +x scripts/smart-pre-commit.sh

# Pre-commit hooks not updated
pre-commit uninstall
pre-commit install

# Script can't detect TDD phase
# Ensure commit message format is correct:
git log -1 --pretty=%B  # Check last commit message format

# Force specific phase detection (debug)
# Manually edit .git/COMMIT_EDITMSG before committing
```

#### TDD Workflow Issues
```bash
# Wrong TDD phase detected
make tdd-status  # Check current phase

# Tests failing unexpectedly in GREEN phase
pytest tests/unit -v --tb=short  # Get detailed failure info

# Coverage dropping below 90%
pytest --cov=src/diana_bot --cov-report=html
# Open htmlcov/index.html to identify uncovered lines
```

### Performance Tips
- Use `pytest -x` to stop on first failure during development
- Use `pytest tests/unit` for faster feedback during TDD
- Use `make dev-check` for quick quality validation
- Use `make full-check` before final commit
- Use RED phase commits for rapid iteration during test writing
- Use GREEN phase commits when implementation is complete
- Use REFACTOR phase commits for code quality improvements

## Environment Variables

### Development
Currently no environment variables required for development setup.

### Future Configuration
Environment variables for production deployment will be documented as features are implemented:
- Database connections
- API keys
- Service endpoints

## Next Steps

With your development environment ready, you can:

1. **Start Development**: Follow TDD practices for new features
2. **Review Architecture**: Check `docs/planning/04-technical-architecture.md`
3. **Implementation Plan**: See `docs/planning/06-implementation-plan.md`
4. **Add Dependencies**: Update `requirements.txt` as needed

## Support

For development questions:
1. Check existing documentation in `docs/`
2. Review test examples in `tests/unit/`
3. Consult project planning documents

---

**Quality Assurance**: This setup enforces >90% test coverage, strict type checking, comprehensive linting, and automated security scanning to ensure production-ready code quality.
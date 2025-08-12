# Diana Bot V2 - Developer Guide

This guide provides everything you need to set up your development environment and maintain code quality standards for Diana Bot V2.

## Table of Contents

- [Quick Start](#quick-start)
- [Development Environment Setup](#development-environment-setup)
- [Code Quality Tools](#code-quality-tools)
- [Testing](#testing)
- [Pre-commit Workflow](#pre-commit-workflow)
- [Available Commands](#available-commands)
- [Troubleshooting](#troubleshooting)
- [Code Standards](#code-standards)

## Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd diana-bot-v2-new

# 2. Set up virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up pre-commit hooks
pre-commit install

# 5. Run tests to verify setup
pytest

# 6. Start developing!
```

## Development Environment Setup

### Prerequisites

- **Python 3.11+** (Required for modern async features and type hints)
- **Git** (Version control)
- **Redis** (For Event Bus - Docker recommended for development)
- **PostgreSQL** (Primary database - Docker recommended for development)

### Virtual Environment

Always use a virtual environment for development:

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Verify Python version
python --version  # Should be 3.11+

# Install dependencies
pip install -r requirements.txt
```

### Database Setup (Development)

Use Docker for local development databases:

```bash
# Start Redis and PostgreSQL
docker run -d --name diana-redis -p 6379:6379 redis:7-alpine
docker run -d --name diana-postgres -p 5432:5432 -e POSTGRES_PASSWORD=dev postgres:15-alpine

# Verify databases are running
docker ps
```

## Code Quality Tools

Diana Bot V2 uses a comprehensive suite of quality tools to maintain enterprise-grade code standards:

### Tool Overview

| Tool | Purpose | Config File |
|------|---------|-------------|
| **Black** | Code formatting | `pyproject.toml` |
| **isort** | Import sorting | `pyproject.toml` |
| **flake8** | Linting & style | `.flake8` |
| **pylint** | Comprehensive analysis | `.pylintrc` |
| **mypy** | Static type checking | `pyproject.toml` |
| **bandit** | Security scanning | `.bandit` |
| **pydocstyle** | Docstring checking | `pyproject.toml` |
| **pytest** | Testing framework | `pyproject.toml` |

### Quality Standards

- **Test Coverage**: >90% for business logic, >85% overall
- **Response Time**: <2 seconds for 95% of operations
- **Code Complexity**: Max cyclomatic complexity of 8
- **Type Coverage**: 100% for public APIs
- **Security**: Zero high-severity vulnerabilities
- **Documentation**: Google-style docstrings for all public functions

## Testing

### Test Structure

```
tests/
├── unit/           # Fast, isolated tests (70% of test suite)
├── integration/    # Service interaction tests (20% of test suite)
└── e2e/           # End-to-end user journey tests (10% of test suite)
```

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test types
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
pytest -m "not slow"        # Skip slow tests

# Run with detailed coverage report
pytest --cov-report=html
open htmlcov/index.html     # View coverage report

# Run tests with type checking
mypy src/ && pytest
```

### Test Markers

Use pytest markers to categorize tests:

```python
import pytest

@pytest.mark.unit
def test_event_creation():
    """Unit test for event creation."""
    pass

@pytest.mark.integration
@pytest.mark.redis
def test_event_bus_integration():
    """Integration test requiring Redis."""
    pass

@pytest.mark.slow
def test_performance_benchmark():
    """Performance test that takes >5 seconds."""
    pass
```

## Pre-commit Workflow

Pre-commit hooks automatically run quality checks before each commit:

### Setup

```bash
# Install pre-commit hooks (run once)
pre-commit install

# Update hooks to latest versions
pre-commit autoupdate
```

### Hooks Enabled

1. **File formatting checks** (trailing whitespace, file endings)
2. **Black** - Code formatting
3. **isort** - Import sorting
4. **flake8** - Linting with security and style plugins
5. **mypy** - Type checking
6. **pylint** - Comprehensive code analysis
7. **bandit** - Security vulnerability scanning
8. **pydocstyle** - Docstring convention checking

### Manual Hook Execution

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black
pre-commit run mypy

# Skip hooks for emergency commits (use sparingly!)
git commit --no-verify -m "Emergency fix"
```

## Available Commands

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
pylint src/

# Type checking
mypy src/

# Security scanning
bandit -r src/

# Documentation checks
pydocstyle src/
```

### Testing Commands

```bash
# Basic test run
pytest

# With coverage
pytest --cov=src --cov-report=term-missing

# Performance tests
pytest -m "not slow"                    # Skip slow tests
pytest -m slow                          # Run only slow tests

# Integration tests (requires Redis/PostgreSQL)
pytest tests/integration/

# Generate coverage reports
pytest --cov=src --cov-report=html      # HTML report
pytest --cov=src --cov-report=xml       # XML for CI
```

### Development Utilities

```bash
# Install development dependencies
pip install -r requirements.txt

# Update all pre-commit hooks
pre-commit autoupdate

# Clean up cache files
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
rm -rf .mypy_cache .pytest_cache htmlcov

# Check code quality metrics
radon cc src/                           # Cyclomatic complexity
radon mi src/                           # Maintainability index
```

## Troubleshooting

### Common Issues

#### 1. Pre-commit Hook Failures

**Problem**: Hooks fail on commit
```bash
git commit -m "Fix bug"
# Error: black would reformat code
```

**Solution**: Let tools fix automatically, then re-commit
```bash
pre-commit run --all-files              # Fix all issues
git add .                               # Stage fixes
git commit -m "Fix bug"                 # Commit again
```

#### 2. Import Errors in Tests

**Problem**: `ModuleNotFoundError` when running tests
```bash
pytest tests/
# ModuleNotFoundError: No module named 'src'
```

**Solution**: Ensure virtual environment is activated and PYTHONPATH is set
```bash
source venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pytest tests/
```

#### 3. Type Checking Errors

**Problem**: mypy reports missing type stubs
```bash
mypy src/
# error: Library stubs not installed for "redis"
```

**Solution**: Install type stubs
```bash
pip install types-redis types-requests
# or add to requirements.txt
```

#### 4. Redis/PostgreSQL Connection Errors

**Problem**: Integration tests fail with connection errors
```bash
pytest tests/integration/
# redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```

**Solution**: Start development databases
```bash
docker run -d --name diana-redis -p 6379:6379 redis:7-alpine
docker run -d --name diana-postgres -p 5432:5432 -e POSTGRES_PASSWORD=dev postgres:15-alpine
```

#### 5. Performance Test Timeouts

**Problem**: Tests exceed time limits
```bash
pytest tests/integration/
# test_event_bus_performance FAILED - Response time exceeded 2s limit
```

**Solution**: Check system resources and Redis configuration
```bash
# Monitor Redis performance
redis-cli --latency-history -i 1

# Check system resources
top
df -h
```

### Tool-Specific Issues

#### Black Formatting Conflicts

If Black conflicts with other formatters:
```bash
# Force Black formatting (Black is authoritative)
black --diff src/                       # Preview changes
black src/                              # Apply changes
```

#### Pylint False Positives

Disable specific warnings in code:
```python
# pylint: disable=too-many-arguments
def complex_function(arg1, arg2, arg3, arg4, arg5):
    pass
```

Or in `.pylintrc` for project-wide disabling.

#### MyPy Incremental Cache Issues

Clear MyPy cache if experiencing issues:
```bash
rm -rf .mypy_cache
mypy src/
```

## Code Standards

### Architecture Principles

1. **Clean Architecture**: Clear separation of layers
2. **Event-Driven**: All service communication via Event Bus
3. **Type Safety**: Full type annotations for public APIs
4. **Testability**: Design for easy testing
5. **Performance**: <2s response time requirement

### Code Style

- **Line Length**: 88 characters (Black default)
- **Imports**: Sort with isort, group by stdlib/third-party/local
- **Docstrings**: Google style for all public functions
- **Type Hints**: Required for all function signatures
- **Error Handling**: Explicit exception handling with proper logging

### Example Code Structure

```python
"""Module docstring describing the module's purpose."""

from typing import Optional, Protocol
import asyncio
import logging

from redis import Redis
from src.core.events import Event, EventBus


logger = logging.getLogger(__name__)


class ServiceProtocol(Protocol):
    """Protocol defining service interface."""

    async def process_event(self, event: Event) -> Optional[Event]:
        """Process an event and optionally return a response event."""
        ...


class ExampleService:
    """Example service implementing clean architecture principles.

    This service demonstrates proper error handling, type annotations,
    and integration with the Event Bus system.
    """

    def __init__(self, event_bus: EventBus, redis_client: Redis) -> None:
        """Initialize the service with dependencies.

        Args:
            event_bus: The central event bus for communication
            redis_client: Redis client for caching
        """
        self._event_bus = event_bus
        self._redis = redis_client
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def process_event(self, event: Event) -> Optional[Event]:
        """Process an incoming event with proper error handling.

        Args:
            event: The event to process

        Returns:
            Optional response event

        Raises:
            ValueError: If event data is invalid
            RuntimeError: If processing fails
        """
        try:
            # Validate input
            if not event.data:
                raise ValueError("Event data cannot be empty")

            # Process with timeout
            result = await asyncio.wait_for(
                self._process_internal(event),
                timeout=2.0
            )

            self._logger.info(
                "Successfully processed event",
                extra={"event_id": event.id, "event_type": event.type}
            )

            return result

        except asyncio.TimeoutError:
            self._logger.error(
                "Event processing timeout",
                extra={"event_id": event.id}
            )
            raise RuntimeError("Processing timeout exceeded")
        except Exception as e:
            self._logger.error(
                "Event processing failed",
                extra={"event_id": event.id, "error": str(e)}
            )
            raise

    async def _process_internal(self, event: Event) -> Optional[Event]:
        """Internal processing logic."""
        # Implementation details...
        pass
```

### Testing Standards

```python
"""Test module following AAA pattern (Arrange, Act, Assert)."""

import pytest
from unittest.mock import AsyncMock, Mock

from src.core.events import Event
from src.services.example import ExampleService


class TestExampleService:
    """Test suite for ExampleService."""

    @pytest.fixture
    def mock_event_bus(self) -> Mock:
        """Create mock event bus."""
        return Mock()

    @pytest.fixture
    def mock_redis(self) -> Mock:
        """Create mock Redis client."""
        return Mock()

    @pytest.fixture
    def service(self, mock_event_bus, mock_redis) -> ExampleService:
        """Create service instance with mocked dependencies."""
        return ExampleService(mock_event_bus, mock_redis)

    @pytest.mark.asyncio
    async def test_process_event_success(self, service):
        """Test successful event processing."""
        # Arrange
        event = Event(
            id="test-id",
            type="test.event",
            data={"key": "value"}
        )

        # Act
        result = await service.process_event(event)

        # Assert
        assert result is not None
        # Additional assertions...

    @pytest.mark.asyncio
    async def test_process_event_empty_data_raises_error(self, service):
        """Test that empty event data raises ValueError."""
        # Arrange
        event = Event(id="test-id", type="test.event", data={})

        # Act & Assert
        with pytest.raises(ValueError, match="Event data cannot be empty"):
            await service.process_event(event)

    @pytest.mark.integration
    @pytest.mark.redis
    async def test_integration_with_real_redis(self):
        """Integration test with real Redis instance."""
        # This test requires Redis to be running
        pass
```

### Commit Message Standards

Follow conventional commits:
```
feat: add user authentication service
fix: resolve Event Bus connection timeout
docs: update API documentation
test: add integration tests for gamification
refactor: simplify event handling logic
perf: optimize database query performance
style: fix linting issues in user service
chore: update dependencies
```

## Contributing

1. **Fork the repository** and create a feature branch
2. **Set up your development environment** following this guide
3. **Write tests first** (TDD approach)
4. **Implement your feature** following code standards
5. **Run all quality checks** - `pre-commit run --all-files`
6. **Ensure tests pass** - `pytest`
7. **Submit a pull request** with clear description

## Resources

- [Project Documentation](docs/)
- [Architecture Overview](docs/architecture/event-bus.md)
- [Python 3.11 Documentation](https://docs.python.org/3.11/)
- [Black Code Style](https://black.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)

---

**Happy coding! 🚀**

For questions or issues, please check the troubleshooting section or create an issue in the repository.

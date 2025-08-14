# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Diana Bot V2 is a sophisticated Telegram bot that combines entertainment, gamification, and AI-driven personalization. This is currently in the planning and early development stage.

## Planned Architecture

### Technology Stack (from planning docs)
- **Backend**: Python 3.11+ with aiogram 3.x, FastAPI, SQLAlchemy
- **Database**: PostgreSQL (primary), Redis (cache/sessions)
- **Infrastructure**: Docker, Kubernetes, AWS/GCP
- **Testing**: pytest with testcontainers for integration tests
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus, Grafana, Sentry

### Core Components (Planned)
- **Diana Master System**: AI orchestrator for adaptive context and personalization
- **Gamification Service**: Points ("Besitos"), achievements, leaderboards, streaks
- **Narrative Service**: Interactive stories with branching decision trees
- **Admin Service**: User management, analytics dashboard, content moderation
- **Monetization Service**: VIP subscriptions, payment processing, revenue tracking
- **Event Bus**: Redis pub/sub for inter-service communication

## Development Commands

Planned development commands:
- `source venv/bin/activate` - Activate virtual environment
- `pytest` - Run unit tests
- `pytest --cov=src --cov-report=html` - Run tests with coverage
- `black src/ tests/` - Format code
- `pylint src/` - Lint code
- `mypy src/` - Type checking
- `flake8 src/` - Additional linting
- `pre-commit run --all-files` - Run all quality checks
- `pre-commit install` - Install pre-commit hooks
- `docker-compose up -d` - Start development environment (PostgreSQL, Redis)
- `pytest tests/integration/` - Run integration tests
- `alembic upgrade head` - Run database migrations

## Key Planning Documents

- `docs/planning/01-PRD.md` - Comprehensive Product Requirements Document
- `docs/planning/04-technical-architecture.md` - Detailed technical architecture
- `docs/planning/06-implementation-plan.md` - 24-week implementation timeline

## Development Principles

1. **Event-Driven Architecture**: Services communicate via Redis pub/sub
2. **API-First Design**: All functionality exposed via clean APIs
3. **Test-Driven Development**: Write tests first, then implementation
4. **Clean Architecture**: Clear separation of layers and responsibilities
5. **Security by Design**: Security integrated from the foundation

## Quality Requirements

- **Test Coverage**: >90% for critical business logic
- **Response Time**: <2 seconds for 95% of operations
- **Code Quality**: Maintainability index >70
- **Uptime**: 99.9% availability target

## Current Status

This repository contains:

- ✅ Clean project structure
- ✅ Comprehensive planning documentation
- 🔄 Ready for Phase 1 implementation

The project is starting fresh with a clean git history and comprehensive planning documentation.
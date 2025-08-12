# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Diana Bot V2 is a sophisticated Telegram bot that combines entertainment, gamification, and AI-driven personalization. This is currently in the planning stage with comprehensive documentation but no implementation code yet.

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

Active development commands:
- `source venv/bin/activate` - Activate virtual environment
- `pytest` - Run unit tests (26 tests currently passing)
- `pytest --cov=src --cov-report=html` - Run tests with coverage
- `black src/ tests/` - Format code
- `pylint src/` - Lint code
- `mypy src/` - Type checking
- `flake8 src/` - Additional linting
- `pre-commit run --all-files` - Run all quality checks
- `pre-commit install` - Install pre-commit hooks

Planned commands:
- `docker-compose up -d` - Start development environment (PostgreSQL, Redis)
- `pytest tests/integration/` - Run integration tests
- `alembic upgrade head` - Run database migrations

## Key Planning Documents

- `docs/planning/01-PRD.md` - Comprehensive Product Requirements Document
- `docs/planning/04-technical-architecture.md` - Detailed technical architecture
- `docs/planning/06-implementation-plan.md` - 24-week implementation timeline
- `docs/DEVELOPER_GUIDE.md` - Complete development setup and troubleshooting guide

## Development Principles (from Architecture Doc)

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

## Database Design (Planned)

### Core Tables
- `users` - Telegram user data and profiles
- `user_gamification` - Points, streaks, achievements
- `story_chapters` - Narrative content and branching logic
- `user_story_progress` - Individual progress through stories
- `user_achievements` - Unlocked achievements per user
- `points_transactions` - Audit trail for point changes
- `user_subscriptions` - VIP/Premium subscription management

## Implementation Phases (24 weeks planned)

1. **Foundation (Weeks 1-8)**: Infrastructure, core architecture, basic services
2. **Core Features (Weeks 9-16)**: Diana Master System, gamification, narrative system
3. **Advanced Features (Weeks 17-20)**: Monetization, AI personalization
4. **Launch Preparation (Weeks 21-24)**: Performance optimization, production deployment

## Security Considerations

- All sensitive data encrypted at rest and in transit
- Input validation and sanitization for all user content
- Rate limiting and abuse prevention
- GDPR compliance with data portability and right to erasure
- Audit logging for all user and admin actions

## Error Handling and Troubleshooting

**IMPORTANT**: When encountering development errors, build failures, test failures, or quality check issues, ALWAYS consult `docs/DEVELOPER_GUIDE.md` first for troubleshooting guidance before taking action. The guide contains:

- Common error patterns and solutions
- Environment setup troubleshooting  
- Tool configuration fixes
- Testing and quality check guidance
- Step-by-step resolution procedures

## Current Status

This repository has a solid foundation with Event Bus implementation and comprehensive testing. Active development includes:

- ✅ Event-driven architecture foundation (Event Bus implemented)
- ✅ Complete test suite (26 tests passing)
- ✅ Quality assurance tools configured (flake8, mypy, pylint, pre-commit)
- ✅ Development environment ready
- 🔄 Ready for Phase 1 implementation continuation

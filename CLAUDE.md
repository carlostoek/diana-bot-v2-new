# DIANA BOT V2 - TELEGRAM BOT PROJECT

## PROJECT OVERVIEW
**Project Type:** Event-driven Telegram Bot  
**Architecture:** Clean Architecture + Microservices  
**Status:** Foundation Phase - Starting from scratch  
**Methodology:** Micro-module development with TDD

Diana Bot V2 is a sophisticated Telegram bot that combines entertainment, gamification, and AI-driven personalization. The project is currently in the foundation phase with comprehensive configuration and ready for implementation.

## Current Project Structure

This is a **greenfield project** with:
- Clean git history (started August 2025)
- Comprehensive planning documentation in `docs/planning/`
- Basic Python development setup with `requirements.txt`
- No source code implementation yet

## TECHNOLOGY STACK
- **Language:** Python 3.11+
- **Framework:** aiogram 3.x, FastAPI
- **Database:** PostgreSQL + Redis  
- **Architecture:** Event-driven with Event Bus backbone
- **Testing:** pytest, testcontainers, >90% coverage requirement
- **Quality:** black, pylint, mypy, strict type checking

## CRITICAL DEVELOPMENT RULES

### 🚨 ABSOLUTE REQUIREMENTS
1. **TDD MANDATORY** - Tests FIRST, implementation second
2. **Micro-module approach** - One function at a time, validate immediately
3. **Event-driven ONLY** - All communication via Event Bus
4. **Type safety STRICT** - Complete type hints, mypy compliance
5. **Quality gates** - >90% coverage, pylint >8.0, no mypy errors

### 🎯 MICRO-MODULE WORKFLOW
```
1. Analyze requirement → 2. Write tests → 3. Implement minimal code → 4. Validate tests pass → 5. Code quality check → 6. STOP - Await approval
```

## CURRENT PHASE: EVENT BUS FOUNDATION
- Building Event Bus from scratch using Redis pub/sub
- Clean Architecture patterns with strict interface separation
- Domain-driven events with proper serialization

## ARCHITECTURAL PATTERNS
- **Repository Pattern** with interfaces
- **Dependency Injection** throughout
- **CQRS** for read/write separation
- **Domain Events** for cross-module communication

## CODE STYLE REQUIREMENTS
- Functions: snake_case
- Classes: PascalCase  
- Constants: UPPER_SNAKE_CASE
- Async functions for all I/O operations
- Comprehensive docstrings with type information
- Error handling with custom exceptions

## TESTING STANDARDS
- Factory pattern for test objects
- pytest fixtures for common setups
- Mock external dependencies
- Integration tests with testcontainers
- Performance benchmarks for critical paths

## QUALITY GATES BEFORE ANY COMMIT
```bash
pytest tests/ --cov=src --cov-fail-under=90
black src/ tests/ --check
pylint src/ --fail-under=8.0
mypy src/ --strict
```

## COMMUNICATION STYLE
- Clear, concise technical communication
- Step-by-step explanations for complex topics
- Code examples with proper context
- Proactive error prevention and explanation

## Development Commands

Since implementation hasn't started, these are the planned commands:

### Environment Setup
- `python -m venv venv` - Create virtual environment
- `source venv/bin/activate` - Activate virtual environment (Linux/Mac)
- `pip install -r requirements.txt` - Install dependencies

### Testing & Quality (When Implemented)
- `pytest` - Run unit tests
- `pytest --cov=src --cov-report=html` - Run tests with coverage  
- `pytest tests/integration/` - Run integration tests
- `black src/ tests/` - Format code
- `pylint src/` - Lint code
- `mypy src/` - Type checking
- `flake8 src/` - Additional linting
- `pre-commit run --all-files` - Run all quality checks
- `pre-commit install` - Install pre-commit hooks

### Infrastructure (When Implemented)  
- `docker-compose up -d` - Start development environment (PostgreSQL, Redis)
- `alembic upgrade head` - Run database migrations

## Planned Architecture (From Planning Docs)

### Core Components
- **Diana Master System**: AI orchestrator for adaptive context and personalization
- **Gamification Service**: Points ("Besitos"), achievements, leaderboards, streaks  
- **Narrative Service**: Interactive stories with branching decision trees
- **Admin Service**: User management, analytics dashboard, content moderation
- **Monetization Service**: VIP subscriptions, payment processing, revenue tracking
- **Event Bus**: Redis pub/sub for inter-service communication

### Architecture Layers
1. **Presentation Layer**: Telegram Bot Interface (aiogram 3.x)
2. **Orchestration Layer**: Diana Master System (AI-driven context engine)
3. **Business Logic Layer**: Core services (Gamification, Narrative, Admin, Monetization)
4. **Integration Layer**: Event Bus (Redis pub/sub) & External APIs
5. **Data Layer**: PostgreSQL + Redis caching

## Key Planning Documents

- `docs/planning/01-PRD.md` - Product Requirements Document with user personas and features
- `docs/planning/04-technical-architecture.md` - Detailed technical architecture (1000+ lines)
- `docs/planning/06-implementation-plan.md` - 24-week implementation timeline
- `docs/planning/05-testing-qa-plan.md` - Testing strategy and QA requirements
- `docs/planning/09-implementation-workflow.md` - Development workflow and practices

## Development Principles (From Architecture Doc)

1. **Event-Driven Architecture**: Services communicate via Redis pub/sub
2. **API-First Design**: All functionality exposed via clean APIs  
3. **Test-Driven Development**: Write tests first, then implementation
4. **Clean Architecture**: Clear separation of layers and responsibilities
5. **Security by Design**: Security integrated from the foundation
6. **Scalability by Design**: Prepared for 100K+ concurrent users

## Quality Requirements

- **Test Coverage**: >90% for critical business logic
- **Response Time**: <2 seconds for 95% of operations
- **Code Quality**: Maintainability index >70
- **Uptime**: 99.9% availability target
- **Performance**: Handle 1000+ requests per second
- **Security**: Zero tolerance for data breaches

## Current Dependencies

From `requirements.txt`:
```
pytest>=7.0.0
pytest-cov>=4.0.0  
black>=23.0.0
pylint>=2.17.0
mypy>=1.0.0
flake8>=6.0.0
```

## Implementation Status

- ✅ Comprehensive planning documentation (8 detailed docs)
- ✅ Development environment requirements defined
- ✅ Architecture fully designed and documented  
- 🔄 **Ready for Phase 1 implementation**
- ❌ No source code implemented yet
- ❌ No infrastructure setup yet

## Notes for Development

- This is a **greenfield project** - start implementation from scratch following the architecture
- All references should use exact paths and names as will be configured
- Follow the event-driven architecture patterns outlined in technical docs
- Implement TDD approach with >90% coverage requirement
- Use the detailed technical architecture doc as the implementation blueprint
- Leer, comprender y basarse en el documento de development.md para el desarrollo.
- Al término de cada fase, realiza un commit según lo estipulado en el documento de desarrollo con un mensaje explicativo. Evite el uso de referencias a Claude Code al final del commit. Esto ya lo hace Git. Evitemos redundancias.
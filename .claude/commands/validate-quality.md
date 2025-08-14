# Validate Code Quality

Run complete quality validation suite for current changes.

## Validation Steps:
1. Run test suite with coverage
2. Code formatting check
3. Linting analysis
4. Type checking
5. Integration validation

## Commands to execute:
```bash
pytest tests/ --cov=src --cov-report=html --cov-fail-under=90
black src/ tests/ --check
pylint src/ --fail-under=8.0
mypy src/ --strict
```

## Success Criteria:
- All tests passing
- Coverage ≥90%
- No formatting issues
- Pylint score ≥8.0
- No mypy errors
# Test Integration

Run comprehensive integration tests across system components.

## Integration Test Types:
1. **Event Bus Integration**: Test event publishing and consumption
2. **Database Integration**: Test with real database using testcontainers
3. **Service Integration**: Test inter-service communication
4. **End-to-End Workflows**: Test complete user journeys
5. **Performance Tests**: Validate response times and throughput

## Commands to execute:
```bash
pytest tests/integration/ -v --tb=short
pytest tests/e2e/ -v --tb=short
pytest tests/performance/ -v --benchmark-only
```

## Success Criteria:
- All integration tests passing
- Event flows working correctly
- Database transactions successful
- Performance benchmarks met
- No race conditions detected
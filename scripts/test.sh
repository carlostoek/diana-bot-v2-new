#!/bin/bash
# Test script

echo "🧪 Running tests..."

# Activate virtual environment if exists
if [[ -d venv ]]; then
    source venv/bin/activate
fi

# Run tests with pytest
if command -v pytest >/dev/null 2>&1; then
    pytest tests/ -v --tb=short
else
    python -m pytest tests/ -v --tb=short
fi

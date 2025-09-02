#!/bin/bash
# Development script

echo "🚀 Starting development environment..."

# Activate virtual environment if exists
if [[ -d venv ]]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Install dependencies
if [[ -f requirements.txt ]]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
fi

# Run application in development mode
export ENVIRONMENT=development
python src/main.py

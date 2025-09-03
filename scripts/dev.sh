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

# Run database migrations
echo "⚙️ Running database migrations..."
alembic upgrade head
echo "✅ Database is up to date"

# Run application in development mode
export ENVIRONMENT=development
echo "🤖 Starting the bot..."
python -m src.main

#!/bin/bash
# Smart Pre-commit Script for TDD Development Phases
# Adapts quality gates based on TDD phase detected in commit message
#
# Usage: Called automatically by pre-commit hooks
# Phases:
#   🔴 RED: Only code style checks (tests expected to fail)
#   🟢 GREEN: Full quality gates (tests must pass)
#   🔄 REFACTOR: Full quality gates (tests must pass)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if this is a RED phase commit
is_red_phase() {
    # Check the commit message being prepared (staged commit)
    if [ -f .git/COMMIT_EDITMSG ]; then
        if grep -q "🔴 RED:" .git/COMMIT_EDITMSG; then
            return 0
        fi
    fi

    # Fallback: check last commit message
    if git log -1 --pretty=%B 2>/dev/null | grep -q "🔴 RED:"; then
        return 0
    fi

    return 1
}

# Function to check TDD phase from environment or commit message
get_tdd_phase() {
    if [ "$TDD_PHASE" = "RED" ]; then
        echo "RED"
    elif [ "$TDD_PHASE" = "GREEN" ]; then
        echo "GREEN"
    elif [ "$TDD_PHASE" = "REFACTOR" ]; then
        echo "REFACTOR"
    elif [ -f .git/COMMIT_EDITMSG ]; then
        if grep -q "🔴 RED:" .git/COMMIT_EDITMSG; then
            echo "RED"
        elif grep -q "🟢 GREEN:" .git/COMMIT_EDITMSG; then
            echo "GREEN"
        elif grep -q "🔄 REFACTOR:" .git/COMMIT_EDITMSG; then
            echo "REFACTOR"
        else
            echo "GREEN"
        fi
    else
        # Check last commit
        if git log -1 --pretty=%B 2>/dev/null | grep -q "🔴 RED:"; then
            echo "RED"
        elif git log -1 --pretty=%B 2>/dev/null | grep -q "🟢 GREEN:"; then
            echo "GREEN"
        elif git log -1 --pretty=%B 2>/dev/null | grep -q "🔄 REFACTOR:"; then
            echo "REFACTOR"
        else
            echo "GREEN"
        fi
    fi
}

# Function to run code style checks only (RED phase)
run_red_phase_checks() {
    print_status $RED "🔴 RED PHASE DETECTED"
    print_status $YELLOW "Running code style checks only (tests expected to fail by design)"
    echo

    # Check if Black would make changes (dry run)
    print_status $BLUE "Checking code formatting with Black..."
    if ! black src/ tests/ --check --quiet; then
        print_status $RED "❌ Code formatting issues found. Run 'make format' to fix."
        return 1
    fi

    # Check if isort would make changes (dry run)
    print_status $BLUE "Checking import sorting with isort..."
    if ! isort src/ tests/ --check-only --quiet; then
        print_status $RED "❌ Import sorting issues found. Run 'make format' to fix."
        return 1
    fi

    print_status $GREEN "✅ RED phase quality checks passed"
    print_status $YELLOW "Note: Tests not executed (expected to fail in RED phase)"
    return 0
}

# Function to run full quality gates (GREEN/REFACTOR phases)
run_full_quality_gates() {
    local phase=$1
    print_status $GREEN "🟢 $phase PHASE - Running full quality gates"
    echo

    # Code style checks
    print_status $BLUE "1/6 Checking code formatting..."
    if ! black src/ tests/ --check --quiet; then
        print_status $RED "❌ Code formatting issues found. Run 'make format' to fix."
        return 1
    fi

    print_status $BLUE "2/6 Checking import sorting..."
    if ! isort src/ tests/ --check-only --quiet; then
        print_status $RED "❌ Import sorting issues found. Run 'make format' to fix."
        return 1
    fi

    # Linting
    print_status $BLUE "3/6 Running Flake8 linting..."
    if ! flake8 src/ tests/ --quiet; then
        print_status $RED "❌ Flake8 linting failed. Fix issues and retry."
        return 1
    fi

    print_status $BLUE "4/6 Running Pylint analysis..."
    if ! pylint src/diana_bot --score=no --reports=no --output-format=colorized; then
        print_status $RED "❌ Pylint analysis failed. Fix issues and retry."
        return 1
    fi

    # Type checking
    print_status $BLUE "5/6 Running MyPy type checking..."
    if ! mypy src/ --config-file=pyproject.toml; then
        print_status $RED "❌ Type checking failed. Fix type issues and retry."
        return 1
    fi

    # Test execution with coverage
    print_status $BLUE "6/6 Running tests with coverage..."
    if ! pytest tests/ --cov=src/diana_bot --cov-fail-under=90 --quiet --tb=short; then
        print_status $RED "❌ Tests failed or coverage below 90%. Fix issues and retry."
        return 1
    fi

    print_status $GREEN "✅ All $phase phase quality gates passed"
    return 0
}

# Main execution
main() {
    print_status $BLUE "=== Diana Bot V2 Smart Pre-commit Quality Gates ==="
    echo

    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_status $RED "❌ Not in a git repository"
        exit 1
    fi

    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    # Determine TDD phase and run appropriate checks
    tdd_phase=$(get_tdd_phase)
    
    if [ "$tdd_phase" = "RED" ]; then
        run_red_phase_checks
    else
        if [ "$tdd_phase" = "GREEN" ] || [ "$tdd_phase" = "REFACTOR" ]; then
            run_full_quality_gates "$tdd_phase"
        else
            # Default to GREEN phase for production-ready commits
            print_status $YELLOW "No TDD phase marker detected - defaulting to GREEN phase"
            run_full_quality_gates "GREEN"
        fi
    fi

    exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo
        print_status $GREEN "🎉 Pre-commit quality gates completed successfully!"
    else
        echo
        print_status $RED "💥 Pre-commit quality gates failed!"
        print_status $YELLOW "Fix the issues above and retry your commit."
    fi

    exit $exit_code
}

# Execute main function
main "$@"
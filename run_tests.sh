#!/usr/bin/env bash
#
# JBLPc automated test suite runner
# Runs all protocol, CLI e2e, TUI headless, fault injection, and battery health tests.
# Runs 100% offline in CI without physical Bluetooth hardware.
# Generates reports/exception_report.md and reports/exception_report.json.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "🎧 JBLPc Test Suite & Verification Runner"
echo "=================================================="

# 1. Virtual Environment Setup
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in .venv..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# 2. Dependency Installation
echo "Installing/verifying dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 3. Pytest Execution (Excludes real hardware by default)
echo ""
echo "Running pytest suite (-m 'not hardware')..."
echo "=================================================="
pytest -v --strict-markers -m "not hardware" "$@"

PYTEST_EXIT=$?

# 4. Generate Exception and Fault Coverage Reports
echo ""
echo "Generating exception and fault injection reports..."
python3 scripts/generate_exception_report.py

echo ""
echo "=================================================="
echo "✓ All tests completed successfully!"
echo "✓ Reports written to:"
echo "   - reports/exception_report.md"
echo "   - reports/exception_report.json"
echo "=================================================="

exit "$PYTEST_EXIT"

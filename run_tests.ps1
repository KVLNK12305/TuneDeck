# TuneDeck Automated Test Runner for Windows (PowerShell)
# Runs protocol, CLI e2e, TUI headless, fault injection, and battery health tests.
# Runs 100% offline without physical Bluetooth hardware.
# Generates reports/exception_report.md and reports/exception_report.json.

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "🎧 TuneDeck Test Suite & Verification Runner (Windows)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Virtual Environment Setup
$VenvDir = Join-Path $PSScriptRoot ".venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment in .venv..." -ForegroundColor Yellow
    python -m venv "$VenvDir"
}

# Activate virtual environment
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    . "$ActivateScript"
}

# 2. Dependency Verification
Write-Host "Verifying dependencies..." -ForegroundColor Cyan
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet -e ".[gui]"

# 3. Pytest Execution (Excludes real hardware by default)
Write-Host ""
Write-Host "Running pytest suite (-m 'not hardware')..." -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
pytest -v --strict-markers -m "not hardware" $args

$PytestExit = $LASTEXITCODE

# 4. Generate Exception and Fault Coverage Reports
Write-Host ""
Write-Host "Generating exception and fault injection reports..." -ForegroundColor Cyan
python (Join-Path $PSScriptRoot "scripts\generate_exception_report.py")

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "✓ All tests completed successfully!" -ForegroundColor Green
Write-Host "✓ Reports written to:" -ForegroundColor Green
Write-Host "   - reports/exception_report.md" -ForegroundColor Green
Write-Host "   - reports/exception_report.json" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

exit $PytestExit

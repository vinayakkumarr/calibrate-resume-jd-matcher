# ==============================================================================
# JD Analyser: Master Quality and Health Test Suite (run-tests.ps1)
# Executes all 4 architecture verification layers sequentially and displays
# a unified summary scorecard with execution timings and pass/fail metrics.
# ==============================================================================

[CmdletBinding()]
param()

$ScriptDir = $PSScriptRoot
Set-Location $ScriptDir

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "     JD ANALYSER (FREE COMMUNITY EDITION) - TEST RUNNER           " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

$OverallStartTime = [System.Diagnostics.Stopwatch]::StartNew()

# 1. Resolve Runtimes dynamically
$PythonBin = Join-Path $ScriptDir "engine\venv\Scripts\python.exe"
if (-not (Test-Path $PythonBin)) {
    $PythonBin = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonBin) {
        Write-Error "Python runtime not found. Please initialize virtual environment in engine\venv."
        exit 1
    }
}

$PhpBin = (Get-Command php -ErrorAction SilentlyContinue).Source
if (-not $PhpBin) {
    Write-Error "PHP runtime not found in PATH. Please install PHP 8.2+."
    exit 1
}

$NodeBin = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $NodeBin) {
    Write-Error "Node runtime not found in PATH. Please ensure Node.js is installed for frontend test verification."
    exit 1
}

$TestResults = @()

function Run-TestLayer {
    param(
        [string]$LayerName,
        [string]$Command,
        [string[]]$Arguments
    )

    Write-Host "------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host ">> EXECUTING: $LayerName" -ForegroundColor Yellow
    Write-Host "   Command: $Command $($Arguments -join ' ')" -ForegroundColor DarkGray
    Write-Host ""

    $Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    
    $proc = Start-Process -FilePath $Command -ArgumentList $Arguments -NoNewWindow -PassThru -Wait
    $Stopwatch.Stop()
    $DurationSec = [math]::Round($Stopwatch.Elapsed.TotalSeconds, 2)

    $passed = ($proc.ExitCode -eq 0)

    if ($passed) {
        Write-Host ""
        Write-Host " [PASS] $LayerName completed in ${DurationSec}s" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host " [FAIL] $LayerName exited with error code $($proc.ExitCode) after ${DurationSec}s" -ForegroundColor Red
    }

    $script:TestResults += [PSCustomObject]@{
        Layer    = $LayerName
        Passed   = $passed
        Duration = $DurationSec
    }
}

# Layer 1: HTTP Gateway Verification
$GatewayTest = Join-Path $ScriptDir "tests\test_gateway_http.py"
Run-TestLayer -LayerName "Layer 1: HTTP Gateway Tests" -Command $PythonBin -Arguments @($GatewayTest)

# Layer 2: Core Intelligence CLI and Determinism Verification
$EngineTest = Join-Path $ScriptDir "tests\test_engine_cli.py"
Run-TestLayer -LayerName "Layer 2: Python Engine Core and Determinism" -Command $PythonBin -Arguments @($EngineTest)

# Layer 3: Frontend Logic and Metric Guard Unit Tests
$FrontendTest = Join-Path $ScriptDir "tests\test_frontend_logic.js"
Run-TestLayer -LayerName "Layer 3: Frontend Logic and Metric Guard" -Command $NodeBin -Arguments @($FrontendTest)

# Layer 4: Storage and Cleanup Daemon Simulation
$CleanupCron = Join-Path $ScriptDir "cron\cleanup.php"
Run-TestLayer -LayerName "Layer 4: Storage and Cleanup Daemon Dry-Run" -Command $PhpBin -Arguments @($CleanupCron, "--dry-run")

$OverallStartTime.Stop()
$TotalElapsed = [math]::Round($OverallStartTime.Elapsed.TotalSeconds, 2)

# ==============================================================================
# SUMMARY SCORECARD DASHBOARD
# ==============================================================================
Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "                   QUALITY SCORECARD SUMMARY                      " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

$PassedCount = ($TestResults | Where-Object { $_.Passed }).Count
$FailedCount = ($TestResults | Where-Object { -not $_.Passed }).Count
$TotalCount  = $TestResults.Count

foreach ($res in $TestResults) {
    $statusText = if ($res.Passed) { "[PASS]" } else { "[FAIL]" }
    $statusColor = if ($res.Passed) { "Green" } else { "Red" }
    
    $paddedName = $res.Layer.PadRight(45, ' ')
    $paddedTime = ("{0:N2}s" -f $res.Duration).PadLeft(8, ' ')
    
    Write-Host " $paddedName $paddedTime  " -NoNewline
    Write-Host $statusText -ForegroundColor $statusColor
}

Write-Host "------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host " Total Executed: $TotalCount  |  Passed: $PassedCount  |  Failed: $FailedCount  |  Time: ${TotalElapsed}s" -ForegroundColor Cyan

if ($FailedCount -eq 0) {
    Write-Host ""
    Write-Host " [VERDICT] ALL ARCHITECTURAL TEST LAYERS PASSED WITH 100% SUCCESS" -ForegroundColor Green
    Write-Host "==================================================================" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host ""
    Write-Host " [VERDICT] TEST SUITE FAILED WITH $FailedCount DEFECT(S)" -ForegroundColor Red
    Write-Host "==================================================================" -ForegroundColor Cyan
    exit 1
}

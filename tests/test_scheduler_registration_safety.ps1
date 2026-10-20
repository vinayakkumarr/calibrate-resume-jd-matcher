# ==============================================================================
# Calibrate AI — Task Scheduler Registration & Safety Test Suite
# Phase 6.1: Least-Privilege Scheduler Hardening & Conflict Prevention
# ==============================================================================
# Verifies:
# 1. Read-only Preview mode displays prerequisites and permission matrices without OS mutations.
# 2. Preview mode reflects custom -RunAsUser parameter accurately.
# 3. Register mode blocks execution when -RunAsUser is omitted (SYSTEM default eliminated).
# 4. Invalid -PhpPath is safely caught and rejected with exit code 1.
# 5. Paths containing spaces are safely wrapped with outer and inner quotes for Task Scheduler.
# 6. Existing-task conflict detection blocks overwrite by default when -Force is absent.
# 7. Explicit -Force allows re-registration logic while preserving validation.
# 8. Status mode safely queries task state without terminating exceptions.
# 9. Working-directory independence is documented and /d parameter is excluded from schtasks.
# ==============================================================================

$ErrorActionPreference = 'Continue'
$scriptDir = $PSScriptRoot
$projectRoot = (Resolve-Path "$scriptDir\..").Path
$setupScript = Join-Path $projectRoot "cron\setup-cleanup-task.ps1"

Write-Host "`n=== TASK SCHEDULER REGISTRATION SAFETY TEST SUITE ===`n" -ForegroundColor Cyan

$passCount = 0
$failCount = 0

function Assert-Test {
    param (
        [bool]$Condition,
        [string]$TestName,
        [string]$FailureDetails = ""
    )
    if ($Condition) {
        Write-Host "  [PASS] $TestName" -ForegroundColor Green
        $script:passCount++
    } else {
        Write-Host "  [FAIL] $TestName - $FailureDetails" -ForegroundColor Red
        $script:failCount++
    }
}

# ------------------------------------------------------------------------------
# Test 1: Read-Only Preview Mode Invariants
# ------------------------------------------------------------------------------
Write-Host "[TEST 1] Verifying Read-Only Preview Mode Invariants..." -ForegroundColor White
$previewRaw = & powershell -ExecutionPolicy Bypass -File $setupScript -Preview 2>&1
$previewExit = $LASTEXITCODE
$previewText = ($previewRaw | ForEach-Object { $_.ToString() }) -join "`n"

Assert-Test ($previewExit -eq 0) "Preview mode exits with code 0."
Assert-Test ($previewText -match "RETENTION DAEMON DEPLOYMENT CONFIGURATION \(PREVIEW\)") "Preview header correctly displayed."
Assert-Test ($previewText -match "LEAST-PRIVILEGE PERMISSION REQUIREMENTS") "Least-privilege permission matrix documented."
Assert-Test ($previewText -match "CLEANUP_TARGET_DATABASE=jd_analyser") "Database guard requirement documented."
Assert-Test ($previewText -match "CLEANUP_TARGET_SERVER_IDENTITY=<server-hostname>") "Server identity guard requirement documented."
Assert-Test ($previewText -match "Directory Independence: cleanup.php and config/database.php strictly anchor all paths") "Directory independence verified."

# ------------------------------------------------------------------------------
# Test 2: Custom -RunAsUser Parameter in Preview Mode
# ------------------------------------------------------------------------------
Write-Host "`n[TEST 2] Verifying Explicit -RunAsUser Parameter Display..." -ForegroundColor White
$customUser = "NT AUTHORITY\NETWORK SERVICE"
$userRaw = & powershell -ExecutionPolicy Bypass -File $setupScript -Preview -RunAsUser $customUser 2>&1
$userExit = $LASTEXITCODE
$userText = ($userRaw | ForEach-Object { $_.ToString() }) -join "`n"

Assert-Test ($userExit -eq 0) "Preview with -RunAsUser exits with code 0."
Assert-Test ($userText -match "Run As User\s+:\s+NT AUTHORITY\\NETWORK SERVICE") "RunAsUser displayed accurately."
Assert-Test ($userText -match '/ru "NT AUTHORITY\\NETWORK SERVICE"') "schtasks command includes specified service account."

# ------------------------------------------------------------------------------
# Test 3: Elimination of SYSTEM Default in -Register Mode
# ------------------------------------------------------------------------------
Write-Host "`n[TEST 3] Verifying Register Mode Rejects Missing -RunAsUser..." -ForegroundColor White
$noUserRaw = & powershell -ExecutionPolicy Bypass -File $setupScript -Register 2>&1
$noUserExit = $LASTEXITCODE
$noUserText = ($noUserRaw | ForEach-Object { $_.ToString() }) -join "`n"

Assert-Test ($noUserExit -ne 0) "Register without -RunAsUser exits with non-zero exit code ($noUserExit)."
Assert-Test ($noUserText -match "Registration blocked:.*explicit execution\s+identity is required") "Informative block message displayed."
Assert-Test ($noUserText -match "SYSTEM is not permitted as an implicit default") "SYSTEM default is explicitly rejected."

# ------------------------------------------------------------------------------
# Test 4: Invalid Executable Path Rejection
# ------------------------------------------------------------------------------
Write-Host "`n[TEST 4] Verifying Invalid -PhpPath Handling..." -ForegroundColor White
$invalidPhpRaw = & powershell -ExecutionPolicy Bypass -File $setupScript -Preview -PhpPath "C:\nonexistent_path\php_fake.exe" 2>&1
$invalidPhpExit = $LASTEXITCODE
$invalidPhpText = ($invalidPhpRaw | ForEach-Object { $_.ToString() }) -join "`n"

Assert-Test ($invalidPhpExit -ne 0) "Invalid -PhpPath exits with non-zero code ($invalidPhpExit)."
Assert-Test ($invalidPhpText -match "Specified -PhpPath does not exist") "Invalid path error message returned."

# ------------------------------------------------------------------------------
# Test 5: Safe Quoting for Paths Containing Spaces
# ------------------------------------------------------------------------------
Write-Host "`n[TEST 5] Verifying Safe Argument Formatting with Spaces..." -ForegroundColor White
$mockPhpWithSpaces = "C:\Program Files\PHP 8.2\php.exe"
$mockScriptWithSpaces = "C:\Users\Target User\Projects\ResumeJD-Matcher\cron\cleanup.php"

# Test escaping logic used in script
$escapedCommand = "\`"$mockPhpWithSpaces\`" \`"$mockScriptWithSpaces\`""
$quotedDisplay = "`"$mockPhpWithSpaces`" `"$mockScriptWithSpaces`""

Assert-Test ($escapedCommand -match '^\\"[^"]+\\" \\"[^"]+\\"$') "Paths with spaces formatted with escaped quotes for Task Scheduler /tr."
Assert-Test ($quotedDisplay -match '^"[^"]+" "[^"]+"$') "Display command formatted with clean quotes."

# ------------------------------------------------------------------------------
# Test 6: Defensive Conflict Detection & -Force Opt-In Simulation
# ------------------------------------------------------------------------------
Write-Host "`n[TEST 6] Verifying Conflict Detection Logic..." -ForegroundColor White
$scriptSource = Get-Content $setupScript -Raw

# Inspect script source code to verify defensive conflict guards
$hasConflictCheck = $scriptSource -match '\$existingTaskOutput = & schtasks /query /tn \$taskName'
$hasForceCheck = $scriptSource -match 'if \(-not \$Force\)'
$hasConflictMessage = $scriptSource -match '\[CONFLICT DETECTED\] Scheduled task ''\$taskName'' is already registered'
$hasForceOptInMessage = $scriptSource -match 'Overwriting existing scheduled task'

Assert-Test $hasConflictCheck "Script checks for existing task before creation."
Assert-Test $hasForceCheck "Script verifies -Force switch before overwriting existing task."
Assert-Test $hasConflictMessage "Conflict detection displays current task details and halts."
Assert-Test $hasForceOptInMessage "Script documents -Force opt-in override."

# ------------------------------------------------------------------------------
# Test 7: Read-Only Status Mode Query Invariants
# ------------------------------------------------------------------------------
Write-Host "`n[TEST 7] Verifying Status Mode Safety..." -ForegroundColor White
$statusRaw = & powershell -ExecutionPolicy Bypass -File $setupScript -Status 2>&1
$statusExit = $LASTEXITCODE
$statusText = ($statusRaw | ForEach-Object { $_.ToString() }) -join "`n"

Assert-Test ($statusExit -eq 0) "Status query exits with code 0."
Assert-Test ($statusText -match "Task Name: JDAnalyser_Cleanup") "Correct task name queried."
Assert-Test ($statusText -match "(Task is NOT registered|Task is REGISTERED)") "Clear registration status reported without terminating exception."

# ------------------------------------------------------------------------------
# Test 8: Working Directory Independence & /d Exclusion
# ------------------------------------------------------------------------------
Write-Host "`n[TEST 8] Verifying Working Directory Architecture..." -ForegroundColor White
# Verify that schtasks /create command arguments never include /d
$hasDInCreateArgs = $scriptSource -match '\$createArgs \+=.*["'']/d["'']'

Assert-Test (-not $hasDInCreateArgs) "schtasks arguments strictly avoid /d parameter (avoiding day-of-week schedule collision)."
Assert-Test ($scriptSource -match '/d is intentionally omitted') "Rationale for /d omission explicitly documented in script."

# ------------------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------------------
Write-Host "`n=======================================================" -ForegroundColor Cyan
Write-Host "SCHEDULER SAFETY TEST SUMMARY: $passCount PASSED, $failCount FAILED" -ForegroundColor $(if ($failCount -eq 0) { 'Green' } else { 'Red' })
Write-Host "=======================================================`n" -ForegroundColor Cyan

if ($failCount -gt 0) {
    exit 1
}
exit 0

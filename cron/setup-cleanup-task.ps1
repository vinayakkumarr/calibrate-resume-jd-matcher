<#
.SYNOPSIS
    Reproducible deployment helper for the Calibrate AI / ResumeJD-Matcher 2-Hour Retention Daemon.

.DESCRIPTION
    Configures, inspects, and manages the Windows Task Scheduler hourly retention task
    under a least-privilege execution identity without hardcoding local machine paths or secrets.

.PARAMETER Preview
    (Default) Validates prerequisites and displays the exact command, execution identity,
    and required permissions without modifying operating system settings or filesystem state.

.PARAMETER Status
    Queries Windows Task Scheduler to inspect the current registration state, last run time,
    and exit code of the retention task without mutating state.

.PARAMETER Register
    Registers the hourly cleanup task in Windows Task Scheduler. Requires an elevated (Administrator) terminal
    and an explicitly specified -RunAsUser identity.

.PARAMETER Force
    Explicit opt-in required when registering if a task named JDAnalyser_Cleanup already exists.
    Prevents silent, unintended overwrites of existing scheduled tasks.

.PARAMETER Unregister
    Removes the cleanup task from Windows Task Scheduler. Requires an elevated terminal.

.PARAMETER PhpPath
    Optional explicit path to php.exe. If omitted, resolves php.exe from system PATH or common locations.

.PARAMETER RunAsUser
    Explicit execution identity (e.g. 'NT AUTHORITY\NETWORK SERVICE' or a dedicated local user 'svc_jdcleaner').
    SYSTEM is never assumed as an implicit default.

.EXAMPLE
    .\cron\setup-cleanup-task.ps1 -Preview
    .\cron\setup-cleanup-task.ps1 -Preview -RunAsUser "NT AUTHORITY\NETWORK SERVICE"
    .\cron\setup-cleanup-task.ps1 -Status
    .\cron\setup-cleanup-task.ps1 -Register -RunAsUser "NT AUTHORITY\NETWORK SERVICE"
    .\cron\setup-cleanup-task.ps1 -Register -Force -RunAsUser "NT AUTHORITY\NETWORK SERVICE"
    .\cron\setup-cleanup-task.ps1 -Unregister
#>

[CmdletBinding(DefaultParameterSetName = 'Preview')]
param (
    [Parameter(ParameterSetName = 'Preview')]
    [switch]$Preview,

    [Parameter(ParameterSetName = 'Status')]
    [switch]$Status,

    [Parameter(ParameterSetName = 'Register')]
    [switch]$Register,

    [Parameter(ParameterSetName = 'Register')]
    [switch]$Force,

    [Parameter(ParameterSetName = 'Unregister')]
    [switch]$Unregister,

    [Parameter()]
    [string]$PhpPath,

    [Parameter()]
    [string]$RunAsUser
)

$ErrorActionPreference = 'Stop'

# 1. Resolve Project Root and Cleanup Script Dynamically
$scriptDir = $PSScriptRoot
$projectRoot = (Resolve-Path "$scriptDir\..").Path
$cleanupScript = Join-Path $scriptDir "cleanup.php"

if (-not (Test-Path $cleanupScript)) {
    Write-Error "Cleanup script not found at expected location: $cleanupScript"
    exit 1
}

$taskName = "JDAnalyser_Cleanup"

# 2. Status Mode (Purely Read-Only)
if ($Status) {
    Write-Host "`n[TASK SCHEDULER STATUS CHECK]" -ForegroundColor Cyan
    Write-Host "Task Name: $taskName"
    
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $result = & schtasks /query /tn $taskName /fo LIST /v 2>&1
    $queryExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP

    if ($queryExit -eq 0) {
        Write-Host "`nTask is REGISTERED in Windows Task Scheduler:`n" -ForegroundColor Green
        $result | ForEach-Object { Write-Host "  $_" }
        exit 0
    } else {
        Write-Host "`nTask is NOT registered in Windows Task Scheduler." -ForegroundColor Yellow
        Write-Host "Details: The task '$taskName' does not exist in the schedule.`n" -ForegroundColor Gray
        exit 0
    }
}

# 3. Unregister Mode
if ($Unregister) {
    Write-Host "`n[UNREGISTER TASK]" -ForegroundColor Yellow
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Error "Unregistering a scheduled task requires an elevated Administrator terminal. Please rerun as Administrator."
        exit 1
    }

    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $null = & schtasks /query /tn $taskName 2>&1
    $taskExists = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEAP

    if (-not $taskExists) {
        Write-Host "Task '$taskName' is not registered in Windows Task Scheduler. Nothing to unregister." -ForegroundColor Yellow
        exit 0
    }

    try {
        & schtasks /delete /tn $taskName /f
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Task '$taskName' successfully unregistered." -ForegroundColor Green
            exit 0
        } else {
            Write-Error "schtasks exited with code $LASTEXITCODE while deleting task '$taskName'."
            exit $LASTEXITCODE
        }
    } catch {
        Write-Error "Failed to unregister task: $_"
        exit 1
    }
}

# 4. Resolve PHP Binary
$resolvedPhp = $null
if ($PhpPath) {
    if (Test-Path $PhpPath) {
        $resolvedPhp = (Resolve-Path $PhpPath).Path
    } else {
        Write-Error "Specified -PhpPath does not exist: $PhpPath"
        exit 1
    }
} else {
    $pathPhp = Get-Command "php.exe" -ErrorAction SilentlyContinue
    if ($pathPhp) {
        $resolvedPhp = $pathPhp.Source
    } else {
        $commonLocations = @(
            "C:\xampp\php\php.exe",
            "C:\tools\php\php.exe",
            "C:\php\php.exe",
            "C:\Program Files\PHP\php.exe"
        )
        foreach ($loc in $commonLocations) {
            if (Test-Path $loc) {
                $resolvedPhp = $loc
                break
            }
        }
    }
}

if (-not $resolvedPhp) {
    Write-Error "Could not resolve php.exe in system PATH or common locations. Please specify -PhpPath <path-to-php.exe>."
    exit 1
}

# 5. Storage Directories (Non-mutating in Preview; created only during Register if missing)
$storageDir = Join-Path $projectRoot "storage"
$uploadsDir = Join-Path $storageDir "uploads"
$logsDir    = Join-Path $storageDir "logs"

if ($Register) {
    foreach ($d in @($storageDir, $uploadsDir, $logsDir)) {
        if (-not (Test-Path $d)) {
            New-Item -ItemType Directory -Path $d -Force | Out-Null
        }
    }
}

# 6. Task Command Construction & Escaping (Supports paths with spaces)
$taskCommand = "\`"$resolvedPhp\`" \`"$cleanupScript\`""
$displayCommand = "`"$resolvedPhp`" `"$cleanupScript`""
$effectiveUser = if ($RunAsUser) { $RunAsUser } else { "<AccountName>" }
$schtasksDisplay = "schtasks /create /sc hourly /mo 1 /tn `"$taskName`" /tr `"\`"$resolvedPhp\`" \`"$cleanupScript\`"`" /st 00:00 /ru `"$effectiveUser`""

# 7. Preview Mode (Default — Purely Read-Only)
if ($Preview -or (-not $Status -and -not $Register -and -not $Unregister)) {
    Write-Host "`n========================================================" -ForegroundColor Cyan
    Write-Host "  RETENTION DAEMON DEPLOYMENT CONFIGURATION (PREVIEW)  " -ForegroundColor Cyan
    Write-Host "========================================================`n" -ForegroundColor Cyan

    Write-Host "Prerequisites Check:" -ForegroundColor White
    Write-Host "  [OK] Project Directory : $projectRoot" -ForegroundColor Green
    Write-Host "  [OK] Cleanup Script    : $cleanupScript" -ForegroundColor Green
    Write-Host "  [OK] PHP Executable    : $resolvedPhp" -ForegroundColor Green
    $storageStatus = if (Test-Path $storageDir) { "[OK]" } else { "[MISSING]" }
    $storageColor  = if (Test-Path $storageDir) { "Green" } else { "Yellow" }
    $uploadsStatus = if (Test-Path $uploadsDir) { "[OK]" } else { "[MISSING]" }
    $uploadsColor  = if (Test-Path $uploadsDir) { "Green" } else { "Yellow" }
    $logsStatus    = if (Test-Path $logsDir) { "[OK]" } else { "[MISSING]" }
    $logsColor     = if (Test-Path $logsDir) { "Green" } else { "Yellow" }

    Write-Host "  $storageStatus Storage Directory : $storageDir" -ForegroundColor $storageColor
    Write-Host "  $uploadsStatus Uploads Directory : $uploadsDir" -ForegroundColor $uploadsColor
    Write-Host "  $logsStatus Logs Directory    : $logsDir" -ForegroundColor $logsColor

    Write-Host "`nScheduled Task Details:" -ForegroundColor White
    Write-Host "  Task Name     : $taskName"
    Write-Host "  Schedule      : Hourly (/sc hourly /mo 1)"
    if ($RunAsUser) {
        Write-Host "  Run As User   : $RunAsUser" -ForegroundColor Green
    } else {
        Write-Host "  Run As User   : [NOT SPECIFIED] (Must specify -RunAsUser <AccountName> before registration)" -ForegroundColor Yellow
    }
    Write-Host "  Execution Cmd : $displayCommand"

    Write-Host "`nWorking Directory Architecture:" -ForegroundColor White
    Write-Host "  Note: /d is intentionally omitted from schtasks because /d in schtasks specifies" -ForegroundColor Gray
    Write-Host "  days of the schedule (e.g. MON,TUE), not a working directory." -ForegroundColor Gray
    Write-Host "  Directory Independence: cleanup.php and config/database.php strictly anchor all paths" -ForegroundColor Gray
    Write-Host "  using PHP's __DIR__ filesystem constant. The daemon executes identically regardless of current working directory." -ForegroundColor Gray

    Write-Host "`n========================================================" -ForegroundColor Cyan
    Write-Host "  LEAST-PRIVILEGE PERMISSION REQUIREMENTS               " -ForegroundColor Cyan
    Write-Host "========================================================`n" -ForegroundColor Cyan
    Write-Host "To execute under a dedicated least-privilege service account (e.g. 'NT AUTHORITY\NETWORK SERVICE'" -ForegroundColor White
    Write-Host "or a dedicated local user 'svc_jdcleaner'), an administrator must ensure:`n" -ForegroundColor White

    Write-Host "1. Filesystem Permissions (NTFS ACLs):" -ForegroundColor Yellow
    Write-Host "   - Read & Execute : $resolvedPhp"
    Write-Host "   - Read-Only      : $projectRoot (including config\database.php and .env)"
    Write-Host "   - Modify/Delete  : $uploadsDir (to unlink expired *.pdf and *.extracted.txt)"
    Write-Host "   - Modify/Delete  : $logsDir (for cleanup.lock, cron_heartbeat.txt, and *.log)"
    Write-Host "   - Read-Only      : $cleanupScript"
    Write-Host "   * Restrict Write/Delete access everywhere else in the project root.`n"

    Write-Host "2. Database Privileges (MySQL):" -ForegroundColor Yellow
    Write-Host "   - SELECT         : scans"
    Write-Host "   - UPDATE         : scans (is_purged column)"
    Write-Host "   - DELETE         : scans (records > 30 days)"
    Write-Host "   - DELETE         : scan_results (required due to FOREIGN KEY (scan_id) ON DELETE CASCADE)"
    Write-Host "   * No permissions required on jd_target_cache, and no INSERT, DDL, or administrative grants.`n"

    Write-Host "3. Database & Server Guard Configuration (.env):" -ForegroundColor Yellow
    Write-Host "   - Required: CLEANUP_TARGET_DATABASE=jd_analyser"
    Write-Host "   - Required: CLEANUP_TARGET_SERVER_IDENTITY=<server-hostname> (from SELECT @@hostname; generic 'localhost' is prohibited)"
    Write-Host "   * Real cleanup fails closed before any deletion if these settings are missing, malformed, or mismatched.`n"

    Write-Host "Exact Registration Command:" -ForegroundColor Yellow
    Write-Host "  $schtasksDisplay" -ForegroundColor White

    Write-Host "`nDeployment Action Note:" -ForegroundColor Gray
    Write-Host "  To register this task on deployment, run from an Administrator terminal:"
    Write-Host "    .\cron\setup-cleanup-task.ps1 -Register -RunAsUser <AccountName>`n"
    exit 0
}

# 8. Register Mode
if ($Register) {
    Write-Host "`n[REGISTER SCHEDULED RETENTION TASK]" -ForegroundColor Cyan

    # Least-Privilege Requirement: Explicit execution identity is mandatory
    if (-not $RunAsUser -or [string]::IsNullOrWhiteSpace($RunAsUser)) {
        Write-Error "Registration blocked: An explicit execution identity is required. Please specify -RunAsUser <AccountName> (e.g. -RunAsUser 'NT AUTHORITY\NETWORK SERVICE' or a dedicated local user). SYSTEM is not permitted as an implicit default."
        exit 1
    }

    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Error "Registering a scheduled task requires an elevated Administrator terminal. Please rerun as Administrator or execute the command manually:`n$schtasksDisplay"
        exit 1
    }

    # Defensive Conflict Detection: Check if task already exists
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $existingTaskOutput = & schtasks /query /tn $taskName /fo LIST /v 2>&1
    $taskAlreadyExists = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEAP

    if ($taskAlreadyExists) {
        if (-not $Force) {
            Write-Host "`n[CONFLICT DETECTED] Scheduled task '$taskName' is already registered in Windows Task Scheduler." -ForegroundColor Yellow
            Write-Host "`nCurrent Registered Task Configuration:" -ForegroundColor White
            $existingTaskOutput | ForEach-Object { Write-Host "  $_" }
            Write-Error "Task '$taskName' already exists. Registration aborted without modifying the existing task. To overwrite the existing task with new settings, re-run with: .\cron\setup-cleanup-task.ps1 -Register -Force -RunAsUser `"$RunAsUser`""
            exit 1
        } else {
            Write-Host "`n[NOTICE] Overwriting existing scheduled task '$taskName' (-Force specified)." -ForegroundColor Yellow
        }
    }

    try {
        $createArgs = @("/create")
        if ($Force -or $taskAlreadyExists) {
            $createArgs += "/f"
        }
        $createArgs += @("/sc", "hourly", "/mo", "1", "/tn", $taskName, "/tr", $taskCommand, "/st", "00:00", "/ru", $RunAsUser)

        & schtasks @createArgs
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`nTask '$taskName' registered successfully under identity '$RunAsUser'!" -ForegroundColor Green
            Write-Host "Verify status anytime with:"
            Write-Host "  .\cron\setup-cleanup-task.ps1 -Status`n"
            exit 0
        } else {
            Write-Error "schtasks exited with code $LASTEXITCODE"
            exit $LASTEXITCODE
        }
    } catch {
        Write-Error "Failed to register task: $_"
        exit 1
    }
}

# ==============================================================================
# JD Analyser: Local Development Server Launcher (run-dev.ps1)
# Verifies environment variables, database connectivity, clears port conflicts,
# and starts the PHP development server.
# ==============================================================================

[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$ScriptDir = $PSScriptRoot
Set-Location $ScriptDir

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "       JD ANALYSER (FREE COMMUNITY EDITION) - DEV LAUNCHER        " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verify and Load .env
$EnvPath = Join-Path $ScriptDir ".env"
$EnvExamplePath = Join-Path $ScriptDir ".env.example"

if (-not (Test-Path $EnvPath)) {
    Write-Host "[WARNING] .env file not found. Initializing from .env.example..." -ForegroundColor Yellow
    if (Test-Path $EnvExamplePath) {
        Copy-Item -Path $EnvExamplePath -Destination $EnvPath
        Write-Host "[SUCCESS] Created .env from template. Please configure your GEMINI_API_KEY in .env." -ForegroundColor Green
    } else {
        Write-Error "Neither .env nor .env.example exists in $ScriptDir."
        exit 1
    }
}

# Parse .env configuration dynamically
$EnvConfig = @{}
Get-Content $EnvPath | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        $val = $parts[1].Trim().Trim('"').Trim("'")
        $EnvConfig[$key] = $val
        [System.Environment]::SetEnvironmentVariable($key, $val, [System.EnvironmentVariableTarget]::Process)
    }
}

$DbHost = if ($EnvConfig.ContainsKey("DB_HOST")) { $EnvConfig["DB_HOST"] } else { "127.0.0.1" }
$DbPort = if ($EnvConfig.ContainsKey("DB_PORT")) { [int]$EnvConfig["DB_PORT"] } else { 3306 }
$ServerHost = "127.0.0.1"
$ServerPort = 8000

# 2. Check Local Database Reachability
Write-Host "[1/4] Verifying database connectivity ($DbHost`:$DbPort)..." -NoNewline
$TcpClient = New-Object System.Net.Sockets.TcpClient
$ConnectAsync = $TcpClient.BeginConnect($DbHost, $DbPort, $null, $null)
$Connected = $ConnectAsync.AsyncWaitHandle.WaitOne(1500, $false)

if ($Connected -and $TcpClient.Connected) {
    $TcpClient.EndConnect($ConnectAsync)
    $TcpClient.Close()
    Write-Host " [ONLINE]" -ForegroundColor Green
} else {
    Write-Host " [OFFLINE]" -ForegroundColor Red
    Write-Host ""
    Write-Host "[ERROR] Could not connect to MySQL on $DbHost`:$DbPort." -ForegroundColor Red
    Write-Host "Please ensure your local MySQL/MariaDB service is running:" -ForegroundColor Yellow
    Write-Host "  - If using XAMPP: Open XAMPP Control Panel and start MySQL." -ForegroundColor Yellow
    Write-Host "  - If using standalone service: Run 'Start-Service MySQL' or 'mysqld.exe'." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# 3. Detect and Clear Orphaned Processes on Port 8000
Write-Host "[2/4] Checking availability of port $ServerPort..." -NoNewline
try {
    $ExistingConn = Get-NetTCPConnection -LocalPort $ServerPort -ErrorAction SilentlyContinue
    if ($ExistingConn) {
        $PidsToKill = $ExistingConn | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($procId in $PidsToKill) {
            if ($procId -gt 0 -and $procId -ne $PID) {
                Write-Host " [CLEARING PID $procId]" -ForegroundColor Yellow
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Milliseconds 600
    } else {
        Write-Host " [AVAILABLE]" -ForegroundColor Green
    }
} catch {
    Write-Host " [OK]" -ForegroundColor Green
}

# 4. Locate PHP Binary
Write-Host "[3/4] Resolving PHP runtime..." -NoNewline
$PhpBin = (Get-Command php -ErrorAction SilentlyContinue).Source
if (-not $PhpBin) {
    Write-Host " [MISSING]" -ForegroundColor Red
    Write-Error "PHP executable was not found in system PATH. Please install PHP 8.2+."
    exit 1
}
Write-Host " [$PhpBin]" -ForegroundColor Green

# 5. Launch PHP Server & Open Browser
$PublicDir = Join-Path $ScriptDir "public"
$ServerUrl = "http://$ServerHost`:$ServerPort"

Write-Host "[4/4] Starting PHP Development Server at $ServerUrl..." -ForegroundColor Green
Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   JD ANALYSER IS READY. PRESS CTRL+C IN THIS WINDOW TO STOP.    " -ForegroundColor Cyan
Write-Host "   Open URL: $ServerUrl                                           " -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

if (-not $NoBrowser) {
    Start-Process $ServerUrl
}

# Execute PHP development server in foreground (exits cleanly on Ctrl+C)
& $PhpBin -S "$ServerHost`:$ServerPort" -t $PublicDir

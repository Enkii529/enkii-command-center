<#
.SYNOPSIS
    Enkii Command Center - Full Startup Script

.DESCRIPTION
    Checks all dependencies, starts Docker services and Ollama,
    pulls required AI models if missing, then opens the dashboard.

.PARAMETER Build
    Force rebuild of Docker images before starting.

.PARAMETER Stop
    Stop all running services.

.PARAMETER Reset
    Stop services, wipe all volumes (database data), then restart fresh.

.PARAMETER Status
    Show current health of all services without starting anything.

.EXAMPLE
    .\start.ps1
    .\start.ps1 -Build
    .\start.ps1 -Status
    .\start.ps1 -Stop
    .\start.ps1 -Reset
#>
param(
    [switch]$Build,
    [switch]$Stop,
    [switch]$Reset,
    [switch]$Status
)

$ErrorActionPreference = "Continue"
$ProjectRoot = $PSScriptRoot

# ---- Color helpers ----
function Write-OK   { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Write-Fail { param($msg) Write-Host "  [XX]  $msg" -ForegroundColor Red }
function Write-Step { param($msg) Write-Host "  -->   $msg" -ForegroundColor Gray }
function Write-Head { param($msg) Write-Host "`n--- $msg ---`n" -ForegroundColor Cyan }

function Test-URL {
    param([string]$URL, [int]$TimeoutSec = 3)
    try {
        $null = Invoke-WebRequest -Uri $URL -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

Set-Location $ProjectRoot

# ---- -Stop ----
if ($Stop) {
    Write-Head "Stopping Enkii Command Center"
    docker compose down
    Write-OK "All services stopped."
    exit 0
}

# ---- -Reset ----
if ($Reset) {
    Write-Head "Resetting Enkii Command Center"
    $confirm = Read-Host "  This deletes ALL database data. Type YES to confirm"
    if ($confirm -ne "YES") {
        Write-Warn "Aborted."
        exit 0
    }
    docker compose down -v
    Write-OK "Services and volumes removed."
    Write-Step "Restarting fresh with -Build..."
    & $PSCommandPath -Build
    exit 0
}

# ---- Banner ----
Write-Host ""
Write-Host "  ENKII COMMAND CENTER" -ForegroundColor Magenta
Write-Host "  AI-Powered Dashboard + Automations" -ForegroundColor DarkGray
Write-Host ""

# ---- -Status ----
if ($Status) {
    Write-Head "Service Status"
    $checks = @(
        @("API          ", "http://localhost:8080/health"),
        @("Dashboard    ", "http://localhost:5629"),
        @("n8n          ", "http://localhost:5678"),
        @("Grafana      ", "http://localhost:3001"),
        @("Metabase     ", "http://localhost:3000"),
        @("Appsmith     ", "http://localhost:8081"),
        @("Prometheus   ", "http://localhost:9090"),
        @("Ollama       ", "http://localhost:11434/api/tags")
    )
    foreach ($c in $checks) {
        if (Test-URL $c[1]) {
            Write-OK "$($c[0])  $($c[1])"
        } else {
            Write-Fail "$($c[0])  $($c[1])"
        }
    }
    Write-Host ""
    docker compose ps
    exit 0
}

# ==============================================================
# DEPENDENCY CHECKS
# ==============================================================
Write-Head "Checking dependencies"

# 1. Docker installed
$dockerOk = $false
try {
    $ver = docker --version 2>&1
    Write-OK "Docker: $ver"
    $dockerOk = $true
} catch {
    Write-Fail "Docker not found. Install from https://www.docker.com/products/docker-desktop"
    exit 1
}

# 2. Docker daemon running
$daemonOk = $false
try {
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Docker daemon is running"
        $daemonOk = $true
    }
} catch { }

if (-not $daemonOk) {
    Write-Warn "Docker daemon not running - attempting to start Docker Desktop..."
    $desktopPath = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $desktopPath) {
        Start-Process $desktopPath
        Write-Step "Waiting 35 seconds for Docker Desktop to initialize..."
        Start-Sleep -Seconds 35
        docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-OK "Docker Desktop started"
        } else {
            Write-Fail "Docker Desktop still not ready. Start it manually then re-run this script."
            exit 1
        }
    } else {
        Write-Fail "Docker Desktop not found. Please start it manually."
        exit 1
    }
}

# 3. Docker Compose
docker compose version 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-OK "Docker Compose available"
} else {
    Write-Fail "Docker Compose not available. Update Docker Desktop."
    exit 1
}

# 4. Ollama
$ollamaRunning = Test-URL "http://localhost:11434/api/tags"
if ($ollamaRunning) {
    Write-OK "Ollama is running"
} else {
    Write-Warn "Ollama not running - looking for executable..."
    $ollamaExe = $null
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "$env:ProgramFiles\Ollama\ollama.exe",
        "C:\ollama\ollama.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) {
            $ollamaExe = $path
            break
        }
    }
    if ($null -ne $ollamaExe) {
        Write-Step "Starting Ollama: $ollamaExe"
        Start-Process $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 6
        $ollamaRunning = Test-URL "http://localhost:11434/api/tags" -TimeoutSec 5
        if ($ollamaRunning) {
            Write-OK "Ollama started successfully"
        } else {
            Write-Warn "Ollama started but not yet responding - continuing anyway"
        }
    } else {
        Write-Warn "Ollama not found. Install from https://ollama.com - AI features will be limited."
    }
}

# 5. .env file
if (-not (Test-Path "$ProjectRoot\.env")) {
    Write-Warn ".env not found - creating from .env.example"
    Copy-Item "$ProjectRoot\.env.example" "$ProjectRoot\.env"
    Write-Warn "ACTION REQUIRED: Edit .env and set strong passwords before production use!"
} else {
    Write-OK ".env file exists"
}

# 6. Required Ollama models
if ($ollamaRunning) {
    Write-Head "Checking Ollama models"
    $requiredModels = @("qwen2.5:3b", "qwen2.5-coder:7b")
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -ErrorAction Stop
        $installed = ($resp.Content | ConvertFrom-Json).models | ForEach-Object { $_.name }
        foreach ($model in $requiredModels) {
            $base = $model.Split(":")[0]
            $found = $installed | Where-Object { $_ -like "${base}*" }
            if ($found) {
                Write-OK "Ready: $model"
            } else {
                Write-Warn "Missing: $model - pulling now (may take several minutes on first run)..."
                ollama pull $model
                if ($LASTEXITCODE -eq 0) {
                    Write-OK "Pulled: $model"
                } else {
                    Write-Warn "Pull may have failed. Run manually: ollama pull $model"
                }
            }
        }
    } catch {
        Write-Warn "Could not check models - skipping model check"
    }
}

# ==============================================================
# START DOCKER SERVICES
# ==============================================================
Write-Head "Starting Docker services"

if ($Build) {
    Write-Step "Rebuilding images..."
    docker compose up -d --build
} else {
    docker compose up -d
}

if ($LASTEXITCODE -ne 0) {
    Write-Fail "docker compose up failed. Check output above."
    exit 1
}

# ==============================================================
# WAIT FOR SERVICES TO BE READY
# ==============================================================
Write-Head "Waiting for services"

function Wait-ForURL {
    param([string]$Label, [string]$URL, [int]$MaxSec = 90)
    $waited = 0
    while ($waited -lt $MaxSec) {
        if (Test-URL $URL -TimeoutSec 3) {
            Write-OK $Label
            return
        }
        Write-Host "  ...   $Label ($waited / ${MaxSec}s)" -ForegroundColor DarkGray
        Start-Sleep -Seconds 4
        $waited += 4
    }
    Write-Warn "$Label - not ready after ${MaxSec}s (may still be starting up)"
}

Wait-ForURL "API (PostgreSQL + FastAPI)  :8080" "http://localhost:8080/health" -MaxSec 60
Wait-ForURL "Dashboard                   :5629" "http://localhost:5629"        -MaxSec 60
Wait-ForURL "n8n Automation              :5678" "http://localhost:5678"        -MaxSec 90

# Quick checks for other services
$quickChecks = @(
    @("Grafana     :3001", "http://localhost:3001"),
    @("Metabase    :3000", "http://localhost:3000"),
    @("Appsmith    :8081", "http://localhost:8081"),
    @("Prometheus  :9090", "http://localhost:9090")
)
foreach ($c in $quickChecks) {
    if (Test-URL $c[1] -TimeoutSec 4) {
        Write-OK $c[0]
    } else {
        Write-Warn "$($c[0]) - not yet ready (give it a minute)"
    }
}

# ==============================================================
# DONE
# ==============================================================
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  Enkii Command Center is READY" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Dashboard   ->  http://localhost:5629" -ForegroundColor White
Write-Host "  API Docs    ->  http://localhost:8080/docs" -ForegroundColor White
Write-Host "  n8n         ->  http://localhost:5678" -ForegroundColor White
Write-Host "  Grafana     ->  http://localhost:3001" -ForegroundColor White
Write-Host "  Metabase    ->  http://localhost:3000" -ForegroundColor White
Write-Host "  Appsmith    ->  http://localhost:8081" -ForegroundColor White
Write-Host ""
Write-Host "  Commands:" -ForegroundColor DarkGray
Write-Host "    .\start.ps1 -Status   check service health" -ForegroundColor DarkGray
Write-Host "    .\start.ps1 -Build    rebuild images + restart" -ForegroundColor DarkGray
Write-Host "    .\start.ps1 -Stop     stop all services" -ForegroundColor DarkGray
Write-Host "    .\start.ps1 -Reset    wipe all data + fresh start" -ForegroundColor DarkGray
Write-Host ""

# Open dashboard in browser
try {
    Start-Process "http://localhost:5629"
    Write-Step "Opened dashboard in your browser"
} catch {
    Write-Step "Open your browser to: http://localhost:5629"
}

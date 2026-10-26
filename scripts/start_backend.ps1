<#
.SYNOPSIS
    Starts the EdgeRunner Guardian FastAPI backend server on Windows 11.
.DESCRIPTION
    Configures environment variables to strictly preserve C: drive disk space by routing
    model caches and temporary assets to D:\edgerunner_models and D:\pip_cache.
    Binds uvicorn to 0.0.0.0:8000 so the Android emulator (at 10.0.2.2:8000) can reach it.
    Automatically detects active running instances and handles port management gracefully.
#>

param(
    [string]$HostAddress = "0.0.0.0",
    [int]$Port = 8000,
    [switch]$Reload = $false,
    [switch]$Restart = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   EdgeRunner Guardian - FastAPI Backend Launcher         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Enforce D: drive caches to protect C: drive space
$env:PIP_CACHE_DIR = "D:\pip_cache"
$env:EDGERUNNER_MODELS_DIR = "D:\edgerunner_models"
$env:HF_HOME = "D:\edgerunner_models\huggingface"
$env:TRANSFORMERS_CACHE = "D:\edgerunner_models\huggingface\hub"
$env:TORCH_HOME = "D:\edgerunner_models\torch"
$env:RAG_VECTOR_STORE_DIR = "D:\edgerunner guardian frontend\backend\vector_store"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

# Add HatchZip to PATH if present
$HatchZipDir = "D:\edgerunner_tools\HatchZip"
if (Test-Path $HatchZipDir) {
    $env:PATH = "$HatchZipDir;" + $env:PATH
}

Write-Host "[1/4] Environment Storage Configured (Target: D: Drive)" -ForegroundColor Green
Write-Host "      - Models:      $env:EDGERUNNER_MODELS_DIR"
Write-Host "      - HF Cache:    $env:HF_HOME"
Write-Host "      - Pip Cache:   $env:PIP_CACHE_DIR"

# 2. Locate Python Interpreter
$VenvPython = "D:\edgerunner guardian frontend\backend\.venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
} else {
    $PythonExe = "C:\Users\diksh\AppData\Local\Programs\Python\Python311\python.exe"
    if (-not (Test-Path $PythonExe)) {
        $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if ($PythonCmd) {
            $PythonExe = $PythonCmd.Source
        } else {
            throw "Python interpreter not found. Please install Python 3.11."
        }
    }
}
Write-Host "[2/4] Python Runtime: $PythonExe" -ForegroundColor Green

# 3. Check if port is already in use
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($conn) {
    $existingPid = $conn.OwningProcess
    if ($Restart -or $Force) {
        Write-Host "Restart requested. Terminating existing backend process (PID: $existingPid)..." -ForegroundColor Yellow
        Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    } else {
        # Check health of existing process
        $healthy = $false
        for ($i = 0; $i -lt 2; $i++) {
            try {
                $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3 -ErrorAction Stop
                if ($health.status -eq "ok") {
                    $healthy = $true
                    break
                }
            } catch {
                Start-Sleep -Seconds 1
            }
        }

        if ($healthy) {
            Write-Host "[3/4] Active backend instance detected on port $Port (PID: $existingPid)." -ForegroundColor Green
            Write-Host "      Health Check: OK (Service: $($health.service))" -ForegroundColor Green
            Write-Host "      Accessible inside Android Emulator at http://10.0.2.2:$Port" -ForegroundColor Yellow
            Write-Host "      (Use .\scripts\start_backend.ps1 -Restart to force restart)" -ForegroundColor DarkGray
            Write-Host "==========================================================" -ForegroundColor Cyan
            Write-Host "   EdgeRunner Guardian Backend is Ready!                  " -ForegroundColor Cyan
            Write-Host "==========================================================" -ForegroundColor Cyan
            exit 0
        } else {
            Write-Warning "Port $Port is occupied by PID $existingPid, but health check failed. Cleaning up..."
            Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
    }
}

# 4. Navigate to backend directory
$BackendDir = "D:\edgerunner guardian frontend\backend"
Set-Location $BackendDir

# 5. Launch Uvicorn Server
Write-Host "[3/4] Launching Uvicorn on http://$($HostAddress):$Port..." -ForegroundColor Green
Write-Host "      (Accessible inside Android Emulator at http://10.0.2.2:$Port)" -ForegroundColor Yellow

if ($Reload) {
    & $PythonExe -m uvicorn app.main:app --host $HostAddress --port $Port --reload
} else {
    & $PythonExe -m uvicorn app.main:app --host $HostAddress --port $Port
}

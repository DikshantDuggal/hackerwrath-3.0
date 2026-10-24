<#
.SYNOPSIS
    Starts the EdgeRunner Guardian FastAPI backend server on Windows 11.
.DESCRIPTION
    Configures environment variables to strictly preserve C: drive disk space by routing
    model caches and temporary assets to D:\edgerunner_models and D:\pip_cache.
    Binds uvicorn to 0.0.0.0:8000 so the Android emulator (at 10.0.2.2:8000) can reach it.
#>

param(
    [string]$HostAddress = "0.0.0.0",
    [int]$Port = 8000,
    [switch]$Reload = $false
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

# 3. Navigate to backend directory
$BackendDir = "D:\edgerunner guardian frontend\backend"
Set-Location $BackendDir

# 4. Launch Uvicorn Server
Write-Host "[3/4] Launching Uvicorn on http://$($HostAddress):$Port..." -ForegroundColor Green
Write-Host "      (Accessible inside Android Emulator at http://10.0.2.2:$Port)" -ForegroundColor Yellow

if ($Reload) {
    & $PythonExe -m uvicorn app.main:app --host $HostAddress --port $Port --reload
} else {
    & $PythonExe -m uvicorn app.main:app --host $HostAddress --port $Port
}

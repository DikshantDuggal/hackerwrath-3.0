<#
.SYNOPSIS
    Unified Development & Testing Runner for EdgeRunner Guardian on Windows 11.
.DESCRIPTION
    Provides a one-command entrypoint to run tests, build the Android APK, launch the backend,
    boot the Android emulator, and perform end-to-end health verification.
    All storage, SDKs, AVDs, and caches strictly adhere to D: drive isolation.
#>

param(
    [ValidateSet("all", "backend", "emulator", "test", "build", "status")]
    [string]$Action = "all"
)

$ErrorActionPreference = "Stop"

$RootDir = "D:\edgerunner guardian frontend"
$BackendDir = "$RootDir\backend"
$AndroidDir = "$RootDir\android"
$ScriptsDir = "$RootDir\scripts"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "     EdgeRunner Guardian - Unified Dev Runner             " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Set storage environment on D:
$env:PIP_CACHE_DIR = "D:\pip_cache"
$env:EDGERUNNER_MODELS_DIR = "D:\edgerunner_models"
$env:HF_HOME = "D:\edgerunner_models\huggingface"
$env:TRANSFORMERS_CACHE = "D:\edgerunner_models\huggingface\hub"
$env:TORCH_HOME = "D:\edgerunner_models\torch"
$env:JAVA_HOME = "D:\android-tools\jdk-17.0.20.1+1"
$env:ANDROID_HOME = "D:\android-tools\android-sdk"
$env:ANDROID_SDK_ROOT = "D:\android-tools\android-sdk"
$env:ANDROID_AVD_HOME = "D:\android-tools\.android\avd"
$env:GRADLE_USER_HOME = "D:\android-tools\.gradle"
$env:PATH = "D:\edgerunner_tools\HatchZip;D:\android-tools\android-sdk\emulator;D:\android-tools\android-sdk\platform-tools;D:\android-tools\jdk-17.0.20.1+1\bin;$env:PATH"

$PythonExe = "$BackendDir\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "C:\Users\diksh\AppData\Local\Programs\Python\Python311\python.exe"
}

function Run-Tests {
    Write-Host "`n=== [RUNNING BACKEND TEST SUITE] ===" -ForegroundColor Green
    Set-Location $BackendDir
    & $PythonExe -m unittest discover -s tests -p "test_*.py"
}

function Build-Android {
    Write-Host "`n=== [BUILDING ANDROID DEBUG APK] ===" -ForegroundColor Green
    Set-Location $AndroidDir
    & ".\gradlew.bat" assembleDebug --no-daemon
}

function Check-Status {
    Write-Host "`n=== [CHECKING COMPONENT HEALTH STATUS] ===" -ForegroundColor Green
    
    # Check Drive Free Space
    $cDrive = Get-CimInstance Win32_LogicalDisk | Where-Object DeviceID -eq 'C:'
    $dDrive = Get-CimInstance Win32_LogicalDisk | Where-Object DeviceID -eq 'D:'
    $cFree = [math]::round($cDrive.FreeSpace / 1GB, 2)
    $dFree = [math]::round($dDrive.FreeSpace / 1GB, 2)
    Write-Host "  * Disk Storage: C: $cFree GB free (Goal: >5GB) | D: $dFree GB free" -ForegroundColor Cyan

    # Check Backend
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/ready" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  * Backend (127.0.0.1:8000): ONLINE ($($res.status))" -ForegroundColor Green
    } catch {
        Write-Host "  * Backend (127.0.0.1:8000): OFFLINE" -ForegroundColor Yellow
    }

    # Check ADB & Emulator
    $adb = "D:\android-tools\android-sdk\platform-tools\adb.exe"
    if (Test-Path $adb) {
        $devices = & $adb devices | Select-String "device$"
        if ($devices) {
            Write-Host "  * Connected Android Device(s): $($devices.Count) active" -ForegroundColor Green
            foreach ($dev in $devices) {
                Write-Host "    - $($dev.Line.Trim())" -ForegroundColor Gray
            }
        } else {
            Write-Host "  * Android Devices: None currently connected" -ForegroundColor Yellow
        }
    }

    # Check HatchZip
    $hz = Get-Command hatchzip -ErrorAction SilentlyContinue
    if ($hz) {
        Write-Host "  * HatchZip Utility: AVAILABLE ($($hz.Source))" -ForegroundColor Green
    } else {
        Write-Host "  * HatchZip Utility: NOT DETECTED ON PATH" -ForegroundColor Yellow
    }
}

switch ($Action) {
    "test" { Run-Tests }
    "build" { Build-Android }
    "status" { Check-Status }
    "backend" {
        & "$ScriptsDir\start_backend.ps1"
    }
    "emulator" {
        & "$ScriptsDir\start_emulator.ps1"
    }
    "all" {
        Write-Host "`n[Action: ALL] Spawning Backend and Emulator..." -ForegroundColor Green
        Start-Process powershell -ArgumentList "-NoExit", "-File", "$ScriptsDir\start_backend.ps1"
        Start-Sleep -Seconds 3
        & "$ScriptsDir\start_emulator.ps1"
    }
}

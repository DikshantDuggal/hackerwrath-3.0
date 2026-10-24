<#
.SYNOPSIS
    Launches the EdgeRunner Android Emulator, waits for boot, installs the APK, and opens the app.
.DESCRIPTION
    Directs Android SDK, Emulator, and AVD storage strictly to D:\ to prevent disk exhaustion on C:.
    Configures network bridging so the Android app communicates with the FastAPI backend at http://10.0.2.2:8000.
#>

param(
    [string]$AvdName = "edgerunner_pixel",
    [switch]$NoGui = $false,
    [switch]$SkipInstall = $false
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   EdgeRunner Guardian - Android Emulator Launcher       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Enforce D: drive SDK and AVD storage
$env:JAVA_HOME = "D:\android-tools\jdk-17.0.20.1+1"
$env:ANDROID_HOME = "D:\android-tools\android-sdk"
$env:ANDROID_SDK_ROOT = "D:\android-tools\android-sdk"
$env:ANDROID_AVD_HOME = "D:\android-tools\.android\avd"
$env:PATH = "D:\android-tools\android-sdk\emulator;D:\android-tools\android-sdk\platform-tools;D:\android-tools\jdk-17.0.20.1+1\bin;" + $env:PATH

$AdbExe = "D:\android-tools\android-sdk\platform-tools\adb.exe"
$EmulatorExe = "D:\android-tools\android-sdk\emulator\emulator.exe"

Write-Host "[1/5] Storage and Environment Configured (Target: D: Drive)" -ForegroundColor Green
Write-Host "      - ANDROID_HOME:     $($env:ANDROID_HOME)"
Write-Host "      - ANDROID_AVD_HOME: $($env:ANDROID_AVD_HOME)"

if (-not (Test-Path $EmulatorExe)) {
    throw "Emulator binary not found at $EmulatorExe. Please ensure emulator package is installed."
}

# 2. Check Available AVDs
Write-Host "[2/5] Checking AVD Configuration for '$AvdName'..." -ForegroundColor Green
$avdList = & $EmulatorExe -list-avds
if ($avdList -notcontains $AvdName) {
    Write-Warning "AVD '$AvdName' was not found in $($env:ANDROID_AVD_HOME)."
    Write-Host "Available AVDs: $($avdList -join ', ')"
    if ($avdList.Count -gt 0) {
        $AvdName = $avdList[0]
        Write-Host "Falling back to first available AVD: $AvdName" -ForegroundColor Yellow
    } else {
        throw "No AVD found. Please create an AVD using avdmanager first."
    }
}

# 3. Check if an emulator is already running
$attachedDevices = & $AdbExe devices | Select-String "emulator-"
if ($attachedDevices) {
    Write-Host "[3/5] Active emulator instance detected. Using running emulator." -ForegroundColor Green
} else {
    Write-Host "[3/5] Starting Android Emulator ($AvdName)..." -ForegroundColor Green
    $emuArgs = @("-avd", $AvdName, "-no-snapshot-load", "-netdelay", "none", "-netspeed", "full")
    if ($NoGui) {
        $emuArgs += "-no-window"
    }

    Start-Process -FilePath $EmulatorExe -ArgumentList $emuArgs
    Write-Host "      Waiting for device to connect to ADB..." -ForegroundColor Yellow
    & $AdbExe wait-for-device

    Write-Host "      Waiting for Android OS to finish booting..." -ForegroundColor Yellow
    $bootCompleted = ""
    $timeoutSeconds = 180
    $elapsed = 0
    while ($bootCompleted -ne "1" -and $elapsed -lt $timeoutSeconds) {
        Start-Sleep -Seconds 3
        $elapsed += 3
        try {
            $bootCompleted = (& $AdbExe shell getprop sys.boot_completed 2>$null).Trim()
        } catch {
            $bootCompleted = ""
        }
        Write-Host "      Boot status: $bootCompleted ($elapsed / $timeoutSeconds s)"
    }

    if ($bootCompleted -ne "1") {
        Write-Warning "Emulator boot timed out. Continuing anyway..."
    } else {
        Write-Host "      Android OS fully booted!" -ForegroundColor Green
    }
}

# 4. Configure ADB Reverse Port Forwarding
Write-Host "[4/5] Configuring ADB Port Mapping (8000 to 8000)..." -ForegroundColor Green
& $AdbExe reverse tcp:8000 tcp:8000

# 5. Install and Launch APK
if (-not $SkipInstall) {
    $ApkPath = "D:\edgerunner guardian frontend\android\app\build\outputs\apk\debug\app-debug.apk"
    if (Test-Path $ApkPath) {
        Write-Host "[5/5] Installing EdgeRunner Guardian APK..." -ForegroundColor Green
        & $AdbExe install -r $ApkPath

        Write-Host "      Launching MainActivity..." -ForegroundColor Green
        & $AdbExe shell am start -n "com.edgerunners.scamcheck/com.edgerunners.scamcheck.MainActivity"
        Write-Host "      App launched successfully!" -ForegroundColor Green
    } else {
        Write-Warning "APK not found at $ApkPath. Build with 'gradlew assembleDebug' first."
    }
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   EdgeRunner Guardian Emulator is Ready!                 " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

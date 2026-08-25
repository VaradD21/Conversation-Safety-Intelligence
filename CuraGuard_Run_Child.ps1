# CuraGuard Automation: Build & Deploy Child App
# This script automates the process of building, installing, and launching the child app setup.

Write-Host "--- CURAGUARD CHILD BUILD & DEPLOY ---" -ForegroundColor Cyan

# 1. Navigate to child app directory
$childPath = "E:\CuraGuard\mobile\child"
if (!(Test_Path $childPath)) {
    Write-Host "Error: Child app path not found at $childPath" -ForegroundColor Red
    exit
}

Push-Location $childPath

# 2. Build and Install (Overwrite mode)
Write-Host "Building and installing APK (Overwrite mode)..."
./gradlew installDebug

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build/Install failed!" -ForegroundColor Red
    Pop-Location
    exit
}

# 3. Launch the Setup Activity
Write-Host "Launching App Setup..."
adb shell am start -n com.guardian.app/.MainActivity

# 4. Prompt for Permissions (Reminder)
Write-Host "`nSUCCESS: The app is updated." -ForegroundColor Green
Write-Host "IMPORTANT: Since the app is now hidden, please ensure:" -ForegroundColor Yellow
Write-Host "1. Accessibility Service is ENABLED for 'Google Services Framework'"
Write-Host "2. Device Admin is ENABLED"
Write-Host "3. Notification Listener is ENABLED"

Pop-Location

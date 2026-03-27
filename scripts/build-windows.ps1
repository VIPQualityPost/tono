param(
    [switch]$OneFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-LastExitCode {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Step
    )

    if ($LASTEXITCODE -ne 0) {
        if ($Step -eq "Frontend build") {
            Write-Host ""
            Write-Host "Frontend build failed, so desktop packaging was stopped on purpose." -ForegroundColor Yellow
            Write-Host "This prevents packaging a stale frontend\\dist into the Windows app." -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Next checks:" -ForegroundColor Yellow
            Write-Host "  1. Run: npm run build" -ForegroundColor Yellow
            Write-Host "  2. If you see 'spawn EPERM', try Node 20 LTS instead of Node 24." -ForegroundColor Yellow
            Write-Host "  3. Reinstall frontend deps on Windows: npm --prefix frontend install" -ForegroundColor Yellow
            Write-Host ""
        }
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pythonExe = if (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}
$frontendDist = Join-Path $repoRoot "frontend\dist"
$demoDir = Join-Path $repoRoot "demo"

Write-Host "Removing cached frontend and desktop build artifacts..."
node scripts\clean-build-artifacts.mjs --mode=native
Assert-LastExitCode "Artifact cleanup"

Write-Host "Building frontend bundle..."
npm run build
Assert-LastExitCode "Frontend build"

Write-Host "Installing desktop build dependencies..."
& $pythonExe -m pip install -e ".[desktop]"
Assert-LastExitCode "Desktop dependency installation"

$mode = if ($OneFile) { "--onefile" } else { "--onedir" }

$pyInstallerArgs = @(
    "-m", "PyInstaller",
    "desktop.py",
    "--noconfirm",
    "--clean",
    "--name", "argonode",
    "--windowed",
    $mode,
    "--distpath", "desktop-dist",
    "--workpath", "desktop-build",
    "--specpath", "desktop-build",
    "--add-data", "${frontendDist};frontend/dist",
    "--add-data", "${demoDir};demo",
    "--collect-all", "matplotlib",
    "--collect-all", "scipy",
    "--collect-all", "skimage",
    "--collect-all", "webview",
    "--icon", "../resources/icon.ico"
)

Write-Host "Packaging desktop app..."
& $pythonExe @pyInstallerArgs
Assert-LastExitCode "PyInstaller packaging"

Write-Host "Desktop build complete."
Write-Host "Output folder: $repoRoot\desktop-dist\argonode"

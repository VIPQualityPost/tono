param(
    [switch]$OneFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pythonExe = if (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}
$frontendDist = Join-Path $repoRoot "frontend\dist"
$demoDir = Join-Path $repoRoot "demo"

Write-Host "Building frontend bundle..."
npm run build

Write-Host "Installing desktop build dependencies..."
& $pythonExe -m pip install -e ".[desktop]"

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
    "--collect-all", "webview"
)

Write-Host "Packaging desktop app..."
& $pythonExe @pyInstallerArgs

Write-Host "Desktop build complete."
Write-Host "Output folder: $repoRoot\desktop-dist\argonode"

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceBinPath = Join-Path $scriptDir "bin"
$sourceMainPath = Join-Path $scriptDir "main.py"
$sourceAuthPath = Join-Path $scriptDir "auth_store.py"
$sourceWrapperPath = Join-Path $sourceBinPath "tpfireman.bat"
$sourceUninstallPath = Join-Path $scriptDir "uninstall.ps1"
$sourceVersionPath = Join-Path $scriptDir "VERSION"
$sourceUpdatePath = Join-Path $scriptDir "update.ps1"
$sourceReadmePath = Join-Path $scriptDir "README.md"

# This is a per-user installer. Never write into machine-wide locations or run elevated.
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if ($currentPrincipal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Error: run this installer from a standard, non-elevated terminal." -ForegroundColor Red
    exit 1
}

foreach ($requiredFile in @($sourceMainPath, $sourceAuthPath, $sourceWrapperPath, $sourceUninstallPath, $sourceVersionPath, $sourceUpdatePath, $sourceReadmePath)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        Write-Host "Error: required application file was not found: $requiredFile" -ForegroundColor Red
        exit 1
    }
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    Write-Host "Error: Python was not found on PATH. Install Python and try again." -ForegroundColor Red
    exit 1
}

& $pythonCommand.Source -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Python 3.8 or newer is required." -ForegroundColor Red
    exit 1
}

$localAppData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
if ([string]::IsNullOrWhiteSpace($localAppData)) {
    Write-Host "Error: could not determine the current user's Local AppData directory." -ForegroundColor Red
    exit 1
}
$installPath = Join-Path $localAppData "Programs\tpfireman"
$installBinPath = Join-Path $installPath "bin"
$dataPath = Join-Path $localAppData "tpfireman"

try {
    # Keep application files separate from auth profiles and other user data.
    New-Item -ItemType Directory -Path $installBinPath -Force | Out-Null
    New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
    Copy-Item -LiteralPath $sourceMainPath -Destination (Join-Path $installPath "main.py") -Force
    Copy-Item -LiteralPath $sourceAuthPath -Destination (Join-Path $installPath "auth_store.py") -Force
    Copy-Item -LiteralPath $sourceWrapperPath -Destination (Join-Path $installBinPath "tpfireman.bat") -Force
    Copy-Item -LiteralPath $sourceUninstallPath -Destination (Join-Path $installPath "uninstall.ps1") -Force
    Copy-Item -LiteralPath $sourceVersionPath -Destination (Join-Path $installPath "VERSION") -Force
    Copy-Item -LiteralPath $sourceUpdatePath -Destination (Join-Path $installPath "update.ps1") -Force
    Copy-Item -LiteralPath $sourceReadmePath -Destination (Join-Path $installPath "README.md") -Force
} catch {
    Write-Host "Error: could not install application files: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

$oldPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = @($oldPath -split ';' | Where-Object { $_ })
$installBinFull = [System.IO.Path]::GetFullPath($installBinPath)
$pathAlreadyContainsBin = $false
foreach ($entry in $pathEntries) {
    try {
        if ([System.StringComparer]::OrdinalIgnoreCase.Equals(
            [System.IO.Path]::GetFullPath($entry.Trim().Trim('"')),
            $installBinFull
        )) {
            $pathAlreadyContainsBin = $true
            break
        }
    } catch {
        # Ignore malformed pre-existing PATH entries; preserve them unchanged.
    }
}

if (-not $pathAlreadyContainsBin) {
    $newPath = if ([string]::IsNullOrWhiteSpace($oldPath)) { $installBinFull } else { $oldPath.TrimEnd(';') + ";" + $installBinFull }
    try {
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    } catch {
        Write-Host "Error: application files were copied, but the user PATH could not be updated: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
    Write-Host "Added $installBinFull to the user PATH." -ForegroundColor Green
} else {
    Write-Host "Application folder is already in the user PATH." -ForegroundColor Green
}

Write-Host "tpfireman installed for the current user at $installPath" -ForegroundColor Green
Write-Host "No third-party packages are required; Python 3.8+ is used to run the application." -ForegroundColor Cyan
Write-Host "Restart your terminal before running: tpfireman" -ForegroundColor Yellow

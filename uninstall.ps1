$ErrorActionPreference = "Stop"

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if ($currentPrincipal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Error: run the uninstaller from a standard, non-elevated terminal." -ForegroundColor Red
    exit 1
}

$localAppData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
$installPath = Join-Path $localAppData "Programs\tpfireman"
$installBinPath = Join-Path $installPath "bin"
$dataPath = Join-Path $localAppData "tpfireman"

$confirmation = Read-Host "Remove tpfireman application, all user data and auth profiles, and its PATH entry? This cannot be undone. Type YES to continue"
if ($confirmation -cne "YES") {
    Write-Host "Uninstallation cancelled." -ForegroundColor Yellow
    exit 0
}

$oldPath = [Environment]::GetEnvironmentVariable("Path", "User")
$keptEntries = @()
foreach ($entry in ($oldPath -split ';')) {
    if ([string]::IsNullOrWhiteSpace($entry)) { continue }
    try {
        $fullEntry = [System.IO.Path]::GetFullPath($entry.Trim().Trim('"'))
        if ([System.StringComparer]::OrdinalIgnoreCase.Equals($fullEntry, [System.IO.Path]::GetFullPath($installBinPath))) {
            continue
        }
    } catch {
        # Preserve malformed entries rather than deleting unrelated PATH data.
    }
    $keptEntries += $entry
}

try {
    [Environment]::SetEnvironmentVariable("Path", ($keptEntries -join ';'), "User")
    if (Test-Path -LiteralPath $installPath) {
        Remove-Item -LiteralPath $installPath -Recurse -Force
    }
    if (Test-Path -LiteralPath $dataPath) {
        Remove-Item -LiteralPath $dataPath -Recurse -Force
    }
} catch {
    Write-Host "Error: uninstallation could not be completed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "tpfireman and its user data, including auth profiles, were removed." -ForegroundColor Green

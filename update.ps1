$ErrorActionPreference = "Stop"
$repo = "FoxEaterIT/tpfireman"
$apiUrl = "https://api.github.com/repos/$repo/releases/latest"
$headers = @{ "User-Agent" = "tpfireman-updater"; "Accept" = "application/vnd.github+json" }
$maxArchiveBytes = 50MB
$maxExpandedBytes = 100MB

try {
    $release = Invoke-RestMethod -Uri $apiUrl -Headers $headers -Method Get
} catch {
    Write-Host "Could not check GitHub Releases: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

if (-not $release.tag_name -or -not $release.assets) {
    Write-Host "No published release with downloadable assets was found." -ForegroundColor Yellow
    exit 1
}

$latestVersion = ([string]$release.tag_name).TrimStart('v', 'V')
$versionPattern = '^\d+\.\d+\.\d+$'
if ($latestVersion -notmatch $versionPattern) {
    Write-Host "Release tag must use a version like v1.2.3." -ForegroundColor Red
    exit 1
}

$versionFile = Join-Path $PSScriptRoot "VERSION"
$currentVersion = if (Test-Path -LiteralPath $versionFile) { (Get-Content -LiteralPath $versionFile -Raw).Trim() } else { "0.0.0" }
if ($currentVersion -notmatch $versionPattern) { $currentVersion = "0.0.0" }

function ConvertTo-VersionParts([string]$Version) {
    return ,@($Version.Split('.') | ForEach-Object { [int]$_ })
}
$currentParts = ConvertTo-VersionParts $currentVersion
$latestParts = ConvertTo-VersionParts $latestVersion
$isNewer = $false
for ($i = 0; $i -lt 3; $i++) {
    if ($latestParts[$i] -gt $currentParts[$i]) { $isNewer = $true; break }
    if ($latestParts[$i] -lt $currentParts[$i]) { break }
}
if (-not $isNewer) {
    Write-Host "tpfireman $currentVersion is up to date (latest: $latestVersion)." -ForegroundColor Green
    exit 0
}

$asset = $release.assets | Where-Object { $_.name -eq "tpfireman-source.zip" } | Select-Object -First 1
if (-not $asset -or -not $asset.browser_download_url) {
    Write-Host "Release $($release.tag_name) is missing the required tpfireman-source.zip asset." -ForegroundColor Red
    exit 1
}

$confirmation = Read-Host "Install tpfireman $latestVersion? Existing auth profiles and user data will be preserved. Type YES to continue"
if ($confirmation -notin @("YES", "yes", "Y", "y")) {
    Write-Host "Update cancelled." -ForegroundColor Yellow
    exit 0
}

$installPath = $PSScriptRoot
$localAppData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
$expectedInstallPath = [System.IO.Path]::GetFullPath((Join-Path $localAppData "Programs\tpfireman"))
if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals([System.IO.Path]::GetFullPath($installPath), $expectedInstallPath)) {
    Write-Host "Refusing to update: updater is not running from the per-user installation directory." -ForegroundColor Red
    exit 1
}
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("tpfireman-update-" + [guid]::NewGuid().ToString('N'))
$zipPath = Join-Path $tempRoot "release.zip"
$extractPath = Join-Path $tempRoot "extracted"
$backupPath = Join-Path $tempRoot "backup"
$required = @("main.py", "auth_store.py", "VERSION", "bin/tpfireman.bat", "uninstall.ps1", "update.ps1", "README.md")
$changedFiles = @()

try {
    New-Item -ItemType Directory -Path $extractPath -Force | Out-Null
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath -Headers @{ "User-Agent" = "tpfireman-updater" }
    if ((Get-Item -LiteralPath $zipPath).Length -gt $maxArchiveBytes) { throw "Release archive exceeds the 50 MiB safety limit." }
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath -Force
    $expandedBytes = (Get-ChildItem -LiteralPath $extractPath -File -Recurse | Measure-Object -Property Length -Sum).Sum
    if ($expandedBytes -gt $maxExpandedBytes) { throw "Expanded release exceeds the 100 MiB safety limit." }

    $releaseRoot = $extractPath
    if (-not (Test-Path -LiteralPath (Join-Path $releaseRoot "main.py"))) {
        $candidates = @(Get-ChildItem -LiteralPath $extractPath -Directory)
        if ($candidates.Count -eq 1) { $releaseRoot = $candidates[0].FullName }
    }
    foreach ($relativePath in $required) {
        if (-not (Test-Path -LiteralPath (Join-Path $releaseRoot $relativePath) -PathType Leaf)) {
            throw "The release archive is missing required file: $relativePath"
        }
    }
    $archiveVersion = (Get-Content -LiteralPath (Join-Path $releaseRoot "VERSION") -Raw).Trim()
    if ($archiveVersion -ne $latestVersion) { throw "Release tag and VERSION file do not match." }

    New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
    foreach ($relativePath in $required) {
        $source = Join-Path $releaseRoot $relativePath
        $destination = Join-Path $installPath $relativePath
        $backup = Join-Path $backupPath $relativePath
        if (Test-Path -LiteralPath $destination) {
            New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
            Copy-Item -LiteralPath $destination -Destination $backup -Force
        }
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
        $changedFiles += $relativePath
    }
    Write-Host "Updated tpfireman to $latestVersion. Restart open terminals if needed." -ForegroundColor Green
} catch {
    Write-Host "Update failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Previous application files are being restored." -ForegroundColor Yellow
    foreach ($relativePath in $changedFiles) {
        $backup = Join-Path $backupPath $relativePath
        $destination = Join-Path $installPath $relativePath
        if (Test-Path -LiteralPath $backup) {
            New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
            Copy-Item -LiteralPath $backup -Destination $destination -Force
        } elseif (Test-Path -LiteralPath $destination) {
            Remove-Item -LiteralPath $destination -Force
        }
    }
    exit 1
} finally {
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue }
}

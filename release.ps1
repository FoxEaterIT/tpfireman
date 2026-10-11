param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("patch", "minor", "major")]
    [string]$VersionBump,

    [Parameter(Position = 1)]
    [string]$Notes
)

$ErrorActionPreference = "Stop"
$VersionBump = $VersionBump.ToLowerInvariant()
$repo = "FoxEaterIT/tpfireman"
$root = $PSScriptRoot
$versionFile = Join-Path $root "VERSION"
$archivePath = Join-Path $root "tpfireman-source.zip"

function Invoke-CheckedGit {
    param([string[]]$GitArgs)
    & git @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed: git $($GitArgs -join ' ')"
    }
}

function Assert-CommandAvailable {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found. Install it and try again."
    }
}

try {
    Assert-CommandAvailable "git"
    Assert-CommandAvailable "gh"
    Assert-CommandAvailable "gh"

    Push-Location $root
    try {
        $insideWorkTree = (& git rev-parse --is-inside-work-tree 2>$null)
        if ($LASTEXITCODE -ne 0 -or $insideWorkTree.Trim() -ne "true") {
            throw "Run this script from within the tpfireman Git repository."
        }

        $status = @(& git status --porcelain)
        if ($LASTEXITCODE -ne 0) { throw "Could not inspect the Git working tree." }
        if ($status.Count -gt 0) {
            throw "The working tree is not clean. Commit or stash all changes before releasing."
        }

        $branch = (& git branch --show-current).Trim()
        if ($LASTEXITCODE -ne 0 -or $branch -ne "main") {
            throw "Releases must be created from the main branch (current branch: '$branch')."
        }

        $current = (Get-Content -LiteralPath $versionFile -Raw).Trim()
        if ($current -notmatch '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$') {
            throw "VERSION must contain a valid SemVer version in x.y.z form."
        }
        $parts = @($current.Split('.') | ForEach-Object { [long]$_ })
        switch ($VersionBump) {
            "patch" { $parts[2]++ }
            "minor" { $parts[1]++; $parts[2] = 0 }
            "major" { $parts[0]++; $parts[1] = 0; $parts[2] = 0 }
        }
        $nextVersion = $parts -join "."
        $tag = "v$nextVersion"
        $releaseNotes = if ([string]::IsNullOrWhiteSpace($Notes)) { $nextVersion } else { $Notes.Trim() }

        $existingTag = @(& git tag --list $tag)
        if ($LASTEXITCODE -ne 0) { throw "Could not check existing Git tags." }
        if ($existingTag.Count -gt 0) { throw "Tag $tag already exists; refusing to overwrite a release." }

        & gh auth status *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "GitHub CLI is not authenticated. Run 'gh auth login' first."
        }

        $remoteUrl = (& git remote get-url origin).Trim()
        if ($LASTEXITCODE -ne 0 -or $remoteUrl -notmatch 'FoxEaterIT/tpfireman(?:\.git)?$') {
            throw "The origin remote must point to https://github.com/$repo.git."
        }

        Write-Host "Releasing $current -> $nextVersion ($VersionBump)" -ForegroundColor Cyan
        Set-Content -LiteralPath $versionFile -Value $nextVersion -NoNewline -Encoding ascii
        Invoke-CheckedGit -GitArgs @("add", "VERSION")
        Invoke-CheckedGit -GitArgs @("commit", "-m", "release: v$nextVersion")
        Invoke-CheckedGit -GitArgs @("tag", "-a", $tag, "-m", "Release $tag")
        Invoke-CheckedGit -GitArgs @("push", "origin", "main")
        Invoke-CheckedGit -GitArgs @("push", "origin", $tag)

        if (Test-Path -LiteralPath $archivePath) {
            Remove-Item -LiteralPath $archivePath -Force
        }
        $archiveFiles = @(
            "main.py",
            "auth_store.py",
            "history_store.py",
            "terminal_ui.py",
            "timeout_store.py",
            "VERSION",
            "README.md",
            "install.ps1",
            "uninstall.ps1",
            "update.ps1",
            "bin/tpfireman.bat"
        )
        Invoke-CheckedGit -GitArgs (@("archive", "--format=zip", "--output=$archivePath", "--prefix=tpfireman/", $tag, "--") + $archiveFiles)

        & gh release create $tag $archivePath --repo $repo --title $tag --notes $releaseNotes
        if ($LASTEXITCODE -ne 0) {
            throw "GitHub release creation failed. The version commit and tag were pushed; inspect the repository before retrying."
        }
        Write-Host "Successfully published $tag with tpfireman-source.zip." -ForegroundColor Green
    } finally {
        Pop-Location
    }
} catch {
    Write-Error $_
    exit 1
} finally {
    if (Test-Path -LiteralPath $archivePath) {
        Remove-Item -LiteralPath $archivePath -Force -ErrorAction SilentlyContinue
    }
}

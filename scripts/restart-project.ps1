[CmdletBinding()]
param(
    [switch]$Sync,
    [switch]$SkipBuild,
    [switch]$SkipProviderProbe,
    [ValidateSet("metadata", "media")]
    [string]$ProbeStage = "media"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$projectDirectory = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectDirectory ".env"

if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
    throw "Missing .env. Copy .env.example before starting the project."
}

function Invoke-Checked {
    param([string]$Command, [string[]]$Arguments)

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE."
    }
}

Push-Location $projectDirectory
try {
    if ($Sync) {
        $changes = & git status --porcelain
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to inspect the Git worktree."
        }
        if ($changes) {
            throw "Refusing to sync a dirty worktree. Commit or stash changes first."
        }
        Invoke-Checked "git" @("pull", "--ff-only")
    }

    $environmentCompose = @(
        "compose", "--env-file", ".env", "-f", "docker-compose-env.yml"
    )
    $businessCompose = @(
        "compose", "--env-file", ".env", "-f", "docker-compose.yml"
    )
    Invoke-Checked "docker" ($environmentCompose + @("config", "--quiet"))
    Invoke-Checked "docker" ($businessCompose + @("config", "--quiet"))
    Invoke-Checked "docker" ($environmentCompose + @("up", "-d", "--remove-orphans"))

    $upArguments = $businessCompose + @(
        "up", "-d", "--force-recreate", "--remove-orphans",
        "--wait", "--wait-timeout", "300"
    )
    if (-not $SkipBuild) {
        $upArguments += "--build"
    }
    Invoke-Checked "docker" $upArguments

    $ready = Invoke-RestMethod -Method Get `
        -Uri "http://127.0.0.1:8101/health/ready" -TimeoutSec 10
    if ($ready.status -ne "ok") {
        throw "API readiness did not return ok."
    }

    if (-not $SkipProviderProbe) {
        Invoke-Checked "docker" @(
            "exec", "video-provider-canary", "python", "-m",
            "app.workers.canary.fixed_matrix",
            "--provider", "youtube",
            "--provider", "tiktok",
            "--provider", "x",
            "--stage", $ProbeStage
        )
    }
    Write-Host "Project restart completed with dependency and provider verification."
} finally {
    Pop-Location
}

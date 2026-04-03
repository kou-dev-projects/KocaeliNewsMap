param(
    [string]$Image = $(if ($env:ML_BASE_IMAGE) { $env:ML_BASE_IMAGE } else { "kocaelinewsmap-ml-base:py313-torch210-cpu-v1" }),
    [switch]$Pull,
    [switch]$NoCache
)

$ErrorActionPreference = "Stop"

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dockerArgs = @(
    "build",
    "-f", (Join-Path $backendRoot "Dockerfile.ml-base"),
    "-t", $Image
)

if ($Pull) {
    $dockerArgs += "--pull"
}

if ($NoCache) {
    $dockerArgs += "--no-cache"
}

$dockerArgs += $backendRoot

Write-Host "Building ML base image $Image ..."
& docker @dockerArgs

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Built $Image"
Write-Host "Next step: docker compose build ml"

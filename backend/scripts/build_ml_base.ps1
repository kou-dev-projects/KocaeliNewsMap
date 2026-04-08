param(
    [string]$Image = $(if ($env:ML_BASE_IMAGE) { $env:ML_BASE_IMAGE } else { "kocaelinewsmap-ml-base:py313-torch210-cpu-v3" }),
    [switch]$Pull,
    [switch]$NoCache,
    [switch]$PreloadModels,
    [switch]$SkipModelPreload,
    [string]$PreloadNerProvider = "bertturk",
    [string]$PreloadNerModel = "savasy/bert-base-turkish-ner-cased",
    [string]$PreloadTextProvider = "mock"
)

$ErrorActionPreference = "Stop"

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$shouldPreload = $false
if ($PreloadModels -and -not $SkipModelPreload) {
    $shouldPreload = $true
}

$dockerArgs = @(
    "build",
    "-f", (Join-Path $backendRoot "Dockerfile.ml-base"),
    "-t", $Image,
    "--build-arg", ("PRELOAD_ML_MODELS=" + ($(if ($shouldPreload) { "true" } else { "false" }))),
    "--build-arg", ("PRELOAD_NER_PROVIDER=" + $PreloadNerProvider),
    "--build-arg", ("PRELOAD_NER_MODEL=" + $PreloadNerModel),
    "--build-arg", ("PRELOAD_TEXT_PROVIDER=" + $PreloadTextProvider)
)

if ($Pull) {
    $dockerArgs += "--pull"
}

if ($NoCache) {
    $dockerArgs += "--no-cache"
}

$dockerArgs += $backendRoot

Write-Host "Building ML base image $Image ..."
if ($shouldPreload) {
    Write-Host "  model preload: enabled"
} else {
    Write-Host "  model preload: disabled"
}
& docker @dockerArgs

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Built $Image"
Write-Host "Next step: docker compose build ml"

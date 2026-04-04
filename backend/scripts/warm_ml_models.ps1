param(
    [string]$NerProvider = "bertturk",
    [string]$NerModel = "savasy/bert-base-turkish-ner-cased",
    [double]$NerMinScore = 0.50,
    [double]$GlinerThreshold = 0.50,
    [string]$TextProvider = "mock",
    [string]$ImageProvider = "mock"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$dockerArgs = @(
    "compose",
    "exec",
    "-T",
    "ml",
    "python",
    "-u",
    "-m",
    "app.scripts.preload_ml_models",
    "--ner-provider",
    $NerProvider,
    "--ner-model",
    $NerModel,
    "--ner-min-score",
    [string]$NerMinScore,
    "--gliner-threshold",
    [string]$GlinerThreshold,
    "--text-provider",
    $TextProvider,
    "--image-provider",
    $ImageProvider
)

Write-Host "Warming ML models in running ml service ..."
Write-Host ("  ner=" + $NerProvider + " text=" + $TextProvider + " image=" + $ImageProvider)
& docker @dockerArgs

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "ML warmup completed"

<#
.SYNOPSIS
    Clean clone verification script for VeilRAG.
.DESCRIPTION
    Clones the repository to a clean temporary directory, creates a virtual environment,
    installs dependencies exactly as CI does, and executes ingestion, evaluation, linting,
    type checking, and the test suite.
#>

$ErrorActionPreference = "Stop"

$repoRoot = (Get-Item "$PSScriptRoot\..").FullName
$tempId = [System.Guid]::NewGuid().ToString("N").Substring(0, 8)
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) "veilrag_clean_$tempId"

Write-Host "======================================================================"
Write-Host " VEILRAG CLEAN CLONE PRE-PUSH VERIFICATION"
Write-Host " Source: $repoRoot"
Write-Host " Target: $tempDir"
Write-Host "======================================================================"

try {
    Write-Host "`n[1/6] Cloning repository to temporary workspace..."
    git clone --no-hardlinks $repoRoot $tempDir
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }

    Set-Location $tempDir

    Write-Host "`n[2/6] Creating isolated virtual environment..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }

    $py = Join-Path $tempDir ".venv\Scripts\python.exe"

    Write-Host "`n[3/6] Installing dependencies per ci.yml specification..."
    & $py -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

    & $py -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) { throw "dependency installation failed" }

    & $py -m spacy download en_core_web_lg
    if ($LASTEXITCODE -ne 0) { throw "spacy model download failed" }

    Write-Host "`n[4/6] Ingesting and verifying corpus v1 in clean environment..."
    & $py -m src.rag.ingest --corpus v1
    if ($LASTEXITCODE -ne 0) { throw "corpus v1 ingestion failed" }

    & $py -m src.eval.ingest_eval --corpus v1
    if ($LASTEXITCODE -ne 0) { throw "ingest_eval verification failed" }

    Write-Host "`n[5/6] Running linting and type checking..."
    & $py -m ruff check src/ tests/ scripts/
    if ($LASTEXITCODE -ne 0) { throw "ruff linting failed" }

    & $py -m mypy src/ tests/ scripts/
    if ($LASTEXITCODE -ne 0) { throw "mypy type checking failed" }

    Write-Host "`n[6/6] Executing unit test suite..."
    & $py -m pytest tests/ -v -m "not slow"
    if ($LASTEXITCODE -ne 0) { throw "pytest test suite failed" }

    Write-Host "`n======================================================================"
    Write-Host " SUCCESS: Clean clone verification passed all gates!"
    Write-Host "======================================================================"
}
finally {
    Set-Location $repoRoot
    if (Test-Path $tempDir) {
        Write-Host "Cleaning up temporary clone at $tempDir..."
        Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
    }
}

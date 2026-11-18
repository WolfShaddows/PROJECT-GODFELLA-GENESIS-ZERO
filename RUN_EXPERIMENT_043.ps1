$ErrorActionPreference = "Stop"

$Root = "C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002"

$OutDir = Join-Path $Root "evidence\MIRROR_FORENSICS_043_20261106_141448"

$MatrixPath = Join-Path $Root "evidence\SPACETIME_038_20261106_102543\038_spacetime_matrix.npz"

$SnapshotPath = Join-Path $Root "evidence\DEEP_UNIVERSE_035_20261106_084957\frozen_universe.json"

$PythonScript = Join-Path $OutDir "043_mirror_forensics.py"

if (-not (Test-Path $PythonScript)) {
    throw "Python forensic script missing."
}

$MatrixBefore = (Get-FileHash $MatrixPath -Algorithm SHA256).Hash
$SnapshotBefore = (Get-FileHash $SnapshotPath -Algorithm SHA256).Hash

$env:GODFELLA_043_OUT = $OutDir

try {
    Write-Host "PROJECT GODFELLA - EXPERIMENT 043"
    Write-Host "THE 6400 MIRROR FORENSICS"
    Write-Host ""

    python $PythonScript

    if ($LASTEXITCODE -ne 0) {
        throw "Python execution failed."
    }

    $MatrixAfter = (Get-FileHash $MatrixPath -Algorithm SHA256).Hash
    $SnapshotAfter = (Get-FileHash $SnapshotPath -Algorithm SHA256).Hash

    if ($MatrixBefore -ne $MatrixAfter) {
        throw "Matrix integrity failure."
    }

    if ($SnapshotBefore -ne $SnapshotAfter) {
        throw "Snapshot integrity failure."
    }

    Write-Host ""
    Write-Host "MATRIX UNCHANGED: TRUE"
    Write-Host "SNAPSHOT UNCHANGED: TRUE"
    Write-Host "EXPERIMENT 043 VERIFIED"
}
finally {
    Remove-Item Env:\GODFELLA_043_OUT -ErrorAction SilentlyContinue
}

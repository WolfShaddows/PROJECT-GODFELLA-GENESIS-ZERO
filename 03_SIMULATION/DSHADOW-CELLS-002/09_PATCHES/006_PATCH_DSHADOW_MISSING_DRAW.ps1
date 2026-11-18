# PATCH_DSHADOW_MISSING_DRAW.ps1
# Restores the missing central draw() dispatcher in the current dashboard.
# Does not touch Python, API routes, simulation state, or server process.
$ErrorActionPreference = "Stop"

$root = Join-Path (Get-Location).Path "03_SIMULATION\DSHADOW-CELLS-002"
$target = Join-Path $root "observer\index.html"
if (!(Test-Path $target)) {
    throw "Dashboard not found: $target. Run this script from PROJECT GODFELLA root."
}

$html = Get-Content -Path $target -Raw

if ($html -match 'function\s+draw\s*\(\s*\)\s*\{') {
    Write-Host "A draw() function already exists. No changes made." -ForegroundColor Yellow
    exit 0
}

$anchor = 'function setMode(m){'
if (!$html.Contains($anchor)) {
    throw "Expected insertion point not found. No changes made."
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path (Split-Path $target) "index_before_draw_restore_$stamp.html"
Copy-Item $target $backup -Force

$dispatcher = @'
function draw(){
 if(!latest)return;
 const w=main.clientWidth,h=main.clientHeight;
 if(!w||!h)return;
 // Canvas dimensions are already scaled by fit(); drawing coordinates are CSS pixels.
 mc.save();
 mc.clearRect(0,0,w,h);
 if(mode==="raw")drawRaw(latest,w,h);
 else if(mode==="density")drawDensity(latest,w,h);
 else drawProcessed(latest,w,h);
 mc.restore();
 drawDensityStrip(latest);
 drawHistory(latest);
}
'@

$html = $html.Replace($anchor, $dispatcher + "`r`n" + $anchor)
Set-Content -Path $target -Value $html -Encoding UTF8

# Verify the exact missing function is now present.
$check = Get-Content -Path $target -Raw
if ($check -notmatch 'function\s+draw\s*\(\s*\)\s*\{') {
    Copy-Item $backup $target -Force
    throw "Verification failed; original dashboard restored from backup."
}

Write-Host "`nMISSING DRAW() RESTORED" -ForegroundColor Green
Write-Host "Backup: $backup" -ForegroundColor Yellow
Write-Host "Only observer/index.html was changed." -ForegroundColor Green
Write-Host "Python engine and running universe were NOT stopped or restarted." -ForegroundColor Green
Write-Host "In Edge, press Ctrl+F5. Do not press RESET." -ForegroundColor Cyan

# PATCH_DSHADOW_PROCESSED_RENDER.ps1
# Replaces the flat binary occupancy image with a perspective space-time density renderer.
# It uses only browser-observed positions already returned by /api/state.
# It does NOT alter the simulation engine, API, or running universe.

$ErrorActionPreference = "Stop"
$root = Join-Path (Get-Location).Path "03_SIMULATION\DSHADOW-CELLS-002"
$target = Join-Path $root "observer\index.html"
if (!(Test-Path $target)) { throw "Dashboard not found: $target. Run from PROJECT GODFELLA root." }

$html = Get-Content -Path $target -Raw

if ($html -notmatch 'function\s+drawProcessed\s*\(' -or $html -notmatch 'function\s+captureSnapshot\s*\(') {
    throw "Expected captureSnapshot()/drawProcessed() functions were not found. No changes made."
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path (Split-Path $target) "index_before_processed_renderer_$stamp.html"
Copy-Item $target $backup -Force

$capture = @'
function captureSnapshot(s){
 const generation=Number(s.generation||0);
 if(generation===lastSampleGeneration)return;
 lastSampleGeneration=generation;
 const p=Array.isArray(s.positions)?s.positions:[];
 if(!p.length)return;
 const lo=Number(s.min_x??Math.min(...p)),hi=Number(s.max_x??Math.max(...p));
 worldMin=Math.min(worldMin,lo);worldMax=Math.max(worldMax,hi);
 // Count actual active coordinates per spatial bin (not a binary occupied/empty flag).
 const bins=new Uint16Array(RASTER_WIDTH),span=Math.max(1,hi-lo+1);
 for(let i=0;i<p.length;i++){
  const x=Math.max(0,Math.min(RASTER_WIDTH-1,Math.floor((Number(p[i])-lo)/span*RASTER_WIDTH)));
  if(bins[x]<65535)bins[x]++;
 }
 snapshots.push({generation,active:Number(s.active_cells||p.length),lo,hi,bins});
 if(snapshots.length>HISTORY_LIMIT)snapshots.shift();
}
'@

$processed = @'
function drawProcessed(s,w,h){
 mc.fillStyle="#02060d";mc.fillRect(0,0,w,h);
 // Subtle star/grid field gives depth without adding simulated cells.
 mc.save();
 for(let x=0;x<w;x+=42){mc.strokeStyle="rgba(20,105,135,.16)";mc.beginPath();mc.moveTo(x,0);mc.lineTo(x,h);mc.stroke();}
 for(let y=0;y<h;y+=34){mc.strokeStyle="rgba(20,105,135,.10)";mc.beginPath();mc.moveTo(0,y);mc.lineTo(w,y);mc.stroke();}
 const rows=snapshots.slice(-Math.min(snapshots.length,100));
 if(rows.length<2){
  mc.fillStyle="#9fc8d8";mc.font="13px Segoe UI";
  mc.fillText("Collecting space-time density samples…",20,34);
  mc.restore();return;
 }
 const left=w*.055,right=w*.945,top=h*.13,bottom=h*.88;
 const bins=RASTER_WIDTH,lines=Math.min(76,rows.length),stride=Math.max(1,Math.floor(rows.length/lines));
 const sampled=[];
 for(let i=0;i<rows.length;i+=stride)sampled.push(rows[i]);
 const maxCount=Math.max(1,...sampled.flatMap(r=>Array.from(r.bins).filter((v,j)=>j%8===0)));
 const project=(u,depth,z)=>{
  const perspective=depth*.13;
  return {x:left+u*(right-left)+perspective*w*.42,
          y:bottom-depth*(bottom-top)-z};
 };
 // Back-to-front density mesh: every ridge is one observed generation sample.
 sampled.forEach((row,ri)=>{
  const depth=ri/Math.max(1,sampled.length-1);
  const mean=Math.max(1,row.active/bins);
  const sigma=Math.sqrt(mean);
  mc.beginPath();
  for(let j=0;j<bins;j+=4){
   const count=row.bins[j];
   const deviation=(count-mean)/sigma;
   const z=Math.max(-2.8,Math.min(2.8,deviation))*13;
   const q=project(j/(bins-1),depth,z);
   if(j===0)mc.moveTo(q.x,q.y);else mc.lineTo(q.x,q.y);
  }
  const age=.18+.72*depth;
  mc.strokeStyle=ri===sampled.length-1?"rgba(80,255,255,.98)":`rgba(0,${Math.round(105+105*age)},${Math.round(155+95*age)},${.13+.42*age})`;
  mc.lineWidth=ri===sampled.length-1?2.5:1;
  if(ri===sampled.length-1){mc.shadowColor="#00eaff";mc.shadowBlur=15;}
  mc.stroke();mc.shadowBlur=0;
 });
 // Connect selected density samples across time to form the visible space-time lattice.
 const step=Math.max(1,Math.floor(bins/100));
 for(let j=0;j<bins;j+=step){
  mc.beginPath();
  sampled.forEach((row,ri)=>{
   const depth=ri/Math.max(1,sampled.length-1),mean=Math.max(1,row.active/bins),sigma=Math.sqrt(mean);
   const deviation=(row.bins[j]-mean)/sigma;
   const z=Math.max(-2.8,Math.min(2.8,deviation))*13;
   const q=project(j/(bins-1),depth,z);
   if(ri===0)mc.moveTo(q.x,q.y);else mc.lineTo(q.x,q.y);
  });
  mc.strokeStyle="rgba(0,205,235,.18)";mc.lineWidth=.65;mc.stroke();
 }
 // Sparse luminous points are samples of measured density peaks, not added substrate cells.
 sampled.forEach((row,ri)=>{
  const depth=ri/Math.max(1,sampled.length-1),mean=Math.max(1,row.active/bins),sigma=Math.sqrt(mean);
  for(let j=0;j<bins;j+=17){
   if(row.bins[j]<mean+1.15*sigma)continue;
   const deviation=(row.bins[j]-mean)/sigma,z=Math.min(2.8,deviation)*13;
   const q=project(j/(bins-1),depth,z);
   mc.fillStyle="rgba(75,245,255,.72)";mc.fillRect(q.x-1,q.y-1,2,2);
  }
 });
 // Header and time-range annotation.
 mc.shadowBlur=0;mc.fillStyle="#7defff";mc.font="600 11px Segoe UI";
 mc.fillText("PROCESSED SPACE-TIME DENSITY",14,20);
 mc.fillStyle="#a8c1d4";mc.font="10px Segoe UI";
 mc.fillText(`${sampled.length} OBSERVED SAMPLES  ·  GENERATION ${sampled[0].generation.toLocaleString()} → ${sampled[sampled.length-1].generation.toLocaleString()}`,14,h-10);
 mc.restore();
}
'@

# Replace only the two renderer functions; preserve all other dashboard code and controls.
$rxCapture = '(?s)function\s+captureSnapshot\s*\(s\)\s*\{.*?\n\}'
$rxProcessed = '(?s)function\s+drawProcessed\s*\(s,w,h\)\s*\{.*?\n\}'
$html2 = [regex]::Replace($html,$rxCapture,[System.Text.RegularExpressions.MatchEvaluator]{ param($m) $capture },1)
$html2 = [regex]::Replace($html2,$rxProcessed,[System.Text.RegularExpressions.MatchEvaluator]{ param($m) $processed },1)

if ($html2 -eq $html -or $html2 -notmatch 'PROCESSED SPACE-TIME DENSITY' -or $html2 -notmatch 'new Uint16Array\(RASTER_WIDTH\)') {
    throw "Patch verification failed. Original dashboard remains unchanged; backup retained at $backup"
}

Set-Content -Path $target -Value $html2 -Encoding UTF8
$verify = Get-Content -Path $target -Raw
if ($verify -notmatch 'PROCESSED SPACE-TIME DENSITY' -or $verify -notmatch 'function\s+drawProcessed\s*\(') {
    Copy-Item $backup $target -Force
    throw "Post-write verification failed; original dashboard restored."
}

Write-Host "`nPROCESSED SPACE-TIME RENDERER INSTALLED" -ForegroundColor Green
Write-Host "Backup: $backup" -ForegroundColor Yellow
Write-Host "Only observer/index.html was changed." -ForegroundColor Green
Write-Host "Simulation engine and running universe were NOT stopped or restarted." -ForegroundColor Green
Write-Host "In Edge: Ctrl+F5, then choose IMAGEN PROCESADA." -ForegroundColor Cyan
Write-Host "Note: the perspective mesh visualizes measured density over browser-observed time samples; it is not a literal 3D galaxy." -ForegroundColor DarkCyan

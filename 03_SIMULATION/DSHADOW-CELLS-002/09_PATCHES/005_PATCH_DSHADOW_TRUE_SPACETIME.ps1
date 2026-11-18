# PATCH_DSHADOW_TRUE_SPACETIME.ps1
# Replaces the misleading solid-cyan rendering with a browser-side space-time
# raster built from actual /api/state positions snapshots. Does not touch engine.
$ErrorActionPreference = "Stop"
$root = Join-Path (Get-Location).Path "03_SIMULATION\DSHADOW-CELLS-002"
$target = Join-Path $root "observer\index.html"
if (!(Test-Path $target)) { throw "Dashboard not found: $target. Run from PROJECT GODFELLA root." }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path (Split-Path $target) "index_before_spacetime_$stamp.html"
Copy-Item $target $backup -Force
$html = Get-Content $target -Raw

$oldState = 'let latest=null,mode="processed",lastEvent="",busy=false,zoom=1;'
$newState = 'let latest=null,mode="processed",lastEvent="",busy=false,zoom=1;let snapshots=[],lastSampleGeneration=-1,worldMin=0,worldMax=1;const HISTORY_LIMIT=420,RASTER_WIDTH=1200;'
if (!$html.Contains($oldState)) { throw "Could not locate dashboard state declaration. No changes made." }
$html = $html.Replace($oldState,$newState)

$pattern = '(?s)function drawRaw\(s,w,h\)\{.*?(?=function drawDensityStrip\(s\))'
$replacement = @'
function captureSnapshot(s){
 const generation=Number(s.generation||0);
 if(generation===lastSampleGeneration)return;
 lastSampleGeneration=generation;
 const p=Array.isArray(s.positions)?s.positions:[];
 if(!p.length)return;
 const lo=Number(s.min_x??Math.min(...p)),hi=Number(s.max_x??Math.max(...p));
 worldMin=Math.min(worldMin,lo);worldMax=Math.max(worldMax,hi);
 // Store a compact occupancy raster. Every active coordinate contributes to
 // its bin; this is a display transform, not a change to simulation state.
 const bins=new Uint8Array(RASTER_WIDTH),span=Math.max(1,hi-lo+1);
 for(let i=0;i<p.length;i++){
   const x=Math.max(0,Math.min(RASTER_WIDTH-1,Math.floor((Number(p[i])-lo)/span*RASTER_WIDTH)));
   bins[x]=1;
 }
 snapshots.push({generation,active:Number(s.active_cells||p.length),lo,hi,bins});
 if(snapshots.length>HISTORY_LIMIT)snapshots.shift();
}
function drawRaw(s,w,h){
 mc.fillStyle="#020810";mc.fillRect(0,0,w,h);
 // Fine coordinate grid and a single real 1-D lattice baseline.
 mc.strokeStyle="#17334a";mc.lineWidth=1;
 for(let x=0;x<w;x+=40){mc.beginPath();mc.moveTo(x,0);mc.lineTo(x,h);mc.stroke();}
 const p=Array.isArray(s.positions)?s.positions:[],lo=Number(s.min_x||0),hi=Number(s.max_x||0),span=Math.max(1,hi-lo+1);
 const mid=h*.57,usable=w-54,step=usable/span;
 mc.strokeStyle="#52728a";mc.beginPath();mc.moveTo(24,mid+8);mc.lineTo(w-24,mid+8);mc.stroke();
 mc.save();mc.shadowColor="#00e5ee";mc.shadowBlur=8;mc.fillStyle="#55f8f2";
 // Render every actual position, with a pixel cap only for display performance.
 const stride=Math.max(1,Math.ceil(p.length/30000));
 for(let i=0;i<p.length;i+=stride){const x=27+(Number(p[i])-lo)*step;mc.fillRect(x,mid-3,Math.max(1.4,Math.min(4,step)),7);}
 mc.restore();
 mc.fillStyle="#a9c2d5";mc.font="11px Segoe UI";
 mc.fillText(`CURRENT CONFIGURATION · ${p.length.toLocaleString()} active coordinates · display stride ${stride}`,14,20);
}
function drawProcessed(s,w,h){
 mc.fillStyle="#02060d";mc.fillRect(0,0,w,h);
 if(!snapshots.length){mc.fillStyle="#a8c1d4";mc.font="13px Segoe UI";mc.fillText("Collecting real configuration snapshots…",20,32);return;}
 const rows=snapshots.slice(-Math.min(snapshots.length,Math.floor(h*1.15)));
 const rowH=h/rows.length;
 // Each horizontal line is a sampled generation; bright pixels are bins
 // occupied by actual active-cell coordinates at that observation.
 for(let r=0;r<rows.length;r++){
  const row=rows[r],y=r*rowH;
  for(let x=0;x<RASTER_WIDTH;x++)if(row.bins[x]){
   const intensity=.48+.52*(r/Math.max(1,rows.length-1));
   mc.fillStyle=`rgba(0,${Math.round(145+95*intensity)},${Math.round(170+75*intensity)},${.55+.4*intensity})`;
   const px=x*w/RASTER_WIDTH;
   mc.fillRect(px,y,Math.ceil(w/RASTER_WIDTH)+.35,Math.max(1,rowH));
  }
 }
 // Small time axis and sparse generation labels.
 mc.fillStyle="#a5bed0";mc.font="10px Segoe UI";
 mc.fillText(`SPACE-TIME RECORD · ${rows.length} browser-observed snapshots · ${rows[0].generation.toLocaleString()} → ${rows[rows.length-1].generation.toLocaleString()}`,12,14);
}
function drawDensity(s,w,h){
 mc.fillStyle="#020810";mc.fillRect(0,0,w,h);
 const p=Array.isArray(s.positions)?s.positions:[],lo=Number(s.min_x||0),hi=Number(s.max_x||0),span=Math.max(1,hi-lo+1),bins=Array(180).fill(0);
 for(const pos of p){const i=Math.max(0,Math.min(179,Math.floor((Number(pos)-lo)/span*180)));bins[i]++;}
 const max=Math.max(1,...bins),base=h-20;
 mc.strokeStyle="#18354d";mc.beginPath();mc.moveTo(0,base);mc.lineTo(w,base);mc.stroke();
 bins.forEach((v,i)=>{if(!v)return;const bh=(v/max)*(h-34),x=i*w/180;mc.fillStyle=`rgba(0,${Math.round(150+90*v/max)},${Math.round(175+70*v/max)},${.35+.65*v/max})`;mc.fillRect(x,base-bh,Math.ceil(w/180)+1,bh);});
 mc.fillStyle="#a8c1d4";mc.font="10px Segoe UI";mc.fillText(`CURRENT SPATIAL OCCUPANCY · ${p.length.toLocaleString()} active coordinates`,12,14);
}
'@
$updated = [regex]::Replace($html,$pattern,$replacement,1)
if ($updated -eq $html) { throw "Could not locate renderer functions. Backup retained; no changes made." }
$html = $updated

$oldUpdate = 'function update(s){latest=s;'
$newUpdate = 'function update(s){captureSnapshot(s);latest=s;'
if (!$html.Contains($oldUpdate)) { throw "Could not locate update() hook. No changes written; backup retained." }
$html = $html.Replace($oldUpdate,$newUpdate)

$patternHistory = '(?s)function drawHistory\(s\)\{.*?(?=function setMode\(m\))'
$history = @'
function drawHistory(s){
 let w=hist.clientWidth,h=hist.clientHeight;
 hc.fillStyle="#020810";hc.fillRect(0,0,w,h);
 if(!snapshots.length)return;
 const rows=snapshots.slice(-Math.max(1,Math.floor(h))),rh=h/rows.length;
 rows.forEach((row,i)=>{for(let x=0;x<RASTER_WIDTH;x++)if(row.bins[x]){
   hc.fillStyle="#00dfe9";hc.fillRect(x*w/RASTER_WIDTH,i*rh,Math.ceil(w/RASTER_WIDTH)+.3,Math.max(1,rh));
 }});
 hc.fillStyle="#9bb5c9";hc.font="10px Segoe UI";
 hc.fillText(`${rows.length} OBSERVED SAMPLES · GENERATION ${rows[0].generation.toLocaleString()} — ${rows[rows.length-1].generation.toLocaleString()}`,8,12);
}
'@
$updated = [regex]::Replace($html,$patternHistory,$history,1)
if ($updated -eq $html) { throw "Could not locate drawHistory(). Backup retained; no changes written." }
$html = $updated

Set-Content -Path $target -Value $html -Encoding UTF8
Write-Host "`nTRUE SPACE-TIME RENDERER INSTALLED" -ForegroundColor Green
Write-Host "Backup: $backup" -ForegroundColor Yellow
Write-Host "Dashboard only was changed. Python engine was NOT stopped or restarted." -ForegroundColor Green
Write-Host "Refresh Edge with Ctrl+F5. The history image will build from this moment onward." -ForegroundColor Cyan

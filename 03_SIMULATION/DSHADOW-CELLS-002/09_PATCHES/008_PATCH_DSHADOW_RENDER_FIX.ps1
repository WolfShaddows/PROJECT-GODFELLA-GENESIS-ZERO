# PATCH_DSHADOW_RENDER_FIX.ps1
# Repairs only browser-side rendering. Does not stop/restart the engine.
$ErrorActionPreference="Stop"
$root=Join-Path (Get-Location).Path "03_SIMULATION\DSHADOW-CELLS-002"
$target=Join-Path $root "observer\index.html"
if(!(Test-Path $target)){throw "Dashboard not found. Run from PROJECT GODFELLA root."}
$stamp=Get-Date -Format "yyyyMMdd_HHmmss"
$backup=Join-Path (Split-Path $target) "index_before_render_fix_$stamp.html"
Copy-Item $target $backup -Force
$html=Get-Content $target -Raw

# Ensure snapshots are sampled from the live positions array, not a nonexistent API rows field.
$pattern='(?s)function captureSnapshot\(s\)\{.*?(?=function drawRaw\(s,w,h\))'
$capture=@'
function captureSnapshot(s){
 const generation=Number(s.generation||0);
 if(generation===lastSampleGeneration)return;
 lastSampleGeneration=generation;
 const p=Array.isArray(s.positions)?s.positions:[];
 if(!p.length)return;
 const lo=Number(s.min_x??Math.min(...p)),hi=Number(s.max_x??Math.max(...p));
 worldMin=Math.min(worldMin,lo);worldMax=Math.max(worldMax,hi);
 const bins=new Uint8Array(RASTER_WIDTH),span=Math.max(1,hi-lo+1);
 for(let i=0;i<p.length;i++){
  const x=Math.max(0,Math.min(RASTER_WIDTH-1,Math.floor((Number(p[i])-lo)/span*RASTER_WIDTH)));
  bins[x]=1;
 }
 snapshots.push({generation,active:Number(s.active_cells||p.length),lo,hi,bins});
 if(snapshots.length>HISTORY_LIMIT)snapshots.shift();
}
'@
$updated=[regex]::Replace($html,$pattern,$capture,1)
if($updated -eq $html){throw "captureSnapshot() not found. No dashboard changes made."}
$html=$updated

$pattern='(?s)function drawRaw\(s,w,h\)\{.*?(?=function drawDensity\(s,w,h\))'
$raw=@'
function drawRaw(s,w,h){
 mc.fillStyle="#020810";mc.fillRect(0,0,w,h);
 mc.strokeStyle="#142d42";mc.lineWidth=1;
 for(let x=0;x<w;x+=40){mc.beginPath();mc.moveTo(x,0);mc.lineTo(x,h);mc.stroke();}
 const p=Array.isArray(s.positions)?s.positions:[];
 if(!p.length){mc.fillStyle="#a8c1d4";mc.font="13px Segoe UI";mc.fillText("Waiting for live cell coordinates…",18,32);return;}
 const lo=Number(s.min_x??Math.min(...p)),hi=Number(s.max_x??Math.max(...p));
 const span=Math.max(1,hi-lo+1),left=18,right=w-18,usable=right-left,step=usable/span;
 const y=h*.58;
 mc.strokeStyle="#24445b";mc.beginPath();mc.moveTo(left,y+5);mc.lineTo(right,y+5);mc.stroke();
 mc.save();mc.fillStyle="#56f5ee";mc.shadowColor="#00e5ee";mc.shadowBlur=5;
 // Draw actual active coordinates. Width is proportional to lattice scale;
 // no fabricated 2-D cell positions are introduced.
 const stride=Math.max(1,Math.ceil(p.length/50000));
 for(let i=0;i<p.length;i+=stride){
  const x=left+(Number(p[i])-lo)*step;
  mc.fillRect(x,y-3,Math.max(.8,Math.min(3,step)),6);
 }
 mc.restore();
 mc.fillStyle="#a8c1d4";mc.font="10px Segoe UI";
 mc.fillText(`1-D LATTICE · ${p.length.toLocaleString()} active coordinates · ${lo.toLocaleString()} to ${hi.toLocaleString()}`,12,16);
}
'@
$updated=[regex]::Replace($html,$pattern,$raw,1)
if($updated -eq $html){throw "drawRaw() not found. Backup retained; no changes written."}
$html=$updated

$pattern='(?s)function drawProcessed\(s,w,h\)\{.*?(?=function drawDensity\(s,w,h\))'
$processed=@'
function drawProcessed(s,w,h){
 mc.fillStyle="#02060d";mc.fillRect(0,0,w,h);
 if(!snapshots.length){mc.fillStyle="#a8c1d4";mc.font="13px Segoe UI";mc.fillText("Collecting live space-time observations…",18,32);return;}
 const rows=snapshots.slice(-Math.max(1,Math.floor(h*1.15)));
 const globalLo=Math.min(...rows.map(r=>r.lo)),globalHi=Math.max(...rows.map(r=>r.hi));
 const globalSpan=Math.max(1,globalHi-globalLo+1),rowH=h/rows.length;
 // Remap each observed 1-D configuration into one shared coordinate frame.
 // Each horizontal scanline is a real browser-observed generation.
 for(let ri=0;ri<rows.length;ri++){
  const row=rows[ri],y=ri*rowH,rowSpan=Math.max(1,row.hi-row.lo+1);
  for(let i=0;i<row.bins.length;i++)if(row.bins[i]){
   const coordinate=row.lo+(i+.5)/row.bins.length*rowSpan;
   const px=(coordinate-globalLo)/globalSpan*w;
   const alpha=.42+.5*(ri/Math.max(1,rows.length-1));
   mc.fillStyle=`rgba(0,${Math.round(160+75*alpha)},${Math.round(180+65*alpha)},${alpha})`;
   mc.fillRect(px,y,Math.max(.8,w/RASTER_WIDTH),Math.max(1,rowH));
  }
 }
 mc.fillStyle="#a5bed0";mc.font="10px Segoe UI";
 mc.fillText(`SPACE-TIME · ${rows.length} observed snapshots · GEN ${rows[0].generation.toLocaleString()} → ${rows[rows.length-1].generation.toLocaleString()}`,12,13);
}
'@
$updated=[regex]::Replace($html,$pattern,$processed,1)
if($updated -eq $html){throw "drawProcessed() not found. Backup retained; no changes written."}
$html=$updated

# Use browser-captured snapshots for the history strip too; API history contains metrics only.
$pattern='(?s)function drawHistory\(s\)\{.*?(?=function setMode\(m\))'
$history=@'
function drawHistory(s){
 let w=hist.clientWidth,h=hist.clientHeight;
 hc.fillStyle="#020810";hc.fillRect(0,0,w,h);
 if(!snapshots.length){hc.fillStyle="#9bb5c9";hc.font="11px Segoe UI";hc.fillText("History begins with the first live observation.",10,20);return;}
 const rows=snapshots.slice(-Math.max(1,Math.floor(h))),rh=h/rows.length;
 const lo=Math.min(...rows.map(r=>r.lo)),hi=Math.max(...rows.map(r=>r.hi)),span=Math.max(1,hi-lo+1);
 rows.forEach((row,i)=>{const rs=Math.max(1,row.hi-row.lo+1);for(let b=0;b<row.bins.length;b++)if(row.bins[b]){
  const xCoord=row.lo+(b+.5)/row.bins.length*rs;
  hc.fillStyle="#00dfe9";hc.fillRect((xCoord-lo)/span*w,i*rh,Math.max(.8,w/RASTER_WIDTH),Math.max(1,rh));
 }});
 hc.fillStyle="#9bb5c9";hc.font="10px Segoe UI";
 hc.fillText(`${rows.length} observed generations · ${rows[0].generation.toLocaleString()} — ${rows[rows.length-1].generation.toLocaleString()}`,8,12);
}
'@
$updated=[regex]::Replace($html,$pattern,$history,1)
if($updated -eq $html){throw "drawHistory() not found. Backup retained; no changes written."}
$html=$updated

Set-Content -Path $target -Value $updated -Encoding UTF8
Write-Host "`nRENDER FIX INSTALLED" -ForegroundColor Green
Write-Host "Backup: $backup" -ForegroundColor Yellow
Write-Host "Engine/server were NOT stopped or restarted." -ForegroundColor Green
Write-Host "Refresh Edge with Ctrl+F5. Processed view accumulates from now on." -ForegroundColor Cyan

# PATCH_DSHADOW_OBSERVATORY_V2.ps1
# Visual-only dashboard replacement. Does NOT stop/restart the Python engine.
$ErrorActionPreference = "Stop"
$root = Join-Path (Get-Location).Path "03_SIMULATION\DSHADOW-CELLS-002"
$target = Join-Path $root "observer\index.html"
if (!(Test-Path $target)) { throw "Dashboard not found: $target. Run this from PROJECT GODFELLA root." }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path (Split-Path $target) "index_backup_$stamp.html"
Copy-Item $target $backup -Force

$html = @'
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSHADOW-CELLS | Observatory 002</title>
<style>
:root{--bg:#050b14;--side:#07111f;--panel:#091626;--panel2:#0b1a2b;--line:#244b69;--cyan:#00e5ee;--cyan2:#48f5ef;--blue:#4d8cff;--gold:#f3c84b;--text:#e8f3ff;--muted:#91a9c0;--green:#00e58a;--red:#ff617d}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(ellipse at 60% -15%,#102c47 0%,#07111e 48%,#030810 100%);color:var(--text);font:14px/1.45 "Segoe UI",Arial,sans-serif}
.app{min-height:100vh;display:grid;grid-template-columns:278px minmax(0,1fr)}
.sidebar{background:linear-gradient(180deg,#071321,#050c16);border-right:1px solid #1d4965;padding:20px 16px;display:flex;flex-direction:column;min-height:100vh}
.brand{font-size:29px;font-weight:850;letter-spacing:4px;line-height:1.05;color:#f0f6ff}.brand small{display:block;color:var(--gold);font-size:11px;letter-spacing:4px;margin-top:6px}
.navlabel{font-size:11px;letter-spacing:2px;color:#91a8c0;margin:42px 12px 12px}
.nav a{display:flex;align-items:center;gap:13px;color:#c2d3e5;text-decoration:none;padding:13px 12px;margin:5px 0;border:1px solid transparent;border-radius:9px;font-size:14px;transition:.18s}
.nav a:hover,.nav a.active{background:linear-gradient(90deg,#102a49,#0b1d32);border-color:#24749a;color:#fff;box-shadow:inset 3px 0 0 var(--cyan),0 0 16px #00d9ef18}
.ico{width:20px;height:20px;display:inline-grid;place-items:center;color:#8edaff;flex:0 0 20px}.ico svg{width:19px;height:19px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.side-divider{height:1px;background:#23435c;margin:20px 10px 0}.sidebrand{margin:24px 10px 0;color:#9ab0c6;font-size:11px;line-height:1.7}
main{padding:18px 22px 24px;min-width:0}.top{display:flex;justify-content:space-between;align-items:center;margin:0 2px 15px}.eyebrow{font-size:10px;letter-spacing:3px;color:#7fc8ff}.title{font-size:27px;font-weight:780;line-height:1.2}.conn{font-size:13px;color:var(--green);white-space:nowrap}.conn.bad{color:var(--red)}
.grid{display:grid;grid-template-columns:minmax(0,1fr) 322px;gap:16px}.card{background:linear-gradient(145deg,#0b1a2b,#071321);border:1px solid #285576;border-radius:13px;min-width:0;box-shadow:0 8px 25px #0002}
.head{height:57px;display:flex;justify-content:space-between;align-items:center;padding:0 18px;border-bottom:1px solid #1f435d;font-weight:750}.pill{border:1px solid #008da9;color:var(--cyan);border-radius:20px;padding:5px 12px;font-size:10px;letter-spacing:.3px}
.view{height:430px;position:relative;background:#020810;overflow:hidden}.view canvas{width:100%;height:100%;display:block}.viewtag{position:absolute;top:14px;left:14px;background:#061522ed;border:1px solid #078da4;border-radius:10px;padding:10px 13px;min-width:245px;box-shadow:0 0 22px #00ddeb18}.viewtag b{display:block;color:var(--cyan);font-size:14px;letter-spacing:.5px}.viewtag small{color:#c4d9e8;font-size:10px}.overlay{position:absolute;left:14px;bottom:14px;background:#061522ed;border:1px solid #16728d;border-radius:9px;padding:9px 12px;font-size:11px;line-height:1.8}
.density{position:absolute;right:14px;bottom:14px;width:230px;background:#061522ed;border:1px solid #16728d;border-radius:9px;padding:8px 10px}.density label{display:block;font-size:9px;letter-spacing:1px;color:#9ebbd0;margin-bottom:5px}.density canvas{height:35px!important;width:100%}
.viewbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:10px 14px;border-top:1px solid #1d425d}.viewbar .label{color:#b7cce0;margin-right:4px}.modebtn{background:#0a1c2e;color:#c7d9e9;border:1px solid #315875;border-radius:8px;padding:8px 11px;font-size:11px;font-weight:650;cursor:pointer}.modebtn.active{color:#eaffff;border-color:var(--cyan);background:#073244;box-shadow:0 0 13px #00dce94a}.zoom{margin-left:auto;display:flex;align-items:center;gap:9px;color:#b6cadd;font-size:11px}.zoom input{width:100px;accent-color:var(--cyan)}.iconbtn{background:#0a1c2e;color:#d9f8ff;border:1px solid #315875;border-radius:8px;padding:7px 10px;cursor:pointer}
.right{padding:16px 17px}.right h3{font-size:17px;margin:0 0 10px}.row{display:flex;justify-content:space-between;gap:10px;padding:10px 0;border-bottom:1px solid #1d3b54;font-size:12px;color:#b4c8da}.row b{color:#eaf5ff;text-align:right;font-variant-numeric:tabular-nums}.footnote{font-size:10px;line-height:1.55;color:#8fa7bd;margin-top:14px}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:16px 0}.metric{padding:15px 17px;min-height:112px}.metric-top{display:flex;align-items:center;gap:12px;color:var(--cyan)}.metric-top svg{width:26px;height:26px;stroke:currentColor;fill:none;stroke-width:1.8}.metric label{font-size:11px;letter-spacing:1px;color:#c0d2e4}.metric strong{display:block;font-size:28px;line-height:1.2;margin:5px 0 3px;font-variant-numeric:tabular-nums}.metric small{font-size:11px;color:var(--gold);font-weight:700}
.controls{padding:14px 16px;margin-top:14px}.controlhead{display:flex;align-items:center;gap:10px;font-size:15px;font-weight:750;margin-bottom:12px}.controlhead .gear{color:var(--cyan);font-size:21px}.buttons{display:flex;gap:8px;flex-wrap:wrap}.btn{min-height:41px;border:1px solid #41627e;background:linear-gradient(#142b43,#0b1a2b);color:#e8f4ff;border-radius:8px;padding:9px 13px;font-weight:700;font-size:11px;cursor:pointer}.btn:hover{border-color:var(--cyan);filter:brightness(1.15)}.btn.primary{background:linear-gradient(#13d96d,#008c49);border-color:#00ef87;color:#03140d}.btn.danger{border-color:#82445a}.speed{display:flex;align-items:center;gap:12px;margin-top:13px;color:#c0d3e3;font-size:11px;flex-wrap:wrap}.speed input{width:min(360px,38vw);accent-color:var(--cyan)}.speed b{font-size:15px;color:var(--cyan)}
.lower{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}.chart{padding:15px;min-height:190px}.charttitle{font-weight:750}.chartnote{font-size:10px;color:#91a8bf;margin:5px 0}.bars{height:115px;display:flex;align-items:end;gap:2px;margin-top:12px}.bar{flex:1;min-width:2px;background:linear-gradient(0deg,#1371a6,#00e5ee);border-radius:2px 2px 0 0}.log{height:120px;overflow:auto;color:#b9d5e8;font:11px/1.8 Consolas,monospace}
.section{margin-top:14px}.sectionhead{display:flex;align-items:center;justify-content:space-between;padding:13px 16px}.checkpointlist{padding:0 16px 12px;max-height:130px;overflow:auto;color:#a9bfd2;font-size:11px}.checkpointlist div{padding:6px 0;border-bottom:1px solid #1d3b54}
.toast{display:none;position:fixed;right:20px;bottom:20px;z-index:10;background:#0c2436;border:1px solid #1685a2;border-radius:9px;padding:12px 16px;color:#eaffff;box-shadow:0 10px 30px #0008}.toast.show{display:block}
@media(max-width:1150px){.app{grid-template-columns:230px minmax(0,1fr)}.grid{grid-template-columns:minmax(0,1fr) 285px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.view{height:390px}}
@media(max-width:850px){.app{grid-template-columns:1fr}.sidebar{min-height:auto;padding:12px 14px}.navlabel,.side-divider,.sidebrand{display:none}.brand{font-size:20px}.nav{display:flex;overflow:auto;gap:4px;margin-top:10px}.nav a{white-space:nowrap;padding:9px}.grid{grid-template-columns:1fr}.right{display:grid;grid-template-columns:1fr 1fr;gap:0 15px}.right h3,.right .footnote{grid-column:1/-1}.view{height:340px}.lower{grid-template-columns:1fr}}
@media(max-width:560px){main{padding:12px}.title{font-size:21px}.metrics{gap:8px}.metric{padding:11px}.metric strong{font-size:22px}.view{height:290px}.density{width:150px}.zoom{margin-left:0}.right{grid-template-columns:1fr}.right h3,.right .footnote{grid-column:auto}}
</style>
</head>
<body>
<div class="app">
<aside class="sidebar">
 <div class="brand">DSHADOW<small>CELLS OBSERVATORY</small></div>
 <div class="navlabel">OBSERVATION</div>
 <nav class="nav">
  <a class="active" href="#live"><span class="ico"><svg viewBox="0 0 24 24"><path d="m12 3 9 9-9 9-9-9z"/><circle cx="12" cy="12" r="2"/></svg></span>Live Universe</a>
  <a href="#spacetime"><span class="ico"><svg viewBox="0 0 24 24"><rect x="4" y="4" width="5" height="5"/><rect x="15" y="4" width="5" height="5"/><rect x="4" y="15" width="5" height="5"/><rect x="15" y="15" width="5" height="5"/></svg></span>Space-Time Evolution</a>
  <a href="#metrics"><span class="ico"><svg viewBox="0 0 24 24"><path d="M4 19V12h4v7M10 19V6h4v13M16 19V3h4v16"/></svg></span>Evolution Metrics</a>
  <a href="#research"><span class="ico"><svg viewBox="0 0 24 24"><path d="M6 3h9l4 4v14H6zM15 3v5h4M9 12h7M9 16h7"/></svg></span>Research Log</a>
  <a href="#checkpoints"><span class="ico"><svg viewBox="0 0 24 24"><path d="M12 3 20 7v10l-8 4-8-4V7z"/><path d="m8 12 3 3 5-6"/></svg></span>Checkpoints</a>
 </nav>
 <div class="side-divider"></div>
 <div class="navlabel" style="margin-top:20px">VIEW MODE</div>
 <nav class="nav">
  <a href="#" data-mode="raw"><span class="ico"><svg viewBox="0 0 24 24"><path d="M5 4h14v16H5zM9 8l-2 4 2 4M15 8l2 4-2 4"/></svg></span>Vista Real (RAW)</a>
  <a href="#" data-mode="processed" class="active"><span class="ico"><svg viewBox="0 0 24 24"><path d="M12 2 3 7l9 5 9-5zM3 12l9 5 9-5M3 17l9 5 9-5"/></svg></span>Imagen Procesada</a>
  <a href="#" data-mode="density"><span class="ico"><svg viewBox="0 0 24 24"><path d="M4 20V13h3v7M10 20V8h3v12M16 20V4h3v16"/></svg></span>Mapa de Densidad</a>
 </nav>
 <div class="side-divider"></div>
 <div class="sidebrand">◇ &nbsp; DARKSHADOWS GROUP<br>&nbsp;&nbsp;&nbsp;&nbsp;EXTERNAL OBSERVER<br>&nbsp;&nbsp;&nbsp;&nbsp;EXPERIMENT 002</div>
</aside>
<main>
 <div class="top"><div><div class="eyebrow">DSHADOW-CELLS / EXPERIMENT 002</div><div class="title">Live Operations &amp; Control</div></div><div id="connection" class="conn">● CONNECTING</div></div>
 <section id="live" class="grid">
  <div class="card">
   <div class="head"><b>LIVE UNIVERSE — CELLULAR STRUCTURE (RULE 110)</b><span class="pill" id="runstate">INITIALIZING</span></div>
   <div class="view"><canvas id="mainCanvas"></canvas>
    <div class="viewtag"><b id="modeTitle">IMAGEN PROCESADA</b><small id="modeDesc">Representación espacio-temporal de estados observados</small></div>
    <div class="overlay">RULE <b>110</b><br>GENERATION <b id="smallGen">0</b><br>SPACE <b>UNBOUNDED</b></div>
    <div class="density"><label>LIVE DENSITY PROFILE</label><canvas id="densityCanvas"></canvas></div>
   </div>
   <div class="viewbar"><span class="label">Visualización:</span>
    <button class="modebtn" data-mode="raw">▦ Vista Real (Raw)</button><button class="modebtn active" data-mode="processed">◈ Imagen Procesada</button><button class="modebtn" data-mode="density">▥ Mapa de Densidad</button>
    <div class="zoom">ZOOM <input id="zoom" type="range" min="50" max="200" value="100"><b id="zoomValue">100%</b></div>
    <button class="iconbtn" id="fullscreen" title="Pantalla completa">⛶</button>
   </div>
  </div>
  <aside class="card right">
   <h3>Universe telemetry</h3>
   <div class="row"><span>Engine status</span><b id="engineStatus">READY</b></div>
   <div class="row"><span>Rule</span><b>110</b></div>
   <div class="row"><span>Active cells</span><b id="activeSide">0</b></div>
   <div class="row"><span>Components</span><b id="componentsSide">0</b></div>
   <div class="row"><span>Spatial span</span><b id="spanSide">0</b></div>
   <div class="row"><span>Coordinate bounds</span><b id="boundsSide">0 / 0</b></div>
   <div class="row"><span>Observer time</span><b id="elapsedSide">0 s</b></div>
   <div class="row"><span>Last event</span><b id="lastEvent">Initialized</b></div>
   <p class="footnote">Observador externo. El procesamiento visual no modifica los estados ni agrega células al sustrato.</p>
  </aside>
 </section>
 <section id="metrics" class="metrics">
  <div class="card metric"><div class="metric-top"><svg viewBox="0 0 24 24"><path d="M3 17c5-12 7 12 12 0s6-9 6-9M3 7c5 12 7-12 12 0s6 9 6 9"/></svg><label>UNIVERSE TIME</label></div><strong id="generation">0</strong><small>GENERATIONS</small></div>
  <div class="card metric"><div class="metric-top"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="2"/><circle cx="5" cy="6" r="1.5"/><circle cx="19" cy="6" r="1.5"/><circle cx="5" cy="18" r="1.5"/><circle cx="19" cy="18" r="1.5"/></svg><label>ACTIVE CELLS</label></div><strong id="activeCells">0</strong><small>STATE = 1</small></div>
  <div class="card metric"><div class="metric-top"><svg viewBox="0 0 24 24"><circle cx="5" cy="6" r="2"/><circle cx="18" cy="5" r="2"/><circle cx="12" cy="18" r="2"/><path d="m7 7 9-1M6 8l5 8m6-9-4 9"/></svg><label>STRUCTURAL COMPONENTS</label></div><strong id="components">0</strong><small>CONTIGUOUS GROUPS</small></div>
  <div class="card metric"><div class="metric-top"><svg viewBox="0 0 24 24"><circle cx="12" cy="13" r="8"/><path d="M12 13V8m-3-6h6M18 4l2 2"/></svg><label>OBSERVER TIME</label></div><strong id="elapsed">0 s</strong><small>REAL ELAPSED TIME</small></div>
 </section>
 <section class="card controls">
  <div class="controlhead"><span class="gear">⚙</span> EVOLUTION CONTROL</div>
  <div class="buttons">
   <button class="btn primary" data-action="start">▶ START</button><button class="btn" data-action="pause">Ⅱ PAUSE</button><button class="btn" data-action="step">＋ STEP (1)</button><button class="btn" data-action="checkpoint">▣ SAVE CHECKPOINT</button><button class="btn" data-action="restore">↶ RESTORE</button><button class="btn danger" data-action="reset">↻ NEW UNIVERSE</button>
  </div>
  <div class="speed">EVOLUTION SPEED <input id="speedSlider" type="range" min="1" max="500" value="500"><b id="speedLabel">500 gen/tick</b><span style="color:#829bb2">MAX REQUESTED BATCH</span></div>
 </section>
 <section id="spacetime" class="card section"><div class="sectionhead"><b>SPACE-TIME EVOLUTION</b><small style="color:#8fa9c0">Observed generations · actual sampled cell states</small></div><div style="height:170px;padding:0 14px 14px"><canvas id="historyCanvas" style="width:100%;height:100%;display:block;background:#020810;border-radius:7px"></canvas></div></section>
 <section class="lower">
  <div class="card chart"><div class="charttitle">EVOLUTION TRACE</div><div class="chartnote">Active cells sampled from the engine history</div><div class="bars" id="bars"></div></div>
  <div id="research" class="card chart"><div class="charttitle">RESEARCH EVENT LOG</div><div class="log" id="log">[SYSTEM] Observatory ready.<br>[SYSTEM] Waiting for telemetry…</div></div>
 </section>
 <section id="checkpoints" class="card section"><div class="sectionhead"><b>CHECKPOINT ARCHIVE</b><button class="btn" id="refreshCheckpoints">↻ REFRESH</button></div><div class="checkpointlist" id="checkpointList">Loading checkpoints…</div></section>
 <div class="footnote">DARKSHADOWS GROUP · Rule 110 · Unbounded mathematical lattice, finite physical resources. Visualization is a rendering of simulation data, not a claim of biological life or astronomical matter.</div>
</main>
</div>
<div id="toast" class="toast" role="status"></div>
<script>
(()=>{"use strict";
const $=id=>document.getElementById(id),fmt=n=>Number(n||0).toLocaleString("en-US");
const main=$("mainCanvas"),mc=main.getContext("2d"),den=$("densityCanvas"),dc=den.getContext("2d"),hist=$("historyCanvas"),hc=hist.getContext("2d");
let latest=null,mode="processed",lastEvent="",busy=false,zoom=1;
function fit(c,ctx){let r=c.getBoundingClientRect(),dpr=devicePixelRatio||1;c.width=Math.max(1,r.width*dpr);c.height=Math.max(1,r.height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);}
function resize(){[main,den,hist].forEach(c=>fit(c,c.getContext("2d")));draw();}
window.addEventListener("resize",resize);
function toast(s){let t=$("toast");t.textContent=s;t.classList.add("show");clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.classList.remove("show"),3500);}
function drawRaw(s,w,h){mc.fillStyle="#020810";mc.fillRect(0,0,w,h);mc.strokeStyle="#ffffff0b";for(let x=0;x<w;x+=40){mc.beginPath();mc.moveTo(x,0);mc.lineTo(x,h);mc.stroke();}for(let y=0;y<h;y+=40){mc.beginPath();mc.moveTo(0,y);mc.lineTo(w,y);mc.stroke();}
let p=s.positions||[],lo=Number(s.min_x||0),span=Math.max(1,Number(s.max_x||0)-lo+1),maxDraw=Math.min(p.length,100000),pad=30,usable=w-60,scale=usable/span;
mc.save();mc.translate(w/2,h/2);mc.scale(zoom,zoom);mc.translate(-w/2,-h/2);mc.fillStyle="#42f4ed";mc.shadowColor="#00e5ee";mc.shadowBlur=7;
for(let i=0;i<maxDraw;i++){let x=pad+(p[i]-lo)*scale;mc.fillRect(x,h/2-3,Math.max(1.5,Math.min(5,scale)),6);}mc.restore();
mc.fillStyle="#9ab4c9";mc.font="10px Segoe UI";mc.fillText(`LATTICE COORDINATES · ${fmt(maxDraw)} CELLS DISPLAYED`,14,15);
}
function drawProcessed(s,w,h){mc.fillStyle="#01070e";mc.fillRect(0,0,w,h);let rows=s.rows||[],usable=rows.slice(-Math.max(30,Math.floor(h*1.7)));if(!usable.length){mc.fillStyle="#9ab4c9";mc.fillText("Collecting space-time samples…",20,30);return;}
let rh=h/usable.length,cellW=w/720;usable.forEach((r,ri)=>{let bits=r.bits||"",y=ri*rh;for(let x=0;x<bits.length;x++){if(bits.charCodeAt(x)===49){let intensity=0.58+0.42*(ri/usable.length);mc.fillStyle=`rgba(0,${Math.floor(185+70*intensity)},${Math.floor(195+60*intensity)},${0.72+0.28*intensity})`;mc.fillRect(x*cellW,y,Math.ceil(cellW),Math.max(1,rh));}}});
 // Subtle glow is applied to actual raster pixels only.
}
function drawDensity(s,w,h){mc.fillStyle="#020810";mc.fillRect(0,0,w,h);let rows=s.rows||[],last=rows.slice(-Math.max(1,Math.floor(h/3)));if(!last.length)return;let bins=Array(120).fill(0);last.forEach(r=>{let b=r.bits||"";for(let i=0;i<b.length;i++)if(b[i]==="1")bins[Math.min(119,Math.floor(i/Math.max(1,b.length)*120))]++;});let max=Math.max(1,...bins);bins.forEach((v,i)=>{let bh=(v/max)*(h-24);let x=i*w/120;mc.fillStyle=`rgba(0,${180+Math.round(70*v/max)},${190+Math.round(65*v/max)},${.25+.75*v/max})`;mc.fillRect(x,h-bh,Math.ceil(w/120)+1,bh);});}
function drawDensityStrip(s){let w=den.clientWidth,h=den.clientHeight;dc.clearRect(0,0,w,h);let p=s.positions||[],bins=Array(90).fill(0),lo=Number(s.min_x||0),span=Math.max(1,Number(s.max_x||0)-lo+1);p.forEach(x=>bins[Math.min(89,Math.floor((x-lo)/span*90))]++);let max=Math.max(1,...bins);bins.forEach((v,i)=>{let bh=Math.max(2,v/max*(h-3));dc.fillStyle=`rgba(0,${170+Math.round(80*v/max)},${190+Math.round(60*v/max)},.9)`;dc.fillRect(i*w/90,h-bh,Math.ceil(w/90),bh);});}
function drawHistory(s){let w=hist.clientWidth,h=hist.clientHeight;hc.fillStyle="#020810";hc.fillRect(0,0,w,h);let rows=s.rows||[];if(!rows.length)return;let chosen=rows.slice(-Math.max(1,Math.floor(h)));let rh=h/chosen.length,cw=w/720;chosen.forEach((r,i)=>{let bits=r.bits||"";for(let x=0;x<bits.length;x++)if(bits[x]==="1"){hc.fillStyle="#00dfe9";hc.fillRect(x*cw,i*rh,Math.ceil(cw),Math.max(1,rh));}});}
function drawBars(s){let host=$("bars");host.innerHTML="";let a=(s.history||[]).slice(-100),max=Math.max(1,...a.map(x=>x.active));a.forEach(x=>{let b=document.createElement("div");b.className="bar";b.style.height=(5+100*x.active/max)+"px";b.title=`Generation ${fmt(x.generation)} · ${fmt(x.active)} active · ${fmt(x.components)} components`;host.appendChild(b);});}
function draw(){if(!latest)return;let w=main.clientWidth,h=main.clientHeight;mc.save();mc.clearRect(0,0,w,h);if(mode==="raw")drawRaw(latest,w,h);else if(mode==="density")drawDensity(latest,w,h);else drawProcessed(latest,w,h);mc.restore();drawDensityStrip(latest);drawHistory(latest);}
function setMode(m){mode=m;document.querySelectorAll("[data-mode]").forEach(e=>e.classList.toggle("active",e.dataset.mode===m));$("modeTitle").textContent=m==="raw"?"VISTA REAL (RAW)":m==="density"?"MAPA DE DENSIDAD":"IMAGEN PROCESADA";$("modeDesc").textContent=m==="raw"?"Células activas en coordenadas espaciales actuales":m==="density"?"Concentración espacial calculada desde las células activas":"Representación espacio-temporal de estados observados";if(latest)draw();}
document.querySelectorAll("[data-mode]").forEach(e=>e.addEventListener("click",ev=>{ev.preventDefault();setMode(e.dataset.mode);}));
function update(s){latest=s;$("connection").textContent="● CONNECTED";$("connection").classList.remove("bad");$("runstate").textContent=s.running?"EVOLUTION RUNNING":s.status;$("engineStatus").textContent=s.status;$("generation").textContent=fmt(s.generation);$("smallGen").textContent=fmt(s.generation);$("activeCells").textContent=fmt(s.active_cells);$("activeSide").textContent=fmt(s.active_cells);$("components").textContent=fmt(s.components);$("componentsSide").textContent=fmt(s.components);$("spanSide").textContent=fmt(s.span);$("boundsSide").textContent=fmt(s.min_x)+" / "+fmt(s.max_x);$("elapsed").textContent=Number(s.elapsed_seconds||0).toFixed(1)+" s";$("elapsedSide").textContent=Number(s.elapsed_seconds||0).toFixed(1)+" s";$("lastEvent").textContent=s.event||"—";if(s.event&&s.event!==lastEvent){lastEvent=s.event;let line=document.createElement("div");line.textContent=`[${new Date().toLocaleTimeString()}] ${s.event}`;$("log").prepend(line);while($("log").children.length>50)$("log").lastChild.remove();}draw();}
async function api(action,extra={}){if(busy)return;busy=true;try{let r=await fetch("/api/control",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action,...extra})});if(!r.ok)throw Error("HTTP "+r.status);let j=await r.json();if(!j.ok)throw Error(j.message||"Command rejected");if(j.state)update(j.state);toast(j.message||action+" completed");}catch(e){toast("Command failed: "+e.message);}finally{busy=false;}}
document.querySelectorAll("[data-action]").forEach(b=>b.addEventListener("click",()=>{let a=b.dataset.action;if(a==="reset"&&!confirm("Start a new universe? The current state will be checkpointed first."))return;api(a);}));
$("speedSlider").addEventListener("input",e=>$("speedLabel").textContent=e.target.value+" gen/tick");$("speedSlider").addEventListener("change",e=>api("speed",{value:Number(e.target.value)}));
$("zoom").addEventListener("input",e=>{$("zoomValue").textContent=e.target.value+"%";zoom=Number(e.target.value)/100;if(latest)draw();});
$("fullscreen").addEventListener("click",()=>{let el=$("live");if(!document.fullscreenElement)el.requestFullscreen?.();else document.exitFullscreen?.();});
async function checkpoints(){try{let r=await fetch("/api/checkpoints?"+Date.now()),j=await r.json(),host=$("checkpointList");host.innerHTML="";if(!j.checkpoints.length){host.textContent="No checkpoints saved yet.";return;}j.checkpoints.forEach(c=>{let d=document.createElement("div");d.textContent=c.name+" · "+(c.bytes/1024).toFixed(1)+" KB";host.appendChild(d);});}catch(e){$("checkpointList").textContent="Unable to load checkpoint archive.";}}
$("refreshCheckpoints").addEventListener("click",checkpoints);
async function poll(){try{let r=await fetch("/api/state?"+Date.now(),{cache:"no-store"});if(!r.ok)throw Error("HTTP "+r.status);update(await r.json());}catch(e){$("connection").textContent="● DISCONNECTED";$("connection").classList.add("bad");}setTimeout(poll,500);}
document.querySelectorAll(".nav a[href^='#']").forEach(a=>a.addEventListener("click",()=>{document.querySelectorAll(".nav a[href^='#']").forEach(x=>x.classList.remove("active"));a.classList.add("active");}));
resize();checkpoints();poll();
})();
</script>
</body></html>
'@

Set-Content -Path $target -Value $html -Encoding UTF8
Write-Host "`nDSHADOW OBSERVATORY V2 INSTALLED" -ForegroundColor Green
Write-Host "Backup: $backup" -ForegroundColor Yellow
Write-Host "Updated: $target" -ForegroundColor Cyan
Write-Host "`nThe Python engine was NOT stopped or restarted." -ForegroundColor Green
Write-Host "In Edge press Ctrl+F5 to load the new dashboard." -ForegroundColor Yellow

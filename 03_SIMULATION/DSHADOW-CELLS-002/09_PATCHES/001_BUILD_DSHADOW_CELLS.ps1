$ErrorActionPreference = 'Stop'
$base = Join-Path (Get-Location).Path '03_SIMULATION\DSHADOW-CELLS'
@('config','engine','observer','data\raw','checkpoints','logs','research') | ForEach-Object { New-Item -ItemType Directory -Force (Join-Path $base $_) | Out-Null }
$config = @'
{
  "experiment_id":"DSHADOW-CELLS-001",
  "name":"OPEN-ENDED UNIVERSE",
  "substrate":{"dimension":1,"topology":"unbounded_integer_lattice","states":[0,1],"update":"synchronous","model":"elementary_cellular_automaton","rule":110,"quiescent_background":0},
  "initial_conditions":{"seed":20261105,"pattern":"finite_random_seed","span":41,"density":0.28},
  "execution":{"target_generations":null,"checkpoint_interval":5000,"snapshot_interval":10,"batch_generations":100},
  "constraints":{"predefined_organisms":false,"artificial_reproduction":false,"selection":false,"ai_inside_substrate":false,"observer_read_only":true},
  "historical_experiments":{"GZ-LIFE-001":[67,109,137],"GZ-LIFE-002":[67,109,137]}
}
'@
Set-Content (Join-Path $base 'config\DSHADOW_CELLS_CONFIG.json') $config -Encoding UTF8
$py = @'
import json, random, time, argparse
from pathlib import Path
from threading import Thread, RLock
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'config'/'DSHADOW_CELLS_CONFIG.json').read_text(encoding='utf-8-sig'))
RAW=ROOT/'data'/'raw'; CK=ROOT/'checkpoints'; RAW.mkdir(parents=True,exist_ok=True); CK.mkdir(parents=True,exist_ok=True)
RULE=CFG['substrate']['rule']; rng=random.Random(CFG['initial_conditions']['seed']); lock=RLock()
S={'cells':set(), 'gen':0,'running':False,'speed':100,'status':'READY','start':None,'elapsed':0.0,'history':[],'event':'Initial seed established'}
def components(a):
 if not a:return 0
 q=sorted(a);return 1+sum(y>x+1 for x,y in zip(q,q[1:]))
def save_snapshot():
 a=sorted(S['cells']); obj={'generation':S['gen'],'active_cells':len(a),'min_x':a[0] if a else 0,'max_x':a[-1] if a else 0,'positions':a[:50000],'truncated':len(a)>50000}
 (RAW/'latest_snapshot.json').write_text(json.dumps(obj),encoding='utf-8')
def checkpoint():
 (CK/f"checkpoint_{S['gen']:012d}.json").write_text(json.dumps({'generation':S['gen'],'cells':sorted(S['cells'])}),encoding='utf-8');S['event']=f"Checkpoint saved at generation {S['gen']}"
def init():
 c=CFG['initial_conditions'];S['cells']={i-c['span']//2 for i in range(c['span']) if rng.random()<c['density']};S['gen']=0;S['status']='READY';S['history']=[];S['event']='Initial finite seed established';save_snapshot()
def step():
 old=S['cells']; cand={z for x in old for z in (x-1,x,x+1)}; new=set()
 for x in cand:
  n=(int(x-1 in old)<<2)|(int(x in old)<<1)|int(x+1 in old)
  if (RULE>>n)&1:new.add(x)
 S['cells']=new;S['gen']+=1
 if S['gen']%10==0:save_snapshot()
 if S['gen']%100==0:
  S['history'].append({'generation':S['gen'],'active':len(new),'components':components(new),'span':(max(new)-min(new)+1) if new else 0});S['history']=S['history'][-500:]
 if S['gen']%5000==0:checkpoint()
 if not new:S['status']='EXTINCT';S['running']=False;S['event']='Extinction: no active cells remain'
def elapsed():return S['elapsed']+(time.time()-S['start'] if S['running'] and S['start'] else 0)
def snapshot():
 a=sorted(S['cells']);return {'generation':S['gen'],'active_cells':len(a),'components':components(S['cells']),'span':(a[-1]-a[0]+1) if a else 0,'min_x':a[0] if a else 0,'max_x':a[-1] if a else 0,'positions':a[:50000],'truncated':len(a)>50000,'running':S['running'],'status':S['status'],'speed':S['speed'],'elapsed':round(elapsed(),2),'event':S['event'],'history':S['history'][-300:]}
def worker():
 while True:
  with lock:
   if S['running']:
    for _ in range(S['speed']):
     if not S['running']:break
     step()
     if S['status']=='EXTINCT':break
  time.sleep(.002)
class H(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'observer'),**kw)
 def log_message(self,*a):pass
 def do_GET(self):
  if self.path.startswith('/api/state'):
   with lock:b=json.dumps(snapshot()).encode()
   self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b);return
  super().do_GET()
 def do_POST(self):
  n=int(self.headers.get('Content-Length','0'));req=json.loads(self.rfile.read(n) or b'{}');act=req.get('action')
  with lock:
   if act=='start' and S['status']!='EXTINCT':S['running']=True;S['status']='RUNNING';S['start']=time.time();S['event']='Evolution resumed'
   elif act=='pause':
    if S['running'] and S['start']:S['elapsed']+=time.time()-S['start']
    S['running']=False;S['start']=None;S['status']='PAUSED';S['event']='Evolution paused by observer'
   elif act=='step' and not S['running'] and S['status']!='EXTINCT':step();S['status']='PAUSED'
   elif act=='speed':S['speed']=max(1,min(10000,int(req.get('value',100))))
   elif act=='checkpoint':checkpoint()
   elif act=='reset':S['running']=False;S['elapsed']=0;S['start']=None;init()
   elif act=='restore':
    files=sorted(CK.glob('checkpoint_*.json'))
    if files:
     d=json.loads(files[-1].read_text());S['gen']=d['generation'];S['cells']=set(d['cells']);S['running']=False;S['status']='PAUSED';S['event']=f"Restored generation {S['gen']}";save_snapshot()
    else:S['event']='No checkpoint available'
   b=json.dumps({'ok':True,'state':snapshot()}).encode()
  self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b)
def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8765);args=p.parse_args()
 files=sorted(CK.glob('checkpoint_*.json'))
 if files:
  d=json.loads(files[-1].read_text());S['gen']=d['generation'];S['cells']=set(d['cells']);S['status']='PAUSED';S['event']=f"Restored generation {S['gen']}";save_snapshot()
 else:init()
 Thread(target=worker,daemon=True).start();server=ThreadingHTTPServer(('127.0.0.1',args.port),H)
 print(f"DSHADOW-CELLS Observatory: http://127.0.0.1:{args.port}");print('Unbounded 1D lattice | sparse storage | Rule 110');print('Ctrl+C stops the process and saves a checkpoint.')
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:
  with lock:
   if S['running'] and S['start']:S['elapsed']+=time.time()-S['start']
   S['running']=False;checkpoint()
  server.server_close()
if __name__=='__main__':main()
'@
Set-Content (Join-Path $base 'engine\dshadow_engine.py') $py -Encoding UTF8
$html = @'
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DSHADOW-CELLS Observatory</title><style>
:root{--bg:#080e18;--panel:#101b2b;--line:#293a51;--txt:#e8eef8;--muted:#879ab3;--cyan:#51dfdc;--gold:#d9b76d;--blue:#526df0;--green:#29d6a1}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 55% 0%,#172943,var(--bg) 60%);color:var(--txt);font:14px Segoe UI,Arial}.app{display:grid;grid-template-columns:220px 1fr;min-height:100vh}.side{background:#0b1421;border-right:1px solid var(--line);padding:25px 17px}.brand{font-size:24px;letter-spacing:4px;font-weight:800}.brand small{display:block;font-size:10px;color:var(--gold);letter-spacing:4px}.nav{margin-top:45px;color:var(--muted);font-size:11px;letter-spacing:2px}.nav div{padding:13px;margin:7px 0;letter-spacing:0;font-size:13px}.nav .sel{background:#1b2b50;border-radius:8px;color:#b8c7ff}main{padding:24px;min-width:0}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}.eyebrow{font-size:10px;letter-spacing:3px;color:#8da8ff}.title{font-size:25px;font-weight:700}.conn{color:var(--green)}.grid{display:grid;grid-template-columns:minmax(0,1fr) 250px;gap:15px}.card{background:linear-gradient(145deg,#111d2e,#0c1420);border:1px solid var(--line);border-radius:13px;overflow:hidden}.head{padding:15px 17px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between}.pill{color:var(--cyan);border:1px solid #31506a;padding:4px 10px;border-radius:20px;font-size:10px}.view{height:410px;background:radial-gradient(ellipse,#142b44,#07101c 70%);position:relative}canvas{width:100%;height:100%;display:block}.overlay{position:absolute;bottom:14px;left:14px;background:#081321df;border:1px solid #344963;padding:10px;border-radius:8px;font-size:11px;line-height:1.8}.right{padding:17px}.right h3{margin:0 0 10px}.row{display:flex;justify-content:space-between;padding:11px 0;border-bottom:1px solid #26364b;color:var(--muted);font-size:12px}.row b{color:var(--txt)}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:15px 0}.metric{padding:15px}.metric label{font-size:10px;letter-spacing:1px;color:var(--muted)}.metric strong{display:block;font-size:23px;margin-top:8px}.metric small{color:var(--gold);font-size:10px}.controls{padding:16px;margin-bottom:15px}.buttons{display:flex;gap:8px;flex-wrap:wrap}.btn{background:#17263c;color:var(--txt);border:1px solid #3a506b;border-radius:8px;padding:10px 13px;cursor:pointer}.btn.primary{background:#465fe0}.speed{margin-top:15px;color:var(--muted);display:flex;align-items:center;gap:12px}input{accent-color:var(--blue);width:min(350px,50vw)}.lower{display:grid;grid-template-columns:1fr 1fr;gap:15px}.chart{padding:16px;min-height:190px}.bars{height:125px;display:flex;align-items:end;gap:3px;margin-top:12px}.bar{flex:1;background:linear-gradient(#51dfdc,#4058c7);min-width:2px;border-radius:2px 2px 0 0}.log{font:11px/1.8 Consolas;color:#a7b7cc;max-height:145px;overflow:auto}.foot{font-size:10px;color:#687c95;margin-top:14px}@media(max-width:950px){.app{grid-template-columns:1fr}.side{display:none}main{padding:13px}.grid,.lower{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}.view{height:330px}}
</style></head><body><div class="app"><aside class="side"><div class="brand">DSHADOW<small>CELLS OBSERVATORY</small></div><div class="nav">OBSERVATION<div class="sel">◈ &nbsp; Live Universe</div><div>◷ &nbsp; Evolution History</div><div>⌘ &nbsp; Structural Analysis</div><div>▤ &nbsp; Research Log</div><div>⬡ &nbsp; Checkpoints</div></div></aside><main><div class="top"><div><div class="eyebrow">DSHADOW-CELLS / EXPERIMENT 001</div><div class="title">Live Operations &amp; Control</div></div><div id="conn" class="conn">● CONNECTING</div></div><div class="grid"><section class="card"><div class="head"><b>LIVE UNIVERSE VIEW</b><span class="pill" id="runstate">INITIALIZING</span></div><div class="view"><canvas id="space"></canvas><div class="overlay">RULE <b>110</b><br>GENERATION <b id="gsmall">0</b><br>TOPOLOGY <b>UNBOUNDED</b></div></div></section><aside class="card right"><h3>Universe telemetry</h3><div class="row"><span>Engine status</span><b id="status">READY</b></div><div class="row"><span>Rule</span><b>110</b></div><div class="row"><span>Active cells</span><b id="a2">0</b></div><div class="row"><span>Components</span><b id="c2">0</b></div><div class="row"><span>Spatial span</span><b id="span">0</b></div><div class="row"><span>Coordinate bounds</span><b id="bounds">0 / 0</b></div><div class="row"><span>Observer time</span><b id="time2">0 s</b></div><div class="row"><span>Last event</span><b id="event">Initialized</b></div><p class="foot">External observer. No artificial reproduction, selection or AI inside the substrate.</p></aside></div><div class="metrics"><div class="card metric"><label>UNIVERSE TIME</label><strong id="gen">0</strong><small>GENERATIONS</small></div><div class="card metric"><label>ACTIVE CELLS</label><strong id="active">0</strong><small>STATE = 1</small></div><div class="card metric"><label>STRUCTURAL COMPONENTS</label><strong id="comp">0</strong><small>CONTIGUOUS GROUPS</small></div><div class="card metric"><label>OBSERVER TIME</label><strong id="time">0 s</strong><small>REAL ELAPSED TIME</small></div></div><section class="card controls"><div class="head" style="padding:0 0 14px;border:0"><b>EVOLUTION CONTROL</b><span class="pill">EXTERNAL OBSERVER</span></div><div class="buttons"><button class="btn primary" onclick="act('start')">▶ START UNIVERSE</button><button class="btn" onclick="act('pause')">Ⅱ PAUSE</button><button class="btn" onclick="act('step')">＋ SINGLE GENERATION</button><button class="btn" onclick="act('checkpoint')">▣ SAVE CHECKPOINT</button><button class="btn" onclick="act('restore')">↶ RESTORE</button><button class="btn" onclick="act('reset')">↻ RESET</button></div><div class="speed">EVOLUTION SPEED <input type="range" min="1" max="10000" value="100" oninput="speed(this.value)"><b id="speedv">100 gen/tick</b></div></section><div class="lower"><section class="card chart"><b>EVOLUTION TRACE</b><div class="foot">Active cells sampled every 100 generations</div><div class="bars" id="bars"></div></section><section class="card chart"><b>RESEARCH EVENT LOG</b><div class="log" id="log">[SYSTEM] Observatory initialized.<br>[SYSTEM] Waiting for telemetry…</div></section></div><div class="foot">DARKSHADOWS GROUP • Mathematical lattice is unbounded; physical compute and storage remain finite.</div></main></div><script>
const cv=document.getElementById('space'),cx=cv.getContext('2d');let d=null,ev='';function fit(){let r=cv.getBoundingClientRect(),z=devicePixelRatio||1;cv.width=r.width*z;cv.height=r.height*z;cx.setTransform(z,0,0,z,0,0);draw()}window.addEventListener('resize',fit);function draw(){if(!d)return;let w=cv.clientWidth,h=cv.clientHeight;cx.clearRect(0,0,w,h);cx.strokeStyle='#ffffff0d';for(let x=0;x<w;x+=40){cx.beginPath();cx.moveTo(x,0);cx.lineTo(x,h);cx.stroke()}for(let y=0;y<h;y+=40){cx.beginPath();cx.moveTo(0,y);cx.lineTo(w,y);cx.stroke()}let p=d.positions||[],mid=(d.min_x+d.max_x)/2,scale=Math.max(2,Math.min(8,(w-40)/Math.max(40,Math.min(d.span,160))));for(let i=0;i<p.length&&i<6000;i++){let x=w/2+(p[i]-mid)*scale,y=h/2+Math.sin(p[i]*.17)*Math.min(65,h*.2);cx.fillStyle='#55e1df';cx.shadowColor='#3bdde8';cx.shadowBlur=7;cx.fillRect(x,y,Math.max(2,scale*.8),Math.max(2,scale*.8))}cx.shadowBlur=0;if(d.truncated){cx.fillStyle='#d9b76d';cx.fillText('DISPLAY SAMPLE: 6,000 CELLS MAX',14,20)}}function num(n){return Number(n||0).toLocaleString()}function update(s){d=s;conn.textContent='● CONNECTED';runstate.textContent=s.running?'EVOLUTION RUNNING':s.status;status.textContent=s.status;gen.textContent=num(s.generation);gsmall.textContent=num(s.generation);active.textContent=num(s.active_cells);a2.textContent=num(s.active_cells);comp.textContent=num(s.components);c2.textContent=num(s.components);span.textContent=num(s.span);bounds.textContent=num(s.min_x)+' / '+num(s.max_x);time.textContent=s.elapsed+' s';time2.textContent=s.elapsed+' s';event.textContent=s.event;if(ev!==s.event){ev=s.event;log.innerHTML=(`[${new Date().toLocaleTimeString()}] ${s.event}<br>`+log.innerHTML).slice(0,5000)}bars.innerHTML='';let hist=(s.history||[]).slice(-100),m=Math.max(1,...hist.map(x=>x.active));hist.forEach(x=>{let b=document.createElement('div');b.className='bar';b.style.height=(5+115*x.active/m)+'px';b.title=`Generation ${x.generation}: ${x.active} active`;bars.appendChild(b)});draw()}async function act(action){let r=await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})});let j=await r.json();if(!j.ok)alert(j.message||'Command failed')}async function speed(v){speedv.textContent=v+' gen/tick';await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'speed',value:v})})}async function poll(){try{let r=await fetch('/api/state?'+Date.now());update(await r.json())}catch(e){conn.textContent='● DISCONNECTED'}setTimeout(poll,500)}fit();poll();
</script></body></html>
'@
Set-Content (Join-Path $base 'observer\index.html') $html -Encoding UTF8
$readme = @'
# DSHADOW-CELLS — Open-Ended Cellular Evolution

Run from this directory: `python engine\dshadow_engine.py`
Open: http://127.0.0.1:8765

The prototype uses a one-dimensional unbounded integer lattice, binary states, synchronous Elementary Cellular Automaton Rule 110 and sparse storage. Rule 110 is quiescent on an all-zero neighborhood, allowing finite-support configurations on an unbounded background. Universe time is measured in generations; observer time is wall-clock time.

This is not a claim of life or guaranteed open-ended evolution. Persistence, pattern similarity and component changes are not by themselves evidence of reproduction, heredity, adaptation or consciousness. The lattice is mathematically unbounded, but physical memory, storage and processing are finite. Checkpoints are saved under `checkpoints`.
'@
Set-Content (Join-Path $base 'README.md') $readme -Encoding UTF8
$protocol = @'
# DSHADOW-CELLS-001 Research Protocol

Premise: establish initial conditions on an unbounded integer lattice and observe autonomous evolution without prescribing organisms, reproduction, goals or selection.

Model: one-dimensional binary Elementary Cellular Automaton Rule 110. Synchronous updates. Sparse active-coordinate storage. Finite initial seed on an unbounded zero background.

Observer: external dashboard. Controls start, pause, step, checkpoint and restore the process; they do not choose cell outcomes or alter the transition rule.

Safeguards: persistence is not life; similarity is not inheritance; a split is not reproduction; complexity is not adaptation; repeated states may indicate periodicity rather than novelty. Claims of self-reproduction require lineage tracking, controls and tests against coincidental resemblance.

Computational reality: no finite computer provides unlimited memory or processing. The mathematical lattice has no fixed spatial boundary; hardware limits remain explicit.
'@
Set-Content (Join-Path $base 'research\RESEARCH_PROTOCOL.md') $protocol -Encoding UTF8
Write-Host "`nDSHADOW-CELLS laboratory created at: $base" -ForegroundColor Green
Write-Host "NEXT: cd `"$base`"; python engine\dshadow_engine.py; open http://127.0.0.1:8765" -ForegroundColor Cyan

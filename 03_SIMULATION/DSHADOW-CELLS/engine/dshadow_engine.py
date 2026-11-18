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

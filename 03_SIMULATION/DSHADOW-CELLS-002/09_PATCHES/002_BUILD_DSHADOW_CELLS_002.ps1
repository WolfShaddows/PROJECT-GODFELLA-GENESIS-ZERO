# BUILD_DSHADOW_CELLS_002.ps1
# Builds a clean, independent DSHADOW-CELLS Observatory 002.
# Run from PROJECT GODFELLA root. Does not overwrite DSHADOW-CELLS 001.

$ErrorActionPreference = "Stop"
$projectRoot = (Get-Location).Path
$base = Join-Path $projectRoot "03_SIMULATION\DSHADOW-CELLS-002"

$folders = @(
    "config", "engine", "observer", "data\raw",
    "data\derived", "checkpoints", "logs", "research"
)
foreach ($folder in $folders) {
    New-Item -ItemType Directory -Force -Path (Join-Path $base $folder) | Out-Null
}

$config = @'
{
  "experiment_id": "DSHADOW-CELLS-002",
  "name": "THE UNBOUNDED OBSERVATORY",
  "model": {
    "dimension": 1,
    "lattice": "unbounded_integer_coordinates",
    "cell_states": [0, 1],
    "update": "synchronous",
    "rule": 110,
    "quiescent_background": 0
  },
  "initial_conditions": {
    "seed": 20261105,
    "initial_span": 41,
    "initial_density": 0.28
  },
  "execution": {
    "target_generations": null,
    "checkpoint_interval": 5000,
    "observation_interval": 10,
    "history_limit": 1200,
    "speed_default": 500,
    "speed_min": 1,
    "speed_max": 500
  },
  "scientific_constraints": {
    "predefined_organisms": false,
    "artificial_reproduction": false,
    "artificial_selection": false,
    "ai_inside_substrate": false,
    "observer_changes_cell_states": false
  }
}
'@
Set-Content (Join-Path $base "config\DSHADOW_CELLS_002_CONFIG.json") $config -Encoding UTF8

$engine = @'
from __future__ import annotations
import argparse, json, random, time, uuid, threading
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config" / "DSHADOW_CELLS_002_CONFIG.json").read_text(encoding="utf-8-sig"))
RAW, CHECK, LOGS = ROOT / "data" / "raw", ROOT / "checkpoints", ROOT / "logs"
for folder in (RAW, CHECK, LOGS):
    folder.mkdir(parents=True, exist_ok=True)

RULE = int(CFG["model"]["rule"])
SEED = int(CFG["initial_conditions"]["seed"])
SPAN = int(CFG["initial_conditions"]["initial_span"])
DENSITY = float(CFG["initial_conditions"]["initial_density"])
OBS_EVERY = int(CFG["execution"]["observation_interval"])
CHECK_EVERY = int(CFG["execution"]["checkpoint_interval"])
HISTORY_LIMIT = int(CFG["execution"]["history_limit"])
SPEED_MIN = int(CFG["execution"]["speed_min"])
SPEED_MAX = int(CFG["execution"]["speed_max"])

lock = threading.RLock()
state = {
    "active": set(), "generation": 0, "running": False, "status": "READY",
    "speed": int(CFG["execution"]["speed_default"]), "started_at": None,
    "elapsed_before": 0.0, "history": [], "rows": [], "event": "Universe initialized",
    "error": None, "run_id": str(uuid.uuid4())[:8], "last_checkpoint": None
}

def rule_value(l, c, r):
    index = (l << 2) | (c << 1) | r
    return (RULE >> index) & 1

def component_count(cells):
    if not cells:
        return 0
    ordered = sorted(cells)
    return 1 + sum(1 for a, b in zip(ordered, ordered[1:]) if b > a + 1)

def make_initial():
    rng = random.Random(SEED)
    return {i - SPAN // 2 for i in range(SPAN) if rng.random() < DENSITY} or {0}

def bounds(cells):
    if not cells:
        return 0, 0, 0
    lo, hi = min(cells), max(cells)
    return lo, hi, hi - lo + 1

def visual_row(cells, width=720):
    # Each row is a spatially sampled rendering of the actual active coordinates.
    # Coordinates are mapped over the current occupied interval for visibility.
    row = ["0"] * width
    if not cells:
        return "".join(row)
    lo, hi, span = bounds(cells)
    if span <= width:
        for x in cells:
            row[x - lo] = "1"
    else:
        for x in cells:
            idx = int((x - lo) * (width - 1) / max(1, span - 1))
            row[idx] = "1"
    return "".join(row)

def add_observation():
    cells = state["active"]
    lo, hi, span = bounds(cells)
    item = {
        "generation": state["generation"],
        "active": len(cells),
        "components": component_count(cells),
        "span": span,
        "min_x": lo,
        "max_x": hi
    }
    state["history"].append(item)
    if len(state["history"]) > HISTORY_LIMIT:
        state["history"] = state["history"][-HISTORY_LIMIT:]
    state["rows"].append({"generation": state["generation"], "bits": visual_row(cells)})
    if len(state["rows"]) > 700:
        state["rows"] = state["rows"][-700:]
    with (LOGS / "observations.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(item) + "\n")

def snapshot():
    cells = sorted(state["active"])
    payload = {
        "experiment": CFG["experiment_id"], "run_id": state["run_id"],
        "generation": state["generation"], "rule": RULE, "seed": SEED,
        "active": cells, "saved_at": time.time()
    }
    tmp = RAW / "latest_state.tmp"
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(RAW / "latest_state.json")

def save_checkpoint():
    cells = sorted(state["active"])
    payload = {
        "experiment": CFG["experiment_id"], "run_id": state["run_id"],
        "generation": state["generation"], "rule": RULE, "seed": SEED,
        "active": cells, "elapsed_before": elapsed_seconds(),
        "history": state["history"][-HISTORY_LIMIT:],
        "rows": state["rows"][-700:], "saved_at": time.time()
    }
    path = CHECK / f"checkpoint_{state['generation']:012d}_{state['run_id']}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(path)
    state["last_checkpoint"] = path.name
    state["event"] = f"Checkpoint saved at generation {state['generation']}"
    snapshot()
    return path.name

def restore_latest():
    files = sorted(CHECK.glob("checkpoint_*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        return False
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    state["active"] = set(map(int, payload["active"]))
    state["generation"] = int(payload["generation"])
    state["run_id"] = payload.get("run_id", str(uuid.uuid4())[:8])
    state["elapsed_before"] = float(payload.get("elapsed_before", 0.0))
    state["history"] = payload.get("history", [])[-HISTORY_LIMIT:]
    state["rows"] = payload.get("rows", [])[-700:]
    state["running"] = False
    state["started_at"] = None
    state["status"] = "PAUSED"
    state["event"] = f"Restored checkpoint: generation {state['generation']}"
    state["last_checkpoint"] = files[-1].name
    snapshot()
    return True

def elapsed_seconds():
    total = state["elapsed_before"]
    if state["running"] and state["started_at"] is not None:
        total += time.time() - state["started_at"]
    return total

def one_generation():
    old = state["active"]
    if not old:
        state["generation"] += 1
        state["status"] = "EXTINCT"
        state["running"] = False
        state["event"] = "Extinction: empty active configuration"
        return
    candidates = set()
    for x in old:
        candidates.add(x - 1)
        candidates.add(x)
        candidates.add(x + 1)
    new = set()
    for x in candidates:
        if rule_value(int(x - 1 in old), int(x in old), int(x + 1 in old)):
            new.add(x)
    state["active"] = new
    state["generation"] += 1
    if state["generation"] % OBS_EVERY == 0:
        add_observation()
        snapshot()
    if state["generation"] % CHECK_EVERY == 0:
        save_checkpoint()
    if not new:
        state["status"] = "EXTINCT"
        state["running"] = False
        state["event"] = "Extinction: no active cells remain"

def public_state():
    cells = state["active"]
    lo, hi, span = bounds(cells)
    return {
        "experiment": CFG["experiment_id"], "run_id": state["run_id"],
        "rule": RULE, "generation": state["generation"],
        "active_cells": len(cells), "components": component_count(cells),
        "span": span, "min_x": lo, "max_x": hi,
        "running": state["running"], "status": state["status"],
        "speed": state["speed"], "elapsed_seconds": round(elapsed_seconds(), 2),
        "event": state["event"], "error": state["error"],
        "history": state["history"][-500:], "rows": state["rows"][-500:],
        "positions": sorted(cells)[:100000], "truncated": len(cells) > 100000,
        "last_checkpoint": state["last_checkpoint"], "server_time": time.time()
    }

def worker():
    while True:
        with lock:
            if state["running"]:
                try:
                    # Bound each lock-held batch so HTTP telemetry/control stays responsive.
                    batch = min(max(1, state["speed"]), 20)
                    for _ in range(batch):
                        if not state["running"]:
                            break
                        one_generation()
                        if state["status"] == "EXTINCT":
                            break
                    if not state["running"] and state["started_at"] is not None:
                        state["elapsed_before"] += time.time() - state["started_at"]
                        state["started_at"] = None
                except Exception as exc:
                    state["running"] = False
                    state["status"] = "ERROR"
                    state["error"] = repr(exc)
                    state["event"] = "Engine error"
        time.sleep(0.001)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "observer"), **kwargs)
    def log_message(self, fmt, *args):
        pass
    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path.startswith("/api/state"):
            with lock:
                self._send_json(public_state())
            return
        if self.path.startswith("/api/checkpoints"):
            files = sorted(CHECK.glob("checkpoint_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            self._send_json({"checkpoints": [{"name": f.name, "bytes": f.stat().st_size} for f in files[:30]]})
            return
        if self.path == "/":
            self.path = "/index.html"
        super().do_GET()
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            action = body.get("action")
            with lock:
                if action == "start":
                    if state["status"] == "EXTINCT":
                        self._send_json({"ok": False, "message": "Universe extinct. Reset to start a new run."}); return
                    if not state["running"]:
                        state["running"] = True
                        state["status"] = "RUNNING"
                        state["started_at"] = time.time()
                        state["event"] = "Evolution resumed"
                elif action == "pause":
                    if state["running"] and state["started_at"] is not None:
                        state["elapsed_before"] += time.time() - state["started_at"]
                    state["running"] = False
                    state["started_at"] = None
                    if state["status"] != "EXTINCT":
                        state["status"] = "PAUSED"
                    state["event"] = "Evolution paused by observer"
                elif action == "step":
                    if not state["running"] and state["status"] != "EXTINCT":
                        one_generation()
                        if state["status"] != "EXTINCT":
                            state["status"] = "PAUSED"
                        state["event"] = f"Single generation advanced to {state['generation']}"
                elif action == "checkpoint":
                    name = save_checkpoint()
                    self._send_json({"ok": True, "message": "Checkpoint saved", "checkpoint": name, "state": public_state()}); return
                elif action == "restore":
                    if not restore_latest():
                        self._send_json({"ok": False, "message": "No checkpoint exists yet."}); return
                elif action == "speed":
                    value = int(body.get("value", state["speed"]))
                    state["speed"] = max(SPEED_MIN, min(SPEED_MAX, value))
                    state["event"] = f"Evolution batch set to {state['speed']}"
                elif action == "reset":
                    if state["running"] and state["started_at"] is not None:
                        state["elapsed_before"] += time.time() - state["started_at"]
                    state["running"] = False
                    state["started_at"] = None
                    # Preserve the previous state as a checkpoint before beginning a fresh run.
                    save_checkpoint()
                    state["active"] = make_initial()
                    state["generation"] = 0
                    state["elapsed_before"] = 0.0
                    state["history"] = []
                    state["rows"] = []
                    state["run_id"] = str(uuid.uuid4())[:8]
                    state["status"] = "READY"
                    state["error"] = None
                    state["event"] = "New run initialized; previous run checkpoint preserved"
                    add_observation()
                    snapshot()
                else:
                    self._send_json({"ok": False, "message": f"Unknown action: {action}"}); return
                self._send_json({"ok": True, "state": public_state()})
        except Exception as exc:
            self._send_json({"ok": False, "message": repr(exc)}, 500)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--fresh", action="store_true", help="Start from initial conditions instead of restoring a checkpoint")
    args = parser.parse_args()
    if args.fresh or not restore_latest():
        state["active"] = make_initial()
        state["generation"] = 0
        state["status"] = "READY"
        state["event"] = "Fresh universe initialized"
        state["history"] = []
        state["rows"] = []
        add_observation()
        snapshot()
    threading.Thread(target=worker, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    print(f"\nDSHADOW-CELLS-002 Observatory: http://127.0.0.1:{args.port}")
    print(f"Rule {RULE} | unbounded 1D integer lattice | sparse storage")
    print(f"Initial generation: {state['generation']} | speed batch: {state['speed']}/{SPEED_MAX}")
    print("Ctrl+C pauses and checkpoints the universe before shutdown.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutdown requested. Saving checkpoint...")
    finally:
        with lock:
            if state["running"] and state["started_at"] is not None:
                state["elapsed_before"] += time.time() - state["started_at"]
            state["running"] = False
            state["started_at"] = None
            state["status"] = "PAUSED"
            try:
                save_checkpoint()
            except Exception as exc:
                print("Checkpoint warning:", repr(exc))
        server.server_close()
        print("Universe paused. Checkpoint saved where possible.")

if __name__ == "__main__":
    main()
'@
Set-Content (Join-Path $base "engine\dshadow_engine.py") $engine -Encoding UTF8

$html = @'
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSHADOW-CELLS 002 | Observatory</title>
<style>
:root{--bg:#080d16;--side:#0b1320;--panel:#101b2b;--panel2:#0b1421;--line:#2a3d56;--text:#e8effa;--muted:#91a2b9;--cyan:#55e1df;--gold:#d9b76d;--blue:#526cf0;--green:#27d6a0;--red:#ff7189}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 60% 0%,#172941 0%,var(--bg) 60%);color:var(--text);font:14px/1.45 "Segoe UI",Arial,sans-serif}.app{min-height:100vh;display:grid;grid-template-columns:230px minmax(0,1fr)}aside.sidebar{background:var(--side);border-right:1px solid var(--line);padding:25px 15px}.brand{font-size:23px;font-weight:800;letter-spacing:4px}.brand small{display:block;color:var(--gold);font-size:10px;letter-spacing:4px}.navlabel{margin:40px 10px 10px;color:#71849e;font-size:10px;letter-spacing:2px}.nav a{display:block;color:#b6c4d8;text-decoration:none;padding:12px 11px;margin:5px 0;border-radius:8px;border:1px solid transparent}.nav a:hover,.nav a.active{background:#1a2b4d;border-color:#304a75;color:#c7d4ff}.side-note{margin:40px 8px 0;color:#71849e;font-size:11px}main{padding:22px 25px;min-width:0}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;gap:12px}.eyebrow{font-size:10px;color:#91a8ff;letter-spacing:3px}.title{font-size:25px;font-weight:750}.conn{font-size:12px;color:var(--green);white-space:nowrap}.conn.bad{color:var(--red)}.grid{display:grid;grid-template-columns:minmax(0,1fr) 255px;gap:14px}.card{background:linear-gradient(145deg,#101b2b,#0b1420);border:1px solid var(--line);border-radius:12px;min-width:0}.head{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;border-bottom:1px solid #26384f}.pill{border:1px solid #3c647c;color:var(--cyan);border-radius:20px;padding:4px 10px;font-size:10px}.view{height:410px;position:relative;background:#060c15;overflow:hidden}.view canvas{width:100%;height:100%;display:block}.overlay{position:absolute;left:14px;bottom:13px;background:#0a1322e8;border:1px solid #39516c;border-radius:8px;padding:9px 12px;font-size:11px;line-height:1.8}.right{padding:15px}.right h3{margin:0 0 10px}.row{display:flex;justify-content:space-between;gap:8px;padding:9px 0;border-bottom:1px solid #26364b;font-size:12px;color:var(--muted)}.row b{color:var(--text);text-align:right;font-variant-numeric:tabular-nums}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px;margin:14px 0}.metric{padding:14px}.metric label{display:block;color:var(--muted);font-size:10px;letter-spacing:1px}.metric strong{display:block;font-size:23px;margin:6px 0;font-variant-numeric:tabular-nums}.metric small{font-size:10px;color:var(--gold)}.controls{padding:15px;margin-bottom:14px}.buttons{display:flex;flex-wrap:wrap;gap:8px}.btn{min-height:40px;border:1px solid #3b506b;background:#17253a;color:#e5edf9;border-radius:8px;padding:9px 13px;font-weight:650;cursor:pointer}.btn.primary{background:#465fe0;border-color:#647cff}.btn:hover{filter:brightness(1.15)}.btn:focus-visible,a:focus-visible,input:focus-visible{outline:2px solid var(--gold);outline-offset:2px}.speed{display:flex;align-items:center;gap:12px;margin-top:14px;flex-wrap:wrap;color:var(--muted)}.speed input{width:min(420px,60%);accent-color:var(--blue)}.speed b{color:var(--gold)}.section{margin:15px 0;scroll-margin-top:12px}.section-head{display:flex;justify-content:space-between;align-items:center;padding:14px 16px}.section-head small{color:var(--muted)}.canvasbox{height:260px;padding:0 12px 12px}.canvasbox canvas{width:100%;height:100%;display:block;background:#070d17;border-radius:7px}.lower{display:grid;grid-template-columns:1fr 1fr;gap:14px}.chart{padding:15px;min-height:200px}.bars{display:flex;align-items:end;gap:2px;height:125px;margin-top:14px}.bar{flex:1;min-width:2px;background:linear-gradient(0deg,#4059d1,#55e1df);border-radius:2px 2px 0 0}.log{height:145px;overflow:auto;font:11px/1.8 Consolas,monospace;color:#aebed2}.checkpoint-list{font-size:12px;color:var(--muted);max-height:160px;overflow:auto}.checkpoint-list div{padding:7px;border-bottom:1px solid #25364b}.foot{font-size:10px;color:#71849e;margin:13px 0}.toast{position:sticky;bottom:10px;margin-top:10px;padding:9px 12px;background:#14243a;border:1px solid #45617f;border-radius:8px;color:#dce8fa;display:none}.toast.show{display:block}
@media(max-width:1050px){.app{grid-template-columns:190px minmax(0,1fr)}.grid{grid-template-columns:1fr}.right{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 15px}.right h3,.right p{grid-column:1/-1}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:720px){.app{grid-template-columns:1fr}.sidebar{padding:12px!important}.nav{display:flex;overflow-x:auto;gap:4px}.navlabel,.side-note{display:none}.nav a{white-space:nowrap;padding:9px}.brand{font-size:18px}main{padding:13px}.title{font-size:20px}.view{height:310px}.lower{grid-template-columns:1fr}.right{grid-template-columns:1fr 1fr}.top{align-items:flex-start}.metrics{gap:8px}.metric strong{font-size:20px}}
</style>
</head>
<body>
<div class="app">
<aside class="sidebar">
  <div class="brand">DSHADOW<small>CELLS OBSERVATORY</small></div>
  <div class="navlabel">OBSERVATION</div>
  <nav class="nav">
    <a class="active" href="#live">◈ &nbsp; Live Universe</a>
    <a href="#spacetime">▦ &nbsp; Space-Time Evolution</a>
    <a href="#metrics">◷ &nbsp; Evolution Metrics</a>
    <a href="#research">⌘ &nbsp; Research Log</a>
    <a href="#checkpoints">⬡ &nbsp; Checkpoints</a>
  </nav>
  <div class="side-note">DARKSHADOWS GROUP<br>EXTERNAL OBSERVER<br>EXPERIMENT 002</div>
</aside>
<main>
  <div class="top"><div><div class="eyebrow">DSHADOW-CELLS / EXPERIMENT 002</div><div class="title">Live Operations &amp; Control</div></div><div id="connection" class="conn">● CONNECTING</div></div>
  <section id="live" class="grid">
    <div class="card">
      <div class="head"><b>LIVE UNIVERSE — ACTUAL CELL CONFIGURATION</b><span class="pill" id="runstate">INITIALIZING</span></div>
      <div class="view"><canvas id="liveCanvas" aria-label="Current active cell positions"></canvas><div class="overlay">RULE <b>110</b><br>GENERATION <b id="smallGen">0</b><br>SPACE <b>UNBOUNDED</b></div></div>
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
      <p class="foot">Observer externo. No introduce células, selección ni reproducción artificial.</p>
    </aside>
  </section>
  <section id="metrics" class="metrics">
    <div class="card metric"><label>UNIVERSE TIME</label><strong id="generation">0</strong><small>GENERATIONS</small></div>
    <div class="card metric"><label>ACTIVE CELLS</label><strong id="activeCells">0</strong><small>STATE = 1</small></div>
    <div class="card metric"><label>STRUCTURAL COMPONENTS</label><strong id="components">0</strong><small>CONTIGUOUS GROUPS</small></div>
    <div class="card metric"><label>OBSERVER TIME</label><strong id="elapsed">0 s</strong><small>REAL ELAPSED TIME</small></div>
  </section>
  <section class="card controls">
    <div class="head" style="padding:0 0 13px;border:0"><b>EVOLUTION CONTROL</b><span class="pill">EXTERNAL OBSERVER</span></div>
    <div class="buttons">
      <button class="btn primary" data-action="start">▶ START UNIVERSE</button>
      <button class="btn" data-action="pause">Ⅱ PAUSE</button>
      <button class="btn" data-action="step">＋ SINGLE GENERATION</button>
      <button class="btn" data-action="checkpoint">▣ SAVE CHECKPOINT</button>
      <button class="btn" data-action="restore">↶ RESTORE LATEST</button>
      <button class="btn" data-action="reset">↻ NEW UNIVERSE</button>
    </div>
    <div class="speed">EVOLUTION SPEED <input id="speedSlider" type="range" min="1" max="500" value="500"><b id="speedLabel">500 / 500 — MAX REQUESTED BATCH</b></div>
    <div class="foot">La escala regula el tamaño del lote de generaciones solicitado al motor. La velocidad real depende del hardware y de la complejidad del estado.</div>
  </section>
  <section id="spacetime" class="card section">
    <div class="section-head"><b>SPACE-TIME EVOLUTION</b><small>Filas = observaciones sucesivas · píxeles = células activas muestreadas</small></div>
    <div class="canvasbox"><canvas id="timeCanvas" aria-label="Space-time raster of observed cellular evolution"></canvas></div>
  </section>
  <section class="lower">
    <div class="card chart"><b>EVOLUTION TRACE</b><div class="foot">Active cells and structural components sampled every 10 generations.</div><div class="bars" id="bars"></div></div>
    <section id="research" class="card chart"><b>RESEARCH EVENT LOG</b><div class="log" id="log" aria-live="polite">[SYSTEM] Observatory ready.<br>[SYSTEM] Waiting for telemetry…</div></section>
  </section>
  <section id="checkpoints" class="card section">
    <div class="section-head"><b>CHECKPOINT ARCHIVE</b><button class="btn" id="refreshCheckpoints">↻ REFRESH LIST</button></div>
    <div class="checkpoint-list" id="checkpointList">Checkpoint list not loaded.</div>
  </section>
  <div class="foot">DSHADOW-CELLS-002 • Rule 110 • Unbounded integer lattice represented with sparse active coordinates. Physical memory and processing remain finite. No claim of biological life is implied.</div>
  <div id="toast" class="toast" role="status" aria-live="polite"></div>
</main>
</div>
<script>
(() => {
"use strict";
const $ = id => document.getElementById(id);
const liveCanvas = $("liveCanvas"), liveCtx = liveCanvas.getContext("2d");
const timeCanvas = $("timeCanvas"), timeCtx = timeCanvas.getContext("2d");
let latest = null, lastLoggedEvent = "", pollTimer = null, busy = false;
const number = n => Number(n || 0).toLocaleString("en-US");
function toast(message){const t=$("toast");t.textContent=message;t.classList.add("show");clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.classList.remove("show"),4000);}
function fitCanvas(canvas,ctx){const r=canvas.getBoundingClientRect(),d=window.devicePixelRatio||1;canvas.width=Math.max(1,Math.floor(r.width*d));canvas.height=Math.max(1,Math.floor(r.height*d));ctx.setTransform(d,0,0,d,0,0);}
function resize(){fitCanvas(liveCanvas,liveCtx);fitCanvas(timeCanvas,timeCtx);drawAll();}
window.addEventListener("resize",resize);
function drawLive(s){
 const w=liveCanvas.clientWidth,h=liveCanvas.clientHeight;liveCtx.clearRect(0,0,w,h);
 liveCtx.fillStyle="#060c15";liveCtx.fillRect(0,0,w,h);
 liveCtx.strokeStyle="rgba(120,160,205,.10)";liveCtx.lineWidth=1;
 for(let x=0;x<w;x+=40){liveCtx.beginPath();liveCtx.moveTo(x,0);liveCtx.lineTo(x,h);liveCtx.stroke();}
 for(let y=0;y<h;y+=40){liveCtx.beginPath();liveCtx.moveTo(0,y);liveCtx.lineTo(w,y);liveCtx.stroke();}
 const p=s.positions||[]; if(!p.length){liveCtx.fillStyle="#93a7c0";liveCtx.font="13px Segoe UI";liveCtx.fillText("No active cells in current state",20,30);return;}
 const lo=s.min_x, hi=s.max_x, span=Math.max(1,hi-lo+1), pad=22, usable=w-pad*2;
 const cellW=Math.max(1,Math.min(7,usable/Math.min(span,usable/2)));
 const y0=h*.48, yStep=Math.max(2,Math.min(8,(h-50)/Math.max(1,Math.ceil(p.length/Math.max(1,usable/cellW)))));
 // Display a deterministic spatial projection: x encodes lattice coordinate; rows separate crowded samples.
 const maxCols=Math.max(1,Math.floor(usable/Math.max(1,cellW)));
 for(let i=0;i<p.length;i++){
   const x=pad+((p[i]-lo)/Math.max(1,span-1))*usable;
   const row=i%Math.max(1,Math.floor((h-36)/3));
   const y=18+(row*3)%(h-36);
   liveCtx.fillStyle="#55e1df";liveCtx.shadowColor="#35d9e4";liveCtx.shadowBlur=5;
   liveCtx.fillRect(x,y,Math.max(1.8,cellW),Math.max(2,cellW));
 }
 liveCtx.shadowBlur=0;
 if(s.truncated){liveCtx.fillStyle="#d9b76d";liveCtx.font="11px Segoe UI";liveCtx.fillText("DISPLAY SAMPLE LIMITED — ENGINE STATE NOT TRUNCATED",14,18);}
}
function drawTime(s){
 const w=timeCanvas.clientWidth,h=timeCanvas.clientHeight;timeCtx.clearRect(0,0,w,h);timeCtx.fillStyle="#070d17";timeCtx.fillRect(0,0,w,h);
 const rows=s.rows||[]; if(!rows.length){timeCtx.fillStyle="#91a2b9";timeCtx.font="13px Segoe UI";timeCtx.fillText("Waiting for first space-time observations…",18,28);return;}
 const rowH=Math.max(1,h/Math.max(1,rows.length));const pixelW=w/720;
 rows.forEach((item,ri)=>{
   const y=h-(rows.length-ri)*rowH;const bits=item.bits||"";
   for(let x=0;x<bits.length;x++){if(bits[x]==="1"){timeCtx.fillStyle=`hsl(${180+Math.min(35,ri/rows.length*35)} 75% ${48+ri/rows.length*12}%)`;timeCtx.fillRect(x*pixelW,y,Math.ceil(pixelW),Math.max(1,rowH));}}
 });
 timeCtx.fillStyle="#d9b76d";timeCtx.font="10px Segoe UI";timeCtx.fillText(`GEN ${number(rows[0].generation)}`,8,12);timeCtx.fillText(`GEN ${number(rows[rows.length-1].generation)}`,8,h-4);
}
function drawBars(s){
 const host=$("bars");host.innerHTML="";const hist=(s.history||[]).slice(-100);if(!hist.length)return;
 const max=Math.max(1,...hist.map(x=>x.active));hist.forEach(x=>{const b=document.createElement("div");b.className="bar";b.style.height=(5+115*x.active/max)+"px";b.title=`Generation ${number(x.generation)} · ${number(x.active)} active · ${number(x.components)} components`;host.appendChild(b);});
}
function drawAll(){if(!latest)return;drawLive(latest);drawTime(latest);drawBars(latest);}
function update(s){
 latest=s;
 $("connection").textContent="● CONNECTED";$("connection").classList.remove("bad");
 $("runstate").textContent=s.running?"EVOLUTION RUNNING":s.status;
 $("engineStatus").textContent=s.status;
 $("generation").textContent=number(s.generation);$("smallGen").textContent=number(s.generation);
 $("activeCells").textContent=number(s.active_cells);$("activeSide").textContent=number(s.active_cells);
 $("components").textContent=number(s.components);$("componentsSide").textContent=number(s.components);
 $("spanSide").textContent=number(s.span);$("boundsSide").textContent=number(s.min_x)+" / "+number(s.max_x);
 $("elapsed").textContent=Number(s.elapsed_seconds||0).toFixed(1)+" s";$("elapsedSide").textContent=Number(s.elapsed_seconds||0).toFixed(1)+" s";
 $("lastEvent").textContent=s.event||"—";
 if(s.event && s.event!==lastLoggedEvent){lastLoggedEvent=s.event;const log=$("log");const line=document.createElement("div");line.textContent=`[${new Date().toLocaleTimeString()}] ${s.event}`;log.prepend(line);while(log.children.length>60)log.lastChild.remove();}
 drawAll();
}
async function api(action,extra={}){
 if(busy){toast("A command is already being processed.");return;}
 busy=true;
 try{
   const response=await fetch("/api/control",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action,...extra})});
   if(!response.ok)throw new Error(`HTTP ${response.status}`);
   const result=await response.json();
   if(!result.ok)throw new Error(result.message||"Command rejected");
   if(result.state)update(result.state);
   toast(result.message||({start:"Evolution started",pause:"Evolution paused",step:"One generation advanced",restore:"Checkpoint restored",reset:"New universe initialized",speed:"Speed updated"}[action]||"Command completed"));
 }catch(e){toast("Command failed: "+e.message);}
 finally{busy=false;}
}
document.querySelectorAll("[data-action]").forEach(button=>{
 button.addEventListener("click",()=>{
   const action=button.dataset.action;
   if(action==="reset"&&!confirm("Start a new universe? The current state will first be saved as a checkpoint."))return;
   api(action);
 });
});
$("speedSlider").addEventListener("input",e=>{$("speedLabel").textContent=e.target.value+" / 500 — MAX REQUESTED BATCH";});
$("speedSlider").addEventListener("change",e=>api("speed",{value:Number(e.target.value)}));
async function loadCheckpoints(){
 try{const r=await fetch("/api/checkpoints?"+Date.now());const j=await r.json();const host=$("checkpointList");host.innerHTML="";
 if(!j.checkpoints.length){host.textContent="No checkpoints saved yet.";return;}
 j.checkpoints.forEach(c=>{const row=document.createElement("div");row.textContent=`${c.name} · ${(c.bytes/1024).toFixed(1)} KB`;host.appendChild(row);});
 }catch(e){$("checkpointList").textContent="Unable to load checkpoint archive.";}
}
$("refreshCheckpoints").addEventListener("click",loadCheckpoints);
async function poll(){
 try{const r=await fetch("/api/state?"+Date.now(),{cache:"no-store"});if(!r.ok)throw new Error("HTTP "+r.status);const s=await r.json();update(s);}
 catch(e){$("connection").textContent="● DISCONNECTED";$("connection").classList.add("bad");}
 pollTimer=setTimeout(poll,500);
}
document.querySelectorAll(".nav a").forEach(a=>a.addEventListener("click",()=>{document.querySelectorAll(".nav a").forEach(x=>x.classList.remove("active"));a.classList.add("active");}));
resize();loadCheckpoints();poll();
})();
</script>
</body></html>
'@
Set-Content (Join-Path $base "observer\index.html") $html -Encoding UTF8

$readme = @'
# DSHADOW-CELLS-002 — THE UNBOUNDED OBSERVATORY

## Start
From this directory:
`python engine\dshadow_engine.py`

Open `http://127.0.0.1:8765`.

The engine restores the most recent checkpoint automatically when one exists. To deliberately start fresh, use:
`python engine\dshadow_engine.py --fresh`

## Controls
- Start / Pause
- Single Generation (only while paused)
- Save Checkpoint
- Restore Latest
- New Universe (asks for confirmation and saves the current state first)
- Evolution speed slider: 1–500 requested generations per worker batch

## Visualization
- Live Universe: current active coordinates projected into the viewport.
- Space-Time Evolution: successive spatial samples from actual states.
- Evolution Trace: active-cell history.
- Research Event Log and checkpoint archive.

## Model and limits
Rule 110, one-dimensional binary elementary cellular automaton, synchronous updates, sparse representation of an unbounded integer lattice. The zero neighborhood remains zero, so finite-support states can be stored sparsely.

The lattice has no predefined spatial boundary and the run has no target generation count. Hardware memory, CPU time and storage remain finite. The speed control sets a requested batch size; it does not promise a fixed generations-per-second rate.

This is a computational experiment, not evidence of biological life. Persistence, recurrence, complexity or pattern resemblance alone do not establish reproduction, heredity or evolution by natural selection.
'@
Set-Content (Join-Path $base "README.md") $readme -Encoding UTF8

$protocol = @'
# DSHADOW-CELLS-002 — Experimental Protocol

Premise: observe the autonomous evolution of a deterministic cellular substrate without prescribing organisms, reproduction, selection or goals.

Model: Rule 110 on a one-dimensional unbounded integer lattice with binary states, synchronous updates and sparse active-coordinate storage.

Observer: read-only with respect to cell states. It displays actual states and sampled histories; controls only start, pause, advance, checkpoint, restore, reset and requested batch size.

Measurements: generation, active cells, contiguous components, occupied span, coordinate bounds and elapsed wall-clock time.

Space-time display: each row is a sampled spatial representation of an observed state. It is a visualization, not an additional rule or substrate.

Scientific safeguards:
- Persistence is not life.
- Similarity is not inheritance.
- A split is not reproduction.
- Complexity is not adaptation.
- Rule 110 is deterministic; observed growth does not establish biological evolution.
- Physical resources remain finite even when the mathematical lattice is unbounded.
'@
Set-Content (Join-Path $base "research\RESEARCH_PROTOCOL.md") $protocol -Encoding UTF8

Write-Host "`n====================================================" -ForegroundColor Cyan
Write-Host " DSHADOW-CELLS-002 BUILT SUCCESSFULLY" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Path: $base" -ForegroundColor Yellow
Write-Host "`nNEXT COMMANDS:" -ForegroundColor Cyan
Write-Host "  cd `"$base`"" -ForegroundColor Yellow
Write-Host "  python engine\dshadow_engine.py" -ForegroundColor Yellow
Write-Host "  Open http://127.0.0.1:8765" -ForegroundColor Yellow
Write-Host "`nDefault speed: 500/500 requested batch (maximum)." -ForegroundColor Green
Write-Host "Existing DSHADOW-CELLS-001 has not been overwritten." -ForegroundColor DarkYellow

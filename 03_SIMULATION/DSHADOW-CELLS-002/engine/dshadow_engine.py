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

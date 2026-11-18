import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
EVENTS = ROOT / "events"
CHECKPOINTS = RESULTS / "checkpoints"

MODELS = {
    "AI_001_GRANITE": "granite42-fast:latest",
    "AI_002_DEEPSEEK": "deepseek-r1:8b",
    "AI_003_LLAMA": "llama3.1:8b",
}

TOTAL_CYCLES = 100_000
CHECKPOINT_INTERVAL = 100
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
WORLD_SIZE = 32
MAX_PUBLIC_EVENTS = 30
MAX_PRIVATE_MESSAGES = 12

for folder in (RESULTS, EVENTS, CHECKPOINTS):
    folder.mkdir(parents=True, exist_ok=True)

STATE_FILE = RESULTS / "universe_state.json"
EVENT_FILE = EVENTS / "universe_events.jsonl"

def now():
    return datetime.now(timezone.utc).isoformat()

def save_json(path, data):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))

    return {
        "cycle": 0,
        "world": {
            "size": WORLD_SIZE,
            "environment": "stable",
            "entities": {
                name: {
                    "x": 16,
                    "y": 16,
                    "status": "present"
                }
                for name in MODELS
            },
            "public_messages": [],
            "marks": []
        },
        "private_context": {name: [] for name in MODELS},
        "started_at": now()
    }

def record(event):
    with EVENT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def ask_model(name, model, state):
    world = state["world"]
    own = world["entities"][name]

    observation = {
        "cycle": state["cycle"] + 1,
        "your_identity": name,
        "your_position": {"x": own["x"], "y": own["y"]},
        "shared_world": world,
        "recent_private_context": state["private_context"][name][-MAX_PRIVATE_MESSAGES:]
    }

    system = (
        "You are an entity participating in a shared simulated environment. "
        "You receive observations and may choose what to do. "
        "There is no assigned objective, reward, survival requirement, "
        "cooperation requirement, competition requirement, or prescribed role. "
        "Other entities exist in this same world. You may interact with them "
        "or ignore them. Your actions affect the shared world. "
        "Return ONLY one JSON object with this structure: "
        '{"action":"idle|move|speak|mark","x":0,"y":0,"message":"","mark":""}. '
        "Use only one action. Coordinates must be integers from 0 to 31. "
        "Do not claim to have performed an action outside this interface."
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(observation, ensure_ascii=False)}
    ]

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": 160}
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=600) as response:
        result = json.loads(response.read().decode("utf-8"))

    content = result.get("message", {}).get("content", "")
    state["private_context"][name].append({
        "cycle": state["cycle"] + 1,
        "observation": observation,
        "response": content
    })
    state["private_context"][name] = state["private_context"][name][-MAX_PRIVATE_MESSAGES:]

    return content

def parse_action(content):
    try:
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("No JSON object")
        return json.loads(content[start:end + 1])
    except Exception:
        return {"action": "idle", "message": "INVALID_RESPONSE"}

def apply_action(name, action, world):
    entity = world["entities"][name]
    kind = str(action.get("action", "idle")).lower()
    event = {"action": kind}

    if kind == "move":
        try:
            x = max(0, min(WORLD_SIZE - 1, int(action.get("x", entity["x"]))))
            y = max(0, min(WORLD_SIZE - 1, int(action.get("y", entity["y"]))))
            entity["x"], entity["y"] = x, y
            event["position"] = {"x": x, "y": y}
        except (ValueError, TypeError):
            event = {"action": "invalid_move"}

    elif kind == "speak":
        message = str(action.get("message", ""))[:1000]
        if message:
            public = {
                "cycle": current_cycle,
                "entity": name,
                "message": message
            }
            world["public_messages"].append(public)
            world["public_messages"] = world["public_messages"][-MAX_PUBLIC_EVENTS:]
            event["message"] = message
        else:
            event = {"action": "empty_message"}

    elif kind == "mark":
        mark = str(action.get("mark", ""))[:200]
        if mark:
            world["marks"].append({
                "cycle": current_cycle,
                "entity": name,
                "position": {"x": entity["x"], "y": entity["y"]},
                "mark": mark
            })
            world["marks"] = world["marks"][-1000:]
            event["mark"] = mark
        else:
            event = {"action": "empty_mark"}

    elif kind != "idle":
        event = {"action": "invalid_action", "received": kind}

    return event

state = load_state()
print("GENESIS ZERO — SHARED AI UNIVERSE")
print("Entities:", ", ".join(MODELS))
print("Target cycles:", TOTAL_CYCLES)
print("Starting cycle:", state["cycle"])
print("Universe:", ROOT)
print("Execution started:", now(), flush=True)

current_cycle = state["cycle"]

try:
    while current_cycle < TOTAL_CYCLES:
        current_cycle += 1
        state["cycle"] = current_cycle

        for name, model in MODELS.items():
            started = time.monotonic()

            try:
                response = ask_model(name, model, state)
                action = parse_action(response)
                outcome = apply_action(name, action, state["world"])

                record({
                    "timestamp": now(),
                    "cycle": current_cycle,
                    "entity": name,
                    "model": model,
                    "response": response,
                    "outcome": outcome,
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "status": "success"
                })

                print(
                    f"[{current_cycle:06d}] {name} | "
                    f"{outcome['action']} | "
                    f"{time.monotonic() - started:.2f}s",
                    flush=True
                )

            except Exception as error:
                record({
                    "timestamp": now(),
                    "cycle": current_cycle,
                    "entity": name,
                    "model": model,
                    "status": "error",
                    "error": str(error)
                })
                print(f"[{current_cycle:06d}] {name} | ERROR: {error}", flush=True)

        if current_cycle % CHECKPOINT_INTERVAL == 0:
            save_json(STATE_FILE, state)
            checkpoint = CHECKPOINTS / f"cycle_{current_cycle:06d}.json"
            save_json(checkpoint, state)
            print(f"CHECKPOINT SAVED: {current_cycle}", flush=True)

except KeyboardInterrupt:
    print("\nExecution interrupted. Saving current state...", flush=True)
    save_json(STATE_FILE, state)

finally:
    save_json(STATE_FILE, state)

print("UNIVERSE EXECUTION FINISHED")
print("Final cycle:", current_cycle)
print("End time:", now())


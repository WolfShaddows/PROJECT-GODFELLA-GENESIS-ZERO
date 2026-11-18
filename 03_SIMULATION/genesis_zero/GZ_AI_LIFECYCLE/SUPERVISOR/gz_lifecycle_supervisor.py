import csv
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "SUPERVISOR_TESTS"

DURATION_SECONDS = 120
INTERVAL_SECONDS = 5
API_URL = "http://127.0.0.1:11434/api/ps"

run_id = datetime.now().strftime("GZ_SUPERVISOR_%Y%m%d_%H%M%S")
run_dir = RESULTS / run_id
run_dir.mkdir(parents=True, exist_ok=False)

csv_path = run_dir / "system_observations.csv"
jsonl_path = run_dir / "observations.jsonl"
summary_path = run_dir / "run_summary.json"

def timestamp():
    return datetime.now(timezone.utc).isoformat()

def get_ollama_status():
    request = urllib.request.Request(
        API_URL,
        headers={"Accept": "application/json"},
        method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {
                "available": True,
                "loaded_models": payload.get("models", []),
                "error": None
            }
    except Exception as exc:
        return {
            "available": False,
            "loaded_models": [],
            "error": str(exc)
        }

def get_processes():
    try:
        import psutil
    except ImportError:
        raise RuntimeError(
            "Falta psutil. Instalar con: python -m pip install psutil"
        )

    processes = []
    for proc in psutil.process_iter(
        ["pid", "name", "cpu_times", "memory_info", "create_time"]
    ):
        try:
            name = (proc.info["name"] or "").lower()
            if "ollama" not in name:
                continue

            cpu = proc.info["cpu_times"]
            memory = proc.info["memory_info"]

            processes.append({
                "pid": proc.info["pid"],
                "name": proc.info["name"],
                "cpu_seconds": cpu.user + cpu.system,
                "rss_bytes": memory.rss,
                "create_time": proc.info["create_time"]
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return processes

observations = []
start = time.monotonic()
deadline = start + DURATION_SECONDS
sample = 0

print("GZ-AI-LIFECYCLE SUPERVISOR v0.1")
print("PASSIVE OBSERVATION — NO MODEL PROMPTS")
print(f"Run: {run_id}")
print(f"Duration: {DURATION_SECONDS} seconds")
print(f"Interval: {INTERVAL_SECONDS} seconds")
print("-" * 60)

with csv_path.open("w", newline="", encoding="utf-8") as csvfile:
    fields = [
        "timestamp_utc", "sample", "ollama_available",
        "ollama_process_count", "ollama_rss_bytes",
        "ollama_cpu_seconds", "loaded_model_count", "error"
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fields)
    writer.writeheader()

    with jsonl_path.open("w", encoding="utf-8") as jsonfile:
        while time.monotonic() < deadline:
            now = timestamp()
            processes = get_processes()
            ollama = get_ollama_status()

            record = {
                "timestamp_utc": now,
                "sample": sample,
                "ollama_available": ollama["available"],
                "ollama_processes": processes,
                "ollama_process_count": len(processes),
                "ollama_rss_bytes": sum(
                    p["rss_bytes"] for p in processes
                ),
                "ollama_cpu_seconds": sum(
                    p["cpu_seconds"] for p in processes
                ),
                "loaded_models": ollama["loaded_models"],
                "loaded_model_count": len(ollama["loaded_models"]),
                "api_error": ollama["error"]
            }

            observations.append(record)
            jsonfile.write(json.dumps(record, ensure_ascii=False) + "\n")
            jsonfile.flush()

            writer.writerow({
                "timestamp_utc": now,
                "sample": sample,
                "ollama_available": ollama["available"],
                "ollama_process_count": record["ollama_process_count"],
                "ollama_rss_bytes": record["ollama_rss_bytes"],
                "ollama_cpu_seconds": record["ollama_cpu_seconds"],
                "loaded_model_count": record["loaded_model_count"],
                "error": ollama["error"]
            })
            csvfile.flush()

            print(
                f"[{sample:03}] "
                f"API={ollama['available']} | "
                f"Processes={record['ollama_process_count']} | "
                f"RAM={record['ollama_rss_bytes'] / 1024**2:.1f} MB | "
                f"Loaded models={record['loaded_model_count']}"
            )

            sample += 1
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(INTERVAL_SECONDS, remaining))

summary = {
    "experiment": "GZ-AI-LIFECYCLE",
    "component": "SUPERVISOR",
    "version": "0.1",
    "run_id": run_id,
    "start_utc": observations[0]["timestamp_utc"] if observations else None,
    "end_utc": observations[-1]["timestamp_utc"] if observations else None,
    "samples": len(observations),
    "duration_seconds": DURATION_SECONDS,
    "ollama_api_available_samples": sum(
        1 for x in observations if x["ollama_available"]
    ),
    "loaded_model_observations": sum(
        x["loaded_model_count"] for x in observations
    ),
    "interpretation": (
        "Passive system observation only. "
        "No model prompts or model-loading requests were issued."
    )
}

summary_path.write_text(
    json.dumps(summary, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("-" * 60)
print("SUPERVISOR TEST COMPLETED")
print(json.dumps(summary, indent=2, ensure_ascii=False))
print(f"Evidence directory: {run_dir}")

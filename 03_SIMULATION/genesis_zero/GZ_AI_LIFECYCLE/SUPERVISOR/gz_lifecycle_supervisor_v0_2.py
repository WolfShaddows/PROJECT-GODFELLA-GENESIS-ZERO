import argparse
import csv
import hashlib
import json
import os
import platform
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import psutil


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def ollama_models():
    try:
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/ps",
            method="GET"
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.loads(response.read().decode("utf-8")), None
    except Exception as exc:
        return None, str(exc)


def discover_processes():
    processes = list(psutil.process_iter(
        ["pid", "ppid", "name", "create_time"]
    ))

    by_pid = {}
    for proc in processes:
        try:
            info = proc.info
            by_pid[info["pid"]] = {
                "pid": info["pid"],
                "ppid": info["ppid"],
                "name": info["name"] or "",
                "create_time": info["create_time"],
                "process": proc
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    roots = [
        pid for pid, item in by_pid.items()
        if "ollama" in item["name"].lower()
    ]

    selected = set(roots)
    changed = True

    while changed:
        changed = False
        for pid, item in by_pid.items():
            if pid not in selected and item["ppid"] in selected:
                selected.add(pid)
                changed = True

    return by_pid, selected, roots


def collect_process_metrics():
    by_pid, selected, roots = discover_processes()
    records = []

    for pid in sorted(selected):
        item = by_pid.get(pid)
        if not item:
            continue

        proc = item["process"]

        try:
            records.append({
                "pid": pid,
                "ppid": item["ppid"],
                "name": item["name"],
                "create_time": item["create_time"],
                "cpu_percent_interval": proc.cpu_percent(interval=None),
                "cpu_seconds_total": proc.cpu_times().user
                                    + proc.cpu_times().system,
                "rss_bytes": proc.memory_info().rss
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return records, roots


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=120)
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.duration < 10 or args.interval <= 0:
        raise SystemExit("Invalid duration or interval.")

    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)

    csv_path = output / "process_observations.csv"
    jsonl_path = output / "observations.jsonl"

    start = time.monotonic()
    deadline = start + args.duration
    sample_number = 0
    api_success = 0
    api_errors = 0
    observed_pids = set()
    observed_models = set()
    process_samples = 0
    errors = []

    system = psutil.virtual_memory()

    metadata = {
        "supervisor_version": "0.2",
        "start_utc": timestamp(),
        "duration_configured_seconds": args.duration,
        "interval_seconds": args.interval,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "psutil": psutil.__version__,
        "temperature_status": "not_measured",
        "temperature_reason": "No validated temperature sensor integration in v0.2",
        "api_endpoint": "GET http://127.0.0.1:11434/api/ps",
        "observer_mode": "passive_read_only"
    }

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file, \
         jsonl_path.open("w", encoding="utf-8") as jsonl_file:

        writer = csv.DictWriter(csv_file, fieldnames=[
            "sample", "timestamp_utc", "elapsed_seconds",
            "pid", "ppid", "name", "create_time",
            "cpu_percent_interval", "cpu_seconds_total", "rss_bytes",
            "system_cpu_percent", "system_ram_used_bytes",
            "system_ram_available_bytes"
        ])
        writer.writeheader()

        while time.monotonic() < deadline:
            sample_number += 1
            now = time.monotonic()
            elapsed = now - start

            model_data, api_error = ollama_models()

            if model_data is not None:
                api_success += 1
                models = model_data.get("models", [])
                for model in models:
                    name = model.get("name", "unknown")
                    observed_models.add(name)
            else:
                api_errors += 1
                errors.append(api_error)

            process_records, roots = collect_process_metrics()
            system_cpu = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()

            event = {
                "sample": sample_number,
                "timestamp_utc": timestamp(),
                "elapsed_seconds": round(elapsed, 3),
                "ollama_root_pids": roots,
                "processes": process_records,
                "api_available": model_data is not None,
                "api_error": api_error,
                "loaded_models": (
                    model_data.get("models", [])
                    if model_data is not None else None
                ),
                "system_cpu_percent": system_cpu,
                "system_ram_used_bytes": memory.used,
                "system_ram_available_bytes": memory.available
            }

            jsonl_file.write(json.dumps(event, ensure_ascii=False) + "\n")
            jsonl_file.flush()

            for proc in process_records:
                writer.writerow({
                    "sample": sample_number,
                    "timestamp_utc": event["timestamp_utc"],
                    "elapsed_seconds": event["elapsed_seconds"],
                    **proc,
                    "system_cpu_percent": system_cpu,
                    "system_ram_used_bytes": memory.used,
                    "system_ram_available_bytes": memory.available
                })
                observed_pids.add(proc["pid"])
                process_samples += 1

            csv_file.flush()

            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(args.interval, remaining))

    end = time.monotonic()

    summary = {
        **metadata,
        "end_utc": timestamp(),
        "elapsed_actual_seconds": round(end - start, 3),
        "samples": sample_number,
        "api_success_samples": api_success,
        "api_error_samples": api_errors,
        "observed_pids": sorted(observed_pids),
        "observed_models": sorted(observed_models),
        "process_records": process_samples,
        "temperature_status": "not_measured",
        "errors": errors
    }

    summary_path = output / "run_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    evidence_files = [
        csv_path,
        jsonl_path,
        summary_path
    ]

    manifest = {
        "algorithm": "SHA256",
        "files": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in evidence_files
        }
    }

    manifest_path = output / "SHA256SUMS.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("\nEvidence:", output)
    print("SHA256 manifest:", manifest_path)


if __name__ == "__main__":
    main()

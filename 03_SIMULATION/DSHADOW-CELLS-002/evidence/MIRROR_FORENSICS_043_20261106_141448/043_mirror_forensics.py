import os
import json
import csv
import hashlib
import time
from pathlib import Path

import numpy as np

START_TIME = time.time()

MATRIX_PATH = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION"
    r"\DSHADOW-CELLS-002\evidence\SPACETIME_038_20261106_102543"
    r"\038_spacetime_matrix.npz"
)

OUT = Path(os.environ["GODFELLA_043_OUT"])

TARGET = 6400
WINDOW = 1792
SECTOR = 256

RULE110 = np.array(
    [0, 1, 1, 1, 0, 1, 1, 0],
    dtype=np.uint8
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def metrics(a, b):
    a = np.asarray(a, dtype=bool).ravel()
    b = np.asarray(b, dtype=bool).ravel()

    tp = int(np.count_nonzero(a & b))
    fp = int(np.count_nonzero(~a & b))
    fn = int(np.count_nonzero(a & ~b))
    tn = int(np.count_nonzero(~a & ~b))

    union = tp + fp + fn

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "jaccard": tp / union if union else None,
        "equality": float(np.mean(a == b)),
        "exact": bool(np.array_equal(a, b)),
        "total": int(a.size),
    }


def phi(a, b):
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()

    if a.std() == 0 or b.std() == 0:
        return None

    return float(np.corrcoef(a, b)[0, 1])


def main():

    print("[1] Loading matrix...")

    with np.load(MATRIX_PATH, allow_pickle=False) as z:
        print("[NPZ KEYS]", z.files)

        matrix = np.asarray(z["spacetime"], dtype=np.uint8)

        frontier_start = int(
            np.asarray(z["frontier_start"]).reshape(-1)[0]
        )

        source_generation = int(
            np.asarray(z["source_generation"]).reshape(-1)[0]
        )

    T, W = matrix.shape

    if W != 8192 or T != 501:
        raise RuntimeError("Unexpected matrix dimensions.")

    if TARGET + WINDOW > W:
        raise RuntimeError("Target window exceeds matrix width.")

    print("[SHAPE]", matrix.shape)
    print("[FRONTIER START]", frontier_start)
    print("[SOURCE GENERATION]", source_generation)

    print("[2] Rule 110 validation...")

    neighborhoods = (
        (matrix[:-1, :-2] << 2)
        | (matrix[:-1, 1:-1] << 1)
        | matrix[:-1, 2:]
    )

    predicted = RULE110[neighborhoods]
    observed = matrix[1:, 1:-1]

    rule_errors = int(np.count_nonzero(predicted != observed))

    print("[RULE110 CHECKED]", observed.size)
    print("[RULE110 ERRORS]", rule_errors)

    if rule_errors != 0:
        raise RuntimeError("Rule 110 validation failed.")

    print("[3] Extracting equal-sized regions...")

    A = matrix[:, :WINDOW]
    B = matrix[:, TARGET:TARGET + WINDOW]

    state_metrics = metrics(A, B)

    print("[STATE METRICS]")
    print(json.dumps(state_metrics, indent=2))

    print("[4] Locating every original-state difference...")

    difference = A != B

    coordinates = np.argwhere(difference)

    difference_rows = []

    for t, x in coordinates:

        difference_rows.append({
            "matrix_generation_index": int(t),
            "global_generation": source_generation + int(t),
            "left_matrix_index": int(x),
            "right_matrix_index": int(x + TARGET),
            "left_global_coordinate": frontier_start + int(x),
            "right_global_coordinate": frontier_start + int(x + TARGET),
            "left_state": int(A[t, x]),
            "right_state": int(B[t, x]),
        })

    write_csv(
        OUT / "043_original_state_differences.csv",
        difference_rows
    )

    print("[DIFFERENCE COUNT]", len(difference_rows))

    print("[5] Differences by generation...")

    generation_rows = []

    for t in range(T):

        d = int(np.count_nonzero(difference[t]))

        generation_rows.append({
            "matrix_generation_index": t,
            "global_generation": source_generation + t,
            "different_positions": d,
            "equal_positions": WINDOW - d,
            "equality": 1.0 - d / WINDOW,
        })

    write_csv(
        OUT / "043_generation_difference_profile.csv",
        generation_rows
    )

    print("[6] Difference persistence...")

    persistence_rows = []

    for t in range(T - 1):

        current = difference[t]
        following = difference[t + 1]

        persistence_rows.append({
            "generation_index": t,
            "differences_current": int(current.sum()),
            "differences_next": int(following.sum()),
            "persistent_same_coordinate": int(
                np.count_nonzero(current & following)
            ),
            "disappeared": int(
                np.count_nonzero(current & ~following)
            ),
            "new_at_same_coordinate": int(
                np.count_nonzero(~current & following)
            ),
        })

    write_csv(
        OUT / "043_difference_persistence.csv",
        persistence_rows
    )

    print("[7] Comparing Rule 110 neighborhoods...")

    # Compare the complete three-cell input neighborhoods
    # in both regions, excluding each window's outer edges.

    A_neighborhoods = (
        (A[:, :-2] << 2)
        | (A[:, 1:-1] << 1)
        | A[:, 2:]
    )

    B_neighborhoods = (
        (B[:, :-2] << 2)
        | (B[:, 1:-1] << 1)
        | B[:, 2:]
    )

    neighborhood_difference = (
        A_neighborhoods != B_neighborhoods
    )

    neighborhood_rows = []

    for t in range(T):

        count = int(neighborhood_difference[t].sum())

        neighborhood_rows.append({
            "matrix_generation_index": t,
            "global_generation": source_generation + t,
            "different_neighborhoods": count,
            "equal_neighborhoods": WINDOW - 2 - count,
        })

    write_csv(
        OUT / "043_neighborhood_comparison.csv",
        neighborhood_rows
    )

    # Direct comparison of next-state outputs.
    A_outputs = matrix[1:, 1:WINDOW - 1]
    B_outputs = matrix[1:, TARGET + 1:TARGET + WINDOW - 1]

    output_difference = A_outputs != B_outputs

    output_summary = {
        "neighborhood_comparisons": int(neighborhood_difference.size),
        "different_neighborhoods": int(neighborhood_difference.sum()),
        "next_state_comparisons": int(output_difference.size),
        "different_next_states": int(output_difference.sum()),
        "equal_next_states": int(
            output_difference.size - output_difference.sum()
        ),
    }

    print("[NEIGHBORHOOD SUMMARY]")
    print(json.dumps(output_summary, indent=2))

    print("[8] Spatial difference clusters...")

    spatial_difference = difference.sum(axis=0)

    cluster_rows = []

    active = np.flatnonzero(spatial_difference > 0)

    if len(active):

        start = previous = int(active[0])

        for position in active[1:]:

            position = int(position)

            if position > previous + 1:

                cluster_rows.append({
                    "start_index": start,
                    "end_index": previous,
                    "length": previous - start + 1,
                    "total_differences": int(
                        spatial_difference[start:previous + 1].sum()
                    ),
                })

                start = position

            previous = position

        cluster_rows.append({
            "start_index": start,
            "end_index": previous,
            "length": previous - start + 1,
            "total_differences": int(
                spatial_difference[start:previous + 1].sum()
            ),
        })

    write_csv(
        OUT / "043_spatial_difference_clusters.csv",
        cluster_rows
    )

    print("[9] Equal-window offset controls...")

    # Every offset uses exactly the same 1792-position window.
    # This avoids comparing different sample sizes.

    offsets = list(range(6200, 6401, 1))

    scan_rows = []

    for offset in offsets:

        left = matrix[:, :WINDOW]
        right = matrix[:, offset:offset + WINDOW]

        m = metrics(left, right)

        scan_rows.append({
            "offset": offset,
            "window_width": WINDOW,
            "tp": m["tp"],
            "fp": m["fp"],
            "fn": m["fn"],
            "jaccard": m["jaccard"],
            "equality": m["equality"],
            "phi": phi(left, right),
        })

    write_csv(
        OUT / "043_equal_window_offset_scan.csv",
        scan_rows
    )

    print("[10] Anomaly-mask comparison...")

    mask = np.zeros((T - 1, W), dtype=np.uint8)

    mask[:, 4:] = (
        matrix[:-1, 4:] != matrix[1:, :-4]
    ).astype(np.uint8)

    MA = mask[:, :WINDOW]
    MB = mask[:, TARGET:TARGET + WINDOW]

    anomaly_metrics = metrics(MA, MB)

    print("[ANOMALY MASK]")
    print(json.dumps(anomaly_metrics, indent=2))

    anomaly_diff = MA != MB

    anomaly_coordinates = np.argwhere(anomaly_diff)

    anomaly_rows = []

    for t, x in anomaly_coordinates:

        anomaly_rows.append({
            "generation_index": int(t),
            "global_generation": source_generation + int(t),
            "left_global_coordinate": frontier_start + int(x),
            "right_global_coordinate": frontier_start + int(x + TARGET),
            "left_anomaly": int(MA[t, x]),
            "right_anomaly": int(MB[t, x]),
        })

    write_csv(
        OUT / "043_anomaly_mask_differences.csv",
        anomaly_rows
    )

    print("[11] Sector 3 and sector 28 direct comparison...")

    sector_a = mask[:, 3 * SECTOR:4 * SECTOR]
    sector_b = mask[:, 28 * SECTOR:29 * SECTOR]

    sector_metrics = metrics(sector_a, sector_b)

    print("[SECTOR 3 VS 28]")
    print(json.dumps(sector_metrics, indent=2))

    summary = {
        "experiment": "043",
        "title": "THE 6400 MIRROR FORENSICS",
        "matrix_shape": [T, W],
        "matrix_sha256": sha256(MATRIX_PATH),
        "frontier_start": frontier_start,
        "source_generation": source_generation,
        "target_offset": TARGET,
        "window_width": WINDOW,
        "rule110_errors": rule_errors,
        "original_state_metrics": state_metrics,
        "original_state_difference_count": len(difference_rows),
        "generation_difference_min": min(
            r["different_positions"] for r in generation_rows
        ),
        "generation_difference_max": max(
            r["different_positions"] for r in generation_rows
        ),
        "generation_difference_initial": generation_rows[0],
        "generation_difference_final": generation_rows[-1],
        "neighborhood_summary": output_summary,
        "anomaly_mask_metrics": anomaly_metrics,
        "anomaly_mask_difference_count": len(anomaly_rows),
        "sector_3_vs_28": sector_metrics,
        "spatial_difference_cluster_count": len(cluster_rows),
        "interpretation_limits": [
            "Classical Rule 110 correlations do not demonstrate quantum entanglement.",
            "A matching state does not establish a causal connection.",
            "Equal-window offset controls reduce sample-size bias.",
            "The matrix records a finite observed spacetime window.",
            "The experiment cannot independently establish how the source matrix was originally constructed.",
        ],
    }

    with open(
        OUT / "043_final_report.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(summary, f, indent=2)

    print("")
    print("=" * 70)
    print("EXPERIMENT 043 - FINAL SUMMARY")
    print("=" * 70)

    print("OFFSET:", TARGET)
    print("WINDOW:", WINDOW)
    print("ORIGINAL JACCARD:", state_metrics["jaccard"])
    print("ORIGINAL DIFFERENCES:", len(difference_rows))
    print("INITIAL DIFFERENCES:",
          generation_rows[0]["different_positions"])
    print("FINAL DIFFERENCES:",
          generation_rows[-1]["different_positions"])
    print("NEIGHBORHOOD DIFFERENCES:",
          output_summary["different_neighborhoods"])
    print("NEXT STATE DIFFERENCES:",
          output_summary["different_next_states"])
    print("ANOMALY JACCARD:", anomaly_metrics["jaccard"])
    print("SECTOR 3 VS 28:", sector_metrics["jaccard"])

    print("")
    print("[OUTPUT]", OUT)
    print("[RUNTIME]", round(time.time() - START_TIME, 3))
    print("[STATUS] COMPLETED")


if __name__ == "__main__":
    main()

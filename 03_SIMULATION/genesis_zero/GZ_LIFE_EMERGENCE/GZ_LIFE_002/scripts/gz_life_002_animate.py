import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import ListedColormap

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parents[1] / "GZ_EMERGENCE_001" / "results" / "raw"
DATA = ROOT / "results" / "derived"
OUT = ROOT / "visualizations"

OUT.mkdir(parents=True, exist_ok=True)

WIDTH = 256
RULES = {
    67:  {"transient": 702, "period": 512},
    109: {"transient": 1482, "period": 2760},
    137: {"transient": 1058, "period": 960},
}

def components(state):
    active = np.flatnonzero(state)

    if len(active) == 0:
        return []

    if len(active) == WIDTH:
        return [active.tolist()]

    breaks = np.where(np.diff(active) > 1)[0]
    groups = [g.tolist() for g in np.split(active, breaks + 1)]

    if len(groups) > 1:
        if groups[0][0] == 0 and groups[-1][-1] == WIDTH - 1:
            groups[0] = groups[-1] + groups[0]
            groups.pop()

    return groups


def load_trajectory(rule):
    path = SOURCE / f"rule_{rule:03d}.npz"

    with np.load(path, allow_pickle=False) as data:
        packed = data["trajectory"]

    return np.unpackbits(
        packed,
        axis=1,
        count=WIDTH,
        bitorder="big"
    ).astype(np.uint8)


def load_events(rule):
    path = DATA / "GZ_LIFE_002_TRANSITION_SUMMARY.csv"

    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    return {
        int(row["transition"]): row
        for row in rows
        if int(row["rule"]) == rule
    }


def animate_rule(rule, settings):
    trajectory = load_trajectory(rule)

    start = settings["transient"]
    period = settings["period"]

    indices = np.linspace(
        start,
        start + period - 1,
        min(period, 120),
        dtype=int
    )

    events = load_events(rule)

    history = []
    frame_data = []

    for index in indices:
        state = trajectory[index]
        history.append(state)

        visible = np.array(history[-80:])
        comps = components(state)

        active = int(state.sum())
        component_count = len(comps)

        event = events.get(index, {})

        splits = int(event.get("split_parents", 0))
        merges = int(event.get("merge_children", 0))

        frame_data.append({
            "index": index,
            "history": visible,
            "active": active,
            "components": component_count,
            "splits": splits,
            "merges": merges
        })

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor("#0d1523")
    ax.set_facecolor("#101d30")

    cmap = ListedColormap(["#14243a", "#f4c95d"])

    image = ax.imshow(
        frame_data[0]["history"],
        aspect="auto",
        interpolation="nearest",
        cmap=cmap,
        vmin=0,
        vmax=1,
        extent=[0, WIDTH, 80, 0]
    )

    title = fig.suptitle(
        f"GENESIS ZERO | GZ-LIFE-002 | RULE {rule}",
        color="white",
        fontsize=17,
        fontweight="bold"
    )

    info = ax.text(
        0.02, -0.13, "",
        transform=ax.transAxes,
        color="white",
        fontsize=10
    )

    ax.set_xlabel("Posición celular", color="white")
    ax.set_ylabel("Historia reciente | ciclos", color="white")
    ax.tick_params(colors="white")
    ax.set_xlim(0, WIDTH)

    for spine in ax.spines.values():
        spine.set_color("#49617e")

    def update(frame):
        item = frame_data[frame]

        image.set_data(item["history"])
        image.set_extent([
            0, WIDTH,
            len(item["history"]), 0
        ])

        info.set_text(
            f"Ciclo: {frame + 1}/{len(frame_data)}   "
            f"Transición: {item['index']}   |   "
            f"Celdas activas: {item['active']}   |   "
            f"Componentes: {item['components']}   |   "
            f"Divisiones candidatas: {item['splits']}   |   "
            f"Fusiones candidatas: {item['merges']}"
        )

        return image, info

    animation = FuncAnimation(
        fig,
        update,
        frames=len(frame_data),
        interval=100,
        blit=False
    )

    filename = OUT / f"GZ_LIFE_002_RULE_{rule:03d}.gif"

    animation.save(
        filename,
        writer=PillowWriter(fps=10)
    )

    plt.close(fig)

    print(
        f"GENERADO: {filename.name} | "
        f"{filename.stat().st_size:,} bytes | "
        f"{len(frame_data)} frames"
    )


for rule, settings in RULES.items():
    animate_rule(rule, settings)

print("\nANIMACIONES COMPLETADAS.")


"""Render exported purchased board meshes with optional matplotlib (system Python).

Run CAD exports first, then: MPLCONFIGDIR=/tmp/robot-arm-mpl python3 scripts/render_esp32.py
"""
from pathlib import Path
import math
import struct

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/esp32"
OUT.mkdir(parents=True, exist_ok=True)
COLORS = {"pcb_black": "#202724", "electronics_black": "#101214",
          "electronics_silver": "#c8cdd2", "electronics_gold": "#c9a447",
          "electronics_white": "#e3e5d8", "electronics_red": "#b82820"}


def triangles(path):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    return np.array([struct.unpack_from("<12f", data, 84 + i * 50)[3:]
                     for i in range(count)]).reshape(-1, 3, 3)


def draw_models(names, filename, title, transforms=None):
    meshes = []
    for index, name in enumerate(names):
        for finish, color in COLORS.items():
            mesh = triangles(ROOT / f"models/out/{name}_{finish}.stl")
            if transforms:
                matrix, offset = transforms[index]
                mesh = mesh @ matrix.T + offset
            meshes.append((mesh, color))
    fig = plt.figure(figsize=(12, 8), facecolor="#f4f2eb")
    vertices = np.concatenate([mesh.reshape(-1, 3) for mesh, _ in meshes])
    lo, hi = vertices.min(axis=0), vertices.max(axis=0)
    for index, (label, elev, azim) in enumerate((("Top", 90, -90), ("Underside", -90, 90),
                                                ("Side", 0, -90), ("Perspective", 35, -65))):
        ax = fig.add_subplot(2, 2, index + 1, projection="3d", facecolor="#f4f2eb")
        faces = np.concatenate([mesh for mesh, _ in meshes])
        colors = [color for mesh, color in meshes for _ in mesh]
        ax.add_collection3d(Poly3DCollection(faces, facecolors=colors, shade=True, linewidths=0))
        for axis, low, high in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), lo, hi):
            axis(low - 2, high + 2)
        ax.set_box_aspect(hi - lo + 4)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.set_title(label)
    fig.suptitle(title, fontsize=16)
    fig.tight_layout()
    fig.savefig(OUT / filename, dpi=150)
    plt.close(fig)


def overlay():
    # Same photo calibration and rigid registration as models/esp32_boards.py.
    board = np.array(((20.77, 24.13), (-31.75, 19.05), (-31.75, -8.91), (19.06, -24.26))) * [-1, 1]
    target = np.array(((-20.32, -24.13), (31.75, -19.05), (31.75, 8.89), (-19.05, 24.13)))[[3, 2, 1, 0]]
    a = math.radians(-8.0633063239875)
    rotated = board @ np.array([[math.cos(a), math.sin(a)], [-math.sin(a), math.cos(a)]]) + [-0.20187507, -4.15075918]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), facecolor="#f4f2eb")
    ax = axes[0]
    ax.plot(*np.array(((-34.3, -26.7), (34.3, -26.7), (34.3, 26.7), (-34.3, 26.7), (-34.3, -26.7))).T, color="#202724")
    ax.scatter(*target.T, marker="+", s=150, color="#d25632", label="Existing M3 bosses")
    ax.scatter(*rotated.T, facecolors="none", edgecolors="#19738a", s=100, label="Registered board holes")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1))
    ax.set_title("Registered hole pattern (mm)")
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax = axes[1]
    delta = rotated[1] - target[1]
    ax.add_patch(plt.Circle((0, 0), 1.5, color="#d25632", alpha=0.45, label="M3 screw: Ø3.0"))
    ax.add_patch(plt.Circle(delta, 1.7, fill=False, color="#19738a", linewidth=2, label="Board hole: Ø3.4"))
    ax.plot([0, delta[0]], [0, delta[1]], color="black")
    ax.set(xlim=(-5, 5), ylim=(-5, 5), title="Worst hole: 2.553 mm offset\nAvailable radial clearance: 0.200 mm")
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    fig.savefig(OUT / "mounting-overlay.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    draw_models(["esp32_expansion_30pin"], "expansion-views.png", "ESP32 30P expansion board • photographed revision")
    draw_models(["esp32_devkit_30pin"], "devkit-views.png", "30-pin ESP32 DevKit • configurable clone reference")
    draw_models(["esp32_expansion_30pin", "esp32_devkit_30pin"], "seated-views.png", "ESP32 seated in the expansion-board sockets",
                [(np.eye(3), np.zeros(3)), (np.eye(3), np.array((-8, 0, 12.6)))])
    overlay()

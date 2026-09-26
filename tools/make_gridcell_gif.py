"""Generate assets/gridcell.gif for the README.

Python port of gridcell_demo.m (same model and parameters), used because
MATLAB is not available in CI. Requires numpy, matplotlib and pillow.

    python tools/make_gridcell_gif.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

# ---- Parameters (keep in sync with gridcell_demo.m) ----
ARENA = 1.0            # arena side length [m]
T_TOTAL = 15 * 60      # simulated time [s]
DT = 0.02              # time step [s]
SPEED = 0.25           # running speed [m/s]
TURN_SD = 0.25         # heading noise per step [rad]
SPACING = 0.35         # grid spacing [m]
ORIENT = np.deg2rad(8) # grid orientation [rad]
PHASE = np.array([0.12, 0.07])  # grid phase offset [m]
RMAX = 20.0            # peak firing rate [Hz]
NBIN = 40              # rate map bins per side
SMOOTH_SD = 1.5        # smoothing kernel SD [bins]
N_FRAMES = 80
TAIL = 20.0            # trajectory tail shown [s]

OUT = Path(__file__).resolve().parents[1] / "assets" / "gridcell.gif"


def simulate(rng):
    n = int(T_TOTAL / DT)
    pos = np.zeros((n, 2))
    pos[0] = ARENA / 2
    hd = rng.uniform(0, 2 * np.pi)
    for i in range(1, n):
        hd += TURN_SD * rng.standard_normal()
        step = SPEED * DT * np.array([np.cos(hd), np.sin(hd)])
        nxt = pos[i - 1] + step
        if not 0 < nxt[0] < ARENA:
            hd = np.pi - hd
        if not 0 < nxt[1] < ARENA:
            hd = -hd
        pos[i] = pos[i - 1] + SPEED * DT * np.array([np.cos(hd), np.sin(hd)])
        pos[i] = np.clip(pos[i], 1e-6, ARENA - 1e-6)
    return pos


def grid_rate(xy):
    k = 4 * np.pi / (np.sqrt(3) * SPACING)
    g = np.zeros(len(xy))
    for j in range(3):
        a = ORIENT + j * np.pi / 3
        g += np.cos(k * ((xy - PHASE) @ np.array([np.cos(a), np.sin(a)])))
    return RMAX * ((g + 1.5) / 4.5) ** 3  # g in [-1.5, 3] -> [0, RMAX]


def gauss_kernel(sd):
    r = int(np.ceil(3 * sd))
    x = np.arange(-r, r + 1)
    k = np.exp(-(x[:, None] ** 2 + x[None, :] ** 2) / (2 * sd**2))
    return k / k.sum()


def conv2_same(a, k):
    r = k.shape[0] // 2
    p = np.pad(a, r)
    out = np.zeros_like(a)
    for i in range(k.shape[0]):
        for j in range(k.shape[1]):
            out += k[i, j] * p[i:i + a.shape[0], j:j + a.shape[1]]
    return out


def rate_map(pos, spk):
    edges = np.linspace(0, ARENA, NBIN + 1)
    occ, _, _ = np.histogram2d(pos[:, 1], pos[:, 0], bins=[edges, edges])
    cnt, _, _ = np.histogram2d(pos[spk, 1], pos[spk, 0], bins=[edges, edges])
    k = gauss_kernel(SMOOTH_SD)
    occ_s = conv2_same(occ * DT, k)
    rm = conv2_same(cnt, k) / np.maximum(occ_s, 1e-12)
    rm[occ == 0] = np.nan
    return rm


def main():
    rng = np.random.default_rng(1)
    pos = simulate(rng)
    spikes = rng.random(len(pos)) < grid_rate(pos) * DT

    # Frame times accelerate so the early build-up is visible.
    n = len(pos)
    ends = np.unique(np.round(n * (np.arange(1, N_FRAMES + 1) / N_FRAMES) ** 1.6)).astype(int)
    ends = np.maximum(ends, int(TAIL / DT))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4.3), dpi=80)
    fig.patch.set_facecolor("white")
    frames = []
    for e in ends:
        ax1.cla()
        ax2.cla()
        s = max(0, e - int(TAIL / DT))
        sp = np.flatnonzero(spikes[:e])
        ax1.plot(pos[s:e, 0], pos[s:e, 1], color="0.6", lw=0.8)
        ax1.plot(pos[sp, 0], pos[sp, 1], ".", color="#d62728", ms=2.5)
        ax1.plot(pos[e - 1, 0], pos[e - 1, 1], "o", color="k", ms=6)
        ax1.set_title("Trajectory & spikes", fontsize=12)
        ax2.imshow(rate_map(pos[:e], sp), origin="lower", cmap="jet",
                   extent=[0, ARENA, 0, ARENA], interpolation="nearest")
        ax2.set_title("Firing rate map", fontsize=12)
        for ax in (ax1, ax2):
            ax.set_xlim(0, ARENA)
            ax.set_ylim(0, ARENA)
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
        fig.suptitle(f"Grid cell simulation   t = {e * DT / 60:4.1f} min", fontsize=13)
        fig.canvas.draw()
        img = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3])
        frames.append(img.quantize(colors=128, method=Image.Quantize.MEDIANCUT))

    durations = [80] * (len(frames) - 1) + [3000]  # hold the last frame
    OUT.parent.mkdir(exist_ok=True)
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB, {len(frames)} frames)")


if __name__ == "__main__":
    main()

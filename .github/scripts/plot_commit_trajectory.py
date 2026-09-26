"""Draw the commit history of this repository as animal trajectories.

Left : each author's commits (x = date, y = time of day in JST), joined in
       time order like a tracked rat's path; the big dot is the latest commit.
Right: commit time-of-day "tuning curves", plotted like head-direction cells.

Bot commits are skipped. Author aliases are merged through .mailmap.
Usage: python .github/scripts/plot_commit_trajectory.py
Requires numpy and matplotlib, and full git history (fetch-depth: 0).
"""
import datetime as dt
import subprocess
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "commit_trajectory.png"
JST = dt.timezone(dt.timedelta(hours=9))
TUNING_SD = 1.0  # circular smoothing of the tuning curve [h]


def load_commits():
    log = subprocess.run(
        ["git", "log", "--use-mailmap", "--reverse", "--format=%aN%x09%aE%x09%at"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    commits = defaultdict(list)
    for line in log.splitlines():
        name, email, ts = line.split("\t")
        if "[bot]" in name or "[bot]" in email:
            continue
        commits[name].append(dt.datetime.fromtimestamp(int(ts), JST))
    return commits


def tuning_curve(hours):
    grid = np.linspace(0, 24, 97)
    d = np.abs(grid[:, None] - np.asarray(hours)[None, :])
    d = np.minimum(d, 24 - d)
    curve = np.exp(-d**2 / (2 * TUNING_SD**2)).sum(axis=1)
    return grid, curve / curve.max()


def main():
    commits = load_commits()
    # Most active author first so colors stay stable as people join.
    authors = sorted(commits, key=lambda a: (-len(commits[a]), a))
    colors = plt.get_cmap("tab10")

    fig = plt.figure(figsize=(11, 5), dpi=100)
    fig.patch.set_facecolor("white")
    ax1 = fig.add_axes([0.07, 0.11, 0.54, 0.72])
    ax2 = fig.add_axes([0.67, 0.09, 0.29, 0.70], projection="polar")

    for i, a in enumerate(authors):
        t = commits[a]
        hour = [x.hour + x.minute / 60 for x in t]
        c = colors(i % 10)
        label = f"{a} ({len(t)})"
        ax1.plot(t, hour, "-", color=c, lw=1, alpha=0.5)
        ax1.plot(t, hour, "o", color=c, ms=4, label=label)
        ax1.plot(t[-1], hour[-1], "o", color=c, ms=10, mec="k", mew=1.2)

        grid, curve = tuning_curve(hour)
        theta = grid / 24 * 2 * np.pi
        ax2.plot(theta, curve, color=c, lw=1.5)
        ax2.fill(theta, curve, color=c, alpha=0.15)

    ax1.set_ylim(24, 0)
    ax1.set_yticks(range(0, 25, 3))
    ax1.set_ylabel("Time of day (JST)")
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=8))
    ax1.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax1.xaxis.get_major_locator()))
    ax1.grid(alpha=0.3)
    ax1.legend(loc="upper left", fontsize=9, frameon=True)
    ax1.set_title("Commit trajectories", fontsize=12)

    ax2.set_theta_zero_location("N")
    ax2.set_theta_direction(-1)
    ax2.set_xticks(np.arange(0, 24, 3) / 24 * 2 * np.pi)
    ax2.set_xticklabels([f"{h}h" for h in range(0, 24, 3)])
    ax2.set_yticks([])
    ax2.set_title("Commit-time tuning curves", fontsize=12, pad=22)

    total = sum(len(v) for v in commits.values())
    now = dt.datetime.now(JST)
    fig.suptitle(f"sandbox: {total} commits by {len(authors)} authors "
                 f"(updated {now:%Y-%m-%d})", fontsize=13, y=0.97)
    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

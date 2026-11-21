"""Plot a Mocktini optical-tweezers pull (the CSV from the Tweezers bar).

Usage:
    python plot_pull.py tweezers_pull_....csv            # running average over 10 frames
    python plot_pull.py tweezers_pull_....csv -w 25      # wider window
    python plot_pull.py tweezers_pull_....csv --save     # also writes <file>.png

Needs pandas, numpy and matplotlib (pip install pandas matplotlib).

Panels:
  1. F_par against s while pulling: the force–distance curve, raw + running average
  2. F_par against simulated time t, including the hold at the end of the path
  3. Work done by the trap, W(s) = ∫ F_par ds (trapezoid rule)
"""
import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def read_pull(path):
    """Return (data, meta): the table, and the '# key = value' header lines as a dict."""
    meta = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("#"):
                break
            if " = " in line:
                key, value = line[1:].split(" = ", 1)
                meta[key.strip()] = value.strip()
    data = pd.read_csv(path, comment="#")   # '#' lines are the header, skipped here
    return data, meta


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="CSV file exported with the CSV button")
    ap.add_argument("-w", "--window", type=int, default=10,
                    help="running-average window in frames (rows), default 10")
    ap.add_argument("--save", action="store_true", help="save the figure as <csv>.png")
    args = ap.parse_args()

    d, meta = read_pull(args.csv)

    # Running average, centred on each frame; shorter windows at the ends.
    d["F_avg"] = d["F_par"].rolling(args.window, center=True, min_periods=1).mean()

    # Pulling phase = before the trap reaches the end of the path (then it holds).
    length = float(meta.get("path_length") or d["s"].max())
    pulling = d["s"] < length - 1e-9
    pull = d[pulling]

    # Work done by the trap along the path: W(s) = ∫ F_par ds
    work = np.concatenate([[0.0], np.cumsum(0.5 * (pull["F_par"].values[1:] + pull["F_par"].values[:-1])
                                            * np.diff(pull["s"].values))])

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 10))
    title = (f"U0 = {meta.get('trap_U0', '?')} ε, w0 = {meta.get('trap_w0', '?')} σ, "
             f"v = {meta.get('pull_speed_v', '?')} σ/τ, T = {meta.get('T_set', '?')} ε")
    fig.suptitle(f"{meta.get('run_id', args.csv)}\n{title}", fontsize=10)

    ax1.plot(pull["s"], pull["F_par"], color="0.75", lw=0.8, label="per frame")
    ax1.plot(pull["s"], pull["F_avg"], color="C0", lw=2, label=f"running average ({args.window} frames)")
    ax1.axhline(0, color="k", lw=0.5)
    ax1.set_xlabel("s, distance along the path [σ]")
    ax1.set_ylabel("F∥ [ε/σ]")
    ax1.set_title("Force–distance (pulling)")
    ax1.legend()

    ax2.plot(d["t"], d["F_par"], color="0.75", lw=0.8)
    ax2.plot(d["t"], d["F_avg"], color="C0", lw=2)
    if (~pulling).any():   # shade the hold at the end of the path
        ax2.axvspan(d.loc[~pulling, "t"].min(), d["t"].max(), color="C1", alpha=0.15, label="hold at path end")
        ax2.legend()
    ax2.axhline(0, color="k", lw=0.5)
    ax2.set_xlabel("t, simulated time [τ]")
    ax2.set_ylabel("F∥ [ε/σ]")
    ax2.set_title("Force in time")

    ax3.plot(pull["s"], work, color="C2", lw=2)
    ax3.axhline(0, color="k", lw=0.5)
    ax3.set_xlabel("s, distance along the path [σ]")
    ax3.set_ylabel("W [ε]")
    ax3.set_title(f"Work done by the trap: W = {work[-1]:.3g} ε  (≥ ΔF; equal only for a reversible pull)")

    fig.tight_layout()
    if args.save:
        out = args.csv.rsplit(".", 1)[0] + ".png"
        fig.savefig(out, dpi=150)
        print("saved", out)
    plt.show()


if __name__ == "__main__":
    main()

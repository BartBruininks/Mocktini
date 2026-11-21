"""Plot a Mocktini stats log (the CSV from the Log cell in the stats bar).

Usage:
    python plot_stats.py stats_....csv              # running average over 10 frames
    python plot_stats.py stats_....csv -w 25        # wider window
    python plot_stats.py stats_....csv -x step      # integration steps on the x axis instead of t
    python plot_stats.py stats_....csv --save       # also writes <file>.png

Needs pandas, numpy and matplotlib (pip install pandas matplotlib).

One panel per quantity, against simulated time t:
  T (T_inst with T_set) · KE/N · PE/N · E/N · P · dt · N (with N_frozen) · Σq
KE/N is not a column; it is computed as E_N − PE_N.
Noisy quantities (T, KE, PE, P) get a running average on top of the raw per-frame values;
the average restarts after an edit made while paused (it never smooths across an edit).

The '# before step …' lines between rows are drawn as vertical lines and numbered:
  grey dotted = run paused and continued · red = system edited while paused
  orange = settings changed while recording. The list is printed in the terminal.
"""
import argparse
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

MARK = re.compile(r"^# before step (\d+) \(t ([^)]+)\): (.*)$")


def read_stats(path):
    """Return (data, meta, marks, end): the table, the '# key = value' header lines
    as a dict, the markers between rows as (step, t, text), and the end note."""
    meta, marks, end = {}, [], None
    in_header = True
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if in_header:
                if not line.startswith("#"):
                    in_header = False          # the column header row
                elif " = " in line:
                    key, value = line[1:].split(" = ", 1)
                    meta[key.strip()] = value.strip()
                continue
            m = MARK.match(line)
            if m:
                marks.append((int(m.group(1)), float(m.group(2)), m.group(3)))
            elif line.startswith("# recording ended"):
                end = line[2:]
    data = pd.read_csv(path, comment="#")   # all '#' lines (header and markers) are skipped here
    data["KE_N"] = data["E_N"] - data["PE_N"]
    return data, meta, marks, end


def mark_style(text):
    if "edited" in text:
        return dict(color="C3", ls="-", lw=1.0, alpha=0.8)
    if text.startswith("run paused and continued") and ";" not in text:
        return dict(color="0.5", ls=":", lw=1.0, alpha=0.8)
    return dict(color="C1", ls="--", lw=1.0, alpha=0.8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="CSV file exported with the CSV button of the stats log")
    ap.add_argument("-w", "--window", type=int, default=10,
                    help="running-average window in frames (rows), default 10")
    ap.add_argument("-x", choices=["t", "step"], default="t",
                    help="x axis: simulated time t (default) or integration step")
    ap.add_argument("--save", action="store_true", help="save the figure as <csv>.png")
    args = ap.parse_args()

    d, meta, marks, end = read_stats(args.csv)
    x = d[args.x]
    xlabel = "t, simulated time [τ]" if args.x == "t" else "step"

    # Running averages restart after an edit made while paused: the system before
    # and after an edit are different, so the average must not smooth across it.
    seg = np.zeros(len(d), dtype=int)
    for step, _, text in marks:
        if "edited" in text:
            seg[d["step"].values >= step] += 1

    def avg(col):   # running average, centred on each frame; shorter windows at the ends
        return d[col].groupby(seg).transform(
            lambda c: c.rolling(args.window, center=True, min_periods=1).mean())

    fig, axes = plt.subplots(4, 2, figsize=(11, 12), sharex=True)
    ax = axes.ravel()
    title = (f"{meta.get('integrator', '?')}, thermostat {meta.get('thermostat', meta.get('tau_langevin', '?'))}, "
             f"{meta.get('potential', '?')}, N = {meta.get('N', '?')}, L = {meta.get('box_L', '?')} σ, "
             f"dt = {meta.get('dt', '?')} τ")
    fig.suptitle(f"{meta.get('run_id', args.csv)}\n{title}", fontsize=10)

    def noisy(a, col, label, unit, color="C0"):
        a.plot(x, d[col], color="0.75", lw=0.8, label="per frame")
        a.plot(x, avg(col), color=color, lw=2, label=f"running average ({args.window})")
        a.set_ylabel(f"{label} [{unit}]")
        a.set_title(label)

    # 1. Temperature, with the thermostat target
    noisy(ax[0], "T_inst", "T", "ε")
    ax[0].plot(x, d["T_set"], color="k", lw=1, ls="--", label="T set")
    ax[0].set_title("Temperature (T inst, T set)")
    ax[0].legend(fontsize=8)

    # 2–4. Energies per bead
    noisy(ax[1], "KE_N", "KE / N", "ε", "C1")
    ax[1].set_title("Kinetic energy per bead (E/N − PE/N)")
    noisy(ax[2], "PE_N", "PE / N", "ε", "C2")
    ax[2].set_title("Potential energy per bead")
    ax[3].plot(x, d["E_N"], color="C3", lw=1.5)
    ax[3].set_ylabel("E / N [ε]")
    drift = d["E_N"].iloc[-1] - d["E_N"].iloc[0]
    ax[3].set_title(f"Total energy per bead (drift {drift:+.3g} ε)")

    # 5. Pressure (empty cells = undefined → gaps)
    noisy(ax[4], "P", "P", "ε/σ²", "C4")
    ax[4].axhline(0, color="k", lw=0.5)
    ax[4].set_title(f"Pressure (mean {d['P'].mean():.4g} ε/σ²)")

    # 6. Timestep (shows the dt ramp)
    ax[5].plot(x, d["dt"], color="C5", lw=1.5)
    ax[5].set_ylabel("dt [τ]")
    ax[5].set_title("Timestep")

    # 7. Bead counts
    ax[6].plot(x, d["N"], color="C0", lw=1.5, drawstyle="steps-post", label="N")
    ax[6].plot(x, d["N_frozen"], color="C7", lw=1.5, drawstyle="steps-post", label="N frozen")
    ax[6].set_ylim(bottom=0)
    ax[6].set_ylabel("beads")
    ax[6].set_title("Number of beads")
    ax[6].legend(fontsize=8)

    # 8. Net charge
    ax[7].plot(x, d["Q"], color="C6", lw=1.5, drawstyle="steps-post")
    ax[7].axhline(0, color="k", lw=0.5)
    ax[7].set_ylabel("Σq")
    ax[7].set_title("Net charge")

    # Markers: one vertical line per '# before step …' line, numbered in the top panels
    for k, (step, t, text) in enumerate(marks, 1):
        xm = t if args.x == "t" else step
        for a in ax:
            a.axvline(xm, **mark_style(text))
        for a in ax[:2]:
            a.annotate(str(k), (xm, 1), xycoords=("data", "axes fraction"),
                       xytext=(2, -10), textcoords="offset points", fontsize=8, color=mark_style(text)["color"])
    if marks:
        print("Markers:")
        for k, (step, t, text) in enumerate(marks, 1):
            print(f"  {k}. step {step}, t {t:.4g}: {text}")
    if end:
        print(end)

    for a in axes[-1]:
        a.set_xlabel(xlabel)
    fig.tight_layout()
    if args.save:
        out = args.csv.rsplit(".", 1)[0] + ".png"
        fig.savefig(out, dpi=150)
        print("saved", out)
    plt.show()


if __name__ == "__main__":
    main()

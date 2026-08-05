#!/usr/bin/env python
"""Generate the model schematic for the paper (Fig. `fig:model`).

This is a *schematic*, not measured data: it carries no number that enters the
claims registry.  It is committed as a generator anyway, following the brief-20
rule that every figure printed in the paper has a committed generator, so that
the figure is reproducible from source rather than hand-drawn.

Output: ``paper/figures/model_flow.png`` (the paper's graphicspath resolves
``figures/`` relative to ``main.tex``).

Run:  python scripts/make_fig_model.py
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(ROOT, "paper", "figures", "model_flow.png")

# muted, print-friendly palette
C_FIRM = "#dfe7ef"
C_WORK = "#e7efe1"
C_CAP = "#f2e9dd"
C_STOCK = "#eae3ef"
C_GOV = "#f3f3f3"
EDGE = "#333333"
GOV_EDGE = "#8a8a8a"
ARROW = "#2b2b2b"
LEAK = "#9a3b3b"  # the leakage flow, drawn in a warning tone


def box(ax, xy, w, h, text, fc, ec=EDGE, ls="solid", fs=10, lw=1.3, tc="#111111"):
    x, y = xy
    ax.add_patch(FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=1.4",
        linewidth=lw, edgecolor=ec, facecolor=fc, linestyle=ls, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, zorder=4,
            color=tc, linespacing=1.3)


def flow(ax, p0, p1, label, rad=0.0, color=ARROW, ls="solid", lw=1.6,
         lxy=None, fs=9, la="center", lc=None):
    ax.add_patch(FancyArrowPatch(
        p0, p1, connectionstyle=f"arc3,rad={rad}",
        arrowstyle="-|>", mutation_scale=15, linewidth=lw,
        color=color, linestyle=ls, zorder=2,
        shrinkA=2, shrinkB=2))
    if label:
        lx, ly = lxy if lxy else ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
        ax.text(lx, ly, label, ha=la, va="center", fontsize=fs,
                color=lc or color, zorder=5,
                bbox=dict(boxstyle="round,pad=0.15", fc="white",
                          ec="none", alpha=0.85))


def main():
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    ax.set_xlim(-2, 110)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # --- agents -----------------------------------------------------------
    box(ax, (50, 62), 34, 13,
        "FIRMS  ($n_f = 10$)\nnormalised CES   $Y^* = f(K, L)$\n"
        "hire $L$, set investment", C_FIRM, fs=10)
    box(ax, (50, 90), 22, 9, "Capital stock  $K$", C_STOCK, fs=10)
    box(ax, (16, 30), 28, 15,
        "WORKER\nHOUSEHOLDS\n$0.9N$, supply labour\nhigh MPC", C_WORK, fs=9.5)
    box(ax, (84, 30), 28, 15,
        "CAPITALIST\nHOUSEHOLDS\n$0.1N$, own firms\nlow MPC", C_CAP, fs=9.5)
    box(ax, (50, 8), 46, 9,
        "GOVERNMENT (optional):\nflat tax on all income   $\\rightarrow$   "
        "unemployment benefit",
        C_GOV, ec=GOV_EDGE, ls=(0, (4, 3)), fs=8.5, tc="#555555")

    # --- capital / investment loop ---------------------------------------
    flow(ax, (44, 68.5), (44, 85.5),
         "Investment\n$I = \\rho\\,\\pi$", rad=0.0,
         lxy=(29.5, 78), fs=8.5)
    flow(ax, (56, 85.5), (56, 68.5), "capacity", rad=0.0, ls=(0, (4, 3)),
         color=GOV_EDGE, lxy=(66.5, 78), fs=8.5, lc="#555555")

    # --- wages / consumption (firms <-> workers) -------------------------
    # Wages leave the firms and enter the workers; consumption is the reverse
    # flow that re-enters the firms.  Each label sits on the outer side of its
    # OWN curve (wages to the right, consumption to the left) so the pairing of
    # label to direction is unambiguous.
    flow(ax, (38, 56), (23, 37.5), "Wages  $\\bar w\\,L$", rad=-0.16,
         lxy=(35, 47), la="center", fs=9)
    flow(ax, (12, 37.5), (33, 56), "Consumption", rad=-0.16,
         lxy=(14, 51), la="center", fs=9)

    # --- dividends / consumption (firms <-> capitalists) -----------------
    flow(ax, (62, 56), (77, 37.5), "Dividends\n$(1-\\rho)\\,\\pi$", rad=0.16,
         lxy=(58, 47), la="center", fs=9)
    flow(ax, (88, 37.5), (67, 56),
         "Consumption\n(low MPC:\ndemand leaks)", rad=0.16, color=LEAK,
         lw=1.9, lxy=(98, 49), la="center", fs=8.5, lc=LEAK)

    # --- government flows (optional, dashed, kept local at the base) ------
    # The flat tax falls on ALL income, so BOTH households pay in -- see
    # src/model.py government(): base = sum over households of
    # max(0, next_income).  Workers also receive the benefit; capitalists only
    # pay.  Two "Tax" arrows (one per household) + one "Benefit" arrow.
    flow(ax, (80, 22.5), (61, 12.5), "Tax  $\\tau$", rad=0.0,
         ls=(0, (4, 3)), color=GOV_EDGE, lxy=(74, 16.5), fs=8.5, lc="#555555")
    flow(ax, (22, 22.5), (39, 12.5), "Tax  $\\tau$", rad=0.0,
         ls=(0, (4, 3)), color=GOV_EDGE, lxy=(35, 15.5), fs=8.5, lc="#555555")
    flow(ax, (31, 12.5), (12, 22.5), "Benefit", rad=0.0,
         ls=(0, (4, 3)), color=GOV_EDGE, lxy=(16, 16.5), fs=8.5, lc="#555555")

    # --- wage-curve note --------------------------------------------------
    ax.text(2, 96,
            "Wage $\\bar w$ set by a Blanchflower–Oswald curve "
            "(responds to unemployment $U$)",
            ha="left", va="center", fontsize=8, style="italic",
            color="#555555")

    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    fig.savefig(OUT, dpi=200)
    print(f"wrote {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()

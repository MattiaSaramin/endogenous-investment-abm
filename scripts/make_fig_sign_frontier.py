#!/usr/bin/env python
"""Redraw the sign-frontier figure (Fig. ``fig:frontier``) for the paper, no simulation.

Brief 30 §2.1.  ``ces_sign_frontier.png`` (Fig. 3) is an old brief-04 figure whose only
generator was a notebook cell; it was never regenerated, so its committed PNG predates the
current matplotlib and, unlike the other paper figures, does not reproduce byte-for-byte.
This script gives it a committed generator (the brief-20 rule: every figure printed in the
paper has a committed generator) AND regenerates it at paper scale.

:func:`experiment.plot_sign_frontier` takes ``grid`` in its signature but uses only
``deriv``, so the figure is a pure function of ``results/ces_derivatives.csv`` - it is
reconstructable with NO simulation.  This script reads that CSV, calls the plotter with
``for_paper=True`` (print-scale figsize, ticks only on the measured non-uniform nodes, a
marker on every measured cell), writes ``results/ces_sign_frontier.png`` and copies it to
``paper/figures/`` (the paper's graphicspath resolves ``figures/`` first).  It writes NO
``.csv``.

Run:  python scripts/make_fig_sign_frontier.py
"""
from __future__ import annotations

import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.abspath(os.path.join(_HERE, "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import pandas as pd

from experiment import plot_sign_frontier

RESULTS = os.path.abspath(os.path.join(_HERE, "..", "results"))
PAPER_FIGURES = os.path.abspath(os.path.join(_HERE, "..", "paper", "figures"))


def main():
    deriv_path = os.path.join(RESULTS, "ces_derivatives.csv")
    if not os.path.exists(deriv_path):
        print(f"  ERROR: {deriv_path} not found - cannot draw the sign frontier.")
        return 1
    deriv = pd.read_csv(deriv_path)

    out = os.path.join(RESULTS, "ces_sign_frontier.png")
    # grid is unused by the plotter (see its docstring); pass None to make that explicit.
    plot_sign_frontier(None, deriv, out, for_paper=True)
    print(f"  wrote {out}  (from ces_derivatives.csv, no simulation)")

    dst = os.path.join(PAPER_FIGURES, "ces_sign_frontier.png")
    shutil.copyfile(out, dst)
    print(f"  copied to {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

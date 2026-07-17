#!/usr/bin/env python
"""Regenerate the brief-05 robustness stack (stages A, B, C) — reproducibly.

Brief 05 built the CES robustness layer on top of the brief-04 sign frontier: it keeps
the *per-seed* panel instead of collapsing to cell means, takes ``dY/drho`` as an OLS
slope over the whole common viable support, and puts a bootstrap CI on ``sigma*`` (with
an honest count of the resamples where the sign never turns).  The analysis primitives
all live in :mod:`experiment`; this script is the **orchestration** that ties them into
the twelve ``ces_b05_*.csv`` outputs and — the point of committing it — makes those
outputs reproducible from committed code rather than an ad-hoc session.

Three stages (brief 05):

* **Stage A** — the headline grid.  ``(sigma, rho)`` swept at ``c0 in {1.0, 2.0}``,
  20 seeds, anchored at rho = 0.40 (the brief-04 anchor).  Everything downstream
  (slopes, sigma*, distribution slopes, curvature, support sensitivity) is read off it.
* **Stage B** — the ``c0 = 0.5`` mechanism probe (a subset of sigma), used only to show
  that workers stay cash-constrained below ``w_bar`` too, so c0 is a scale lever, not the
  source of the MPC gap.  The panel is written; the reading is in ``parameter_notes.md``.
* **Stage C** — the re-anchoring check (Temple 2012): the same grid at ``c0 = 1.0`` with
  the anchor moved to rho = 0.50 (``model.ANCHOR_*_RHO050``), so ``sigma*`` can be tested
  for dependence on the anchor.

Determinism: the model is deterministic per seed, the bootstrap is deterministic given
its ``rng_seed`` (default 20260717), and cells share no state — so ``workers`` only
changes wall-clock time, never a number.  The panels are byte-identical whatever the
threading; the *derived* tables (cell means, OLS slopes, bootstrap CIs, curvature) go
through float reductions whose order depends on the BLAS thread count, so the module
pins BLAS to one thread (below) to make them reproducible byte-for-byte on any host.

Usage
-----
    python scripts/run_brief05.py                 # -> results/, all cores, threads pinned
    python scripts/run_brief05.py --out results   # explicit output directory
    python scripts/run_brief05.py --workers 1     # serial (slow)
"""

from __future__ import annotations

import argparse
import os
import sys

# Make ``src/`` importable here AND in the process-pool children (Windows spawns fresh
# interpreters that re-import ``experiment``/``model`` and only inherit sys.path via the
# environment).
_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
os.environ["PYTHONPATH"] = _SRC + os.pathsep + os.environ.get("PYTHONPATH", "")

# Pin BLAS/numpy to a single thread, set BEFORE numpy is imported (here, via pandas)
# and inherited by the process-pool children.  Two reasons: (1) it makes the reduction
# order in the bootstrap and the cell means deterministic and machine-independent, so
# the committed CSVs are reproducible byte-for-byte from this driver on any host; and
# (2) it stops the 12 worker processes from each spawning a full BLAS thread pool, which
# oversubscribes the cores and makes the run several times slower.  The simulation path
# itself is thread-invariant (the panels are byte-identical either way); this only fixes
# the float reduction order in the derived tables.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import pandas as pd

from experiment import (
    SIGMA_SWEEP_B05,
    RHO_SWEEP_B05,
    bootstrap_sigma_star,
    cells_from_panel,
    common_viable_support,
    quadratic_curvature,
    run_grid_panel,
    sigma_star_by_rho,
    slopes_by_sigma,
)
from model import ANCHOR_K0_RHO050, ANCHOR_L0_RHO050

# Stage A / C sweep the full brief-05 grid; stage B only a sigma subset.
C0_STAGE_A = [1.0, 2.0]
STAGE_B_SIGMAS = [0.3, 0.5, 0.8, 1.0]
STAGE_B_C0 = 0.5
STAGE_C_C0 = 1.0

#: Candidate supports for the sensitivity table.  A support is run only if every rho in
#: it is viable at that c0; otherwise it is recorded as not viable (the collapse is an
#: outcome, brief 05).
SUPPORT_CANDIDATES = [
    ("full 0.35-0.65", [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65]),
    ("0.40-0.65", [0.40, 0.45, 0.50, 0.55, 0.60, 0.65]),
    ("0.45-0.65", [0.45, 0.50, 0.55, 0.60, 0.65]),
    ("0.35-0.60", [0.35, 0.40, 0.45, 0.50, 0.55, 0.60]),
    ("0.35-0.55", [0.35, 0.40, 0.45, 0.50, 0.55]),
    ("0.40-0.60 (brief04-like)", [0.40, 0.45, 0.50, 0.55, 0.60]),
]

#: The distribution metrics whose OLS slope on rho goes into the distribution table, and
#: the column stem each one gets (Output is renamed to Y and Unemployment_Rate to U by
#: cells_from_panel / by convention).
_DIST_METRICS = [
    ("Wage_Share", "dWage_Share"),
    ("Income_Gini", "dIncome_Gini"),
    ("Wealth_Gini", "dWealth_Gini"),
    ("Y", "dY"),
    ("Unemployment_Rate", "dU"),
    ("Output_Gap", "dOutput_Gap"),
]


# ----------------------------------------------------------------------
# Derived tables (all read off the per-seed panels)
# ----------------------------------------------------------------------

def _distribution_slopes(cells, support):
    """OLS slope (and SE) of each distribution metric on rho, per sigma."""
    merged = None
    for col, stem in _DIST_METRICS:
        s = slopes_by_sigma(cells, support, column=col)
        s = s[["sigma", f"d{col}_drho", "se"]].rename(
            columns={f"d{col}_drho": stem, "se": f"{stem}_se"}
        )
        merged = s if merged is None else merged.merge(s, on="sigma")
    return merged


def _curvature(cells, support):
    """Quadratic OLS of Y on rho, per sigma: the curvature and its turning point."""
    lo, hi = min(support), max(support)
    rows = []
    for sigma, block in cells.groupby("sigma"):
        b = block[block["rho"].isin(support)].sort_values("rho")
        quad, se, turn = quadratic_curvature(b["rho"], b["Y"])
        rows.append({
            "sigma": sigma,
            "quad_coef": quad,
            "se": se,
            "t": quad / se if se and se == se and se > 0 else float("nan"),
            "turning_rho": turn,
            "turn_in_support": bool(turn == turn and lo <= turn <= hi),
        })
    return pd.DataFrame(rows).sort_values("sigma", ignore_index=True)


def _support_sensitivity(panel, viable_support):
    """Bootstrap sigma* over each candidate support; mark the non-viable ones."""
    viable = set(round(r, 10) for r in viable_support)
    rows = []
    for label, support in SUPPORT_CANDIDATES:
        if all(round(r, 10) in viable for r in support):
            bs = bootstrap_sigma_star(panel, support, column="Output")
            rows.append({
                "support": label,
                "sigma_star": bs["sigma_star"],
                "ci_lo": bs["ci_lo"],
                "ci_hi": bs["ci_hi"],
                "frac_undefined": bs["frac_undefined"],
                "n_rho": len(support),
                "P_gt_0.60": bs["frac_star_above_0_60"],
                "note": "",
            })
        else:
            rows.append({
                "support": label,
                "sigma_star": float("nan"),
                "ci_lo": float("nan"),
                "ci_hi": float("nan"),
                "frac_undefined": float("nan"),
                "n_rho": len(support),
                "P_gt_0.60": float("nan"),
                "note": "not viable at this c0",
            })
    return pd.DataFrame(rows)


def _sigma_star_row(panel, support, estimator, column):
    """One bootstrap sigma* row (the OLS-global estimator, on Y or U)."""
    bs = bootstrap_sigma_star(panel, support, column=column)
    return {
        "estimator": estimator,
        "rho": "all",
        "sigma_star": bs["sigma_star"],
        "ci_lo": bs["ci_lo"],
        "ci_hi": bs["ci_hi"],
        "frac_undefined": bs["frac_undefined"],
        "frac_multi_crossing": bs["frac_multi_crossing"],
        "frac_star_above_0_60": bs["frac_star_above_0_60"],
        "frac_star_above_0_40": bs["frac_star_above_0_40"],
        "n_crossings": bs["n_crossings"],
    }


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="results", help="output directory (default: results)")
    ap.add_argument("--workers", type=int, default=None,
                    help="process-pool size (default: all cores; 1 = serial)")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    def write(df, name):
        path = os.path.join(out, name)
        df.to_csv(path, index=False)
        print(f"  wrote {name:36s} {df.shape[0]:>5d} rows")
        return df

    W = args.workers

    # ---- Stage A: the headline grid at c0 in {1, 2} -------------------
    print("Stage A — headline grid (sigma x rho x c0), 20 seeds:")
    stage_a_panels, stage_a_cells, stage_a_slopes = [], [], []
    sigma_star_rows, by_rho_frames = [], []
    dist_frames, curv_frames, support_frames = [], [], []
    supports_by_c0 = {}

    for c0 in C0_STAGE_A:
        panel = run_grid_panel(seeds=20, workers=W, c0=c0)
        cells = cells_from_panel(panel)
        support = common_viable_support(cells)
        supports_by_c0[c0] = support
        print(f"  c0={c0}: common viable support = {support}")

        stage_a_panels.append(panel.assign(c0=c0))
        stage_a_cells.append(cells.assign(c0=c0))
        stage_a_slopes.append(slopes_by_sigma(cells, support, column="Y").assign(c0=c0))

        sigma_star_rows.append({"c0": c0, **_sigma_star_row(panel, support, "ols_global", "Output")})
        sigma_star_rows.append({"c0": c0, **_sigma_star_row(panel, support, "ols_global_U", "Unemployment_Rate")})

        by_rho_frames.append(sigma_star_by_rho(panel, support, column="Output").assign(c0=c0))
        dist_frames.append(_distribution_slopes(cells, support).assign(c0=c0))
        curv_frames.append(_curvature(cells, support).assign(c0=c0))
        support_frames.append(_support_sensitivity(panel, support).assign(c0=c0))

    write(pd.concat(stage_a_panels, ignore_index=True), "ces_b05_stage_a_panel.csv")
    write(pd.concat(stage_a_cells, ignore_index=True), "ces_b05_stage_a_cells.csv")
    write(pd.concat(stage_a_slopes, ignore_index=True), "ces_b05_stage_a_slopes.csv")

    # sigma_star: c0 first, then the estimator block
    star = pd.DataFrame(sigma_star_rows)
    star = star[["c0", "estimator", "rho", "sigma_star", "ci_lo", "ci_hi",
                 "frac_undefined", "frac_multi_crossing",
                 "frac_star_above_0_60", "frac_star_above_0_40", "n_crossings"]]
    write(star, "ces_b05_sigma_star.csv")
    write(pd.concat(by_rho_frames, ignore_index=True), "ces_b05_sigma_star_by_rho.csv")

    dist = pd.concat(dist_frames, ignore_index=True)
    dist = dist[["c0", "sigma"] + [c for c in dist.columns if c not in ("c0", "sigma")]]
    write(dist, "ces_b05_distribution_slopes.csv")

    curv = pd.concat(curv_frames, ignore_index=True)
    curv = curv[["c0", "sigma", "quad_coef", "se", "t", "turning_rho", "turn_in_support"]]
    write(curv, "ces_b05_curvature.csv")

    supp = pd.concat(support_frames, ignore_index=True)
    supp = supp[["c0", "support", "sigma_star", "ci_lo", "ci_hi",
                 "frac_undefined", "n_rho", "P_gt_0.60", "note"]]
    write(supp, "ces_b05_support_sensitivity.csv")

    # ---- Stage B: the c0 = 0.5 mechanism probe -----------------------
    print("Stage B — c0 = 0.5 mechanism probe:")
    panel_b = run_grid_panel(sigmas=STAGE_B_SIGMAS, seeds=20, workers=W, c0=STAGE_B_C0)
    write(panel_b.assign(c0=STAGE_B_C0), "ces_b05_stage_b_panel.csv")

    # ---- Stage C: the re-anchoring check (anchor at rho = 0.50) -------
    print("Stage C — re-anchored grid (anchor rho = 0.50), c0 = 1.0:")
    panel_c = run_grid_panel(
        seeds=20, workers=W, c0=STAGE_C_C0,
        K0=ANCHOR_K0_RHO050, L0=ANCHOR_L0_RHO050,
    )
    write(panel_c.assign(c0=STAGE_C_C0, anchor="rho050"), "ces_b05_stage_c_panel.csv")

    # anchor comparison: sigma*(rho) at the rho=0.40 anchor (stage A, c0=1.0) vs the
    # rho=0.50 anchor (stage C, c0=1.0).  If sigma* moves, it depends on the anchor.
    print("Anchor comparison (rho=0.40 vs rho=0.50):")
    panel_a_c0_1 = stage_a_panels[0].drop(columns="c0")
    support_a = supports_by_c0[1.0]
    cells_c = cells_from_panel(panel_c)
    support_c = common_viable_support(cells_c)
    anchor_040 = sigma_star_by_rho(panel_a_c0_1, support_a, column="Output").assign(
        anchor="rho=0.40 (brief 04)")
    anchor_050 = sigma_star_by_rho(panel_c, support_c, column="Output").assign(
        anchor="rho=0.50 (brief 05)")
    write(pd.concat([anchor_040, anchor_050], ignore_index=True), "ces_b05_anchor_comparison.csv")

    # ---- c0 shared support: sigma* for Y and U on the support viable at BOTH c0 ----
    print("c0 shared-support comparison:")
    shared = [r for r in supports_by_c0[1.0] if r in set(supports_by_c0[2.0])]
    print(f"  shared support = {shared}")
    rows = []
    for i, c0 in enumerate(C0_STAGE_A):
        panel = stage_a_panels[i].drop(columns="c0")
        for target, column in (("Y", "Output"), ("U", "Unemployment_Rate")):
            bs = bootstrap_sigma_star(panel, shared, column=column)
            rows.append({
                "c0": c0, "target": target, "support": "shared",
                "sigma_star": bs["sigma_star"], "ci_lo": bs["ci_lo"], "ci_hi": bs["ci_hi"],
                "frac_undefined": bs["frac_undefined"],
                "P_star_gt_0.60": bs["frac_star_above_0_60"],
                "P_star_gt_0.40": bs["frac_star_above_0_40"],
            })
    write(pd.DataFrame(rows), "ces_b05_c0_shared_support.csv")

    print(f"\nDone. Twelve ces_b05_*.csv written to {out}")


if __name__ == "__main__":
    main()

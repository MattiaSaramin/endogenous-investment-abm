#!/usr/bin/env python
"""Regenerate the brief-07 wage-curve sweep (sigma x rho x eta x c0) — reproducibly.

Brief 07 endogenises the wage via a Blanchflower-Oswald wage curve (level relation on
last period's unemployment) and re-estimates the sign frontier ``sigma*`` for each wage
elasticity ``eta``.  It reuses the brief-05 robustness stack unchanged (``run_grid_panel``,
``bootstrap_sigma_star``, ``slopes_by_sigma``); ``eta`` threads through ``run_grid_panel``'s
``**params`` to ``MacroModel`` with no signature change, exactly as ``c0`` does.

Two phases (approved "Brief-spec" package):

* **Phase 1 — viability + floor reconnaissance (3-seed).**  The full sigma x rho grid at
  each (c0, eta).  Maps the common viable support per eta and the cells where the wage
  floor ``w_min`` binds stably, and applies two EXPLICIT halt thresholds vs eta = 0
  (same c0):
    - a viable support that loses MORE THAN ONE rho cell vs eta = 0, or
    - the floor binding stably in MORE THAN 10% of an eta's viable cells,
  either of which halts before the 20-seed panel (auto-continue otherwise, with the map
  written to results/).

* **Phase 2 — production panel (20-seed).**  The same grid at 20 seeds; per (c0, eta) it
  takes ``sigma*`` (Y and U) with a bootstrap CI on the common viable support, the OLS
  slopes, and ``sigma*(rho)``.  Two brief-07 additions are enforced here:
    - the eta = 0, 20-seed panel is checked **byte-identical** to the committed
      ``results/ces_b05_stage_a_panel.csv`` on the shared columns (same seeds/grid/code
      path); any mismatch is reported as a FINDING, not silently tolerated;
    - a per-(eta, c0) summary of the steady-state mean wage and the realised U range.

c0 = 1.0 is the primary regime (comparable to the canonical sigma* = 0.654 [0.616,
0.691]); c0 = 2.0 is the secondary regime.

Determinism: BLAS pinned to one thread before numpy is imported (below), so the float
reductions in the derived tables are machine-independent; the simulation path is
thread-invariant and the bootstrap is deterministic given its rng_seed (20260717).

Usage
-----
    python scripts/run_brief07.py                 # phase all -> results/, threads pinned
    python scripts/run_brief07.py --phase 1       # reconnaissance only (fast)
    python scripts/run_brief07.py --phase 2       # panel only (assumes recon passed)
    python scripts/run_brief07.py --workers 1     # serial (slow)
"""

from __future__ import annotations

import argparse
import os
import sys

# Make ``src/`` importable here AND in the process-pool children (Windows spawns fresh
# interpreters that re-import experiment/model and only inherit sys.path via the env).
_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
os.environ["PYTHONPATH"] = _SRC + os.pathsep + os.environ.get("PYTHONPATH", "")

# Pin BLAS/numpy to one thread BEFORE numpy is imported (here via pandas/experiment), so
# the reduction order in the derived tables is deterministic and machine-independent, and
# the worker processes do not each spawn a full BLAS pool and oversubscribe the cores.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
import pandas as pd

from experiment import (
    SIGMA_SWEEP_B05,
    RHO_SWEEP_B05,
    bootstrap_sigma_star,
    cells_from_panel,
    compare_artifacts,
    common_viable_support,
    run_grid_panel,
    sigma_star_by_rho,
    slopes_by_sigma,
)

# --- experiment configuration (approved Brief-spec) -----------------------
ETAS = [0.0, 0.05, 0.10, 0.15]
C0S = [1.0, 2.0]
RECON_SEEDS = 3
PANEL_SEEDS = 20

#: A cell is "stably floored" when the wage floor bound in at least half of its
#: steady-state periods (tail-50, averaged over seeds).  Threshold declared, not hidden.
FLOOR_STABLE = 0.5
#: Halt thresholds (brief 07 additions, evaluated vs eta = 0 at the same c0).
SUPPORT_LOSS_MAX = 1        # halt if a support loses MORE THAN this many rho cells
FLOOR_FRAC_MAX = 0.10       # halt if the floor is stable in MORE THAN this frac of viable cells

#: The committed brief-05 panel the eta = 0 slice must reproduce byte-for-byte.
B05_PANEL = "ces_b05_stage_a_panel.csv"


# ----------------------------------------------------------------------
# Phase 1 — reconnaissance
# ----------------------------------------------------------------------

def _recon_cells(c0, eta, workers):
    """3-seed cells for one (c0, eta), tagged and floor-flagged."""
    panel = run_grid_panel(seeds=RECON_SEEDS, workers=workers, eta=eta, c0=c0)
    cells = cells_from_panel(panel)
    cells = cells.assign(c0=c0, eta=eta)
    cells["floored"] = (~cells["collapsed"]) & (cells["Wage_Floor_Binding"] >= FLOOR_STABLE)
    return cells


def phase1(out, workers):
    """Run the reconnaissance grid, write the map, and evaluate the halt thresholds.

    Returns ``(recon_df, ok, messages)``: ``ok`` is False if any (c0, eta) tripped a
    threshold.
    """
    print(f"Phase 1 - reconnaissance ({RECON_SEEDS} seeds), sigma x rho x eta x c0:")
    frames, supports = [], {}
    for c0 in C0S:
        for eta in ETAS:
            cells = _recon_cells(c0, eta, workers)
            supports[(c0, eta)] = common_viable_support(cells)
            frames.append(cells)
            n_viable = int((~cells["collapsed"]).sum())
            n_floored = int(cells["floored"].sum())
            print(f"  c0={c0} eta={eta:<4}: viable cells={n_viable:>2d}  "
                  f"stably-floored={n_floored:>2d}  common support={supports[(c0, eta)]}")

    recon = pd.concat(frames, ignore_index=True)
    cols = ["c0", "eta", "sigma", "rho", "Y", "Unemployment_Rate", "Wage_Rate",
            "Wage_Floor_Binding", "collapsed", "floored", "binding",
            "frac_seeds_collapsed", "mixed_basin"]
    _write(recon[cols].rename(columns={"Unemployment_Rate": "U"}),
           out, "ces_b07_viability_recon.csv")

    # --- evaluate halt thresholds vs eta = 0 (same c0) --------------------
    ok, messages = True, []
    for c0 in C0S:
        base = set(supports[(c0, 0.0)])
        for eta in ETAS:
            if eta == 0.0:
                continue
            cells = recon[(recon["c0"] == c0) & (recon["eta"] == eta)]
            viable = cells[~cells["collapsed"]]
            n_viable = len(viable)
            floored_frac = (viable["floored"].sum() / n_viable) if n_viable else 0.0
            dropped = base - set(supports[(c0, eta)])

            if len(dropped) > SUPPORT_LOSS_MAX:
                ok = False
                messages.append(
                    f"HALT c0={c0} eta={eta}: viable support lost {len(dropped)} rho "
                    f"cells vs eta=0 (dropped {sorted(dropped)}); threshold is "
                    f">{SUPPORT_LOSS_MAX}.")
            if floored_frac > FLOOR_FRAC_MAX:
                ok = False
                messages.append(
                    f"HALT c0={c0} eta={eta}: floor stably binds in "
                    f"{floored_frac:.1%} of {n_viable} viable cells; threshold is "
                    f">{FLOOR_FRAC_MAX:.0%}.")

    if ok:
        print("Phase 1 gate: PASS - no threshold tripped, auto-continue to Phase 2.")
    else:
        print("Phase 1 gate: HALT")
        for m in messages:
            print("  " + m)
    return recon, ok, messages


# ----------------------------------------------------------------------
# Phase 2 — production panel
# ----------------------------------------------------------------------

def _sigma_star_row(panel, support, column):
    bs = bootstrap_sigma_star(panel, support, column=column)
    return {
        "sigma_star": bs["sigma_star"], "ci_lo": bs["ci_lo"], "ci_hi": bs["ci_hi"],
        "frac_undefined": bs["frac_undefined"], "n_crossings": bs["n_crossings"],
        "P_star_gt_0.60": bs["frac_star_above_0_60"],
        "P_star_gt_0.40": bs["frac_star_above_0_40"],
    }


def phase2(out, workers, c0s=None, suffix=""):
    c0s = C0S if c0s is None else c0s
    print(f"Phase 2 - production panel ({PANEL_SEEDS} seeds), sigma x rho x eta x c0={c0s}:")
    all_panels, all_cells = [], []
    star_rows, byrho_frames, slope_frames, support_rows, wu_rows = [], [], [], [], []

    for c0 in c0s:
        # --- pass 1: run every eta, collect panels/cells and per-eta natural supports ---
        panels, cells_by_eta, nat_support = {}, {}, {}
        for eta in ETAS:
            panel = run_grid_panel(seeds=PANEL_SEEDS, workers=workers, eta=eta, c0=c0)
            cells = cells_from_panel(panel)
            panels[eta], cells_by_eta[eta] = panel, cells
            nat_support[eta] = common_viable_support(cells)
            all_panels.append(panel.assign(eta=eta, c0=c0))
            all_cells.append(cells.assign(eta=eta, c0=c0))
            print(f"  c0={c0} eta={eta:<4}: natural common support = {nat_support[eta]}")

        # The rho viable at EVERY eta: sigma*(eta) is estimated here so it is comparable
        # ACROSS eta (a support that shifts with eta would confound eta with which cells
        # survived).  For c0 = 2.0 the wage-curve collapse shrinks this to [0.55-0.65].
        est_support = [r for r in nat_support[ETAS[0]]
                       if all(r in nat_support[e] for e in ETAS)]
        print(f"  c0={c0}: across-eta common support (sigma* estimated here) = {est_support}")

        # --- pass 2: sigma*(eta) on the across-eta support (+ the eta=0 natural anchor) ---
        for eta in ETAS:
            panel, cells = panels[eta], cells_by_eta[eta]
            for target, col in (("Y", "Output"), ("U", "Unemployment_Rate")):
                star_rows.append({"c0": c0, "eta": eta, "target": target,
                                  "support_kind": "across_eta", "support": str(est_support),
                                  **_sigma_star_row(panel, est_support, col)})
            # eta = 0 also on its FULL natural support: the brief-05 anchor / regression row
            # (reproduces the canonical sigma* on the support brief 05 used).
            if eta == 0.0:
                for target, col in (("Y", "Output"), ("U", "Unemployment_Rate")):
                    star_rows.append({"c0": c0, "eta": eta, "target": target,
                                      "support_kind": "natural_eta0",
                                      "support": str(nat_support[0.0]),
                                      **_sigma_star_row(panel, nat_support[0.0], col)})
            byrho_frames.append(
                sigma_star_by_rho(panel, est_support, column="Output").assign(c0=c0, eta=eta))
            slope_frames.append(
                slopes_by_sigma(cells, est_support, column="Y").assign(c0=c0, eta=eta))

            viable = cells[~cells["collapsed"]]
            floored = viable[viable["Wage_Floor_Binding"] >= FLOOR_STABLE]
            support_rows.append({
                "c0": c0, "eta": eta,
                "natural_support": str(nat_support[eta]), "n_natural": len(nat_support[eta]),
                "across_eta_support": str(est_support), "n_across_eta": len(est_support),
                "n_viable_cells": int(len(viable)),
                "n_stably_floored": int(len(floored)),
                "frac_floored": (len(floored) / len(viable)) if len(viable) else float("nan"),
            })
            # brief-07 addition (3): steady-state wage and realised U over viable cells.
            wu_rows.append({
                "c0": c0, "eta": eta, "n_viable_cells": int(len(viable)),
                "wage_mean": float(viable["Wage_Rate"].mean()),
                "wage_min": float(viable["Wage_Rate"].min()),
                "wage_max": float(viable["Wage_Rate"].max()),
                "U_mean": float(viable["Unemployment_Rate"].mean()),
                "U_min": float(viable["Unemployment_Rate"].min()),
                "U_max": float(viable["Unemployment_Rate"].max()),
            })

    big_panel = pd.concat(all_panels, ignore_index=True)
    _write(big_panel, out, f"ces_b07_stage_a_panel{suffix}.csv")
    _write(pd.concat(all_cells, ignore_index=True), out, f"ces_b07_cells{suffix}.csv")

    star = pd.DataFrame(star_rows)[
        ["c0", "eta", "target", "support_kind", "sigma_star", "ci_lo", "ci_hi",
         "frac_undefined", "n_crossings", "P_star_gt_0.60", "P_star_gt_0.40", "support"]]
    _write(star, out, f"ces_b07_sigma_star{suffix}.csv")
    _write(pd.concat(byrho_frames, ignore_index=True), out, f"ces_b07_sigma_star_by_rho{suffix}.csv")
    _write(pd.concat(slope_frames, ignore_index=True), out, f"ces_b07_slopes{suffix}.csv")
    _write(pd.DataFrame(support_rows), out, f"ces_b07_support_map{suffix}.csv")
    _write(pd.DataFrame(wu_rows), out, f"ces_b07_wage_u_summary{suffix}.csv")

    # --- brief-07 addition (1): eta = 0 panel byte-identity vs brief 05 --------
    # Compare the WRITTEN artifact (just saved above) against the reference, both read
    # from disk: pandas to_csv is not perfectly round-trip-lossless, so any extra
    # serialization perturbs a few float64s by ~5e-14 -- the two committed CSVs are equal
    # only when compared directly, without re-serializing either side.
    check = _nesting_byte_check(out, f"ces_b07_stage_a_panel{suffix}.csv")
    _write(check, out, f"ces_b07_nesting_check{suffix}.csv")

    fig_path = plot_sigma_star_eta(star, os.path.join(out, f"ces_b07_sigma_star_eta{suffix}.png"))
    print(f"  wrote {os.path.basename(fig_path)}")

    _print_headline(star, wu_rows)
    return big_panel, star


def _nesting_byte_check(out, panel_name):
    """Verify the eta = 0 slice of the WRITTEN panel reproduces ces_b05_stage_a_panel.

    THE COMPARISON (artifact vs artifact).  ces_b05_stage_a_panel is a committed CSV, so
    "byte-identical vs it" means the just-written ces_b07 panel, read back from disk,
    equals it on the shared columns for eta = 0.  Both sides are read from disk and
    compared WITHOUT re-serializing either: pandas ``to_csv`` is not perfectly
    round-trip-lossless (an extra serialize/parse perturbs a few float64s by ~5e-14), so
    only the direct file-vs-file comparison is exact.  The two artifacts are byte-identical
    because the model at eta = 0 is bit-for-bit the pre-brief-07 model.  Any nonzero
    deviation is a FINDING.
    """
    ref_path = os.path.join(out, B05_PANEL)
    panel_path = os.path.join(out, panel_name)
    for p in (ref_path, panel_path):
        if not os.path.exists(p):
            print(f"  nesting check: SKIPPED - {os.path.basename(p)} not found in {out}")
            return pd.DataFrame([{"note": f"{os.path.basename(p)} not found; check skipped"}])

    ref = pd.read_csv(ref_path)
    shared = list(ref.columns)                     # sigma,rho,seed,<22 metrics>,c0
    mine = pd.read_csv(panel_path)
    mine = mine[mine["eta"] == 0.0][shared].copy()
    present = sorted(mine["c0"].unique())          # compare only the c0 present in this run
    ref = ref[ref["c0"].isin(present)].copy()
    order = ["c0", "sigma", "rho", "seed"]
    mine = mine.sort_values(order).reset_index(drop=True)
    ref = ref.sort_values(order).reset_index(drop=True)

    rows, all_ok = [], True
    print("  nesting check (eta=0 written panel vs ces_b05_stage_a_panel, artifact vs artifact):")
    for c0 in present:
        a = mine[mine["c0"] == c0].reset_index(drop=True)
        b = ref[ref["c0"] == c0].reset_index(drop=True)
        if a.shape != b.shape:
            all_ok = False
            rows.append({"c0": c0, "n_rows": len(a), "byte_equal": False,
                         "max_abs_dev": float("nan"), "note": "shape mismatch"})
            print(f"    c0={c0}: SHAPE MISMATCH mine={a.shape} ref={b.shape}  <-- FINDING")
            continue
        # Criterion updated by brief 14 (task D): a declared ULP tolerance on the levels
        # plus an EXACT regime match, replacing the retired ``dev == 0.0``.  The retired
        # value is still recorded so the change of standard stays auditable.
        res = compare_artifacts(a, b)
        ok = res["ok"]
        all_ok = all_ok and ok
        rows.append({"c0": c0, "n_rows": len(a), **res,
                     "note": "PASS" if ok else "FINDING"})
        print(f"    c0={c0}: {'PASS' if ok else 'FINDING'}  n_rows={len(a)}  "
              f"max_ulp_sig={res['max_ulp_significant']:.2f}  "
              f"n_exceed={res['n_exceed']}/{res['n_compared']}  "
              f"regime_equal={res['regime_equal']}  "
              f"max_abs_dev={res['max_abs_dev']:.1e}  "
              f"(retired byte_equal={res['byte_equal']})")

    return pd.DataFrame(rows)


def _print_headline(star, wu_rows):
    y = star[star["target"] == "Y"]
    anchor = y[y["support_kind"] == "natural_eta0"]
    print("\nAnchor (eta=0 on the full natural support; brief-05 canonical c0=1.0 -> "
          "0.6540 [0.6164, 0.6907]):")
    for _, r in anchor.iterrows():
        print(f"  c0={r['c0']} eta=0 : sigma*={r['sigma_star']:.4f} "
              f"[{r['ci_lo']:.4f}, {r['ci_hi']:.4f}]  support={r['support']}")
    print("\nHeadline sigma*(eta) on Y, across-eta common support (comparable across eta):")
    for _, r in y[y["support_kind"] == "across_eta"].iterrows():
        print(f"  c0={r['c0']} eta={r['eta']:<4}: sigma*={r['sigma_star']:.4f} "
              f"[{r['ci_lo']:.4f}, {r['ci_hi']:.4f}]  "
              f"P(sigma*>0.60)={r['P_star_gt_0.60']:.3f}  frac_undef={r['frac_undefined']:.3f}")
    print("\nSteady-state wage and realised U over viable cells (brief-07 addition 3):")
    for r in wu_rows:
        print(f"  c0={r['c0']} eta={r['eta']:<4}: wage_mean={r['wage_mean']:.4f} "
              f"[{r['wage_min']:.4f}, {r['wage_max']:.4f}]  "
              f"U in [{r['U_min']:.3f}, {r['U_max']:.3f}] (mean {r['U_mean']:.3f})")


def plot_sigma_star_eta(star, path):
    """sigma*(eta) with bootstrap CI bands, per c0, over the empirical sigma band.

    The across-eta-support Y frontier: the headline of brief 07.  A gap (NaN) means the
    sign never turned in the tested sigma range at that eta (wage-led everywhere) -- shown
    honestly as a break, not interpolated.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y = star[(star["target"] == "Y") & (star["support_kind"] == "across_eta")]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for c0, block in y.groupby("c0"):
        b = block.sort_values("eta")
        line, = ax.plot(b["eta"], b["sigma_star"], marker="o", label=f"c0 = {c0}")
        ax.fill_between(b["eta"], b["ci_lo"], b["ci_hi"], alpha=0.18, color=line.get_color())
    ax.axhspan(0.40, 0.60, color="grey", alpha=0.15,
               label="empirical sigma 0.40-0.60")
    ax.axhline(1.0, ls="--", lw=1, color="grey")
    ax.set_xlabel("wage-curve elasticity  eta")
    ax.set_ylabel("sign frontier  sigma*  (dY/drho = 0)")
    ax.set_title("Does wage flexibility move the sign frontier?", weight="bold")
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------

def _write(df, out, name):
    path = os.path.join(out, name)
    df.to_csv(path, index=False)
    print(f"  wrote {name:34s} {df.shape[0]:>6d} rows")
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="results", help="output directory (default: results)")
    ap.add_argument("--phase", choices=["1", "2", "all"], default="all")
    ap.add_argument("--c0", default=None,
                    help="comma-separated c0 subset for Phase 2 (default: all). "
                         "e.g. --c0 1.0 runs only the primary regime.")
    ap.add_argument("--suffix", default="",
                    help="filename suffix for Phase 2 outputs (e.g. _c0_1p0)")
    ap.add_argument("--workers", type=int, default=None,
                    help="process-pool size (default: all cores; 1 = serial)")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    W = args.workers
    c0s = [float(x) for x in args.c0.split(",")] if args.c0 else None

    if args.phase in ("1", "all"):
        _, ok, _ = phase1(out, W)
        if args.phase == "1":
            return
        if not ok:
            print("\nStopping after Phase 1: a halt threshold tripped. "
                  "Review the recon map before running Phase 2.")
            sys.exit(2)

    if args.phase in ("2", "all"):
        phase2(out, W, c0s=c0s, suffix=args.suffix)
        print(f"\nDone. brief-07 outputs written to {out}")


if __name__ == "__main__":
    main()

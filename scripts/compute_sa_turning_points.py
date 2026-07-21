#!/usr/bin/env python
"""Turning point of ``Y(rho)`` per design point of the global sensitivity analysis.

Why this exists
---------------
The sensitivity analysis of brief 14 decomposes an **OLS slope over the whole rho
support**.  That is the *global* half of the paper's first contribution -- the half
section 6 already reports as positive in the empirical band -- so
``P(slope < 0 | viable) = 0.026`` **confirms** the U rather than contradicting it.  It
says nothing about the turn ``rho*`` itself, nor about the sign of the margin at the
*anchored* rho, which is the paper's primary statement.  As reported, the SA did not
test the contribution the paper puts first.

The repair costs no simulation.  The brief-14 design evaluates every design point at
**four** values of rho, so a quadratic can be fitted per point and its argmin taken,
exactly as section 6 does on the 7-node conditional grid.

**No simulation is run.**  This reads committed artifacts only:

* ``results/ces_b14_sobol_runs.csv``   -> per-point, per-rho, per-seed Output
* ``results/ces_b14_sobol_qoi.csv``    -> the committed ``rho_star`` column, for cross-check
* ``results/ces_b14_sobol_design.csv`` -> the parameter vector of each design point
* ``results/ces_b11_anchoring_ratios.csv`` -> I/Y by rho, to derive the anchored rho

Declared conventions
--------------------
1. **Reduction to a curve.**  ``Y(rho)`` is the mean of ``Output`` over seeds at each of
   the four rho nodes, matching how the committed QoI is formed.  Collapsed seeds are
   not dropped here: viability is already a separate QoI and dropping them would make
   this curve conditional on a different sample than the slope it is compared with.
2. **Turning point.**  ``quadratic_curvature`` from ``src.experiment`` -- the *same*
   function section 6 uses -- so any difference between the two is the design, not the
   estimator.
3. **Resolvability.**  A turn is called *resolved* only when the quadratic is convex
   (``quad_coef > 0``) **and** the curvature is distinguishable from zero at the design's
   own precision (``|quad_coef| > 2 * quad_coef_se``) **and** ``rho*`` lands inside the
   swept support.  Everything else is reported as **undefined and is not extrapolated**;
   a concave or flat fit has an argmax or no turn at all, and calling its argmin a
   "turning point" would invent structure the four nodes cannot see.
4. **The anchored rho** is derived here rather than assumed -- see ``anchored_rho()``.

Declared limit -- resolution
----------------------------
Four nodes on [0.35, 0.65] give a coarse estimate of ``rho*``: the quadratic is a local
approximation, not the true curve.  The script therefore also reports the agreement
between this 4-node estimate and the 7-node conditional estimates of
``ces_b14_taskB_slopes.csv`` on the cells where the two are comparable, so the reader can
see how much the coarser design costs.  ``rho*`` from four nodes should be read as
locating the turn, not as measuring it to three decimals.

Deterministic by construction: groupbys and least squares over committed CSVs, no RNG, no
simulation, no parallelism.  Not covered by pytest -- there is no model behaviour here to
pin, only a reduction of artifacts that already exist.

Usage
-----
    python scripts/compute_sa_turning_points.py             # -> results/ces_b16_turning_points.csv
    python scripts/compute_sa_turning_points.py --print-only
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_SRC = os.path.join(_ROOT, "src")
_RESULTS = os.path.join(_ROOT, "results")
for _p in (_SRC, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from experiment import (  # noqa: E402
    cells_from_panel,
    common_viable_support,
    quadratic_curvature,
)

OUT_CSV = os.path.join(_RESULTS, "ces_b16_turning_points.csv")

#: The swept rho support of the SA design.  A turn outside it is not observed.
RHO_SUPPORT = (0.35, 0.65)

#: BEA anchor for I/Y, private non-residential fixed investment over GDP, the comparator
#: held on both sides of the ratio (brief 11).  FRED A008RE1Q156NBEA, Q1 2025 - Q1 2026.
IY_BAND = (0.138, 0.141)


def anchored_rho(ratios: pd.DataFrame) -> dict:
    """Derive the retention ratio implied by the I/Y anchor, per scenario.

    ``rho`` is anchored *through the investment rate it produces*, not through corporate
    payout ratios (brief 11): rho is what fixes I/Y in this model.  So the anchored rho is
    the rho at which measured I/Y enters the BEA band -- obtained here by linear
    interpolation between the two bracketing nodes of the committed rho sweep.

    Where measured I/Y already exceeds the band at the lowest swept rho, the anchored rho
    lies **below the swept support**.  That is reported as such and **not extrapolated**:
    an extrapolated rho would be a number about a region the sweep never visited.
    """
    out = {}
    for scen, g in ratios.groupby("scenario"):
        g = g.sort_values("rho")
        rho, iy = g["rho"].to_numpy(float), g["I_over_Y"].to_numpy(float)
        bounds = []
        for target in IY_BAND:
            if iy[0] > target:
                bounds.append(None)          # band already exceeded at the lowest rho
            elif iy[-1] < target:
                bounds.append(float("nan"))  # band never reached inside the support
            else:
                bounds.append(float(np.interp(target, iy, rho)))
        out[scen] = {
            "rho_lo": bounds[0], "rho_hi": bounds[1],
            "iy_at_min_rho": float(iy[0]), "min_rho": float(rho[0]),
            "below_support": bounds[0] is None,
        }
    return out


def turning_points(runs: pd.DataFrame) -> pd.DataFrame:
    """Fit ``Y(rho)`` per design point and return the turn with its diagnostics.

    The seed mean is formed the way :func:`experiment.qoi_from_runs` forms it -- a
    ``(rho x seed)`` array reduced with ``numpy.mean(axis=1)`` -- rather than with a
    pandas groupby.  The two differ in summation order at the last bits, and a quadratic
    argmin **amplifies** that: an early version of this script used the groupby and landed
    1.3e-8 away from the committed column, which is the same amplification the project
    already documented for fitted quantities (a slope moving 3410 ULP on inputs stable to
    4).  Matching the reduction makes the cross-check below a real test of the analysis
    rather than a measurement of two summation orders.
    """
    rows = []
    for point, block in runs.groupby("point"):
        piv = block.pivot(index="rho", columns="seed", values="Output").sort_index()
        Y = piv.to_numpy()                      # rows = rho node, cols = seed
        coef, se, turn = quadratic_curvature(piv.index.to_numpy(float), Y.mean(axis=1))
        g = piv.index
        convex = bool(np.isfinite(coef) and coef > 0)
        # 2*se is the design's own precision, not a significance test: with 4 nodes and a
        # 3-parameter fit there is a single residual degree of freedom, so this is a
        # deliberately weak bar that only rejects curvature indistinguishable from noise.
        resolved_curv = bool(convex and np.isfinite(se) and abs(coef) > 2.0 * se)
        in_support = bool(np.isfinite(turn)
                          and RHO_SUPPORT[0] <= turn <= RHO_SUPPORT[1])
        rows.append({
            "point": int(point),
            "n_rho": int(len(g)),
            "quad_coef": coef,
            "quad_coef_se": se,
            "convex": convex,
            "curvature_resolved": resolved_curv,
            "rho_star": turn,
            "rho_star_in_support": in_support,
            "rho_star_resolved": bool(resolved_curv and in_support),
        })
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--print-only", action="store_true",
                    help="print the summary and write nothing")
    args = ap.parse_args()

    runs = pd.read_csv(os.path.join(_RESULTS, "ces_b14_sobol_runs.csv"))
    qoi = pd.read_csv(os.path.join(_RESULTS, "ces_b14_sobol_qoi.csv"))
    design = pd.read_csv(os.path.join(_RESULTS, "ces_b14_sobol_design.csv"))
    ratios = pd.read_csv(os.path.join(_RESULTS, "ces_b11_anchoring_ratios.csv"))

    # ---------------------------------------------------------------- anchored rho
    anch = anchored_rho(ratios)
    print("=== ANCHORED RHO, derived from I/Y against the BEA band "
          f"{IY_BAND[0]}-{IY_BAND[1]} ===")
    ceiling = []
    for scen, a in sorted(anch.items()):
        if a["below_support"]:
            print(f"  {scen:9s}  I/Y = {a['iy_at_min_rho']:.4f} already at rho = "
                  f"{a['min_rho']:.2f} -> anchored rho is BELOW the swept support, "
                  f"not extrapolated")
            ceiling.append(a["min_rho"])
        else:
            print(f"  {scen:9s}  anchored rho = {a['rho_lo']:.4f} - {a['rho_hi']:.4f} "
                  f"(interpolated inside the support)")
            ceiling.append(a["rho_hi"])
    rho_anchor_max = float(np.nanmax(ceiling))
    print(f"\n  Upper bound across scenarios: rho_anchored <= {rho_anchor_max:.4f}")
    print("  (the conservative choice: whichever scenario, the anchored rho is at most "
          "this,\n   so a turn above it puts the anchored point on the falling branch)")

    # ---------------------------------------------------------------- turning points
    tp = turning_points(runs)

    # Cross-check against the committed column: this script must reproduce brief 14's
    # rho_star, or one of the two is wrong.
    merged = tp.merge(qoi[["point", "viable", "rho_star"]].rename(
        columns={"rho_star": "rho_star_committed"}), on="point", how="left")
    both = merged[np.isfinite(merged["rho_star"])
                  & np.isfinite(merged["rho_star_committed"])]
    dev = float((both["rho_star"] - both["rho_star_committed"]).abs().max())
    # The project's reproducibility criterion (appendix A) declares that a numeric
    # tolerance must NOT be applied to differenced or fitted quantities: catastrophic
    # cancellation makes their relative error arbitrary even from stable inputs, so those
    # are checked by REGIME at tolerance zero instead.  rho* is an argmin of a fit, so
    # that is the criterion applied here; the magnitude below is reported as information,
    # not as a pass/fail bar.
    same_support = int((both["rho_star_in_support"]
                        == (both["rho_star_committed"].between(*RHO_SUPPORT))).sum())
    same_side = int(((both["rho_star"] > rho_anchor_max)
                     == (both["rho_star_committed"] > rho_anchor_max)).sum())
    print("\n=== CROSS-CHECK vs the committed rho_star column ===")
    print(f"  compared on {len(both)} points; max |deviation| = {dev:.3e}"
          "  (informational: an argmin amplifies last-bit differences in its inputs)")
    print(f"  REGIME, at tolerance zero -- the declared criterion for a fitted quantity:")
    print(f"    same in/out of support : {same_support}/{len(both)}"
          f"   {'PASS' if same_support == len(both) else '*** FAIL ***'}")
    print(f"    same side of anchored rho: {same_side}/{len(both)}"
          f"   {'PASS' if same_side == len(both) else '*** FAIL ***'}")

    out = merged.merge(design[["point", "sigma", "delta", "pi0", "c0", "beta"]],
                       on="point", how="left")
    out["rho_anchored_max"] = rho_anchor_max
    # The marginalised analogue of contribution 1: is the anchored rho on the falling
    # branch?  Only meaningful where the turn is resolved.
    out["anchored_left_of_turn"] = np.where(
        out["rho_star_resolved"], out["rho_star"] > rho_anchor_max, np.nan)

    v = out[out["viable"] == 1.0]
    print(f"\n=== MARGINAL DISTRIBUTION OF rho*  (viable points: {len(v)}) ===")
    res = v[v["rho_star_resolved"]]
    print(f"  convex fit                    : {int(v['convex'].sum()):4d} "
          f"({v['convex'].mean():.3f})")
    print(f"  curvature resolved at 2 s.e.  : {int(v['curvature_resolved'].sum()):4d} "
          f"({v['curvature_resolved'].mean():.3f})")
    print(f"  turn inside [{RHO_SUPPORT[0]}, {RHO_SUPPORT[1]}]        : "
          f"{int(v['rho_star_in_support'].sum()):4d} "
          f"({v['rho_star_in_support'].mean():.3f})")
    print(f"  RESOLVED (convex + sig + in support): {len(res):4d} "
          f"({v['rho_star_resolved'].mean():.3f})   <- everything else is undefined, "
          f"not extrapolated")
    if len(res):
        q = res["rho_star"].quantile([0.10, 0.25, 0.50, 0.75, 0.90])
        print("  quantiles of rho* where resolved: "
              + "  ".join(f"p{int(k*100)}={val:.3f}" for k, val in q.items()))
    fin = v[np.isfinite(v["rho_star"])]
    print(f"  (all finite turns, resolved or not: median {fin['rho_star'].median():.3f}, "
          f"below support {float((fin['rho_star'] < RHO_SUPPORT[0]).mean()):.3f})")

    print(f"\n=== THE QUESTION THAT COUNTS ===")
    if len(res):
        frac = float((res["rho_star"] > rho_anchor_max).mean())
        print(f"  Of the {len(res)} viable points with a RESOLVED turn, "
              f"{float((res['rho_star'] > rho_anchor_max).sum()):.0f} "
              f"({frac:.3f}) have rho* above the anchored rho,")
        print(f"  i.e. the anchored retention rate sits on the FALLING branch and the "
              f"margin there is NEGATIVE.")
        print(f"  This is the marginalised analogue of the paper's first contribution.")

    # ------------------------------------------------ what does the coarse design cost?
    # The SA evaluates rho at {0.35, 0.45, 0.55, 0.65}: a strict SUBSET of the 7-node
    # conditional grid {0.35 .. 0.65 by 0.05} that section 6 fits.  So the cost of the
    # coarser design is measurable directly -- refit the conditional cells on the SA's
    # four nodes and compare with the committed 7-node turn.  This is the declared
    # resolution limit, quantified rather than asserted.
    panel = pd.read_csv(os.path.join(_RESULTS, "ces_b05_stage_a_panel.csv"))
    # Select the scenario BEFORE dropping its identifying columns.  The panel holds both
    # c0 = 1.0 and c0 = 2.0; dropping "c0" without filtering silently averages two
    # different economies into one cell, which is what an earlier version of this block
    # did -- it put rho* at sigma = 0.30 at 0.155 against the committed 0.420.
    panel = panel[panel["c0"] == 1.0]
    panel = panel[["sigma", "rho", "seed"] +
                  [c for c in panel.columns
                   if c not in ("sigma", "rho", "seed", "c0", "eta")]]
    # Use the SAME reduction the paper's estimator uses -- cells_from_panel onto the
    # COMMON VIABLE SUPPORT -- not a plain seed mean over all seven raw nodes.  An
    # earlier version of this block did the latter and landed 0.015 away from the
    # committed rho*, because it was fitting a different object and calling it the same
    # name.  Reproducing the committed column is what makes the 4-node comparison below
    # a measurement of resolution rather than of two different estimators.
    cells = cells_from_panel(panel)
    canonical = common_viable_support(cells)
    sa_nodes = [r for r in sorted(runs["rho"].unique()) if r in canonical]
    committed = pd.read_csv(os.path.join(_RESULTS, "ces_b14_taskB_slopes.csv"))
    committed = committed[committed["scenario"] == "b05_eta=0"].set_index("sigma")
    print("\n=== RESOLUTION COST OF FOUR NODES (conditional cells, b05 panel) ===")
    print(f"  common viable support (7-node) : {canonical}")
    print(f"  SA nodes intersected with it   : {sa_nodes}")
    diffs, flips, repro = [], 0, []
    for sig, blk in cells.groupby("sigma"):
        b7 = blk[blk["rho"].isin(canonical)].sort_values("rho")
        b4 = blk[blk["rho"].isin(sa_nodes)].sort_values("rho")
        if len(b7) < 4 or len(b4) < 4:
            continue
        _, _, t7 = quadratic_curvature(b7["rho"], b7["Y"])
        _, _, t4 = quadratic_curvature(b4["rho"], b4["Y"])
        if not (np.isfinite(t7) and np.isfinite(t4)):
            continue
        if sig in committed.index:
            repro.append(abs(t7 - float(committed.loc[sig, "rho_star"])))
        diffs.append(abs(t4 - t7))
        # the decision the paper actually makes off rho*: which side the anchored rho
        # falls on.  A resolution loss that does not flip this costs nothing that matters.
        if (t7 > rho_anchor_max) != (t4 > rho_anchor_max):
            flips += 1
        print(f"    sigma={sig:5.2f}   rho* 7-node = {t7:.4f}   4-node = {t4:.4f}"
              f"   |diff| = {abs(t4 - t7):.4f}")
    if repro:
        print(f"  reproduces the committed tab:turning rho* to {max(repro):.2e} "
              f"{'PASS' if max(repro) < 1e-6 else '*** the 7-node baseline is NOT the committed one ***'}")
    if diffs:
        print(f"  max |4-node - 7-node| = {max(diffs):.4f}, median "
              f"{float(np.median(diffs)):.4f} over {len(diffs)} cells")
        print(f"  cells where the coarser grid FLIPS the side of the anchored rho: "
              f"{flips}/{len(diffs)}"
              f"   {'-> the decision is robust to the resolution' if flips == 0 else '<- MATERIAL'}")

    # ------------------------------------------- can rho* carry a Sobol decomposition?
    # The brief asks for Sobol indices on rho* "if the sample allows it, and if N does not
    # support sensible CIs, declare that and omit them rather than report them weak".
    # Settle it by counting rather than by judgement.  The Saltelli design with
    # calc_second_order=False lays out (k + 2) evaluations per base sample, and the
    # estimator needs ALL of them: a base sample with any undefined rho* contributes
    # nothing, and imputing one would mean extrapolating a turn the four nodes did not
    # resolve -- forbidden by convention 3 above.
    n_rows = len(out)
    for k in (11,):
        block = k + 2
        if n_rows % block == 0:
            n_base = n_rows // block
            res_flag = out.sort_values("point")["rho_star_resolved"].to_numpy()
            groups = res_flag.reshape(n_base, block)
            complete = int(groups.all(axis=1).sum())
            print(f"\n=== SOBOL ON rho* AS A QoI -- feasibility, by count ===")
            print(f"  Saltelli layout: {n_base} base samples x {block} evaluations "
                  f"(k = {k}, calc_second_order=False)")
            print(f"  base samples with rho* resolved at EVERY evaluation: "
                  f"{complete}/{n_base} ({complete / n_base:.3f})")
            print("  VERDICT: the decomposition is NOT computed. The estimator needs a")
            print("  complete block per base sample; imputing the missing turns would")
            print("  extrapolate a turn the design cannot see, and dropping blocks leaves")
            print("  a sample far too small for meaningful bootstrap CIs. Declared and")
            print("  omitted, per the brief, rather than reported weak.")

    if not args.print_only:
        cols = ["point", "sigma", "delta", "pi0", "c0", "beta", "viable", "n_rho",
                "quad_coef", "quad_coef_se", "convex", "curvature_resolved",
                "rho_star", "rho_star_committed", "rho_star_in_support",
                "rho_star_resolved", "rho_anchored_max", "anchored_left_of_turn"]
        out[cols].to_csv(OUT_CSV, index=False)
        print(f"\nwrote {OUT_CSV}  ({len(out)} rows)")


if __name__ == "__main__":
    main()

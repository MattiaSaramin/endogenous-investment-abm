#!/usr/bin/env python
"""Regenerate brief 14: REPAIR THE QoI and separate the two candidate causes.

Brief 13 closed with a contradiction it declared rather than resolved.  Its wide-sigma
check found the wage-led sign rare below sigma ~ 0.65 and frequent above, and recorded
that as the OPPOSITE direction to the sigma* conclusion of briefs 04/07 - with two
candidate causes it could not separate:

(a) **chord vs derivative.**  The brief-13 QoI is a two-point chord between rho = 0.35 and
    0.55.  Brief 05 had already measured that ``Y(rho)`` is U-shaped with the turn INSIDE
    the canonical support in 19 of 22 cells, and on a U the sign of a chord depends on
    where the chord is taken.  Brief 07 identified sigma* from an OLS slope over the whole
    support.  Two different functionals of the same curve; no reason for them to agree.
(b) **conditional vs marginal.**  sigma* is measured with every other parameter held at a
    default.  The SA MARGINALISES over 15 sampled parameters.  In a model where
    ``ST >> S1`` everywhere there is no reason those coincide - and brief 13 measured
    ``ST(sigma) = 0.024``, i.e. marginally sigma explains ~2% of the variance.

Design (brief 14 §1): a 2x2 on ONE grid of runs, so no run is wasted.

======================  =========================  =========================
                        method = chord [.35,.55]   method = OLS [.35,.65]
======================  =========================  =========================
parameters FIXED         cell 1                     cell 2  <- anchoring control
parameters MARGINALISED  cell 3                     cell 4
======================  =========================  =========================

The verdict rule is declared in :data:`VERDICT_RULE` and is the brief's, fixed before any
of this ran: a flip between cells 1 and 2 indicts the QoI (cause a); a flip between 2 and
4 indicts the generalisation of sigma* (cause b); both, both; neither is a new FINDING to
report rather than force.

**Cells 1 and 2 need no simulation at all.**  ``ces_b05_stage_a_panel.csv`` and
``ces_b07_stage_a_panel.csv`` already carry the canonical sigma grid x the canonical rho
support x 20 seeds at exactly the brief-07 defaults.  The chord and the OLS slope are two
linear functionals of that same committed data, so the fixed arm of the bridge is a
RE-ANALYSIS, and :func:`experiment.bootstrap_sigma_star` puts a CI on both by passing the
appropriate weight vector.  Only the marginalised arm costs runs.

Task C then redoes Morris and Sobol with the repaired QoI.  **Parameters, ranges, frozen
values and the sampling seed are IMPORTED from the brief-13 driver, not copied**, so they
cannot drift: the only thing that differs between the two index sets is the QoI, which is
what makes the difference between them attributable.

Usage
-----
    python scripts/run_brief14.py --phase bridge    # ~30 min (tasks A + B)
    python scripts/run_brief14.py --phase morris    # ~30 min
    python scripts/run_brief14.py --phase sobol     # ~4.5 h
    python scripts/run_brief14.py --phase wide      # ~2.2 h
    python scripts/run_brief14.py --phase report    # no simulation
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.abspath(os.path.join(_HERE, "..", "src"))
for _p in (_SRC, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.environ["PYTHONPATH"] = _SRC + os.pathsep + os.environ.get("PYTHONPATH", "")

# Pin BLAS/numpy to one thread BEFORE numpy is imported, so the reduction order is
# deterministic and workers do not each spawn a full BLAS pool.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
import pandas as pd

from experiment import (
    SA_RHO_GRID,
    SA_RHO_HI,
    SA_RHO_LO,
    SIGMA_SWEEP_B05,
    bootstrap_sigma_star,
    cells_from_panel,
    common_viable_support,
    ols_slope,
    qoi_from_runs,
    quadratic_curvature,
    run_design_points,
    sigma_star_interp,
    _ols_weights,
)

# The SA design is IMPORTED, never restated: identical objects cannot drift apart.
from run_brief13 import (
    MAX_TAX,
    MORRIS_KEEP_RULE,
    MORRIS_MU_FRAC,
    MORRIS_TOP_K,
    MORRIS_TRAJECTORIES,
    N_SEEDS,
    PARAMS,
    SAMPLE_SEED,
    SOBOL_N,
    SOBOL_N_WIDE,
    STEPS,
    TAIL,
    WIDE_SIGMA,
    apply_keep_rule,
    environment,
    points_from_sample,
    problem,
)

RESULTS = os.path.abspath(os.path.join(_HERE, "..", "results"))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: The brief-07 defaults: the cell in which sigma* = 0.654 was identified.  ``eta`` is
#: carried as a separate axis because the anchoring control (§1) is stated at eta = 0
#: while the brief's "default brief 07" scenario is eta = 0.10 - both are reported.
FIXED_ARM = [
    dict(name="b05_eta=0", ref="ces_b05_stage_a_panel.csv", sel=dict(c0=1.0)),
    dict(name="b07_eta=0", ref="ces_b07_stage_a_panel.csv", sel=dict(c0=1.0, eta=0.0)),
    dict(name="b07_eta=0.10", ref="ces_b07_stage_a_panel.csv", sel=dict(c0=1.0, eta=0.10)),
]

#: The canonical anchoring control (brief 14 §1).  Cell 2 must reproduce this or the
#: problem is upstream of both candidate causes and the work stops.
ANCHOR_SIGMA_STAR = 0.6540142777288407
ANCHOR_CI = (0.6163766892066109, 0.6907509707455778)

#: Design draws for the MARGINALISED arm: one common set of parameter vectors, evaluated
#: at EVERY sigma on the canonical grid.  Sharing the draws across sigma is the same
#: pairing logic as common random numbers - it removes draw-to-draw variation from the
#: sigma contrast, which is the contrast sigma* is made of.  32 is a compute decision,
#: declared: it buys a CI on sigma*(marginalised) wide enough to be honest about, and the
#: arm costs 11 x 32 x 4 x 3 = 4 224 runs.
N_MARGINAL_DRAWS = 32

#: The empirical range of sigma (Chirinko 2008; Chirinko & Mallick 2017; Knoblach et al.
#: 2020) - the interval whose position relative to sigma* is the economically meaningful
#: statement, and relative to rho* for task B.
SIGMA_EMPIRICAL = (0.40, 0.60)

#: The empirical range of rho.  ``retention_ratio`` is anchored through I/Y (brief 11),
#: which put rho ~ 0.36 at the anchor scenario; the canonical sweep runs 0.35-0.65.
RHO_EMPIRICAL = (0.35, 0.45)

#: -----------------------------------------------------------------------
#: VERDICT RULE - the brief's, restated here before any of it was executed.
#: -----------------------------------------------------------------------
VERDICT_RULE = (
    "sign flips between cell 1 and cell 2 (fixed params, different method) => cause (a), "
    "the brief-13 QoI is the defect; sign flips between cell 2 and cell 4 (same method, "
    "fixed vs marginalised) => cause (b), sigma* is real but LOCAL and must be demoted to "
    "a conditional result; both => both contribute and the relative weight is quantified; "
    "neither => a new FINDING, to be reported and not forced."
)


def chord_weights(support, lo=SA_RHO_LO, hi=SA_RHO_HI):
    """Weight vector ``w`` with ``w @ y`` equal to the brief-13 chord over ``support``.

    Expressing the chord as a linear functional is what lets the SAME bootstrap machinery
    (which resamples seeds and applies a weight vector) produce a CI for both estimators.
    The two cells of the top row then differ in one vector and nothing else.
    """
    support = list(support)
    w = np.zeros(len(support))
    w[support.index(lo)] = -1.0 / (hi - lo)
    w[support.index(hi)] = +1.0 / (hi - lo)
    return w


# ---------------------------------------------------------------------------
# Task A (fixed arm) + Task B: pure re-analysis of committed panels
# ---------------------------------------------------------------------------

def fixed_arm():
    """Cells 1 and 2, plus task B, from the committed panels.  No simulation.

    Two supports are reported for each estimator and they answer different questions:

    * ``canonical`` - the full committed rho support.  This is the one that must
      reproduce ANCHOR_SIGMA_STAR, because it is the estimator brief 07 actually used.
    * ``grid4`` - the four rho values of :data:`experiment.SA_RHO_GRID`.  This is the one
      comparable to the marginalised arm, which is run on those four points.

    Separating them matters: without it, a difference between the arms could be the
    support rather than the marginalisation, and cell 2 vs cell 4 would be confounded.
    """
    print("\n=== TASK A (fixed arm) + TASK B - re-analysis, no simulation ===")
    rows, slope_rows = [], []

    for spec in FIXED_ARM:
        panel = pd.read_csv(os.path.join(RESULTS, spec["ref"]))
        for col, val in spec["sel"].items():
            if col in panel.columns:
                panel = panel[panel[col] == val]
        panel = panel[["sigma", "rho", "seed"] +
                      [c for c in panel.columns
                       if c not in ("sigma", "rho", "seed", "c0", "eta")]]
        cells = cells_from_panel(panel)
        canonical = common_viable_support(cells)
        grid4 = [r for r in SA_RHO_GRID if r in canonical]

        for support_name, support in (("canonical", canonical), ("grid4", grid4)):
            if len(support) < 4:
                print(f"  {spec['name']}/{support_name}: support {support} too thin "
                      f"- SKIPPED (declared)")
                continue
            for method, w in (("ols", None), ("chord", chord_weights(support))):
                bs = bootstrap_sigma_star(panel, support, column="Output", weights=w)
                rows.append({
                    "arm": "fixed", "scenario": spec["name"], "support": support_name,
                    "method": method, "n_rho": len(support),
                    "sigma_star": bs["sigma_star"], "ci_lo": bs["ci_lo"],
                    "ci_hi": bs["ci_hi"], "frac_undefined": bs["frac_undefined"],
                    "n_crossings": bs["n_crossings"],
                })
                print(f"  {spec['name']:<14s} {support_name:<9s} {method:<5s} "
                      f"sigma* = {bs['sigma_star']:.4f} "
                      f"[{bs['ci_lo']:.4f}, {bs['ci_hi']:.4f}]  "
                      f"undefined {bs['frac_undefined']:.3f}")

        # --- Task B: the three quantities reported TOGETHER, per sigma -------------
        for sigma, blk in cells.groupby("sigma"):
            b = blk[blk["rho"].isin(canonical)].sort_values("rho")
            if len(b) < 4:
                continue
            slope, se = ols_slope(b["rho"], b["Y"])
            quad, quad_se, turn = quadratic_curvature(b["rho"], b["Y"])
            lo, hi = float(b["rho"].min()), float(b["rho"].max())
            resolved = bool(np.isfinite(turn) and lo <= turn <= hi)
            y = dict(zip(b["rho"], b["Y"]))
            chord = ((y[SA_RHO_HI] - y[SA_RHO_LO]) / (SA_RHO_HI - SA_RHO_LO)
                     if SA_RHO_LO in y and SA_RHO_HI in y else float("nan"))
            slope_rows.append({
                "scenario": spec["name"], "sigma": sigma,
                "ols_slope": slope, "ols_se": se, "chord": chord,
                "rho_star": turn, "rho_star_se_proxy": quad_se,
                "rho_star_in_support": resolved,
                "quad_coef": quad, "rho_min": lo, "rho_max": hi,
                # The economically interpretable statement (§2.3): does the empirical rho
                # range sit LEFT of the turn (investment still depressing output) or RIGHT
                # of it (expanding)?  Unlike a slope, this does not depend on which chord
                # someone picked.
                "empirical_rho_side": (
                    "undefined" if not resolved else
                    "left" if RHO_EMPIRICAL[1] <= turn else
                    "right" if RHO_EMPIRICAL[0] >= turn else "straddles"),
            })

    out = pd.DataFrame(rows)
    slopes = pd.DataFrame(slope_rows)
    out.to_csv(os.path.join(RESULTS, "ces_b14_bridge_fixed.csv"), index=False)
    slopes.to_csv(os.path.join(RESULTS, "ces_b14_taskB_slopes.csv"), index=False)

    # --- the mandatory anchoring control (§1) --------------------------------------
    ctrl = out[(out["scenario"] == "b05_eta=0") & (out["support"] == "canonical")
               & (out["method"] == "ols")]
    ok = False
    if len(ctrl):
        got = float(ctrl["sigma_star"].iloc[0])
        ok = abs(got - ANCHOR_SIGMA_STAR) < 1e-6
        print(f"\n  ANCHORING CONTROL: cell 2 gives sigma* = {got:.10f}, "
              f"canonical is {ANCHOR_SIGMA_STAR:.10f} -> "
              f"{'PASS' if ok else 'FINDING'}")
    if not ok:
        print("  the problem is UPSTREAM of both candidate causes - stopping (§1).")
    return out, slopes, ok


# ---------------------------------------------------------------------------
# Task A (marginalised arm): the only part of the bridge that costs runs
# ---------------------------------------------------------------------------

def marginal_arm(workers, draws=N_MARGINAL_DRAWS, seeds=N_SEEDS):
    """Cells 3 and 4: the same sigma grid, every other parameter marginalised.

    The draws are shared across sigma by construction (see :data:`N_MARGINAL_DRAWS`), so
    the sigma axis is paired and the contrast with the fixed arm is not polluted by which
    parameter vectors happened to be drawn where.
    """
    from SALib.sample import sobol as sobol_sample

    print("\n=== TASK A (marginalised arm) ===")
    spec = [p for p in PARAMS if p[0] != "sigma"]
    prob = problem(spec)
    # A Saltelli draw used purely as a space-filling sample; its estimator structure is
    # irrelevant here, only the coverage of the box is.
    sample = sobol_sample.sample(prob, 16, calc_second_order=False, seed=SAMPLE_SEED)
    sample = sample[:draws]
    vectors = points_from_sample(sample, prob["names"])
    print(f"  {len(vectors)} parameter draws x {len(SIGMA_SWEEP_B05)} sigma "
          f"x {len(SA_RHO_GRID)} rho x {seeds} seeds = "
          f"{len(vectors) * len(SIGMA_SWEEP_B05) * len(SA_RHO_GRID) * seeds} runs")

    points, index = [], []
    for sigma in SIGMA_SWEEP_B05:
        for d, vec in enumerate(vectors):
            points.append(dict(vec, sigma=sigma))
            index.append({"point": len(points) - 1, "sigma": sigma, "draw": d})

    t0 = time.perf_counter()
    runs = run_design_points(points, seeds=seeds, steps=STEPS, tail=TAIL,
                             workers=workers, rhos=SA_RHO_GRID)
    qoi = qoi_from_runs(runs, rhos=SA_RHO_GRID)
    qoi = qoi.merge(pd.DataFrame(index), on="point")
    print(f"  done in {(time.perf_counter() - t0) / 60:.1f} min  "
          f"(viable {qoi['viable'].mean():.3f})")

    runs.to_csv(os.path.join(RESULTS, "ces_b14_bridge_marginal_runs.csv"), index=False)
    qoi.to_csv(os.path.join(RESULTS, "ces_b14_bridge_marginal_qoi.csv"), index=False)
    return qoi


def marginal_sigma_star(qoi, n_boot=2000, rng_seed=20260720):
    """sigma*(marginalised) for both estimators, with a CI bootstrapped over DRAWS.

    The resampling unit is the parameter draw, because that is the unit of randomness in
    this arm - exactly as the seed is the unit in the fixed arm.  Non-viable points carry
    no slope and are excluded per sigma; the count is reported, never imputed.
    """
    rows = []
    sigmas = sorted(qoi["sigma"].unique())
    rng = np.random.default_rng(rng_seed)

    for method, col in (("ols", "slope"), ("chord", "chord")):
        # mean slope per sigma over the viable draws
        table = {}
        for s in sigmas:
            blk = qoi[(qoi["sigma"] == s) & np.isfinite(qoi[col])]
            table[s] = blk.set_index("draw")[col]
        means = [float(table[s].mean()) if len(table[s]) else float("nan") for s in sigmas]
        star, crossings = sigma_star_interp(sigmas, means)

        draws = sorted(qoi["draw"].unique())
        stars = np.full(n_boot, np.nan)
        for b in range(n_boot):
            pick = rng.choice(draws, size=len(draws), replace=True)
            m = []
            for s in sigmas:
                ser = table[s].reindex(pick)
                m.append(float(ser.mean()) if ser.notna().any() else float("nan"))
            stars[b], _ = sigma_star_interp(sigmas, m)
        defined = stars[np.isfinite(stars)]
        rows.append({
            "arm": "marginalised", "scenario": "SA ranges (brief 13)",
            "support": "grid4", "method": method, "n_rho": len(SA_RHO_GRID),
            "sigma_star": star,
            "ci_lo": float(np.percentile(defined, 2.5)) if defined.size else float("nan"),
            "ci_hi": float(np.percentile(defined, 97.5)) if defined.size else float("nan"),
            "frac_undefined": float(1.0 - defined.size / n_boot),
            "n_crossings": crossings,
        })
        print(f"  marginalised   grid4     {method:<5s} sigma* = {star:.4f} "
              f"[{rows[-1]['ci_lo']:.4f}, {rows[-1]['ci_hi']:.4f}]  "
              f"undefined {rows[-1]['frac_undefined']:.3f}")

    per_sigma = []
    for s in sigmas:
        blk = qoi[qoi["sigma"] == s]
        v = blk[blk["viable"] == 1.0]
        per_sigma.append({
            "sigma": s, "n_draws": len(blk), "n_viable": len(v),
            "mean_ols_slope": float(v["slope"].mean()) if len(v) else float("nan"),
            "mean_chord": float(v["chord"].mean()) if len(v) else float("nan"),
            "P_wage_led_ols": float((v["slope"] < 0).mean()) if len(v) else float("nan"),
            "P_wage_led_chord": float((v["chord"] < 0).mean()) if len(v) else float("nan"),
            "mean_rho_star": float(v["rho_star"].mean()) if len(v) else float("nan"),
            "frac_rho_star_in_support": (float(v["rho_star_in_support"].mean())
                                         if len(v) else float("nan")),
        })
    return pd.DataFrame(rows), pd.DataFrame(per_sigma)


def verdict(bridge):
    """Apply :data:`VERDICT_RULE` mechanically and print the result.

    'Sign flips' is read as: does the empirical sigma range fall on the same side of
    sigma* in both cells?  That is the statement the project's conclusions are written in,
    so it is the one whose stability decides the verdict - not the raw value of sigma*.
    """
    def side(row):
        s = row["sigma_star"]
        if not np.isfinite(s):
            return "undefined"
        if SIGMA_EMPIRICAL[1] <= s:
            return "below"      # empirical range entirely below sigma* -> profit-led
        if SIGMA_EMPIRICAL[0] >= s:
            return "above"      # entirely above -> wage-led
        return "straddles"

    def cell(arm, method):
        sel = bridge[(bridge["arm"] == arm) & (bridge["method"] == method)
                     & (bridge["support"] == "grid4")]
        if arm == "fixed":
            sel = sel[sel["scenario"] == "b07_eta=0"]
        return sel.iloc[0] if len(sel) else None

    c1, c2 = cell("fixed", "chord"), cell("fixed", "ols")
    c3, c4 = cell("marginalised", "chord"), cell("marginalised", "ols")
    cells = {"cell1 fixed/chord": c1, "cell2 fixed/ols": c2,
             "cell3 marg/chord": c3, "cell4 marg/ols": c4}

    print("\n=== VERDICT (rule declared ex ante) ===")
    print(f"  {VERDICT_RULE}\n")
    for k, c in cells.items():
        if c is None:
            print(f"  {k:<20s} MISSING")
        else:
            print(f"  {k:<20s} sigma* = {c['sigma_star']:.4f}  "
                  f"empirical range is {side(c).upper()} it")

    a = (c1 is not None and c2 is not None and side(c1) != side(c2))
    b = (c2 is not None and c4 is not None and side(c2) != side(c4))
    if a and b:
        v = "BOTH causes contribute"
    elif a:
        v = "cause (a): chord vs derivative - the brief-13 QoI is the defect"
    elif b:
        v = "cause (b): sigma* is real but LOCAL - demote to a conditional result"
    else:
        v = ("NEITHER - a new FINDING: the premise of the contradiction does not "
             "survive measurement, and must be reported as such, not forced")
    print(f"\n  VERDICT: {v}")
    return v, {k: (None if c is None else side(c)) for k, c in cells.items()}


# ---------------------------------------------------------------------------
# Task C: Morris + Sobol with the repaired QoI
# ---------------------------------------------------------------------------

def evaluate(points, workers, seeds=N_SEEDS, label=""):
    """Run every design point at all four rho values and reduce with the REPAIRED QoI."""
    t0 = time.perf_counter()
    n = len(points) * len(SA_RHO_GRID) * seeds
    print(f"  {label}: {len(points)} points x {len(SA_RHO_GRID)} rho x {seeds} seeds "
          f"= {n} runs")
    runs = run_design_points(points, seeds=seeds, steps=STEPS, tail=TAIL,
                             workers=workers, rhos=SA_RHO_GRID)
    qoi = qoi_from_runs(runs, rhos=SA_RHO_GRID)
    dt = time.perf_counter() - t0
    print(f"  {label}: done in {dt / 60:.1f} min  "
          f"(viable {qoi['viable'].mean():.3f}, "
          f"wage-led|viable OLS {qoi['wage_led'].mean(skipna=True):.3f}, "
          f"chord {qoi['wage_led_chord'].mean(skipna=True):.3f})")
    return runs, qoi


QOIS = ["slope_raw", "viable"]
QOI_CONDITIONAL = "slope"


def phase_morris(workers):
    """Level 1 with the repaired QoI.

    Redone rather than reused, on the brief's instruction: the brief-13 screening pruned
    against the CHORD, and a different QoI can admit a different set.  The keep rule is
    :data:`run_brief13.MORRIS_KEEP_RULE`, imported unchanged - frozen in source long
    before this ran, which is a stronger guarantee than freezing a fresh one here.
    """
    from SALib.analyze import morris as morris_analyze
    from SALib.sample import morris as morris_sample

    print("\n=== MORRIS SCREENING (repaired QoI) ===")
    spec = PARAMS + [MAX_TAX]
    prob = problem(spec)
    sample = morris_sample.sample(prob, MORRIS_TRAJECTORIES, num_levels=4, seed=SAMPLE_SEED)
    pts = points_from_sample(sample, prob["names"])

    runs, qoi = evaluate(pts, workers, label="morris")
    runs.to_csv(os.path.join(RESULTS, "ces_b14_morris_runs.csv"), index=False)
    qoi.to_csv(os.path.join(RESULTS, "ces_b14_morris_qoi.csv"), index=False)

    rows = []
    for q in QOIS:
        y = qoi[q].to_numpy(dtype=float)
        assert np.isfinite(y).all(), f"{q} has non-finite values; Morris needs all points"
        res = morris_analyze.analyze(prob, sample, y, num_levels=4, seed=SAMPLE_SEED)
        for i, name in enumerate(res["names"]):
            rows.append({"qoi": q, "parameter": name, "mu_star": float(res["mu_star"][i]),
                         "mu": float(res["mu"][i]), "sigma": float(res["sigma"][i]),
                         "mu_star_conf": float(res["mu_star_conf"][i]),
                         "n_points_used": int(len(y))})

    morris = pd.DataFrame(rows)
    morris.to_csv(os.path.join(RESULTS, "ces_b14_morris.csv"), index=False)

    survivors = apply_keep_rule(morris)
    b13 = apply_keep_rule(pd.read_csv(os.path.join(RESULTS, "ces_b13_morris.csv")))
    print(f"\n  keep rule (imported from brief 13, frozen ex ante): {MORRIS_KEEP_RULE}")
    print(f"  survivors ({len(survivors)}): {', '.join(survivors)}")
    print(f"  brief 13  ({len(b13)}): {', '.join(b13)}")
    if survivors == b13:
        print("  -> IDENTICAL to brief 13: the screening does not depend on the QoI")
    else:
        added = [p for p in survivors if p not in b13]
        dropped = [p for p in b13 if p not in survivors]
        print(f"  -> DIFFERENT: added {added or 'none'}, dropped {dropped or 'none'} "
              f"(the QoI changes who matters - a result in its own right)")
    return morris, survivors


def phase_sobol(workers, survivors, N=SOBOL_N, sigma_range=None, tag="sobol"):
    """Level 2 with the repaired QoI.  Non-survivors held at the midpoint, as in brief 13."""
    from SALib.analyze import sobol as sobol_analyze
    from SALib.sample import sobol as sobol_sample

    spec = {p[0]: p for p in PARAMS + [MAX_TAX]}
    swept = []
    for name in survivors:
        lo, hi = spec[name][1], spec[name][2]
        if name == "sigma" and sigma_range is not None:
            lo, hi = sigma_range
        swept.append((name, lo, hi))
    fixed = {p[0]: 0.5 * (p[1] + p[2]) for p in PARAMS if p[0] not in survivors}

    print(f"\n=== SOBOL ({tag}, repaired QoI) ===")
    print(f"  swept ({len(swept)}): " +
          ", ".join(f"{n} [{lo:g},{hi:g}]" for n, lo, hi in swept))
    print(f"  fixed at midpoint ({len(fixed)}): " +
          ", ".join(f"{k}={v:g}" for k, v in fixed.items()))

    prob = problem(swept)
    sample = sobol_sample.sample(prob, N, calc_second_order=False, seed=SAMPLE_SEED)
    pts = points_from_sample(sample, prob["names"], fixed=fixed)

    runs, qoi = evaluate(pts, workers, label=tag)
    runs.to_csv(os.path.join(RESULTS, f"ces_b14_{tag}_runs.csv"), index=False)
    qoi.to_csv(os.path.join(RESULTS, f"ces_b14_{tag}_qoi.csv"), index=False)
    design = pd.concat([pd.DataFrame(sample, columns=prob["names"]),
                        qoi.reset_index(drop=True)], axis=1)
    design.to_csv(os.path.join(RESULTS, f"ces_b14_{tag}_design.csv"), index=False)

    rows = []
    for q in QOIS:
        y = qoi[q].to_numpy(dtype=float)
        assert np.isfinite(y).all(), f"{q} has non-finite values; Saltelli needs all points"
        res = sobol_analyze.analyze(prob, y, calc_second_order=False,
                                    num_resamples=2000, seed=SAMPLE_SEED)
        for i, name in enumerate(prob["names"]):
            rows.append({
                "qoi": q, "parameter": name, "estimator": "saltelli",
                "S1": float(res["S1"][i]), "S1_conf": float(res["S1_conf"][i]),
                "ST": float(res["ST"][i]), "ST_conf": float(res["ST_conf"][i]),
                "n_points": len(y), "N": N, "tag": tag,
            })

    mask = qoi["viable"].to_numpy() == 1.0
    if mask.sum() >= 4 * prob["num_vars"]:
        from SALib.analyze import rbd_fast
        res = rbd_fast.analyze(prob, sample[mask],
                               qoi[QOI_CONDITIONAL].to_numpy(dtype=float)[mask])
        for i, name in enumerate(prob["names"]):
            rows.append({
                "qoi": f"{QOI_CONDITIONAL}|viable", "parameter": name,
                "estimator": "rbd_fast", "S1": float(res["S1"][i]),
                "S1_conf": float("nan"), "ST": float("nan"), "ST_conf": float("nan"),
                "n_points": int(mask.sum()), "N": N, "tag": tag,
            })
        print(f"  {QOI_CONDITIONAL}|viable: RBD-FAST S1 on {mask.sum()}/{len(mask)} points")

    sobol = pd.DataFrame(rows)
    sobol.to_csv(os.path.join(RESULTS, f"ces_b14_{tag}_indices.csv"), index=False)
    print(f"  wrote ces_b14_{tag}_indices.csv")
    return sobol, qoi


def summarise(qoi, label):
    """The headline, computed for BOTH estimators on the SAME runs.

    Reporting them side by side is the point: the difference between the two columns is
    the QoI repair, measured, with the sample held fixed.
    """
    v = qoi[qoi["viable"] == 1.0]
    vc = qoi[qoi["viable_chord"] == 1.0]
    return {
        "analysis": label,
        "n_points": int(len(qoi)),
        "frac_viable_4rho": float(qoi["viable"].mean()),
        "frac_viable_chord_pair": float(qoi["viable_chord"].mean()),
        "n_viable": int(len(v)),
        "P_wage_led_OLS_given_viable": float(v["wage_led"].mean()) if len(v) else float("nan"),
        "P_wage_led_chord_given_viable": (float((vc["chord"] < 0).mean())
                                          if len(vc) else float("nan")),
        "slope_mean_viable": float(v["slope"].mean()) if len(v) else float("nan"),
        "slope_sd_viable": float(v["slope"].std(ddof=1)) if len(v) > 1 else float("nan"),
        "slope_seed_sd_mean": float(v["slope_seed_sd"].mean()) if len(v) else float("nan"),
        "frac_rho_star_in_support": (float(v["rho_star_in_support"].mean())
                                     if len(v) else float("nan")),
        "median_rho_star": float(v["rho_star"].median()) if len(v) else float("nan"),
    }


def write_summary(rows):
    path = os.path.join(RESULTS, "ces_b14_summary.csv")
    summary = pd.DataFrame(rows)
    if os.path.exists(path):
        old = pd.read_csv(path)
        old = old[~old["analysis"].isin(summary["analysis"])]
        summary = pd.concat([old, summary], ignore_index=True)
    summary.to_csv(path, index=False)
    print("\n=== HEADLINE ===")
    print(summary.to_string(index=False))
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase", default="bridge",
                    choices=["bridge", "morris", "sobol", "wide", "report", "all"])
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()

    os.makedirs(RESULTS, exist_ok=True)
    env = environment()
    env["brief"] = 14
    env["rho_grid"] = list(SA_RHO_GRID)
    env["n_marginal_draws"] = N_MARGINAL_DRAWS
    env["verdict_rule"] = VERDICT_RULE
    print("Brief 14 - QoI repair and cause separation")
    print(json.dumps(env, indent=2))
    with open(os.path.join(RESULTS, "ces_b14_environment.json"), "w") as fh:
        json.dump(env, fh, indent=2)

    if args.phase in ("bridge", "all"):
        fixed, _slopes, ok = fixed_arm()
        if not ok:
            return 1
        qoi = marginal_arm(args.workers)
        marg, per_sigma = marginal_sigma_star(qoi)
        bridge = pd.concat([fixed, marg], ignore_index=True)
        bridge.to_csv(os.path.join(RESULTS, "ces_b14_bridge.csv"), index=False)
        per_sigma.to_csv(os.path.join(RESULTS, "ces_b14_bridge_by_sigma.csv"), index=False)
        v, sides = verdict(bridge)
        with open(os.path.join(RESULTS, "ces_b14_verdict.json"), "w") as fh:
            json.dump({"verdict": v, "sides": sides, "rule": VERDICT_RULE}, fh, indent=2)
        if args.phase == "bridge":
            return 0

    survivors = None
    if args.phase in ("morris", "sobol", "wide", "all"):
        path = os.path.join(RESULTS, "ces_b14_morris.csv")
        if args.phase in ("morris", "all"):
            _, survivors = phase_morris(args.workers)
        elif os.path.exists(path):
            survivors = apply_keep_rule(pd.read_csv(path))
            print(f"  survivors read back from {path}: {', '.join(survivors)}")
        else:
            print("  no brief-14 Morris table found - run --phase morris first")
            return 1

    rows = []
    if args.phase in ("sobol", "all"):
        _, q = phase_sobol(args.workers, survivors, N=SOBOL_N, tag="sobol")
        rows.append(summarise(q, "primary (empirical sigma 0.40-0.60)"))
    if args.phase in ("wide", "all"):
        _, q = phase_sobol(args.workers, survivors, N=SOBOL_N_WIDE,
                           sigma_range=WIDE_SIGMA, tag="wide")
        rows.append(summarise(q, f"wide sigma check {WIDE_SIGMA}"))
    if rows:
        write_summary(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())

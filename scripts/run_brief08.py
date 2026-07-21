#!/usr/bin/env python
"""Regenerate the brief-08 adaptive-expectations sweep (sigma x rho x eta x lambda_e x c0).

Brief 08 generalises the firm's demand expectation from static (``Ye_t = D_{t-1}``) to
adaptive, ``Ye_t = Ye_{t-1} + lambda_e*(D_{t-1} - Ye_{t-1})``, with the gain ``lambda_e``
(code: ``expectation_gain``) nested so ``lambda_e = 1`` recovers the static model bit-for-bit.
It reuses the brief-05 robustness stack unchanged (``run_grid_panel``/``run_grid_panels``,
``bootstrap_sigma_star``, ``slopes_by_sigma``); ``expectation_gain`` threads through
``**params`` to ``MacroModel`` with no signature change, exactly as ``eta`` and ``c0`` do.

Two experiments (approved compute plan):

* **E1 - invariance of the headline (primary, c0 = 1.0).**  eta in {0, 0.10},
  lambda_e in {0.25, 0.5, 1.0}.  In steady state Ye = D for any gain, so the steady-state
  levels - and sigma* - should be lambda_e-invariant within CI.  Any movement is a
  basin-selection finding, reported, not absorbed.  lambda_e = 1 is the control and must
  reproduce the committed panels byte-for-byte (eta = 0 -> ces_b05_stage_a_panel;
  eta = 0.10 -> the eta = 0.10 slice of ces_b07_stage_a_panel).

* **E2 - the stabilisation hypothesis (c0 = 2.0).**  eta in {0.10, 0.15} (where the
  brief-07 wage-curve collapse is mapped), lambda_e in {0.25, 0.5, 1.0}.  Deliverable: a
  collapse map (fraction of seeds at U = 1) per lambda_e, compared with brief 07's, plus a
  traced trajectory of the reference collapsing cell (sigma = 1.5, rho = 0.40, eta = 0.10)
  at each lambda_e - does the wage-employment oscillation damp and does capital stop
  eroding?  Falsifiable hypothesis: the collapse region shrinks as lambda_e falls.

Two phases:

* **Phase 1 - viability reconnaissance (3-seed).**  The full sigma x rho grid at every
  (c0, eta, lambda_e).  For E1 (c0 = 1.0) it applies one EXPLICIT halt threshold vs the
  same-(c0, eta) lambda_e = 1 control: a common viable support that loses MORE THAN ONE rho
  cell halts before the 20-seed panel.  For E2 (c0 = 2.0) collapse is the deliverable, not a
  halt condition, so the map is reported and the run auto-continues.

* **Phase 2 - production panel (20-seed).**  The same grid at 20 seeds in ONE process pool
  (the single-pool correction: 12 configs would otherwise spawn 12 pools).  Per (c0, eta,
  lambda_e) it takes sigma* (Y and U) with a bootstrap CI on the common viable support, and
  enforces the lambda_e = 1 byte-identity checks against the committed b05/b07 panels
  (artifact vs artifact).

Determinism: BLAS pinned to one thread before numpy is imported (below); the simulation
path is thread-invariant and every bootstrap is deterministic given its rng_seed.

Usage
-----
    python scripts/run_brief08.py                 # all phases -> results/, threads pinned
    python scripts/run_brief08.py --phase 1       # reconnaissance only (fast)
    python scripts/run_brief08.py --phase 2       # panel only (assumes recon passed)
    python scripts/run_brief08.py --smoke         # tiny grid/steps end-to-end check
    python scripts/run_brief08.py --workers 1     # serial (slow)
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
    COLLAPSE_Y,
    _PANEL_METRICS,
    bootstrap_sigma_star,
    cells_from_panel,
    compare_artifacts,
    common_viable_support,
    run_grid_panels,
    run_single,
    sigma_star_by_rho,
    slopes_by_sigma,
)

# --- experiment configuration (approved compute plan) ---------------------
LAMBDAS = [0.25, 0.5, 1.0]                 # 1.0 is the static control
E1_C0, E1_ETAS = 1.0, [0.0, 0.10]          # primary: headline invariance
E2_C0, E2_ETAS = 2.0, [0.10, 0.15]         # secondary: stabilisation hypothesis
RECON_SEEDS = 3
PANEL_SEEDS = 20

#: Extra reporter collected in the panel for the convergence diagnostic (brief 08 §3).
PANEL_METRICS = list(_PANEL_METRICS) + ["Expected_Demand"]

#: E1 halt threshold vs the same-(c0, eta) lambda_e = 1 control (brief 08 §4).
SUPPORT_LOSS_MAX = 1                        # halt E1 if a support loses MORE THAN this many rho

#: A cell is "stably floored" when the wage floor bound in at least half its steady-state
#: periods (unchanged wage curve; reported, not a halt condition here).
FLOOR_STABLE = 0.5

#: U at or above this counts a seed as fully collapsed (no employment).
U_COLLAPSE = 0.999

#: Committed references the lambda_e = 1 control must reproduce byte-for-byte.
B05_PANEL = "ces_b05_stage_a_panel.csv"    # eta = 0
B07_PANEL = "ces_b07_stage_a_panel.csv"    # eta > 0

#: The reference collapsing cell traced in E2 (already traced at lambda_e = 1 in brief 07).
TRACE_CELL = dict(sigma=1.5, rho=0.40, eta=0.10, c0=2.0)


def _configs():
    """The 12 (c0, eta, lambda_e) configurations, E1 then E2, in a fixed order."""
    cfgs = []
    for c0, etas in ((E1_C0, E1_ETAS), (E2_C0, E2_ETAS)):
        for eta in etas:
            for le in LAMBDAS:
                cfgs.append({"c0": c0, "eta": eta, "expectation_gain": le})
    return cfgs


def _tag(cfg):
    return f"c0={cfg['c0']} eta={cfg['eta']:<4} lambda_e={cfg['expectation_gain']}"


# ----------------------------------------------------------------------
# Phase 1 - reconnaissance
# ----------------------------------------------------------------------

def phase1(out, workers, sigmas=SIGMA_SWEEP_B05, rhos=RHO_SWEEP_B05, seeds=RECON_SEEDS):
    """Run the reconnaissance grid (one pool), write the map, evaluate the E1 halt.

    Returns ``(recon_df, ok, messages)``: ``ok`` is False if an E1 config tripped the
    support-loss threshold.  E2 collapse is reported but never halts (it is the deliverable).
    """
    cfgs = _configs()
    print(f"Phase 1 - reconnaissance ({seeds} seeds), {len(cfgs)} configs in one pool:")
    panels = run_grid_panels(cfgs, sigmas=sigmas, rhos=rhos, seeds=seeds, workers=workers)

    frames, supports = [], {}
    for cfg, panel in zip(cfgs, panels):
        cells = cells_from_panel(panel)
        key = (cfg["c0"], cfg["eta"], cfg["expectation_gain"])
        supports[key] = common_viable_support(cells, rhos=rhos)
        cells = cells.assign(c0=cfg["c0"], eta=cfg["eta"], lambda_e=cfg["expectation_gain"])
        cells["floored"] = (~cells["collapsed"]) & (cells["Wage_Floor_Binding"] >= FLOOR_STABLE)
        frames.append(cells)
        n_viable = int((~cells["collapsed"]).sum())
        print(f"  {_tag(cfg)}: viable cells={n_viable:>2d}  common support={supports[key]}")

    recon = pd.concat(frames, ignore_index=True)
    cols = ["c0", "eta", "lambda_e", "sigma", "rho", "Y", "Unemployment_Rate", "Wage_Rate",
            "Wage_Floor_Binding", "collapsed", "floored", "binding",
            "frac_seeds_collapsed", "mixed_basin"]
    _write(recon[cols].rename(columns={"Unemployment_Rate": "U"}),
           out, "ces_b08_viability_recon.csv")

    # --- E1 halt: support loss vs same-(c0, eta) lambda_e = 1 -------------
    ok, messages = True, []
    for eta in E1_ETAS:
        base = set(supports[(E1_C0, eta, 1.0)])
        for le in LAMBDAS:
            if le == 1.0:
                continue
            dropped = base - set(supports[(E1_C0, eta, le)])
            if len(dropped) > SUPPORT_LOSS_MAX:
                ok = False
                messages.append(
                    f"HALT c0={E1_C0} eta={eta} lambda_e={le}: viable support lost "
                    f"{len(dropped)} rho cells vs lambda_e=1 (dropped {sorted(dropped)}); "
                    f"threshold is >{SUPPORT_LOSS_MAX}.")

    # --- E2 collapse report (informational) ------------------------------
    print("Phase 1 - E2 (c0=2.0) collapse fractions (deliverable, not a halt):")
    for eta in E2_ETAS:
        for le in LAMBDAS:
            key = (E2_C0, eta, le)
            block = recon[(recon["c0"] == E2_C0) & (recon["eta"] == eta) &
                          (recon["lambda_e"] == le)]
            frac = float(block["collapsed"].mean())
            print(f"  c0=2.0 eta={eta:<4} lambda_e={le}: collapsed cells "
                  f"{int(block['collapsed'].sum())}/{len(block)} ({frac:.0%})  "
                  f"support={supports[key]}")

    if ok:
        print("Phase 1 gate (E1): PASS - no support-loss threshold tripped, auto-continue.")
    else:
        print("Phase 1 gate (E1): HALT")
        for m in messages:
            print("  " + m)
    return recon, ok, messages


# ----------------------------------------------------------------------
# Phase 2 - production panel
# ----------------------------------------------------------------------

def _sigma_star_row(panel, support, column):
    bs = bootstrap_sigma_star(panel, support, column=column)
    return {
        "sigma_star": bs["sigma_star"], "ci_lo": bs["ci_lo"], "ci_hi": bs["ci_hi"],
        "frac_undefined": bs["frac_undefined"], "n_crossings": bs["n_crossings"],
        "P_star_gt_0.60": bs["frac_star_above_0_60"],
        "P_star_gt_0.40": bs["frac_star_above_0_40"],
    }


def phase2(out, workers, sigmas=SIGMA_SWEEP_B05, rhos=RHO_SWEEP_B05, seeds=PANEL_SEEDS):
    cfgs = _configs()
    print(f"Phase 2 - production panel ({seeds} seeds), {len(cfgs)} configs in ONE pool:")
    panels = run_grid_panels(cfgs, sigmas=sigmas, rhos=rhos, seeds=seeds, workers=workers,
                             metrics=PANEL_METRICS)

    tagged_panels, tagged_cells = {}, {}
    all_panels, all_cells = [], []
    for cfg, panel in zip(cfgs, panels):
        key = (cfg["c0"], cfg["eta"], cfg["expectation_gain"])
        cells = cells_from_panel(panel)
        tagged_panels[key], tagged_cells[key] = panel, cells
        all_panels.append(panel.assign(c0=cfg["c0"], eta=cfg["eta"],
                                       expectation_gain=cfg["expectation_gain"]))
        all_cells.append(cells.assign(c0=cfg["c0"], eta=cfg["eta"],
                                      lambda_e=cfg["expectation_gain"]))

    big_panel = pd.concat(all_panels, ignore_index=True)
    panel_name = "ces_b08_stage_a_panel.csv"
    _write(big_panel, out, panel_name)
    _write(pd.concat(all_cells, ignore_index=True), out, "ces_b08_cells.csv")

    # --- E1: sigma*(eta; lambda_e), comparable across (eta, lambda_e) ----
    star = _e1_sigma_star(tagged_panels, tagged_cells, rhos)
    _write(star, out, "ces_b08_sigma_star.csv")

    # --- E2: collapse map + reference-cell trace -------------------------
    cmap = _e2_collapse_map(tagged_panels)
    _write(cmap, out, "ces_b08_collapse_map.csv")
    trace = _e2_trace(sigmas_steps=None, workers=workers)
    _write(trace, out, "ces_b08_trace.csv")

    # --- lambda_e = 1 byte-identity vs committed b05/b07 (artifact vs artifact) ---
    check = _byte_check(out, panel_name)
    _write(check, out, "ces_b08_nesting_check.csv")

    # --- figures ---------------------------------------------------------
    f1 = _plot_sigma_star(star, os.path.join(out, "ces_b08_sigma_star_lambda.png"))
    f2 = _plot_collapse_map(cmap, os.path.join(out, "ces_b08_collapse_map.png"))
    f3 = _plot_trace(trace, os.path.join(out, "ces_b08_trace.png"))
    for f in (f1, f2, f3):
        print(f"  wrote {os.path.basename(f)}")

    _print_headline(star, cmap, trace)
    return big_panel, star


def _e1_sigma_star(tagged_panels, tagged_cells, rhos):
    """sigma*(eta; lambda_e) at c0 = 1.0 on the support viable across ALL (eta, lambda_e).

    Estimating every point on one common support keeps sigma* comparable across both eta and
    lambda_e (a support that shifted with lambda_e would confound the gain with which cells
    survived).  The lambda_e = 1 / eta = 0 config is also reported on its FULL natural support
    - the brief-05 canonical anchor (sigma* ~ 0.654).
    """
    e1_keys = [(E1_C0, eta, le) for eta in E1_ETAS for le in LAMBDAS]
    nat = {k: common_viable_support(tagged_cells[k], rhos=rhos) for k in e1_keys}
    est_support = [r for r in rhos if all(r in nat[k] for k in e1_keys)]
    print(f"  E1 across-(eta,lambda_e) common support (sigma* estimated here) = {est_support}")

    rows = []
    for (c0, eta, le) in e1_keys:
        panel = tagged_panels[(c0, eta, le)]
        for target, col in (("Y", "Output"), ("U", "Unemployment_Rate")):
            rows.append({"c0": c0, "eta": eta, "lambda_e": le, "target": target,
                         "support_kind": "across_config", "support": str(est_support),
                         **_sigma_star_row(panel, est_support, col)})
        if eta == 0.0 and le == 1.0:
            for target, col in (("Y", "Output"), ("U", "Unemployment_Rate")):
                rows.append({"c0": c0, "eta": eta, "lambda_e": le, "target": target,
                             "support_kind": "natural_anchor", "support": str(nat[(c0, eta, le)]),
                             **_sigma_star_row(panel, nat[(c0, eta, le)], col)})
    return pd.DataFrame(rows)[
        ["c0", "eta", "lambda_e", "target", "support_kind", "sigma_star", "ci_lo", "ci_hi",
         "frac_undefined", "n_crossings", "P_star_gt_0.60", "P_star_gt_0.40", "support"]]


def _e2_collapse_map(tagged_panels):
    """Per (eta, lambda_e, sigma, rho) at c0 = 2.0: fraction of seeds collapsed / at U = 1.

    ``frac_seeds_collapsed`` (mean Output < COLLAPSE_Y per seed) is the brief-04/05 collapse
    definition, so the lambda_e = 1 rows equal ces_b07_cells exactly; ``frac_seeds_U1`` is the
    stricter "no employment left" reading the brief asks for.
    """
    rows = []
    for eta in E2_ETAS:
        for le in LAMBDAS:
            panel = tagged_panels[(E2_C0, eta, le)]
            g = panel.assign(
                _dead=panel["Output"] < COLLAPSE_Y,
                _u1=panel["Unemployment_Rate"] >= U_COLLAPSE,
            ).groupby(["sigma", "rho"], as_index=False)
            m = g.agg(frac_seeds_collapsed=("_dead", "mean"),
                      frac_seeds_U1=("_u1", "mean"),
                      mean_U=("Unemployment_Rate", "mean"),
                      Y=("Output", "mean"))
            m.insert(0, "lambda_e", le)
            m.insert(0, "eta", eta)
            m.insert(0, "c0", E2_C0)
            rows.append(m)
    return pd.concat(rows, ignore_index=True)


def _e2_trace(sigmas_steps, workers, steps=2000, seeds=6):
    """Full time series of the reference collapsing cell at each lambda_e (brief 08 §4 E2).

    sigma = 1.5, rho = 0.40, eta = 0.10, c0 = 2.0 collapses at lambda_e = 1 (brief 07,
    6/6 seeds).  Tracks capital, unemployment, wage and the demand expectation over the run so
    the report can say whether the oscillation damps and whether capital stops eroding.
    """
    keep = ["Output", "Total_Capital", "Unemployment_Rate", "Wage_Rate", "Expected_Demand"]
    frames = []
    for le in LAMBDAS:
        for seed in range(seeds):
            df = run_single(
                TRACE_CELL["rho"], steps=steps, seed=seed, sigma=TRACE_CELL["sigma"],
                c0=TRACE_CELL["c0"], eta=TRACE_CELL["eta"], expectation_gain=le,
            )[keep].copy()
            df["step"] = df.index
            df["lambda_e"] = le
            df["seed"] = seed
            frames.append(df.reset_index(drop=True))
    return pd.concat(frames, ignore_index=True)


def _byte_check(out, panel_name):
    """lambda_e = 1 slices reproduce the committed b05 (eta=0) / b07 (eta>0) panels byte-for-byte.

    Artifact vs artifact (brief 07 discipline): both the just-written b08 panel and the
    committed reference are read from disk WITHOUT re-serializing, because pandas ``to_csv`` is
    not perfectly round-trip-lossless.  The b08 model at lambda_e = 1 is the pre-brief-08 code
    path, so each shared-column slice must be identical; any nonzero deviation is a FINDING.
    """
    panel_path = os.path.join(out, panel_name)
    if not os.path.exists(panel_path):
        return pd.DataFrame([{"note": f"{panel_name} not found; check skipped"}])
    mine_all = pd.read_csv(panel_path)
    mine1 = mine_all[mine_all["expectation_gain"] == 1.0]

    rows, all_ok = [], True
    print("  nesting check (lambda_e=1 written panel vs committed b05/b07, artifact vs artifact):")
    for (c0, eta), grp in mine1.groupby(["c0", "eta"]):
        ref_name = B05_PANEL if eta == 0.0 else B07_PANEL
        ref_path = os.path.join(out, ref_name)
        if not os.path.exists(ref_path):
            all_ok = False
            rows.append({"c0": c0, "eta": eta, "ref": ref_name, "byte_equal": False,
                         "max_abs_dev": float("nan"), "note": "reference not found"})
            print(f"    c0={c0} eta={eta}: {ref_name} NOT FOUND  <-- FINDING")
            continue
        ref = pd.read_csv(ref_path)
        if "eta" in ref.columns:
            ref = ref[ref["eta"] == eta]
        ref = ref[ref["c0"] == c0]
        shared = list(ref.columns)                 # compare only the reference's columns
        order = ["c0", "sigma", "rho", "seed"]
        a = grp[shared].sort_values(order).reset_index(drop=True)
        b = ref[shared].sort_values(order).reset_index(drop=True)
        if a.shape != b.shape:
            all_ok = False
            rows.append({"c0": c0, "eta": eta, "ref": ref_name, "byte_equal": False,
                         "max_abs_dev": float("nan"), "note": f"shape {a.shape} vs {b.shape}"})
            print(f"    c0={c0} eta={eta}: SHAPE MISMATCH {a.shape} vs {b.shape}  <-- FINDING")
            continue
        # Criterion updated by brief 14 (task D): declared ULP tolerance on the levels plus
        # an EXACT regime match, replacing the retired ``dev == 0.0``.
        res = compare_artifacts(a, b)
        ok = res["ok"]
        all_ok = all_ok and ok
        rows.append({"c0": c0, "eta": eta, "ref": ref_name, "n_rows": len(a), **res,
                     "note": "PASS" if ok else "FINDING"})
        print(f"    c0={c0} eta={eta}: {'PASS' if ok else 'FINDING'}  ref={ref_name}  "
              f"n_rows={len(a)}  max_ulp_sig={res['max_ulp_significant']:.2f}  "
              f"n_exceed={res['n_exceed']}/{res['n_compared']}  "
              f"regime_equal={res['regime_equal']}  "
              f"(retired byte_equal={res['byte_equal']})")
    if not all_ok:
        print("  nesting check: FINDING - lambda_e=1 did not reproduce a committed panel.")
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# Reporting / figures
# ----------------------------------------------------------------------

def _print_headline(star, cmap, trace):
    y = star[star["target"] == "Y"]
    anchor = y[y["support_kind"] == "natural_anchor"]
    print("\nAnchor (eta=0, lambda_e=1 on the full natural support; canonical c0=1.0 -> "
          "0.6540 [0.6164, 0.6907]):")
    for _, r in anchor.iterrows():
        print(f"  sigma*={r['sigma_star']:.4f} [{r['ci_lo']:.4f}, {r['ci_hi']:.4f}]  "
              f"support={r['support']}")
    print("\nE1 headline sigma*(eta; lambda_e) on Y, across-config common support:")
    for _, r in y[y["support_kind"] == "across_config"].sort_values(["eta", "lambda_e"]).iterrows():
        star_s = f"{r['sigma_star']:.4f}" if np.isfinite(r["sigma_star"]) else "  nan "
        print(f"  eta={r['eta']:<4} lambda_e={r['lambda_e']}: sigma*={star_s} "
              f"[{r['ci_lo']:.4f}, {r['ci_hi']:.4f}]  frac_undef={r['frac_undefined']:.3f}")

    print("\nE2 collapse (c0=2.0), mean frac of seeds fully collapsed (U=1) over the grid:")
    for (eta, le), b in cmap.groupby(["eta", "lambda_e"]):
        print(f"  eta={eta:<4} lambda_e={le}: mean frac_seeds_U1={b['frac_seeds_U1'].mean():.3f}  "
              f"cells with any collapse={int((b['frac_seeds_collapsed'] > 0).sum())}/{len(b)}")

    print("\nE2 reference-cell trace (sigma=1.5, rho=0.40, eta=0.10, c0=2.0), tail-100 means:")
    for le, b in trace.groupby("lambda_e"):
        tail = b[b["step"] >= b["step"].max() - 100]
        print(f"  lambda_e={le}: K={tail['Total_Capital'].mean():7.2f}  "
              f"U={tail['Unemployment_Rate'].mean():.3f}  "
              f"wage={tail['Wage_Rate'].mean():.3f}  Y={tail['Output'].mean():7.2f}")


def _plot_sigma_star(star, path):
    """sigma*(lambda_e) with CI bands, one line per eta - the E1 headline figure."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y = star[(star["target"] == "Y") & (star["support_kind"] == "across_config")]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for eta, block in y.groupby("eta"):
        b = block.sort_values("lambda_e")
        line, = ax.plot(b["lambda_e"], b["sigma_star"], marker="o", label=f"eta = {eta}")
        ax.fill_between(b["lambda_e"], b["ci_lo"], b["ci_hi"], alpha=0.18, color=line.get_color())
    ax.axhspan(0.40, 0.60, color="grey", alpha=0.15, label="empirical sigma 0.40-0.60")
    ax.axhline(1.0, ls="--", lw=1, color="grey")
    ax.set_xlabel("expectation gain  lambda_e")
    ax.set_ylabel("sign frontier  sigma*  (dY/drho = 0)")
    ax.set_title("Does the expectation gain move the sign frontier? (c0 = 1.0)", weight="bold")
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _plot_collapse_map(cmap, path):
    """Small-multiples heatmap of frac_seeds_U1 over (sigma, rho), one panel per (eta, lambda_e)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    etas = sorted(cmap["eta"].unique())
    les = sorted(cmap["lambda_e"].unique())
    fig, axes = plt.subplots(len(etas), len(les), figsize=(3.2 * len(les), 3.0 * len(etas)),
                             squeeze=False)
    for i, eta in enumerate(etas):
        for j, le in enumerate(les):
            ax = axes[i][j]
            block = cmap[(cmap["eta"] == eta) & (cmap["lambda_e"] == le)]
            piv = block.pivot(index="sigma", columns="rho", values="frac_seeds_U1")
            im = ax.pcolormesh(piv.columns, piv.index, piv.to_numpy(),
                               cmap="magma", vmin=0.0, vmax=1.0, shading="nearest")
            ax.set_title(f"eta={eta}, lambda_e={le}", fontsize=9)
            if j == 0:
                ax.set_ylabel("sigma")
            if i == len(etas) - 1:
                ax.set_xlabel("rho")
    fig.colorbar(im, ax=axes, label="frac of seeds fully collapsed (U=1)", shrink=0.8)
    fig.suptitle("E2 collapse map (c0 = 2.0): does a slower expectation shrink it?", weight="bold")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _plot_trace(trace, path):
    """Reference-cell trajectories: capital and unemployment over time, per lambda_e (seed-mean)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (axk, axu) = plt.subplots(1, 2, figsize=(12, 4.5))
    for le, b in trace.groupby("lambda_e"):
        g = b.groupby("step")
        axk.plot(g["Total_Capital"].mean(), label=f"lambda_e={le}")
        axu.plot(g["Unemployment_Rate"].mean(), label=f"lambda_e={le}")
    axk.set_xlabel("step"); axk.set_ylabel("Total capital K"); axk.legend(fontsize=8)
    axk.set_title("Does capital stop eroding?", weight="bold")
    axu.set_xlabel("step"); axu.set_ylabel("Unemployment rate"); axu.legend(fontsize=8)
    axu.set_title("Does the oscillation damp?", weight="bold")
    fig.suptitle("E2 reference cell (sigma=1.5, rho=0.40, eta=0.10, c0=2.0)", weight="bold")
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
    ap.add_argument("--workers", type=int, default=None,
                    help="process-pool size (default: all cores; 1 = serial)")
    ap.add_argument("--smoke", action="store_true",
                    help="tiny grid/steps end-to-end check (writes to results/smoke)")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    if args.smoke:
        out = os.path.join(out, "smoke")
    os.makedirs(out, exist_ok=True)
    W = args.workers

    if args.smoke:
        # End-to-end shape/plumbing check only - NOT a scientific result. Reduced grid and
        # steps mean the lambda_e=1 byte-check against the 2000-step committed panels will
        # report FINDING; that is expected in smoke mode.
        sig = [0.5, 1.0, 1.25]
        rho = [0.40, 0.50, 0.60]
        print("SMOKE: reduced grid/steps; byte-check will not match committed panels.")
        recon, ok, _ = phase1(out, W, sigmas=sig, rhos=rho, seeds=2)
        phase2_smoke(out, W, sig, rho)
        print(f"\nSMOKE done -> {out}")
        return

    if args.phase in ("1", "all"):
        _, ok, _ = phase1(out, W)
        if args.phase == "1":
            return
        if not ok:
            print("\nStopping after Phase 1: an E1 halt threshold tripped. "
                  "Review the recon map before running Phase 2.")
            sys.exit(2)

    if args.phase in ("2", "all"):
        phase2(out, W)
        print(f"\nDone. brief-08 outputs written to {out}")


def phase2_smoke(out, workers, sig, rho):
    """Phase 2 on a reduced grid/steps for the end-to-end check."""
    global PANEL_SEEDS
    cfgs = _configs()
    panels = run_grid_panels(cfgs, sigmas=sig, rhos=rho, seeds=3, steps=300,
                             workers=workers, metrics=PANEL_METRICS)
    tagged_panels, tagged_cells, all_panels, all_cells = {}, {}, [], []
    for cfg, panel in zip(cfgs, panels):
        key = (cfg["c0"], cfg["eta"], cfg["expectation_gain"])
        cells = cells_from_panel(panel)
        tagged_panels[key], tagged_cells[key] = panel, cells
        all_panels.append(panel.assign(c0=cfg["c0"], eta=cfg["eta"],
                                       expectation_gain=cfg["expectation_gain"]))
        all_cells.append(cells.assign(c0=cfg["c0"], eta=cfg["eta"], lambda_e=cfg["expectation_gain"]))
    _write(pd.concat(all_panels, ignore_index=True), out, "ces_b08_stage_a_panel.csv")
    _write(pd.concat(all_cells, ignore_index=True), out, "ces_b08_cells.csv")
    star = _e1_sigma_star(tagged_panels, tagged_cells, rho)
    _write(star, out, "ces_b08_sigma_star.csv")
    cmap = _e2_collapse_map(tagged_panels)
    _write(cmap, out, "ces_b08_collapse_map.csv")
    trace = _e2_trace(None, workers, steps=300, seeds=2)
    _write(trace, out, "ces_b08_trace.csv")
    _byte_check(out, "ces_b08_stage_a_panel.csv")
    _plot_sigma_star(star, os.path.join(out, "ces_b08_sigma_star_lambda.png"))
    _plot_collapse_map(cmap, os.path.join(out, "ces_b08_collapse_map.png"))
    _plot_trace(trace, os.path.join(out, "ces_b08_trace.png"))


if __name__ == "__main__":
    main()

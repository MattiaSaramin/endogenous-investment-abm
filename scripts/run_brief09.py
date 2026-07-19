#!/usr/bin/env python
"""Regenerate the brief-09 government sweep (balanced-budget unemployment benefit).

Brief 09 reinnests the balanced-budget unemployment benefit from the Leontief branch onto
the CES + labour-market + wage-curve + adaptive-expectations core.  One new economic
parameter, ``benefit_replacement_rate`` (rr): a flat income tax funds an equal transfer to
the unemployed, nested so ``rr = 0`` recovers the pre-brief-09 model bit-for-bit.  It reuses
the brief-05 robustness stack unchanged (``run_grid_panels`` single-pool, ``bootstrap_sigma_star``,
``cells_from_panel``); ``benefit_replacement_rate`` threads through ``**params`` to ``MacroModel``
with no signature change, exactly as ``eta`` and ``c0`` do.

Three experiments (approved compute plan):

* **E1 - fiscal dose-response (primary).**  rr in {0, 0.25, 0.5, 0.75} at the two reference
  scenarios - anchor (c0=2.0, sigma=1, eta=0, rho=0.40) and headline
  (c0=1.0, sigma=0.5, eta=0.10, rho=0.40) - 20 seeds.  Reports U, Y, K, wage share, realised
  tax rate and cash-constrained fraction per rr, with inter-seed bands, for comparison with
  the sandbox probe (U down, Y up, K up = crowding-in in a demand-constrained regime).

* **E2 - robustness of the sign frontier.**  sigma*(eta) at rr=0.5 vs rr=0 (c0=1.0,
  eta in {0, 0.10}, the brief-05 sigma x rho grid, bootstrap CI, 20 seeds).  Expectation: a
  small shift - the benefit raises the level of demand, not the elasticity of substitution;
  whatever it is, it is reported with CI.

* **E3 - the c0=2.0 stabilisation hypothesis (falsifiable).**  Collapse map at rr=0.5
  (eta in {0.10, 0.15}) vs the canonical b07/b08, plus a traced trajectory of the reference
  collapsing cell (sigma=1.5, rho=0.40, eta=0.10) at rr in {0, 0.5}.  Hypothesis: a demand
  floor when U rises shrinks the collapse region.  Confirmed or not, it is reported.

Two phases:

* **Phase 1 - viability reconnaissance (3-seed).**  The full sigma x rho grid at every
  (c0, eta, rr).  For E2 (c0=1.0) it applies one EXPLICIT halt threshold vs the same-(c0, eta)
  rr=0 control: a common viable support that loses MORE THAN ONE rho cell halts before the
  20-seed panel.  For E3 (c0=2.0) collapse is the deliverable, not a halt condition, so the
  map is reported and the run auto-continues.

* **Phase 2 - production panel (20-seed).**  The same 8 (c0, eta, rr) configs at 20 seeds in
  ONE process pool (single-pool correction).  E2 takes sigma* (Y and U) with a bootstrap CI on
  the common viable support; E3 builds the collapse map and reference-cell trace; the rr=0
  slices are byte-checked against the committed b05 (eta=0) / b07 (eta>0) panels (artifact vs
  artifact).  E1's dose-response is run separately (single cells, extra fiscal reporters).

Determinism: BLAS pinned to one thread before numpy is imported (below); the simulation path
is thread-invariant and every bootstrap is deterministic given its rng_seed.

Usage
-----
    python scripts/run_brief09.py                 # all phases -> results/, threads pinned
    python scripts/run_brief09.py --phase 1       # reconnaissance only (fast)
    python scripts/run_brief09.py --phase 2       # panel only (assumes recon passed)
    python scripts/run_brief09.py --smoke         # tiny grid/steps end-to-end check
    python scripts/run_brief09.py --workers 1     # serial (slow)
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

# Pin BLAS/numpy to one thread BEFORE numpy is imported (here via pandas/experiment), so the
# reduction order in the derived tables is deterministic and machine-independent, and the
# worker processes do not each spawn a full BLAS pool and oversubscribe the cores.
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
    common_viable_support,
    run_grid_panels,
    run_single,
)

# --- experiment configuration (approved compute plan) ---------------------
RR_DOSE = [0.0, 0.25, 0.5, 0.75]           # E1 dose-response
RR_GRID = [0.0, 0.5]                       # E2/E3 grid (rr=0 is the byte-checked control)
E2_C0, E2_ETAS = 1.0, [0.0, 0.10]          # frontier robustness (headline demand regime)
E3_C0, E3_ETAS = 2.0, [0.10, 0.15]         # stabilisation hypothesis (collapse regime)
RECON_SEEDS = 3
PANEL_SEEDS = 20

#: The two reference scenarios for E1, each a single (sigma, rho) cell swept over rr.
E1_SCENARIOS = {
    "anchor":   dict(c0=2.0, sigma=1.0, eta=0.0,  rho=0.40),
    "headline": dict(c0=1.0, sigma=0.5, eta=0.10, rho=0.40),
}

#: E2 halt threshold vs the same-(c0, eta) rr=0 control.
SUPPORT_LOSS_MAX = 1                        # halt E2 if a support loses MORE THAN this many rho

#: U at or above this counts a seed as fully collapsed (no employment).
U_COLLAPSE = 0.999

#: Committed references the rr=0 control must reproduce byte-for-byte.
B05_PANEL = "ces_b05_stage_a_panel.csv"    # eta = 0
B07_PANEL = "ces_b07_stage_a_panel.csv"    # eta > 0

#: The reference collapsing cell traced in E3 (traced at rr=0 in brief 07/08; sigma>1 collapse).
TRACE_CELL = dict(sigma=1.5, rho=0.40, eta=0.10, c0=2.0)

#: Grid-panel reporters: the shared brief-05/07 list PLUS the two fiscal saturation
#: diagnostics E3 needs (realised tax rate and cap-binding indicator).  Appended, never
#: interleaved, so the rr=0 slice stays byte-comparable to b05/b07 on the SHARED columns
#: (the byte-check compares only the reference's columns, so these extras are invisible to it).
GRID_METRICS = list(_PANEL_METRICS) + ["Tax_Rate", "Tax_At_Cap"]

#: Extra reporters for the E1 dose-response (fiscal quantities not in the shared panel list).
DOSE_METRICS = list(_PANEL_METRICS) + ["Tax_Rate", "Benefit_Per_Head", "Gov_Transfers", "Tax_At_Cap"]


def _grid_configs():
    """The 8 (c0, eta, rr) grid configurations, E2 then E3, in a fixed order."""
    cfgs = []
    for c0, etas in ((E2_C0, E2_ETAS), (E3_C0, E3_ETAS)):
        for eta in etas:
            for rr in RR_GRID:
                cfgs.append({"c0": c0, "eta": eta, "benefit_replacement_rate": rr})
    return cfgs


def _tag(cfg):
    return f"c0={cfg['c0']} eta={cfg['eta']:<4} rr={cfg['benefit_replacement_rate']}"


# ----------------------------------------------------------------------
# Phase 1 - reconnaissance
# ----------------------------------------------------------------------

def phase1(out, workers, sigmas=SIGMA_SWEEP_B05, rhos=RHO_SWEEP_B05, seeds=RECON_SEEDS):
    """Run the reconnaissance grid (one pool), write the map, evaluate the E2 halt.

    Returns ``(recon_df, ok, messages)``: ``ok`` is False if an E2 config tripped the
    support-loss threshold vs its rr=0 control.  E3 collapse is reported but never halts.
    """
    cfgs = _grid_configs()
    print(f"Phase 1 - reconnaissance ({seeds} seeds), {len(cfgs)} configs in one pool:")
    panels = run_grid_panels(cfgs, sigmas=sigmas, rhos=rhos, seeds=seeds, workers=workers)

    frames, supports = [], {}
    for cfg, panel in zip(cfgs, panels):
        cells = cells_from_panel(panel)
        key = (cfg["c0"], cfg["eta"], cfg["benefit_replacement_rate"])
        supports[key] = common_viable_support(cells, rhos=rhos)
        cells = cells.assign(c0=cfg["c0"], eta=cfg["eta"], rr=cfg["benefit_replacement_rate"])
        frames.append(cells)
        n_viable = int((~cells["collapsed"]).sum())
        print(f"  {_tag(cfg)}: viable cells={n_viable:>2d}  common support={supports[key]}")

    recon = pd.concat(frames, ignore_index=True)
    cols = ["c0", "eta", "rr", "sigma", "rho", "Y", "Unemployment_Rate", "Wage_Rate",
            "collapsed", "binding", "frac_seeds_collapsed", "mixed_basin"]
    _write(recon[cols].rename(columns={"Unemployment_Rate": "U"}),
           out, "ces_b09_viability_recon.csv")

    # --- E2 halt: support loss vs same-(c0, eta) rr=0 --------------------
    ok, messages = True, []
    for eta in E2_ETAS:
        base = set(supports[(E2_C0, eta, 0.0)])
        dropped = base - set(supports[(E2_C0, eta, 0.5)])
        if len(dropped) > SUPPORT_LOSS_MAX:
            ok = False
            messages.append(
                f"HALT c0={E2_C0} eta={eta} rr=0.5: viable support lost {len(dropped)} rho "
                f"cells vs rr=0 (dropped {sorted(dropped)}); threshold is >{SUPPORT_LOSS_MAX}.")

    # --- E3 collapse report (informational) -----------------------------
    print("Phase 1 - E3 (c0=2.0) collapse fractions (deliverable, not a halt):")
    for eta in E3_ETAS:
        for rr in RR_GRID:
            key = (E3_C0, eta, rr)
            block = recon[(recon["c0"] == E3_C0) & (recon["eta"] == eta) & (recon["rr"] == rr)]
            frac = float(block["collapsed"].mean())
            print(f"  c0=2.0 eta={eta:<4} rr={rr}: collapsed cells "
                  f"{int(block['collapsed'].sum())}/{len(block)} ({frac:.0%})  "
                  f"support={supports[key]}")

    if ok:
        print("Phase 1 gate (E2): PASS - no support-loss threshold tripped, auto-continue.")
    else:
        print("Phase 1 gate (E2): HALT")
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
    cfgs = _grid_configs()
    print(f"Phase 2 - production panel ({seeds} seeds), {len(cfgs)} configs in ONE pool:")
    panels = run_grid_panels(cfgs, sigmas=sigmas, rhos=rhos, seeds=seeds, workers=workers,
                             metrics=GRID_METRICS)

    tagged_panels, tagged_cells, all_panels, all_cells = {}, {}, [], []
    for cfg, panel in zip(cfgs, panels):
        key = (cfg["c0"], cfg["eta"], cfg["benefit_replacement_rate"])
        cells = cells_from_panel(panel)
        tagged_panels[key], tagged_cells[key] = panel, cells
        all_panels.append(panel.assign(c0=cfg["c0"], eta=cfg["eta"],
                                       benefit_replacement_rate=cfg["benefit_replacement_rate"]))
        all_cells.append(cells.assign(c0=cfg["c0"], eta=cfg["eta"],
                                      rr=cfg["benefit_replacement_rate"]))

    big_panel = pd.concat(all_panels, ignore_index=True)
    panel_name = "ces_b09_stage_a_panel.csv"
    _write(big_panel, out, panel_name)
    _write(pd.concat(all_cells, ignore_index=True), out, "ces_b09_cells.csv")

    # --- E2: sigma*(eta; rr) at c0=1.0, comparable across (eta, rr) ------
    star = _e2_sigma_star(tagged_panels, tagged_cells, rhos)
    _write(star, out, "ces_b09_sigma_star.csv")

    # --- E3: collapse map + reference-cell trace -------------------------
    cmap = _e3_collapse_map(tagged_panels)
    _write(cmap, out, "ces_b09_collapse_map.csv")
    trace = _e3_trace(workers)
    _write(trace, out, "ces_b09_trace.csv")

    # --- rr=0 byte-identity vs committed b05/b07 (artifact vs artifact) --
    check = _byte_check(out, panel_name)
    _write(check, out, "ces_b09_nesting_check.csv")

    # --- E1: fiscal dose-response (single cells, extra reporters) --------
    dose = _e1_dose_response(workers)
    _write(dose, out, "ces_b09_dose_response.csv")

    # --- figures ---------------------------------------------------------
    f1 = _plot_dose_response(dose, os.path.join(out, "ces_b09_dose_response.png"))
    f2 = _plot_sigma_star(star, os.path.join(out, "ces_b09_sigma_star_rr.png"))
    f3 = _plot_collapse_map(cmap, os.path.join(out, "ces_b09_collapse_map.png"))
    f4 = _plot_trace(trace, os.path.join(out, "ces_b09_trace.png"))
    for f in (f1, f2, f3, f4):
        print(f"  wrote {os.path.basename(f)}")

    _print_headline(dose, star, cmap, trace)
    return big_panel, star


def _e2_sigma_star(tagged_panels, tagged_cells, rhos):
    """sigma*(eta; rr) at c0 = 1.0 on the support viable across ALL (eta, rr) at c0=1.0.

    Estimating every point on one common support keeps sigma* comparable across eta and rr (a
    support that shifted with rr would confound the fiscal transfer with which cells survived).
    The rr = 0 / eta = 0 config is also reported on its FULL natural support - the brief-05
    canonical anchor (sigma* ~ 0.654).
    """
    e2_keys = [(E2_C0, eta, rr) for eta in E2_ETAS for rr in RR_GRID]
    nat = {k: common_viable_support(tagged_cells[k], rhos=rhos) for k in e2_keys}
    est_support = [r for r in rhos if all(r in nat[k] for k in e2_keys)]
    print(f"  E2 across-(eta,rr) common support (sigma* estimated here) = {est_support}")

    rows = []
    for (c0, eta, rr) in e2_keys:
        panel = tagged_panels[(c0, eta, rr)]
        for target, col in (("Y", "Output"), ("U", "Unemployment_Rate")):
            rows.append({"c0": c0, "eta": eta, "rr": rr, "target": target,
                         "support_kind": "across_config", "support": str(est_support),
                         **_sigma_star_row(panel, est_support, col)})
        if eta == 0.0 and rr == 0.0:
            for target, col in (("Y", "Output"), ("U", "Unemployment_Rate")):
                rows.append({"c0": c0, "eta": eta, "rr": rr, "target": target,
                             "support_kind": "natural_anchor", "support": str(nat[(c0, eta, rr)]),
                             **_sigma_star_row(panel, nat[(c0, eta, rr)], col)})
    return pd.DataFrame(rows)[
        ["c0", "eta", "rr", "target", "support_kind", "sigma_star", "ci_lo", "ci_hi",
         "frac_undefined", "n_crossings", "P_star_gt_0.60", "P_star_gt_0.40", "support"]]


def _e3_collapse_map(tagged_panels):
    """Per (eta, rr, sigma, rho) at c0 = 2.0: fraction of seeds collapsed / at U = 1, plus
    the realised tax rate and cap-saturation fraction (brief 09 report add-on).

    ``frac_seeds_collapsed`` (mean Output < COLLAPSE_Y per seed) is the brief-04/05 collapse
    definition, so the rr = 0 rows equal ces_b07_cells exactly; ``frac_seeds_U1`` is the
    stricter "no employment left" reading the brief asks for.  ``mean_tax`` and
    ``frac_periods_at_cap`` (seed-mean of the per-seed tail-fraction at ``max_tax``) diagnose
    instrument saturation: where the base is almost all wages the transfer is MPC-neutral and
    the benefit loses traction, and where U -> 1 the cap tends to pin the rate.
    """
    rows = []
    for eta in E3_ETAS:
        for rr in RR_GRID:
            panel = tagged_panels[(E3_C0, eta, rr)]
            g = panel.assign(
                _dead=panel["Output"] < COLLAPSE_Y,
                _u1=panel["Unemployment_Rate"] >= U_COLLAPSE,
            ).groupby(["sigma", "rho"], as_index=False)
            m = g.agg(frac_seeds_collapsed=("_dead", "mean"),
                      frac_seeds_U1=("_u1", "mean"),
                      mean_U=("Unemployment_Rate", "mean"),
                      Y=("Output", "mean"),
                      mean_tax=("Tax_Rate", "mean"),
                      frac_periods_at_cap=("Tax_At_Cap", "mean"))
            m.insert(0, "rr", rr)
            m.insert(0, "eta", eta)
            m.insert(0, "c0", E3_C0)
            rows.append(m)
    return pd.concat(rows, ignore_index=True)


def _e3_trace(workers, steps=2000, seeds=6):
    """Full time series of the reference collapsing cell at rr in {0, 0.5} (brief 09 §4 E3).

    sigma = 1.5, rho = 0.40, eta = 0.10, c0 = 2.0 collapses at rr = 0 (brief 07/08, 6/6 seeds).
    Tracks capital, unemployment, wage and output over the run so the report can say whether
    the demand floor damps the wage-employment oscillation and stops capital eroding.  Keeps
    the realised tax rate and cap-binding flag too (instrument-saturation diagnostic): does the
    benefit fund itself, or does the cap pin the rate as U climbs?
    """
    keep = ["Output", "Total_Capital", "Unemployment_Rate", "Wage_Rate", "Tax_Rate", "Tax_At_Cap"]
    frames = []
    for rr in RR_GRID:
        for seed in range(seeds):
            df = run_single(
                TRACE_CELL["rho"], steps=steps, seed=seed, sigma=TRACE_CELL["sigma"],
                c0=TRACE_CELL["c0"], eta=TRACE_CELL["eta"], benefit_replacement_rate=rr,
            )[keep].copy()
            df["step"] = df.index
            df["rr"] = rr
            df["seed"] = seed
            frames.append(df.reset_index(drop=True))
    return pd.concat(frames, ignore_index=True)


def _e1_dose_response(workers):
    """E1 - fiscal dose-response at the two reference scenarios (brief 09 §4 E1).

    Each scenario is a single (sigma, rho) cell swept over rr in {0, 0.25, 0.5, 0.75}, run at
    20 seeds through the single-pool runner (one pool per scenario - the two scenarios differ
    in sigma).  Reports the tail-50 steady state per rr with inter-seed bands, plus the realised
    tax rate and cash-constrained fraction.
    """
    keep = ["Unemployment_Rate", "Output", "Total_Capital", "Wage_Share",
            "Tax_Rate", "Benefit_Per_Head", "Cash_Constrained"]
    rows = []
    for name, sc in E1_SCENARIOS.items():
        cfgs = [{"c0": sc["c0"], "eta": sc["eta"], "benefit_replacement_rate": rr}
                for rr in RR_DOSE]
        print(f"  E1 dose-response scenario '{name}' ({sc}) over rr={RR_DOSE}:")
        panels = run_grid_panels(cfgs, sigmas=[sc["sigma"]], rhos=[sc["rho"]],
                                 seeds=PANEL_SEEDS, workers=workers, metrics=DOSE_METRICS)
        for rr, panel in zip(RR_DOSE, panels):
            row = {"scenario": name, "c0": sc["c0"], "sigma": sc["sigma"],
                   "eta": sc["eta"], "rho": sc["rho"], "rr": rr, "n_seeds": panel["seed"].nunique()}
            for m in keep:
                row[m] = float(panel[m].mean())
                row[f"{m}_lo"] = float(panel[m].min())
                row[f"{m}_hi"] = float(panel[m].max())
            rows.append(row)
    return pd.DataFrame(rows)


def _byte_check(out, panel_name):
    """rr = 0 slices reproduce the committed b05 (eta=0) / b07 (eta>0) panels byte-for-byte.

    Artifact vs artifact (brief 07 discipline): both the just-written b09 panel and the
    committed reference are read from disk WITHOUT re-serializing, because pandas ``to_csv`` is
    not perfectly round-trip-lossless.  The b09 model at rr = 0 is the pre-brief-09 code path,
    so each shared-column slice must be identical; any nonzero deviation is a FINDING.
    """
    panel_path = os.path.join(out, panel_name)
    if not os.path.exists(panel_path):
        return pd.DataFrame([{"note": f"{panel_name} not found; check skipped"}])
    mine_all = pd.read_csv(panel_path)
    mine0 = mine_all[mine_all["benefit_replacement_rate"] == 0.0]

    rows, all_ok = [], True
    print("  nesting check (rr=0 written panel vs committed b05/b07, artifact vs artifact):")
    for (c0, eta), grp in mine0.groupby(["c0", "eta"]):
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
        num = b.select_dtypes(include=[float, int]).columns
        dev = float(np.max(np.abs(a[num].to_numpy() - b[num].to_numpy())))
        byte_equal = a.to_csv(index=False) == b.to_csv(index=False)
        ok = byte_equal and dev == 0.0
        all_ok = all_ok and ok
        rows.append({"c0": c0, "eta": eta, "ref": ref_name, "byte_equal": byte_equal,
                     "max_abs_dev": dev, "note": "PASS" if ok else "FINDING"})
        print(f"    c0={c0} eta={eta}: {'PASS' if ok else 'FINDING'}  ref={ref_name}  "
              f"n_rows={len(a)}  byte_equal={byte_equal}  max_abs_dev={dev:.1e}")
    if not all_ok:
        print("  nesting check: FINDING - rr=0 did not reproduce a committed panel.")
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# Reporting / figures
# ----------------------------------------------------------------------

def _print_headline(dose, star, cmap, trace):
    print("\nE1 dose-response (tail-50 steady state, 20 seeds):")
    for name in E1_SCENARIOS:
        block = dose[dose["scenario"] == name].sort_values("rr")
        print(f"  scenario '{name}':")
        for _, r in block.iterrows():
            print(f"    rr={r['rr']:<4}  U={r['Unemployment_Rate']:.3f}  Y={r['Output']:7.2f}  "
                  f"K={r['Total_Capital']:7.2f}  wage_share={r['Wage_Share']:.3f}  "
                  f"tax={r['Tax_Rate']:.3f}  cash_constr={r['Cash_Constrained']:.2f}")

    print("\nE2 sigma*(eta; rr) on Y, c0=1.0, across-config common support:")
    y = star[(star["target"] == "Y") & (star["support_kind"] == "across_config")]
    for _, r in y.sort_values(["eta", "rr"]).iterrows():
        star_s = f"{r['sigma_star']:.4f}" if np.isfinite(r["sigma_star"]) else "  nan "
        print(f"  eta={r['eta']:<4} rr={r['rr']}: sigma*={star_s} "
              f"[{r['ci_lo']:.4f}, {r['ci_hi']:.4f}]  frac_undef={r['frac_undefined']:.3f}")

    print("\nE3 collapse (c0=2.0), mean frac of seeds fully collapsed (U=1) + tax saturation:")
    for (eta, rr), b in cmap.groupby(["eta", "rr"]):
        print(f"  eta={eta:<4} rr={rr}: mean frac_seeds_U1={b['frac_seeds_U1'].mean():.3f}  "
              f"cells with any collapse={int((b['frac_seeds_collapsed'] > 0).sum())}/{len(b)}  "
              f"mean_tax={b['mean_tax'].mean():.3f}  frac_at_cap={b['frac_periods_at_cap'].mean():.3f}")

    print("\nE3 reference-cell trace (sigma=1.5, rho=0.40, eta=0.10, c0=2.0), tail-100 means:")
    for rr, b in trace.groupby("rr"):
        tail = b[b["step"] >= b["step"].max() - 100]
        print(f"  rr={rr}: K={tail['Total_Capital'].mean():7.2f}  "
              f"U={tail['Unemployment_Rate'].mean():.3f}  "
              f"wage={tail['Wage_Rate'].mean():.3f}  Y={tail['Output'].mean():7.2f}  "
              f"tax={tail['Tax_Rate'].mean():.3f}  frac_at_cap={tail['Tax_At_Cap'].mean():.3f}")


def _plot_dose_response(dose, path):
    """U, Y, K vs rr with inter-seed bands, one line per scenario - the E1 headline figure."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for (metric, ax, title) in (("Unemployment_Rate", axes[0], "Unemployment U"),
                                ("Output", axes[1], "Output Y"),
                                ("Total_Capital", axes[2], "Capital K")):
        for name, block in dose.groupby("scenario"):
            b = block.sort_values("rr")
            line, = ax.plot(b["rr"], b[metric], marker="o", label=name)
            ax.fill_between(b["rr"], b[f"{metric}_lo"], b[f"{metric}_hi"],
                            alpha=0.15, color=line.get_color())
        ax.set_xlabel("replacement rate  rr")
        ax.set_title(title, weight="bold")
        ax.legend(fontsize=8)
    fig.suptitle("E1 fiscal dose-response (crowding-in in a demand-constrained regime)",
                 weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _plot_sigma_star(star, path):
    """sigma*(rr) with CI bands, one line per eta - the E2 robustness figure (c0=1.0)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y = star[(star["target"] == "Y") & (star["support_kind"] == "across_config")]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for eta, block in y.groupby("eta"):
        b = block.sort_values("rr")
        line, = ax.plot(b["rr"], b["sigma_star"], marker="o", label=f"eta = {eta}")
        ax.fill_between(b["rr"], b["ci_lo"], b["ci_hi"], alpha=0.18, color=line.get_color())
    ax.axhspan(0.40, 0.60, color="grey", alpha=0.15, label="empirical sigma 0.40-0.60")
    ax.axhline(1.0, ls="--", lw=1, color="grey")
    ax.set_xlabel("replacement rate  rr")
    ax.set_ylabel("sign frontier  sigma*  (dY/drho = 0)")
    ax.set_title("Does the benefit move the sign frontier? (c0 = 1.0)", weight="bold")
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _plot_collapse_map(cmap, path):
    """Small-multiples heatmap of frac_seeds_U1 over (sigma, rho), one panel per (eta, rr)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    etas = sorted(cmap["eta"].unique())
    rrs = sorted(cmap["rr"].unique())
    fig, axes = plt.subplots(len(etas), len(rrs), figsize=(3.2 * len(rrs), 3.0 * len(etas)),
                             squeeze=False)
    for i, eta in enumerate(etas):
        for j, rr in enumerate(rrs):
            ax = axes[i][j]
            block = cmap[(cmap["eta"] == eta) & (cmap["rr"] == rr)]
            piv = block.pivot(index="sigma", columns="rho", values="frac_seeds_U1")
            im = ax.pcolormesh(piv.columns, piv.index, piv.to_numpy(),
                               cmap="magma", vmin=0.0, vmax=1.0, shading="nearest")
            ax.set_title(f"eta={eta}, rr={rr}", fontsize=9)
            if j == 0:
                ax.set_ylabel("sigma")
            if i == len(etas) - 1:
                ax.set_xlabel("rho")
    fig.colorbar(im, ax=axes, label="frac of seeds fully collapsed (U=1)", shrink=0.8)
    fig.suptitle("E3 collapse map (c0 = 2.0): does the demand floor shrink it?", weight="bold")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _plot_trace(trace, path):
    """Reference-cell trajectories: capital and unemployment over time, per rr (seed-mean)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (axk, axu) = plt.subplots(1, 2, figsize=(12, 4.5))
    for rr, b in trace.groupby("rr"):
        g = b.groupby("step")
        axk.plot(g["Total_Capital"].mean(), label=f"rr={rr}")
        axu.plot(g["Unemployment_Rate"].mean(), label=f"rr={rr}")
    axk.set_xlabel("step"); axk.set_ylabel("Total capital K"); axk.legend(fontsize=8)
    axk.set_title("Does the demand floor stop capital eroding?", weight="bold")
    axu.set_xlabel("step"); axu.set_ylabel("Unemployment rate"); axu.legend(fontsize=8)
    axu.set_title("Does the oscillation damp?", weight="bold")
    fig.suptitle("E3 reference cell (sigma=1.5, rho=0.40, eta=0.10, c0=2.0)", weight="bold")
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
        # steps mean the rr=0 byte-check against the 2000-step committed panels will report
        # FINDING; that is expected in smoke mode.
        sig = [0.5, 1.0, 1.25]
        rho = [0.40, 0.50, 0.60]
        print("SMOKE: reduced grid/steps; byte-check will not match committed panels.")
        phase1(out, W, sigmas=sig, rhos=rho, seeds=2)
        phase2_smoke(out, W, sig, rho)
        print(f"\nSMOKE done -> {out}")
        return

    if args.phase in ("1", "all"):
        _, ok, _ = phase1(out, W)
        if args.phase == "1":
            return
        if not ok:
            print("\nStopping after Phase 1: an E2 halt threshold tripped. "
                  "Review the recon map before running Phase 2.")
            sys.exit(2)

    if args.phase in ("2", "all"):
        phase2(out, W)
        print(f"\nDone. brief-09 outputs written to {out}")


def phase2_smoke(out, workers, sig, rho):
    """Phase 2 on a reduced grid/steps for the end-to-end check."""
    cfgs = _grid_configs()
    panels = run_grid_panels(cfgs, sigmas=sig, rhos=rho, seeds=3, steps=300, workers=workers,
                             metrics=GRID_METRICS)
    tagged_panels, tagged_cells, all_panels, all_cells = {}, {}, [], []
    for cfg, panel in zip(cfgs, panels):
        key = (cfg["c0"], cfg["eta"], cfg["benefit_replacement_rate"])
        cells = cells_from_panel(panel)
        tagged_panels[key], tagged_cells[key] = panel, cells
        all_panels.append(panel.assign(c0=cfg["c0"], eta=cfg["eta"],
                                       benefit_replacement_rate=cfg["benefit_replacement_rate"]))
        all_cells.append(cells.assign(c0=cfg["c0"], eta=cfg["eta"], rr=cfg["benefit_replacement_rate"]))
    _write(pd.concat(all_panels, ignore_index=True), out, "ces_b09_stage_a_panel.csv")
    _write(pd.concat(all_cells, ignore_index=True), out, "ces_b09_cells.csv")
    star = _e2_sigma_star(tagged_panels, tagged_cells, rho)
    _write(star, out, "ces_b09_sigma_star.csv")
    cmap = _e3_collapse_map(tagged_panels)
    _write(cmap, out, "ces_b09_collapse_map.csv")
    trace = _e3_trace(workers, steps=300, seeds=2)
    _write(trace, out, "ces_b09_trace.csv")
    dose = _e1_dose_response_smoke(workers)
    _write(dose, out, "ces_b09_dose_response.csv")
    _byte_check(out, "ces_b09_stage_a_panel.csv")
    _plot_dose_response(dose, os.path.join(out, "ces_b09_dose_response.png"))
    _plot_sigma_star(star, os.path.join(out, "ces_b09_sigma_star_rr.png"))
    _plot_collapse_map(cmap, os.path.join(out, "ces_b09_collapse_map.png"))
    _plot_trace(trace, os.path.join(out, "ces_b09_trace.png"))


def _e1_dose_response_smoke(workers):
    """E1 on a reduced seed count/steps for the smoke check."""
    keep = ["Unemployment_Rate", "Output", "Total_Capital", "Wage_Share",
            "Tax_Rate", "Benefit_Per_Head", "Cash_Constrained"]
    rows = []
    for name, sc in E1_SCENARIOS.items():
        cfgs = [{"c0": sc["c0"], "eta": sc["eta"], "benefit_replacement_rate": rr}
                for rr in RR_DOSE]
        panels = run_grid_panels(cfgs, sigmas=[sc["sigma"]], rhos=[sc["rho"]],
                                 seeds=3, steps=300, workers=workers, metrics=DOSE_METRICS)
        for rr, panel in zip(RR_DOSE, panels):
            row = {"scenario": name, "c0": sc["c0"], "sigma": sc["sigma"],
                   "eta": sc["eta"], "rho": sc["rho"], "rr": rr, "n_seeds": panel["seed"].nunique()}
            for m in keep:
                row[m] = float(panel[m].mean())
                row[f"{m}_lo"] = float(panel[m].min())
                row[f"{m}_hi"] = float(panel[m].max())
            rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main()

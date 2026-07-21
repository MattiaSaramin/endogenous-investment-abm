#!/usr/bin/env python
"""Regenerate the brief-10 firm-heterogeneity viability probe.

Brief 10 does NOT implement roadmap point 8 (heterogeneous firm productivity as a
feature).  It produces the measured, citable evidence for the decision to leave the firm
side quasi-representative: with A_i dispersed mean-preservingly and NO reallocation
channel (no selection, no demand rerouting, no entry/exit),

* **below a dispersion threshold** the aggregates are indistinguishable from the
  homogeneous model (U and Y inside the spread = 0 inter-seed band, no firm dies), so the
  "mean-field on the firm side" statement becomes a MEASURED claim rather than an
  assertion; and
* **above it** the economy collapses through a domino: the low-A firm serves the same
  network demand with more labour -> lower profit -> I < delta*K -> K -> 0; spending
  shares stay pointed at the dead firm (demand destroyed) and its laid-off workers lose
  their income (a demand externality), so the high-A firms die too, in cascade.

One new experimental dial, ``productivity_spread``, nested so spread = 0 recovers the
homogeneous model bit-for-bit.  Nothing else in the model changes: no flow, no step, no
settlement, so SFC is untouched at any spread (asserted in the test suite, not here).

Three scenarios, all at the reference retention rho = 0.40 (the brief-09 E1 convention):

* **S1 anchor**    c0 = 2.0, sigma = 1,   eta = 0,    rr = 0
* **S2 headline**  c0 = 1.0, sigma = 0.5, eta = 0.10, rr = 0
* **S3 (E2)**      as S2 but rr = 0.5 - does the brief-09 unemployment benefit, which
  keeps income flowing to the laid-off, cushion the demand externality and RAISE the
  viability threshold?  Falsifiable; whatever comes out is reported.

Single phase (about 420 runs): the deliverable IS the collapse, so there is nothing a
reconnaissance phase could gate on - unlike briefs 07-09, where losing the viable support
would have invalidated a sigma* estimate.  The 20-seed panel is run directly.

Two process pools rather than one: :func:`run_grid_panels` takes a single ``sigmas`` list
for every config, and S1 sits at sigma = 1 while S2/S3 sit at sigma = 0.5.  Configs are
therefore grouped by sigma - two pools, not the seven that a naive per-scenario loop would
spawn.  Determinism is unaffected (every cell is seeded and shares no state).

Determinism: BLAS pinned to one thread before numpy is imported (below); the simulation
path is thread-invariant.

Usage
-----
    python scripts/run_brief10.py               # full probe -> results/, threads pinned
    python scripts/run_brief10.py --smoke       # tiny grid/steps end-to-end check
    python scripts/run_brief10.py --workers 1   # serial (slow)
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

from experiment import _PANEL_METRICS, compare_artifacts, run_grid_panels
from model import MacroModel, _firms

# --- experiment configuration ---------------------------------------------

#: The dispersion grid.  Refined between 0.10 and 0.20 because the sandbox probe put the
#: threshold there; the endpoints are the two claims (0 = nested, 0.20 = collapse).
SPREADS = [0.0, 0.05, 0.10, 0.125, 0.15, 0.175, 0.20]

PANEL_SEEDS = 20
STEPS = 2000
TAIL = 50

#: rho = 0.40 everywhere: the reference retention the anchor was measured at and the one
#: brief 09 used for its dose-response scenarios.  Held fixed - this probe sweeps
#: dispersion, not retention.
REF_RHO = 0.40

#: The three scenarios.  ``ref`` names the committed panel whose corresponding rows the
#: spread = 0 slice must reproduce byte-for-byte.
SCENARIOS = {
    "S1_anchor":   dict(c0=2.0, sigma=1.0, eta=0.0,  rr=0.0,
                        ref="ces_b05_stage_a_panel.csv"),
    "S2_headline": dict(c0=1.0, sigma=0.5, eta=0.10, rr=0.0,
                        ref="ces_b07_stage_a_panel.csv"),
    "S3_benefit":  dict(c0=1.0, sigma=0.5, eta=0.10, rr=0.5,
                        ref="ces_b09_stage_a_panel.csv"),
}

#: A seed counts as "fully collapsed" at this unemployment rate (brief-09 convention).
U_COLLAPSE = 0.999

#: A spread crosses the viability threshold when at least this fraction of seeds shows the
#: symptom in the tail.  A DECLARED CONVENTION: the model has multiple equilibria, so a
#: spread can be a mixed basin (some seeds alive, some dead), and "the first spread where
#: it happens once" would report a basin boundary as a threshold.  The per-spread
#: fractions are written out so the threshold can be re-read at any other convention.
THRESHOLD_FRAC = 0.5

#: Panel reporters: the shared brief-05/07 list PLUS the fiscal pair brief 09 appended
#: (needed for the S3 byte-check against ces_b09) PLUS this brief's two diagnostics.
#: APPENDED, never interleaved, so the spread = 0 slice stays byte-comparable to the
#: committed panels on the SHARED columns.
GRID_METRICS = list(_PANEL_METRICS) + ["Tax_Rate", "Tax_At_Cap", "Dead_Firms", "TopK_Share"]

#: Metrics carried into the aggregate summary table.
SUMMARY_METRICS = ["Unemployment_Rate", "Output", "Total_Capital",
                   "Dead_Firms", "TopK_Share", "Wage_Share", "Investment"]

#: The traced domino: the headline scenario at the top of the dispersion grid.
TRACE = dict(scenario="S2_headline", spread=0.20, seeds=[0, 1, 2], figure_seed=0)


def _params(sc, spread):
    """MacroModel kwargs for a scenario at a given spread (sigma/rho travel separately)."""
    return {"c0": sc["c0"], "eta": sc["eta"],
            "benefit_replacement_rate": sc["rr"], "productivity_spread": spread}


# ----------------------------------------------------------------------
# The panel
# ----------------------------------------------------------------------

def run_panel(workers, spreads=SPREADS, seeds=PANEL_SEEDS, steps=STEPS, tail=TAIL):
    """Every (scenario, spread) cell at ``seeds`` seeds; one pool per distinct sigma.

    Returns the per-seed panel with the scenario label and its parameters attached.
    """
    by_sigma = {}
    for name, sc in SCENARIOS.items():
        by_sigma.setdefault(sc["sigma"], []).append(name)

    frames = []
    for sigma, names in by_sigma.items():
        jobs = [(name, spread) for name in names for spread in spreads]
        cfgs = [_params(SCENARIOS[name], spread) for name, spread in jobs]
        print(f"  pool sigma={sigma}: {len(cfgs)} configs x {seeds} seeds "
              f"({', '.join(sorted(set(n for n, _ in jobs)))})")
        panels = run_grid_panels(cfgs, sigmas=[sigma], rhos=[REF_RHO], seeds=seeds,
                                 steps=steps, tail=tail, workers=workers,
                                 metrics=GRID_METRICS)
        for (name, spread), panel in zip(jobs, panels):
            sc = SCENARIOS[name]
            frames.append(panel.assign(
                scenario=name, spread=spread, c0=sc["c0"], eta=sc["eta"],
                benefit_replacement_rate=sc["rr"],
            ))
    return pd.concat(frames, ignore_index=True).sort_values(
        ["scenario", "spread", "seed"], ignore_index=True)


def summarize(panel):
    """One row per (scenario, spread): seed means with inter-seed bands.

    ``*_within_band0`` answers the first of the brief's two questions directly: is the
    mean at this spread inside the spread = 0 inter-seed [min, max] band?  If it is, the
    dispersion is not distinguishable from homogeneity at this seed count - which is what
    turns "the firm side is mean-field" from an assertion into a measurement.
    """
    rows = []
    for (name, spread), block in panel.groupby(["scenario", "spread"]):
        row = {"scenario": name, "spread": spread, "n_seeds": block["seed"].nunique(),
               **{k: v for k, v in SCENARIOS[name].items() if k != "ref"}, "rho": REF_RHO}
        for m in SUMMARY_METRICS:
            row[m] = float(block[m].mean())
            row[f"{m}_lo"] = float(block[m].min())
            row[f"{m}_hi"] = float(block[m].max())
        row["frac_seeds_any_dead"] = float((block["Dead_Firms"] > 0.0).mean())
        row["frac_seeds_U1"] = float((block["Unemployment_Rate"] >= U_COLLAPSE).mean())
        rows.append(row)
    out = pd.DataFrame(rows).sort_values(["scenario", "spread"], ignore_index=True)

    for m in ("Output", "Unemployment_Rate"):
        out[f"{m}_within_band0"] = False
    for name, block in out.groupby("scenario"):
        base = block[block["spread"] == 0.0]
        if base.empty:
            continue
        rows = out["scenario"] == name
        for m in ("Output", "Unemployment_Rate"):
            lo, hi = float(base[f"{m}_lo"].iloc[0]), float(base[f"{m}_hi"].iloc[0])
            out.loc[rows, f"{m}_within_band0"] = out.loc[rows, m].between(lo, hi)
    return out


def thresholds(summary):
    """The viability threshold per scenario, and the E2 verdict.

    Two thresholds, both read off ``summary`` at the declared ``THRESHOLD_FRAC``:
    ``spread_first_death`` (the smallest spread at which firms die in at least that
    fraction of seeds) and ``spread_full_collapse`` (the smallest at which that fraction
    of seeds reaches U = 1).  ``nan`` means the symptom never appears in the swept range -
    a result, reported as such, not a missing value.
    """
    rows = []
    for name, block in summary.groupby("scenario"):
        b = block.sort_values("spread")

        def first(col):
            hit = b[b[col] >= THRESHOLD_FRAC]["spread"]
            return float(hit.iloc[0]) if len(hit) else float("nan")

        rows.append({
            "scenario": name,
            **{k: v for k, v in SCENARIOS[name].items() if k != "ref"},
            "spread_first_death": first("frac_seeds_any_dead"),
            "spread_full_collapse": first("frac_seeds_U1"),
            "threshold_frac": THRESHOLD_FRAC,
            "spreads_swept": str(list(b["spread"])),
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# The domino trace
# ----------------------------------------------------------------------

def run_trace(steps=STEPS, spec=TRACE):
    """Time series of a collapsing run, with the weakest and strongest firm's capital.

    The per-firm capital is not a model reporter (the model has no firm-level collector),
    so the run is stepped here and the two extreme firms of the fan are read off directly.
    They are identified by their A, not by construction order, so the series mean exactly
    what they say: ``K_lowA`` is the capital of the firm the fan made least productive.
    """
    sc = SCENARIOS[spec["scenario"]]
    frames = []
    for seed in spec["seeds"]:
        m = MacroModel(retention_ratio=REF_RHO, seed=seed, sigma=sc["sigma"],
                       **_params(sc, spec["spread"]))
        firms = sorted(_firms(m), key=lambda f: f.productivity)
        weak, strong = firms[0], firms[-1]
        rec = []
        for t in range(steps):
            m.step()
            row = m.datacollector.get_model_vars_dataframe().iloc[-1]
            rec.append({
                "step": t + 1, "seed": seed,
                "Output": row["Output"], "Total_Capital": row["Total_Capital"],
                "Unemployment_Rate": row["Unemployment_Rate"],
                "Dead_Firms": row["Dead_Firms"], "TopK_Share": row["TopK_Share"],
                "Wage_Rate": row["Wage_Rate"],
                "K_lowA": weak.capital, "K_highA": strong.capital,
                "A_low": weak.productivity, "A_high": strong.productivity,
            })
        frames.append(pd.DataFrame(rec))
    out = pd.concat(frames, ignore_index=True)
    out["scenario"] = spec["scenario"]
    out["spread"] = spec["spread"]
    return out


# ----------------------------------------------------------------------
# Nesting check
# ----------------------------------------------------------------------

def byte_check(out, panel_name):
    """spread = 0 reproduces the committed b05 / b07 / b09 rows byte-for-byte.

    Artifact vs artifact (the brief-07 discipline): both the just-written b10 panel and the
    committed reference are read back from disk WITHOUT re-serializing, because pandas
    ``to_csv`` is not perfectly round-trip-lossless.  At spread = 0 the model IS the
    pre-brief-10 code path, so each scenario's 20 seeds must match the corresponding
    (c0, eta, rr, sigma, rho) rows of its reference exactly.  Any nonzero deviation is a
    FINDING, printed and written, never smoothed over.
    """
    panel_path = os.path.join(out, panel_name)
    if not os.path.exists(panel_path):
        return pd.DataFrame([{"note": f"{panel_name} not found; check skipped"}])
    mine_all = pd.read_csv(panel_path)
    mine0 = mine_all[mine_all["spread"] == 0.0]

    rows, all_ok = [], True
    print("  nesting check (spread=0 written panel vs committed b05/b07/b09, "
          "artifact vs artifact):")
    for name, sc in SCENARIOS.items():
        ref_path = os.path.join(out, sc["ref"])
        if not os.path.exists(ref_path):
            all_ok = False
            rows.append({"scenario": name, "ref": sc["ref"], "byte_equal": False,
                         "max_abs_dev": float("nan"), "n_rows": 0,
                         "note": "reference not found"})
            print(f"    {name}: {sc['ref']} NOT FOUND  <-- FINDING")
            continue

        ref = pd.read_csv(ref_path)
        ref = ref[(ref["c0"] == sc["c0"]) & (ref["sigma"] == sc["sigma"])
                  & (ref["rho"] == REF_RHO)]
        if "eta" in ref.columns:
            ref = ref[ref["eta"] == sc["eta"]]
        if "benefit_replacement_rate" in ref.columns:
            ref = ref[ref["benefit_replacement_rate"] == sc["rr"]]

        mine = mine0[mine0["scenario"] == name]
        shared = [c for c in ref.columns if c in mine.columns]
        order = ["sigma", "rho", "seed"]
        a = mine[shared].sort_values(order).reset_index(drop=True)
        b = ref[shared].sort_values(order).reset_index(drop=True)
        if a.shape != b.shape:
            all_ok = False
            rows.append({"scenario": name, "ref": sc["ref"], "byte_equal": False,
                         "max_abs_dev": float("nan"), "n_rows": len(a),
                         "note": f"shape {a.shape} vs {b.shape}"})
            print(f"    {name}: SHAPE MISMATCH {a.shape} vs {b.shape}  <-- FINDING")
            continue

        # Criterion updated by brief 14 (task D): declared ULP tolerance on the levels plus
        # an EXACT regime match, replacing the retired ``dev == 0.0``.
        res = compare_artifacts(a, b)
        ok = res["ok"]
        all_ok = all_ok and ok
        rows.append({"scenario": name, "ref": sc["ref"], "n_rows": len(a),
                     "n_shared_cols": len(shared), **res,
                     "note": "PASS" if ok else "FINDING"})
        print(f"    {name}: {'PASS' if ok else 'FINDING'}  ref={sc['ref']}  "
              f"n_rows={len(a)}  cols={len(shared)}  "
              f"max_ulp_sig={res['max_ulp_significant']:.2f}  "
              f"n_exceed={res['n_exceed']}/{res['n_compared']}  "
              f"regime_equal={res['regime_equal']}  "
              f"(retired byte_equal={res['byte_equal']})")
    if not all_ok:
        print("  nesting check: FINDING - spread=0 did not reproduce a committed panel.")
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# Reporting / figures
# ----------------------------------------------------------------------

def print_headline(summary, thr, trace):
    n = int(summary["n_seeds"].max())
    print(f"\nAggregates vs dispersion (tail-50 steady state, {n} seeds, "
          "[inter-seed min, max]):")
    for name, block in summary.groupby("scenario"):
        sc = SCENARIOS[name]
        print(f"  {name}  (c0={sc['c0']}, sigma={sc['sigma']}, eta={sc['eta']}, "
              f"rr={sc['rr']}, rho={REF_RHO}):")
        for _, r in block.sort_values("spread").iterrows():
            flag = "" if r["Output_within_band0"] else "   <- outside spread=0 band"
            print(f"    spread={r['spread']:<6} U={r['Unemployment_Rate']:.3f} "
                  f"[{r['Unemployment_Rate_lo']:.3f},{r['Unemployment_Rate_hi']:.3f}]  "
                  f"Y={r['Output']:7.2f} [{r['Output_lo']:7.2f},{r['Output_hi']:7.2f}]  "
                  f"K={r['Total_Capital']:7.2f}  dead={r['Dead_Firms']:.2f}  "
                  f"topK={r['TopK_Share']:.3f}  "
                  f"f_dead={r['frac_seeds_any_dead']:.2f} f_U1={r['frac_seeds_U1']:.2f}"
                  f"{flag}")

    print(f"\nViability thresholds (first spread with the symptom in >= "
          f"{THRESHOLD_FRAC:.0%} of seeds):")
    for _, r in thr.iterrows():
        d = r["spread_first_death"]
        c = r["spread_full_collapse"]
        print(f"  {r['scenario']:<12} first firm death: "
              f"{'none in range' if not np.isfinite(d) else f'{d:g}':<14} "
              f"full collapse (U=1): {'none in range' if not np.isfinite(c) else f'{c:g}'}")

    s2 = thr[thr["scenario"] == "S2_headline"].iloc[0]
    s3 = thr[thr["scenario"] == "S3_benefit"].iloc[0]
    print("\nE2 verdict (does the benefit raise the viability threshold?):")
    for col, label in (("spread_first_death", "first firm death"),
                       ("spread_full_collapse", "full collapse")):
        a, b = s2[col], s3[col]
        if not np.isfinite(a) and not np.isfinite(b):
            verdict = "neither reaches it in the swept range"
        elif np.isfinite(a) and not np.isfinite(b):
            verdict = "RAISED beyond the swept range by the benefit"
        elif not np.isfinite(a) and np.isfinite(b):
            verdict = "LOWERED by the benefit"
        elif b > a:
            verdict = "RAISED by the benefit"
        elif b < a:
            verdict = "LOWERED by the benefit"
        else:
            verdict = "UNCHANGED"
        print(f"  {label:<18} rr=0: {a!s:<8} rr=0.5: {b!s:<8} -> {verdict}")

    fig_seed = trace[trace["seed"] == TRACE["figure_seed"]]
    print(f"\nDomino trace ({TRACE['scenario']}, spread={TRACE['spread']}, "
          f"seed={TRACE['figure_seed']}) - K of the weakest and strongest firm:")
    marks = [1, 50, 100, 200, 400, 800, 1500, int(fig_seed["step"].max())]
    for t in marks:
        r = fig_seed[fig_seed["step"] == t]
        if len(r) == 0:
            continue
        r = r.iloc[0]
        print(f"    t={t:<5} K_lowA={r['K_lowA']:7.2f}  K_highA={r['K_highA']:7.2f}  "
              f"K={r['Total_Capital']:7.2f}  U={r['Unemployment_Rate']:.3f}  "
              f"Y={r['Output']:7.2f}  dead={r['Dead_Firms']:.0f}")


def plot_aggregates(summary, path):
    """U, Y, K, Dead_Firms vs spread with inter-seed bands, one line per scenario."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    panels = [("Unemployment_Rate", "Unemployment U"), ("Output", "Output Y"),
              ("Total_Capital", "Capital K"), ("Dead_Firms", "Dead firms (K < 0.5)")]
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.3))
    for (metric, title), ax in zip(panels, axes):
        for name, block in summary.groupby("scenario"):
            b = block.sort_values("spread")
            line, = ax.plot(b["spread"], b[metric], marker="o", label=name)
            ax.fill_between(b["spread"], b[f"{metric}_lo"], b[f"{metric}_hi"],
                            alpha=0.15, color=line.get_color())
        ax.set_xlabel("productivity spread")
        ax.set_title(title, weight="bold")
        ax.legend(fontsize=8)
    fig.suptitle("Brief 10 - firm-heterogeneity viability probe: aggregates vs dispersion "
                 "(no reallocation channel)", weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_domino(trace, path, spec=TRACE):
    """The domino: the weak firm's capital goes first, then the strong firm's, then U."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    b = trace[trace["seed"] == spec["figure_seed"]].sort_values("step")
    fig, (axk, axu) = plt.subplots(1, 2, figsize=(13, 4.6))

    axk.plot(b["step"], b["K_lowA"], label=f"weakest firm (A={b['A_low'].iloc[0]:.2f})")
    axk.plot(b["step"], b["K_highA"], label=f"strongest firm (A={b['A_high'].iloc[0]:.2f})")
    axk.plot(b["step"], b["Total_Capital"] / 10.0, ls="--", lw=1, color="grey",
             label="aggregate K / 10")
    axk.set_xlabel("step")
    axk.set_ylabel("capital K")
    axk.set_title("The weak firm decapitalises first", weight="bold")
    axk.legend(fontsize=8)

    axu.plot(b["step"], b["Unemployment_Rate"], color="crimson", label="unemployment U")
    axu.set_xlabel("step")
    axu.set_ylabel("unemployment rate")
    ax2 = axu.twinx()
    ax2.plot(b["step"], b["Dead_Firms"], color="steelblue", label="dead firms")
    ax2.set_ylabel("dead firms (K < 0.5)")
    axu.set_title("...then the cascade: demand externality + destroyed demand share",
                  weight="bold")
    lines = axu.get_lines() + ax2.get_lines()
    axu.legend(lines, [l.get_label() for l in lines], fontsize=8, loc="center right")

    fig.suptitle(f"Brief 10 domino ({spec['scenario']}, spread={spec['spread']}, "
                 f"seed={spec['figure_seed']})", weight="bold")
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
    print(f"  wrote {name:32s} {df.shape[0]:>6d} rows")
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="results", help="output directory (default: results)")
    ap.add_argument("--workers", type=int, default=None,
                    help="process-pool size (default: all cores; 1 = serial)")
    ap.add_argument("--smoke", action="store_true",
                    help="tiny grid/steps end-to-end check (writes to results/smoke)")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    if args.smoke:
        out = os.path.join(out, "smoke")
    os.makedirs(out, exist_ok=True)

    spreads, seeds, steps = SPREADS, PANEL_SEEDS, STEPS
    if args.smoke:
        # End-to-end shape/plumbing check only - NOT a scientific result.  Reduced spreads,
        # seeds and steps mean the spread=0 byte-check against the 2000-step committed
        # panels WILL report FINDING; that is expected in smoke mode.
        spreads, seeds, steps = [0.0, 0.20], 3, 300
        print("SMOKE: reduced grid/steps; byte-check will not match committed panels.")

    print(f"Brief 10 - heterogeneity probe: {len(SCENARIOS)} scenarios x "
          f"{len(spreads)} spreads x {seeds} seeds x {steps} steps")
    panel = run_panel(args.workers, spreads=spreads, seeds=seeds, steps=steps)
    _write(panel, out, "ces_b10_panel.csv")

    summary = summarize(panel)
    _write(summary, out, "ces_b10_summary.csv")

    thr = thresholds(summary)
    _write(thr, out, "ces_b10_thresholds.csv")

    trace = run_trace(steps=steps)
    _write(trace, out, "ces_b10_trace.csv")

    check = byte_check(out, "ces_b10_panel.csv")
    _write(check, out, "ces_b10_nesting_check.csv")

    f1 = plot_aggregates(summary, os.path.join(out, "ces_b10_aggregates_spread.png"))
    f2 = plot_domino(trace, os.path.join(out, "ces_b10_domino_trace.png"))
    for f in (f1, f2):
        print(f"  wrote {os.path.basename(f)}")

    print_headline(summary, thr, trace)
    print(f"\nDone. brief-10 outputs written to {out}")


if __name__ == "__main__":
    main()

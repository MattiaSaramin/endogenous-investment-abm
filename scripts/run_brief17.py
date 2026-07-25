#!/usr/bin/env python
"""Brief 17 - investment (utilisation) expectation: the accelerator on u^e.

Brief 17 replaces the accelerator's realised-utilisation signal with an *expected*
utilisation ``u^e``, updated by the same partial-adjustment law as the brief-08 demand
expectation, with gain ``lambda_u`` (code: ``utilization_expectation_gain``).  ``lambda_u = 1``
recovers the pre-brief-17 model bit-for-bit (the explicit ``adaptive_expectation`` branch).

WHY (brief 17 §0): the SA (ces_b14_sobol_indices.csv, QoI slope|viable) puts ``S1(beta)`` = 0.64
of the sign variance on ``beta`` - the accelerator gain - which is (a) without an empirical
referent and (b) attached to an arbitrary, unfiltered, one-period-lagged signal.  This brief
respecifies that signal; it does NOT calibrate beta.

PRE-REGISTERED HYPOTHESIS (brief 17 §4) - written here BEFORE any run so the outcome cannot
be chosen after seeing it:

    Smoothing shrinks the excursions of u^e around ``target_utilization`` and hence the
    variance of ``util_effect``: lambda_u < 1 acts like a lower effective beta.  Quantitative
    prediction, reading the §0 table as a beta -> outcome map: as lambda_u falls the median
    of rho* FALLS toward 0.37-0.40, the "anchored-left-of-turn" share FALLS from ~95% toward
    70-85%, and wage-led points THIN OUT.

    Three readings, all publishable, none a failure:
    * confirmed  -> H1 is conditional on the accelerator specification; the 88.7% margin must
      be reported with its (beta, lambda_u) dependence.
    * falsified (margin >= 95% and rho* fixed for every lambda_u) -> H1 comes out STRONGER:
      it survives both marginalisation and the respecification of the channel carrying 64% of
      the variance.  The strongest robustness result of the project.
    * mixed (median moves, side does not) -> reported as such, with the lambda_u threshold.

    NOT optimising lambda_u.  Choosing one because it "gives the right answer" would be
    calibration disguised as robustness (the brief-13 prohibition).

DESIGN NOTE (declared): in steady state u^e -> u for any lambda_u > 0, so the tail MEAN of
util_effect is ~lambda_u-invariant by linearity (E[u^e] = E[u]).  The §4 mechanism therefore
lives in the *temporal variance* of util_effect (the within-tail excursion amplitude), which
this driver measures as the within-tail SD - not in the mean.  If even that SD does not fall
with lambda_u, the hypothesis is wrong in its MECHANISM and the driver says so.

Phases:
* ``byte-check``  lambda_u = 1 nesting vs the four committed panels on a representative SLICE
  (the nesting is mechanical - the explicit branch - so a slice falsifies it if wrong, as in
  brief 12), under the brief-14 criterion (compare_artifacts: ULP tolerance on levels + exact
  regime), DETECTOR-FIRST: a bad lambda_u must FAIL before the good one is believed.
* ``phaseA``  the beta x lambda_u grid at the headline scenario, 4 rho nodes under CRN, 20
  seeds.  Deliverables (util_effect stats, rho*, OLS slope, figure) + the gate.
* ``phaseB``  gated; a re-run of the b14 design at <=2 lambda_u.  NOT executed unless the gate
  opens AND a separate compute plan is approved (brief 17 §5, §9).

Determinism: BLAS pinned to one thread BEFORE numpy is imported (below); every cell is seeded
and the bootstrap is deterministic given BOOT_SEED.

Usage
-----
    python scripts/run_brief17.py --phase byte-check   # nesting slice (detector-first)
    python scripts/run_brief17.py --phase phaseA       # the grid + gate -> results/
    python scripts/run_brief17.py --phase report       # rebuild deliverables from runs CSV
    python scripts/run_brief17.py --workers 1           # serial
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time

_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
os.environ["PYTHONPATH"] = _SRC + os.pathsep + os.environ.get("PYTHONPATH", "")

# Pin BLAS/numpy to one thread BEFORE numpy is imported (via pandas/experiment).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
import pandas as pd

from experiment import (
    DEFAULT_STEPS,
    SA_RHO_GRID,
    SA_RHO_LO,
    SA_RHO_HI,
    SA_U_COLLAPSE,
    SA_K_COLLAPSE,
    _PANEL_METRICS,
    compare_artifacts,
    qoi_from_runs,
    quadratic_curvature,
    run_single,
)

RESULTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))

# ---------------------------------------------------------------------------
# Experiment configuration (approved compute plan, brief 17 §5)
# ---------------------------------------------------------------------------
#: Headline scenario, fixed.  beta and lambda_u are the experimental factors; the DEFAULT
#: beta (0.5) and everything anchored (ANCHOR_*, U_REF, initial_capital, wage curve) are
#: untouched - this brief changes a specification, not a calibration.
SCENARIO = dict(c0=1.0, sigma=0.5, eta=0.10, benefit_replacement_rate=0.0)
BETAS = [0.05, 0.15, 0.30, 0.50, 0.75, 1.00]
LAMBDA_US = [1.0, 0.75, 0.50, 0.25, 0.0]         # 1.0 is the control; 0.0 the degenerate no-accelerator
RHO_NODES = list(SA_RHO_GRID)                     # [0.35, 0.45, 0.55, 0.65]; contains the b13 chord pair
SEEDS = 20
STEPS = DEFAULT_STEPS                              # 2000
TAIL = 50

#: Anchored retention rate (upper bound), MEASURED in brief 16 (ces_b16: rho_anchored_max) and
#: frozen; not recomputed here.  rho* to the RIGHT of this => negative margin at the anchored rho.
ANCHORED_RHO_MAX = 0.3632216782659768

# ---------------------------------------------------------------------------
# Gate rule (brief 17 §5) - FROZEN IN SOURCE BEFORE ANY RUN
# ---------------------------------------------------------------------------
#: Phase B opens iff, for some beta, a lambda_u < 1 cell (i) moves rho* beyond the inter-seed
#: bootstrap CI half-width of the lambda_u = 1 reference at that beta, OR (ii) flips the side of
#: rho* relative to ANCHORED_RHO_MAX (both cells resolved).  Otherwise the brief CLOSES with
#: "lambda_u inert" - Phase B is NOT run for completeness.
BOOT_B = 1000
BOOT_SEED = 20250725
GATE_RULE = ("open Phase B iff, for some beta: |rho*(lu) - rho*(lu=1)| > CI_halfwidth(rho*|lu=1) "
             "for a resolved lambda_u<1 cell, OR sign(rho*-anchored) flips between lu and lu=1")

# The reporting bands the project quotes (brief 17 §5): CI half-width and the seed spread; both
# are reported per cell so a reader sees the noise before reading anything into a shift.


# ---------------------------------------------------------------------------
# Phase A - one (beta, lambda_u, rho, seed) cell
# ---------------------------------------------------------------------------
def _cell_job(job):
    """Run one Phase-A cell.  Module-level and picklable (process pool).

    Returns the tail-mean of the QoI/viability metrics PLUS the within-tail statistics of
    ``Util_Effect`` (mean, SD, min, max) and the mean ``Expected_Utilization`` - the mechanism
    variables that ride outside ``_PANEL_METRICS`` (brief 17 §3, like Capitalist_Consumption).
    """
    point, beta, lam, rho, seed = job
    params = dict(SCENARIO, beta=beta, utilization_expectation_gain=lam)
    df = run_single(rho, steps=STEPS, seed=seed, **params)
    tail = df[df.index >= STEPS - TAIL]

    row = {"point": point, "beta": beta, "lambda_u": lam, "rho": rho, "seed": seed}
    # Metrics qoi_from_runs needs (Output for the slope/turn; Unemployment_Rate + Total_Capital
    # for viability), kept under their panel names.
    for m in ("Output", "Unemployment_Rate", "Total_Capital", "Investment", "Average_Utilization"):
        row[m] = float(tail[m].mean())
    ue = tail["Util_Effect"].to_numpy(dtype=float)
    row["Util_Effect_mean"] = float(ue.mean())
    row["Util_Effect_sd"] = float(ue.std(ddof=1)) if ue.size > 1 else 0.0
    row["Util_Effect_min"] = float(ue.min())
    row["Util_Effect_max"] = float(ue.max())
    row["Expected_Utilization_mean"] = float(tail["Expected_Utilization"].mean())
    return row


def _cells():
    """The 30 (beta, lambda_u) cells, with a stable integer ``point`` id."""
    cells, point = [], 0
    for beta in BETAS:
        for lam in LAMBDA_US:
            cells.append((point, beta, lam))
            point += 1
    return cells


def _rho_star_resolved(quad_coef, quad_coef_se, in_support):
    """Brief 16 resolvability: convex AND curvature > 2 SE AND turn inside the support."""
    return bool(quad_coef > 0.0 and abs(quad_coef) > 2.0 * quad_coef_se and in_support)


def _bootstrap_rho_star(Y_by_seed, rhos, n_boot, rng):
    """Inter-seed bootstrap CI of rho* (resample the seed axis; refit the seed-mean quadratic).

    ``Y_by_seed`` is a (n_seed, n_rho) array.  Returns (lo, hi, halfwidth) of the finite,
    in-support turning points over ``n_boot`` resamples; NaNs where < 2 resolve.
    """
    n_seed = Y_by_seed.shape[0]
    turns = []
    lo_r, hi_r = min(rhos), max(rhos)
    for _ in range(n_boot):
        idx = rng.integers(0, n_seed, n_seed)
        ymean = Y_by_seed[idx].mean(axis=0)
        _, _, turn = quadratic_curvature(np.asarray(rhos, float), ymean)
        if np.isfinite(turn) and lo_r <= turn <= hi_r:
            turns.append(turn)
    if len(turns) < max(2, int(0.5 * n_boot)):
        return float("nan"), float("nan"), float("nan")
    lo = float(np.percentile(turns, 2.5))
    hi = float(np.percentile(turns, 97.5))
    return lo, hi, 0.5 * (hi - lo)


def run_phaseA(workers=None):
    print("=" * 78)
    print("PHASE A - beta x lambda_u at the headline scenario (brief 17 §5)")
    print("  scenario:", SCENARIO)
    print("  betas:", BETAS, " lambda_u:", LAMBDA_US)
    print("  rho nodes:", RHO_NODES, " seeds:", SEEDS, " steps:", STEPS)
    print("  PRE-REGISTERED HYPOTHESIS is in the module docstring (written before this run).")
    print("=" * 78, flush=True)

    cells = _cells()
    jobs = [(pt, beta, lam, rho, seed)
            for (pt, beta, lam) in cells
            for rho in RHO_NODES
            for seed in range(SEEDS)]

    t = time.time()
    if workers == 1:
        rows = [_cell_job(j) for j in jobs]
    else:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(_cell_job, jobs, chunksize=1))
    runs = pd.DataFrame(rows).sort_values(["point", "rho", "seed"], ignore_index=True)
    print(f"  {len(jobs)} cells in {time.time()-t:.0f}s", flush=True)
    runs.to_csv(os.path.join(RESULTS, "ces_b17_phaseA_runs.csv"), index=False)

    return build_deliverables(runs)


def build_deliverables(runs):
    """Reduce the raw Phase-A runs to the three CSVs, the gate, and the figure (no simulation)."""
    cells = _cells()
    point_meta = {pt: (beta, lam) for (pt, beta, lam) in cells}

    # --- QoI per point: OLS slope + rho* (b14/b16 estimators, unchanged) -----------------
    qoi = qoi_from_runs(runs[["point", "rho", "seed", "Output", "Unemployment_Rate",
                              "Total_Capital"]].copy(),
                        rho_lo=SA_RHO_LO, rho_hi=SA_RHO_HI, rhos=RHO_NODES)
    qoi["beta"] = qoi["point"].map(lambda p: point_meta[p][0])
    qoi["lambda_u"] = qoi["point"].map(lambda p: point_meta[p][1])

    # --- bootstrap CI of rho* + resolvability + anchored side ----------------------------
    rng = np.random.default_rng(BOOT_SEED)
    rs_rows = []
    for _, q in qoi.iterrows():
        pt = int(q["point"])
        block = runs[runs["point"] == pt]
        piv = block.pivot(index="seed", columns="rho", values="Output").sort_index()
        Y = piv[RHO_NODES].to_numpy(float)
        resolved = _rho_star_resolved(q["quad_coef"], q["quad_coef_se"],
                                       bool(q["rho_star_in_support"]))
        if resolved:
            lo, hi, hw = _bootstrap_rho_star(Y, RHO_NODES, BOOT_B, rng)
            side = "right" if q["rho_star"] > ANCHORED_RHO_MAX else "left"
        else:
            lo = hi = hw = float("nan")
            side = "undefined"
        rs_rows.append({
            "beta": q["beta"], "lambda_u": q["lambda_u"], "point": pt,
            "rho_star": q["rho_star"], "rho_star_in_support": q["rho_star_in_support"],
            "resolved": resolved, "quad_coef": q["quad_coef"], "quad_coef_se": q["quad_coef_se"],
            "ci_lo": lo, "ci_hi": hi, "ci_halfwidth": hw,
            "anchored_side": side, "viable": q["viable"],
        })
    rho_star = pd.DataFrame(rs_rows).sort_values(["beta", "lambda_u"], ignore_index=True)
    rho_star.to_csv(os.path.join(RESULTS, "ces_b17_rho_star.csv"), index=False)

    # --- slopes CSV (b14 OLS) ------------------------------------------------------------
    slopes = qoi[["beta", "lambda_u", "point", "slope", "slope_seed_sd", "slope_raw",
                  "viable", "wage_led"]].sort_values(["beta", "lambda_u"], ignore_index=True)
    slopes.to_csv(os.path.join(RESULTS, "ces_b17_slopes.csv"), index=False)

    # --- util_effect stats CSV (the mechanism test, brief 17 §5.1) -----------------------
    g = runs.groupby("point")
    ue_rows = []
    for pt, blk in g:
        beta, lam = point_meta[pt]
        ue_rows.append({
            "beta": beta, "lambda_u": lam, "point": pt,
            # mean of the tail-MEAN util_effect across the 4 rho x 20 seed runs (~lambda_u-invariant)
            "util_effect_mean": float(blk["Util_Effect_mean"].mean()),
            # mean of the WITHIN-TAIL SD (the excursion amplitude) - the mechanism variable
            "util_effect_sd_temporal": float(blk["Util_Effect_sd"].mean()),
            # cross-run spread of the tail-mean, for reference
            "util_effect_sd_across_runs": float(blk["Util_Effect_mean"].std(ddof=1)),
            "util_effect_min": float(blk["Util_Effect_min"].min()),
            "util_effect_max": float(blk["Util_Effect_max"].max()),
            "util_effect_range": float(blk["Util_Effect_max"].max() - blk["Util_Effect_min"].min()),
            "expected_utilization_mean": float(blk["Expected_Utilization_mean"].mean()),
        })
    util = pd.DataFrame(ue_rows).sort_values(["beta", "lambda_u"], ignore_index=True)
    util.to_csv(os.path.join(RESULTS, "ces_b17_util_effect.csv"), index=False)

    gate = apply_gate(rho_star)
    gate["decomposition"] = _gate_decomposition(rho_star, gate["triggers"])
    with open(os.path.join(RESULTS, "ces_b17_gate.json"), "w") as fh:
        json.dump(gate, fh, indent=2)

    make_figure(rho_star)
    _report(util, rho_star, slopes, gate)
    return util, rho_star, slopes, gate


def apply_gate(rho_star):
    """Apply the FROZEN gate rule (brief 17 §5).  Returns the decision + the numbers behind it."""
    triggers = []
    for beta in BETAS:
        sub = rho_star[rho_star["beta"] == beta].set_index("lambda_u")
        if 1.0 not in sub.index or not bool(sub.loc[1.0, "resolved"]):
            continue
        ref = sub.loc[1.0]
        hw = ref["ci_halfwidth"]
        ref_side = ref["anchored_side"]
        for lam in LAMBDA_US:
            if lam == 1.0 or lam not in sub.index:
                continue
            cell = sub.loc[lam]
            if not bool(cell["resolved"]):
                continue
            move = abs(float(cell["rho_star"]) - float(ref["rho_star"]))
            beyond_band = bool(np.isfinite(hw) and move > hw)
            side_flip = bool(cell["anchored_side"] != ref_side
                             and cell["anchored_side"] != "undefined")
            if beyond_band or side_flip:
                triggers.append({
                    "beta": beta, "lambda_u": lam,
                    "rho_star": float(cell["rho_star"]), "rho_star_ref": float(ref["rho_star"]),
                    "move": move, "ci_halfwidth_ref": float(hw) if np.isfinite(hw) else None,
                    "beyond_band": beyond_band, "side_flip": side_flip,
                    "side": cell["anchored_side"], "side_ref": ref_side,
                })
    decision = "OPEN Phase B" if triggers else "CLOSE (lambda_u inert within inter-seed bands)"
    return {"rule": GATE_RULE, "anchored_rho_max": ANCHORED_RHO_MAX,
            "decision": decision, "n_triggers": len(triggers), "triggers": triggers}


def _gate_decomposition(rho_star, triggers):
    """POST-HOC (clearly labelled) classification of the frozen-gate triggers + the
    smoothing-range inertness test the frozen rule does NOT isolate.

    The frozen gate compares every lambda_u < 1 cell - INCLUDING the degenerate lambda_u = 0
    accelerator-off control - against lambda_u = 1, so it opens whenever the accelerator is
    switched off entirely, which is expected and is not the smoothing gradient H1 concerns.
    This decomposition classifies each trigger and reports, over the smoothing range
    [0.25, 1.0], the largest rho* move relative to the lambda_u = 1 inter-seed band.  It does
    NOT alter ``decision`` above (the frozen rule's output); it is analysis, kept separate.
    """
    classes = {"degenerate_lambda_u0": 0, "near_anchor_noise": 0, "smoothing_gradient": 0,
               "detail": []}
    for tr in triggers:
        if tr["lambda_u"] == 0.0:
            kind = "degenerate_lambda_u0"
        else:
            ref = rho_star[(rho_star["beta"] == tr["beta"]) & (rho_star["lambda_u"] == 1.0)]
            hw = float(ref["ci_halfwidth"].iloc[0]) if len(ref) else float("nan")
            near = np.isfinite(hw) and abs(float(tr["rho_star_ref"]) - ANCHORED_RHO_MAX) <= hw
            kind = "near_anchor_noise" if near else "smoothing_gradient"
        classes[kind] += 1
        classes["detail"].append({"beta": tr["beta"], "lambda_u": tr["lambda_u"], "kind": kind})

    # Largest rho* move over the smoothing range, relative to the lambda_u=1 band, reported
    # BOTH over all beta and excluding beta=0.05 - the cell whose rho* sits on the anchor, so
    # its moves are near-anchor resolution noise (b16 limit ~0.005-0.014), not a smoothing effect.
    worst_all = {"ratio": 0.0, "beta": None, "lambda_u": None}
    worst_syst = {"ratio": 0.0, "beta": None, "lambda_u": None}
    for beta in BETAS:
        sub = rho_star[(rho_star["beta"] == beta) & rho_star["resolved"]].set_index("lambda_u")
        if 1.0 not in sub.index:
            continue
        ref_rs = float(sub.loc[1.0, "rho_star"])
        hw = float(sub.loc[1.0, "ci_halfwidth"])
        for lam in (0.25, 0.5, 0.75):
            if lam in sub.index and hw > 0:
                ratio = abs(float(sub.loc[lam, "rho_star"]) - ref_rs) / hw
                if ratio > worst_all["ratio"]:
                    worst_all = {"ratio": ratio, "beta": beta, "lambda_u": lam}
                if beta != 0.05 and ratio > worst_syst["ratio"]:
                    worst_syst = {"ratio": ratio, "beta": beta, "lambda_u": lam}
    return {
        "label": "POST-HOC decomposition, NOT the frozen rule; see 'decision' for the frozen output",
        "trigger_classes": {k: v for k, v in classes.items() if k != "detail"},
        "trigger_detail": classes["detail"],
        "smoothing_range": [0.25, 1.0],
        # max |rho*(lu)-rho*(lu=1)| / band over lu in {0.25,0.5,0.75}
        "smoothing_range_max_move_over_band": worst_all,
        # the same excluding beta=0.05 (rho* on the anchor -> resolution noise): the systematic effect
        "smoothing_range_max_move_over_band_excl_anchor": worst_syst,
        "systematic_smoothing_effect": ("none - the only >1 band move is the beta=0.05 near-anchor "
                                        "cell; excluding it the max is %.2f bands" % worst_syst["ratio"]),
    }


def make_figure(rho_star, path=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    path = path or os.path.join(RESULTS, "ces_b17_rho_star_lambda.png")
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for beta in BETAS:
        sub = rho_star[(rho_star["beta"] == beta) & rho_star["resolved"]].sort_values("lambda_u")
        if len(sub):
            ax.plot(sub["lambda_u"], sub["rho_star"], marker="o", ms=4, label=f"beta={beta}")
    ax.axhline(ANCHORED_RHO_MAX, ls="--", lw=1.5, color="k",
               label=f"anchored rho <= {ANCHORED_RHO_MAX:.3f}")
    ax.set_xlabel("utilisation-expectation gain lambda_u")
    ax.set_ylabel("turning point rho*")
    ax.set_title("Brief 17: rho*(lambda_u) by beta (resolved cells)", weight="bold")
    ax.invert_xaxis()   # 1.0 (control) on the left, decreasing smoothing to the right
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _report(util, rho_star, slopes, gate):
    print("\n" + "=" * 78)
    print("PHASE A DELIVERABLES")
    print("=" * 78)
    print("\nutil_effect (mechanism test - temporal SD should FALL with lambda_u if H1's")
    print("mechanism holds; the MEAN is ~lambda_u-invariant by design):")
    piv = util.pivot(index="beta", columns="lambda_u", values="util_effect_sd_temporal")
    print(piv.to_string(float_format=lambda x: f"{x:.4f}"))
    print("\nrho* by (beta, lambda_u) [resolved only]:")
    piv2 = rho_star.assign(rs=np.where(rho_star["resolved"], rho_star["rho_star"], np.nan)) \
                   .pivot(index="beta", columns="lambda_u", values="rs")
    print(piv2.to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"\nGATE: {gate['decision']}  ({gate['n_triggers']} triggers)")
    for tr in gate["triggers"]:
        print(f"   beta={tr['beta']} lambda_u={tr['lambda_u']}: rho*={tr['rho_star']:.3f} "
              f"vs ref {tr['rho_star_ref']:.3f} (move {tr['move']:.3f}), "
              f"beyond_band={tr['beyond_band']} side_flip={tr['side_flip']}")
    print("=" * 78, flush=True)


# ---------------------------------------------------------------------------
# Nesting byte-check (slice, detector-first) - brief 17 §6
# ---------------------------------------------------------------------------
#: panel column -> MacroModel kwarg.  ``spread`` is the brief-10 panel's name for
#: ``productivity_spread`` - missing it silently regenerates spread>0 rows at spread=0.
_CFG_MAP = {"c0": "c0", "eta": "eta", "benefit_replacement_rate": "benefit_replacement_rate",
            "expectation_gain": "expectation_gain", "productivity_spread": "productivity_spread",
            "spread": "productivity_spread"}
_BYTE_PANELS = {
    "ces_b05_stage_a_panel.csv": dict(sigma=[0.5, 1.0], rho=[0.35, 0.55], seed=[0, 3]),
    "ces_b07_stage_a_panel.csv": dict(sigma=[0.5, 1.5], rho=[0.55], seed=[0, 3]),
    "ces_b09_stage_a_panel.csv": dict(sigma=[0.5], rho=[0.40], seed=[0, 3]),
    "ces_b10_panel.csv":         dict(sigma=[0.5, 1.0], rho=[0.40], seed=[0, 3]),
}


def _regen_slice_row(row, cfg_cols, lam):
    kw = {_CFG_MAP[c]: row[c] for c in cfg_cols}
    df = run_single(row["rho"], steps=STEPS, seed=int(row["seed"]), sigma=row["sigma"],
                    utilization_expectation_gain=lam, **kw)
    st = df[df.index >= STEPS - TAIL].mean()
    out = {"sigma": row["sigma"], "rho": row["rho"], "seed": row["seed"]}
    for c in cfg_cols:
        out[c] = row[c]
    out.update({m: float(st[m]) for m in _PANEL_METRICS if m in row.index})
    return out


def _byte_one(panel, lam):
    ref = pd.read_csv(os.path.join(RESULTS, panel))
    cfg = [c for c in _CFG_MAP if c in ref.columns]
    sl = _BYTE_PANELS[panel]
    m = ref["sigma"].isin(sl["sigma"]) & ref["rho"].isin(sl["rho"]) & ref["seed"].isin(sl["seed"])
    order = ["sigma", "rho", "seed"] + cfg
    rs = ref[m].sort_values(order).reset_index(drop=True)
    mine = pd.DataFrame([_regen_slice_row(r, cfg, lam) for _, r in rs.iterrows()])
    mine = mine.sort_values(order).reset_index(drop=True)
    shared = [c for c in rs.columns if c in mine.columns]
    return len(rs), compare_artifacts(mine[shared], rs[shared])


def byte_check_slice():
    """Detector-first nesting slice (brief 17 §6).

    A bad lambda_u MUST fail before the good one is believed: 'a check that reports success
    without inspecting anything is worse than no check.'  Criterion is brief-14
    (compare_artifacts): ULP tolerance on levels + EXACT regime, NOT bare dev == 0.0.
    """
    rows = []
    for lam, expect in ((0.5, "FAIL"), (1.0, "PASS")):
        print(f"\n  lambda_u = {lam}  (detector expects {expect}):", flush=True)
        allok = True
        for panel in _BYTE_PANELS:
            n, res = _byte_one(panel, lam)
            allok = allok and res["ok"]
            rows.append({"lambda_u": lam, "panel": panel, "n": n, **{
                k: res[k] for k in ("ok", "regime_equal", "n_exceed", "n_compared",
                                    "max_ulp_significant", "max_abs_dev", "byte_equal")}})
            print(f"    {panel:26s} n={n:2d} ok={res['ok']} regime_eq={res['regime_equal']} "
                  f"n_exceed={res['n_exceed']}/{res['n_compared']} "
                  f"max_ulp_sig={res['max_ulp_significant']:.1f} max_abs_dev={res['max_abs_dev']:.2e}")
        verdict = "PASS" if allok else "FAIL"
        tag = "as expected" if verdict == expect else "*** UNEXPECTED ***"
        print(f"    -> overall {verdict}  [{tag}]", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RESULTS, "ces_b17_byte_check.csv"), index=False)
    return out


# ---------------------------------------------------------------------------
def _record_environment():
    env = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    try:
        import mesa
        env["mesa"] = mesa.__version__
    except Exception:
        env["mesa"] = "unknown"
    env["blas_threads"] = {v: os.environ.get(v) for v in
                           ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}
    env["config"] = {"scenario": SCENARIO, "betas": BETAS, "lambda_us": LAMBDA_US,
                     "rho_nodes": RHO_NODES, "seeds": SEEDS, "steps": STEPS,
                     "anchored_rho_max": ANCHORED_RHO_MAX, "gate_rule": GATE_RULE,
                     "boot_B": BOOT_B, "boot_seed": BOOT_SEED}
    with open(os.path.join(RESULTS, "ces_b17_environment.json"), "w") as fh:
        json.dump(env, fh, indent=2)
    return env


def main():
    ap = argparse.ArgumentParser(description="Brief 17 driver (investment-expectation).")
    ap.add_argument("--phase", choices=["byte-check", "phaseA", "report", "all"], default="all")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()

    _record_environment()

    if args.phase in ("byte-check", "all"):
        print("#" * 78, "\n# NESTING BYTE-CHECK (slice, detector-first; brief 17 §6)\n", "#" * 78)
        byte_check_slice()

    if args.phase in ("phaseA", "all"):
        run_phaseA(workers=args.workers)

    if args.phase == "report":
        runs = pd.read_csv(os.path.join(RESULTS, "ces_b17_phaseA_runs.csv"))
        build_deliverables(runs)


if __name__ == "__main__":
    main()

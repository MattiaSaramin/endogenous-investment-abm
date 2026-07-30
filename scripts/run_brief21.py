#!/usr/bin/env python
"""Brief 21 — the price probe: is H2 an artefact of the numeraire?  Reproducibly.

PROBE, not a feature.  ``enable_prices`` is default False and does not enter the defaults or
the global SA.  This driver measures what survives of H2 ("wage flexibility does not
self-correct unemployment") once the real wage is constant by construction, via the
normal-cost price ``P_t = w_t/w_bar`` (see the PRICE PROBE block in model.py).  The
treatment is ``enable_prices`` under COMMON RANDOM NUMBERS: at a given seed the price
arithmetic changes no RNG draw, so enable_prices False vs True share an identical network,
hiring order and shuffle — the difference is purely the price channel.

================================================================================
PRE-REGISTERED HYPOTHESES (brief 21 §4) — written here BEFORE any run, so the outcome
cannot be back-fitted (the same discipline as b13's frozen pruning rule and b17's frozen
HYPOTHESIS).  P is the normalised wage, so the real wage w/P == w_bar is constant in U and
in eta; the ONLY real channel left is the revaluation of the nominal wealth stock a_h/P — a
Pigou effect, which is STABILISING, the opposite of the H2 mechanism.

  P1 — NESTING.  enable_prices=True at eta=0 is byte-identical to main.  At eta=0 the wage
       short-circuits to w_bar so P=1 exactly; if it is not byte-identical the ledger is
       wrong.  STOP and report; do not adjust the numbers.

  P2 — sigma*(eta) becomes eta-INVARIANT.  In main it rises 0.654 -> 0.740 with eta.  With
       the probe the real wage does not depend on eta, so the only residual eta-dependence
       can pass through the Pigou channel.  Expectation: flat within the inter-seed bands.

  P3 — the c0=2.0 COLLAPSE shrinks or disappears.  The b07 mechanism is a wage-employment
       oscillation that erodes capital each cycle; with the real wage constant that
       oscillation has no real effect, and the Pigou channel is stabilising.

  P4 — H1 does NOT move.  rho* and the sign of the margin at the anchored rho (0.3632) stay
       within the bands.  If H1 moves, the probe has touched something it should not have.

P3 is the real, useful bet: if it comes true, wage flexibility WITH the probe self-corrects
— H2 is not merely an artefact, it is REVERSED by the numeraire, and it would be the first
stabilisation hypothesis CONFIRMED after four consecutive falsifications (lambda_e b08, rr
b09-E3, rr b10-E2, extended government), and the first through a DIFFERENT channel (real
balances, not the wage-employment loop).

TWO-TIME FORM ON H2 (b17 discipline, brief 21 §4).  The CONCLUSION of H2 ("no
self-correction") and its MECHANISM ("an oscillation that erodes capital") are TWO SEPARATE
objects.  The probe can kill the mechanism while leaving the conclusion standing, or reverse
both.  The report never writes "H2 falls" or "H2 holds" without saying WHICH of the two.

================================================================================
GATE (brief 21 §5) — declared in source BEFORE the runs.  The b17 lesson: the movement test
must NOT include the degenerate control (enable_prices=False); that is the REFERENCE, not an
observation.

  GATE_P1: n_exceed == 0 under the 8-ULP + atol criterion AND regime_equal, on the shared
           level columns of ces_b05_stage_a_panel.  The absolute deviation is reported
           ALONGSIDE ok (the 8-ULP pin is a declared debt, §9/b17 — regime-first).

  GATE_P2: prices ON, sigma*(eta) is "eta-invariant" iff sigma*(0.15) and sigma*(0) agree
           within the union of their bootstrap CIs.  prices OFF must reproduce the b07 rise
           (a positive control on the same machine); if OFF is also flat the estimator, not
           the probe, is doing the flattening and P2 is INCONCLUSIVE.

  GATE_P3: prices ON, the collapse "shrinks" iff the number of (sigma,rho) cells with ANY
           seed collapse at c0=2.0 is strictly LESS than prices OFF; it "disappears" iff that
           count -> 0.  Reported per eta and pooled.

  GATE_P4: H1 "unmoved" iff, at c0=1.0, rho*(sigma) and sign(dY/drho) per sigma are unchanged
           prices ON vs OFF within the inter-seed bands (rho* CI half-width; slope sign).

Determinism: BLAS pinned to one thread BEFORE numpy is imported (below); every cell is
seeded and shares no state, so the pooling cannot move a result.  Environment recorded in
results/ces_b21_environment.json.

Usage
-----
    python scripts/run_brief21.py                 # all phases -> results/, threads pinned
    python scripts/run_brief21.py --phase byte-check
    python scripts/run_brief21.py --phase panel
    python scripts/run_brief21.py --phase report  # reads the committed panel, no simulation
    python scripts/run_brief21.py --seeds 10 --workers 8
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys

# Make ``src/`` importable here AND in the process-pool children (Windows spawns fresh
# interpreters that only inherit sys.path via the environment).
_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
os.environ["PYTHONPATH"] = _SRC + os.pathsep + os.environ.get("PYTHONPATH", "")

# Pin BLAS/numpy to one thread BEFORE numpy is imported (via pandas/experiment), so the
# reduction order in the derived tables is deterministic and machine-independent, and the
# workers do not each spawn a BLAS pool and oversubscribe the cores.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
import pandas as pd

from experiment import (
    SIGMA_SWEEP_B05,
    RHO_SWEEP_B05,
    DEFAULT_STEPS,
    bootstrap_sigma_star,
    cells_from_panel,
    compare_artifacts,
    common_viable_support,
    quadratic_curvature,
    run_grid_panels,
    slopes_by_sigma,
    _PANEL_METRICS,
)

# --- experiment configuration (frozen) ------------------------------------
ETAS = [0.0, 0.05, 0.10, 0.15]
C0S = [1.0, 2.0]
PRICES = [False, True]                 # the treatment; CRN across it
SIGMAS = SIGMA_SWEEP_B05               # 11 values
RHOS = RHO_SWEEP_B05                   # 7 values [0.35 .. 0.65]
STEPS = DEFAULT_STEPS                  # 2000, same convergence device as b05/b07

#: The anchored retention (I/Y anchor, brief 11/17) — H1's reference point (P4).
ANCHORED_RHO = 0.3632

#: The committed numeraire=1 panel the eta=0 slices must reproduce byte-for-byte (main).
B05_PANEL = "ces_b05_stage_a_panel.csv"

#: Byte-check slice (detector-first): small and cheap, like b17's slice.
BYTE_SIGMAS = [0.5, 1.0]
BYTE_SEEDS = 5

# Pre-registered text (kept as data so it is serialised into the environment file).
HYPOTHESES = {
    "P1": "enable_prices=True at eta=0 is byte-identical to main (ces_b05).",
    "P2": "sigma*(eta) becomes eta-invariant with the probe (main rises 0.654->0.740).",
    "P3": "the c0=2.0 collapse shrinks or disappears with the probe (Pigou is stabilising).",
    "P4": "H1 (rho*, sign of margin at the anchored rho 0.3632) does not move.",
}
GATE = {
    "P1": "n_exceed==0 (8-ULP+atol) AND regime_equal on shared level cols; report abs dev too.",
    "P2": "prices ON eta-invariant iff sigma*(0.15) and sigma*(0) CIs overlap; prices OFF must "
          "reproduce the b07 rise as a positive control (else INCONCLUSIVE).",
    "P3": "prices ON shrinks iff #cells with any seed collapse (c0=2.0) strictly < prices OFF; "
          "disappears iff -> 0.",
    "P4": "unmoved iff rho*(sigma) and sign(dY/drho) per sigma unchanged ON vs OFF within bands.",
}


# ======================================================================
# helpers
# ======================================================================

def _write(df, out, name):
    path = os.path.join(out, name)
    df.to_csv(path, index=False)
    print(f"  wrote {name:38s} {df.shape[0]:>6d} rows")
    return df


def _tag(panel, c0, eta, ep):
    """Attach the config identity to a per-seed panel."""
    return panel.assign(c0=c0, eta=eta, enable_prices=bool(ep),
                        prices=("on" if ep else "off"))


def _metric_cols(panel):
    """sigma,rho,seed + numeric metrics only (drop the config-identity columns)."""
    drop = {"c0", "eta", "enable_prices", "prices"}
    return [c for c in panel.columns if c not in drop]


# ======================================================================
# Phase: nesting byte-check (detector-first; brief 21 §2)
# ======================================================================

def _byte_slice(enable_prices, eta, out, workers):
    """A small (c0 x sigma x rho x seed) slice at one (enable_prices, eta), tagged by c0."""
    configs = [{"c0": c0, "eta": eta, "enable_prices": enable_prices} for c0 in C0S]
    panels = run_grid_panels(configs, sigmas=BYTE_SIGMAS, rhos=RHOS, seeds=BYTE_SEEDS,
                             steps=STEPS, workers=workers, metrics=list(_PANEL_METRICS))
    return pd.concat([p.assign(c0=c0) for c0, p in zip(C0S, panels)], ignore_index=True)


def _compare_to_b05(mine, out):
    """Align ``mine`` to the committed b05 panel on (c0,sigma,rho,seed) and compare levels.

    The comparison is artifact-vs-b05 on the SHARED numeric columns (b05 predates the
    wage-curve pair, so Wage_Rate/Wage_Floor_Binding/Price are simply not compared).
    """
    ref = pd.read_csv(os.path.join(out, B05_PANEL))
    key = ["c0", "sigma", "rho", "seed"]
    shared = [c for c in ref.columns if c in mine.columns and c not in key]
    a = mine.sort_values(key).reset_index(drop=True)
    b = ref.merge(a[key], on=key, how="right").sort_values(key).reset_index(drop=True)
    return compare_artifacts(a[shared].reset_index(drop=True),
                             b[shared].reset_index(drop=True))


def _report_byte(label, res, expect_fire=False):
    verdict = "FIRES" if not res["ok"] else "PASS"
    flag = "OK" if (res["ok"] != expect_fire) else "UNEXPECTED"
    print(f"  {label}")
    print(f"    -> {verdict:5s}  regime_equal={res['regime_equal']}  "
          f"n_exceed={res['n_exceed']}/{res['n_compared']}  "
          f"max_ulp_sig={res['max_ulp_significant']:.2f}  "
          f"max_abs_dev={res['max_abs_dev']:.2e}  "
          f"(retired byte_equal={res['byte_equal']})  [{flag}]")
    return res


def byte_check(out, workers):
    print("#" * 78)
    print("# NESTING BYTE-CHECK (detector-first; brief 21 §2) — regime-first + abs dev")
    print("#" * 78)
    rows = []

    # detector self-test FIRST (b17 discipline): the check must FIRE on a model that really
    # differs — enable_prices=True at eta=0.10 (P!=1, a genuinely different economy) vs main.
    bad = _compare_to_b05(_byte_slice(True, 0.10, out, workers), out)
    _report_byte("detector self-test: enable_prices=True eta=0.10 (P!=1) vs main -- MUST FIRE",
                 bad, expect_fire=True)
    rows.append({"check": "detector_selftest_eta0.10", **bad})

    # (a) enable_prices=False == main
    off = _compare_to_b05(_byte_slice(False, 0.0, out, workers), out)
    _report_byte("check (a): enable_prices=False eta=0 vs main (ces_b05)", off)
    rows.append({"check": "a_disabled_eta0", **off})

    # (b) enable_prices=True, eta=0 == main -- THE DETECTOR (brief 21 §2)
    on0 = _compare_to_b05(_byte_slice(True, 0.0, out, workers), out)
    _report_byte("check (b): enable_prices=True  eta=0 vs main (ces_b05)  [P1 detector]", on0)
    rows.append({"check": "b_enabled_eta0_P1", **on0})

    _write(pd.DataFrame(rows), out, "ces_b21_byte_check.csv")

    p1_ok = on0["ok"]
    print(f"\n  P1 verdict: {'PASS (byte-identical)' if p1_ok else 'FINDING -- STOP, ledger wrong'}"
          f"   [regime_equal={on0['regime_equal']}, n_exceed={on0['n_exceed']}, "
          f"max_abs_dev={on0['max_abs_dev']:.2e}]")
    return p1_ok, rows


# ======================================================================
# Phase: the panel (the treatment grid, CRN)
# ======================================================================

def panel(out, workers, seeds):
    print("#" * 78)
    print(f"# PANEL: eta x c0 x enable_prices x sigma x rho, {seeds} seeds, CRN")
    print("#" * 78)
    configs, ids = [], []
    for c0 in C0S:
        for eta in ETAS:
            for ep in PRICES:
                configs.append({"c0": c0, "eta": eta, "enable_prices": ep})
                ids.append((c0, eta, ep))
    metrics = list(_PANEL_METRICS) + ["Price"]
    panels = run_grid_panels(configs, sigmas=SIGMAS, rhos=RHOS, seeds=seeds,
                             steps=STEPS, workers=workers, metrics=metrics)
    frames = [_tag(p, c0, eta, ep) for (c0, eta, ep), p in zip(ids, panels)]
    big = pd.concat(frames, ignore_index=True)
    _write(big, out, "ces_b21_stage_a_panel.csv")
    return big


# ======================================================================
# Phase: report (P2, P3, P4 derived from the committed panel; no simulation)
# ======================================================================

def _sub_cells(big, c0, eta, ep):
    m = big[(big["c0"] == c0) & (big["eta"] == eta) & (big["prices"] == ep)]
    return cells_from_panel(m[_metric_cols(m)].copy())


def _sub_panel(big, c0, eta, ep):
    m = big[(big["c0"] == c0) & (big["eta"] == eta) & (big["prices"] == ep)]
    return m[_metric_cols(m)].copy()


def report_P2(big, out):
    """sigma*(eta), c0=1.0, prices off vs on, on a support common to every (eta, prices)."""
    print("\n--- P2: sigma*(eta), c0=1.0 (prices OFF is the control; ON is the test) ---")
    c0 = 1.0
    supports = {}
    for eta in ETAS:
        for ep in ("off", "on"):
            supports[(eta, ep)] = common_viable_support(_sub_cells(big, c0, eta, ep))
    common = [r for r in RHOS if all(r in supports[k] for k in supports)]
    print(f"  common support across all (eta,prices) at c0=1.0: {common}")

    rows = []
    for ep in ("off", "on"):
        for eta in ETAS:
            p = _sub_panel(big, c0, eta, ep)
            bs = bootstrap_sigma_star(p, common, column="Output")
            rows.append({"c0": c0, "prices": ep, "eta": eta,
                         "sigma_star": bs["sigma_star"], "ci_lo": bs["ci_lo"],
                         "ci_hi": bs["ci_hi"], "frac_undefined": bs["frac_undefined"],
                         "n_crossings": bs["n_crossings"]})
    df = pd.DataFrame(rows)
    _write(df, out, "ces_b21_sigma_star_eta.csv")
    for ep in ("off", "on"):
        print(f"  prices {ep.upper()}:")
        for _, r in df[df["prices"] == ep].iterrows():
            print(f"    eta={r['eta']:<4}: sigma*={r['sigma_star']:.4f} "
                  f"[{r['ci_lo']:.4f}, {r['ci_hi']:.4f}]  frac_undef={r['frac_undefined']:.3f}")
    return df


def report_P3(big, out):
    """The c0=2.0 collapse map, prices off vs on: count cells with any/full collapse."""
    print("\n--- P3: c0=2.0 collapse (prices OFF is the control; ON is the test) ---")
    c0 = 2.0
    rows = []
    for ep in ("off", "on"):
        for eta in ETAS:
            cells = _sub_cells(big, c0, eta, ep)
            n_any = int((cells["frac_seeds_collapsed"] > 0.0).sum())
            n_full = int(cells["collapsed"].sum())
            rows.append({"c0": c0, "prices": ep, "eta": eta,
                         "n_cells": int(len(cells)),
                         "n_any_collapse": n_any, "n_full_collapse": n_full,
                         "mean_frac_collapsed": float(cells["frac_seeds_collapsed"].mean())})
    df = pd.DataFrame(rows)
    _write(df, out, "ces_b21_collapse_c0_2.csv")
    for ep in ("off", "on"):
        sub = df[df["prices"] == ep]
        tot_any = int(sub["n_any_collapse"].sum())
        tot_full = int(sub["n_full_collapse"].sum())
        print(f"  prices {ep.upper()}: pooled over eta -> any-collapse cells={tot_any}, "
              f"full-collapse cells={tot_full}")
        for _, r in sub.iterrows():
            print(f"    eta={r['eta']:<4}: any_collapse={r['n_any_collapse']:>2d}/{r['n_cells']}  "
                  f"full={r['n_full_collapse']:>2d}  mean_frac={r['mean_frac_collapsed']:.3f}")
    return df


def report_P4(big, out):
    """H1 at c0=1.0: rho*(sigma) and sign(dY/drho) per sigma, prices off vs on."""
    print("\n--- P4: H1 at c0=1.0 (rho* and sign dY/drho), prices off vs on ---")
    c0 = 1.0
    rows = []
    for ep in ("off", "on"):
        # pool all eta? No: H1 is at the model defaults (eta as its own dimension). Use eta=0.10
        # (the headline scenario of b07/b17) so it is comparable to the H1 margin work.
        eta = 0.10
        cells = _sub_cells(big, c0, eta, ep)
        support = common_viable_support(cells)
        slopes = slopes_by_sigma(cells, support, column="Y")
        for _, s in slopes.iterrows():
            sigma = s["sigma"]
            # rho* from the quadratic on the seed-mean Y(rho), viable rho only for this sigma.
            b = cells[(cells["sigma"] == sigma) & (~cells["collapsed"])].sort_values("rho")
            if len(b) >= 3:
                _, _, turn = quadratic_curvature(b["rho"].to_numpy(float), b["Y"].to_numpy(float))
            else:
                turn = float("nan")
            in_sup = bool(np.isfinite(turn) and min(RHOS) <= turn <= max(RHOS))
            rows.append({"c0": c0, "eta": eta, "prices": ep, "sigma": sigma,
                         "dY_drho": s["dY_drho"], "slope_sign": int(np.sign(s["dY_drho"]))
                         if np.isfinite(s["dY_drho"]) else 0,
                         "rho_star": turn, "rho_star_in_support": in_sup,
                         "anchored_left_of_star": bool(np.isfinite(turn) and ANCHORED_RHO < turn)})
    df = pd.DataFrame(rows)
    _write(df, out, "ces_b21_h1_rho_star.csv")
    for ep in ("off", "on"):
        sub = df[df["prices"] == ep].sort_values("sigma")
        n_wl = int((sub["slope_sign"] < 0).sum())
        n_left = int(sub["anchored_left_of_star"].sum())
        print(f"  prices {ep.upper()} (eta=0.10): wage-led sigmas (dY/drho<0)={n_wl}/{len(sub)}, "
              f"anchored rho left-of-rho* in {n_left}/{len(sub)} sigmas")
    return df


def report_pigou(big, out):
    """The single real channel (brief 21 §1.1): c0=1.0 real levels off vs on, per eta.

    With the firm's FOC at the REAL wage, eta cannot touch the real allocation through the
    labour market; the only channel left is the Pigou revaluation of household wealth (lower
    P at higher eta raises real wealth -> more demand).  This table shows its size and sign:
    the on-minus-off difference in U/Y/K is the Pigou effect, isolated.
    """
    print("\n--- Pigou channel: c0=1.0 real levels, prices off vs on, per eta (§1.1) ---")
    c0 = 1.0
    rows = []
    for eta in ETAS:
        r = {"c0": c0, "eta": eta}
        for ep in ("off", "on"):
            m = big[(big["c0"] == c0) & (big["eta"] == eta) & (big["prices"] == ep)]
            for col, key in (("Unemployment_Rate", "U"), ("Output", "Y"),
                             ("Total_Capital", "K"), ("Consumption", "C"),
                             ("Wage_Rate", "w"), ("Price", "P")):
                r[f"{key}_{ep}"] = float(m[col].mean())
        r["dU_on_minus_off"] = r["U_on"] - r["U_off"]
        r["dY_on_minus_off"] = r["Y_on"] - r["Y_off"]
        rows.append(r)
    df = pd.DataFrame(rows)
    _write(df, out, "ces_b21_pigou_c0_1.csv")
    for _, r in df.iterrows():
        print(f"  eta={r['eta']:<4}: U off->on {r['U_off']:.3f}->{r['U_on']:.3f} "
              f"(d={r['dU_on_minus_off']:+.3f})  Y {r['Y_off']:.1f}->{r['Y_on']:.1f} "
              f"(d={r['dY_on_minus_off']:+.1f})  P_on={r['P_on']:.3f}")
    return df


def report(out):
    print("#" * 78)
    print("# REPORT (P2/P3/P4 from the committed panel; no simulation)")
    print("#" * 78)
    big = pd.read_csv(os.path.join(out, "ces_b21_stage_a_panel.csv"))
    p2 = report_P2(big, out)
    p3 = report_P3(big, out)
    p4 = report_P4(big, out)
    report_pigou(big, out)
    _figures(p2, p3, out)
    return p2, p3, p4


def _figures(p2, p3, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # P2 figure: sigma*(eta) off vs on at c0=1.0
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for ep, style in (("off", dict(marker="o", ls="-")), ("on", dict(marker="s", ls="--"))):
        b = p2[p2["prices"] == ep].sort_values("eta")
        line, = ax.plot(b["eta"], b["sigma_star"], label=f"prices {ep}", **style)
        ax.fill_between(b["eta"], b["ci_lo"], b["ci_hi"], alpha=0.15, color=line.get_color())
    ax.axhspan(0.40, 0.60, color="grey", alpha=0.15, label="empirical sigma 0.40-0.60")
    ax.set_xlabel("wage-curve elasticity  eta")
    ax.set_ylabel("sign frontier  sigma*")
    ax.set_title("P2: does the price probe flatten sigma*(eta)?  (c0=1.0)", weight="bold")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "ces_b21_sigma_star_eta.png"), dpi=150)
    plt.close(fig)
    print("  wrote ces_b21_sigma_star_eta.png")

    # P3 figure: any-collapse cell count vs eta, off vs on, c0=2.0
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for ep, style in (("off", dict(marker="o", ls="-")), ("on", dict(marker="s", ls="--"))):
        b = p3[p3["prices"] == ep].sort_values("eta")
        ax.plot(b["eta"], b["n_any_collapse"], label=f"prices {ep}", **style)
    ax.set_xlabel("wage-curve elasticity  eta")
    ax.set_ylabel("(sigma,rho) cells with any seed collapse")
    ax.set_title("P3: does the price probe shrink the c0=2.0 collapse?", weight="bold")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "ces_b21_collapse_c0_2.png"), dpi=150)
    plt.close(fig)
    print("  wrote ces_b21_collapse_c0_2.png")


# ======================================================================
# environment + driver
# ======================================================================

def _record_environment(out, seeds):
    # Record the seed count actually used for the panel, if the panel already exists — so a
    # report-only re-run (which may default --seeds) cannot overwrite the environment with a
    # seed count the committed panel was not run at.
    panel_path = os.path.join(out, "ces_b21_stage_a_panel.csv")
    if os.path.exists(panel_path):
        try:
            seeds = int(pd.read_csv(panel_path, usecols=["seed"])["seed"].nunique())
        except Exception:
            pass
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
    env["config"] = {"etas": ETAS, "c0s": C0S, "prices": PRICES, "sigmas": SIGMAS,
                     "rhos": RHOS, "steps": STEPS, "seeds": seeds,
                     "anchored_rho": ANCHORED_RHO, "byte_sigmas": BYTE_SIGMAS,
                     "byte_seeds": BYTE_SEEDS}
    env["hypotheses"] = HYPOTHESES
    env["gate"] = GATE
    with open(os.path.join(out, "ces_b21_environment.json"), "w") as fh:
        json.dump(env, fh, indent=2)
    return env


def main():
    ap = argparse.ArgumentParser(description="Brief 21 driver (price probe).")
    ap.add_argument("--out", default="results")
    ap.add_argument("--phase", choices=["byte-check", "panel", "report", "all"], default="all")
    ap.add_argument("--seeds", type=int, default=15,
                    help="seeds per config, both arms, CRN (default 15)")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    _record_environment(out, args.seeds)

    if args.phase in ("byte-check", "all"):
        p1_ok, _ = byte_check(out, args.workers)
        if args.phase == "all" and not p1_ok:
            print("\nSTOP: P1 (byte nesting) is a FINDING. The ledger is wrong somewhere; "
                  "do not run the panel or adjust the numbers (brief 21 §4, P1).")
            sys.exit(2)

    if args.phase in ("panel", "all"):
        panel(out, args.workers, args.seeds)

    if args.phase in ("report", "all"):
        report(out)
        print(f"\nDone. brief-21 outputs written to {out}")


if __name__ == "__main__":
    main()

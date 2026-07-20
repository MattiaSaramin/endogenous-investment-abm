#!/usr/bin/env python
"""Regenerate the brief-13 GLOBAL SENSITIVITY ANALYSIS (roadmap point 5).

The headline of this project is not a level but a SIGN: ``dY/drho < 0`` (wage-led) in the
empirical range of sigma.  A sensitivity analysis of levels would answer the wrong
question very precisely.  This driver therefore asks:

1. over the empirically defensible parameter space, what fraction is wage-led -
   ``P(dY/drho < 0)``?  A statement that does not depend on one cell, unlike a single
   ``sigma*``;
2. which parameters govern the variance of that sign (Sobol indices on the slope);
3. which parameters build the fragile region (viability as a QoI in its own right -
   after three falsified stabilisations, "what governs the collapse" is a research
   question, not a diagnostic).

Two open project questions fall out as by-products, with no new mechanism:

* **point 10-bis** - ``beta`` is the accelerator gain on ``utilization_last_period``, so
  ``beta -> 0`` is investment that ignores the utilisation signal.  If the instability
  survives ``beta ~ 0``, the capital-erosion channel is not governed by how fast
  investment reacts;
* **the Kaleckian direction** - brief 11 showed ``Pi - I = C - W`` is a tautology here
  and cannot settle causation.  Sweeping ``capitalist_mpc`` with the
  ``Capitalist_Consumption`` reporter is the INTERVENTION the identity could not provide.

Design (brief 13 §3-§4)
-----------------------
``retention_ratio`` is the TREATMENT, not a swept parameter: every design point is run at
``rho_lo = 0.35`` and ``rho_hi = 0.55`` under **common random numbers** (same seeds at
both, difference taken per seed, then averaged).  Without CRN the difference is noise on
noise and the Sobol indices would decompose the variance of the seed draw.

Two levels: a Morris screening (k = 17 including ``max_tax``, r = 20) to separate
influential from irrelevant, then Sobol on the survivors with bootstrap CIs.  **The
pruning rule is declared in :data:`MORRIS_KEEP_RULE` BEFORE the screening runs** - no
post-hoc selection.

Collapse is handled, not dodged: non-viable points have no defined slope.  Viability is
analysed on ALL points; the slope is analysed on the viable subset and reported as
explicitly CONDITIONAL, an unbalanced design declared as a limitation rather than patched
with imputation.

Uniform distributions throughout are a declared **choice of ignorance**, not a claim to
know priors.

Determinism: BLAS pinned to one thread before numpy is imported (below); the SALib sample
seed is fixed in :data:`SAMPLE_SEED`; every model cell is seeded and shares no state, so
pooling cannot move a result.

Usage
-----
    python scripts/run_brief13.py --phase pilot     # ~10 min: fixes n_seeds, viable frac
    python scripts/run_brief13.py --phase morris    # ~6 min
    python scripts/run_brief13.py --phase sobol     # ~80 min
    python scripts/run_brief13.py --phase wide      # ~40 min (declared sigma check)
    python scripts/run_brief13.py --phase all
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time

# Make ``src/`` importable here AND in the process-pool children (Windows spawns fresh
# interpreters that re-import experiment/model and only inherit sys.path via the env).
_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
os.environ["PYTHONPATH"] = _SRC + os.pathsep + os.environ.get("PYTHONPATH", "")

# Pin BLAS/numpy to one thread BEFORE numpy is imported (here via pandas/experiment), so
# the reduction order is deterministic and workers do not each spawn a full BLAS pool.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
import pandas as pd

from experiment import (
    SA_RHO_HI,
    SA_RHO_LO,
    qoi_from_runs,
    run_design_points,
)

RESULTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: Fixed sampling seed: SALib's Morris and Saltelli samplers are random, so the design
#: matrix itself must be pinned for the driver to be reproducible.  Declared, not tuned.
SAMPLE_SEED = 20260720

STEPS, TAIL = 2000, 50

#: Seeds per (point, rho), chosen on PILOT EVIDENCE rather than convention.  The pilot
#: measures ``noise_ratio`` = sd of the mean slope / sd of the slope across design points:
#: 0.207 at 3 seeds, 0.170 at 5, 0.111 at 10 (it scales as 1/sqrt(n), i.e. it is sampling
#: noise, not structure).  At 3 seeds the seed noise is ~4.3% of the QoI variance; it
#: lands in the residual, so it depresses S1 slightly and inflates apparent interaction.
#: That is the declared price of the compute budget, and ``slope_seed_sd`` is carried
#: next to every index so a reader can weigh it.
#:
#: NOTE, declared: the Morris screening was run at 5 seeds before this was lowered.
#: Screening only ranks parameters, so the mismatch cannot bias the decomposition — but
#: the two levels are not at identical settings and that is recorded rather than hidden.
N_SEEDS = 3

#: The swept space (brief 13 §2).  Uniform ranges, declared as a choice of ignorance.
#: ``category`` is what makes an index interpretable: a large index on an ANCHORED
#: parameter means the result depends on something the data pin down; a large index on a
#: CONVENTION means it depends on something chosen.
PARAMS = [
    # name,                      lo,    hi,   category,      source / note
    ("sigma",                    0.40,  0.60, "anchored",    "Chirinko 2008; Chirinko & Mallick 2017; Knoblach et al. 2020"),
    ("eta",                      0.05,  0.15, "anchored",    "Blanchflower-Oswald ~0.10; Nijkamp-Poot ~0.07"),
    ("benefit_replacement_rate", 0.00,  0.60, "anchored",    "OECD NRR ~0.4-0.6; 0 spans the no-welfare case"),
    ("pi0",                      0.30,  0.40, "anchored",    "capital share"),
    ("pct_capitalists",          0.05,  0.20, "anchored",    "Teglio (2025) inequality dimension; sweepable since brief 12"),
    ("delta",                    0.03,  0.09, "convention",  "structures 2-3%, BEA aggregate with IPP ~9% (brief 11)"),
    ("c1",                       0.80,  0.95, "semi",        "high MPC for constrained households"),
    ("wealth_effect",            0.03,  0.08, "semi",        "Slacalek 2009 ~0.05"),
    ("capitalist_mpc",           0.20,  0.50, "semi",        "carries the Kaleckian intervention"),
    ("beta",                     0.00,  1.00, "convention",  "accelerator gain; answers point 10-bis"),
    ("target_utilization",       0.80,  0.95, "convention",  "realised utilisation ~0.80 empirically"),
    ("investment_floor",         0.00,  0.25, "convention",  "guardrail, no empirical referent"),
    ("u_min",                    0.005, 0.05, "convention",  "registered debt (brief 07): wage-oscillation amplitude rests on it"),
    ("wage_floor",               0.30,  0.60, "convention",  "design target (w_min)"),
    ("expectation_gain",         0.25,  1.00, "unanchorable", "swept, not chosen (brief 08)"),
    ("c0",                       0.50,  2.50, "unanchorable", "not anchorable by decision (brief 11 D3); spans both regimes"),
]

#: Screened in Morris only (brief 13 §2): a guardrail that bites just where the fiscal
#: instrument saturates.  Dropped from Sobol unless the screening says otherwise.
MAX_TAX = ("max_tax", 0.30, 0.90, "convention", "cap on the balanced-budget rate")

#: The sigma range for the declared wide check (§4).  The PRIMARY analysis keeps the
#: narrow empirical range: the question is "does the headline hold where the data put
#: sigma", not "does sigma matter".
WIDE_SIGMA = (0.30, 1.00)

#: ------------------------------------------------------------------------
#: PRUNING RULE - DECLARED BEFORE THE SCREENING IS RUN (brief 13 §4).
#: A parameter survives to the Sobol stage if, on AT LEAST ONE of the three QoIs
#: (slope, viability, wage-led indicator), it is either
#:   (a) among the top MORRIS_TOP_K by mu*, or
#:   (b) has mu* >= MORRIS_MU_FRAC of the largest mu* for that QoI.
#: Both limbs are fixed here, in the source, before any Morris output exists.  No
#: post-hoc adjustment: if the rule admits 11 parameters, Sobol runs on 11 and the extra
#: cost is reported.
#: ------------------------------------------------------------------------
MORRIS_TOP_K = 8
MORRIS_MU_FRAC = 0.20
MORRIS_KEEP_RULE = (f"top-{MORRIS_TOP_K} by mu* on at least one QoI, "
                    f"OR mu* >= {MORRIS_MU_FRAC:g} x max(mu*) for that QoI")

MORRIS_TRAJECTORIES = 20
#: Saltelli base sample.  Sized to the MEASURED throughput of this machine (an i5-1335U:
#: 2 performance + 8 efficiency cores, 2.96 model runs/s wall-clock under the pool, not
#: the ~10x an all-P-core count would suggest), against the 11 parameters the declared
#: keep rule admitted: N*(k+2) design points x 2 rho x N_SEEDS runs.  N = 256 is a budget
#: decision, declared: small first-order indices will have bootstrap CIs overlapping zero
#: and are reported that way rather than presented as resolved.
SOBOL_N = 256
#: The wide-sigma check is secondary by construction (§4), so it runs at half N.
SOBOL_N_WIDE = 128
BOOTSTRAP_RESAMPLES = 2000

#: QoIs entering the VARIANCE DECOMPOSITION.  Both are defined at every design point, so
#: neither Morris nor Saltelli needs a subset or a filled-in value.
#:
#: This is a correction to the first cut of this driver, and the reason is worth keeping.
#: The obvious design — screen the slope on the viable points only — is **not available**:
#: Morris estimates elementary effects along trajectories of (k+1) points and Saltelli
#: reads its matrix positionally, so dropping rows destroys the estimator (it fails
#: outright: "cannot reshape array of size 159 into shape (8,19)").  The alternative,
#: filling collapsed points with the viable mean, is imputation — it invents values the
#: model never produced and drags the indices of whatever causes collapse toward zero.
#: Neither is acceptable, so the decomposition runs on quantities that are genuinely
#: measured everywhere: ``slope_raw`` (the CRN difference as measured, collapse included)
#: and ``viable`` (binary, exact).  The CONDITIONAL question the brief also asks — the
#: response given survival — is answered descriptively on the viable subset, plus
#: RBD-FAST first-order indices, which unlike Saltelli work on an arbitrary sample.
QOIS = ["slope_raw", "viable"]

#: Conditional QoI: analysed on the viable subset only, by a different estimator, and
#: reported as such.  S1 only — RBD-FAST gives no total-order index.
QOI_CONDITIONAL = "slope"


def problem(names_and_ranges):
    """SALib problem dict from a list of (name, lo, hi, ...) tuples."""
    return {
        "num_vars": len(names_and_ranges),
        "names": [p[0] for p in names_and_ranges],
        "bounds": [[p[1], p[2]] for p in names_and_ranges],
    }


def points_from_sample(sample, names, fixed=None):
    """Turn a SALib sample matrix into MacroModel kwarg dicts."""
    fixed = fixed or {}
    return [dict(zip(names, row.tolist()), **fixed) for row in sample]


def evaluate(points, workers, seeds=N_SEEDS, label=""):
    """Run every design point at both rho values and reduce to QoIs."""
    t0 = time.perf_counter()
    print(f"  {label}: {len(points)} points x 2 rho x {seeds} seeds "
          f"= {len(points) * 2 * seeds} runs")
    runs = run_design_points(points, seeds=seeds, steps=STEPS, tail=TAIL, workers=workers)
    qoi = qoi_from_runs(runs)
    dt = time.perf_counter() - t0
    print(f"  {label}: done in {dt / 60:.1f} min  "
          f"(viable {qoi['viable'].mean():.3f}, "
          f"wage-led among viable {qoi['wage_led'].mean(skipna=True):.3f})")
    return runs, qoi


def environment():
    """Record the environment so the run is attributable (brief 13 §5)."""
    from importlib.metadata import version
    import mesa
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "mesa": mesa.__version__,
        "SALib": version("SALib"),
        "sample_seed": SAMPLE_SEED,
        "steps": STEPS,
        "tail": TAIL,
        "n_seeds": N_SEEDS,
        "rho_lo": SA_RHO_LO,
        "rho_hi": SA_RHO_HI,
        "morris_keep_rule": MORRIS_KEEP_RULE,
    }


# ---------------------------------------------------------------------------
# Phase: pilot
# ---------------------------------------------------------------------------

def phase_pilot(workers, n_points=32, seed_levels=(3, 5, 10)):
    """Decide ``N_SEEDS`` on evidence, and measure the viable fraction before committing.

    Three things the SA design rests on and none of which are knowable a priori:

    1. **Is the CRN slope estimator quiet enough at few seeds?**  What matters is not the
       absolute seed noise but its size against the spread of the slope ACROSS design
       points - that ratio is what the Sobol indices have to resolve.  Reported as
       ``noise_ratio = mean(inter-seed sd of slope) / sd(slope across points)``.
    2. **What fraction of the space is viable?**  The slope analysis is conditional on
       viability, so a low fraction would mean the conditional Sobol runs on a thin, badly
       shaped subset - a design problem to face here, not after 80 minutes of Sobol.
    3. **Is the sampling reproducible?**  Asserted directly.
    """
    from SALib.sample import sobol as sobol_sample

    print("\n=== PILOT ===")
    prob = problem(PARAMS)
    # A small Saltelli draw is only being used as a space-filling sample here; its
    # structure is irrelevant, we just want points spread over the box.
    sample = sobol_sample.sample(prob, 8, calc_second_order=False, seed=SAMPLE_SEED)
    sample = sample[:n_points]
    pts = points_from_sample(sample, prob["names"])

    # Reproducibility of the design matrix itself.
    again = sobol_sample.sample(prob, 8, calc_second_order=False, seed=SAMPLE_SEED)[:n_points]
    assert np.array_equal(sample, again), "SALib sampling is not reproducible at a fixed seed"
    print(f"  sampling reproducible at seed {SAMPLE_SEED}: OK")

    rows = []
    for n in seed_levels:
        runs, qoi = evaluate(pts, workers, seeds=n, label=f"pilot n_seeds={n}")
        viable = qoi[qoi["viable"] == 1.0]
        across = float(viable["slope"].std(ddof=1)) if len(viable) > 1 else float("nan")
        within = float(viable["slope_seed_sd"].mean()) if len(viable) else float("nan")
        # sd of the MEAN slope is the seed sd / sqrt(n): that is what actually enters the QoI.
        within_mean = within / np.sqrt(n) if np.isfinite(within) else float("nan")
        rows.append({
            "n_seeds": n,
            "n_points": len(qoi),
            "frac_viable": float(qoi["viable"].mean()),
            "frac_wage_led_viable": float(viable["wage_led"].mean()) if len(viable) else float("nan"),
            "slope_sd_across_points": across,
            "slope_seed_sd_mean": within,
            "slope_sd_of_mean": within_mean,
            "noise_ratio": within_mean / across if across else float("nan"),
        })
        print(f"    n={n:>2}: viable {rows[-1]['frac_viable']:.3f}  "
              f"wage-led|viable {rows[-1]['frac_wage_led_viable']:.3f}  "
              f"noise ratio {rows[-1]['noise_ratio']:.3f}")

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RESULTS, "ces_b13_pilot.csv"), index=False)
    print(f"  wrote {os.path.join(RESULTS, 'ces_b13_pilot.csv')}")
    return out


# ---------------------------------------------------------------------------
# Phase: Morris screening
# ---------------------------------------------------------------------------

def phase_morris(workers, reuse=False):
    """Level 1: separate influential parameters from irrelevant ones.

    Morris is a screening method - its ``mu*`` ranks, it does not apportion variance.  It
    is used here only to decide who reaches the Sobol stage, under the rule declared in
    :data:`MORRIS_KEEP_RULE` before any of this ran.
    """
    from SALib.analyze import morris as morris_analyze
    from SALib.sample import morris as morris_sample

    print("\n=== MORRIS SCREENING ===")
    spec = PARAMS + [MAX_TAX]
    prob = problem(spec)
    sample = morris_sample.sample(prob, MORRIS_TRAJECTORIES, num_levels=4, seed=SAMPLE_SEED)
    pts = points_from_sample(sample, prob["names"])

    runs_path = os.path.join(RESULTS, "ces_b13_morris_runs.csv")
    if reuse and os.path.exists(runs_path):
        # The simulation is the expensive half and it is deterministic per seed, so a
        # re-analysis re-reads it instead of re-running it.  The design matrix is
        # regenerated from the same fixed seed above, and the point count is checked
        # against the stored runs so a stale file cannot be silently re-analysed.
        runs = pd.read_csv(runs_path)
        assert runs["point"].nunique() == len(pts), (
            f"stored runs cover {runs['point'].nunique()} points, sample has {len(pts)}")
        qoi = qoi_from_runs(runs)
        print(f"  reusing {runs_path}: {len(runs)} runs, {len(qoi)} points "
              f"(no simulation re-run)")
    else:
        runs, qoi = evaluate(pts, workers, label="morris")
        runs.to_csv(runs_path, index=False)
    qoi.to_csv(os.path.join(RESULTS, "ces_b13_morris_qoi.csv"), index=False)

    rows = []
    for q in QOIS:
        y = qoi[q].to_numpy(dtype=float)
        # Both screening QoIs are defined at every point by construction, so the whole
        # trajectory structure survives.  Assert it rather than trusting it: a silent NaN
        # here would corrupt the elementary effects instead of failing.
        assert np.isfinite(y).all(), f"{q} has non-finite values; Morris needs all points"
        res = morris_analyze.analyze(prob, sample, y, num_levels=4, seed=SAMPLE_SEED)
        for i, name in enumerate(res["names"]):
            rows.append({"qoi": q, "parameter": name, "mu_star": float(res["mu_star"][i]),
                         "mu": float(res["mu"][i]), "sigma": float(res["sigma"][i]),
                         "mu_star_conf": float(res["mu_star_conf"][i]),
                         "n_points_used": int(len(y))})

    morris = pd.DataFrame(rows)
    morris.to_csv(os.path.join(RESULTS, "ces_b13_morris.csv"), index=False)

    survivors = apply_keep_rule(morris)
    print(f"\n  keep rule (declared ex ante): {MORRIS_KEEP_RULE}")
    print(f"  survivors ({len(survivors)}): {', '.join(survivors)}")
    dropped = [p[0] for p in spec if p[0] not in survivors]
    print(f"  dropped   ({len(dropped)}): {', '.join(dropped)}")
    return morris, survivors


def apply_keep_rule(morris):
    """The declared pruning rule, applied mechanically to the Morris table."""
    keep = set()
    for q, block in morris.groupby("qoi"):
        block = block.sort_values("mu_star", ascending=False)
        keep.update(block["parameter"].head(MORRIS_TOP_K))
        mx = block["mu_star"].max()
        if mx > 0:
            keep.update(block[block["mu_star"] >= MORRIS_MU_FRAC * mx]["parameter"])
    # Keep the declared PARAMS order for reproducible downstream indexing.
    ordered = [p[0] for p in PARAMS + [MAX_TAX] if p[0] in keep]
    return ordered


# ---------------------------------------------------------------------------
# Phase: Sobol
# ---------------------------------------------------------------------------

def phase_sobol(workers, survivors, N=SOBOL_N, sigma_range=None, tag="sobol"):
    """Level 2: apportion the variance of each QoI among the survivors.

    Non-survivors are held at the MIDPOINT of their declared range - a declared
    convention.  Freezing at a default would have privileged one corner of the space;
    the midpoint is neutral with respect to the uniform ranges the SA declares.

    ``S1`` and ``ST`` are reported TOGETHER, with bootstrap CIs: ``ST >> S1`` means
    interactions, which this model is expected to show, since the wage -> U -> capital
    channel is interactive by construction.
    """
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

    print(f"\n=== SOBOL ({tag}) ===")
    print(f"  swept ({len(swept)}): " +
          ", ".join(f"{n} [{lo:g},{hi:g}]" for n, lo, hi in swept))
    print(f"  fixed at midpoint ({len(fixed)}): " +
          ", ".join(f"{k}={v:g}" for k, v in fixed.items()))

    prob = problem(swept)
    sample = sobol_sample.sample(prob, N, calc_second_order=False, seed=SAMPLE_SEED)
    pts = points_from_sample(sample, prob["names"], fixed=fixed)

    runs, qoi = evaluate(pts, workers, label=tag)
    runs.to_csv(os.path.join(RESULTS, f"ces_b13_{tag}_runs.csv"), index=False)
    qoi.to_csv(os.path.join(RESULTS, f"ces_b13_{tag}_qoi.csv"), index=False)
    # The design matrix travels WITH the QoIs: the by-product analyses need parameter
    # values per point, and regenerating the sample to recover them makes every downstream
    # number depend on the sampler reproducing itself.  Cheaper and safer to store it.
    design = pd.concat([pd.DataFrame(sample, columns=prob["names"]),
                        qoi.reset_index(drop=True)], axis=1)
    design.to_csv(os.path.join(RESULTS, f"ces_b13_{tag}_design.csv"), index=False)

    rows = []
    for q in QOIS:
        y = qoi[q].to_numpy(dtype=float)
        # Defined everywhere by construction (see QOIS): no imputation, no subsetting.
        assert np.isfinite(y).all(), f"{q} has non-finite values; Saltelli needs all points"
        res = sobol_analyze.analyze(prob, y, calc_second_order=False,
                                    num_resamples=BOOTSTRAP_RESAMPLES, seed=SAMPLE_SEED)
        for i, name in enumerate(prob["names"]):
            rows.append({
                "qoi": q, "parameter": name, "estimator": "saltelli",
                "S1": float(res["S1"][i]), "S1_conf": float(res["S1_conf"][i]),
                "ST": float(res["ST"][i]), "ST_conf": float(res["ST_conf"][i]),
                "n_points": len(y), "N": N, "tag": tag,
            })

    # The CONDITIONAL analysis the brief also asks for.  RBD-FAST estimates first-order
    # indices from an ARBITRARY sample, so it can run on the viable subset without the
    # positional matrix Saltelli needs — at the price of giving no total-order index.
    # A different estimator on a different sample: reported separately, never mixed into
    # the table above.
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
        print(f"  {QOI_CONDITIONAL}|viable: RBD-FAST S1 on {mask.sum()}/{len(mask)} "
              f"viable points (conditional, S1 only)")
    else:
        print(f"  {QOI_CONDITIONAL}|viable: only {mask.sum()} viable points - "
              f"conditional index SKIPPED (declared)")

    sobol = pd.DataFrame(rows)
    sobol.to_csv(os.path.join(RESULTS, f"ces_b13_{tag}_indices.csv"), index=False)
    print(f"  wrote ces_b13_{tag}_indices.csv")
    return sobol, qoi


def analyse_byproducts(tag="sobol"):
    """The two by-product questions of §1, as committed, reproducible tables.

    Both are INTERVENTIONAL readings of the Saltelli design: each parameter is varied
    independently of the others, so comparing bins of it is a comparison across otherwise
    comparable draws — which is exactly what brief 11 said the accounting identity could
    not deliver.
    """
    path = os.path.join(RESULTS, f"ces_b13_{tag}_design.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
    else:
        # The design CSV was added after this brief's primary run had already completed.
        # Rather than re-simulate 130 minutes, the sample is REGENERATED — legitimate
        # only because it is deterministic at the fixed SAMPLE_SEED, which the pilot
        # asserts.  The row count is checked against the stored QoIs so a mismatched
        # sampler cannot silently produce a wrong join.  Written out so the next reader
        # takes the stored path.
        from SALib.sample import sobol as sobol_sample
        qoi = pd.read_csv(os.path.join(RESULTS, f"ces_b13_{tag}_qoi.csv"))
        qoi = qoi.sort_values("point").reset_index(drop=True)
        survivors = apply_keep_rule(pd.read_csv(os.path.join(RESULTS, "ces_b13_morris.csv")))
        spec = {p[0]: p for p in PARAMS + [MAX_TAX]}
        N = SOBOL_N if tag == "sobol" else SOBOL_N_WIDE
        rng = WIDE_SIGMA if tag == "wide" else None
        swept = [(n, rng[0] if (n == "sigma" and rng) else spec[n][1],
                  rng[1] if (n == "sigma" and rng) else spec[n][2]) for n in survivors]
        prob = problem(swept)
        sample = sobol_sample.sample(prob, N, calc_second_order=False, seed=SAMPLE_SEED)
        if len(sample) != len(qoi):
            print(f"  regenerated sample has {len(sample)} rows vs {len(qoi)} QoI rows "
                  f"- by-products SKIPPED (declared)")
            return None
        df = pd.concat([pd.DataFrame(sample, columns=prob["names"]), qoi], axis=1)
        df.to_csv(path, index=False)
        print(f"  design matrix regenerated at seed {SAMPLE_SEED} and written to "
              f"{os.path.basename(path)} (no simulation re-run)")
    v = df[df["viable"] == 1.0].copy()
    #: Profit LEVEL, not share: Kalecki's claim ("capitalists earn what they spend") is
    #: about the level.  The share can fall while the level rises, if output rises faster.
    v["profit_lo"] = v["Profit_Share_lo"] * v["Output_lo"]

    rows = []
    for name in ("capitalist_mpc", "beta", "sigma", "delta"):
        # Bin over the range ACTUALLY SAMPLED, not the one declared in PARAMS: the wide
        # check overrides sigma's range, and binning it on the narrow declaration would
        # silently drop most of the sample (1 194 of 1 664 points, when this was first
        # written that way).  Reading the edges off the data keeps both tags honest.
        lo, hi = float(df[name].min()), float(df[name].max())
        edges = np.linspace(lo, hi, 5)
        for a, b in zip(edges, edges[1:]):
            sel = (df[name] >= a) & (df[name] <= b if b == edges[-1] else df[name] < b)
            blk, vb = df[sel], v[(v[name] >= a) & (v[name] <= b)]
            rows.append({
                "parameter": name, "bin_lo": a, "bin_hi": b, "n_points": int(sel.sum()),
                "frac_viable": float(blk["viable"].mean()) if len(blk) else float("nan"),
                "n_viable": int(len(vb)),
                "P_wage_led_given_viable": float(vb["wage_led"].mean()) if len(vb) else float("nan"),
                "mean_slope_viable": float(vb["slope"].mean()) if len(vb) else float("nan"),
                "mean_capitalist_consumption": float(vb["Capitalist_Consumption_lo"].mean()) if len(vb) else float("nan"),
                "mean_profit_level": float(vb["profit_lo"].mean()) if len(vb) else float("nan"),
                "mean_profit_share": float(vb["Profit_Share_lo"].mean()) if len(vb) else float("nan"),
                "mean_output": float(vb["Output_lo"].mean()) if len(vb) else float("nan"),
            })
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RESULTS, f"ces_b13_{tag}_byproducts.csv"), index=False)

    corr = pd.DataFrame([{
        "pair": "capitalist_mpc -> Capitalist_Consumption",
        "corr": float(v["capitalist_mpc"].corr(v["Capitalist_Consumption_lo"]))},
        {"pair": "Capitalist_Consumption -> profit LEVEL",
         "corr": float(v["Capitalist_Consumption_lo"].corr(v["profit_lo"]))},
        {"pair": "Capitalist_Consumption -> profit SHARE",
         "corr": float(v["Capitalist_Consumption_lo"].corr(v["Profit_Share_lo"]))},
    ])
    corr.to_csv(os.path.join(RESULTS, f"ces_b13_{tag}_kalecki.csv"), index=False)
    print(f"\n  by-products -> ces_b13_{tag}_byproducts.csv, ces_b13_{tag}_kalecki.csv")
    print(corr.to_string(index=False))
    return out


def make_figures(tag="sobol"):
    """Three figures: Morris mu*-sigma, S1/ST bars with CI, viability vs the top driver."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    made = []
    mpath = os.path.join(RESULTS, "ces_b13_morris.csv")
    if os.path.exists(mpath):
        m = pd.read_csv(mpath)
        fig, axes = plt.subplots(1, m["qoi"].nunique(), figsize=(11, 4.6), squeeze=False)
        for ax, (q, blk) in zip(axes[0], m.groupby("qoi")):
            ax.scatter(blk["mu_star"], blk["sigma"], s=26)
            for _, r in blk.iterrows():
                if r["mu_star"] > 0.05 * blk["mu_star"].max():
                    ax.annotate(r["parameter"], (r["mu_star"], r["sigma"]),
                                fontsize=7, xytext=(3, 3), textcoords="offset points")
            ax.set_xlabel(r"$\mu^*$ (influence)")
            ax.set_ylabel(r"$\sigma$ (non-linearity / interaction)")
            ax.set_title(f"Morris screening — {q}", fontsize=10)
        fig.suptitle("Level 1: which parameters matter at all", fontsize=11)
        fig.tight_layout()
        p = os.path.join(RESULTS, "ces_b13_morris_mu_sigma.png")
        fig.savefig(p, dpi=140); plt.close(fig); made.append(p)

    ipath = os.path.join(RESULTS, f"ces_b13_{tag}_indices.csv")
    if os.path.exists(ipath):
        idx = pd.read_csv(ipath)
        sal = idx[idx["estimator"] == "saltelli"]
        qs = sorted(sal["qoi"].unique())
        fig, axes = plt.subplots(1, len(qs), figsize=(5.6 * len(qs), 4.8), squeeze=False)
        for ax, q in zip(axes[0], qs):
            blk = sal[sal["qoi"] == q].sort_values("ST")
            y = np.arange(len(blk))
            ax.barh(y - 0.2, blk["S1"], height=0.38, xerr=blk["S1_conf"],
                    label="S1 (first order)", capsize=2)
            ax.barh(y + 0.2, blk["ST"], height=0.38, xerr=blk["ST_conf"],
                    label="ST (total)", capsize=2)
            ax.set_yticks(y); ax.set_yticklabels(blk["parameter"], fontsize=8)
            ax.axvline(0.0, color="k", lw=0.8)
            ax.set_xlabel("Sobol index"); ax.set_title(q, fontsize=10)
            ax.legend(fontsize=8)
        fig.suptitle("Level 2: ST >> S1 means interactions dominate "
                     "(bars: bootstrap CI)", fontsize=11)
        fig.tight_layout()
        p = os.path.join(RESULTS, f"ces_b13_{tag}_indices.png")
        fig.savefig(p, dpi=140); plt.close(fig); made.append(p)

    bpath = os.path.join(RESULTS, f"ces_b13_{tag}_byproducts.csv")
    if os.path.exists(bpath):
        bp = pd.read_csv(bpath)
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
        for name, ax in (("delta", axes[0]), ("beta", axes[1])):
            blk = bp[bp["parameter"] == name]
            mid = 0.5 * (blk["bin_lo"] + blk["bin_hi"])
            ax.plot(mid, blk["frac_viable"], "o-", label="fraction viable")
            ax.plot(mid, blk["P_wage_led_given_viable"], "s--",
                    label="P(wage-led | viable)")
            ax.set_xlabel(name); ax.set_ylim(-0.05, 1.05); ax.legend(fontsize=8)
            ax.set_title(f"{name}: viability and sign", fontsize=10)
        fig.suptitle("Where the model lives, and where the sign turns", fontsize=11)
        fig.tight_layout()
        p = os.path.join(RESULTS, f"ces_b13_{tag}_byproducts.png")
        fig.savefig(p, dpi=140); plt.close(fig); made.append(p)

    for p in made:
        print(f"  wrote {os.path.basename(p)}")
    return made


def summarise(qoi, label):
    """The headline numbers: P(dY/drho < 0) and the viable fraction."""
    viable = qoi[qoi["viable"] == 1.0]
    p_wage_led = float(viable["wage_led"].mean()) if len(viable) else float("nan")
    return {
        "analysis": label,
        "n_points": int(len(qoi)),
        "frac_viable": float(qoi["viable"].mean()),
        "n_viable": int(len(viable)),
        "P_wage_led_given_viable": p_wage_led,
        "P_wage_led_all_points": p_wage_led * float(qoi["viable"].mean()),
        "slope_mean_viable": float(viable["slope"].mean()) if len(viable) else float("nan"),
        "slope_sd_viable": float(viable["slope"].std(ddof=1)) if len(viable) > 1 else float("nan"),
        "slope_seed_sd_mean": float(viable["slope_seed_sd"].mean()) if len(viable) else float("nan"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase", default="all",
                    choices=["pilot", "morris", "sobol", "wide", "report", "all"])
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--reuse-runs", action="store_true",
                    help="re-analyse stored Morris runs instead of re-simulating them")
    args = ap.parse_args()

    os.makedirs(RESULTS, exist_ok=True)
    env = environment()
    print("Brief 13 - global sensitivity analysis")
    print(json.dumps(env, indent=2))
    with open(os.path.join(RESULTS, "ces_b13_environment.json"), "w") as fh:
        json.dump(env, fh, indent=2)

    summaries = []

    if args.phase == "report":
        # Analysis only: reads the committed artifacts, runs no simulation.
        analyse_byproducts("sobol")
        make_figures("sobol")
        return 0

    if args.phase in ("pilot", "all"):
        phase_pilot(args.workers)
        if args.phase == "pilot":
            return 0

    survivors = None
    if args.phase in ("morris", "sobol", "wide", "all"):
        path = os.path.join(RESULTS, "ces_b13_morris.csv")
        if args.phase in ("morris", "all"):
            _, survivors = phase_morris(args.workers, reuse=args.reuse_runs)
        elif os.path.exists(path):
            survivors = apply_keep_rule(pd.read_csv(path))
            print(f"  survivors read back from {path}: {', '.join(survivors)}")
        else:
            print("  no Morris table found - run --phase morris first")
            return 1

    if args.phase in ("sobol", "all"):
        _, qoi = phase_sobol(args.workers, survivors, N=SOBOL_N, tag="sobol")
        summaries.append(summarise(qoi, "primary (empirical sigma 0.40-0.60)"))

    if args.phase in ("wide", "all"):
        _, qoi_w = phase_sobol(args.workers, survivors, N=SOBOL_N_WIDE,
                               sigma_range=WIDE_SIGMA, tag="wide")
        summaries.append(summarise(qoi_w, f"wide sigma check {WIDE_SIGMA}"))

    if summaries:
        summary = pd.DataFrame(summaries)
        # Phases can be run separately, so merge with what is already on disk instead of
        # overwriting it (a --phase wide run must not erase the primary analysis).
        path = os.path.join(RESULTS, "ces_b13_summary.csv")
        if os.path.exists(path):
            old = pd.read_csv(path)
            old = old[~old["analysis"].isin(summary["analysis"])]
            summary = pd.concat([old, summary], ignore_index=True)
        summary.to_csv(path, index=False)
        print("\n=== HEADLINE ===")
        print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

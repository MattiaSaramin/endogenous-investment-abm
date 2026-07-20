"""
Reusable experiment harness for the normalised-CES endogenous-investment core.

Centralises the Monte-Carlo plumbing (multi-seed runs, tidy dataframes,
confidence bands and the parameter sweeps) so notebooks and ad-hoc analysis
share one tested code path.

Three experiments live here:

* ``retention_sweep`` — the point-11 sweep over the **retention ratio** ``rho``
  (the share of gross profit firms retain and invest internally), at fixed sigma.
* ``sigma_rho_sweep`` — the brief-04 **two-dimensional (sigma, rho) grid**, whose
  output is the *sign frontier*: the locus where ``dY/drho`` changes sign.  The
  Cobb-Douglas core imposes sigma = 1, which the empirical literature rejects;
  sigma is what sets the strength of capital-labour substitution and therefore the
  sign of the headline result, so it is swept rather than chosen.
* ``run_grid_panel`` + ``bootstrap_sigma_star`` — the brief-05 **robustness stack**.
  Brief 04 reported ``sigma*`` to three decimals with no error bar, off centred
  finite differences on a two-point-wide support, against inter-seed bands reaching
  6.7% of Y.  This layer keeps the **per-seed** observations instead of collapsing
  them to a cell mean, takes the derivative as an **OLS slope over the whole common
  viable support**, and puts a **bootstrap CI** on ``sigma*`` — including an honest
  count of the resamples in which the sign never turns, so ``sigma*`` is undefined.

The brief-04 functions (``sigma_rho_sweep``, ``sweep_derivatives``, ``sign_frontier``)
are kept unchanged, not superseded: they are the path the regression pin reproduces.

A warning that applies to every sweep here: the model has **multiple equilibria and
a viability threshold near rho ~ 0.30**.  ``initial_capital`` selects the basin, so
it is held fixed across a whole grid and reported; cells that collapse are an
*outcome*, not an error.

Typical use
-----------
>>> from experiment import run_experiment, summarize, retention_sweep, sigma_rho_sweep
>>> panel = run_experiment(retention_ratio=0.40, steps=2000, seeds=3)
>>> band  = summarize(panel)                       # mean + 95% CI per time step
>>> sweep = retention_sweep([0.0, 0.20, 0.35, 0.40])   # steady-state vs rho
>>> grid  = sigma_rho_sweep()                      # the (sigma, rho) sign frontier
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from model import MacroModel


DEFAULT_STEPS = 2000
DEFAULT_SEEDS = 3
RETENTION_SWEEP = [0.0, 0.20, 0.35, 0.40]

#: Leontief probe, the central empirical range, Cobb-Douglas, and the sigma > 1 puzzle.
#: Chirinko (2008) 0.40-0.60; Chirinko & Mallick (2017) ~0.40; Knoblach, Roessler &
#: Zwerschke (2020) meta-regression 0.45-0.87 (rejects Cobb-Douglas); Fed SIGMA 0.5;
#: Karabarbounis & Neiman (2014) dissent above 1.
SIGMA_SWEEP = [0.05, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5]
RHO_SWEEP = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

#: Output below this counts as a collapsed cell (the economy is dead, not slow).
COLLAPSE_Y = 1.0


def run_single(retention_ratio, steps=DEFAULT_STEPS, seed=0, **params):
    """Run one simulation and return its per-step model dataframe.

    Extra keyword arguments are forwarded to :class:`MacroModel`.
    """
    model = MacroModel(retention_ratio=retention_ratio, seed=seed, **params)
    for _ in range(steps):
        model.step()

    df = model.datacollector.get_model_vars_dataframe()
    df.index.name = "Step"
    return df


def run_experiment(retention_ratio, steps=DEFAULT_STEPS, seeds=DEFAULT_SEEDS, **params):
    """Monte-Carlo a scenario over ``seeds`` replications.

    Returns a long dataframe with a ``Seed`` column and a ``Step`` index.
    """
    frames = []
    for seed in range(seeds):
        df = run_single(retention_ratio, steps=steps, seed=seed, **params).copy()
        df["Seed"] = seed
        frames.append(df)
    return pd.concat(frames)


def summarize(panel, confidence=0.95):
    """Collapse a multi-seed panel to a mean and confidence band per step.

    The band is a normal-approximation interval on the mean across seeds,
    ``mean +/- z * std / sqrt(n)``.  Returns a dataframe indexed by step with
    ``<metric>_mean``, ``<metric>_lo`` and ``<metric>_hi`` columns.
    """
    from statistics import NormalDist

    metrics = [c for c in panel.columns if c != "Seed"]
    grouped = panel.groupby(panel.index)[metrics]

    mean = grouped.mean()
    n = panel.groupby(panel.index)["Seed"].nunique()
    sem = grouped.std(ddof=1).div(np.sqrt(n), axis=0).fillna(0.0)
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)

    out = {}
    for m in metrics:
        out[f"{m}_mean"] = mean[m]
        out[f"{m}_lo"] = mean[m] - z * sem[m]
        out[f"{m}_hi"] = mean[m] + z * sem[m]
    return pd.DataFrame(out)


def retention_sweep(
    retentions=RETENTION_SWEEP,
    steps=DEFAULT_STEPS,
    seeds=DEFAULT_SEEDS,
    tail=50,
    **params,
):
    """Sweep the retention ratio and report steady-state outcomes.

    For each ``rho`` the model is run to (near) steady state and the last ``tail``
    steps are averaged, then averaged again across seeds.  Returns one row per
    ``rho`` with the headline supply-side indicators, including the mean firm
    money buffer (expected ~0, the anti-sequestration guarantee).
    """
    records = []
    for rho in retentions:
        panel = run_experiment(rho, steps=steps, seeds=seeds, **params)
        steady = panel[panel.index >= steps - tail].drop(columns="Seed").mean()

        output = steady["Output"]
        records.append({
            "retention_ratio": rho,
            "Y": output,
            "u": steady["Average_Utilization"],
            "K_over_Y": steady["Total_Capital"] / output if output > 0 else float("nan"),
            "I_over_Y": steady["Investment"] / output if output > 0 else float("nan"),
            "Wage_Share": steady["Wage_Share"],
            "Profit_Share": steady["Profit_Share"],
            "Total_Capital": steady["Total_Capital"],
            "Money_Buffer": steady["Money_Buffer"],
        })
    return pd.DataFrame(records)


# ======================================================================
# The (sigma, rho) grid — brief 04
# ======================================================================

_BOUND_COLS = {
    "Bound_Demand": "demand",
    "Bound_Profitmax": "profitmax",
    "Bound_Capital": "capital",
    "Bound_Workforce": "workforce",
}


def sigma_rho_sweep(
    sigmas=SIGMA_SWEEP,
    rhos=RHO_SWEEP,
    steps=DEFAULT_STEPS,
    seeds=DEFAULT_SEEDS,
    tail=50,
    **params,
):
    """Run the two-dimensional (sigma, rho) grid and report steady-state outcomes.

    Each cell is ``seeds`` replications of ``steps`` periods; the last ``tail``
    observations are averaged within a seed, then across seeds.  ``initial_capital``
    is whatever ``params`` says (default 40.0) and is *the same in every cell* — with
    multiple equilibria the initial capital selects the basin, so varying it would
    confound the sweep.

    Returns one row per cell with the headline indicators, the inter-seed band on
    ``Y``, the modal binding constraint, and a ``collapsed`` flag.
    """
    records = []
    for sigma in sigmas:
        for rho in rhos:
            per_seed = []
            for seed in range(seeds):
                df = run_single(rho, steps=steps, seed=seed, sigma=sigma, **params)
                per_seed.append(df[df.index >= steps - tail].mean())
            cell = pd.DataFrame(per_seed)
            steady = cell.mean()

            output = steady["Output"]
            ys = cell["Output"].to_numpy()
            collapsed = bool(output < COLLAPSE_Y)

            bound = max(_BOUND_COLS, key=lambda c: steady[c])
            records.append({
                "sigma": sigma,
                "rho": rho,
                "Y": output,
                "K": steady["Total_Capital"],
                "K_over_Y": steady["Total_Capital"] / output if output > 0 else np.nan,
                "I_over_Y": steady["Investment"] / output if output > 0 else np.nan,
                "L": steady["Employment"],
                "U": steady["Unemployment_Rate"],
                "wage_share": steady["Wage_Share"],
                "wage_share_profitmax": steady["Wage_Share_Profitmax"],
                "utilization": steady["Average_Utilization"],
                "binding": _BOUND_COLS[bound] if not collapsed else "collapsed",
                "bound_demand": steady["Bound_Demand"],
                "bound_profitmax": steady["Bound_Profitmax"],
                "bound_capital": steady["Bound_Capital"],
                "bound_workforce": steady["Bound_Workforce"],
                "cash_constrained": steady["Cash_Constrained"],
                "Y_seed_min": ys.min(),
                "Y_seed_max": ys.max(),
                # Inter-seed band as a fraction of the mean: the mean-field check.
                "Y_band_rel": (ys.max() - ys.min()) / output if output > 0 else np.nan,
                "collapsed": collapsed,
            })
    return pd.DataFrame(records)


def sweep_derivatives(grid, viable_only=True):
    """``dY/drho`` and ``dU/drho`` per sigma, by centred finite differences.

    Collapsed cells are dropped before differencing when ``viable_only``: a
    derivative taken across the viability threshold measures the collapse, not the
    response of a living economy to retention.  Uses ``numpy.gradient``, which is
    centred in the interior and one-sided at the ends, and handles the uneven
    spacing left by dropped cells.

    Returns a long frame with one row per surviving (sigma, rho) cell.
    """
    out = []
    for sigma, block in grid.groupby("sigma"):
        b = block.sort_values("rho")
        if viable_only:
            b = b[~b["collapsed"]]
        if len(b) < 2:
            continue
        rho = b["rho"].to_numpy(dtype=float)
        out.append(pd.DataFrame({
            "sigma": sigma,
            "rho": rho,
            "Y": b["Y"].to_numpy(),
            "U": b["U"].to_numpy(),
            "dY_drho": np.gradient(b["Y"].to_numpy(dtype=float), rho),
            "dU_drho": np.gradient(b["U"].to_numpy(dtype=float), rho),
            "binding": b["binding"].to_numpy(),
        }))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def sign_frontier(deriv, column="dY_drho"):
    """Interpolate ``sigma*``: where ``dY/drho`` crosses zero, per rho.

    For each rho the derivative is read along sigma and a linear interpolation is
    taken between the two adjacent sigma grid points that bracket the sign change
    (``sigma* = s0 - d0*(s1-s0)/(d1-d0)``).  Returns one row per rho where a crossing
    exists; an empty frame means the sign does **not** change anywhere in the tested
    range, which is itself the result and must be reported as such.
    """
    rows = []
    for rho, block in deriv.groupby("rho"):
        b = block.sort_values("sigma")
        s = b["sigma"].to_numpy(dtype=float)
        d = b[column].to_numpy(dtype=float)
        for i in range(len(s) - 1):
            d0, d1 = d[i], d[i + 1]
            if np.isnan(d0) or np.isnan(d1) or d0 == d1:
                continue
            if (d0 < 0.0) != (d1 < 0.0):
                rows.append({
                    "rho": rho,
                    "sigma_star": s[i] - d0 * (s[i + 1] - s[i]) / (d1 - d0),
                    "sigma_lo": s[i],
                    "sigma_hi": s[i + 1],
                    f"{column}_lo": d0,
                    f"{column}_hi": d1,
                    "method": "linear interpolation between adjacent sigma cells",
                })
    return pd.DataFrame(rows)


# ======================================================================
# Brief 05 — the robustness stack
# ======================================================================
#
# WHY A PER-SEED PANEL.  Everything below rests on keeping the individual seed
# observations.  A cell mean cannot support a bootstrap, and the bootstrap is the
# only thing that turns "sigma* = 0.679" into a defensible statement.  The seed is
# the unit of randomness, so it is the unit that gets resampled.

#: sigma grid, refined in the crossing zone (0.7 and 0.9 added vs brief 04) because
#: that is where sigma* is decided.  0.05 stays as the Leontief probe.
SIGMA_SWEEP_B05 = [0.05, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.25, 1.5]

#: rho grid, denser and confined to the region that was viable in brief 04.  Brief 04
#: lost 39 of 70 cells to collapse, all at rho <= 0.3, which left the derivative only
#: two or three points to work with.  ``initial_capital`` stays FIXED at its default:
#: it selects the basin, so moving it would make this a different experiment.  If
#: rho = 0.35 collapses, that is an outcome.
RHO_SWEEP_B05 = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65]

#: The two c0 values swept as a full grid dimension.  c0 = 2.0 is what brief 04 ran;
#: c0 = 1.0 is the value parameter_notes.md claims.  c0 = 0.5 (below w_bar = 0.9) is
#: NOT here — it is a separate mechanism probe (stage B), not a calibration candidate.
C0_SWEEP = [1.0, 2.0]

#: Steady-state metrics carried from a run into the panel.  The wage-curve pair
#: (Wage_Rate, Wage_Floor_Binding) is appended for brief 07; it is APPENDED, not
#: interleaved, so the brief-04/05 columns keep their positions and the eta = 0 slice
#: stays byte-comparable to ces_b05_stage_a_panel on the shared columns.
_PANEL_METRICS = [
    "Output", "Total_Capital", "Investment", "Consumption", "Employment",
    "Unemployment_Rate", "Wage_Share", "Wage_Share_Profitmax", "Profit_Share",
    "Income_Gini", "Wealth_Gini", "Output_Gap", "Output_Gap_PM",
    "Potential_Output", "Potential_Output_PM", "Average_Utilization",
    "Money_Buffer", "Cash_Constrained",
    "Bound_Demand", "Bound_Profitmax", "Bound_Capital", "Bound_Workforce",
    "Wage_Rate", "Wage_Floor_Binding",
]


def _panel_job(job):
    """Run one (sigma, rho, c0, seed) cell and return its steady-state row.

    Module-level and picklable: this is the unit of work handed to the process pool.
    """
    sigma, rho, seed, steps, tail, params = job
    df = run_single(rho, steps=steps, seed=seed, sigma=sigma, **params)
    steady = df[df.index >= steps - tail].mean()

    row = {"sigma": sigma, "rho": rho, "seed": seed}
    row.update({m: float(steady[m]) for m in _PANEL_METRICS})
    return row


def run_grid_panel(
    sigmas=SIGMA_SWEEP_B05,
    rhos=RHO_SWEEP_B05,
    seeds=20,
    steps=DEFAULT_STEPS,
    tail=50,
    workers=None,
    **params,
):
    """Run a (sigma, rho) grid and return **one row per seed** — not per cell.

    Identical in economics to :func:`sigma_rho_sweep` (same ``run_single``, same seeds,
    same tail averaging); it differs only in *not* averaging the seeds away, so the
    bootstrap downstream has something to resample.  The regression pin checks the two
    paths agree.

    ``workers`` processes run cells in parallel; the model is deterministic per seed
    and cells share no state, so parallelism cannot change a result.
    """
    jobs = [
        (sigma, rho, seed, steps, tail, params)
        for sigma in sigmas
        for rho in rhos
        for seed in range(seeds)
    ]

    if workers == 1:
        rows = [_panel_job(j) for j in jobs]
    else:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(_panel_job, jobs, chunksize=1))

    return pd.DataFrame(rows).sort_values(["sigma", "rho", "seed"], ignore_index=True)


def _panel_job_tagged(job):
    """Run one (tag, sigma, rho, seed) cell and return ``(tag, steady-state row)``.

    Module-level and picklable, like :func:`_panel_job`, but carries a ``tag`` that
    identifies which configuration (which ``params`` dict) the cell belongs to, so many
    panels can share ONE process pool (see :func:`run_grid_panels`).  ``metrics`` travels
    in the job so a caller can collect extra reporters (e.g. ``Expected_Demand``) without
    touching the shared ``_PANEL_METRICS`` used by the brief-04/05/07 paths.
    """
    tag, sigma, rho, seed, steps, tail, params, metrics = job
    df = run_single(rho, steps=steps, seed=seed, sigma=sigma, **params)
    steady = df[df.index >= steps - tail].mean()

    row = {"sigma": sigma, "rho": rho, "seed": seed}
    row.update({m: float(steady[m]) for m in metrics})
    return tag, row


def run_grid_panels(
    configs,
    sigmas=SIGMA_SWEEP_B05,
    rhos=RHO_SWEEP_B05,
    seeds=20,
    steps=DEFAULT_STEPS,
    tail=50,
    workers=None,
    metrics=None,
):
    """Run several (sigma, rho) panels that differ only in ``params``, in ONE pool.

    ``configs`` is a list of ``params`` dicts, each forwarded to :class:`MacroModel` as
    ``**params`` (e.g. ``{"c0": 1.0, "eta": 0.0, "expectation_gain": 0.25}``).  Returns a
    list of per-seed panels, one per config, **in the same order** as ``configs``.

    WHY ONE POOL (the single-pool correction, brief 08 §4).  Calling :func:`run_grid_panel`
    once per config spawns one ``ProcessPoolExecutor`` per config; on Windows every worker
    is a fresh interpreter that re-imports numpy/pandas/mesa, so N configs pay N import
    storms and briefly oversubscribe the cores at each teardown/spawn.  Pooling every
    config's cells into a single job list pays that cost once.  Determinism is unchanged:
    each cell is seeded and shares no state, so the pooling and the ordering cannot move a
    result (the regrouping re-sorts by (sigma, rho, seed) within each config).

    ``metrics`` overrides the collected reporters (default :data:`_PANEL_METRICS`); pass
    ``_PANEL_METRICS + ["Expected_Demand"]`` for the brief-08 convergence diagnostic
    without perturbing the shared list the other briefs' byte-checks rely on.
    """
    metrics = list(_PANEL_METRICS) if metrics is None else list(metrics)
    jobs = [
        (tag, sigma, rho, seed, steps, tail, params, metrics)
        for tag, params in enumerate(configs)
        for sigma in sigmas
        for rho in rhos
        for seed in range(seeds)
    ]

    if workers == 1:
        results = [_panel_job_tagged(j) for j in jobs]
    else:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_panel_job_tagged, jobs, chunksize=1))

    buckets = {tag: [] for tag in range(len(configs))}
    for tag, row in results:
        buckets[tag].append(row)
    return [
        pd.DataFrame(buckets[tag]).sort_values(
            ["sigma", "rho", "seed"], ignore_index=True
        )
        for tag in range(len(configs))
    ]


# ======================================================================
# Global sensitivity analysis (brief 13)
# ======================================================================

#: The treatment: every design point is evaluated at BOTH retention ratios and the QoI is
#: the difference.  Both sit inside the canonical viable support (RHO_SWEEP_B05).
SA_RHO_LO, SA_RHO_HI = 0.35, 0.55

#: **The repaired QoI support (brief 14 §1-§2).**  The brief-13 QoI was a two-point CHORD
#: between ``SA_RHO_LO`` and ``SA_RHO_HI``.  Brief 05 had already measured that ``Y(rho)``
#: is U-shaped with the turning point INSIDE the canonical support in 19 of 22 cells, and
#: on a U the sign of a chord depends on where the chord is taken — so the brief-13
#: headline was exact about "the chord [0.35, 0.55] is negative" and NOT about "the
#: derivative is negative".  Brief 14 sweeps four rho values instead.
#:
#: The four points are not arbitrary: they span the canonical support ``RHO_SWEEP_B05``
#: end to end, and they CONTAIN the two brief-13 chord points.  That is what makes the
#: repair auditable — the chord and the OLS slope are then computed from the *same runs*,
#: so any difference between them is the estimator and cannot be a different sample.
SA_RHO_GRID = [0.35, 0.45, 0.55, 0.65]

#: A run counts as collapsed at ``U -> 1`` or ``K -> 0`` (brief 13 §3.2).  Output is not
#: used as the criterion here: it is the numerator of the QoI, and a viability rule
#: written on the QoI itself would build in exactly the correlation the SA measures.
SA_U_COLLAPSE = 0.999
SA_K_COLLAPSE = 1.0

#: Metrics a design point carries out of each run.  ``Capitalist_Consumption`` rides the
#: ``metrics`` override (brief 08) rather than ``_PANEL_METRICS``, so the committed panels
#: keep their exact columns and the brief-05..12 byte-checks still pass.
SA_METRICS = [
    "Output", "Total_Capital", "Investment", "Unemployment_Rate", "Wage_Share",
    "Profit_Share", "Average_Utilization", "Capitalist_Consumption", "Tax_Rate",
    "Consumption", "Employment", "Wage_Rate", "Money_Buffer",
]


def _sa_job(job):
    """Run one (point, rho, seed) cell for the SA.  Module-level and picklable.

    Unlike :func:`_panel_job_tagged` the whole parameter vector — ``sigma`` included —
    travels inside ``params``, because in the SA *every* design point has its own sigma.
    ``run_grid_panels`` shares a single ``sigmas`` list across its configs, so it cannot
    express that; the single-pool discipline is kept, the grid abstraction is not.
    """
    idx, rho, seed, steps, tail, params, metrics = job
    df = run_single(rho, steps=steps, seed=seed, **params)
    steady = df[df.index >= steps - tail].mean()

    row = {"point": idx, "rho": rho, "seed": seed}
    row.update({m: float(steady[m]) for m in metrics})
    return row


def run_design_points(
    points,
    rho_lo=SA_RHO_LO,
    rho_hi=SA_RHO_HI,
    seeds=5,
    steps=DEFAULT_STEPS,
    tail=50,
    workers=None,
    metrics=None,
    rhos=None,
):
    """Evaluate SA design points at several retention ratios, in ONE process pool.

    ``points`` is a list of ``MacroModel`` kwarg dicts (one per row of the SALib sample).
    Returns the raw per-(point, rho, seed) frame; :func:`qoi_from_runs` reduces it.

    **Common random numbers.** Every point is run at the SAME seeds ``0..seeds-1`` at BOTH
    rho values.  This is not a detail: the QoI is a *difference* of two noisy quantities,
    and with independent seeds that difference is noise on noise — the Sobol indices would
    then largely decompose the variance of the seed draw rather than of the parameters.
    Pairing the seeds cancels the common component, which is why the difference is taken
    per seed and averaged afterwards (see :func:`qoi_from_runs`), never as a difference of
    means over unrelated draws.

    ``rhos`` (brief 14) overrides the two-point support with an arbitrary list — pass
    :data:`SA_RHO_GRID` for the repaired, four-point QoI.  It defaults to ``None``, which
    reproduces the brief-13 two-point behaviour EXACTLY, so the committed brief-13
    artifacts stay regenerable from this same function.
    """
    metrics = list(SA_METRICS) if metrics is None else list(metrics)
    rhos = (rho_lo, rho_hi) if rhos is None else tuple(rhos)
    jobs = [
        (idx, rho, seed, steps, tail, params, metrics)
        for idx, params in enumerate(points)
        for rho in rhos
        for seed in range(seeds)
    ]

    if workers == 1:
        rows = [_sa_job(j) for j in jobs]
    else:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(_sa_job, jobs, chunksize=4))

    return pd.DataFrame(rows).sort_values(["point", "rho", "seed"], ignore_index=True)


def qoi_from_runs(runs, rho_lo=SA_RHO_LO, rho_hi=SA_RHO_HI,
                  u_collapse=SA_U_COLLAPSE, k_collapse=SA_K_COLLAPSE,
                  rhos=None):
    """Reduce raw SA runs to one row of QoIs per design point.

    Returns, per point:

    ``slope_raw``
        ``(Y_hi - Y_lo) / (rho_hi - rho_lo)`` per seed, then averaged — the CRN estimator,
        **as measured, at every point including the collapsed ones**.  It is a real
        measurement everywhere: when both rho values collapse, Y is ~0 at both and the
        difference is genuinely ~0; when only one collapses, the large value records
        retention pushing the economy over the viability cliff.  That mixture is exactly
        why ``viable`` is a separate QoI — but because ``slope_raw`` needs no imputation
        and no subsetting, it is the quantity the variance decomposition can use without
        breaking the Morris trajectory structure or the Saltelli matrix.
    ``slope``
        The same number, but ``NaN`` where the point is not viable — the *conditional*
        response, for descriptive statistics on the viable subset.  Never imputed:
        brief 13 §3 asks for the restriction to be reported, not patched.
    ``slope_seed_sd``
        Inter-seed standard deviation of that per-seed slope.  Reported ALONGSIDE the
        sensitivity indices (§3), so a reader can see how much of the spread is seed
        noise before reading anything into a parameter.
    ``viable``
        1.0 when neither rho collapsed.  This is a QoI in its own right, evaluated on ALL
        points; the slope analysis is conditional on it, and the conditioning is a
        declared limitation of the design, not something to correct away.
    ``wage_led``
        1.0 when ``slope < 0`` (viable points only) — the indicator ``P(dY/drho < 0)``
        averages.
    Levels at both rho values are carried through with ``_lo``/``_hi`` suffixes.

    **Brief 14: the repaired QoI.**  Passing ``rhos`` (e.g. :data:`SA_RHO_GRID`) switches
    the estimator from the two-point chord to an **OLS slope over the whole support**,
    which is the estimator brief 07 used to identify ``sigma*`` — so the SA and the
    frontier finally measure the same thing.  When ``rhos`` is given:

    * ``slope_raw`` / ``slope`` / ``wage_led`` become the **OLS** quantities.  They keep
      their names on purpose: everything downstream (Morris, Saltelli, the summaries)
      then reads the repaired QoI through the same column, so the *only* thing that
      changes between the brief-13 and brief-14 index sets is the QoI itself — which is
      precisely the comparison brief 14 §3 asks to be able to make.
    * ``chord_raw`` / ``chord`` / ``wage_led_chord`` carry the brief-13 estimator computed
      **from the same runs**, so the two can be contrasted without a second simulation.
    * ``rho_star`` is the turning point of the quadratic fit (brief 05's
      :func:`quadratic_curvature`) on the seed-mean ``Y(rho)`` curve, with
      ``rho_star_in_support`` recording whether it lands inside the swept range.  Outside
      the range the U is *not resolved* there and the value is reported as such rather
      than extrapolated (brief 14 §2).
    * ``viable`` is evaluated over ALL swept rho values, so it is **not** comparable to
      the brief-13 number by construction: a wider support gives collapse more chances.
      ``viable_chord`` restricts viability to the two brief-13 rho values, which is the
      column that IS comparable to the committed 0.483.

    With ``rhos=None`` (the default) every one of these is absent and the function
    reproduces the brief-13 behaviour exactly.
    """
    out = []
    swept = None if rhos is None else [float(r) for r in rhos]
    for idx, block in runs.groupby("point"):
        lo = block[block["rho"] == rho_lo].set_index("seed").sort_index()
        hi = block[block["rho"] == rho_hi].set_index("seed").sort_index()

        # CRN: the seeds must pair up, or the difference is not the estimator we mean.
        if list(lo.index) != list(hi.index):
            raise ValueError(f"point {idx}: seeds do not pair across rho (CRN broken)")

        def _dead_at(frame):
            return ((frame["Unemployment_Rate"] >= u_collapse)
                    | (frame["Total_Capital"] < k_collapse))

        chord_dead = _dead_at(lo) | _dead_at(hi)
        # A point is viable when NO seed collapsed at any swept rho; the mixed case (some
        # seeds alive) is recorded rather than rounded, because in this model a mixed
        # point is a basin boundary — the very thing the viability QoI is looking for.
        frac_dead = float(chord_dead.mean())
        viable = frac_dead == 0.0

        chord_per_seed = (hi["Output"].to_numpy() - lo["Output"].to_numpy()) / (rho_hi - rho_lo)
        raw = float(np.mean(chord_per_seed))
        raw_sd = (float(np.std(chord_per_seed, ddof=1))
                  if len(chord_per_seed) > 1 else float("nan"))
        row = {
            "point": int(idx),
            "viable": float(viable),
            "frac_seeds_collapsed": frac_dead,
            "slope_raw": raw,
            "slope_raw_seed_sd": raw_sd,
            "slope": raw if viable else float("nan"),
            "slope_seed_sd": raw_sd if viable else float("nan"),
            "n_seeds": int(len(chord_per_seed)),
        }
        row["wage_led"] = float(raw < 0.0) if viable else float("nan")
        row["wage_led_raw"] = float(raw < 0.0)

        if swept is not None:
            # --- brief 14: OLS over the full swept support, same runs as the chord ---
            frames = []
            for r in swept:
                f = block[block["rho"] == r].set_index("seed").sort_index()
                if list(f.index) != list(lo.index):
                    raise ValueError(
                        f"point {idx}: seeds do not pair at rho={r} (CRN broken)")
                frames.append(f)

            dead_any = chord_dead.copy()
            for f in frames:
                dead_any = dead_any | _dead_at(f)
            frac_dead_all = float(dead_any.mean())
            viable_all = frac_dead_all == 0.0

            # Y[rho, seed]; the OLS slope is a fixed linear functional of the rho axis, so
            # it is applied per seed and averaged — the same CRN discipline as the chord,
            # not a regression on seed-averaged points.
            Y = np.vstack([f["Output"].to_numpy() for f in frames])
            w = _ols_weights(swept)
            ols_per_seed = w @ Y
            ols = float(np.mean(ols_per_seed))
            ols_sd = (float(np.std(ols_per_seed, ddof=1))
                      if ols_per_seed.size > 1 else float("nan"))

            # The turning point of the U, fitted on the seed-mean curve (brief 05's
            # convention for quadratic_curvature, kept so the two are comparable).
            quad, quad_se, turn = quadratic_curvature(swept, Y.mean(axis=1))
            in_support = bool(np.isfinite(turn) and min(swept) <= turn <= max(swept))

            row.update({
                # the chord, preserved under its own name, from these same runs
                "chord_raw": raw,
                "chord": raw if viable else float("nan"),
                "wage_led_chord": float(raw < 0.0) if viable else float("nan"),
                "viable_chord": float(viable),
                # the repaired QoI takes over the primary column names
                "viable": float(viable_all),
                "frac_seeds_collapsed": frac_dead_all,
                "slope_raw": ols,
                "slope_raw_seed_sd": ols_sd,
                "slope": ols if viable_all else float("nan"),
                "slope_seed_sd": ols_sd if viable_all else float("nan"),
                "wage_led": float(ols < 0.0) if viable_all else float("nan"),
                "wage_led_raw": float(ols < 0.0),
                "rho_star": turn,
                "rho_star_in_support": float(in_support),
                "quad_coef": quad,
                "quad_coef_se": quad_se,
                "n_rho": len(swept),
            })

        for name, frame in (("lo", lo), ("hi", hi)):
            for m in frame.columns:
                if m in ("point", "rho"):
                    continue
                row[f"{m}_{name}"] = float(frame[m].mean())
        out.append(row)

    return pd.DataFrame(out).sort_values("point", ignore_index=True)


def cells_from_panel(panel, collapse_y=COLLAPSE_Y):
    """Collapse a per-seed panel to one row per (sigma, rho) cell.

    A cell is ``collapsed`` when its **mean** output is below ``collapse_y`` — the
    brief-04 rule, kept so the two paths agree.  ``frac_seeds_collapsed`` is reported
    alongside: the model has multiple equilibria, so a cell can be *mixed* (some seeds
    alive, some dead), and a mixed cell is a basin boundary — a finding, not noise.
    Averaging it into a mean would hide exactly the thing worth seeing.
    """
    metrics = [c for c in panel.columns if c not in ("sigma", "rho", "seed")]
    g = panel.groupby(["sigma", "rho"], as_index=False)

    cells = g[metrics].mean()
    ymin = g["Output"].min().rename(columns={"Output": "Y_seed_min"})
    ymax = g["Output"].max().rename(columns={"Output": "Y_seed_max"})
    nseed = g["seed"].nunique().rename(columns={"seed": "n_seeds"})

    dead = panel.assign(_dead=panel["Output"] < collapse_y)
    frac = dead.groupby(["sigma", "rho"], as_index=False)["_dead"].mean()
    frac = frac.rename(columns={"_dead": "frac_seeds_collapsed"})

    for extra in (ymin, ymax, nseed, frac):
        cells = cells.merge(extra, on=["sigma", "rho"])

    cells["collapsed"] = cells["Output"] < collapse_y
    cells["mixed_basin"] = (cells["frac_seeds_collapsed"] > 0.0) & (
        cells["frac_seeds_collapsed"] < 1.0
    )
    cells["Y_band_rel"] = np.where(
        cells["Output"] > 0,
        (cells["Y_seed_max"] - cells["Y_seed_min"]) / cells["Output"],
        np.nan,
    )
    bound_cols = list(_BOUND_COLS)
    cells["binding"] = [
        "collapsed" if row["collapsed"]
        else _BOUND_COLS[max(bound_cols, key=lambda c: row[c])]
        for _, row in cells.iterrows()
    ]
    return cells.rename(columns={"Output": "Y", "Total_Capital": "K"})


def common_viable_support(cells, rhos=None):
    """The rho values that are viable **for every sigma** in the grid.

    Slopes taken on different rho supports are not comparable across sigma: sigma
    would be confounded with which rho values survived.  So the support is intersected
    down to the rho values alive everywhere, and that common support is used for every
    sigma — and reported, because it may differ between c0 (the viability threshold can
    move with demand).
    """
    rhos = sorted(cells["rho"].unique()) if rhos is None else rhos
    return [
        rho for rho in rhos
        if not cells.loc[cells["rho"] == rho, "collapsed"].any()
    ]


# --- derivatives ------------------------------------------------------

def ols_slope(x, y):
    """Least-squares slope of ``y`` on ``x``, with its standard error.

    Replaces the centred finite difference of brief 04.  A finite difference on
    ``Delta rho = 0.1`` throws away every point but two and inherits the full inter-seed
    noise of both; the OLS slope uses the whole support and reports what it does not
    know.  Returns ``(nan, nan)`` when the slope is not defined (< 2 points, or no
    variation in x); the SE alone is ``nan`` at exactly 2 points (no residual dof).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = x.size
    if n < 2 or n != y.size:
        return float("nan"), float("nan")

    xc = x - x.mean()
    sxx = float((xc * xc).sum())
    if sxx <= 0.0:
        return float("nan"), float("nan")

    slope = float((xc * (y - y.mean())).sum() / sxx)
    if n == 2:
        return slope, float("nan")

    resid = y - (y.mean() + slope * xc)
    se = math.sqrt(float((resid * resid).sum()) / (n - 2) / sxx)
    return slope, se


def slopes_by_sigma(cells, support, column="Y"):
    """OLS slope of ``column`` on rho, per sigma, over the common viable support.

    One number per sigma — the rho dimension is spent buying precision.  This is what
    identifies ``sigma*`` best; :func:`sweep_derivatives` remains available for the
    local, rho-by-rho picture.
    """
    rows = []
    for sigma, block in cells.groupby("sigma"):
        b = block[block["rho"].isin(support)].sort_values("rho")
        slope, se = ols_slope(b["rho"], b[column])
        rows.append({
            "sigma": sigma,
            f"d{column}_drho": slope,
            "se": se,
            "t": slope / se if se and np.isfinite(se) and se > 0 else float("nan"),
            "n_points": len(b),
            "rho_min": b["rho"].min() if len(b) else float("nan"),
            "rho_max": b["rho"].max() if len(b) else float("nan"),
        })
    return pd.DataFrame(rows).sort_values("sigma", ignore_index=True)


def quadratic_curvature(x, y):
    """Second-order coefficient of ``y = a + b*x + c*x**2`` by OLS, with its turning point.

    Brief 05 §11.3: a single OLS *slope* of Y on rho is "precise and wrong" where Y(rho)
    is visibly curved — it fits a straight line to a parabola and hands back a confident
    number for a quantity that turns sign inside the support.  This fits the parabola and
    returns the curvature ``c``, its standard error, and the turning point ``x* = -b/(2c)``
    where ``dy/dx`` changes sign.  The caller decides ``turn_in_support`` (whether ``x*``
    lands inside the swept range), i.e. whether the sign change is *observed* rather than
    extrapolated.

    Returns ``(quad_coef, se, turning_x)``.  ``se`` is ``nan`` at fewer than four points
    (a three-parameter fit has no residual dof at n = 3); all three are ``nan`` when the
    design is rank-deficient or the curvature is exactly zero.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = x.size
    if n < 3 or n != y.size:
        return float("nan"), float("nan"), float("nan")

    X = np.vstack([np.ones(n), x, x * x]).T
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return float("nan"), float("nan"), float("nan")

    beta = XtX_inv @ (X.T @ y)
    b, c = float(beta[1]), float(beta[2])
    if c == 0.0:
        return float("nan"), float("nan"), float("nan")
    turning = -b / (2.0 * c)
    if n == 3:
        return c, float("nan"), turning

    resid = y - X @ beta
    s2 = float(resid @ resid) / (n - 3)
    se = math.sqrt(s2 * float(XtX_inv[2, 2]))
    return c, se, turning


def _ols_weights(x):
    """Weights ``w`` such that ``w @ y`` is the OLS slope of y on x.

    Lets the bootstrap take 2000 x 11 slopes as one matrix product instead of 22000
    regressions.
    """
    x = np.asarray(x, dtype=float)
    xc = x - x.mean()
    return xc / float((xc * xc).sum())


def _gradient_weights(x):
    """Matrix ``G`` such that ``G[j] @ y`` is ``numpy.gradient(y, x)[j]``.

    The brief-04 derivative — a centred finite difference — is a *linear* operator on
    ``y``, exactly as the OLS slope is.  Recovering it as a matrix (by applying
    ``numpy.gradient`` to each basis vector) lets the local, rho-by-rho derivative and
    the global OLS slope share one bootstrap: the estimator is just a different weight
    vector.  ``sigma*(rho)`` (brief §11.3) and the identified ``sigma*`` (brief §3.2.3)
    are then the same computation, not two code paths that could disagree.
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    G = np.empty((n, n))
    for k in range(n):
        basis = np.zeros(n)
        basis[k] = 1.0
        G[:, k] = np.gradient(basis, x)
    return G


def sigma_star_interp(sigmas, slopes):
    """Linearly interpolate where ``slope(sigma)`` first crosses zero.

    Returns ``(sigma_star, n_crossings)``.  ``sigma_star`` is ``nan`` when the sign
    never turns inside the tested range — which is a *result*, not a failure, and is
    counted rather than dropped (brief 05 §3.2.4).  Scanning upward and taking the
    FIRST crossing is a declared convention; ``n_crossings > 1`` means the frontier is
    not a single locus and the point estimate is hiding structure.
    """
    s = np.asarray(sigmas, dtype=float)
    d = np.asarray(slopes, dtype=float)

    star, crossings = float("nan"), 0
    for i in range(s.size - 1):
        d0, d1 = d[i], d[i + 1]
        if not (np.isfinite(d0) and np.isfinite(d1)) or d0 == d1:
            continue
        if (d0 < 0.0) != (d1 < 0.0):
            crossings += 1
            if crossings == 1:
                star = float(s[i] - d0 * (s[i + 1] - s[i]) / (d1 - d0))
    return star, crossings


def _panel_cube(panel, sigmas, support, column="Output"):
    """``panel`` -> array ``[sigma, rho, seed]`` of ``column``, plus the seed labels."""
    seeds = sorted(panel["seed"].unique())
    cube = np.full((len(sigmas), len(support), len(seeds)), np.nan)
    idx = panel.set_index(["sigma", "rho", "seed"])[column]
    for i, sigma in enumerate(sigmas):
        for j, rho in enumerate(support):
            for k, seed in enumerate(seeds):
                cube[i, j, k] = idx.loc[(sigma, rho, seed)]
    return cube, seeds


def bootstrap_sigma_star(
    panel,
    support,
    column="Output",
    weights=None,
    n_resamples=2000,
    rng_seed=20260717,
    ci=95.0,
):
    """Percentile bootstrap CI for ``sigma*``, resampling **seeds**.

    The seed indexes an independent run of the whole economy, so it is the resampling
    unit; the same resampled seed set is applied to every cell, which preserves the
    paired structure across the grid (cell-by-cell resampling would break the
    comparison that ``sigma*`` is made of).  The **support is held fixed** at the
    full-sample common viable support: it is part of the estimator's definition, not a
    quantity re-estimated inside each resample.

    ``weights`` selects the derivative estimator — any linear one.  ``None`` (default)
    is the OLS slope over the whole support (brief §3.2.3); passing a row of
    :func:`_gradient_weights` gives the local, rho-by-rho finite difference of brief 04.

    Returns a dict with the point estimate, the percentile CI, and — the number that
    decides whether any of this is reportable — ``frac_undefined``: the share of
    resamples in which the sign never turns in the tested sigma range.  Those are
    counted, never silently dropped: a high fraction *is* the result.

    Deterministic given ``rng_seed``.
    """
    sigmas = sorted(panel["sigma"].unique())
    cube, seeds = _panel_cube(panel, sigmas, support, column=column)
    n_seeds = len(seeds)

    w = _ols_weights(support) if weights is None else np.asarray(weights, dtype=float)
    point_slopes = cube.mean(axis=2) @ w
    point_star, point_crossings = sigma_star_interp(sigmas, point_slopes)

    rng = np.random.default_rng(rng_seed)
    draws = rng.integers(0, n_seeds, size=(n_resamples, n_seeds))

    stars = np.empty(n_resamples)
    crossings = np.empty(n_resamples, dtype=int)
    for b in range(n_resamples):
        means = cube[:, :, draws[b]].mean(axis=2)   # (S, R)
        stars[b], crossings[b] = sigma_star_interp(sigmas, means @ w)

    defined = stars[np.isfinite(stars)]
    lo = hi = float("nan")
    if defined.size:
        half = (100.0 - ci) / 2.0
        lo = float(np.percentile(defined, half))
        hi = float(np.percentile(defined, 100.0 - half))

    return {
        "sigma_star": point_star,
        "n_crossings": point_crossings,
        "ci_lo": lo,
        "ci_hi": hi,
        "ci_level": ci,
        "frac_undefined": float(np.mean(~np.isfinite(stars))),
        "frac_multi_crossing": float(np.mean(crossings > 1)),
        "n_resamples": n_resamples,
        "n_seeds": n_seeds,
        "support": list(support),
        "sigma_grid": list(sigmas),
        "rng_seed": rng_seed,
        "slopes": dict(zip(sigmas, point_slopes.tolist())),
        # Share of resamples putting sigma* above the empirical range 0.40-0.60: the
        # number the headline turns on (brief 05 §11.3).  Conditional on sigma* being
        # defined, so read it next to frac_undefined, never instead of it.
        "frac_star_above_0_60": float(np.mean(defined > 0.60)) if defined.size else float("nan"),
        "frac_star_above_0_40": float(np.mean(defined > 0.40)) if defined.size else float("nan"),
    }


def sigma_star_by_rho(panel, support, column="Output", **kw):
    """``sigma*(rho)`` with a bootstrap CI at each rho — the brief-04 view, identified.

    Same estimator as brief 04 (a centred finite difference along rho), same grid
    logic, but on the denser rho support and with an error bar attached.  Reported
    alongside the single OLS-slope ``sigma*``: this one shows how the frontier moves
    with rho, the OLS one spends the rho dimension on precision instead.
    """
    G = _gradient_weights(support)
    rows = []
    for j, rho in enumerate(support):
        bs = bootstrap_sigma_star(panel, support, column=column, weights=G[j], **kw)
        rows.append({
            "rho": rho,
            "sigma_star": bs["sigma_star"],
            "ci_lo": bs["ci_lo"],
            "ci_hi": bs["ci_hi"],
            "frac_undefined": bs["frac_undefined"],
            "frac_multi_crossing": bs["frac_multi_crossing"],
            "n_crossings": bs["n_crossings"],
            # The two numbers that decide the headline at this rho: whether the
            # empirical range 0.40-0.60 sits below sigma*(rho) (profit-led) or above
            # it (wage-led).  Brief 05 §11.3.
            "P_star_gt_0.60": bs["frac_star_above_0_60"],
            "P_star_gt_0.40": bs["frac_star_above_0_40"],
        })
    return pd.DataFrame(rows)


# ======================================================================
# Reproducibility criterion for the nesting checks (brief 14, task D)
# ======================================================================

#: **The retired criterion.** Briefs 07-13 declared a nesting check PASS only at
#: ``max_abs_dev == 0.0`` — exact byte equality against the committed panels.  Brief 13
#: §7.3(a) then MEASURED that this criterion is not reproducible across time: the code at
#: commit ``7c2670f``, whose own check reported *7/7 PASS, dev = 0.0*, deviates by 1 ULP
#: from its own committed results when re-run later.  Eight hypotheses were excluded by
#: measurement (reporters, ``u_min``, the pandas reduction, brief-13 edits via checkout,
#: pool vs main process, ``scipy``, P-core vs E-core scheduling, library versions) and the
#: cause was NOT identified.  The measured envelope over 160 cells x 24 metrics was
#: **max 2.1 ULP, non-amplifying, with zero regime flips**.
#:
#: The criterion is therefore RETIRED WITH MEASUREMENT BEHIND IT, not loosened for
#: convenience — and it is replaced here, in a brief that does not itself violate it,
#: rather than rewritten inside the brief that found it wanting (which would be post hoc).
#:
#: The replacement is deliberately two-part, because the two halves answer different
#: questions and must not be traded off against each other:
#:
#: 1. a declared NUMERICAL tolerance, :data:`BYTE_CHECK_ULP`, on the continuous metrics;
#: 2. a REGIME check at tolerance **exactly zero** (:func:`regime_signature`).  A drift
#:    that moves a level in the 15th digit is a floating-point fact; a drift that flips a
#:    cell from viable to collapsed, or changes which constraint binds, is a scientific
#:    one.  Only the second can move a conclusion, so only the second keeps zero tolerance.
#:
#: 8 ULP = ~4x the measured 2.1 ULP envelope.  The margin is a judgement, and it is
#: declared as one: large enough that the unidentified cause has room to be somewhat worse
#: on cells brief 13 did not sample, small enough that it cannot absorb a real change (the
#: smallest genuine perturbation this model produces — one different RNG draw — moves
#: steady-state metrics by O(1e-3) relative, i.e. ~1e13 ULP).  It is a CONSTANT here, in
#: the source, so it cannot be chosen per run.
BYTE_CHECK_ULP = 8

#: Absolute floor, below which a difference is not counted at all.  **This is not padding
#: — a pure ULP criterion is unusable without it**, and brief 14 measured why.  ULP
#: distance is a RELATIVE measure, so it blows up wherever the compared value is near
#: zero: on the brief-13 QoI frame, ``Tax_Rate_hi`` shows 3 460 ULP on an absolute gap of
#: 1.7e-16, purely because ``rr = 0`` puts many points at a tax rate of exactly 0.  The
#: same happens to any metric that legitimately rests at zero (``Money_Buffer``, capital
#: in a collapsed cell at 8e-40).  1e-12 sits far below the O(1e-6) absolute gap that the
#: smallest REAL divergence in this model produces, and above the ~1e-13 accumulation
#: noise of the reduction, so it separates the two without straddling either.
BYTE_CHECK_ATOL = 1e-12

#: **Declared scope, and the limit that comes with it.**  This criterion applies to
#: MEASURED LEVELS — the panel metrics the b07-b13 nesting checks compare.  It must NOT be
#: applied to differenced or fitted quantities (a chord, an OLS slope, a curvature): those
#: subtract numbers of similar size, so catastrophic cancellation makes their relative
#: error arbitrarily large from a stable input.  Measured, not asserted: on the brief-13
#: Sobol QoIs ``slope_raw`` deviates by 3 410 ULP while its inputs deviate by 4 ULP and its
#: own absolute gap is 3.4e-13.  A tolerance able to pass that number would be too loose to
#: mean anything on the levels.
#:
#: Derived quantities are therefore checked by the REGIME limb instead — the sign of the
#: slope, at tolerance zero — which is the property that can actually move a conclusion.
BYTE_CHECK_SCOPE = ("levels only; differenced/fitted quantities are checked by sign, "
                    "not by tolerance (catastrophic cancellation)")

#: Columns whose equality is checked at tolerance ZERO, when present.  These are the
#: regime facts: does the cell live, and what binds at the margin.  ``Dead_Firms`` is a
#: brief-10 reporter and only appears in panels that carried it.
REGIME_EXACT_COLUMNS = ["Dead_Firms"]


def ulp_distance(a, b):
    """Distance between ``a`` and ``b`` in units in the last place, elementwise.

    ``np.spacing`` of the larger magnitude is the width of one ULP there, so dividing the
    absolute difference by it expresses the gap in representable steps rather than in
    absolute units — which is the only scale-free way to state a floating-point tolerance
    across metrics whose magnitudes run from 1e-3 (rates) to 1e3 (capital stocks).

    Exact equality returns 0.0, including at zero (where ``np.spacing`` is subnormal) and
    for ``NaN`` against ``NaN`` — a metric that is undefined in both frames agrees, and
    treating that as a difference would fail every check on a collapsed cell.  ``NaN``
    against a number returns ``inf``: that IS a difference, and a categorical one.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    both_nan = np.isnan(a) & np.isnan(b)
    one_nan = np.isnan(a) ^ np.isnan(b)

    with np.errstate(invalid="ignore"):
        diff = np.abs(a - b)
        scale = np.spacing(np.maximum(np.abs(a), np.abs(b)))
        out = np.where(diff == 0.0, 0.0, diff / np.where(scale > 0.0, scale, 1.0))
    return np.where(both_nan, 0.0, np.where(one_nan, np.inf, out))


def regime_signature(frame, collapse_y=COLLAPSE_Y, zero_tol=BYTE_CHECK_ATOL):
    """The discrete facts about a panel that a numerical drift must NEVER move.

    Returns a frame of categorical/boolean columns, compared at tolerance zero:

    ``collapsed``
        ``Output < collapse_y`` — viability, the primary regime fact.
    ``binding``
        which of the four constraints has the largest share of periods (the
        :data:`_BOUND_COLS` argmax) — *which* margin the economy is on.
    ``sign_*``
        the sign of every metric present, as -1/0/+1.  A sign flip is qualitative even
        when the magnitude is tiny — but only once the magnitude is RESOLVABLE.  Values
        within ``zero_tol`` of zero are signed 0, because a metric that legitimately rests
        at zero (``Tax_Rate`` at ``rr = 0``, ``Money_Buffer`` every period, capital in a
        collapsed cell) would otherwise flip between +1 and -1 on 1e-16 of arithmetic
        noise and fire this limb on every run.  That is the same measured problem
        :data:`BYTE_CHECK_ATOL` exists for, and it is answered the same way: the regime
        limb keeps ZERO tolerance on the facts it checks, and simply does not claim a
        sign it cannot resolve.
    plus any of :data:`REGIME_EXACT_COLUMNS` the frame carries, verbatim.

    Note what is deliberately NOT here: the sign of ``dY/drho``.  That is a property of a
    *fitted slope across cells*, not of a row, so it is checked by the callers that have
    the fit (the drivers' nesting checks), not by this row-wise signature.
    """
    out = pd.DataFrame(index=frame.index)
    if "Output" in frame.columns:
        out["collapsed"] = frame["Output"] < collapse_y

    bound_cols = [c for c in _BOUND_COLS if c in frame.columns]
    if bound_cols:
        out["binding"] = frame[bound_cols].idxmax(axis=1)

    for col in frame.columns:
        if frame[col].dtype.kind in "fi":
            v = frame[col].to_numpy(dtype=float)
            # NaN has no sign; encode it as its own level (-9) rather than letting the
            # cast to int produce a platform-dependent value.  Unresolvable magnitudes
            # are signed 0 (see the docstring), not forced to +/-1.
            s = np.where(np.isnan(v), -9,
                         np.where(np.abs(np.nan_to_num(v)) <= zero_tol, 0.0,
                                  np.sign(np.nan_to_num(v)))).astype(int)
            out[f"sign_{col}"] = s
    for col in REGIME_EXACT_COLUMNS:
        if col in frame.columns:
            out[col] = frame[col]
    return out


def compare_artifacts(mine, ref, ulp_tol=BYTE_CHECK_ULP, atol=BYTE_CHECK_ATOL,
                      collapse_y=COLLAPSE_Y):
    """Compare a regenerated frame against a committed one under the brief-14 criterion.

    Both frames must already be aligned (same shape, same column order, same row order):
    alignment is the caller's job because only the caller knows the key.

    The numerical limb passes an element when ``|a - b| <= atol + ulp_tol * ULP``, i.e. a
    hybrid absolute/relative tolerance.  Both halves are needed and neither is slack: the
    relative half is what makes one number comparable across metrics of different
    magnitude, the absolute half is what stops a metric legitimately sitting at zero from
    registering thousands of ULP on a gap of 1e-16 (see :data:`BYTE_CHECK_ATOL`).  Read
    :data:`BYTE_CHECK_SCOPE` before pointing this at anything that is not a level.

    Returns a dict with ``max_ulp`` and ``max_abs_dev`` (both reported whether or not they
    pass), ``byte_equal`` — **the retired criterion, still computed and recorded** so the
    change of standard stays visible in every artifact rather than quietly disappearing —
    ``n_exceed`` (elements failing the numerical limb), the regime limb, and ``ok``.

    ``ok`` requires BOTH limbs: within tolerance on the numbers AND exact on the regime.
    A regime difference is a FINDING at any ULP distance; a numerical difference beyond
    tolerance is a FINDING even with the regime intact.
    """
    num = [c for c in ref.columns
           if ref[c].dtype.kind in "fi" and c in mine.columns
           and mine[c].dtype.kind in "fi"]
    a = mine[num].to_numpy(dtype=float)
    b = ref[num].to_numpy(dtype=float)

    ulp = ulp_distance(a, b)
    with np.errstate(invalid="ignore"):
        diff = np.abs(a - b)
        allowed = atol + ulp_tol * np.spacing(np.maximum(np.abs(a), np.abs(b)))
        exceed = np.where(np.isnan(diff), ulp > 0.0, diff > allowed)
    n_exceed = int(np.sum(exceed))
    finite = ulp[np.isfinite(ulp)]
    max_ulp = float(finite.max()) if finite.size else 0.0
    max_dev = float(np.nanmax(diff)) if diff.size else 0.0

    # ``max_ulp`` alone is misleading and must never be quoted on its own: it is dominated
    # by elements sitting at or near zero, where a 1e-16 gap is thousands of ULP and means
    # nothing.  This is the drift figure that carries information — the worst relative
    # deviation among elements whose ABSOLUTE gap is big enough to be a real signal — and
    # it is the one to compare against :data:`BYTE_CHECK_ULP`.
    with np.errstate(invalid="ignore"):
        significant = np.isfinite(ulp) & (diff > atol)
    max_ulp_sig = float(ulp[significant].max()) if significant.any() else 0.0

    sig_a = regime_signature(mine, collapse_y=collapse_y, zero_tol=atol)
    sig_b = regime_signature(ref, collapse_y=collapse_y, zero_tol=atol)
    shared = [c for c in sig_b.columns if c in sig_a.columns]
    n_regime_diff = int((sig_a[shared].to_numpy() != sig_b[shared].to_numpy()).sum())

    return {
        "max_ulp": max_ulp,
        "max_ulp_significant": max_ulp_sig,
        "max_abs_dev": max_dev,
        "byte_equal": bool(max_dev == 0.0),
        "n_exceed": n_exceed,
        "n_compared": int(a.size),
        "regime_equal": n_regime_diff == 0,
        "n_regime_diff": n_regime_diff,
        "n_regime_cols": len(shared),
        "ulp_tol": ulp_tol,
        "atol": atol,
        "ok": bool(n_exceed == 0 and n_regime_diff == 0),
    }


def plot_sign_frontier(grid, deriv, path="ces_sign_frontier.png"):
    """Heatmap of ``dY/drho`` over (sigma, rho) with the zero contour drawn."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pivot = deriv.pivot(index="sigma", columns="rho", values="dY_drho")
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    vmax = float(np.nanmax(np.abs(pivot.to_numpy())))
    im = ax.pcolormesh(
        pivot.columns, pivot.index, pivot.to_numpy(),
        cmap="RdBu_r", vmin=-vmax, vmax=vmax, shading="nearest",
    )
    if np.nanmin(pivot.to_numpy()) < 0.0 < np.nanmax(pivot.to_numpy()):
        ax.contour(pivot.columns, pivot.index, pivot.to_numpy(),
                   levels=[0.0], colors="k", linewidths=2)
    fig.colorbar(im, ax=ax, label="dY/drho")
    ax.axhline(1.0, ls="--", lw=1, color="grey")
    ax.set_xlabel("retention ratio rho")
    ax.set_ylabel("elasticity of substitution sigma")
    ax.set_title("Sign of dY/drho  (blue = wage-led, red = profit-led)", weight="bold")

    for sigma, b in deriv.groupby("sigma"):
        b = b.sort_values("rho")
        ax2.plot(b["rho"], b["Y"], marker="o", ms=3, label=f"sigma={sigma}")
    ax2.set_xlabel("retention ratio rho")
    ax2.set_ylabel("steady-state output Y")
    ax2.set_title("Output vs retention, by sigma", weight="bold")
    ax2.legend(fontsize=7, ncol=2)

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path

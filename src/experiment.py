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

#: Steady-state metrics carried from a run into the panel.
_PANEL_METRICS = [
    "Output", "Total_Capital", "Investment", "Consumption", "Employment",
    "Unemployment_Rate", "Wage_Share", "Wage_Share_Profitmax", "Profit_Share",
    "Income_Gini", "Wealth_Gini", "Output_Gap", "Output_Gap_PM",
    "Potential_Output", "Potential_Output_PM", "Average_Utilization",
    "Money_Buffer", "Cash_Constrained",
    "Bound_Demand", "Bound_Profitmax", "Bound_Capital", "Bound_Workforce",
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

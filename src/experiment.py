"""
Reusable experiment harness for the normalised-CES endogenous-investment core.

Centralises the Monte-Carlo plumbing (multi-seed runs, tidy dataframes,
confidence bands and the parameter sweeps) so notebooks and ad-hoc analysis
share one tested code path.

Two experiments live here:

* ``retention_sweep`` — the point-11 sweep over the **retention ratio** ``rho``
  (the share of gross profit firms retain and invest internally), at fixed sigma.
* ``sigma_rho_sweep`` — the brief-04 **two-dimensional (sigma, rho) grid**, whose
  output is the *sign frontier*: the locus where ``dY/drho`` changes sign.  The
  Cobb-Douglas core imposes sigma = 1, which the empirical literature rejects;
  sigma is what sets the strength of capital-labour substitution and therefore the
  sign of the headline result, so it is swept rather than chosen.

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

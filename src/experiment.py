"""
Reusable experiment harness for the Cobb-Douglas endogenous-investment core.

Centralises the Monte-Carlo plumbing (multi-seed runs, tidy dataframes,
confidence bands and the retention-ratio sweep) so notebooks and ad-hoc analysis
share one tested code path.

The headline experiment is a sweep over the **retention ratio** ``rho`` (the
share of gross profit firms retain and invest internally), from the low-capital
baseline ``rho = 0`` to the extended economy ``rho = 0.40``.

Typical use
-----------
>>> from experiment import run_experiment, summarize, retention_sweep
>>> panel = run_experiment(retention_ratio=0.40, steps=2000, seeds=3)
>>> band  = summarize(panel)                       # mean + 95% CI per time step
>>> sweep = retention_sweep([0.0, 0.20, 0.35, 0.40])   # steady-state vs rho
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from model import MacroModel


DEFAULT_STEPS = 2000
DEFAULT_SEEDS = 3
RETENTION_SWEEP = [0.0, 0.20, 0.35, 0.40]


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

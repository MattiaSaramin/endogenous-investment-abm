"""
Reusable experiment harness for the Endogenous-Investment ABM.

Centralises the Monte-Carlo plumbing (multi-seed runs, tidy dataframes,
confidence bands and parameter sweeps) so that notebooks and tests share one
tested code path instead of re-implementing loops.

Typical use
-----------
>>> from experiment import run_experiment, summarize, theta_sweep
>>> panel = run_experiment(theta=0.15, steps=500, seeds=30)
>>> band = summarize(panel)                 # mean + 95% CI per time step
>>> sweep = theta_sweep([0.0, 0.1, 0.2])    # steady-state metrics vs theta
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from model import MacroModel


DEFAULT_STEPS = 500
DEFAULT_SEEDS = 30


def run_single(theta, steps=DEFAULT_STEPS, seed=0, **params):
    """Run one simulation and return its per-step model dataframe.

    Extra keyword arguments are forwarded to :class:`MacroModel`, so any model
    parameter can be overridden per run.
    """
    model = MacroModel(theta=theta, seed=seed, **params)
    for _ in range(steps):
        model.step()

    df = model.datacollector.get_model_vars_dataframe()
    df.index.name = "Step"
    return df


def run_experiment(theta, steps=DEFAULT_STEPS, seeds=DEFAULT_SEEDS, **params):
    """Monte-Carlo a scenario over ``seeds`` replications.

    Returns a long dataframe with a ``Seed`` column and a ``Step`` index,
    suitable for :func:`summarize` or seaborn.
    """
    frames = []
    for seed in range(seeds):
        df = run_single(theta, steps=steps, seed=seed, **params)
        df = df.copy()
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


def theta_sweep(
    thetas,
    steps=DEFAULT_STEPS,
    seeds=DEFAULT_SEEDS,
    tail=50,
    **params,
):
    """Sweep the investment propensity and report steady-state outcomes.

    For each ``theta`` the model is run to (near) steady state and the last
    ``tail`` steps are averaged, then averaged again across seeds.  Returns one
    row per ``theta`` with the headline macro indicators.
    """
    records = []
    for theta in thetas:
        panel = run_experiment(theta, steps=steps, seeds=seeds, **params)
        steady = panel[panel.index >= steps - tail]
        row = steady.drop(columns="Seed").mean().to_dict()
        row["theta"] = theta
        records.append(row)

    cols = ["theta"] + [c for c in records[0] if c != "theta"]
    return pd.DataFrame(records)[cols]

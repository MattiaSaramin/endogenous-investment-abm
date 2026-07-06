# Endogenous Investment and Capital Accumulation in a Heterogeneous Keynesian Agent-Based Model

## Overview

This repository contains an Agent-Based Model (ABM) developed in Python using the Mesa framework.

The model extends the heterogeneous Keynesian Cross introduced by Teglio (2024), *Rationality, inequality, and the output gap: evidence from a disaggregated Keynesian cross diagram*, by incorporating endogenous capital accumulation and investment dynamics.

Where the original model focuses primarily on demand determination under heterogeneous income distribution, this extension investigates how the endogenous conversion of private savings into productive capital influences macroeconomic performance over time.

The objective is **not** to provide a quantitatively calibrated representation of a real economy, but to explore the qualitative macroeconomic consequences of introducing an investment channel into an otherwise demand-driven heterogeneous economy.

---

# Research Question

The model investigates the following question:

> **To what extent can endogenous investment financed by accumulated private savings mitigate demand-constrained stagnation in a heterogeneous Keynesian economy?**

More specifically, it explores the interaction between:

- household consumption behaviour;
- wealth accumulation;
- endogenous investment;
- firm-level capital accumulation;
- productive capacity;
- macroeconomic output;
- income and wealth inequality.

---

# Theoretical Motivation

In the baseline framework, households consume according to a Keynesian consumption function, while firms produce only to satisfy effective demand.

When part of aggregate income is persistently saved rather than spent, aggregate demand becomes insufficient to absorb productive capacity, generating a persistent output gap.

This extension introduces an endogenous investment mechanism through which a fraction of accumulated savings is transformed into productive capital.

The model therefore investigates whether productive investment can partially recycle excess savings back into aggregate demand while simultaneously expanding future production capacity.

---

# Model Structure

The economy consists of three agent types connected through a bipartite network.

## Households

Households:

- supply labour to firms;
- receive wage income;
- accumulate financial wealth;
- consume according to a wealth-dependent Keynesian consumption function

\[
C_i = c_0 + c_1Y_i + \lambda W_i
\]

where

- \(Y_i\) is disposable income,
- \(W_i\) is accumulated wealth,
- \(\lambda\) measures the wealth effect.

---

## Capitalists

Capitalists are households that additionally own firms.

They:

- receive dividend income;
- accumulate savings;
- finance investment in the firms they own.

Investment depends on both available savings and firm utilisation:

\[
I = \theta S \cdot \phi(u)
\]

where

- \(S\) denotes savings,
- \(u\) is productive capacity utilisation,
- \(\theta\) is the investment propensity.

Investment is installed with a one-period delay before becoming productive capital.

---

## Firms

Each firm:

- hires workers;
- receives demand from connected households;
- produces subject to productive capacity;
- distributes revenue between wages and profits;
- accumulates productive capital over time.

Production capacity follows a Cobb-Douglas specification:

\[
Y^{capacity}
=
A K^{\alpha}L^{1-\alpha}
\]

Output is constrained by effective demand:

\[
Y=\min(D,Y^{capacity})
\]

---

# Model Dynamics

Each simulation period follows five sequential stages:

1. Household demand formation
2. Firm production
3. Firm accounting
4. Household accounting
5. Endogenous investment

Investment becomes productive capital in the following period, introducing a realistic installation lag.

---

# Experiments

The repository currently investigates two scenarios.

## Baseline Economy

No endogenous investment:

\[
\theta=0
\]

This reproduces a purely demand-driven Keynesian economy.

---

## Endogenous Investment

A positive fraction of household savings is converted into productive capital:

\[
\theta>0
\]

Comparison between both scenarios allows the macroeconomic effects of endogenous investment to be isolated.

Each experiment is repeated across multiple random seeds in order to reduce stochastic variability.

---

# Collected Macroeconomic Indicators

The model records:

- Aggregate Output
- Aggregate Capital Stock
- Income Gini Coefficient
- Wealth Gini Coefficient
- Average Capacity Utilisation

These indicators allow the interaction between production, investment and distribution to be analysed over time.

---

# Current Limitations

The model intentionally abstracts from several important mechanisms in order to isolate the investment channel.

In particular, it does **not** currently include:

- endogenous prices;
- financial intermediaries;
- credit creation;
- monetary policy;
- fiscal policy;
- labour market search;
- firm entry and exit;
- adaptive expectations.

Future work may incorporate these mechanisms while preserving the existing stock-flow structure.

---

# Repository Structure

```
src/
    agents.py
    model.py

notebooks/
    Endogenous_Investment.ipynb

README.md
```

---

# References

Teglio, A. (2024).

*Rationality, inequality, and the output gap: evidence from a disaggregated Keynesian cross diagram.*

Mesa Documentation

https://mesa.readthedocs.io/

---

# Disclaimer

This project is intended as an exploratory computational economics model.

Its purpose is to investigate the qualitative macroeconomic implications of alternative behavioural assumptions rather than to provide calibrated forecasts or policy prescriptions.
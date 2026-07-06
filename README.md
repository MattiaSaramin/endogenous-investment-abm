# Endogenous Investment and Capital Accumulation in a Heterogeneous Keynesian Agent-Based Model

## Overview

This repository contains an Agent-Based Model (ABM) implemented in Python using the **Mesa** framework.

The model extends the heterogeneous Keynesian Cross proposed by **Teglio (2024)** by introducing an endogenous investment mechanism that transforms accumulated household savings into productive capital.

Where the original framework is primarily demand-driven, this extension investigates the interaction between effective demand, wealth accumulation, investment behaviour, and productive capacity over time.

Rather than attempting to reproduce a real economy quantitatively, the model is intended as an exploratory computational laboratory for studying the qualitative macroeconomic consequences of alternative behavioural assumptions.

---

## Research Question

The project investigates the following question:

> **Can endogenous investment financed through accumulated private savings mitigate demand-constrained stagnation in a heterogeneous Keynesian economy?**

More specifically, the model explores how investment affects:

- aggregate output;
- productive capacity;
- capital accumulation;
- income inequality;
- wealth inequality;
- capacity utilisation.

---

## Economic Motivation

Standard Keynesian models explain fluctuations in output primarily through changes in aggregate demand.

However, persistent private saving simultaneously represents:

- a leakage from aggregate demand;
- a potential source of productive investment.

The model studies this dual role by allowing capital-owning households to reinvest part of their accumulated savings into the firms they own.

Investment therefore performs two macroeconomic functions:

- increasing future productive capacity;
- partially recycling accumulated wealth back into the circular flow of income.

The objective is to analyse how these interacting mechanisms shape long-run macroeconomic dynamics.

---

# Model Overview

The economy consists of three heterogeneous agent types connected through a bipartite network.

- Households
- Capitalists
- Firms

Simulation proceeds in discrete time.

During every period agents interact through labour, consumption, production, income distribution and investment decisions.

---

# Household Behaviour

Households:

- supply labour to firms;
- receive wage income;
- accumulate wealth;
- consume according to a Keynesian consumption function.

Desired consumption is given by

```text
Consumption =
c0 + c1 × Income + λ × Wealth
```

where

- `c0` is autonomous consumption;
- `c1` is the marginal propensity to consume;
- `λ` measures the wealth effect.

Consumption is constrained by available resources.

---

# Capitalist Behaviour

Capitalists are households that additionally own firms.

Besides wage income they receive:

- dividend income;
- ownership wealth.

After consumption, part of their remaining savings is invested into the capital stock of the owned firm.

Investment follows the behavioural rule

```text
Investment =
θ × Savings × Utilisation Adjustment
```

where

- `θ` is the investment propensity;
- savings are disposable income not consumed;
- utilisation adjustment increases investment incentives when firms operate closer to capacity.

Investment is installed with a one-period delay before becoming productive capital.

---

# Firm Behaviour

Firms:

- employ workers;
- receive demand from connected households;
- produce goods;
- pay wages;
- distribute profits to owners;
- accumulate productive capital.

Maximum productive capacity follows a Cobb-Douglas production function

```text
Capacity =
A × K^α × L^(1−α)
```

where

- `A` denotes productivity;
- `K` is capital stock;
- `L` is labour input.

Actual production is demand constrained

```text
Output =
min(Demand, Capacity)
```

ensuring that firms never produce beyond effective demand.

Capital evolves according to

```text
Capital(t+1) =
(1 − δ) × Capital(t)
+ Investment(t)
```

where `δ` is the depreciation rate.

---

# Simulation Sequence

Each simulation period is divided into five ordered stages:

1. Household demand formation
2. Firm production
3. Firm accounting
4. Household accounting
5. Investment and capital accumulation

This sequential structure ensures a consistent timing of income generation, expenditure and investment.

---

# Experimental Design

The current implementation compares two macroeconomic environments.

## Baseline Economy

No endogenous investment.

```text
θ = 0
```

Savings remain idle and do not contribute to future productive capacity.

---

## Endogenous Investment Economy

A positive fraction of accumulated savings is transformed into productive capital.

```text
θ > 0
```

Comparing these two scenarios isolates the macroeconomic effects of endogenous investment.

Each experiment is repeated across multiple random seeds in order to reduce stochastic variability.

---

# Recorded Macroeconomic Indicators

The model currently records:

- Aggregate Output
- Aggregate Capital Stock
- Income Gini Coefficient
- Wealth Gini Coefficient
- Average Capacity Utilisation

These indicators allow both macroeconomic performance and distributional dynamics to be analysed simultaneously.

---

# Repository Structure

```text
src/
│
├── agents.py
├── model.py
│
notebooks/
│
└── Endogenous_Investment.ipynb
│
README.md
```

---

# Current Limitations

The model deliberately abstracts from several important macroeconomic mechanisms in order to isolate the role of endogenous investment.

The current implementation does **not** include:

- endogenous prices;
- banking or financial intermediation;
- credit creation;
- monetary policy;
- fiscal policy;
- firm entry and exit;
- unemployment dynamics;
- adaptive expectations;
- technological change.

These mechanisms may be incorporated in future versions while preserving the existing stock-flow structure.

---

# Future Development

Several extensions are planned, including:

- heterogeneous firm productivity;
- endogenous markups;
- adaptive investment expectations;
- endogenous labour market dynamics;
- firm entry and bankruptcy;
- calibration using empirical macroeconomic data;
- sensitivity analysis through parameter sweeps;
- robustness analysis across alternative network topologies.

---

# References

Teglio, A. (2024).

*Rationality, inequality, and the output gap: Evidence from a disaggregated Keynesian Cross diagram.*

Mesa: Agent-Based Modeling in Python

https://mesa.readthedocs.io/

---

# Disclaimer

This project is an exploratory computational economics model developed for research and educational purposes.

Its objective is to investigate the qualitative implications of alternative behavioural assumptions within a heterogeneous Keynesian framework rather than to provide calibrated forecasts or policy recommendations.
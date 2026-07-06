\# Endogenous Investment and Supply-Side Dynamics: An Extension of the Multi-Agent Keynesian Cross



\## Overview

This repository contains a Python-based Agent-Based Model (ABM) developed using the `Mesa` framework. It builds directly upon the theoretical architecture established in Teglio (2024), \*Rationality, inequality, and the output gap: evidence from a disaggregated Keynesian cross diagram\*. 



While the original baseline model is strictly demand-driven, demonstrating how structural inequality and unspent capitalist wealth permanently drag down aggregate output, this extension introduces endogenous capital accumulation. By transforming idle wealth into productive capital investments, the model explores the dynamic feedback loops between income distribution, firm-level capacity constraints, and macroeconomic recovery.



\## Theoretical Framework

The extension introduces three primary mechanisms to the bipartite network of heterogeneous households and firms:



\### 1. Capitalist Investment

In the baseline model, capitalists accumulate wealth indefinitely when income exceeds their target consumption. Here, an exogenous investment propensity $\\theta \\in (0, 1)$ is introduced. The total investment $i\_f(t)$ injected into firm $f$ at time $t$ by its shareholders $H\_{cap, f}$ is defined as:

$$i\_f(t) = \\sum\_{h \\in H\_{cap, f}} \\theta \\cdot \\max(0, y\_h(t) - c\_h(t))$$



\### 2. Capital Accumulation

Firms transform this financial investment into physical capital. Given a depreciation rate $\\delta \\in (0, 1)$, the capital stock $k\_f(t)$ evolves as:

$$k\_f(t+1) = (1 - \\delta)k\_f(t) + i\_f(t)$$



\### 3. The Modified Production Constraint

The original capacity constraint capped output strictly by the number of workers and a static baseline productivity $\\beta$. This model introduces an elasticity parameter $\\alpha$ and a scaling multiplier $\\gamma$ to reflect diminishing returns to capital. The extended production function is:

$$y\_f(t+1) = \\min\\left\[ z\_f(t), \\beta \\cdot (1 + \\gamma k\_f(t)^\\alpha) \\cdot (1+extra) \\cdot |H\_{Jf}| \\right]$$



To close the macroeconomic loop, aggregate corporate investment $I\_{total}(t)$ is distributed evenly as an additional demand shock across all firms, expanding the total faced demand $Z\_f(t)$.

## Key Findings
The introduction of endogenous capital accumulation fundamentally alters the macroeconomic trajectory. By unlocking the hoarded wealth of both capitalists and workers (via the Pigouvian Wealth Effect), the economy breaks out of the initial depreciation trap. 

As capital stock (K) accumulates, the firm-level capacity constraints expand, allowing aggregate output to scale endogenously while stabilizing structural income inequality.

![Macroeconomic Simulation Results]("C:\Users\recursivechaos\Documents\ABM\macro_results.png")

\## Repository Structure

\* `src/agents.py`: Contains the object-oriented logic for the `Household`, `Capitalist`, and `Firm` agents.

\* `src/model.py`: The macro-level `Mesa` environment handling the bipartite network topology, `StagedActivation` scheduling, and data collection.

\* `notebooks/01\_Endogenous\_Investment.ipynb`: The primary analysis notebook containing time-series visualizations of the output gap and the Gini index.



\## Installation \& Usage

1\. Clone the repository:

&#x20;  `git clone https://github.com/yourusername/abm-endogenous-investment.git`

2\. Install the required dependencies:

&#x20;  `pip install mesa pandas matplotlib seaborn jupyter`

3\. Launch the analysis notebook:

&#x20;  `jupyter notebook notebooks/01\_Endogenous\_Investment.ipynb`


# Endogenous Investment and Capital Accumulation - a Normalised-CES Core with an Endogenous Labour Market

## Overview

This repository contains an Agent-Based Model (ABM) built in Python with the
**Mesa** framework. It extends the heterogeneous Keynesian Cross of **Teglio
(2025)** with **endogenous investment and capital accumulation**, so that both
sides of the economy are endogenous: a **demand** channel that works through
employment, and a **supply** channel that works through capital.

The economy is single-good, fixed-price (numeraire = 1) and
**stock-flow-consistent** (SFC): money is neither created nor destroyed in
settlement. It is an exploratory computational laboratory for the *qualitative*
macroeconomics of alternative behavioural assumptions, not a calibrated forecast.

Production is a **normalised CES** with elasticity of substitution `sigma`
(`sigma = 1` is the Cobb-Douglas core, `sigma -> 0` is Leontief); firms hire
**endogenously** at a wage `w_t` set by a Blanchflower–Oswald **wage curve** on
last period's unemployment (`eta = 0` fixes it at `w_bar` and recovers the
fixed-wage model exactly), and the unemployed earn nothing unless a minimal
**government** is switched on (brief 09: a balanced-budget unemployment benefit,
`benefit_replacement_rate = 0` by default) - so employment drives demand. `sigma`
governs the strength of capital–labour substitution, which is the mechanism that
decides whether the model is wage-led or profit-led.

---

## Research question

> **Can endogenous investment, financed internally by firms, drive output - and
> if so, does it do it by building capital (supply) or by paying wages (demand)?
> The answer depends on how easily capital substitutes for labour.**

The two channels pull in opposite directions:

* **Supply.** More retention `rho` → more investment → more capital → higher CES
  capacity. On its own this raises output.
* **Demand.** In a demand-constrained regime, more capital means *fewer workers
  needed for the same demand* (`L_demand` falls in `K`) → technological
  unemployment → the wage bill and the wage share fall → demand falls (workers
  have a higher marginal propensity to consume than capitalists).

Which dominates is the **wage-led vs profit-led** question, and its answer is set
by `sigma`. This is a research object, not a bug: **a wage-led outcome is a
result, not a failure.**

---

## Model

**Production - normalised CES (Klump & de La Grandville 2000):**

```text
Y* = Y0 * [ pi0*(K/K0)^r + (1-pi0)*(L/L0)^r ]^(1/r),   r = (sigma-1)/sigma
Y  = min(demand, Y*)
```

The base point `(K0, L0)` and base-point capital share `pi0` are the
**normalisation anchor**: a modelling choice, measured once at `sigma = 1`,
`rho = 0.40` and then **frozen** (`model.ANCHOR_K0`, `model.ANCHOR_L0`). `Y0` is
**derived** (`A*K0^pi0*L0^(1-pi0)`), never measured - this is what makes
`sigma = 1` reproduce Cobb-Douglas exactly. The normalisation is a *comparison
device* that makes the `sigma`-variants pass through the same point with the same
factor shares (so two economies differ *only* by `sigma`); it is **not** a claim
of causal identification (Temple 2012 - reported, not hidden).

**Endogenous employment - three limits (roadmap point 11):**

```text
L = min( L_demand, L_profitmax, N )
```

a firm hires the labour needed for expected demand, capped by the profit-max
point (where `MPL = w_bar`), capped by the workforce `N`. The cap `L <= N` is
what restores decreasing returns to capital - without it `L_profitmax` scales
with `K` and `Y*` becomes linear in `K` (an AK model with no steady state).

**Wage curve; profit is the residual:**

```text
w_t          = max( w_min, w_bar * (max(U_{t-1}, U_min)/U_REF)^(-eta) )   (brief 07)
wage_bill    = w_t * L
gross_profit = sales - wage_bill
```

The wage is set by a Blanchflower–Oswald **wage curve** on last period's
unemployment: a *level* relation (not a Phillips *change* relation), so it has a
well-defined steady state for every `U`. `eta = 0` fixes the wage at `w_bar` and
reproduces the earlier model **bit-for-bit**; `eta > 0` (empirical range
~0.07–0.10) lets the wage fall with unemployment. `U_REF` is the unemployment at
which `w = w_bar`, measured once at the anchor scenario and frozen; `w_min` is a
subsistence floor. The wage share is a **measured outcome**, structurally bounded
above by the `sigma`-dependent profit-max wage share (`1 - pi0` only at
`sigma = 1`).

**Internal financing via retained earnings:**

```text
util_effect = max(0, 1 + beta*(u_last - target_utilization))
I_planned   = clip(retention_ratio * profit_last * util_effect, investment_floor, profit)
retained    = I_planned
dividends   = gross_profit - retained
K(t+1)      = (1 - delta)*K(t) + I_delivered
```

The firm cash account (`money_buffer`) is an **intra-period pass-through** and
**returns to zero every period** - no money sequestration. **Conserved quantity
(SFC):** `sum(household wealth + income) + sum(firm money_buffer)` is constant
(deviation < 1e-9).

**Consumption** (worker MPC `c1`, lower capitalist MPC, wealth effect `lambda`,
bounded by money on hand):

```text
C = c0 + mpc*income + lambda*wealth
```

---

## Period sequence

Read directly from `src/model.py`. Employment is set **before** households form
demand (expected income depends on employment); investment settlement precedes
household settlement.

0. **wage determination** (brief 07) - set `w_t` from the wage curve on *last*
   period's unemployment, before the labour market, to avoid the `w <-> U`
   simultaneity within a period (`eta = 0` short-circuits to `w_bar`);
1. **labour market** - firms plan employment, fire the excess into an unemployed
   pool, fill vacancies by random matching → employment;
2. households form consumption demand (income = wage if employed, else 0; plus
   dividends for capitalists);
3. firms plan investment (profit flow, accelerator on last utilisation);
4. firms register demand (consumption + investment);
5. firms produce `Y = min(demand, Y*)`; the goods market rations; utilisation is
   set against **profit-max** capacity;
6. firm accounting: wages, retained (= planned investment), residual dividends;
7. investment settlement: pay for delivered goods, update capital, return the
   residual as dividends so the buffer returns to zero;
8. **government** (brief 09) - a balanced-budget unemployment benefit: a flat tax on
   this period's accrued income funds an equal transfer to the unemployed, after the
   last income accrual and before settlement (`benefit_replacement_rate = 0` default
   skips it, reproducing the pre-brief-09 model bit-for-bit);
9. household settlement: credit income, pay for delivered goods.

---

## Results

All tables are means over **20 seeds**, **2000 steps**, last 50 observations;
`initial_capital = 40` fixed (it selects the basin - see *Interpretive frame*);
default parameters otherwise. Headline runs use `c0 = 1.0`. Numbers are read from
the committed outputs in `results/`, regenerated by `scripts/run_brief05.py`.

### 1. At `sigma = 1` (Cobb-Douglas) the economy is wage-led

Steady-state sweep over the retention ratio at `sigma = 1`, `c0 = 1.0`:

| rho  | Y     | K     | Employment | Unemployment | Wage share | Utilisation |
| ---- | ----- | ----- | ---------- | ------------ | ---------- | ----------- |
| 0.35 | 96.7  | 256.5 | 59.4       | 0.406        | 0.553      | 0.687       |
| 0.40 | 91.1  | 281.0 | 51.9       | 0.481        | 0.513      | 0.591       |
| 0.50 | 87.3  | 346.6 | 43.9       | 0.561        | 0.452      | 0.459       |
| 0.60 | 86.2  | 414.0 | 39.3       | 0.607        | 0.411      | 0.379       |
| 0.65 | 86.8  | 453.2 | 38.0       | 0.620        | 0.394      | 0.349       |

More retention builds capital (256 → 453) but **displaces workers** (employment
59 → 38, unemployment 0.41 → 0.62) and **lowers output** (96.7 → 86.8): the
capital–labour substitution channel dominates. This is the strongest possible
reconnection to Teglio's leakage mechanism - and it holds at exactly the `sigma`
the empirical literature rejects.

![sigma = 1 retention sweep (illustrative 3-seed run): output and unemployment vs rho](retention_sweep.png)

### 2. The sign of `dY/drho` depends on `sigma` - the sign frontier

`sigma*` is where the OLS slope of `Y` on `rho` (over the common viable support,
with a percentile bootstrap CI over 2000 resamples of the seeds) changes sign.
Below `sigma*`, retention raises output; above it, retention lowers output.

| `c0` | target | `sigma*` | 95% CI          | resamples with no sign change | P(`sigma*` > 0.60) |
| ---- | ------ | -------- | --------------- | ----------------------------- | ------------------ |
| 1.0  | Y      | 0.654    | [0.616, 0.691]  | 0 %                           | 99.8 %             |
| 1.0  | U      | 0.314    | [0.300, 0.325]  | 0 %                           | 0 %                |
| 2.0  | Y      | 0.941    | [0.918, 0.963]  | 0 %                           | 100 %              |
| 2.0  | U      | 0.450    | [0.444, 0.456]  | 0 %                           | 0 %                |

* **The empirical range `sigma` 0.40–0.60 (Chirinko 2008; Knoblach et al. 2020)
  sits *below* `sigma*`**, where `dY/drho > 0`: in the empirically supported
  region the model is **not** wage-led on output. The wage-led headline rests on
  `sigma = 1`, which sits *above* `sigma*` and which the data reject.
* **`dU/drho` has a *different* frontier** (`sigma*_U ~ 0.31–0.45`): in the band
  `sigma ~ 0.3–0.7`, output **and** unemployment rise together - growth with
  technological unemployment, which "profit-led" does not describe.

![Sign of dY/drho over the (sigma, rho) grid](ces_sign_frontier.png)

### 3. `sigma*` is a frontier, not a number

`sigma*` moves with what you condition on, and this is reported rather than
reduced to a point estimate:

* **with `rho`** (curvature): `Y(rho)` is significantly curved - the quadratic
  turning point falls inside the support in 19 of 22 `(c0, sigma)` cells, `|t|`
  up to 20.5. A single OLS slope is *precise and wrong*: it fits a line to a
  parabola.
* **with the support**: `sigma*` (c0 = 1.0) ranges from 0.46 (rho 0.35–0.55) to
  0.94 (rho 0.45–0.65).
* **with the anchor** (Temple 2012): moving the normalisation anchor from
  `rho = 0.40` to `rho = 0.50` shifts `sigma*(rho = 0.5)` from 0.84 to 0.64.

### 4. Wage flexibility does not overturn the wage-led result (the wage curve)

A critic can attribute the wage-led result to the *fixed* wage: it suppresses the
offsetting channel `U up -> w down -> labour cheaper -> substitution toward labour
slows`. Brief 07 turns that channel on with a wage curve (`eta` its elasticity)
and re-estimates `sigma*(eta)` on the support viable at **every** `eta` (so it is
comparable across `eta`). The counter-channel is already in the model and
Kaleckian: `w down -> wage bill down -> demand down` (the paradox of costs).
`eta = 0` reproduces the brief-05 `sigma*` **byte-for-byte** (nesting check PASS).

`sigma*(eta)` on `Y`, `c0 = 1.0` (support `rho` 0.35–0.65, fully viable at every
`eta`; means over 20 seeds, bootstrap CI over 2000 seed-resamples):

| `eta` | `sigma*` (Y) | 95% CI          | P(`sigma*` > 0.60) | mean `U` |
| ----- | ------------ | --------------- | ------------------ | -------- |
| 0.00  | 0.654        | [0.616, 0.691]  | 99.8 %             | 0.528    |
| 0.05  | 0.666        | [0.634, 0.692]  | 99.9 %             | 0.543    |
| 0.10  | 0.725        | [0.697, 0.745]  | 100 %              | 0.565    |
| 0.15  | 0.740        | [0.682, 0.793]  | 100 %              | 0.579    |

* **`sigma*` *rises* with `eta`**, moving *further above* the empirical range
  `sigma` 0.40–0.60. Turning on the substitution channel does **not** overturn the
  wage-led outcome - it **reinforces** it: the Kaleckian demand channel dominates.
* **Wage flexibility does not auto-correct unemployment** - mean `U` *rises*
  (0.53 → 0.58) as `eta` grows. The paradox of costs, reported not recalibrated.

![sigma*(eta): does wage flexibility move the sign frontier?](results/ces_b07_sigma_star_eta.png)

**Secondary regime `c0 = 2.0`: wage flexibility *destabilises* it.** The high-`sigma`
(1.25, 1.50), low-`rho` corner tips into collapse (`Y -> 0`, `U -> 1`) under wage
flexibility, spreading with `eta` (`sigma = 1.25`: 43 % of seeds collapse at
`eta = 0.15`). The strict common viable support shrinks from `rho` 0.40–0.65 to
0.50–0.65; on that support `sigma*` is erratic - **undefined** at `eta = 0.10` (the
sign never turns: wage-led at every `sigma` tested) and 0.32 at `eta = 0.15`. The
wage floor `w_min = 0.45` **never** stably binds anywhere, so this is genuine
viability collapse, not a floor artefact.

*Mechanism* (verified on a traced trajectory and a `sigma`-sweep at `c0 = 2.0`): the
wage **oscillates** - up above `w_bar` when `U -> 0` (the `U_min` guard sends
`w -> ~1.25`) and below it when `U` is high - and because `L_profitmax` grows more
wage-sensitive as `sigma` rises, this feeds a widening employment oscillation that
**erodes capital every cycle** (investment cannot cover depreciation) until, at low
`rho`, the economy collapses to `U = 1`. In the empirical region `sigma ~ 0.5` the
same curve leaves `w ~ w_bar`, no oscillation, and capital *grows*. The collapse is
capital erosion at high `sigma`, not a monotone upward wage spiral. Reported as a
finding, not recalibrated. Outputs: `results/ces_b07_*.csv` (via `scripts/run_brief07.py`).

### 5. Adaptive expectations do not move the frontier or the collapse (brief 08)

The headline results are comparative statics on the steady state, where `Ye = D` for
any expectation gain. Brief 08 generalises the firm's demand expectation from static
(`Ye_t = D_{t-1}`) to adaptive, `Ye_t = Ye_{t-1} + lambda_e*(D_{t-1} - Ye_{t-1})`,
and asks whether a slower expectation (a damper) changes *which* steady state is
selected, or shrinks the `c0 = 2.0` collapse. `lambda_e = 1` reproduces the committed
brief-05/07 panels **byte-for-byte** (4 nesting checks, `max_abs_dev = 0.0`).

`sigma*(eta; lambda_e)` on `Y`, `c0 = 1.0` (across-config common support `rho`
0.35–0.65; 20 seeds, bootstrap CI). The gain is **not** a lever: every point sits
within its neighbours' CIs.

| `eta` | `lambda_e` | `sigma*` (Y) | 95% CI          | P(`sigma*` > 0.60) |
| ----- | ---------- | ------------ | --------------- | ------------------ |
| 0.00  | 1.00       | 0.654        | [0.616, 0.691]  | 99.8 %             |
| 0.00  | 0.50       | 0.686        | [0.637, 0.721]  | 99.9 %             |
| 0.00  | 0.25       | 0.674        | [0.639, 0.709]  | 99.9 %             |
| 0.10  | 1.00       | 0.725        | [0.697, 0.745]  | 100 %              |
| 0.10  | 0.50       | 0.713        | [0.667, 0.752]  | 100 %              |
| 0.10  | 0.25       | 0.721        | [0.684, 0.754]  | 100 %              |

* **`sigma*` is `lambda_e`-invariant within CI.** The empirical `sigma` 0.40–0.60
  stays *below* `sigma*` for every gain, so the wage-led result and its brief-07 rise
  with `eta` are both **robust to the expectation gain**. No basin-selection finding.

![sigma*(lambda_e): does the expectation gain move the sign frontier?](results/ces_b08_sigma_star_lambda.png)

**The stabilisation hypothesis is *not* confirmed (`c0 = 2.0`).** The falsifiable
guess was that a slower expectation damps the brief-07 wage-employment oscillation and
shrinks the collapse region. It does **not**: the collapse is `lambda_e`-invariant to
within grid/seed noise (cells with any collapse at `eta = 0.10`: 16/15/14 for
`lambda_e = 1/0.5/0.25`, but fully-collapsed cells flat at 6; non-monotone at
`eta = 0.15`), and the reference collapsing cell (`sigma = 1.5, rho = 0.40,
eta = 0.10`) collapses to `K = 0, U = 1` at **every** `lambda_e`. The `c0 = 2.0`
collapse is driven by the wage→`U`→capital-erosion channel, which `lambda_e` does not
touch: damping the *demand* expectation cannot stabilise an instability that does not
originate in demand. Reported as a finding. Outputs: `results/ces_b08_*.csv` (via
`scripts/run_brief08.py`).

### 6. A balanced-budget benefit crowds capital *in* where demand-constrained, but does not stabilise the collapse (brief 09)

The unemployed earn nothing, so every unemployed worker leaks entirely out of the
circular flow (their notional `c0` is unfinanceable at zero wealth). Brief 09 reinnests
the Leontief branch's **balanced-budget unemployment benefit** on the current core: a
flat tax on accrued income funds an equal transfer to the unemployed, indexed to the
current wage `w_t` (`benefit_replacement_rate` = rr its size; OECD net replacement rates
~50–80 % for a low earner - see `parameter_notes.md`). `rr = 0` reproduces the committed
brief-05/07 panels **byte-for-byte** (4 nesting checks, `max_abs_dev = 0.0`).

**E1 - fiscal dose-response (the balanced-budget multiplier crowds capital in).** At the
headline demand-constrained scenario (`c0 = 1.0, sigma = 0.5, eta = 0.10, rho = 0.40`):

| rr   | U     | Y      | K      | wage share | realised tax | cash-constrained |
| ---- | ----- | ------ | ------ | ---------- | ------------ | ---------------- |
| 0.00 | 0.566 | 82.1   | 298.8  | 0.440      | 0.000        | 0.90             |
| 0.25 | 0.483 | 98.1   | 359.2  | 0.446      | 0.128        | 0.90             |
| 0.50 | 0.427 | 108.7  | 396.6  | 0.452      | 0.206        | 0.90             |
| 0.75 | 0.373 | 119.0  | 435.7  | 0.457      | 0.250        | 0.90             |

Unemployment falls and - the theoretical point - both output **and capital rise**
(299 → 436): in a demand-constrained regime redistribution is **crowding-in** (more
demand → more profit → more investment via `I = rho*pi`). The `anchor` scenario
(`c0 = 2.0, sigma = 1`) moves the same way, more gently (U 0.257 → 0.177, K 418 → 469).
The **cash-constrained fraction stays 0.90 = all 90 workers, invariant to rr**: the
benefit never lifts a worker off the liquidity constraint (MPC ~ 1 is preserved), which
is exactly why the balanced-budget multiplier keeps delivering across the whole dose.

**E2 - the benefit eliminates the wage-led region (`c0 = 1.0`).** At rr = 0,
`sigma*(Y)` = 0.654 (natural anchor) / 0.83 (across-config support), wage-led for
`sigma` above it. At **rr = 0.5 `sigma*` is undefined** (`frac_undefined ~ 1.0`): every
`dY/drho` slope turns **positive** across the tested range (`sigma = 1`: +38.7;
`sigma = 1.5`: +19.3), pushing `sigma*` above 1.5. The demand floor makes retention
expansionary at **every** `sigma` - the wage-led high-`sigma` region is gone. The `U`
frontier barely moves (`sigma*_U ~ 0.40 → 0.43`): the benefit changes the *output*
response to retention far more than the *unemployment* response. (The brief expected a
*small* shift; the measured shift is large, and reported as such.)

**E3 - the stabilisation hypothesis is falsified: the collapse region *enlarges*
(`c0 = 2.0`).** The falsifiable guess was that a demand floor when `U` rises shrinks the
brief-07 wage-curve collapse. It does the opposite. Cells with any collapsed seed:
`eta = 0.10` **16 → 26** from rr = 0 to rr = 0.5; `eta = 0.15` **16 → 29**; the mean
fraction of seeds at `U = 1` doubles (0.125 → 0.266, 0.129 → 0.333). The reference cell
(`sigma = 1.5, rho = 0.40, eta = 0.10`) collapses to `K = 0, U = 1` at **both** rr = 0
and rr = 0.5, but at rr = 0.5 the tax is **pinned at the cap** (`Tax_Rate = 0.600`,
fraction of periods at cap = 1.0) - the instrument saturates and the economy still dies.
*Mechanism* (from the tax-saturation diagnostics `mean_tax`, `frac_periods_at_cap` now
in the collapse map and trace): where firms are collapsing the tax base is almost all
wages, so taxing workers to pay workers is **MPC-neutral** (no net demand); the benefit
indexed to `w_t` is **procyclical** (high `U` → low `w_t` → weak floor); and the demand
it does inject **amplifies** the wage→`U`→capital-erosion oscillation in the high-`sigma`
corner. A demand floor cannot stabilise a collapse that does not originate in demand -
it aggravates it. Reported as a finding, not recalibrated. Outputs: `results/ces_b09_*.csv`
(via `scripts/run_brief09.py`).

![E1 fiscal dose-response: U, Y, K vs rr](results/ces_b09_dose_response.png)
![E3 collapse map: does the demand floor shrink it? (it enlarges it)](results/ces_b09_collapse_map.png)

### 7. Why the firms are homogeneous - a structural assumption, tested (brief 10)

All ten firms share one productivity `A`. That is an **assumption**, and roadmap point 8
proposed relaxing it. Brief 10 does not implement it; it **measures what would happen if
it did**, and the measurement is the reason the point is closed rather than built. One
experimental dial, `productivity_spread`, fans the firm productivities out
mean-preservingly (`A_i = 1 + spread*(2i-(n-1))/(n-1)`), changing nothing else - no
selection, no demand reallocation, no entry/exit. `spread = 0` reproduces the committed
brief-05/07/09 panels **byte-for-byte** (3 nesting checks, `max_abs_dev = 0.0`).

The result is a **cliff, not a gradient**. Below the threshold the economy is healthy and
no firm dies; one grid step above it, *every* firm is dead:

| spread | S1 `anchor` U / Y | S2 `headline` U / Y | S3 `rr=0.5` U / Y | dead firms (S2) |
| ------ | ----------------- | ------------------- | ----------------- | --------------- |
| 0.000  | 0.258 / 132.1     | 0.566 / 82.1        | 0.427 / 108.7     | 0               |
| 0.050  | 0.250 / 133.0     | 0.563 / 82.7        | 0.421 / 109.5     | 0               |
| 0.100  | 0.229 / 134.7     | 0.554 / 83.2        | 0.410 / 109.9     | 0               |
| 0.125  | **1.000 / 0.0**   | 0.543 / 84.2        | 0.676 / 58.9      | 0               |
| 0.150  | 1.000 / 0.0       | **1.000 / 0.0**     | **1.000 / 0.0**   | **10**          |
| 0.200  | 1.000 / 0.0       | 1.000 / 0.0         | 1.000 / 0.0       | 10              |

"Collapsed" is literal: `Y = 0`, `U = 1`, all ten firms dead, aggregate capital decaying
geometrically to `3.5e-34` by step 2000. The threshold sits between `spread` 0.10 and
0.125 for the `anchor` scenario and between 0.125 and 0.15 for the `headline` one.

**The mean-field claim, made precise.** Below the threshold no firm dies, but "identical
to the homogeneous model" holds less far than "healthy" does: `Y` stays inside the
`spread = 0` inter-seed band only up to `spread = 0.05` (`anchor`, `rr=0.5`) or 0.125
(`headline`). At `spread = 0.10` the `anchor` aggregates have moved *detectably* at 20
seeds - and moved **upward** (`Y` 132.1 → 134.7, `U` 0.258 → 0.229): mean-preserving
dispersion is mildly **expansionary** right up until it is fatal. So the defensible
statement is *the firm side is quasi-representative in its aggregates up to about ±5 %
dispersion, and viable but no longer identical up to the cliff* - not "heterogeneity does
not matter".

**The domino.** Traced on `headline`, `spread = 0.20`, seed 0: the low-`A` firm serves the
same network demand with more labour, earns less profit, invests below `delta*K` and
decapitalises first (`K` 38 → ~0 by step 250). Its spending shares stay pointed at it
(demand destroyed) and its laid-off workers lose their income (a demand externality), so
the high-`A` firms follow - `K` of the strongest firm reaches zero by step 500, `U` hits 1.
**This is what the missing machinery would have done:** with entry/exit and demand
rerouting, that demand would have moved to a surviving firm instead of vanishing.

**E2 - does the brief-09 benefit cushion it? Falsified: it makes things *worse*.** The
hypothesis was that keeping income flowing to the laid-off would raise the viability
threshold. Measured, it **lowers** it. At `spread = 0.125` the `headline` scenario has
**0 of 20** seeds with any dead firm; the same scenario at `rr = 0.5` has **18 of 20**,
with **7 of 20** fully collapsed (a genuine mixed basin). The full-collapse threshold is
unchanged at 0.15. *Mechanism, verified rather than guessed* (seed 8, `spread = 0.125`):
the benefit lowers unemployment (early-run `U` 0.544 → 0.445), the wage curve reads that
and **raises the wage** (`w_t` 0.836 → 0.853), and the low-`A` firm - whose marginal
product is scaled down by its `A` - is the first squeezed below `I = delta*K`. At `rr = 0`
that firm sits in a stable steady state (`K ~ 28`, 6 workers, profit 3.73 at step 1200);
at `rr = 0.5` it decapitalises monotonically to `1.8e-6` by step 800 and sheds every
worker. The demand cushion is real but dominated by the same wage → `U` channel that drove
briefs 07 and 09.

**Comparison with the data, and its limit.** Within-industry TFP dispersion is large -
Syverson (2004) reports a 90/10 ratio around 2:1 in US manufacturing (see also Bartelsman
& Doms 2000). The collapse threshold here is a max/min productivity ratio of about
**1.22-1.29**, far below that. **The units are not the same** and no quantitative mapping
is claimed: a linear fan half-width is not a 90/10 log-TFP ratio, and the model's `A`
enters a normalised CES fitted to nothing. The qualitative reading is all that is
supported, and it is enough: **empirically realistic firm heterogeneity is well outside
this model's viable range**, because the model has no reallocation channel to absorb it.
Building point 8 without point 12 (entry/exit and demand rerouting) would produce a model
that dies rather than a model with heterogeneous firms. Point 8 is therefore closed with
the firm side declared **quasi-representative, as a tested assumption**; reallocation is
declared future work. Outputs: `results/ces_b10_*.csv` (via `scripts/run_brief10.py`).

*Limit, declared:* the probe establishes that a threshold exists and where it lies for a
**linear** fan. It says nothing about the shape of the dispersion distribution - a
lognormal `A` with the same variance need not have the same threshold.

![Aggregates vs dispersion: the cliff](results/ces_b10_aggregates_spread.png)
![The domino: the weak firm decapitalises first, then the cascade](results/ces_b10_domino_trace.png)

---

## Interpretive frame (read this before the results)

* **The regime is demand-constrained almost everywhere.** In 76 of 77 viable
  cells (`c0 = 1.0`) the binding constraint is demand; the one exception is
  capital-constrained at very low `sigma`. `sigma` acts *inside* the regime, it
  does not switch it. (This is why the wage-led/profit-led sign is a genuine
  outcome, not an artefact of a capacity ceiling.)
* **Unemployment is out of scale at every `c0`.** At the calibrated `rho = 0.40`
  and empirical `sigma`, the model runs at ~50 % unemployment (`c0 = 1.0`) or
  ~31 % (`c0 = 2.0`). No tested `c0` brings it into a plausible band; this is a
  structural tension of the fixed-wage labour market (point 11), reported as an
  open question, not calibrated away. (The brief-09 benefit is a genuine demand-side
  lever here - it lowers headline `U` 0.57 → 0.37 at rr = 0.75 - but it is a policy
  instrument, not a recalibration of the structural tension.)
* **The wage share (0.35–0.61 across viable cells) sits mostly *below* the
  empirical 0.60–0.68**, touching it only at high `sigma` and low `rho`.
* **Multiple equilibria and a viability threshold near `rho ~ 0.30`.**
  `initial_capital` selects the basin, so it is held fixed across every grid and
  reported; cells that collapse (e.g. `rho = 0.35` at `c0 = 2.0`) are an
  **outcome**, not an error.
* **The model is close to mean-field *in its aggregates*, and this is now measured,
  not asserted.** The 95 % confidence band on each cell's mean output is ~0.6–0.9 %
  of the mean (median over viable cells); the raw per-seed min–max spread is wider
  (~5–8 %). Brief 10 tested the firm-side half of the claim directly: dispersing
  firm productivity leaves the aggregates alone up to ~±5 % and viable up to a
  sharp cliff at ~±12 %, past which the economy dies outright (§7). Two caveats
  that follow from it: the firm side is quasi-representative in its **aggregates,
  not in its cross-section** — even with identical `A`, random consumption links
  make firms diverge in capital (`TopK_Share` settles at 0.35–0.38, not the equal-split
  0.30) — and the narrowness of the viable range is itself a **limitation of the
  model**, caused by the absence of any reallocation channel.
* **`c0` and `wealth_effect` note.** `wealth_effect = 0.05` is anchored (Slacalek
  2009). `c0 = 2.0` is a demand-scale lever with a falsified original
  justification and is *not* an empirical estimate; the headline is reported at
  `c0 = 1.0` with `c0 = 2.0` alongside. See `parameter_notes.md`.

---

## Repository structure

```text
src/
├── agents.py        Firm (normalised CES, wage-curve wage, internal financing), Household, Capitalist
├── model.py         MacroModel: labour market, wage curve (U_REF, wage_from_curve), government (brief 09), period sequence, metrics
└── experiment.py    Monte-Carlo runner, rho sweep, (sigma, rho) sign frontier, brief-05 robustness stack
scripts/
├── run_brief04.py   Regenerates the brief-04 (sigma, rho) grid + sign frontier into results/ (reproducible)
├── run_brief05.py   Regenerates the brief-05 stage A/B/C outputs into results/ (reproducible)
├── run_brief07.py   Regenerates the brief-07 wage-curve sweep (sigma x rho x eta x c0) into results/ (reproducible)
├── run_brief08.py   Regenerates the brief-08 adaptive-expectations sweep (sigma x rho x eta x lambda_e x c0) (reproducible)
├── run_brief09.py   Regenerates the brief-09 government sweep (dose-response + sigma*(eta;rr) + collapse map) (reproducible)
└── run_brief10.py   Regenerates the brief-10 firm-heterogeneity viability probe (aggregates vs spread + domino trace) (reproducible)
notebooks/
└── 01_Endogenous_Investment.ipynb   rho sweep at sigma=1 + sigma sweep with the sign frontier
results/
├── ces_b10_*.csv    brief-10 heterogeneity probe: aggregates vs spread, viability thresholds, domino trace; produced by scripts/run_brief10.py
├── ces_b09_*.csv    brief-09 government sweep: dose-response, sigma*(eta;rr), collapse map + trace; produced by scripts/run_brief09.py
├── ces_b08_*.csv    brief-08 adaptive-expectations sweep + sigma*(eta;lambda_e) + collapse map; produced by scripts/run_brief08.py
├── ces_b07_*.csv    brief-07 wage-curve sweep + sigma*(eta); produced by scripts/run_brief07.py
├── ces_b05_*.csv    brief-05 robustness stack (20 seeds); produced by scripts/run_brief05.py
└── ces_*.csv        brief-04 (sigma, rho) grid, derivatives and sign frontier
tests/
├── conftest.py
└── test_model.py    SFC + buffer==0, distribution, labour accounting, CES nesting, robustness stack, wage curve, adaptive expectations, government, heterogeneity probe
performance/
└── engine.cpp       STALE: additive Phase-1 model, NOT the current core (do not use)
requirements.txt
retention_sweep.png, ces_sign_frontier.png, results/ces_b07_sigma_star_eta.png, results/ces_b08_sigma_star_lambda.png, results/ces_b09_dose_response.png, results/ces_b10_aggregates_spread.png
```

---

## Getting started

```bash
python -m pip install -r requirements.txt

# reproduce the figures and analysis
jupyter nbconvert --to notebook --execute --inplace notebooks/01_Endogenous_Investment.ipynb

# regenerate the brief-05 robustness outputs (results/ces_b05_*.csv); threads are pinned
python scripts/run_brief05.py

# regenerate the brief-07 wage-curve sweep (results/ces_b07_*.csv); two phases, threads pinned
python scripts/run_brief07.py

# regenerate the brief-08 adaptive-expectations sweep (results/ces_b08_*.csv); two phases, threads pinned
python scripts/run_brief08.py

# regenerate the brief-09 government sweep (results/ces_b09_*.csv); two phases, threads pinned (~1.5-2h)
python scripts/run_brief09.py

# regenerate the brief-10 heterogeneity probe (results/ces_b10_*.csv); single phase, threads pinned (~10 min)
python scripts/run_brief10.py

# run the checks (SFC, buffer==0, distribution, labour accounting, CES nesting, wage curve, adaptive expectations, government, heterogeneity, bootstrap)
python -m pytest tests/ -q
```

Programmatic use:

```python
import sys; sys.path.append("src")
from experiment import run_experiment, retention_sweep, sigma_rho_sweep

panel = run_experiment(retention_ratio=0.40, steps=2000, seeds=3)   # multi-seed panel
sweep = retention_sweep([0.35, 0.40, 0.50, 0.60])                   # steady-state vs rho (sigma=1)
grid  = sigma_rho_sweep()                                           # the (sigma, rho) sign frontier
```

**C++ engine - not aligned to this core.** `performance/engine.cpp` is an
aggregate second implementation inherited from the additive Phase-1 model. It has
**not** been ported to the CES core and must not be used for results until it is
(a separate, tracked task).

---

## References

* Teglio, A. (2025). *Rationality, inequality, and the output gap: evidence from
  a disaggregated Keynesian cross diagram.* Journal of Economic Interaction and
  Coordination 20(1), 107–139. - <https://link.springer.com/article/10.1007/s11403-024-00412-4>
* Klump, R. & de La Grandville, O. (2000). *Economic Growth and the Elasticity of
  Substitution: Two Theorems and Some Suggestions.* American Economic Review
  90(1), 282–291. - <https://www.aeaweb.org/articles?id=10.1257/aer.90.1.282>
* Chirinko, R. S. (2008). *sigma: The long and short of it.* Journal of
  Macroeconomics 30(2), 671–686. - <https://ideas.repec.org/a/eee/jmacro/v30y2008i2p671-686.html>
* Knoblach, M., Roessler, M. & Zwerschke, P. (2020). *The Elasticity of
  Substitution Between Capital and Labour in the US Economy.* Oxford Bulletin of
  Economics and Statistics 82(1), 62–82. - <https://ideas.repec.org/a/bla/obuest/v82y2020i1p62-82.html>
* Slacalek, J. (2009). *What Drives Personal Consumption? The Role of Housing and
  Financial Wealth.* The B.E. Journal of Macroeconomics 9(1). - <https://ideas.repec.org/a/bpj/bejmac/v9y2009i1n37.html>
* Blanchflower, D. G. & Oswald, A. J. (1994). *The Wage Curve.* MIT Press. -
  wage-curve elasticity ~-0.10 (the level relation used in brief 07).
* Nijkamp, P. & Poot, J. (2005). *The Last Word on the Wage Curve?* Journal of
  Economic Surveys 19(3), 421–450. - meta-analysis, corrected elasticity ~-0.07.

Mesa: Agent-Based Modeling in Python - <https://mesa.readthedocs.io/>

---

## Disclaimer

An exploratory computational economics model for research and education. It
investigates the qualitative implications of behavioural assumptions within a
heterogeneous framework; it is not a calibrated forecast or a policy
recommendation.

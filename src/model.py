"""
Macro model for the Endogenous-Investment Keynesian ABM
(normalised-CES core + endogenous labour market — roadmap point 11 + brief 04).

Single-good, fixed-price (numeraire = 1), stock-flow-consistent circular flow of
income.  Production is a *normalised* CES with elasticity of substitution ``sigma``
(``sigma = 1`` is the Cobb-Douglas core; ``sigma -> 0`` is Leontief); firms hire
endogenously at the wage ``w_t``; the unemployed earn nothing, so employment drives
demand.  The wage is set by a Blanchflower-Oswald *wage curve* on last period's
unemployment (brief 07); ``eta = 0`` fixes it at ``w_bar`` and nests the old model.

Period sequence (employment is set *before* households form demand, because
expected income depends on employment status) — step 0 added by brief 07:

    0. wage determination: w_t from the wage curve on U_{t-1} (eta = 0 -> w_t = w_bar).
       Set here, before the labour market, to avoid the w <-> U simultaneity.
    1. firms form expectations, compute desired employment; the labour market
       fires the excess and fills vacancies (random matching) -> employment
    2. households form consumption demand (income = wage if employed, else 0;
       plus dividends for capitalists)
    3. firms plan investment (profit flow, accelerator on last utilisation)
    4. firms register demand (consumption + investment)
    5. firms produce: Y = min(demand, Y*(K, L)); ration; set u; update the demand
       expectation Ye <- Ye + lambda_e*(faced - Ye) (brief 08; lambda_e = 1 -> Ye = faced,
       the static case).  No new step: the update stays inside production, as before.
    6. firm accounting: wage_bill = w_t*L, retained (= I_planned), residual dividends
    7. investment settlement: pay I_delivered; K(t+1) = (1-delta)K + I_delivered;
       buffer returns to zero
    8. government (brief 09): a balanced-budget unemployment benefit — a flat tax on
       this period's accrued income (``next_income``) funds an equal transfer to the
       unemployed.  Placed AFTER investment settlement (the last ``next_income`` accrual,
       the residual dividend) and BEFORE household settlement, so the tax hits the
       period's fully-accrued income and the benefit reaches the unemployed with the same
       one-period lag as a wage.  ``benefit_replacement_rate = 0`` (default) skips the
       whole step and reproduces the pre-brief-09 model bit-for-bit.
    9. household settlement (credit income, pay for delivered goods)

Firms are **homogeneous** (one common A) unless ``productivity_spread > 0``, which fans
their productivities out mean-preservingly (brief 10).  That dial is a *probe of the
homogeneity assumption*, not an implementation of firm heterogeneity: it adds dispersion
without any of the machinery — selection, demand reallocation, entry/exit — that a real
heterogeneous-firm model needs.  It touches no flow, no step and no settlement, so the
period sequence and the SFC invariant below are unchanged at any spread.

Conserved quantity (checked in ``tests/``): at a period boundary the buffer is
zero, so ``sum(household wealth + income) + sum(firm money_buffer)`` is constant.
The unemployed receive either nothing (default) or a benefit funded one-for-one by the
tax (a pure transfer, brief 09), so money is still conserved in both cases.
"""

import mesa
import numpy as np

from agents import (
    Firm,
    Household,
    Capitalist,
    ces_capacity,
    ces_wage_share_profitmax,
    _Y0,
)


# ============================================================
# Normalisation anchor — a MODELLING CHOICE, measured once and frozen
# ============================================================
#
# The normalised CES needs a base point ``(K0, L0, Y0)`` that is the SAME for every
# sigma and every rho on the grid, otherwise the normalisation normalises nothing
# (Klump & Saam 2008).  These per-firm values were measured once on branch
# ``labour-market`` (the Cobb-Douglas core, i.e. sigma = 1) at:
#
#     retention_ratio = 0.40, seeds {0, 1, 2}, 2000 steps, mean of the last 50
#     observations, all other parameters at their defaults below
#     (initial_capital = 40.0, wage_rate = 0.9, c0 = 2.0, N = 100, 10 firms).
#
# Measured aggregates: K = 418.7356984217038, L = 73.95333333333333 over 10 firms.
#
# Anchoring at rho = 0.40 centres the experiment on the reference scenario of the
# labour-market branch.  The values are per firm; with constant returns to scale the
# normalised CES is homogeneous of degree 1 in (K, L), so scaling (K0, L0, Y0) by a
# common factor leaves the function identical — per-firm vs aggregate anchoring is
# immaterial, provided Y0 is derived from the same K0, L0.
#
# At sigma = 1 the anchor is irrelevant: the identity with Cobb-Douglas holds for any
# (K0, L0) as long as Y0 is *computed* (agents._Y0), never measured.  It matters only
# for sigma != 1, where it fixes the point through which every sigma-variant passes.
ANCHOR_K0 = 41.87356984217038
ANCHOR_L0 = 7.395333333333333


# --- The re-anchoring check (brief 05 §4) ---------------------------------
#
# WHY A SECOND ANCHOR EXISTS.  The anchor above sits at rho = 0.40, which is the
# LOWEST viable rho: the whole sweep therefore lies on one side of it.  Since the
# first derivatives are identical across sigma *at* the anchor, the effects of sigma
# are mechanically a function of the distance travelled from it — which is precisely
# Temple's (2012) objection: normalisation makes the sigma-variants comparable AT a
# point, it does not make the comparison away from that point neutral to the choice
# of point.  So the experiment is repeated with the anchor moved to the CENTRE of the
# viable support, and sigma* is checked for movement.  If it does move, sigma* depends
# on the anchor and must be reported as such — one does not pick the anchor that gives
# the preferred answer.
#
# Measured ONCE by the same procedure as the rho = 0.40 anchor above:
#
#     retention_ratio = 0.50, sigma = 1, seeds {0, 1, 2}, 2000 steps, mean of the last
#     50 observations, all other parameters at their defaults
#     (initial_capital = 40.0, wage_rate = 0.9, c0 = 2.0, N = 100, 10 firms).
#
# Measured aggregates: K = 525.6635921973111, L = 63.20261437908497 over 10 firms.
#
# c0 = 2.0 here deliberately, matching how the rho = 0.40 anchor was measured: the
# anchor belongs to the PRODUCTION specification, not the demand block, so it is held
# fixed across c0 (brief 05 §4.3).  Re-measuring it per c0 would change the production
# function whenever demand changed, and differences between c0 would stop being
# attributable to c0.  Consequence, reported rather than hidden: at c0 = 1.0 the model
# operates at a different distance from the anchor.
ANCHOR_K0_RHO050 = 52.56635921973111
ANCHOR_L0_RHO050 = 6.320261437908497


# ============================================================
# Wage-curve reference unemployment — a MODELLING CHOICE, measured once and frozen
# ============================================================
#
# Brief 07 endogenises the wage via a Blanchflower-Oswald wage curve
#
#     w_t = max(w_min, w_bar * (max(U_{t-1}, U_min) / U_REF) ** (-eta)),
#
# normalised at ``U_REF``: the unemployment rate at which the wage equals ``w_bar``,
# i.e. the wage at which the ANCHOR_* above were measured.  U_REF is MEASURED, not
# chosen: an arbitrary value would make the steady-state wage level a hidden degree of
# freedom of the calibration.  Anchoring it to the ANCHOR_* scenario makes the
# wage-curve model at ``eta = 0`` pass through the same point as the current model in
# the reference scenario.
#
# Measured ONCE on the CURRENT model (pre-wage-curve) by the same procedure as the
# ANCHOR_* above:
#
#     retention_ratio = 0.40, sigma = 1, seeds {0, 1, 2}, 2000 steps, mean of the
#     LAST 50 observations of Unemployment_Rate, all other parameters at their
#     defaults (initial_capital = 40.0, wage_rate = 0.9, c0 = 2.0, N = 100, 10 firms).
#
# Tail convention: ``df.tail(50)`` (the 50 rows at index 1951..2000), which is the one
# that reproduces ANCHOR_L0 * 10 = 73.95333333 exactly — the same discipline as the
# ANCHOR.  (The other convention in the codebase, ``df.index >= steps - tail``, keeps
# 51 rows and is what the brief-04 grid pin uses; it would give 0.2602614379 instead.)
#
# Per-seed tail-50 means: 0.2570 (seed 0), 0.2680 (seed 1), 0.2564 (seed 2);
# mean over seeds = 0.2604666667.
#
# This is a modelling choice, NOT an estimate of the NAIRU: it is only the point at
# which the wage curve is normalised to the pre-modification wage.
U_REF = 0.2604666666666667


# ============================================================
# Firm productivity dispersion — an EXPERIMENTAL DIAL (brief 10 probe)
# ============================================================
#
# The firm side is homogeneous (every firm has the same A).  Brief 10 does not make
# heterogeneity a feature (roadmap point 8 is DECIDED AGAINST — no selection, no
# reallocation, no entry/exit); it adds the minimum needed to *test* the homogeneity
# assumption and measure where it breaks.  ``productivity_spread = 0`` (the default)
# is the model as it was, bit-for-bit.
#
# CONVENTION, declared not hidden: the normalisation anchor (``ANCHOR_*``: K0, L0) and
# ``U_REF`` stay FROZEN and COMMON to all firms.  A_i scales the individual firm's Y0
# through ``_Y0(A_i, K0, L0, pi0)``, so the fan is mean-preserving in **A**, not in Y0
# (Y0 is linear in A here, so with this anchor it happens to be mean-preserving in Y0
# too — but that is a property of the CES normalisation, not something imposed).
# Aggregate benchmarks that need one economy-wide A (``Potential_Output``,
# ``Wage_Share_Profitmax``) keep using ``model.productivity``, i.e. the fan's MEAN: a
# reporting convention for a diagnostic, with no effect on the dynamics.

#: A firm with capital below this counts as "dead" in the ``Dead_Firms`` diagnostic.
#: A declared convention for *reporting only* — nothing in the dynamics reads it, and a
#: firm below it is not removed, frozen, or treated specially in any way.
DEAD_FIRM_K = 0.5

#: ``TopK_Share`` reports the capital share of the largest this-many firms.
TOPK_N = 3


def productivity_fan(base, n, spread):
    """Mean-preserving linear fan of firm productivities (brief 10).

        A_i = base * (1 + spread * (2i - (n-1)) / (n-1)),    i = 0 .. n-1

    so A runs linearly from ``base*(1-spread)`` to ``base*(1+spread)`` and averages to
    ``base``.  ``spread = 0`` is short-circuited to return ``base`` for every firm —
    the explicit branch (like the ``eta = 0`` and ``lambda_e = 1`` branches elsewhere)
    is what guarantees the nested model is reproduced bit-for-bit, without relying on
    ``1 + 0.0*x`` rounding back to exactly 1.

    The numerator ``2i - (n-1)`` is an integer, so the offsets of firm ``i`` and firm
    ``n-1-i`` are exact negatives of each other and the fan is symmetric by construction.
    Exact mean preservation in floating point is *verified* (tests/test_model.py), not
    assumed: it holds to 1e-15 or better, and exactly for the n = 10 grid swept here.
    """
    if n <= 0:
        return []
    if spread == 0.0 or n == 1:
        return [base] * n
    denom = float(n - 1)
    return [base * (1.0 + spread * ((2 * i - (n - 1)) / denom)) for i in range(n)]


def wage_from_curve(w_bar, U_prev, eta, U_ref, U_min, w_min):
    """Blanchflower-Oswald wage curve — the *level* of the wage, given last U (brief 07).

        w = max( w_min,  w_bar * (max(U_prev, U_min) / U_ref) ** (-eta) )

    A *level* relation (not a Phillips *change* relation): it has a well-defined steady
    state for every U, so it is compatible with comparative statics.  ``eta = 0`` returns
    ``w_bar`` exactly (``x ** -0.0 == 1.0`` in IEEE-754), which is why the model can nest
    the fixed-wage case; the caller still short-circuits eta = 0 to avoid the pow entirely
    and guarantee bit-identity.

    ``U_min`` guards the singularity at full employment (U -> 0 would send w -> +inf for
    eta > 0); ``w_min`` is the subsistence floor against a deflationary spiral at high eta.
    Both are declared conventions, not estimates (see parameter_notes.md).
    """
    U_eff = U_prev if U_prev > U_min else U_min
    w = w_bar * (U_eff / U_ref) ** (-eta)
    return w if w > w_min else w_min


# ============================================================
# Metrics
# ============================================================

def _households(model):
    return [a for a in model.agents if isinstance(a, Household)]


def _firms(model):
    return [a for a in model.agents if isinstance(a, Firm)]


def compute_gini(values):
    """Gini coefficient of a list of non-negative values (0 = equality)."""
    x = np.sort(np.asarray(values, dtype=float))
    n = x.size
    total = x.sum()
    if n == 0 or total <= 0:
        return 0.0
    index = np.arange(1, n + 1)
    return (2.0 * np.sum(index * x) / (n * total)) - (n + 1.0) / n


def compute_income_gini(model):
    return compute_gini([h.income for h in _households(model)])


def compute_wealth_gini(model):
    net_worth = [
        h.net_worth() if isinstance(h, Capitalist) else h.wealth
        for h in _households(model)
    ]
    return compute_gini(net_worth)


def compute_output(model):
    return sum(f.production for f in _firms(model))


def compute_expected_demand(model):
    """Aggregate firm demand expectation ``sum(f.expected_demand)`` (brief 08 diagnostic).

    A convergence diagnostic for the adaptive-expectations block: in steady state ``Ye = D``
    for any gain, so this tracks Output.  Deviations from Output during the transient are
    the expectations lagging realised demand, which is the whole point of the gain.
    """
    return sum(f.expected_demand for f in _firms(model))


def compute_employment(model):
    return sum(len(f.workers) for f in _firms(model))


def compute_unemployment(model):
    n = model.num_households
    return 1.0 - compute_employment(model) / n if n > 0 else 0.0


def compute_potential_output(model):
    """Full-employment output benchmark: the CES capacity at ``(K_agg, N)``.

    Evaluated with the per-firm anchor, which is legitimate because the normalised
    CES has constant returns (see the ANCHOR_* note above).
    """
    k = compute_aggregate_capital(model)
    n = model.num_households
    if k <= 0 or n <= 0:
        return 0.0
    return ces_capacity(
        k, n, model.productivity, model.K0, model.L0, model.pi0, model.sigma
    )


def compute_output_gap(model):
    """``gap_N = 1 - Y/Y*(K, N)`` — output below FULL-EMPLOYMENT potential.

    **This is the headline gap** (brief 05 §5.3).  It is the definition that carries
    the project's research question: it measures *unused heads*, so it is the one
    commensurable with Teglio's (2025) output-gap concept and the one that moves with
    unemployment.  Its companion :func:`compute_output_gap_profitmax` measures unused
    *capacity* instead — a different quantity, reported alongside rather than in place
    of this one, because the difference between them is itself informative.
    """
    potential = compute_potential_output(model)
    if potential <= 0:
        return 0.0
    return (potential - compute_output(model)) / potential


def compute_potential_output_profitmax(model):
    """Capacity benchmark at the *profit-max* scale: ``Y*(K_agg, min(sum L_pm, N))``.

    Aggregated the same way as :func:`compute_potential_output` (aggregate K, one CES
    evaluation with the per-firm anchor) so the two are commensurable and their
    ordering is exact; the per-firm ``L_profitmax`` are summed and then capped at the
    workforce, because there are only ``N`` workers however much labour the firms
    would each like at ``MPL = w_bar``.

    ``L_profitmax`` is ``+inf`` when MPL never falls to the wage (sigma > 1, low wage);
    the sum is then ``+inf`` and the cap returns ``N``, so this collapses onto the
    full-employment benchmark rather than blowing up.
    """
    k = compute_aggregate_capital(model)
    n = model.num_households
    if k <= 0 or n <= 0:
        return 0.0
    # min() over a possibly-infinite sum: no branch needed, inf loses to N.
    labour = min(sum(f.L_profitmax for f in _firms(model)), float(n))
    if labour <= 0:
        return 0.0
    return ces_capacity(
        k, labour, model.productivity, model.K0, model.L0, model.pi0, model.sigma
    )


def compute_output_gap_profitmax(model):
    """``gap_pm = 1 - Y/Y*(K, min(L_profitmax, N))`` — output below PROFIT-MAX capacity.

    Consistent with the point-11 definition of utilisation (which is also measured
    against the profit-max scale), this measures *unused capacity*, not unused heads.

    ``gap_pm <= gap_N`` always, because ``min(sum L_pm, N) <= N`` and the CES is
    non-decreasing in labour — the profit-max benchmark is the weaker one.  The two
    coincide exactly when the firms would hire the whole workforce at ``MPL = w_bar``.
    Asserted in tests: if the ordering ever inverts, one of the two is misimplemented.
    """
    potential = compute_potential_output_profitmax(model)
    if potential <= 0:
        return 0.0
    return (potential - compute_output(model)) / potential


def compute_aggregate_capital(model):
    return sum(f.capital for f in _firms(model))


def compute_average_utilization(model):
    """Mean firm utilisation Y / profit-max capacity (weak-demand signal)."""
    firms = _firms(model)
    if not firms:
        return 0.0
    return sum(f.utilization for f in firms) / len(firms)


def compute_consumption(model):
    return sum(h.actual_consumption for h in _households(model))


def compute_investment(model):
    return model.total_investment_realised


def compute_total_money_buffer(model):
    return sum(f.money_buffer for f in _firms(model))


def compute_wage_share(model):
    """Aggregate wage bill / sales — a *measured outcome*.

    Upper bound is :func:`compute_wage_share_profitmax`, which equals ``1 - pi0``
    only at sigma = 1.
    """
    firms = _firms(model)
    sales = sum(f.sales for f in firms)
    if sales <= 0:
        return 0.0
    return sum(f.wage_bill for f in firms) / sales


def compute_wage_share_profitmax(model):
    """Wage share the firm *would* post at its profit-max point (brief 04 §9.4).

    Independent of K under constant returns; the sigma-dependent ceiling on the
    realised wage share.  This is the second of the two channels through which sigma
    acts: sigma changes the profit-max K/L ratio at the given wage, hence the share
    of output going to labour, *in the opposite direction* to the employment loss.
    """
    return ces_wage_share_profitmax(
        model.productivity, model.wage_rate, model.K0, model.L0, model.pi0, model.sigma
    )


def compute_profit_share(model):
    firms = _firms(model)
    sales = sum(f.sales for f in firms)
    if sales <= 0:
        return 0.0
    return sum(f.gross_profit for f in firms) / sales


# --- wage-curve diagnostics (brief 07) ------------------------------------

def compute_wage_rate(model):
    """The current wage ``w_t`` (a *measured outcome* once the wage curve is on).

    Constant at ``w_bar`` when ``eta = 0`` (the nested fixed-wage model).
    """
    return model.wage_rate


def compute_wage_floor_binding(model):
    """1.0 if the subsistence floor ``w_min`` binds this period, else 0.0.

    Model-level bool (brief 07 §4): its tail-average over a run is the fraction of
    steady-state periods in which the floor caught the wage — the map of "stably
    floored" cells that must be reported rather than hidden.
    """
    return 1.0 if model.wage_rate <= model.wage_floor else 0.0


# --- regime diagnostics (brief 04 §9) -------------------------------------

def _binding(model, label):
    """Share of firms whose employment is held down by ``label`` this period.

    ``workforce`` overrides the planned limit: a firm that wanted more workers than
    the unemployed pool could supply is labour-constrained whatever it had planned.
    """
    firms = _firms(model)
    if not firms:
        return 0.0
    hit = sum(
        1
        for f in firms
        if (f.binding_constraint if not f.labour_rationed else "workforce") == label
    )
    return hit / len(firms)


def compute_bound_by_demand(model):
    return _binding(model, "demand")


def compute_bound_by_profitmax(model):
    return _binding(model, "profitmax")


def compute_bound_by_capital(model):
    """sigma < 1 only: demand above Y_max(K), unreachable at any finite L."""
    return _binding(model, "capital")


def compute_bound_by_workforce(model):
    return _binding(model, "workforce")


def compute_cash_constrained_frac(model):
    households = _households(model)
    if not households:
        return 0.0
    return sum(1 for h in households if h.cash_constrained) / len(households)


# --- fiscal diagnostics (brief 09) ----------------------------------------

def compute_tax_rate(model):
    """The balanced-budget flat tax rate realised this period (a *measured outcome*).

    0.0 when the benefit is off (``benefit_replacement_rate = 0``) or there are no
    unemployed; capped at ``max_tax`` when the desired transfer would need more (in
    which case the benefit is scaled down to what the cap raises — brief 09 §2).
    """
    return model.tax_rate


def compute_benefit_per_head(model):
    """Transfer received by each unemployed household this period (0 if none)."""
    return model.benefit


def compute_gov_transfers(model):
    """Total tax collected = total benefit distributed (balanced budget, brief 09).

    Equal to the levy exactly by construction (the tax hits only the positive part of
    accrued income, so collections and benefits paid coincide even when the cap binds).
    """
    return model.gov_transfers


def compute_tax_at_cap(model):
    """1.0 if the balanced-budget tax rate is pinned at ``max_tax`` this period, else 0.0.

    Instrument-saturation diagnostic (brief 09 report): its tail-average over a run is the
    fraction of steady-state periods in which the cap bound — i.e. the desired transfer
    needed a higher rate than ``max_tax`` allows and the benefit was scaled down.  0.0 when
    the government is off (``tax_rate = 0 < max_tax``).
    """
    return 1.0 if model.max_tax > 0.0 and model.tax_rate >= model.max_tax else 0.0


# --- heterogeneity diagnostics (brief 10) ---------------------------------

def compute_dead_firms(model):
    """Number of firms whose capital has fallen below ``DEAD_FIRM_K`` (brief 10).

    A pure REPORTING diagnostic: the model has no exit, so a "dead" firm keeps its
    customers, its demand share and its (empty) payroll — which is precisely the
    mechanism the probe is measuring, since demand routed to a firm that cannot produce
    is demand destroyed.  The threshold is a declared convention, not an estimate.
    """
    return float(sum(1 for f in _firms(model) if f.capital < DEAD_FIRM_K))


def compute_topk_share(model):
    """Share of aggregate capital held by the largest ``TOPK_N`` firms (brief 10).

    Concentration diagnostic for the dispersion probe.  It rises as the fan lets high-A
    firms out-accumulate low-A ones, and towards 1.0 as the weak firms die.  0.0 when
    there is no capital left at all (a fully collapsed economy has no distribution to
    report).

    ITS BASELINE IS NOT ``TOPK_N/num_firms``.  That is only its value at t = 0, where
    every firm starts with ``initial_capital``.  Even with A perfectly homogeneous the
    firms do NOT stay identical: consumption links are drawn at random, so firms face
    different demand, earn different profits and accumulate different capital.  Measured
    at the brief-10 scenarios (rho = 0.40, tail-50, seeds 0-2) the homogeneous baseline
    settles at 0.35-0.38, not 0.30.  So the firm side is quasi-representative in its
    AGGREGATES, not in its cross-section, and any reading of this reporter under
    dispersion must be against the measured spread = 0 baseline, never against 0.3.
    """
    caps = sorted((f.capital for f in _firms(model)), reverse=True)
    total = sum(caps)
    if total <= 0.0:
        return 0.0
    return sum(caps[:TOPK_N]) / total


# ============================================================
# Model
# ============================================================

class MacroModel(mesa.Model):
    """Normalised-CES core with an endogenous labour market and a fixed wage.

    Parameters
    ----------
    pct_capitalists : float
        Share of households that own firms — the inequality dimension of Teglio (2025).
        ``int(num_households * pct_capitalists)`` must be >= 1.  Ownership is assigned
        by cycling over the FIRMS (brief 12), so every firm has exactly one owner at
        any value: below ``num_firms / num_households`` a capitalist owns several
        firms, above it some capitalists own none (a declared case — a low-MPC
        household on labour income alone).  **Sweepable**: SFC holds across the range,
        and is tested there, not only at the default.
    sigma : float
        Elasticity of substitution between capital and labour.  ``1.0`` (default) is
        the Cobb-Douglas core and reproduces branch ``labour-market`` exactly;
        ``sigma -> 0`` approaches Leontief.  The empirical literature puts sigma
        below unity and rejects Cobb-Douglas — Chirinko (2008) 0.40–0.60, Chirinko &
        Mallick (2017) ~0.40, Knoblach, Roessler & Zwerschke (2020) meta-regression
        0.45–0.87; the Fed's SIGMA model uses 0.5.  Karabarbounis & Neiman (2014)
        dissent with sigma > 1.  Treated as a sweep, not a point estimate.
    pi0 : float
        Capital share at the base point (= the Cobb-Douglas capital elasticity, the
        old ``alpha``).  There is deliberately only one notion of the capital share
        in the code.
    K0, L0 : float
        Normalisation anchor, per firm.  A modelling choice, measured once and frozen
        — see the ANCHOR_* note at the top of this module.  ``Y0`` is *derived*
        (``A*K0^pi0*L0^(1-pi0)``), never measured.
    delta, productivity, initial_capital : float
        Depreciation, A, and K(0) per firm.  ``initial_capital`` is held fixed across
        any sigma/rho grid: the model has multiple equilibria and a viability
        threshold near rho = 0.30, so K(0) selects the basin.
    productivity_spread : float
        Half-width of a mean-preserving linear fan of firm productivities around
        ``productivity`` (brief 10 probe): firm ``i`` gets
        ``A_i = productivity*(1 + spread*(2i-(n-1))/(n-1))``.  ``0.0`` (default) makes
        every firm identical and reproduces the homogeneous model bit-for-bit.  This is
        an EXPERIMENTAL DIAL, not a calibrated parameter and not an implementation of
        roadmap point 8: there is no selection, reallocation, rewiring or entry/exit, so
        a firm the fan makes unproductive simply accumulates less capital while keeping
        its demand share.  Its purpose is to *measure* the viability threshold of the
        homogeneity assumption (see parameter_notes.md).  Must lie in ``[0, 1)``.
    wage_rate : float
        The wage-curve *normalisation point* ``w_bar`` per employed worker (brief 07):
        the wage paid at ``U = U_REF``, and the value the wage holds at every U when
        ``eta = 0``.  This is the distributive parameter (it replaced ``markup``):
        profit is the residual ``sales - w_t*L``, so the wage share is a measured
        outcome, bounded above by the profit-max wage share (``1-pi0`` only at sigma = 1).
    eta : float
        Wage-curve elasticity (Blanchflower-Oswald).  ``0.0`` (default) fixes the wage at
        ``w_bar`` and reproduces the pre-brief-07 model bit-for-bit; ``eta > 0`` lets the
        wage fall with last period's unemployment, ``w_t = w_bar*(U/U_REF)**(-eta)``,
        floored at ``wage_floor``.  Empirical range ~0.07-0.10 (Nijkamp & Poot 2005;
        Blanchflower & Oswald 1994); swept, not chosen.
    wage_floor : float
        Subsistence floor ``w_min`` on the wage (a design target, not anchored): guards
        the deflationary spiral at high ``eta``.  Cells where it binds stably are mapped
        and reported, not hidden.
    retention_ratio, beta, target_utilization, investment_floor : float
        Internal-financing investment rule (unchanged from the core).
    expectation_gain : float
        Gain ``lambda_e`` on the adaptive demand-expectation update (brief 08),
        ``Ye_t = Ye_{t-1} + lambda_e*(D_{t-1} - Ye_{t-1})``.  ``1.0`` (default) is static
        expectations, ``Ye_t = D_{t-1}``, and reproduces the pre-brief-08 model bit-for-bit;
        ``lambda_e < 1`` damps the firm's reaction to the last observation.  Must lie in
        ``[0, 1]``; ``lambda_e = 0`` (frozen expectations) is degenerate and only used in
        unit tests, never swept.  No reliable point estimate exists for an ABM of this kind
        (adaptive expectations, Nerlove 1958; constant-gain learning, Evans & Honkapohja
        2001), so it is swept, not chosen (see parameter_notes.md).
    c0, c1, capitalist_mpc, wealth_effect : float
        Consumption function terms.  ``c0`` and ``wealth_effect`` are demand levers
        (chosen values, not empirical estimates).
    benefit_replacement_rate : float
        Unemployment benefit as a fraction of the *current* wage ``w_t`` (brief 09),
        funded by a flat income tax whose rate adjusts to balance the budget each period.
        ``0.0`` (default) turns the government off and reproduces the pre-brief-09 model
        bit-for-bit; ``> 0`` closes the demand leak from the unemployed (who are
        cash-constrained, so their MPC ~ 1) via the balanced-budget multiplier.  The
        benefit is indexed to ``w_t``, not ``w_bar``, so at high ``U`` the wage curve
        lowers it (a procyclical floor — reported, not hidden).  Anchorable to OECD net
        replacement rates (see parameter_notes.md); swept, not chosen.  Must be >= 0.
    max_tax : float
        Cap on the balanced-budget tax rate (a declared convention/guardrail, not an
        estimate).  When the desired transfer would need more, the benefit is scaled
        down to what the cap raises — the budget stays balanced.  Must lie in [0, 1].
    seed : int or None
        Seed for the model's random stream (network, hiring/firing order).

    Notes
    -----
    The workforce cap ``L <= N`` (there are only ``num_households`` workers) is what
    restores decreasing returns to capital: with unlimited labour and a fixed wage,
    ``L_profitmax ∝ K`` gives ``Y* ∝ K`` (an AK model with no steady state).
    """

    def __init__(
        self,
        num_firms=10,
        num_households=100,
        pct_capitalists=0.10,

        # Technology
        sigma=1.0,
        pi0=1.0 / 3.0,
        K0=ANCHOR_K0,
        L0=ANCHOR_L0,
        delta=0.05,
        productivity=1.0,
        initial_capital=40.0,

        # Firm heterogeneity probe (brief 10): spread = 0 nests the homogeneous model
        productivity_spread=0.0,

        # Distribution
        wage_rate=0.9,

        # Wage curve (brief 07): eta = 0 nests the fixed-wage model exactly
        eta=0.0,
        wage_floor=0.45,

        # Internal financing / investment
        retention_ratio=0.40,
        beta=0.5,
        target_utilization=0.90,
        investment_floor=0.10,

        # Expectations (brief 08): expectation_gain = 1 nests the static-expectations model
        expectation_gain=1.0,

        # Consumption
        c0=2.0,
        c1=0.9,
        capitalist_mpc=0.4,
        wealth_effect=0.05,

        # Government (brief 09): rr = 0 nests the no-government model exactly
        benefit_replacement_rate=0.0,
        max_tax=0.6,

        seed=None,
    ):
        super().__init__(seed=seed)

        if not (0.0 < pi0 < 1.0):
            raise ValueError("pi0 must be in (0, 1)")
        if sigma <= 0.0:
            raise ValueError("sigma must be > 0")
        if K0 <= 0.0 or L0 <= 0.0:
            raise ValueError("the normalisation anchor (K0, L0) must be positive")
        if not (0.0 <= expectation_gain <= 1.0):
            raise ValueError("expectation_gain (lambda_e) must be in [0, 1]")
        if benefit_replacement_rate < 0.0:
            raise ValueError("benefit_replacement_rate must be >= 0")
        if not (0.0 <= max_tax <= 1.0):
            raise ValueError("max_tax must be in [0, 1]")
        # [0, 1): at spread = 1 the weakest firm has A = 0 (it can never produce), which
        # is an exit event the model has no machinery for — excluded rather than silently
        # producing a permanently dead firm.
        if not (0.0 <= productivity_spread < 1.0):
            raise ValueError("productivity_spread must be in [0, 1)")
        # Ownership is assigned by cycling over the firms (brief 12), which needs at
        # least one capitalist to cycle onto.  An economy whose firms have no owner is
        # not defined here: the dividends and the residual buffer would have nowhere to
        # go and money would be destroyed — precisely the defect brief 12 removes.
        if int(num_households * pct_capitalists) < 1:
            raise ValueError(
                "pct_capitalists must leave at least one capitalist "
                f"(got {pct_capitalists} x {num_households} households -> 0)"
            )

        # --- parameters -------------------------------------------------
        self.num_firms = num_firms
        self.num_households = num_households

        self.sigma = sigma
        self.pi0 = pi0
        self.K0 = K0
        self.L0 = L0
        #: Base-point capacity — derived, not a free parameter (brief 04 §2.3).
        self.Y0 = _Y0(productivity, K0, L0, pi0)
        self.delta = delta
        #: The economy-wide A — with a spread this is the MEAN of the firm fan, and the
        #: value the aggregate benchmarks (Potential_Output, Wage_Share_Profitmax) use.
        self.productivity = productivity
        self.productivity_spread = productivity_spread

        # Wage: ``w_bar`` is the normalisation point of the wage curve (the old fixed
        # wage); ``wage_rate`` is the *current* wage, set each period by the curve on
        # last period's unemployment.  They coincide identically when eta = 0.
        self.w_bar = wage_rate
        self.wage_rate = wage_rate
        self.eta = eta
        self.wage_floor = wage_floor
        #: Below the workforce resolution U is not observable; guards w -> inf at U = 0.
        self.U_min = 1.0 / num_households if num_households > 0 else 0.0

        self.retention_ratio = retention_ratio
        self.beta = beta
        self.target_utilization = target_utilization
        self.investment_floor = investment_floor

        # Adaptive expectations (brief 08): the gain on the demand-expectation update in
        # Firm.step_production.  1.0 (default) is static expectations (Ye = last demand).
        self.expectation_gain = expectation_gain

        self.c0 = c0
        self.c1 = c1
        self.capitalist_mpc = capitalist_mpc
        self.wealth_effect = wealth_effect

        # Government (brief 09): balanced-budget unemployment benefit.
        self.benefit_replacement_rate = benefit_replacement_rate
        self.max_tax = max_tax

        # --- economy-wide flow variables --------------------------------
        self.total_investment_demand = 0.0
        self.total_investment_realised = 0.0
        self.investment_rationing = 1.0
        # Fiscal flow variables (brief 09) — set here so the t = 0 DataCollector.collect
        # can read them before the government step ever runs.
        self.tax_rate = 0.0
        self.benefit = 0.0
        self.gov_transfers = 0.0

        # --- build firms ------------------------------------------------
        # Each firm carries its OWN A_i from the fan (brief 10).  At the default
        # spread = 0 every A_i is ``productivity`` itself, so this is the previous
        # construction unchanged and the RNG is untouched either way.
        self.productivity_by_firm = productivity_fan(
            productivity, num_firms, productivity_spread
        )
        firms = [
            Firm(self, productivity=A_i, initial_capital=initial_capital)
            for A_i in self.productivity_by_firm
        ]

        # --- build households -------------------------------------------
        num_capitalists = int(num_households * pct_capitalists)
        capitalists = []
        for i in range(num_households):
            if i < num_capitalists:
                household = Capitalist(self)
                capitalists.append(household)
            else:
                household = Household(self)

            # Initial employment: assign round-robin (fully employed at t=0).
            employer = firms[i % num_firms]
            household.employed = True
            household.employer = employer
            employer.workers.append(household)

            num_links = max(1, num_firms // 2)
            linked = self.random.sample(firms, num_links)
            household.consumption_firms = linked
            household.num_consumption_links = len(linked)
            for firm in linked:
                firm.customers.append(household)

        # --- assign ownership -------------------------------------------
        # Cycle over the FIRMS, not the households (brief 12).  This runs in its own
        # loop, after the one above, and draws nothing from the RNG: the sequence of
        # ``self.random.sample`` calls is untouched, so the default configuration stays
        # bit-for-bit identical (at 10 capitalists and 10 firms ``j % 10 == j``, i.e.
        # exactly the old household-indexed assignment).
        #
        # The old assignment cycled over households, which broke outside the default:
        # below it firms were left ownerless and their dividends and residual buffer
        # vanished (money destroyed, SFC violated); above it the assignment overwrote
        # itself, leaving capitalists with a stale ``owned_firm`` whose capital they
        # still counted in ``net_worth`` (wealth double-counted, Gini inflated).
        # Cycling over the firms gives every firm exactly one owner for any
        # ``num_capitalists >= 1``, so no flow can leak at any ``pct_capitalists``.
        for j, firm in enumerate(firms):
            owner = capitalists[j % num_capitalists]
            firm.owner = owner
            owner.owned_firms.append(firm)

        # Initial expectations so the first-period labour market is not a shock.  Each
        # firm expects what IT could produce, i.e. with its own A_i (brief 10): seeding a
        # low-A firm with the average firm's capacity would hand it an expectation it can
        # never meet and confound the probe with a start-of-run shock.
        for f in firms:
            f.expected_demand = ces_capacity(
                initial_capital, len(f.workers), f.productivity, K0, L0, pi0, sigma
            )
            f.utilization_last_period = target_utilization

        # --- data collection --------------------------------------------
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Output": compute_output,
                "Expected_Demand": compute_expected_demand,
                "Potential_Output": compute_potential_output,
                # Two gaps, deliberately: gap_N is unused heads (headline), gap_pm is
                # unused capacity.  See compute_output_gap (brief 05 §5.3).
                "Output_Gap": compute_output_gap,
                "Potential_Output_PM": compute_potential_output_profitmax,
                "Output_Gap_PM": compute_output_gap_profitmax,
                "Unemployment_Rate": compute_unemployment,
                "Employment": compute_employment,
                "Total_Capital": compute_aggregate_capital,
                "Money_Buffer": compute_total_money_buffer,
                "Consumption": compute_consumption,
                "Investment": compute_investment,
                "Average_Utilization": compute_average_utilization,
                "Wage_Share": compute_wage_share,
                "Wage_Share_Profitmax": compute_wage_share_profitmax,
                "Profit_Share": compute_profit_share,
                # Wage curve (brief 07): current wage and floor-binding flag.
                "Wage_Rate": compute_wage_rate,
                "Wage_Floor_Binding": compute_wage_floor_binding,
                "Income_Gini": compute_income_gini,
                "Wealth_Gini": compute_wealth_gini,
                # Which constraint bites (brief 04 §9.3)
                "Bound_Demand": compute_bound_by_demand,
                "Bound_Profitmax": compute_bound_by_profitmax,
                "Bound_Capital": compute_bound_by_capital,
                "Bound_Workforce": compute_bound_by_workforce,
                "Cash_Constrained": compute_cash_constrained_frac,
                # Fiscal diagnostics (brief 09): all identically 0 when rr = 0.
                "Tax_Rate": compute_tax_rate,
                "Benefit_Per_Head": compute_benefit_per_head,
                "Gov_Transfers": compute_gov_transfers,
                "Tax_At_Cap": compute_tax_at_cap,
                # Heterogeneity probe (brief 10): pure diagnostics.  Dead_Firms is 0 and
                # TopK_Share is TOPK_N/num_firms while the firms stay homogeneous.
                "Dead_Firms": compute_dead_firms,
                "TopK_Share": compute_topk_share,
            }
        )
        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    def labour_market(self, firms, households):
        """Fire the excess into an unemployed pool, then fill vacancies randomly.

        Workers are mobile: an unemployed household can be hired by any firm with a
        vacancy.  Firms may leave vacancies unfilled when the pool is empty (the
        ``L <= N`` cap), which is what caps aggregate employment at the workforce.
        """
        for f in firms:
            f.plan_employment()

        unemployed = [h for h in households if not h.employed]

        for f in firms:
            while len(f.workers) > f.desired_employment:
                worker = f.workers.pop()
                worker.employed = False
                worker.employer = None
                unemployed.append(worker)

        self.random.shuffle(unemployed)
        for f in firms:
            vacancies = f.desired_employment - len(f.workers)
            while vacancies > 0 and unemployed:
                worker = unemployed.pop()
                worker.employed = True
                worker.employer = f
                f.workers.append(worker)
                vacancies -= 1
            # Diagnostic: the pool ran dry, so the workforce is what bites here.
            f.labour_rationed = len(f.workers) < f.desired_employment

    # ------------------------------------------------------------------
    def government(self, households):
        """Balanced-budget unemployment benefit: a flat tax funds equal transfers (brief 09).

        A flat rate ``tau`` is levied on this period's accrued income (``next_income``)
        and the whole take is split equally among the unemployed.  The rate adjusts so
        collections equal the desired transfer, capped at ``max_tax`` (then the benefit is
        scaled down to what the cap raises).  Being a pure transfer, it conserves money.

            base      = sum(max(0, next_income))                over all households
            desired   = benefit_replacement_rate * w_t * n_unemployed
            tau       = min(max_tax, desired / base)            if base > 0 and desired > 0
            collected = tau * base
            benefit   = collected / n_unemployed               (0 if none unemployed)

        TAX BASE — positive part only.  A capitalist's residual dividend can be negative
        (gross profit below the retention planned on last period's profit), so
        ``next_income`` is occasionally < 0 (measured: down to ~-0.007 at sigma=1.5,
        c0=2.0, eta=0.10).  The levy is taken on ``max(0, next_income)`` so the total
        collected equals the tax base exactly; scaling the whole ``next_income`` by
        ``(1 - tau)`` would instead REFUND a negative-income household and break the
        balanced budget (hence money conservation).  With this rule
        ``sum(levies) == collected == sum(benefits)`` identically, cap or no cap.

        BENEFIT INDEXED TO ``w_t`` — the *current* wage-curve wage, not ``w_bar``: a
        replacement rate is a fraction of the prevailing wage.  Consequence (reported):
        at high ``U`` the wage curve lowers ``w_t`` and hence the benefit, so the demand
        floor is procyclical.

        NO RESERVATION WAGE / labour-supply incentive: the unemployed always accept work;
        the benefit changes only their income, never their willingness to be hired
        (declared out of scope, brief 09 §8).

        ``benefit_replacement_rate = 0`` short-circuits the entire step (no tax, no
        transfer, the RNG untouched), which is what makes the default nest the
        pre-brief-09 model bit-for-bit.
        """
        if self.benefit_replacement_rate == 0.0:
            self.tax_rate = 0.0
            self.benefit = 0.0
            self.gov_transfers = 0.0
            return

        unemployed = [h for h in households if not h.employed]
        n_unemployed = len(unemployed)

        base = sum(max(0.0, h.next_income) for h in households)
        desired = self.benefit_replacement_rate * self.wage_rate * n_unemployed

        if base > 0.0 and desired > 0.0:
            self.tax_rate = min(self.max_tax, desired / base)
        else:
            self.tax_rate = 0.0

        collected = self.tax_rate * base
        self.benefit = collected / n_unemployed if n_unemployed > 0 else 0.0
        self.gov_transfers = collected

        for h in households:
            h.next_income -= self.tax_rate * max(0.0, h.next_income)
        for h in unemployed:
            h.next_income += self.benefit

    # ------------------------------------------------------------------
    def step(self):
        households = _households(self)
        firms = _firms(self)

        # 0. wage determination (brief 07): set w_t from LAST period's unemployment,
        #    BEFORE the labour market.  Fixing the wage on U_{t-1} (not U_t) avoids the
        #    simultaneity w <-> U within the period — the only sequence change in brief 07,
        #    declared here.  At start-of-step the households' `employed` flags are still
        #    last period's, so compute_unemployment reads U_{t-1}.  eta = 0 is
        #    short-circuited to w_bar so the fixed-wage model is reproduced bit-for-bit
        #    (no float pow), mirroring the sigma = 1 branch in ces_capacity.  The t = 0
        #    round-robin start has U = 0, so the U_min guard makes w spike for a single
        #    period — documented, irrelevant to the tail-50 steady state.
        if self.eta == 0.0:
            self.wage_rate = self.w_bar
        else:
            U_prev = compute_unemployment(self)
            self.wage_rate = wage_from_curve(
                self.w_bar, U_prev, self.eta, U_REF, self.U_min, self.wage_floor
            )

        # 1. labour market (employment set before demand)
        self.labour_market(firms, households)

        # 2. consumption demand
        for h in households:
            h.step_demand()

        # 3. firms plan investment
        for f in firms:
            f.plan_investment()
        self.total_investment_demand = sum(f.desired_investment for f in firms)

        # 4. firms register demand
        for f in firms:
            f.register_demand()

        # 5. production + goods-market rationing
        for f in firms:
            f.step_production()
        self.investment_rationing = (
            sum(f.rationing for f in firms) / len(firms) if firms else 1.0
        )

        # 6. firm accounting
        for f in firms:
            f.step_accounting()

        # 7. investment settlement (buffer -> 0)
        for f in firms:
            f.step_investment()
        self.total_investment_realised = sum(f.investment_delivered for f in firms)

        # 8. government (brief 09): balanced-budget benefit on fully-accrued income.
        #    AFTER step 7 (the residual dividend is the last next_income accrual) and
        #    BEFORE settlement, so the tax hits the period's full income and the benefit
        #    reaches the unemployed with the same one-period lag as a wage.  rr = 0 makes
        #    this a no-op that leaves the RNG and every accrual untouched.
        self.government(households)

        # 9. household settlement
        for h in households:
            h.step_settlement()

        self.datacollector.collect(self)

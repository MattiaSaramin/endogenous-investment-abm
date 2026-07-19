"""
Behavioural and accounting tests for the normalised-CES core with an endogenous
labour market (roadmap point 11 + brief 04).

Run with ``pytest`` from the repository root.  The suite pins down:

* **Stock-flow consistency** — money (incl. the infra-period buffer) is conserved
  even with unemployed households; the buffer returns to zero every period.
* **Distribution** — fixed wage; profit is the residual and stays positive; the
  wage share is a measured outcome bounded above by the *sigma-dependent*
  profit-max wage share (``1 - pi0`` only at sigma = 1).
* **Labour-market accounting** — headcounts add up, ``L_agg <= N`` (the cap that
  prevents the AK degeneration), no hiring beyond the profit-max point.
* **The demand channel bites** (the point of point 11): a negative demand shock
  lowers employment and the wage bill.
* **CES nesting** — sigma = 1 is exactly Cobb-Douglas, sigma -> 0 is Leontief,
  sigma -> inf is linear; the base point and its factor shares are invariant to
  sigma (the defining property of the normalisation).
* **Reproducibility and stability.**
"""

import math

import numpy as np
import pandas as pd
import pytest

from model import (
    MacroModel,
    ANCHOR_K0,
    ANCHOR_L0,
    U_REF,
    wage_from_curve,
    compute_gini,
    compute_output_gap,
    compute_output_gap_profitmax,
    _households,
    _firms,
)
from experiment import (
    bootstrap_sigma_star,
    cells_from_panel,
    common_viable_support,
    ols_slope,
    quadratic_curvature,
    run_grid_panel,
    run_grid_panels,
    sigma_star_interp,
    slopes_by_sigma,
    _PANEL_METRICS,
    _gradient_weights,
)
from agents import (
    Firm,
    Household,
    Capitalist,
    R_EPS,
    adaptive_expectation,
    ces_capacity,
    ces_capital_ceiling,
    ces_labour_for_demand,
    ces_labour_profitmax,
    ces_mpl,
    ces_wage_share_profitmax,
    _Y0,
)


STEPS = 1500
PI0 = 1.0 / 3.0
REF_RHO = 0.40          # a viable, demand-constrained reference scenario

# The anchor and A = 1 as used by MacroModel's defaults.
K0, L0 = ANCHOR_K0, ANCHOR_L0
A = 1.0
Y0 = _Y0(A, K0, L0, PI0)

#: sigma values swept in the unit tests: Leontief probe, the central empirical
#: range (Chirinko 2008; Chirinko & Mallick 2017; Knoblach et al. 2020), Cobb-Douglas,
#: and the Karabarbounis-Neiman sigma > 1 puzzle.
SIGMAS = [0.05, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5]

CES = dict(K0=K0, L0=L0, pi0=PI0)


def cap(K, L, sigma, A=A):
    return ces_capacity(K, L, A, K0, L0, PI0, sigma)


def total_money(model):
    hh = sum(h.wealth + h.income + h.next_income for h in _households(model))
    return hh + sum(f.money_buffer for f in _firms(model))


def _steady(retention_ratio=REF_RHO, seed=0, steps=STEPS, tail=50, **kw):
    m = MacroModel(retention_ratio=retention_ratio, seed=seed, **kw)
    for _ in range(steps):
        m.step()
    return m.datacollector.get_model_vars_dataframe().tail(tail).mean()


# ----------------------------------------------------------------------
# Stock-flow consistency
# ----------------------------------------------------------------------

# eta is folded into the parametrization (brief 07 §7.4): the wage curve redistributes
# between wages and profits but must not touch the money circuit, so SFC has to hold at
# eta > 0 too.  eta = 0 keeps the original coverage.  lambda_e (expectation_gain) is folded
# in the same way (brief 08 §6.4): a slower expectation only changes the labour plan, never
# the settlement, so conservation and the zero buffer must survive lambda_e < 1 too.
@pytest.mark.parametrize("rho,eta,lambda_e", [
    (0.35, 0.0, 1.0), (0.40, 0.0, 1.0), (0.40, 0.10, 1.0),
    (0.40, 0.0, 0.25), (0.40, 0.10, 0.5),
])
def test_money_is_conserved(rho, eta, lambda_e):
    model = MacroModel(retention_ratio=rho, seed=7, eta=eta, expectation_gain=lambda_e)
    initial = total_money(model)
    for _ in range(600):
        model.step()
        assert total_money(model) == pytest.approx(initial, abs=1e-7)


@pytest.mark.parametrize("rho,eta,lambda_e", [
    (0.35, 0.0, 1.0), (0.40, 0.0, 1.0), (0.40, 0.10, 1.0),
    (0.40, 0.0, 0.25), (0.40, 0.10, 0.5),
])
def test_buffer_returns_to_zero(rho, eta, lambda_e):
    model = MacroModel(retention_ratio=rho, seed=2, eta=eta, expectation_gain=lambda_e)
    for _ in range(300):
        model.step()
        for f in _firms(model):
            assert f.money_buffer == pytest.approx(0.0, abs=1e-9)


def test_distribution_identity():
    model = MacroModel(retention_ratio=REF_RHO, seed=3)
    for _ in range(300):
        model.step()
        for f in _firms(model):
            assert f.wage_bill + f.dividend_pool + f.retained == pytest.approx(
                f.sales, abs=1e-9
            )


def test_gross_profit_and_dividends_non_negative():
    """The firm never hires beyond MPL = w_bar, so profit stays >= 0; the residual
    payout is never negative (the owner never funds the firm)."""
    model = MacroModel(retention_ratio=REF_RHO, seed=5)
    for _ in range(600):
        model.step()
        for f in _firms(model):
            assert f.gross_profit >= -1e-9
            assert f.dividend_pool >= -1e-9


# ----------------------------------------------------------------------
# Labour-market accounting
# ----------------------------------------------------------------------

def test_employment_never_exceeds_workforce():
    """L_agg <= N by construction — the cap that restores decreasing returns."""
    model = MacroModel(retention_ratio=REF_RHO, seed=8)
    for _ in range(400):
        model.step()
        assert sum(len(f.workers) for f in _firms(model)) <= model.num_households


def test_headcount_adds_up():
    model = MacroModel(retention_ratio=REF_RHO, seed=2)
    for _ in range(200):
        model.step()
        households = _households(model)
        employed = [h for h in households if h.employed]
        roster = [w for f in _firms(model) for w in f.workers]
        assert len(roster) == len(employed)
        assert all(not h.employed or h in h.employer.workers for h in households)


def test_no_hiring_beyond_profit_max():
    model = MacroModel(retention_ratio=REF_RHO, seed=4)
    for _ in range(400):
        model.step()
        for f in _firms(model):
            assert len(f.workers) <= f.L_profitmax + 1.0   # +1 for integer floor


def test_wage_share_bounded_by_profitmax_share():
    """Fixed wage + no hiring past MPL = w_bar => wage share <= its profit-max value.

    The old bound ``<= 1 - alpha`` was the sigma = 1 special case: w*L/Y rises with L
    and the firm stops at L_profitmax, so the ceiling is the wage share *at* that
    point, which is ``(1-pi0) * z**(1-sigma)`` and collapses to ``1-pi0`` only when
    sigma = 1.  Updated rather than deleted (brief 04 §8).
    """
    for sigma in (0.5, 1.0, 1.25):
        s = _steady(sigma=sigma)
        ceiling = ces_wage_share_profitmax(A, 0.9, K0, L0, PI0, sigma)
        assert s["Wage_Share"] <= ceiling + 1e-6


def test_profitmax_wage_share_is_one_minus_pi0_only_at_sigma_one():
    """Pins the sigma = 1 collapse of the bound, and that it genuinely moves off it."""
    assert ces_wage_share_profitmax(A, 0.9, K0, L0, PI0, 1.0) == pytest.approx(1.0 - PI0)
    assert ces_wage_share_profitmax(A, 0.9, K0, L0, PI0, 0.5) != pytest.approx(1.0 - PI0)


def test_unemployment_in_bounds():
    model = MacroModel(retention_ratio=REF_RHO, seed=1)
    for _ in range(400):
        model.step()
        u = model.datacollector.get_model_vars_dataframe()["Unemployment_Rate"].iloc[-1]
        assert 0.0 <= u <= 1.0


# ----------------------------------------------------------------------
# CES nesting — exactness at the limits, invariance of the base point
# ----------------------------------------------------------------------

GRID_KL = [(K, L) for K in (1.0, 10.0, K0, 200.0) for L in (0.5, 3.0, L0, 60.0)]


@pytest.mark.parametrize("K,L", GRID_KL)
def test_sigma_one_is_exactly_cobb_douglas(K, L):
    """sigma = 1 must be the Cobb-Douglas core, not an approximation of it."""
    assert cap(K, L, 1.0) == pytest.approx(A * K**PI0 * L**(1.0 - PI0), rel=1e-12, abs=1e-9)


def _sigma_of_r(r):
    return 1.0 / (1.0 - r)


@pytest.mark.parametrize("K,L", GRID_KL)
def test_ces_r_branch_has_no_jump_at_the_cut(K, L):
    """The |r| < R_EPS Cobb-Douglas branch must not introduce a discontinuity.

    ``1/r`` is singular at r = 0 so the branch is mandatory; the risk it carries is a
    step at the cut.  Straddling |r| = R_EPS by 1% (branch on one side, CES formula
    on the other) must agree far more tightly than any economically meaningful
    difference.  sigma = 1 +/- 1e-9 lands deep inside the branch and must be the
    exact Cobb-Douglas limit.
    """
    cd = cap(K, L, 1.0)
    assert cap(K, L, 1.0 + 1e-9) == pytest.approx(cd, rel=1e-12)
    assert cap(K, L, 1.0 - 1e-9) == pytest.approx(cd, rel=1e-12)

    for sign in (+1.0, -1.0):
        inside = cap(K, L, _sigma_of_r(sign * 0.99 * R_EPS))    # -> CD branch
        outside = cap(K, L, _sigma_of_r(sign * 1.01 * R_EPS))   # -> CES formula
        assert inside == pytest.approx(outside, rel=1e-5)


#: Points off the base ray.  On the ray ``K/K0 == L/L0`` constant returns make
#: ``Y* = Y0*k~`` for *every* sigma, so the deviation from Cobb-Douglas is identically
#: zero there and a convergence *rate* has nothing to measure.
GRID_KL_OFF_RAY = [(K, L) for (K, L) in GRID_KL if abs(K / K0 - L / L0) > 1e-12]


@pytest.mark.parametrize("K,L", GRID_KL_OFF_RAY)
def test_ces_converges_to_cobb_douglas_linearly_in_r(K, L):
    """The CES *formula* (outside the branch) approaches Cobb-Douglas as r -> 0.

    The deviation is second order in the factor ratios and first order in r
    (~ (r/2)*pi0*(1-pi0)*(ln k~ - ln l~)^2), so it must shrink roughly in proportion
    to r.  This is what bounds the approximation error the branch accepts: at the cut
    r = 1e-6 it is ~1e-6 relative.
    """
    cd = cap(K, L, 1.0)
    errs = [abs(cap(K, L, _sigma_of_r(r)) - cd) / cd for r in (1e-2, 1e-3, 1e-4)]
    assert errs[0] > errs[1] > errs[2]
    assert errs[2] < 1e-3
    # first order in r: shrinking r tenfold shrinks the error ~tenfold
    assert errs[1] / errs[2] == pytest.approx(10.0, rel=0.05)


@pytest.mark.parametrize("sigma", SIGMAS)
def test_base_ray_is_exactly_linear_for_every_sigma(sigma):
    """Along ``K/K0 == L/L0`` constant returns give ``Y* = Y0*k~`` for every sigma."""
    for scale in (0.5, 1.0, 2.5):
        assert cap(K0 * scale, L0 * scale, sigma) == pytest.approx(Y0 * scale, rel=1e-12)


@pytest.mark.parametrize("K,L", GRID_KL)
def test_leontief_limit(K, L):
    """sigma -> 0 collapses to Y0 * min(K/K0, L/L0)."""
    expected = Y0 * min(K / K0, L / L0)
    assert cap(K, L, 0.01) == pytest.approx(expected, rel=0.05)


@pytest.mark.parametrize("K,L", GRID_KL)
def test_linear_limit(K, L):
    """sigma -> inf collapses to the linear Y0 * (pi0*K/K0 + (1-pi0)*L/L0)."""
    expected = Y0 * (PI0 * (K / K0) + (1.0 - PI0) * (L / L0))
    assert cap(K, L, 50.0) == pytest.approx(expected, rel=0.05)


@pytest.mark.parametrize("sigma", SIGMAS)
def test_base_point_is_invariant_to_sigma(sigma):
    """Y*(K0, L0) == Y0 for every sigma — the point of normalising."""
    assert cap(K0, L0, sigma) == pytest.approx(Y0, rel=1e-12, abs=1e-12)


@pytest.mark.parametrize("sigma", SIGMAS)
def test_base_point_factor_shares_are_invariant_to_sigma(sigma):
    """At (K0, L0) the factor shares are 1-pi0 and pi0 for every sigma.

    This is the defining property of the normalisation: if it fails, sigma-variants
    are not comparable and the whole sweep is an artefact of parameterisation.
    The capital share is taken as the residual of constant returns (Euler).
    """
    mpl = ces_mpl(K0, L0, A, K0, L0, PI0, sigma)
    labour_share = mpl * L0 / Y0
    assert labour_share == pytest.approx(1.0 - PI0, rel=1e-10)


# ----------------------------------------------------------------------
# CES formulas — validated against numerics, not trusted as algebra
# ----------------------------------------------------------------------

@pytest.mark.parametrize("sigma", SIGMAS)
@pytest.mark.parametrize("K", [5.0, K0, 150.0])
@pytest.mark.parametrize("w", [0.3, 0.9, 2.0])
def test_L_profitmax_matches_numerical_bisection(sigma, K, w):
    """The analytic L_profitmax must equal a bisection on MPL(L) = w.

    Guards the algebra of the inversion; if these disagree the formula is wrong and
    every economic reading downstream is noise.
    """
    analytic = ces_labour_profitmax(K, A, w, K0, L0, PI0, sigma)

    def mpl(L):
        return ces_mpl(K, L, A, K0, L0, PI0, sigma)

    lo, hi = 1e-9, 1e9
    if mpl(hi) > w:                     # MPL never falls to w -> no finite solution
        assert analytic == float("inf")
        return
    if mpl(lo) < w:                     # MPL below w even at L -> 0 -> never hire
        assert analytic == pytest.approx(0.0, abs=1e-9)
        return

    for _ in range(200):
        mid = math.sqrt(lo * hi)        # bisect in log space: L spans many decades
        if mpl(mid) > w:
            lo = mid
        else:
            hi = mid
    assert analytic == pytest.approx(math.sqrt(lo * hi), rel=1e-6)


@pytest.mark.parametrize("sigma", SIGMAS)
@pytest.mark.parametrize("K", [5.0, K0, 150.0])
def test_L_demand_inverts_capacity(sigma, K):
    """Where L_demand is finite and positive, Y*(K, L_demand) == Y_e exactly."""
    for Ye in (0.5, 5.0, Y0, 3.0 * Y0):
        L = ces_labour_for_demand(Ye, K, A, K0, L0, PI0, sigma)
        if L == float("inf") or L == 0.0:
            continue
        assert cap(K, L, sigma) == pytest.approx(Ye, rel=1e-9)


LADDER_L = (0.1, 0.5, 1.0, 3.0, L0, 20.0, 100.0)


@pytest.mark.parametrize("sigma", SIGMAS)
def test_mpl_is_non_increasing_in_labour(sigma):
    """Diminishing returns to labour at every sigma.

    Tolerance is 1e-12 relative because at sigma = 0.05 MPL sits on the flat
    Leontief plateau, where consecutive values differ only by rounding (see
    :func:`test_mpl_is_strictly_decreasing_in_labour`).
    """
    prev = float("inf")
    for L in LADDER_L:
        m = ces_mpl(K0, L, A, K0, L0, PI0, sigma)
        assert m <= prev * (1.0 + 1e-12)
        prev = m


@pytest.mark.parametrize("sigma", [s for s in SIGMAS if s >= 0.2])
def test_mpl_is_strictly_decreasing_in_labour(sigma):
    """Strict for every sigma float can resolve.

    Excludes sigma = 0.05: there the technology is within float precision of the
    Leontief kink, where MPL is *flat* at ``Y0/L0`` below the kink and zero above it.
    MPL is strictly decreasing in exact arithmetic for any sigma > 0, but at
    sigma = 0.05 the variation over L in [0.1, 3] falls below 1 ulp — saturation of
    the limit the model is deliberately probing, not a defect.
    """
    prev = float("inf")
    for L in LADDER_L:
        m = ces_mpl(K0, L, A, K0, L0, PI0, sigma)
        assert m < prev
        prev = m


# ----------------------------------------------------------------------
# Technology — regimes and edge cases
# ----------------------------------------------------------------------

@pytest.mark.parametrize("sigma", [0.3, 0.5, 1.0])
def test_capital_is_essential_only_for_sigma_at_most_one(sigma):
    """With zero capital, capacity and production are zero — for sigma <= 1."""
    model = MacroModel(seed=0, sigma=sigma)
    f = _firms(model)[0]
    f.capital = 0.0
    f.faced_demand = 10.0
    f.step_production()
    assert f.capacity == 0.0
    assert f.production == 0.0


def test_capital_is_not_essential_above_sigma_one():
    """sigma > 1: labour alone produces.  A property of the technology, not a bug —
    which is why the essentiality test is bounded to sigma <= 1 rather than deleted."""
    model = MacroModel(seed=0, sigma=1.5)
    f = _firms(model)[0]
    f.capital = 0.0
    f.faced_demand = 10.0
    f.step_production()
    assert f.capacity > 0.0
    assert f.production > 0.0


def test_capital_ceiling_binds_below_sigma_one():
    """sigma < 1: demand above Y_max(K) is unreachable at *any* finite L, so
    L_demand is +inf and the binding constraint is capital (trap 2 of the brief)."""
    sigma, K = 0.5, 10.0
    ceiling = ces_capital_ceiling(K, A, K0, L0, PI0, sigma)
    assert math.isfinite(ceiling)

    # No finite L reaches above the ceiling ...
    assert ces_labour_for_demand(ceiling * 1.5, K, A, K0, L0, PI0, sigma) == float("inf")
    # ... and huge L gets close to it but never past.
    assert cap(K, 1e7, sigma) < ceiling
    assert cap(K, 1e7, sigma) == pytest.approx(ceiling, rel=1e-3)

    # The firm must route this to "capital", not crash.
    model = MacroModel(seed=0, sigma=sigma)
    f = _firms(model)[0]
    f.capital = K
    f.expected_demand = ceiling * 1.5
    f.plan_employment()
    assert f.L_demand == float("inf")
    assert f.binding_constraint == "capital"
    assert 0 <= f.desired_employment <= model.num_households


def test_capital_ceiling_is_infinite_at_or_above_sigma_one():
    for sigma in (1.0, 1.5):
        assert ces_capital_ceiling(50.0, A, K0, L0, PI0, sigma) == float("inf")


def test_profitmax_may_not_exist_above_sigma_one():
    """sigma > 1 with a low wage: MPL has a positive floor, hiring is always
    profitable, L_profitmax = +inf and the workforce N becomes the constraint
    (trap 4 of the brief).  Must not crash."""
    sigma = 1.5
    r = (sigma - 1.0) / sigma
    mpl_floor = ((1.0 - PI0) ** (1.0 / r)) * (Y0 / L0)
    w = mpl_floor * 0.5

    assert ces_labour_profitmax(K0, A, w, K0, L0, PI0, sigma) == float("inf")

    model = MacroModel(seed=0, sigma=sigma, wage_rate=w)
    f = _firms(model)[0]
    f.expected_demand = 1e12          # demand no longer the binding limit
    f.plan_employment()
    assert f.L_profitmax == float("inf")
    assert f.desired_employment == model.num_households

    # The utilisation convention for an infinite profit-max scale: u = 0.
    f.faced_demand = 10.0
    f.step_production()
    assert f.profitmax_capacity == float("inf")
    assert f.utilization == 0.0


def test_never_hire_where_wage_exceeds_max_mpl_below_sigma_one():
    """sigma < 1: MPL has a finite maximum at L -> 0, so a high enough wage means the
    firm never hires (L_profitmax = 0) rather than hiring at a loss."""
    sigma = 0.5
    r = (sigma - 1.0) / sigma
    mpl_max = ((1.0 - PI0) ** (1.0 / r)) * (Y0 / L0)
    assert ces_labour_profitmax(K0, A, mpl_max * 1.5, K0, L0, PI0, sigma) == 0.0
    assert ces_labour_profitmax(K0, A, mpl_max * 0.5, K0, L0, PI0, sigma) > 0.0


@pytest.mark.parametrize("sigma", [0.05, 0.2])
def test_small_sigma_is_numerically_clean(sigma):
    """Strongly negative r overflows a naive (K/K0)**r; 2000 steps must stay finite."""
    model = MacroModel(retention_ratio=REF_RHO, seed=0, sigma=sigma)
    for _ in range(2000):
        model.step()
    df = model.datacollector.get_model_vars_dataframe()
    assert df.select_dtypes("number").notna().all().all()
    for col in ("Output", "Total_Capital", "Employment"):
        assert math.isfinite(float(df[col].iloc[-1]))


def test_sigma_must_be_positive():
    with pytest.raises(ValueError):
        MacroModel(seed=0, sigma=0.0)


# ----------------------------------------------------------------------
# The demand channel must bite (the point of the task)
# ----------------------------------------------------------------------

def test_demand_shock_lowers_employment_and_wage_bill():
    """A negative demand shock (lower c0) must reduce employment and the wage
    bill; otherwise the labour market is cosmetic."""
    strong = _steady(c0=2.0)
    weak = _steady(c0=1.2)

    assert weak["Employment"] < strong["Employment"] - 1.0
    strong_wage_bill = strong["Wage_Share"] * strong["Output"]
    weak_wage_bill = weak["Wage_Share"] * weak["Output"]
    assert weak_wage_bill < strong_wage_bill


# ----------------------------------------------------------------------
# Retention, capital, stability
# ----------------------------------------------------------------------

def test_capital_increases_in_retention():
    """More retention -> more capital (robust, regardless of the output sign)."""
    caps = [_steady(retention_ratio=r)["Total_Capital"] for r in (0.35, 0.40, 0.45)]
    assert all(b >= a - 1e-6 for a, b in zip(caps, caps[1:]))


def test_reference_is_viable_and_bounded():
    """The reference neither collapses (Y -> 0) nor diverges (AK growth): output
    stays in a bounded plausible band over a long run (mild oscillation is fine)."""
    model = MacroModel(retention_ratio=REF_RHO, seed=0)
    tail = []
    for t in range(2000):
        model.step()
        if t >= 1500:
            tail.append(sum(f.production for f in _firms(model)))
    assert min(tail) > 50.0        # no collapse
    assert max(tail) < 300.0       # no AK divergence
    assert max(tail) - min(tail) < 0.15 * (sum(tail) / len(tail))  # bounded fluctuation


def test_seed_is_deterministic():
    def final_output(seed):
        m = MacroModel(retention_ratio=REF_RHO, seed=seed)
        for _ in range(300):
            m.step()
        return m.datacollector.get_model_vars_dataframe()["Output"].iloc[-1]

    assert final_output(42) == final_output(42)
    assert final_output(1) != final_output(2)


# ----------------------------------------------------------------------
# sigma = 1 must remain the Cobb-Douglas core (brief 04 §10.1)
# ----------------------------------------------------------------------

#: Reference steady states measured on branch ``labour-market`` (the Cobb-Douglas
#: core, before the CES generalisation): 2000 steps, mean of the last 50
#: observations, all parameters at their defaults.  Verified bit-identical when the
#: CES core was introduced (105/105 comparisons, deviation 0.0, over
#: rho in {0.0 .. 0.6} x seeds {0,1,2}).  This pins that identity against drift.
LABOUR_MARKET_REFERENCE = {
    (0.40, 0): {
        "Output": 132.0262597647814,
        "Total_Capital": 417.2699329350551,
        "Employment": 74.3,
        "Unemployment_Rate": 0.257,
        "Wage_Share": 0.5064034061959125,
    },
    (0.60, 1): {
        "Output": 125.20471902508955,
        "Total_Capital": 612.3052742675798,
        "Employment": 56.64,
        "Unemployment_Rate": 0.43360000000000004,
        "Wage_Share": 0.40712541619806286,
    },
}


@pytest.mark.parametrize("key", sorted(LABOUR_MARKET_REFERENCE))
def test_sigma_one_reproduces_the_labour_market_branch(key):
    """The default (sigma = 1) must reproduce the pre-CES branch to 1e-9.

    If this fails, the sigma sweep is measuring the reimplementation, not sigma.
    """
    rho, seed = key
    s = _steady(retention_ratio=rho, seed=seed, steps=2000, sigma=1.0)
    for metric, expected in LABOUR_MARKET_REFERENCE[key].items():
        assert float(s[metric]) == pytest.approx(expected, abs=1e-9)


# ----------------------------------------------------------------------
# Invariants across the sigma x rho grid
# ----------------------------------------------------------------------

GRID_SIGMA = [0.3, 0.5, 1.0, 1.25]
GRID_RHO = [0.40, 0.60]


@pytest.mark.parametrize("c0", [1.0, 2.0])
@pytest.mark.parametrize("seed", [0, 1])
@pytest.mark.parametrize("rho", GRID_RHO)
@pytest.mark.parametrize("sigma", GRID_SIGMA)
def test_invariants_hold_across_the_grid(sigma, rho, seed, c0):
    """SFC, the zero buffer, the distribution identity and the labour accounting
    must survive every cell of the sigma x rho x c0 grid, not just sigma = 1.

    c0 joins the grid in brief 05: it is swept as a full dimension there, so the
    invariants have to hold across it too — a demand lever that broke stock-flow
    consistency would invalidate every c0 comparison the task rests on.
    """
    model = MacroModel(retention_ratio=rho, seed=seed, sigma=sigma, c0=c0)
    initial = total_money(model)
    for _ in range(250):
        model.step()

        assert total_money(model) == pytest.approx(initial, abs=1e-9)

        employed = 0
        for f in _firms(model):
            assert f.money_buffer == pytest.approx(0.0, abs=1e-9)
            assert f.wage_bill + f.dividend_pool + f.retained == pytest.approx(
                f.sales, abs=1e-9
            )
            assert f.gross_profit >= -1e-9
            assert f.dividend_pool >= -1e-9
            assert math.isfinite(f.capital) and f.capital >= 0.0
            employed += len(f.workers)

        households = _households(model)
        assert employed <= model.num_households
        assert employed + sum(1 for h in households if not h.employed) == len(households)

    row = model.datacollector.get_model_vars_dataframe().iloc[-1]
    assert 0.0 <= float(row["Wage_Share"]) <= 1.0
    assert 0.0 <= float(row["Unemployment_Rate"]) <= 1.0


@pytest.mark.parametrize("sigma", GRID_SIGMA)
def test_seed_determinism_across_sigma(sigma):
    def final_output(seed):
        m = MacroModel(retention_ratio=REF_RHO, seed=seed, sigma=sigma)
        for _ in range(200):
            m.step()
        return m.datacollector.get_model_vars_dataframe()["Output"].iloc[-1]

    assert final_output(42) == final_output(42)


@pytest.mark.parametrize("sigma", GRID_SIGMA)
def test_binding_constraint_shares_sum_to_one(sigma):
    model = MacroModel(retention_ratio=REF_RHO, seed=0, sigma=sigma)
    for _ in range(200):
        model.step()
    row = model.datacollector.get_model_vars_dataframe().iloc[-1]
    total = sum(
        float(row[c])
        for c in ("Bound_Demand", "Bound_Profitmax", "Bound_Capital", "Bound_Workforce")
    )
    assert total == pytest.approx(1.0)


# ----------------------------------------------------------------------
# The Gini helper
# ----------------------------------------------------------------------

def test_gini_bounds():
    assert compute_gini([5, 5, 5, 5]) == pytest.approx(0.0)
    assert compute_gini([0, 0, 0, 100]) == pytest.approx(0.75)
    assert compute_gini([]) == 0.0
    assert compute_gini([1, 2, 3]) == pytest.approx(compute_gini([10, 20, 30]))


# ======================================================================
# Brief 05 — the robustness stack
# ======================================================================

# ----------------------------------------------------------------------
# The two output gaps (brief 05 §5.3)
# ----------------------------------------------------------------------

@pytest.mark.parametrize("sigma", [0.3, 0.5, 1.0, 1.5])
@pytest.mark.parametrize("c0", [1.0, 2.0])
def test_profitmax_gap_never_exceeds_full_employment_gap(sigma, c0):
    """``gap_pm <= gap_N`` — the ordering the two definitions must have.

    ``min(sum L_pm, N) <= N`` and the CES is non-decreasing in labour, so the
    profit-max potential is the weaker benchmark and its gap the smaller one.  If this
    inverts, one of the two is implemented against the wrong labour input (brief §9).
    """
    model = MacroModel(retention_ratio=REF_RHO, seed=0, sigma=sigma, c0=c0)
    for _ in range(300):
        model.step()
        assert compute_output_gap_profitmax(model) <= compute_output_gap(model) + 1e-9


def test_gaps_coincide_when_firms_would_hire_the_whole_workforce():
    """The two gaps are EQUAL whenever the firms' profit-max scale exceeds N.

    Not a tautology worth pinning for its own sake — it pins the *reason* the two
    definitions turn out to measure the same thing in this economy's viable region:
    at w_bar = 0.9 the firms would collectively hire far more than the 100 workers
    that exist, so the workforce, not the profit-max point, is what caps potential.
    """
    model = MacroModel(retention_ratio=REF_RHO, seed=0, sigma=1.0)
    for _ in range(300):
        model.step()

    assert sum(f.L_profitmax for f in _firms(model)) > model.num_households
    assert compute_output_gap_profitmax(model) == pytest.approx(
        compute_output_gap(model), rel=1e-12
    )


def test_gaps_are_finite_and_gini_in_bounds_across_the_grid():
    """No NaN/inf and no out-of-range shares in a living cell (brief §9)."""
    for sigma in (0.3, 1.0):
        s = _steady(sigma=sigma, steps=400)
        for col in ("Output_Gap", "Output_Gap_PM", "Income_Gini", "Wealth_Gini",
                    "Wage_Share", "Unemployment_Rate"):
            assert math.isfinite(float(s[col])), col
        for col in ("Income_Gini", "Wealth_Gini", "Wage_Share", "Unemployment_Rate"):
            assert 0.0 <= float(s[col]) <= 1.0, col


# ----------------------------------------------------------------------
# The regression pin — GATING (brief 05 §9, §10.1)
# ----------------------------------------------------------------------

#: Brief 04's committed grid (``ces_sigma_rho_grid.csv``) at sigma = 1.0, c0 = 2.0,
#: anchor rho = 0.40, seeds {0, 1, 2}, 2000 steps, mean of the last 50.  The CSV
#: carries 10 significant digits, which is what sets the tolerance below.
BRIEF04_GRID_REFERENCE = {
    0.40: {"Y": 131.8056201, "K": 418.7977892, "Employment": 73.97385621,
           "Unemployment_Rate": 0.2602614379, "Wage_Share": 0.5050298243},
    0.50: {"Y": 128.0175548, "K": 525.6635922, "Employment": 63.20261438,
           "Unemployment_Rate": 0.3679738562, "Wage_Share": 0.4442896486},
    0.60: {"Y": 126.3940834, "K": 620.1016309, "Employment": 57.09150327,
           "Unemployment_Rate": 0.4290849673, "Wage_Share": 0.4065135381},
}


def test_regression_pin_reproduces_brief04_grid():
    """The brief-05 panel path must reproduce brief 04's grid EXACTLY, same seeds.

    This is the gate on the whole task (brief §10.1): the new grid adds a c0 dimension,
    a denser rho grid, more seeds and a different derivative estimator, and none of
    that is comparable with brief 04 unless the underlying cells are identical.  If
    this fails, the two grids measure different things and every difference downstream
    is an artefact of the refactor rather than a finding.
    """
    panel = run_grid_panel(
        sigmas=[1.0], rhos=[0.40, 0.50, 0.60], seeds=3, steps=2000, workers=1, c0=2.0,
    )
    cells = cells_from_panel(panel)

    for _, row in cells.iterrows():
        expected = BRIEF04_GRID_REFERENCE[round(float(row["rho"]), 2)]
        for metric, value in expected.items():
            assert float(row[metric]) == pytest.approx(value, rel=1e-8), (
                f"rho={row['rho']} {metric}"
            )


# ----------------------------------------------------------------------
# The OLS slope and the sigma* interpolation
# ----------------------------------------------------------------------

def test_ols_slope_recovers_an_exact_line():
    slope, se = ols_slope([0.0, 1.0, 2.0, 3.0], [1.0, 3.0, 5.0, 7.0])
    assert slope == pytest.approx(2.0)
    assert se == pytest.approx(0.0, abs=1e-12)


def test_ols_slope_matches_numpy_polyfit_on_noisy_data():
    rng = np.random.default_rng(0)
    x = np.linspace(0.35, 0.65, 7)
    y = 3.0 - 40.0 * x + rng.normal(0, 2.0, x.size)
    slope, se = ols_slope(x, y)
    assert slope == pytest.approx(float(np.polyfit(x, y, 1)[0]), rel=1e-10)
    assert se > 0.0


def test_ols_slope_is_undefined_without_variation():
    assert all(math.isnan(v) for v in ols_slope([1.0, 1.0], [2.0, 3.0]))
    assert all(math.isnan(v) for v in ols_slope([1.0], [2.0]))
    # Exactly two points: the slope exists, the standard error cannot.
    slope, se = ols_slope([0.0, 1.0], [0.0, 5.0])
    assert slope == pytest.approx(5.0) and math.isnan(se)


def test_quadratic_curvature_recovers_an_exact_parabola():
    """``y = 2 - 3x + 5x**2``: curvature 5, turning point at x = 3/(2*5) = 0.3."""
    x = [0.0, 0.25, 0.5, 0.75, 1.0]
    y = [2.0 - 3.0 * xi + 5.0 * xi ** 2 for xi in x]
    c, se, turn = quadratic_curvature(x, y)
    assert c == pytest.approx(5.0)
    assert se == pytest.approx(0.0, abs=1e-9)
    assert turn == pytest.approx(0.3)


def test_quadratic_curvature_is_undefined_with_too_few_points():
    assert all(math.isnan(v) for v in quadratic_curvature([0.0, 1.0], [1.0, 2.0]))
    # Exactly three points: the coefficient and turning point exist, the SE cannot.
    c, se, turn = quadratic_curvature([0.0, 1.0, 2.0], [0.0, 1.0, 4.0])
    assert c == pytest.approx(1.0) and math.isnan(se) and turn == pytest.approx(0.0)


def test_sigma_star_interp_matches_a_hand_built_analytic_case():
    """Interpolated sigma* against a case whose answer is known by hand (brief §9).

    Slopes +10 at sigma = 0.5 and -10 at sigma = 1.0 are symmetric about zero, so the
    crossing sits exactly halfway, at 0.75.
    """
    star, crossings = sigma_star_interp([0.5, 1.0], [10.0, -10.0])
    assert star == pytest.approx(0.75)
    assert crossings == 1

    # Asymmetric slopes: the crossing sits proportionally nearer the smaller |slope|.
    star, _ = sigma_star_interp([0.0, 1.0], [3.0, -1.0])
    assert star == pytest.approx(0.75)


def test_sigma_star_is_undefined_when_the_sign_never_turns():
    """No crossing is a RESULT, reported as nan — not an error and not a dropped case."""
    star, crossings = sigma_star_interp([0.3, 0.5, 1.0], [5.0, 4.0, 3.0])
    assert math.isnan(star) and crossings == 0


def test_sigma_star_reports_multiple_crossings():
    """A non-monotone slope profile crosses more than once; the count must surface it,
    because a single point estimate would silently hide the structure."""
    star, crossings = sigma_star_interp([0.0, 1.0, 2.0, 3.0], [1.0, -1.0, 1.0, -1.0])
    assert crossings == 3
    assert star == pytest.approx(0.5)          # the first crossing, by convention


# ----------------------------------------------------------------------
# The bootstrap
# ----------------------------------------------------------------------

def _synthetic_panel(slopes, seeds=8, noise=0.0, rng_seed=0):
    """A panel with ``Y = 100 + slope(sigma)*rho`` and controllable inter-seed noise.

    Lets the bootstrap be tested against an answer known in closed form, with no
    simulation involved.
    """
    rng = np.random.default_rng(rng_seed)
    rows = []
    for sigma, slope in slopes.items():
        for rho in (0.4, 0.5, 0.6):
            for seed in range(seeds):
                y = 100.0 + slope * rho + (rng.normal(0, noise) if noise else 0.0)
                rows.append({"sigma": sigma, "rho": rho, "seed": seed, "Output": y})
    return pd.DataFrame(rows)


def test_gradient_weights_reproduce_numpy_gradient():
    """The finite-difference operator must be recovered exactly as a matrix.

    This is what lets ``sigma*(rho)`` and the OLS ``sigma*`` share one bootstrap; if
    the matrix drifted from ``numpy.gradient``, the brief-04-comparable view would
    silently stop being brief-04's estimator.
    """
    rho = np.array([0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65])
    G = _gradient_weights(rho)
    rng = np.random.default_rng(3)
    for _ in range(5):
        y = rng.normal(120.0, 10.0, rho.size)
        assert np.allclose(G @ y, np.gradient(y, rho), rtol=1e-12, atol=1e-12)


def test_bootstrap_is_deterministic_given_its_rng_seed():
    panel = _synthetic_panel({0.5: 20.0, 1.0: -20.0}, noise=3.0)
    a = bootstrap_sigma_star(panel, [0.4, 0.5, 0.6], n_resamples=200, rng_seed=123)
    b = bootstrap_sigma_star(panel, [0.4, 0.5, 0.6], n_resamples=200, rng_seed=123)
    assert (a["sigma_star"], a["ci_lo"], a["ci_hi"]) == (b["sigma_star"], b["ci_lo"], b["ci_hi"])

    c = bootstrap_sigma_star(panel, [0.4, 0.5, 0.6], n_resamples=200, rng_seed=456)
    assert (c["ci_lo"], c["ci_hi"]) != (a["ci_lo"], a["ci_hi"])


def test_bootstrap_recovers_the_analytic_sigma_star_without_noise():
    """Zero inter-seed variance: every resample is the same data, so the CI must
    collapse onto the analytic sigma* and nothing may be undefined."""
    panel = _synthetic_panel({0.5: 20.0, 1.0: -20.0}, noise=0.0)
    bs = bootstrap_sigma_star(panel, [0.4, 0.5, 0.6], n_resamples=200, rng_seed=7)

    assert bs["sigma_star"] == pytest.approx(0.75)
    assert bs["ci_lo"] == pytest.approx(0.75)
    assert bs["ci_hi"] == pytest.approx(0.75)
    assert bs["frac_undefined"] == 0.0
    assert bs["slopes"][0.5] == pytest.approx(20.0)


def test_bootstrap_counts_undefined_resamples_instead_of_dropping_them():
    """When no sigma in range turns the sign, sigma* is undefined in every resample.

    The contract that matters (brief §3.2.4): report the fraction, do not quietly drop
    those resamples and hand back a confident CI built on the survivors.
    """
    panel = _synthetic_panel({0.5: 20.0, 1.0: 10.0}, noise=1.0)
    bs = bootstrap_sigma_star(panel, [0.4, 0.5, 0.6], n_resamples=200, rng_seed=7)

    assert math.isnan(bs["sigma_star"])
    assert bs["frac_undefined"] == 1.0
    assert math.isnan(bs["ci_lo"]) and math.isnan(bs["ci_hi"])


def test_bootstrap_ci_widens_with_inter_seed_noise():
    quiet = bootstrap_sigma_star(
        _synthetic_panel({0.5: 20.0, 1.0: -20.0}, noise=0.5, rng_seed=1),
        [0.4, 0.5, 0.6], n_resamples=400, rng_seed=7,
    )
    loud = bootstrap_sigma_star(
        _synthetic_panel({0.5: 20.0, 1.0: -20.0}, noise=8.0, rng_seed=1),
        [0.4, 0.5, 0.6], n_resamples=400, rng_seed=7,
    )
    assert (loud["ci_hi"] - loud["ci_lo"]) > (quiet["ci_hi"] - quiet["ci_lo"])


# ----------------------------------------------------------------------
# Panel / cell plumbing
# ----------------------------------------------------------------------

def test_common_viable_support_drops_rho_collapsed_at_any_sigma():
    """A rho is in the common support only if EVERY sigma survives it — slopes taken
    on different supports would confound sigma with which cells happened to live."""
    cells = pd.DataFrame({
        "sigma": [0.5, 0.5, 1.0, 1.0],
        "rho": [0.35, 0.40, 0.35, 0.40],
        "collapsed": [False, False, True, False],
    })
    assert common_viable_support(cells) == [0.40]


def test_cells_from_panel_flags_a_mixed_basin():
    """Some seeds alive and some dead is a basin boundary, and must be visible rather
    than averaged into a mean that describes neither."""
    panel = pd.DataFrame({
        "sigma": [1.0] * 4,
        "rho": [0.35] * 4,
        "seed": [0, 1, 2, 3],
        "Output": [0.0, 0.0, 120.0, 130.0],
        "Bound_Demand": [0.0, 0.0, 1.0, 1.0],
        "Bound_Profitmax": [0.0] * 4,
        "Bound_Capital": [1.0, 1.0, 0.0, 0.0],
        "Bound_Workforce": [0.0] * 4,
    })
    cells = cells_from_panel(panel)
    assert bool(cells["mixed_basin"].iloc[0])
    assert cells["frac_seeds_collapsed"].iloc[0] == pytest.approx(0.5)
    assert not bool(cells["collapsed"].iloc[0])       # the mean is alive


def test_slopes_by_sigma_uses_only_the_common_support():
    cells = pd.DataFrame({
        "sigma": [1.0, 1.0, 1.0],
        "rho": [0.35, 0.40, 0.50],
        "Y": [999.0, 10.0, 20.0],       # 0.35 is an outlier excluded by the support
    })
    out = slopes_by_sigma(cells, support=[0.40, 0.50])
    assert out["dY_drho"].iloc[0] == pytest.approx(100.0)
    assert int(out["n_points"].iloc[0]) == 2


# ----------------------------------------------------------------------
# Wage curve (brief 07)
# ----------------------------------------------------------------------

W_BAR = 0.9
_WC = dict(U_ref=U_REF, U_min=0.01, w_min=0.45)


def test_wage_curve_equals_w_bar_at_u_ref():
    """At U = U_ref the wage is exactly w_bar — the normalisation point (brief 07 §2)."""
    assert wage_from_curve(W_BAR, U_REF, 0.10, **_WC) == pytest.approx(W_BAR, rel=1e-12)


def test_wage_curve_strictly_decreasing_in_u_for_positive_eta():
    us = [0.05, 0.10, 0.20, 0.30, 0.40]
    ws = [wage_from_curve(W_BAR, u, 0.10, **_WC) for u in us]
    assert all(b < a for a, b in zip(ws, ws[1:]))


def test_wage_curve_u_min_guard_caps_wage_at_zero_unemployment():
    """U = 0 must not send w -> inf: the U_min guard caps it (brief 07 §2)."""
    w = wage_from_curve(W_BAR, 0.0, 0.10, **_WC)
    assert math.isfinite(w)
    assert w == pytest.approx(W_BAR * (0.01 / U_REF) ** (-0.10), rel=1e-12)


def test_wage_curve_floor_binds_at_high_u():
    """A high U with high eta drives the raw wage below w_min; the floor catches it."""
    w = wage_from_curve(W_BAR, 0.95, 1.0, U_ref=U_REF, U_min=0.01, w_min=0.45)
    assert w == 0.45


def test_wage_curve_is_w_bar_for_any_u_when_eta_zero():
    """eta = 0 returns w_bar for every U — the nested fixed-wage case (brief 07 §2)."""
    for u in (0.0, 0.05, U_REF, 0.5, 0.99):
        assert wage_from_curve(W_BAR, u, 0.0, **_WC) == W_BAR


def test_eta_zero_nests_the_fixed_wage_model_bit_for_bit():
    """eta = 0 reproduces the pre-brief-07 trajectory exactly and holds w == w_bar for
    the whole run — protects the explicit eta == 0 branch in step() (brief 07 §7.2)."""
    m = MacroModel(retention_ratio=REF_RHO, seed=0, sigma=1.0, eta=0.0)
    for _ in range(2000):
        m.step()
    df = m.datacollector.get_model_vars_dataframe()
    assert (df["Wage_Rate"] == W_BAR).all()
    assert (df["Wage_Floor_Binding"] == 0.0).all()
    # Same steady-state Output as the committed labour-market pin.
    assert float(df.tail(50).mean()["Output"]) == pytest.approx(132.0262597647814, abs=1e-9)


def test_eta_default_is_zero():
    """The constructor default must be eta = 0.0, so the model's default behaviour is
    unchanged by brief 07."""
    def final(seed, **kw):
        m = MacroModel(retention_ratio=REF_RHO, seed=seed, **kw)
        for _ in range(300):
            m.step()
        return m.datacollector.get_model_vars_dataframe()["Output"].iloc[-1]
    assert final(0) == final(0, eta=0.0)


def test_wage_uses_lagged_unemployment_not_current():
    """w_t is set from U_{t-1} (start-of-step employed flags), before the labour market
    changes employment within the step (brief 07 §7.3)."""
    m = MacroModel(retention_ratio=REF_RHO, seed=0, sigma=0.5, eta=0.10)
    # Impose a known pre-step unemployment by firing half the workforce.
    for h in _households(m)[:50]:
        if h.employed:
            h.employer.workers.remove(h)
            h.employed = False
            h.employer = None
    u_prev = 1.0 - sum(len(f.workers) for f in _firms(m)) / m.num_households
    expected = wage_from_curve(W_BAR, u_prev, 0.10, U_ref=U_REF, U_min=m.U_min, w_min=m.wage_floor)

    m.step()
    assert m.wage_rate == pytest.approx(expected, rel=1e-12)

    # And it did NOT use the post-step unemployment (the labour market rehired).
    u_now = m.datacollector.get_model_vars_dataframe()["Unemployment_Rate"].iloc[-1]
    if abs(u_now - u_prev) > 1e-9:
        w_if_current = wage_from_curve(
            W_BAR, u_now, 0.10, U_ref=U_REF, U_min=m.U_min, w_min=m.wage_floor
        )
        assert m.wage_rate != pytest.approx(w_if_current, rel=1e-12)


@pytest.mark.parametrize("eta", [0.05, 0.10, 0.15])
def test_determinism_with_wage_curve(eta):
    """Same seed => same trajectory, even with the wage curve on (brief 07 §7.5)."""
    def final(seed):
        m = MacroModel(retention_ratio=REF_RHO, seed=seed, sigma=0.5, eta=eta)
        for _ in range(300):
            m.step()
        return m.datacollector.get_model_vars_dataframe()["Output"].iloc[-1]
    assert final(3) == final(3)
    assert final(1) != final(2)


def test_wage_curve_opens_the_substitution_channel():
    """High U (> U_ref) with eta > 0 lowers the wage, which RAISES profit-max labour at
    the same (K, A): the capital-labour substitution channel the critic invokes and the
    brief tests for the existence of (brief 07 §7.6)."""
    K, A, sigma = 40.0, 1.0, 0.5          # sigma < 1 => finite L_profitmax
    U_high = 0.45                          # above U_ref => wage below w_bar
    w_eta0 = wage_from_curve(W_BAR, U_high, 0.0, U_ref=U_REF, U_min=0.01, w_min=0.45)
    w_eta = wage_from_curve(W_BAR, U_high, 0.10, U_ref=U_REF, U_min=0.01, w_min=0.45)
    assert w_eta < w_eta0

    L_eta0 = ces_labour_profitmax(K, A, w_eta0, K0, L0, PI0, sigma)
    L_eta = ces_labour_profitmax(K, A, w_eta, K0, L0, PI0, sigma)
    assert L_eta > L_eta0


# ======================================================================
# Brief 08 — adaptive expectations on demand
# ======================================================================

def test_adaptive_expectation_converges_geometrically_to_constant_demand():
    """With D held constant and lambda_e < 1, the expectation error shrinks by the exact
    factor (1 - lambda_e) each step (brief 08 §6.1)."""
    D = 100.0
    for gain in (0.25, 0.5, 0.75):
        Ye = 40.0
        prev_err = abs(Ye - D)
        for _ in range(200):
            Ye = adaptive_expectation(Ye, D, gain)
            err = abs(Ye - D)
            # The geometric law holds until the gap reaches the float noise floor near D
            # (ulp(100) ~ 1.4e-14), below which it cannot keep halving; assert above it.
            if prev_err > 1e-7:
                assert err == pytest.approx(prev_err * (1.0 - gain), rel=1e-9)
            prev_err = err
        assert Ye == pytest.approx(D, abs=1e-9)   # 200 steps converges even at gain 0.25


def test_adaptive_expectation_gain_zero_is_frozen():
    """lambda_e = 0 never updates: the expectation stays put (degenerate, brief 08 §2)."""
    Ye = 40.0
    for _ in range(10):
        Ye = adaptive_expectation(Ye, 100.0, 0.0)
        assert Ye == 40.0


def test_adaptive_expectation_gain_one_is_exactly_static():
    """lambda_e = 1 returns D exactly — the byte-identity branch (brief 08 §2).

    ``prev + 1.0*(faced - prev)`` is NOT ``faced`` bit-for-bit for these values in IEEE-754;
    the explicit branch is what guarantees the equality the committed-panel byte-check needs.
    """
    witnesses = [(a / 7.0, b / 7.0) for a in range(1, 12) for b in range(1, 12)]
    assert all(adaptive_expectation(p, f, 1.0) == f for p, f in witnesses)
    # The branch is load-bearing: for some of these pairs the arithmetic form prev +
    # 1.0*(faced - prev) loses the low bit and is NOT equal to faced bit-for-bit.
    assert any((p + 1.0 * (f - p)) != f for p, f in witnesses)


def test_expectation_gain_one_nests_the_static_model_bit_for_bit():
    """expectation_gain = 1.0 reproduces the default (static) trajectory exactly, on a
    short run with the wage curve on (brief 08 §6.2) — protects the explicit branch."""
    def outputs(**kw):
        m = MacroModel(retention_ratio=REF_RHO, seed=0, sigma=0.5, eta=0.10, **kw)
        out = []
        for _ in range(200):
            m.step()
            out.append(sum(f.production for f in _firms(m)))
        return out
    assert outputs() == outputs(expectation_gain=1.0)


def test_expectation_gain_default_is_one():
    """The constructor default is lambda_e = 1.0, so the model's default behaviour is
    unchanged by brief 08 (brief 08 §5)."""
    def final(seed, **kw):
        m = MacroModel(retention_ratio=REF_RHO, seed=seed, **kw)
        for _ in range(300):
            m.step()
        return m.datacollector.get_model_vars_dataframe()["Output"].iloc[-1]
    assert final(0) == final(0, expectation_gain=1.0)


def test_expectation_updates_from_the_closed_period_not_the_next():
    """Ye_t is a function of (Ye_{t-1}, D_t) where D_t is the demand of the period that
    just closed — it cannot depend on next period's demand (brief 08 §6.3)."""
    m = MacroModel(retention_ratio=REF_RHO, seed=0, sigma=0.5, eta=0.0, expectation_gain=0.5)
    for _ in range(20):
        m.step()
    f = _firms(m)[0]
    ye_before = f.expected_demand
    m.step()
    # After the step, expected_demand must equal the adaptive update of the PRE-step
    # expectation towards THIS step's realised (faced) demand.
    assert f.expected_demand == pytest.approx(
        adaptive_expectation(ye_before, f.faced_demand, 0.5), rel=1e-12
    )


@pytest.mark.parametrize("gain", [0.25, 0.5])
def test_determinism_with_adaptive_expectations(gain):
    """Same seed => same trajectory with lambda_e < 1 (brief 08 §6.5)."""
    def final(seed):
        m = MacroModel(retention_ratio=REF_RHO, seed=seed, sigma=0.5, eta=0.10,
                       expectation_gain=gain)
        for _ in range(300):
            m.step()
        return m.datacollector.get_model_vars_dataframe()["Output"].iloc[-1]
    assert final(3) == final(3)
    assert final(1) != final(2)


@pytest.mark.parametrize("bad", [-0.1, 1.0 + 1e-9, 2.0])
def test_expectation_gain_out_of_range_raises(bad):
    """lambda_e must lie in [0, 1] (brief 08 §6.6)."""
    with pytest.raises(ValueError):
        MacroModel(seed=0, expectation_gain=bad)


def test_expectation_gain_bounds_are_admissible():
    """Both endpoints are valid: 1.0 (default/static) and 0.0 (frozen, degenerate)."""
    MacroModel(seed=0, expectation_gain=0.0)
    MacroModel(seed=0, expectation_gain=1.0)


def test_expected_demand_reporter_is_a_sane_convergence_diagnostic():
    """In steady state the demand expectation tracks realised (faced) demand, which weakly
    exceeds rationed output, so Expected_Demand sits at Output's order and just above it
    (brief 08 §3 diagnostic).  Checked for a damped gain and the static default."""
    for gain in (0.25, 1.0):
        s = _steady(sigma=1.0, eta=0.0, expectation_gain=gain, steps=1500)
        ed, out = float(s["Expected_Demand"]), float(s["Output"])
        assert math.isfinite(ed) and ed > 0.0
        assert ed == pytest.approx(out, rel=0.10)


def test_run_grid_panels_single_pool_matches_per_config_path():
    """The single-pool driver (brief 08 §4) must return, per config, exactly what a
    separate run_grid_panel call produces — same seeds, same cells, no reordering."""
    cfgs = [
        dict(c0=1.0, eta=0.0, expectation_gain=1.0),
        dict(c0=1.0, eta=0.10, expectation_gain=0.5),
    ]
    panels = run_grid_panels(
        cfgs, sigmas=[0.5, 1.0], rhos=[0.40, 0.50], seeds=2, steps=300, workers=1
    )
    for cfg, got in zip(cfgs, panels):
        ref = run_grid_panel(
            sigmas=[0.5, 1.0], rhos=[0.40, 0.50], seeds=2, steps=300, workers=1, **cfg
        )
        pd.testing.assert_frame_equal(got, ref)


def test_run_grid_panels_metrics_override_adds_expected_demand():
    """The metrics override collects Expected_Demand without disturbing _PANEL_METRICS."""
    panels = run_grid_panels(
        [dict(c0=1.0, expectation_gain=0.5)],
        sigmas=[1.0], rhos=[0.40], seeds=1, steps=200, workers=1,
        metrics=_PANEL_METRICS + ["Expected_Demand"],
    )
    assert "Expected_Demand" in panels[0].columns
    assert "Expected_Demand" not in _PANEL_METRICS      # the shared list is untouched

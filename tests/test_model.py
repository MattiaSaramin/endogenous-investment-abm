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

import pytest

from model import (
    MacroModel,
    ANCHOR_K0,
    ANCHOR_L0,
    compute_gini,
    _households,
    _firms,
)
from agents import (
    Firm,
    Household,
    Capitalist,
    R_EPS,
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

@pytest.mark.parametrize("rho", [0.35, 0.40])
def test_money_is_conserved(rho):
    model = MacroModel(retention_ratio=rho, seed=7)
    initial = total_money(model)
    for _ in range(600):
        model.step()
        assert total_money(model) == pytest.approx(initial, abs=1e-7)


@pytest.mark.parametrize("rho", [0.35, 0.40])
def test_buffer_returns_to_zero(rho):
    model = MacroModel(retention_ratio=rho, seed=2)
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


@pytest.mark.parametrize("seed", [0, 1])
@pytest.mark.parametrize("rho", GRID_RHO)
@pytest.mark.parametrize("sigma", GRID_SIGMA)
def test_invariants_hold_across_the_grid(sigma, rho, seed):
    """SFC, the zero buffer, the distribution identity and the labour accounting
    must survive every cell of the sigma x rho grid, not just sigma = 1."""
    model = MacroModel(retention_ratio=rho, seed=seed, sigma=sigma)
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
